import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import math

from skyfield.api import load
from skyfield.framelib import ecliptic_frame

# ----------------------------
# 1. Astro Engine Setup
# ----------------------------
PLANETS = ['mercury', 'venus', 'mars', 'jupiter', 'saturn']

@st.cache_resource
def load_skyfield():
    """Cache the ephemeris so it doesn't reload on every button click"""
    ephemeris = load('de421.bsp')
    ts = load.timescale()
    earth = ephemeris['earth']
    planets = {name: ephemeris[f"{name} barycenter"] for name in PLANETS}
    return ephemeris, ts, earth, planets

def get_daily_astro_pull(date: pd.Timestamp, ts, earth, planets):
    """Calculates the net planetary directional pull for a specific day"""
    t = ts.utc(date.year, date.month, date.day)
    
    net_pull = 0.0
    for name, body in planets.items():
        ast = earth.at(t).observe(body)
        try:
            lat, lon, _ = ast.frame_latlon(ecliptic_frame)
            lon_rad = lon.radians
            lat_rad = lat.radians
            _, _, dist = ast.radec()
            distance = max(dist.au, 0.1) # Prevent division by zero
            
            # Gravitational vector projected on the Y-axis (Up/Down)
            # Weighted by inverse square of distance
            pull = (math.sin(lon_rad) * math.cos(lat_rad)) / (distance ** 2)
            net_pull += pull
        except Exception:
            continue
            
    return net_pull

# ----------------------------
# 2. Market Math & Backtesting
# ----------------------------
def calculate_signals(df, ts, earth, planets):
    """Generates daily signals using Rolling Z-Scores of Astro Pull vs Price Momentum"""
    
    # 1. Calculate Daily Astro Pull
    astro_pulls = []
    progress_bar = st.progress(0)
    st.write("Calculating planetary vectors for historical data...")
    
    total_days = len(df)
    for i, date in enumerate(df.index):
        pull = get_daily_astro_pull(date, ts, earth, planets)
        astro_pulls.append(pull)
        if i % 50 == 0:
            progress_bar.progress(min(i / total_days, 1.0))
            
    progress_bar.progress(1.0)
    df['Astro_Pull'] = astro_pulls
    
    # 2. Calculate Market Momentum (10-day slope)
    df['Price_Momentum'] = df['Close'].diff(10)
    
    # 3. Create the Astro-Oscillator (Difference between normalized market and astro vectors)
    # We use a 20-day rolling window to calculate dynamic Z-scores
    df['Astro_Z'] = (df['Astro_Pull'] - df['Astro_Pull'].rolling(20).mean()) / df['Astro_Pull'].rolling(20).std()
    df['Momentum_Z'] = (df['Price_Momentum'] - df['Price_Momentum'].rolling(20).mean()) / df['Price_Momentum'].rolling(20).std()
    
    df['Divergence'] = df['Momentum_Z'] - df['Astro_Z']
    
    # 4. Generate Signals (Trigger when divergence is extreme)
    signals = []
    for div in df['Divergence']:
        if pd.isna(div):
            signals.append("HOLD")
        elif div > 1.5:  # Market is high, planets are low -> Reversal Down
            signals.append("🔴 SELL")
        elif div < -1.5: # Market is low, planets are high -> Reversal Up
            signals.append("🟢 BUY")
        else:
            signals.append("HOLD")
            
    df['Signal'] = signals
    
    # 5. Evaluate Backtest (Look forward 2 trading days)
    df['T+2_Close'] = df['Close'].shift(-2)
    df['Trade_Return_%'] = ((df['T+2_Close'] - df['Close']) / df['Close']) * 100
    
    results = []
    for i in range(len(df)):
        sig = df['Signal'].iloc[i]
        ret = df['Trade_Return_%'].iloc[i]
        
        if pd.isna(ret): # Last few days of the dataset won't have future data yet
            results.append("Pending")
        elif sig == "🟢 BUY":
            results.append("✅ WIN" if ret > 0 else "❌ LOSS")
        elif sig == "🔴 SELL":
            results.append("✅ WIN" if ret < 0 else "❌ LOSS")
        else:
            results.append("-")
            
    df['Outcome'] = results
    return df.dropna(subset=['Close'])

# ----------------------------
# 3. Streamlit UI
# ----------------------------
st.set_page_config(page_title="Daily Astro-Gann Signals", layout="wide")
st.title("🌌 Daily Astro-Gann Signal Generator")
st.markdown("Generates point-in-time daily trading signals for the next day, and backtests historical accuracy over a 2-day trading window.")

# Load Skyfield (Cached)
ephemeris, ts, earth, planets = load_skyfield()

st.sidebar.header("Asset Configuration")
ticker = st.sidebar.text_input("Ticker Symbol", value="^NSEI")
start_date = st.sidebar.date_input("Backtest Start Date", value=pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("End Date (Leave as today for LIVE signals)", value=pd.to_datetime("today"))

if st.sidebar.button("Generate Signals & Backtest"):
    with st.spinner(f"Fetching {ticker} and running daily planetary physics..."):
        try:
            # Fetch Data
            df = yf.download(ticker, start=start_date, end=end_date + timedelta(days=1), progress=False)
            if df.empty:
                st.error("No data found. Check ticker or dates.")
                st.stop()
                
            # Flatten multi-index if necessary (common in new yfinance versions)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            # Run calculations
            analyzed_df = calculate_signals(df, ts, earth, planets)
            
            # Extract action-only trades
            trades_df = analyzed_df[analyzed_df['Signal'].isin(["🟢 BUY", "🔴 SELL"])].copy()
            wins = len(trades_df[trades_df['Outcome'] == "✅ WIN"])
            losses = len(trades_df[trades_df['Outcome'] == "❌ LOSS"])
            total_resolved = wins + losses
            win_rate = (wins / total_resolved * 100) if total_resolved > 0 else 0
            
            st.success("Computation Complete!")
            
            # --- LIVE SIGNAL SECTION ---
            st.markdown("---")
            st.subheader("⚡ LIVE SIGNAL FOR NEXT OPEN")
            latest_day = analyzed_df.iloc[-1]
            latest_date = analyzed_df.index[-1].strftime('%Y-%m-%d')
            current_signal = latest_day['Signal']
            
            if current_signal == "🟢 BUY":
                st.info(f"**Date:** {latest_date} | **Action:** 🟢 BUY (Expect upward move over next 2 days)")
            elif current_signal == "🔴 SELL":
                st.error(f"**Date:** {latest_date} | **Action:** 🔴 SELL (Expect downward move over next 2 days)")
            else:
                st.warning(f"**Date:** {latest_date} | **Action:** ⚖️ HOLD (No planetary edge detected today)")
            st.markdown("---")
            
            # --- BACKTEST RESULTS ---
            st.subheader("📊 Backtest Scorecard (T+2 Days Return)")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Signals Generated", total_resolved)
            c2.metric("Winning Trades", wins)
            c3.metric("Losing Trades", losses)
            
            # Color code the win rate
            if win_rate > 55:
                c4.metric("Win Rate", f"{win_rate:.1f}%", "Profitable Edge")
            else:
                c4.metric("Win Rate", f"{win_rate:.1f}%", "-No Statistical Edge")
            
            # --- TRADE LOG ---
            st.subheader("📅 Detailed Trade Log")
            # Format dataframe for display
            display_df = trades_df.copy()
            display_df.index = display_df.index.strftime('%Y-%m-%d')
            display_df = display_df[['Close', 'Signal', 'Trade_Return_%', 'Outcome']]
            display_df['Trade_Return_%'] = display_df['Trade_Return_%'].round(2).astype(str) + "%"
            
            st.dataframe(display_df.sort_index(ascending=False), use_container_width=True)
            
        except Exception as e:
            st.error(f"An error occurred: {e}")