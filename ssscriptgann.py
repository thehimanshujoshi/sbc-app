import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from scipy.signal import find_peaks
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any

from skyfield.api import load
from skyfield.framelib import ecliptic_frame

# ----------------------------
# 1. Configuration & Core Classes
# ----------------------------
PLANETS = ['mercury', 'venus', 'mars', 'jupiter', 'saturn']
ORBITAL_PERIODS = {'mercury': 88, 'venus': 225, 'mars': 687, 'jupiter': 4333, 'saturn': 10759}
EARTH_AXIAL_TILT = 23.5
HISTOGRAM_BINS = 12
ANALYSIS_MAX_DAYS = 360
ANALYSIS_STEP_DAYS = 7

class SkyfieldPlanetaryDataProvider:
    def __init__(self):
        self.ephemeris = load('de421.bsp')
        self.timescale = load.timescale()
        self.earth = self.ephemeris['earth']
        self.planets = {name: self.ephemeris[f"{name} barycenter"] for name in PLANETS}
        self.orbital_periods = ORBITAL_PERIODS

    @staticmethod
    def _norm_deg(x: float) -> float:
        return float(x % 360.0)

    def get_planetary_data(self, date: datetime) -> Dict[str, Dict[str, float]]:
        t = self.timescale.utc(date.year, date.month, date.day)
        t_next = self.timescale.utc((date + timedelta(days=1)).year, (date + timedelta(days=1)).month, (date + timedelta(days=1)).day)
        data = {}
        
        for name, body in self.planets.items():
            ast = self.earth.at(t).observe(body)
            lon_deg, lat_deg, velocity = 0.0, 0.0, 0.0
            
            try:
                lat, lon, lat_rate, lon_rate = ast.frame_latlon_and_rates(ecliptic_frame)
                lon_deg, lat_deg = float(lon.degrees), float(lat.degrees)
                velocity = float(lon_rate.degrees_per_day) if hasattr(lon_rate, "degrees_per_day") else float(lon_rate)
            except Exception:
                try:
                    lat, lon, _ = ast.frame_latlon(ecliptic_frame)
                    lon_deg, lat_deg = float(lon.degrees), float(lat.degrees)
                    ast_next = self.earth.at(t_next).observe(body)
                    lat_n, lon_n, _ = ast_next.frame_latlon(ecliptic_frame)
                    velocity = float((float(lon_n.degrees) - lon_deg + 540.0) % 360.0 - 180.0)
                except Exception:
                    pass

            try:
                _, dec, dist = ast.radec()
                decl, distance = float(dec.degrees), float(dist.au)
            except Exception:
                decl, distance = lat_deg, 0.0

            data[name] = {
                'longitude': self._norm_deg(lon_deg), 'latitude': lat_deg,
                'declination': decl, 'distance': distance, 'velocity': velocity,
                'orbital_period': float(self.orbital_periods.get(name, 1.0))
            }
        return data

@dataclass
class MarketData:
    dates: List[datetime]
    prices: np.ndarray
    ref_date: datetime
    ref_price: float
    times_from_start: np.ndarray
    poly_coeffs: np.ndarray

class ComponentCalculator:
    def __init__(self, market: MarketData):
        self.market = market

    def calculate_k(self, target_date: datetime, planet_data: Dict[str, Dict[str, float]]) -> float:
        T_market = float(np.mean(np.diff([d.toordinal() for d in self.market.dates]))) if len(self.market.dates) < 2 else 1.0
        omega_market = 2.0 * np.pi / max(T_market, 1e-9)
        days_elapsed = (target_date - self.market.dates[0]).days
        sync_sum = 0.0
        for data in planet_data.values():
            omega_planet = 2.0 * np.pi / max(data.get('orbital_period', 1.0), 1.0)
            theta_market = (omega_market * days_elapsed) % (2.0 * np.pi)
            delta_theta = np.radians(data['longitude']) - theta_market
            coupling = np.exp(-abs(omega_planet - omega_market) / max(omega_market, 1e-10))
            contribution = coupling * np.sin(delta_theta)
            if data.get('velocity', 0.0) < 0: contribution *= -1.0
            sync_sum += contribution
        return float(sync_sum)

    def calculate_w(self, planet_data: Dict[str, Dict[str, float]]) -> float:
        longitudes = [v['longitude'] for v in planet_data.values()]
        declinations = [v['declination'] for v in planet_data.values()]
        velocities = [v['velocity'] for v in planet_data.values()]
        
        hist, _ = np.histogram(longitudes, bins=HISTOGRAM_BINS, range=(0, 360))
        probs_nz = (hist / max(len(longitudes), 1))[hist > 0]
        H = -np.sum(probs_nz * np.log2(probs_nz + 1e-12)) if probs_nz.size > 0 else 0.0
        H_max = np.log2(HISTOGRAM_BINS) if HISTOGRAM_BINS > 0 else 1.0
        I = 1.0 - (H / H_max) if H_max > 0 else 0.0
        
        arr = [v * np.sin(np.radians(d)) for v, d in zip(velocities, declinations)]
        grad_time = float(np.mean(arr)) if arr else 0.0
        grad_space = float(np.std(declinations) / EARTH_AXIAL_TILT) if declinations else 0.0
        return float(I * grad_time * (1.0 + grad_space))

    def calculate_p(self, target_date: datetime, planet_data: Dict[str, Dict[str, float]]) -> float:
        days_ahead = (target_date - self.market.ref_date).days
        if days_ahead <= 0: return 0.0
        
        price_projection = float(np.polyval(self.market.poly_coeffs, self.market.times_from_start[-1] + days_ahead))
        total_vec = np.zeros(3, dtype=float)
        for p in planet_data.values():
            lon, lat = np.radians(p['longitude']), np.radians(p['declination'])
            weight = 1.0 / (max(p.get('distance', 1e-6), 1e-6) ** 2)
            total_vec += weight * np.array([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])
        
        attraction = float(np.linalg.norm(total_vec)) * (price_projection - float(self.market.ref_price)) / max((days_ahead ** 1.5), 1e-9)
        return float(attraction)

# ----------------------------
# 2. Automated Extremes & Engine Orchestration
# ----------------------------
def fetch_and_find_extremes(symbol: str, start_date: str, distance: int) -> List[Tuple[str, float, str]]:
    df = yf.download(symbol, start=start_date, progress=False)
    if df.empty:
        raise ValueError(f"No data found for ticker {symbol}")
    
    prices = df['Close'].values.flatten()
    dates = df.index
    
    tops_idx, _ = find_peaks(prices, distance=distance)
    bottoms_idx, _ = find_peaks(-prices, distance=distance)
    
    extremes = [(dates[i].strftime('%Y-%m-%d'), float(prices[i]), 'top') for i in tops_idx] + \
               [(dates[i].strftime('%Y-%m-%d'), float(prices[i]), 'bottom') for i in bottoms_idx]
    
    extremes.sort(key=lambda x: pd.to_datetime(x[0]))
    return extremes

def run_analysis(extremes: List[Tuple[str, float, str]]) -> pd.DataFrame:
    if not extremes: raise ValueError("No extremes found. Try decreasing peak distance.")
    
    parsed = sorted([{'date': datetime.strptime(e[0], '%Y-%m-%d'), 'price': float(e[1])} for e in extremes], key=lambda x: x['date'])
    dates = [p['date'] for p in parsed]
    prices = np.array([p['price'] for p in parsed], dtype=float)
    times = np.array([(d - dates[0]).days for d in dates], dtype=float)
    poly = np.polyfit(times, prices, 2) if prices.size >= 3 else np.array([0.0, 0.0, float(prices[-1])])
    
    market = MarketData(dates, prices, dates[-1], float(prices[-1]), times, poly)
    calc = ComponentCalculator(market)
    provider = SkyfieldPlanetaryDataProvider()

    results, prev = [], None
    for days in range(0, ANALYSIS_MAX_DAYS + 1, ANALYSIS_STEP_DAYS):
        target = market.ref_date + timedelta(days=days)
        pdata = provider.get_planetary_data(target)
        k, w, p = calc.calculate_k(target, pdata), calc.calculate_w(pdata), calc.calculate_p(target, pdata)
        
        row = {'days': days, 'date': target.strftime('%Y-%m-%d'), 'K': k, 'W': w, 'P': p}
        if prev is not None:
            row.update({
                'K_change': (np.sign(k) != np.sign(prev['K'])) and (prev['K'] != 0),
                'W_change': (np.sign(w) != np.sign(prev['W'])) and (prev['W'] != 0),
                'P_change': (np.sign(p) != np.sign(prev['P'])) and (prev['P'] != 0)
            })
            row['critical_point'] = any([row['K_change'], row['W_change'], row['P_change']])
        else:
            row.update({'K_change': False, 'W_change': False, 'P_change': False, 'critical_point': False})
        
        results.append(row)
        prev = {'K': k, 'W': w, 'P': p}

    df = pd.DataFrame(results)
    
    # Thresholding & Classification
    k_arr, w_arr, p_arr = df['K'].dropna().to_numpy(), df['W'].dropna().to_numpy(), df['P'].dropna().to_numpy()
    t = {
        'K_strong_neg': float(np.percentile(k_arr[k_arr < 0], 25)) if k_arr[k_arr < 0].size else 0,
        'K_weak_neg': float(np.percentile(k_arr[k_arr < 0], 75)) if k_arr[k_arr < 0].size else 0,
        'K_weak_pos': float(np.percentile(k_arr[k_arr > 0], 25)) if k_arr[k_arr > 0].size else 0,
        'K_strong_pos': float(np.percentile(k_arr[k_arr > 0], 75)) if k_arr[k_arr > 0].size else 0,
        'P_threshold_pos': float(np.percentile(p_arr[p_arr > 0], 25)) if p_arr[p_arr > 0].size else 0,
        'W_low': float(np.percentile(np.abs(w_arr), 25)) if w_arr.size else 0,
    }

    def get_signal(row):
        k, w, p = row['K'], row['W'], row['P']
        if k < t['K_strong_neg']: return "🚀 STRONG BUY"
        if k < t['K_weak_neg']: return "🟢 BUY"
        if k > t['K_strong_pos']: return "🔴 STRONG SELL"
        if k > t['K_weak_pos']: return "⚠️ SELL"
        if k > 0: return "🟡 LIGHT SELL"
        if k < 0 and p > t['P_threshold_pos']: return "🔥 DUAL BUY"
        if abs(k) < 0.1 and abs(w) < t['W_low']: return "⚖️ EQUILIBRIUM"
        return "🔄 TRANSITION"

    def get_phase(K, W, P):
        if K < 0 and P > 0.5: return "🚀 Inverse Coherence - Bullish Impulse"
        if K > 0 and abs(K) > 0.3 and P < 0: return "⚠️ Divergence - Possible Top"
        if K > 0.5 and P < -0.3: return "📻 Harmonic Contraction - Confirmed Drop"
        if abs(K) < 0.2 and abs(W) < 0.2 and abs(P) < 0.2: return "⚖️ Equilibrium - Sideways"
        if P > 0 and K < 0.3: return "📈 Sustained Rise"
        return "🔄 Transition"

    df['signal'] = df.apply(get_signal, axis=1)
    df['phase'] = df.apply(lambda r: get_phase(r['K'], r['W'], r['P']), axis=1)
    df['lightning'] = df.apply(lambda r: "⚡" if (r['K'] < t['K_strong_neg'] or r['K'] > t['K_strong_pos'] or (r['K_change'] and abs(r['K']) > abs(t['K_weak_neg']) * 0.5) or (r['P_change'] and abs(r['P']) > 10.0)) else "", axis=1)
    
    return df

# ----------------------------
# 3. Streamlit UI
# ----------------------------
st.set_page_config(page_title="Automated Gann Analysis", layout="wide")
st.title("🌌 Automated Gann Planetary Analysis")
st.markdown("Enter a ticker symbol to automatically fetch data, identify market extremes, and run orbital projections.")

st.sidebar.header("Asset Configuration")
ticker = st.sidebar.text_input("Yahoo Finance Ticker", value="^NSEI")
st.sidebar.caption("Examples: ^NSEI (Nifty 50), CL=F (Crude), GC=F (Gold), RELIANCE.NS")
start_date = st.sidebar.date_input("Fetch History From", value=pd.to_datetime("2020-01-01"))
peak_distance = st.sidebar.slider("Days between major extremes", min_value=10, max_value=100, value=30)

if st.sidebar.button("Run Automated Analysis"):
    with st.spinner(f"Fetching {ticker} data and calculating orbital mechanics (this may take a few seconds on first run)..."):
        try:
            extremes = fetch_and_find_extremes(ticker, start_date, peak_distance)
            st.info(f"Automatically identified {len(extremes)} historical Tops and Bottoms.")
            
            df_results = run_analysis(extremes)
            crit_df = df_results[df_results['critical_point'] == True].copy()
            
            st.success("Analysis Complete!")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Critical Events Detected", len(crit_df))
            col2.metric("Potential BUY Signals", len(crit_df[crit_df['signal'].str.contains('BUY', na=False)]))
            col3.metric("Potential SELL Signals", len(crit_df[crit_df['signal'].str.contains('SELL', na=False)]))
            
            st.subheader(f"📅 Critical Forecast Dates for {ticker}")
            display_df = crit_df[['lightning', 'days', 'date', 'signal', 'phase', 'K', 'W', 'P']]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
        except Exception as e:
            st.error(f"Error: {e}")
            st.write("Ensure the ticker symbol is correct and valid on Yahoo Finance.")