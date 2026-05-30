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
# 2. Hybrid Market Math (Astro + TA)
# ----------------------------
def calculate_signals(df, ts, earth, planets, tp_pct, sl_pct):
    # 1. Astro Calculations
    astro_pulls = []
    for date in df.index:
        astro_pulls.append(get_daily_astro_pull(date, ts, earth, planets))
    df['Astro_Pull'] = astro_pulls
    
    # 2. Technical Analysis (The Reality Check)
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    
    # Calculate RSI manually
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    df['Price_Momentum'] = df['Close'].diff(10)
    df['Astro_Z'] = (df['Astro_Pull'] - df['Astro_Pull'].rolling(20).mean()) / df['Astro_Pull'].rolling(20).std()
    df['Momentum_Z'] = (df['Price_Momentum'] - df['Price_Momentum'].rolling(20).mean()) / df['Price_Momentum'].rolling(20).std()
    df['Divergence'] = df['Momentum_Z'] - df['Astro_Z']
    
    # 3. Hybrid Signal Generation (Astro + TA Confluence)
    signals = []
    for i in range(len(df)):
        div = df['Divergence'].iloc[i]
        close = df['Close'].iloc[i]
        sma = df['SMA_50'].iloc[i]
        rsi = df['RSI'].iloc[i]
        
        if pd.isna(div) or pd.isna(sma):
            signals.append("HOLD")
        # BUY: Astro says buy AND we are above 50-day average (Uptrend) AND not overbought
        elif div < -1.5 and close > sma and rsi < 70:
            signals.append("🟢 BUY")
        # SELL: Astro says sell AND we are below 50-day average (Downtrend) AND not oversold
        elif div > 1.5 and close < sma and rsi > 30:
            signals.append("🔴 SELL")
        else:
            signals.append("HOLD")
            
    df['Signal'] = signals
    
    # 4. Strict Risk Management Backtesting (Simulating Intraday)
    # We assume entry at the NEXT day's Open.
    df['Next_Open'] = df['Open'].shift(-1)
    df['Next_High'] = df['High'].shift(-1)
    df['Next_Low'] = df['Low'].shift(-1)
    
    results = []
    profits = []
    
    for i in range(len(df)):
        sig = df['Signal'].iloc[i]
        
        if sig == "HOLD" or pd.isna(df['Next_Open'].iloc[i]):
            results.append("-")
            profits.append(0.0)
            continue
            
        entry_price = df['Next_Open'].iloc[i]
        high = df['Next_High'].iloc[i]
        low = df['Next_Low'].iloc[i]
        
        if sig == "🟢 BUY":
            target = entry_price * (1 + (tp_pct/100))
            stop = entry_price * (1 - (sl_pct/100))
            # Did it hit target or stop first? (Approximation using daily ranges)
            if low <= stop:
                results.append("❌ STOPPED OUT")
                profits.append(-sl_pct)
            elif high >= target:
                results.append("✅ TP HIT")
                profits.append(tp_pct)
            else:
                results.append("⏳ FLAT (Time Exit)")
                profits.append(((df['Close'].shift(-1).iloc[i] - entry_price) / entry_price) * 100)
                
        elif sig == "🔴 SELL":
            target = entry_price * (1 - (tp_pct/100))
            stop = entry_price * (1 + (sl_pct/100))
            if high >= stop:
                results.append("❌ STOPPED OUT")
                profits.append(-sl_pct)
            elif low <= target:
                results.append("✅ TP HIT")
                profits.append(tp_pct)
            else:
                results.append("⏳ FLAT (Time Exit)")
                profits.append(((entry_price - df['Close'].shift(-1).iloc[i]) / entry_price) * 100)
                
    df['Outcome'] = results
    df['P&L_%'] = profits
    return df.dropna(subset=['Close'])

# ----------------------------
# 3. Streamlit UI
# ----------------------------
st.set_page_config(page_title="Hybrid Quant-Astro Alg", layout="wide")
st.title("📈 Hybrid Quant-Astro Algorithmic Trader")
st.markdown("Combines planetary physics with strict Technical Analysis (Trend & RSI) and strict Risk Management.")

ephemeris, ts, earth, planets = load_skyfield()

st.sidebar.header("1. Asset & Time")
ticker = st.sidebar.text_input("Ticker Symbol", value="^NSEI")
start_date = st.sidebar.date_input("Backtest Start Date", value=pd.to_datetime("2021-01-01"))
end_date = st.sidebar.date_input("End Date", value=pd.to_datetime("today"))

st.sidebar.header("2. Risk Management (Crucial)")
take_profit = st.sidebar.number_input("Take Profit Target (%)", value=1.0, step=0.1)
stop_loss = st.sidebar.number_input("Stop Loss (%)", value=0.5, step=0.1)

if st.sidebar.button("Run Hybrid Algorithm"):
    with st.spinner("Crunching historical market data and astrophysics..."):
        try:
            df = yf.download(ticker, start=start_date, end=end_date + timedelta(days=1), progress=False)
            if df.empty:
                st.error("No data found.")
                st.stop()
                
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            analyzed_df = calculate_signals(df, ts, earth, planets, take_profit, stop_loss)
            
            trades_df = analyzed_df[analyzed_df['Signal'].isin(["🟢 BUY", "🔴 SELL"])].copy()
            wins = len(trades_df[trades_df['Outcome'] == "✅ TP HIT"])
            losses = len(trades_df[trades_df['Outcome'] == "❌ STOPPED OUT"])
            flats = len(trades_df[trades_df['Outcome'] == "⏳ FLAT (Time Exit)"])
            
            total_resolved = wins + losses + flats
            win_rate = (wins / total_resolved * 100) if total_resolved > 0 else 0
            
            net_profit = trades_df['P&L_%'].sum()
            
            # --- LIVE EXECUTION PLAN ---
            st.markdown("---")
            st.subheader("⚡ LIVE EXECUTION PLAN (TOMORROW)")
            latest_day = analyzed_df.iloc[-1]
            latest_date = analyzed_df.index[-1].strftime('%Y-%m-%d')
            current_signal = latest_day['Signal']
            last_close = latest_day['Close']
            
            if current_signal == "🟢 BUY":
                st.success(f"**ACTION FOR {latest_date}:** 🟢 BUY ENTRY ALERTS TRIPPED")
                st.write(f"- **Entry Rule:** Buy exactly at Tomorrow's Market Open.")
                st.write(f"- **Take Profit Order (Limit):** Set to sell at {last_close * (1 + (take_profit/100)):.2f} (+{take_profit}%)")
                st.write(f"- **Stop Loss Order (SL):** Set strict stop at {last_close * (1 - (stop_loss/100)):.2f} (-{stop_loss}%)")
                st.write(f"- **Time Exit:** If neither is hit, close position manually at 3:15 PM.")
            elif current_signal == "🔴 SELL":
                st.error(f"**ACTION FOR {latest_date}:** 🔴 SELL ENTRY ALERTS TRIPPED")
                st.write(f"- **Entry Rule:** Short exactly at Tomorrow's Market Open.")
                st.write(f"- **Take Profit Order (Limit):** Set to cover at {last_close * (1 - (take_profit/100)):.2f} (+{take_profit}%)")
                st.write(f"- **Stop Loss Order (SL):** Set strict stop at {last_close * (1 + (stop_loss/100)):.2f} (-{stop_loss}%)")
                st.write(f"- **Time Exit:** If neither is hit, close position manually at 3:15 PM.")
            else:
                st.warning(f"**ACTION FOR {latest_date}:** ⚖️ HOLD")
                st.write("- **Analysis:** Trend and Astro-momentum are not aligned. Do not force a trade today. Preserve capital.")
            st.markdown("---")
            
            # --- BACKTEST RESULTS ---
            st.subheader(f"📊 Backtest Scorecard ({start_date.year} - {end_date.year})")
            st.caption("Because we added strict trend filters, there will be FEWER trades, but they should be HIGHER quality.")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Trades Taken", total_resolved)
            c2.metric("Target Hits (Wins)", wins)
            c3.metric("Stopped Out (Losses)", losses)
            
            if net_profit > 0:
                c4.metric("Net Cumulative P&L", f"+{net_profit:.2f}%", "Profitable")
            else:
                c4.metric("Net Cumulative P&L", f"{net_profit:.2f}%", "-Loss")
            
            # --- TRADE LOG ---
            st.subheader("📅 Detailed Trade Log")
            display_df = trades_df[['Close', 'Signal', 'Outcome', 'P&L_%']].copy()
            display_df.index = display_df.index.strftime('%Y-%m-%d')
            display_df['P&L_%'] = display_df['P&L_%'].round(2).astype(str) + "%"
            st.dataframe(display_df.sort_index(ascending=False), use_container_width=True)
            
        except Exception as e:
            st.error(f"An error occurred: {e}")