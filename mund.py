import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import calendar
import swisseph as swe

# =====================================================================
# 1. APPLICATION SETUP & PREMIUM UI STYLING
# =====================================================================
st.set_page_config(
    page_title="Institutional Astro-Finance Oracle",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    h1, h2, h3, h4 { font-family: 'Inter', sans-serif; font-weight: 700; color: #e6edf3; }
    
    /* Oracle Forecasting Cards */
    .forecast-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; margin-bottom: 15px; display: flex; align-items: center; }
    .date-badge { background: #21262d; border: 1px solid #30363d; padding: 10px 15px; border-radius: 6px; font-weight: bold; margin-right: 20px; text-align: center; min-width: 120px; }
    
    /* Strict Signal Classes */
    .rise-signal { border-left: 6px solid #2ea043; }
    .fall-signal { border-left: 6px solid #f85149; }
    .volatility-signal { border-left: 6px solid #d4af37; }
    
    .text-rise { color: #3fb950; font-weight: bold; font-size: 1.1em; }
    .text-fall { color: #ff7b72; font-weight: bold; font-size: 1.1em; }
    .text-warn { color: #d2a8ff; font-weight: bold; font-size: 1.1em; }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. MASSIVE ASSET DICTIONARY & ASTRO MAPPINGS
# =====================================================================
PLANETS = {
    swe.SUN: "Sun", swe.MARS: "Mars", swe.MERCURY: "Mercury", 
    swe.JUPITER: "Jupiter", swe.VENUS: "Venus", swe.SATURN: "Saturn", 
    swe.TRUE_NODE: "Rahu" 
}

ZODIAC_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
EXALTED = {"Sun": 0, "Mars": 9, "Mercury": 5, "Jupiter": 3, "Venus": 11, "Saturn": 6, "Rahu": 1, "Ketu": 7}
DEBILITATED = {"Sun": 6, "Mars": 3, "Mercury": 11, "Jupiter": 9, "Venus": 5, "Saturn": 0, "Rahu": 7, "Ketu": 1}

# Exhaustive Asset Search Engine Database
EQUITY_SECTORS = {
    "Public Sector Undertakings (PSUs)": "Sun", "Government Bonds": "Sun", "Central Banks": "Sun", "Power Generation": "Sun",
    "Defence Manufacturing": "Mars", "Real Estate (Commercial)": "Mars", "Real Estate (Residential)": "Mars", "Infrastructure & Construction": "Mars", "Aerospace & Weapons": "Mars",
    "Information Technology (IT)": "Mercury", "Telecommunications": "Mercury", "E-Commerce Platforms": "Mercury", "FinTech & Payment Gateways": "Mercury", "Logistics & Freight": "Mercury", "Social Media": "Mercury",
    "Banking (Large Cap)": "Jupiter", "NBFCs (Tier 1)": "Jupiter", "Mutual Funds & AMCs": "Jupiter", "Education & EdTech": "Jupiter", "Insurance": "Jupiter",
    "Automobile Manufacturing": "Venus", "Luxury Brands & Retail": "Venus", "Media & Entertainment": "Venus", "Textiles & Apparel": "Venus", "Hospitality & Hotels": "Venus", "FMCG (Cosmetics)": "Venus",
    "Oil & Gas Exploration": "Saturn", "Coal & Mining": "Saturn", "Steel & Iron Mills": "Saturn", "Heavy Machinery": "Saturn", "Waste Management": "Saturn",
    "Artificial Intelligence (AI)": "Rahu", "Biotechnology": "Rahu", "Electric Vehicles (EVs)": "Rahu", "Quantum Computing": "Rahu", "Space Exploration Tech": "Rahu",
    "Pharmaceuticals (R&D)": "Ketu", "Cybersecurity": "Ketu", "Data Forensics": "Ketu", "Alternative Medicine": "Ketu", "Auditing & Compliance": "Ketu"
}

COMMODITIES = {
    "Gold (Physical/Bullion)": "Sun", "Gold (Bonds/ETFs)": "Jupiter",
    "Silver": "Venus", "Copper": "Mars", "Platinum": "Venus", "Palladium": "Rahu",
    "Crude Oil (Brent/WTI)": "Saturn", "Natural Gas": "Saturn", "Thermal Coal": "Saturn", "Uranium": "Rahu",
    "Wheat": "Jupiter", "Corn": "Jupiter", "Sugar": "Venus", "Coffee": "Mars", "Cotton": "Venus", "Soybeans": "Jupiter"
}

CRYPTOCURRENCIES = {
    "Bitcoin (BTC)": "Rahu", "Ethereum (ETH)": "Mercury", "Solana (SOL)": "Mercury",
    "CBDCs (Govt Crypto)": "Sun", "XRP (Banking Crypto)": "Jupiter", 
    "Privacy Coins (Monero/Zcash)": "Ketu", "Memecoins (DOGE/SHIB)": "Rahu",
    "Gaming/Metaverse Tokens": "Venus", "DeFi Bluechips (AAVE/UNI)": "Jupiter", "Layer 2 Infrastructure": "Saturn"
}

# =====================================================================
# 3. HIGH-PRECISION CALCULATION ENGINE
# =====================================================================
@st.cache_data(ttl=3600)
def get_ephemeris(year, month, day):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(year, month, day, 12.0) 
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    
    pos_data = {}
    sun_lon = swe.calc_ut(jd, swe.SUN, flags)[0][0]
    
    for p_id, p_name in PLANETS.items():
        pos, _ = swe.calc_ut(jd, p_id, flags)
        lon, speed = pos[0], pos[3]
        sign_idx = int(lon / 30)
        
        # Combustion Math (Usually 8-12 degrees from Sun)
        is_combust = False
        if p_name not in ["Sun", "Rahu", "Ketu"]:
            diff = abs(lon - sun_lon)
            if diff > 180: diff = 360 - diff
            is_combust = diff <= 10
            
        pos_data[p_name] = {
            "lon": lon, "sign_idx": sign_idx, "sign_name": ZODIAC_SIGNS[sign_idx],
            "is_retro": speed < 0 and p_name not in ["Sun", "Rahu"],
            "is_combust": is_combust
        }
        
    rahu_lon = pos_data["Rahu"]["lon"]
    ketu_lon = (rahu_lon + 180) % 360
    pos_data["Ketu"] = {
        "lon": ketu_lon, "sign_idx": int(ketu_lon / 30), "sign_name": ZODIAC_SIGNS[int(ketu_lon / 30)],
        "is_retro": True, "is_combust": False
    }
    return pos_data

def get_advance_forecast(planet, start_date, days=90):
    """Scans the future to predict exact dates of structural rises or falls for an asset's ruling planet."""
    forecast_events = []
    
    for d in range(1, days + 1):
        target = start_date + timedelta(days=d)
        prev = target - timedelta(days=1)
        
        curr_data = get_ephemeris(target.year, target.month, target.day)[planet]
        prev_data = get_ephemeris(prev.year, prev.month, prev.day)[planet]
        
        # 1. Sign Change (Sector Rotation)
        if curr_data["sign_idx"] != prev_data["sign_idx"]:
            if curr_data["sign_idx"] == EXALTED.get(planet):
                forecast_events.append({"date": target, "signal": "RISE", "title": f"Enters Exaltation ({curr_data['sign_name']})", "desc": "Massive structural breakout. Institutional accumulation peaks. Highly Bullish."})
            elif curr_data["sign_idx"] == DEBILITATED.get(planet):
                forecast_events.append({"date": target, "signal": "FALL", "title": f"Enters Debilitation ({curr_data['sign_name']})", "desc": "Severe fundamental bleeding. Asset loses intrinsic value. Highly Bearish."})
            else:
                forecast_events.append({"date": target, "signal": "VOLATILE", "title": f"Transits into {curr_data['sign_name']}", "desc": "Sector rotation triggers volume spikes. Trend shifts direction."})
                
        # 2. Retrogression Shifts (Reversals)
        if curr_data.get("is_retro") and not prev_data.get("is_retro"):
            forecast_events.append({"date": target, "signal": "FALL", "title": "Turns Retrograde", "desc": "Trend reversal. Growth stalls, panic selling or violent unpredictable corrections expected."})
        elif not curr_data.get("is_retro") and prev_data.get("is_retro"):
            forecast_events.append({"date": target, "signal": "RISE", "title": "Turns Direct", "desc": "Bearish pressure lifts. Asset resumes primary upward momentum. Excellent entry point."})
            
        # 3. Combustion Shifts (Burnout)
        if curr_data.get("is_combust") and not prev_data.get("is_combust"):
            forecast_events.append({"date": target, "signal": "FALL", "title": "Enters Combustion (Asta)", "desc": "Asset momentum burns out. Over-regulation, liquidity drain, or loss of market interest."})
        elif not curr_data.get("is_combust") and prev_data.get("is_combust"):
            forecast_events.append({"date": target, "signal": "RISE", "title": "Exits Combustion", "desc": "Asset escapes pressure zone. Recovery rally initiates."})
            
    return forecast_events
# =====================================================================
# 4. VIEW CONTROLLERS & MASTER INTERFACE
# =====================================================================
st.sidebar.title("Astro-Finance Engine")

# Dynamic Date Input (50 Years Back to 50 Years Forward)
default_date = datetime.date(2026, 5, 23)
min_date = default_date - timedelta(days=365*50)
max_date = default_date + timedelta(days=365*50)

selected_date = st.sidebar.date_input("Master Temporal Anchor", value=default_date, min_value=min_date, max_value=max_date)

view_mode = st.sidebar.radio("Execution Dashboard", [
    "Advance Sector Forecast (Rise/Fall Predictor)", 
    "Daily Intraday Confluence",
    "Macro Yearly View"
])

st.sidebar.markdown("---")
st.sidebar.caption("Calculations powered by PySwissEph (Lahiri Chitrapaksha Ayanamsa)")

# ---------------------------------------------------------
# TAB 1: ADVANCE SECTOR FORECAST (The Core Predictive Goal)
# ---------------------------------------------------------
if view_mode == "Advance Sector Forecast (Rise/Fall Predictor)":
    st.header("🔭 Advance Asset Predictive Oracle")
    st.markdown("Search for any specific sector, commodity, or crypto. The Oracle will scan the future and predict exact dates for market **Rises (Breakouts)** and **Falls (Crashes)** based on planetary cycles.")
    
    # Asset Categorization Toggle
    asset_category = st.radio("Select Asset Class", ["Equities & Sectors", "Commodities", "Cryptocurrencies"], horizontal=True)
    
    # Dynamic Search Dictionary Mapping
    if asset_category == "Equities & Sectors":
        db, icon = EQUITY_SECTORS, "🏢"
    elif asset_category == "Commodities":
        db, icon = COMMODITIES, "🛢️"
    else:
        db, icon = CRYPTOCURRENCIES, "₿"
        
    # Searchable Selectbox
    selected_asset = st.selectbox(f"Search {asset_category}", options=sorted(list(db.keys())))
    ruling_planet = db[selected_asset]
    
    st.markdown(f"### {icon} {selected_asset} is governed by **{ruling_planet}**")
    
    # Forecasting Horizon
    lookahead_days = st.slider("Forecast Horizon (Days from Anchor Date)", min_value=30, max_value=365, value=90, step=30)
    
    if st.button("Generate Advance Forecast", type="primary"):
        with st.spinner(f"Simulating orbital mechanics for {ruling_planet} over the next {lookahead_days} days..."):
            forecast = get_advance_forecast(ruling_planet, selected_date, days=lookahead_days)
            
        if not forecast:
            st.info(f"No major structural shifts (Retrograde, Combustion, or Exaltation/Debilitation) detected for {selected_asset} in the next {lookahead_days} days. Expect continuation of current trends.")
        else:
            st.success(f"Future Timeline Generated: {len(forecast)} Major Inflection Points Detected.")
            
            for event in forecast:
                # Dynamic Styling based on Signal
                if event['signal'] == "RISE":
                    css_class = "forecast-card rise-signal"
                    text_class = "text-rise"
                    icon_sig = "🚀 EXPECTED RISE"
                elif event['signal'] == "FALL":
                    css_class = "forecast-card fall-signal"
                    text_class = "text-fall"
                    icon_sig = "🩸 EXPECTED FALL"
                else:
                    css_class = "forecast-card volatility-signal"
                    text_class = "text-warn"
                    icon_sig = "⚡ EXTREME VOLATILITY"
                    
                formatted_date = event['date'].strftime("%d %b %Y")
                
                st.markdown(f"""
                <div class="{css_class}">
                    <div class="date-badge">
                        <div style="font-size: 1.2em;">{formatted_date}</div>
                        <div class="{text_class}" style="font-size: 0.8em; margin-top: 5px;">{icon_sig}</div>
                    </div>
                    <div>
                        <h4 style="margin: 0 0 5px 0;">{event['title']}</h4>
                        <p style="margin: 0; color: #8b949e;">{event['desc']}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 2: DAILY INTRADAY CONFLUENCE
# ---------------------------------------------------------
elif view_mode == "Daily Intraday Confluence":
    st.header(f"⚡ Intraday Intelligence Matrix: {selected_date.strftime('%d %B %Y')}")
    
    ephem_data = get_ephemeris(selected_date.year, selected_date.month, selected_date.day)
    
    cols = st.columns(4)
    col_idx = 0
    for p_name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"]:
        data = ephem_data[p_name]
        with cols[col_idx % 4]:
            state = "🔄 Retro" if data.get('is_retro') else "➡️ Direct"
            if p_name in ["Sun", "Moon"]: state = "➡️ Direct"
            if p_name in ["Rahu", "Ketu"]: state = "🔄 Retro"
            
            combust_badge = "🔥 Combust" if data.get('is_combust') else ""
            
            st.markdown(f"""
            <div style="background: #161b22; padding: 10px; border-radius: 5px; border: 1px solid #30363d; margin-bottom: 10px;">
                <h4 style="margin:0; color:#d4af37;">{p_name}</h4>
                <div style="font-size: 0.9em;">Sign: {data['sign_name']} ({data['lon']%30:.1f}°)</div>
                <div style="font-size: 0.8em; color: #8b949e;">{state} {combust_badge}</div>
            </div>
            """, unsafe_allow_html=True)
        col_idx += 1
        
    st.markdown("---")
    st.markdown("### Broad Asset Class Day-Trading Posture")
    st.info("Use the **Advance Sector Forecast** tab to search specific micro-sectors. Below is the macro daily posture.")

# ---------------------------------------------------------
# TAB 3: MACRO YEARLY VIEW
# ---------------------------------------------------------
elif view_mode == "Macro Yearly View":
    st.header(f"🦅 Macro Strategic Posture: {selected_date.year}")
    st.markdown("Tracking foundational slow-moving planetary shifts for long-term portfolio restructuring.")
    
    data_points = get_ephemeris(selected_date.year, selected_date.month, 1)
    
    for p_name in ["Jupiter", "Saturn", "Rahu"]:
        p_data = data_points[p_name]
        
        if p_name == "Jupiter": title, focus = "Banking & Wealth Flow", "Financials, NBFCs, Agro"
        elif p_name == "Saturn": title, focus = "Structural & Energy Markets", "Oil, Gas, Mining, Heavy Metals"
        else: title, focus = "Disruptive Tech & Speculation", "AI, Crypto, Biotech"
            
        st.markdown(f"""
        <div style="background: #161b22; border-left: 5px solid #58a6ff; padding: 15px; margin-bottom: 15px; border-radius: 4px;">
            <h3 style="margin:0 0 5px 0;">{p_name} in {p_data['sign_name']} — {title}</h3>
            <p style="margin:0;"><strong>Macro Sectors Impacted:</strong> {focus}</p>
        </div>
        """, unsafe_allow_html=True)
