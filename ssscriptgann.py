import streamlit as st
import pandas as pd
import yfinance as yf
from scipy.signal import find_peaks

# Import the core logic from your original script
from gann_core import (
    SkyfieldPlanetaryDataProvider,
    StaticExtremesRepository,
    GannAnalysisService,
    setup_logging
)

st.set_page_config(page_title="Automated Gann Analysis", layout="wide")

st.title("🌌 Automated Gann Planetary Analysis")
st.markdown("Enter a ticker symbol, and this app will fetch the data, find the highs/lows, and run the orbital forecast automatically.")

# --- UI for Ticker Input ---
st.sidebar.header("1. Asset Configuration")
ticker = st.sidebar.text_input("Yahoo Finance Ticker", value="^NSEI")
st.sidebar.caption("Examples: ^NSEI (Nifty 50), CL=F (Crude Oil), GC=F (Gold), RELIANCE.NS")

start_date = st.sidebar.date_input("Fetch History From", value=pd.to_datetime("2020-01-01"))
peak_distance = st.sidebar.slider("Days between major Tops/Bottoms", min_value=10, max_value=100, value=30)

# --- Logic to Auto-Fetch Data and Find Extremes ---
def fetch_and_find_extremes(symbol, start, distance):
    df = yf.download(symbol, start=start, progress=False)
    if df.empty:
        raise ValueError(f"No data found for ticker {symbol}")
    
    # We use the 'Close' price. (Some yfinance versions return MultiIndex, so we ensure 1D array)
    prices = df['Close'].values.flatten()
    dates = df.index
    
    # Find Tops (Peaks)
    tops_idx, _ = find_peaks(prices, distance=distance)
    # Find Bottoms (Valleys by inverting the data)
    bottoms_idx, _ = find_peaks(-prices, distance=distance)
    
    extremes = []
    for idx in tops_idx:
        extremes.append((dates[idx].strftime('%Y-%m-%d'), float(prices[idx]), 'top'))
    for idx in bottoms_idx:
        extremes.append((dates[idx].strftime('%Y-%m-%d'), float(prices[idx]), 'bottom'))
    
    # Sort chronologically
    extremes.sort(key=lambda x: pd.to_datetime(x[0]))
    return extremes

if st.sidebar.button("Run Automated Analysis"):
    with st.spinner(f"Fetching data for {ticker} and running planetary math..."):
        try:
            # 1. Auto-generate the extremes
            auto_extremes = fetch_and_find_extremes(ticker, start_date, peak_distance)
            
            st.info(f"Automatically found {len(auto_extremes)} major Tops/Bottoms for {ticker} since {start_date}.")
            
            # 2. Run Gann Service
            setup_logging()
            provider = SkyfieldPlanetaryDataProvider()
            repo = StaticExtremesRepository(auto_extremes)
            service = GannAnalysisService(provider, repo)
            
            df_results, thresholds = service.run_analysis()
            
            # 3. Filter and Display
            crit_df = df_results[df_results['critical_point'] == True].copy()
            
            st.success("Analysis Complete!")
            
            # Display Executive Summary
            st.subheader("Executive Summary")
            buys = len(crit_df[crit_df['signal'].str.contains('BUY', na=False)])
            sells = len(crit_df[crit_df['signal'].str.contains('SELL', na=False)])
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Critical Events Detected", len(crit_df))
            col2.metric("Potential BUY Signals", buys)
            col3.metric("Potential SELL Signals", sells)
            
            # Display the Table
            st.subheader(f"📅 Critical Forecast Dates for {ticker}")
            display_df = crit_df[['lightning', 'days', 'date', 'signal', 'phase', 'K', 'W', 'P']]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.write("Check if the ticker symbol is correct.")
