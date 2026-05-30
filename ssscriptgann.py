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
    ephemeris = load('de421.bsp')
    ts = load.timescale()
    earth = ephemeris['earth']
    planets = {name: ephemeris[f"{name} barycenter"] for name in PLANETS}
    return ephemeris, ts, earth, planets

def get_daily_astro_pull(date: pd.Timestamp, ts, earth, planets):
    t = ts.utc(date.year, date.month, date.day)
    net_pull = 0.0
    for name, body in planets.items():
        ast = earth.at(t).observe(body)
        try:
            lat, lon, _ = ast.frame_latlon(ecliptic_frame)
            lon_rad = lon.radians
            lat_rad = lat.radians
            _, _, dist = ast.radec()
            distance = max(dist.au, 0.1)
            pull = (math.sin(lon_rad) * math.cos(lat_rad)) / (distance ** 2)
            net_pull += pull
        except Exception:
            continue
    return net_pull

# ----------------------------
# 2. Hybrid Market Math & Real-World Window
# ----------------------------
def calculate_signals(df, ts, earth, planets, tp_pct, sl_pct, holding_window, direction_pref):
    # 1. Astro Calculations
    astro_pulls = []
    for date in df.index:
        astro_pulls.append(get_daily_astro_pull(date, ts, earth, planets))
    df['Astro_Pull'] = astro_pulls
    
    # 2. Technical Analysis
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    df['Price_Momentum'] = df['Close'].diff(10)
    df['Astro_Z'] = (df['Astro_Pull'] - df['Astro_Pull'].rolling(20).mean()) / df['Astro_Pull'].rolling(20).std()
    df['Momentum_Z'] = (df['Price_Momentum'] - df['Price_Momentum'].rolling(20).mean()) / df['Price_Momentum'].rolling(20).std()
    df['Divergence'] = df['Momentum_Z'] - df['Astro_Z']
    
    # 3. Hybrid Signal Generation
    raw_signals = []
    for i in range(len(df)):
        div = df['Divergence'].iloc[i]
        close = df['Close'].iloc[i]
        sma = df['SMA_50'].iloc[i]
        rsi = df['RSI'].iloc[i]
        
        if pd.isna(div) or pd.isna(sma):
            raw_signals.append("HOLD")
        elif div < -1.5 and close > sma and rsi < 70:
            raw_signals.append("🟢 BUY")
        elif div > 1.5 and close < sma and rsi > 30:
            raw_signals.append("🔴 SELL")
        else:
            raw_signals.append("HOLD")
            
    # Apply User's Direction Preference
    final_signals = []
    for sig in raw_signals:
        if direction_pref == "Long Only" and sig == "🔴 SELL":
            final_signals.append("HOLD")
        elif direction_pref == "Short Only" and sig == "🟢 BUY":
            final_signals.append("HOLD")
        else:
            final_signals.append(sig)
            
    df['Signal'] = final_signals
    
    # 4. Strict N-Day Rolling Trade Logic
    results = []
    profits = []
    
    for i in range(len(df)):
        sig = df['Signal'].iloc[i]
        
        # If HOLD or trade window extends beyond available current data
        if sig == "HOLD" or (i + holding_window >= len(df)):
            results.append("-")
            profits.append(0.0)
            continue
            
        entry_price = df['Open'].iloc[i+1]
        window_high = df['High'].iloc[i+1 : i+1+holding_window].max()
        window_low = df['Low'].iloc[i+1 : i+1+holding_window].min()
        time_exit_price = df['Close'].iloc[i+holding_window]
        
        if sig == "🟢 BUY":
            target = entry_price * (1 + (tp_pct/100))
            stop = entry_price * (1 - (sl_pct/100))
            
            if window_low <= stop and window_high >= target:
                results.append("⚠️ MIXED (Assumed Stop)")
                profits.append(-sl_pct)
            elif window_low <= stop:
                results.append("❌ STOPPED OUT")
                profits.append(-sl_pct)
            elif window_high >= target:
                results.append("✅ TP HIT")
                profits.append(tp_pct)
            else:
                results.append(f"⏳ TIME EXIT ({holding_window}d)")
                profits.append(((time_exit_price - entry_price) / entry_price) * 100)
                
        elif sig == "🔴 SELL":
            target = entry_price * (1 - (tp_pct/100))
            stop = entry_price * (1 + (sl_pct/100))
            
            if window_high >= stop and window_low <= target:
                results.append("⚠️ MIXED (Assumed Stop)")
                profits.append(-sl_pct)
            elif window_high >= stop:
                results.append("❌ STOPPED OUT")
                profits.append(-sl_pct)
            elif window_low <= target:
                results.append("✅ TP HIT")
                profits.append(tp_pct)
            else:
                results.append(f"⏳ TIME EXIT ({holding_window}d)")
                profits.append(((entry_price - time_exit_price) / entry_price) * 100)
                
    df['Outcome'] = results
    df['P&L_%'] = profits
    return df.dropna(subset=['Close'])

# ----------------------------
# 3. Streamlit UI
# ----------------------------
st.set_page_config(page_title="Pro Signal Terminal", layout="wide")
st.title("📟 Pro Trading Terminal: Astro-Quant System")
st.markdown("Filter by market direction, set time limits, and simulate real-world execution.")

ephemeris, ts, earth, planets = load_skyfield()

# SIDEBAR CONFIGURATION
st.sidebar.header("1. Data Feed")
ticker = st.sidebar.text_input("Ticker Symbol", value="^NSEI")
start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2022-01-01"))
end_date = st.sidebar.date_input("End Date", value=pd.to_datetime("today"))

st.sidebar.header("2. Trade Desk Constraints")
trade_direction = st.sidebar.radio("Direction Preference", ["Both (Long & Short)", "Long Only", "Short Only"])
holding_window = st.sidebar.slider("Max Holding Window (Days)", min_value=1, max_value=15, value=3)

st.sidebar.header("3. Risk Limits")
take_profit = st.sidebar.number_input("Take Profit Limit (%)", value=1.5, step=0.1)
stop_loss = st.sidebar.number_input("Stop Loss Limit (%)", value=0.7, step=0.1)

if st.sidebar.button("Execute System Engine"):
    with st.spinner("Compiling signals and executing simulated trades..."):
        try:
            df = yf.download(ticker, start=start_date, end=end_date + timedelta(days=15), progress=False)
            if df.empty:
                st.error("No data found for this ticker/date range.")
                st.stop()
                
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            # Run Engine
            analyzed_df = calculate_signals(df, ts, earth, planets, take_profit, stop_loss, holding_window, trade_direction)
            
            trades_df = analyzed_df[analyzed_df['Signal'].isin(["🟢 BUY", "🔴 SELL"])].copy()
            wins = len(trades_df[trades_df['Outcome'] == "✅ TP HIT"])
            losses = len(trades_df[trades_df['Outcome'].str.contains("STOP")]) # Catches normal stops and mixed stops
            flats = len(trades_df[trades_df['Outcome'].str.contains("TIME EXIT")])
            
            total_resolved = wins + losses + flats
            win_rate = (wins / total_resolved * 100) if total_resolved > 0 else 0
            net_profit = trades_df['P&L_%'].sum()
            
            # --- LIVE EXECUTION PLAN ---
            st.markdown("---")
            st.subheader("⚡ TOMORROW'S TRADE ORDER")
            
            # We look at the most recent available close to generate tomorrow's signal
            latest_day = analyzed_df.iloc[-holding_window - 1] if len(analyzed_df) > holding_window else analyzed_df.iloc[-1]
            latest_date = analyzed_df.index[-holding_window - 1].strftime('%Y-%m-%d') if len(analyzed_df) > holding_window else analyzed_df.index[-1].strftime('%Y-%m-%d')
            
            current_signal = latest_day['Signal']
            last_close = latest_day['Close']
            
            if current_signal == "🟢 BUY":
                st.success(f"**ORDER GENERATED FOR TOMORROW OPEN:** 🟢 LONG POSITION")
                st.write(f"1. **Execute:** Buy at Market Open.")
                st.write(f"2. **Take Profit (Limit):** {last_close * (1 + (take_profit/100)):.2f} (+{take_profit}%)")
                st.write(f"3. **Stop Loss (Limit):** {last_close * (1 - (stop_loss/100)):.2f} (-{stop_loss}%)")
                st.write(f"4. **Time Constraint:** Close position automatically after {holding_window} trading days if targets are unmet.")
            elif current_signal == "🔴 SELL":
                st.error(f"**ORDER GENERATED FOR TOMORROW OPEN:** 🔴 SHORT POSITION")
                st.write(f"1. **Execute:** Sell Short at Market Open.")
                st.write(f"2. **Take Profit (Limit):** {last_close * (1 - (take_profit/100)):.2f} (+{take_profit}%)")
                st.write(f"3. **Stop Loss (Limit):** {last_close * (1 + (stop_loss/100)):.2f} (-{stop_loss}%)")
                st.write(f"4. **Time Constraint:** Close position automatically after {holding_window} trading days if targets are unmet.")
            else:
                st.warning(f"**ORDER GENERATED FOR TOMORROW OPEN:** ⚖️ FLAT (NO TRADE)")
                st.write("- Market conditions or planetary physics do not meet execution criteria. Preserve capital.")
            st.markdown("---")
            
            # --- BACKTEST RESULTS ---
            st.subheader(f"📊 Strategy Performance ({start_date.year} - Present)")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Executed Trades", total_resolved)
            c2.metric("Target Hits (Wins)", wins)
            c3.metric("Losses / Time Exits", losses + flats)
            
            if net_profit > 0:
                c4.metric("Net Cumulative Edge", f"+{net_profit:.2f}%", "Profitable")
            else:
                c4.metric("Net Cumulative Edge", f"{net_profit:.2f}%", "-Loss")
            
            # --- TRADE LOG ---
            st.subheader("📅 Backtest Trade Ledger")
            display_df = trades_df[['Close', 'Signal', 'Outcome', 'P&L_%']].copy()
            display_df.index = display_df.index.strftime('%Y-%m-%d')
            display_df['P&L_%'] = display_df['P&L_%'].round(2).astype(str) + "%"
            st.dataframe(display_df.sort_index(ascending=False), use_container_width=True)
            
        except Exception as e:
            st.error(f"An error occurred: {e}")
