### 📋 PART 1: Core Engine, Mathematical Ephemeris, and Data Infrastructure

```python
import streamlit as st
import pandas as pd
import datetime
import calendar
import swisseph as swe

# =====================================================================
# 1. APPLICATION SETUP & CUSTOM USER EXPERIENCE STYLING
# =====================================================================
st.set_page_config(
    page_title="Institutional Astro-Finance Intelligence Platform",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Contrast Financial Dashboard CSS Styling
st.markdown("""
<style>
    .main { background-color: #0b0f19; color: #f0f6fc; }
    h1, h2, h3, h4 { font-family: 'Inter', sans-serif; font-weight: 700; }
    .metric-container { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; margin-bottom: 20px; }
    
    /* Strict Trading & Investing Signal Classes */
    .bull-run { background: rgba(46, 160, 67, 0.15); border-left: 6px solid #2ea043; padding: 15px; border-radius: 4px; margin: 12px 0; }
    .market-crash { background: rgba(248, 81, 73, 0.15); border-left: 6px solid #f85149; padding: 15px; border-radius: 4px; margin: 12px 0; }
    .neutral-accumulation { background: rgba(56, 139, 253, 0.15); border-left: 6px solid #388bfd; padding: 15px; border-radius: 4px; margin: 12px 0; }
    .high-volatility { background: rgba(212, 175, 55, 0.15); border-left: 6px solid #d4af37; padding: 15px; border-radius: 4px; margin: 12px 0; }
    
    .text-bull { color: #56d364; font-weight: bold; }
    .text-bear { color: #ff7b72; font-weight: bold; }
    .text-warn { color: #e3b341; font-weight: bold; }
    .text-info { color: #79c0ff; font-weight: bold; }
    
    .panchang-box { background: #0d1117; border: 1px dashed #30363d; padding: 12px; border-radius: 6px; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. DEFINITIVE SECTOR, COMMODITY, AND CRYPTOCURRENCY ASTRO MAPPINGS
# =====================================================================
PLANETS = {
    swe.SUN: "Sun", swe.MARS: "Mars", swe.MERCURY: "Mercury", 
    swe.JUPITER: "Jupiter", swe.VENUS: "Venus", swe.SATURN: "Saturn", 
    swe.TRUE_NODE: "Rahu" # Ketu is solved geometrically 180° opposite
}

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# High-Precision Asset Class, Commodities, and Crypto Mappings
FINANCE_SECTORS = {
    "Sun": {"equity": "PSUs, Top-Tier Monopolies, Sovereign Bonds", "commodity": "Physical Gold Bullion", "crypto": "Central Bank Digital Currencies (CBDCs)"},
    "Mars": {"equity": "Defence Manufacturing, Aerospace, Real Estate, Heavy Infrastructure", "commodity": "Industrial Copper, Scrap Metals, Weapons Supply", "crypto": "High-Throughput Utility Tokens"},
    "Mercury": {"equity": "Information Technology, Tech Hardware, Telecom Networks, E-Commerce, FinTech", "commodity": "Paper Markets, Freight Logistics Pricing", "crypto": "Smart Contract Platforms, Interoperability Protocols"},
    "Jupiter": {"equity": "Banking, Tier-1 NBFCs, Mutual Funds, Large-Cap Financial Services", "commodity": "Agricultural Commodities (Wheat, Corn)", "crypto": "Major Institutional Assets (Wrapped Core Tokens)"},
    "Venus": {"equity": "Automobile Manufacturers, Luxury Brands, Media & Entertainment, Premium Textiles", "commodity": "Refined Sugar, Silver Spot Markets", "crypto": "Consumer dApps, NFT Markets, Gaming Infrastructure"},
    "Saturn": {"equity": "Oil Exploration, Natural Gas Distribution, Thermal Coal Mining, Steel Mills, Heavy Machinery", "commodity": "Crude Oil Brent/WTI, Iron Ore, Coking Coal", "crypto": "Proof-of-Work Legacy Networks, Utility Privacy Tokens"},
    "Rahu": {"equity": "Artificial Intelligence, Quantum Computing Startups, Biotechnology, Electric Vehicles", "commodity": "Unconventional Energy, Rare Earth Elements", "crypto": "Bitcoin (Speculative Flagship), High-Beta Memecoins, Synthetic Derivatives"},
    "Ketu": {"equity": "Pharmaceuticals R&D, Cybersecurity Architecture, Data Forensics, Corporate Auditing", "commodity": "Chemical Compounds, Medical Isotope Supplies", "crypto": "Anonymity Protocols, Decentralized Storage Solutions"}
}

# Vedic Astrology Planetary Alignment Matrix Indices
EXALTED = {"Sun": 0, "Mars": 9, "Mercury": 5, "Jupiter": 3, "Venus": 11, "Saturn": 6, "Rahu": 1, "Ketu": 7}
DEBILITATED = {"Sun": 6, "Mars": 3, "Mercury": 11, "Jupiter": 9, "Venus": 5, "Saturn": 0, "Rahu": 7, "Ketu": 1}

# =====================================================================
# 3. HIGH-PRECISION SWISS EPHEMERIS MATHEMATICAL ENGINE
# =====================================================================
@st.cache_data(ttl=3600)
def calculate_sidereal_ephemeris(year, month, day):
    """Calculates ultra-precise sidereal (Lahiri Chitrapaksha) planetary coordinates."""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(year, month, day, 12.0) # Evaluated at 12:00 PM noon standard base coordinate
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    
    positions = {}
    for p_id, p_name in PLANETS.items():
        pos, _ = swe.calc_ut(jd, p_id, flags)
        lon = pos[0]
        speed = pos[3]
        sign_idx = int(lon / 30)
        
        positions[p_name] = {
            "lon": lon,
            "sign_idx": sign_idx,
            "sign_name": ZODIAC_SIGNS[sign_idx],
            "deg": lon % 30,
            "is_retro": speed < 0 and p_id not in [swe.SUN, swe.TRUE_NODE]
        }
        
    # Manual execution of geometric nodes for accurate Ketu coordination
    rahu_lon = positions["Rahu"]["lon"]
    ketu_lon = (rahu_lon + 180) % 360
    ketu_sign = int(ketu_lon / 30)
    positions["Ketu"] = {
        "lon": ketu_lon,
        "sign_idx": ketu_sign,
        "sign_name": ZODIAC_SIGNS[ketu_sign],
        "deg": ketu_lon % 30,
        "is_retro": True # Ketu systematically mimics Rahu's backward velocity
    }
    return positions

@st.cache_data(ttl=3600)
def calculate_tropical_ephemeris(year, month, day):
    """Calculates Western Tropical longitudes for Western confluence metrics."""
    jd = swe.julday(year, month, day, 12.0)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    tropical = {}
    for p_id, p_name in PLANETS.items():
        pos, _ = swe.calc_ut(jd, p_id, flags)
        tropical[p_name] = pos[0]
    return tropical

def evaluate_vedha_intersections(p1_name, p1_sign, p2_name, p2_sign, p1_retro, p2_combust):
    """SBC Algorithmic Interpretation Matrix engine."""
    p1_malefic = p1_name in ["Mars", "Saturn", "Rahu", "Ketu"]
    
    if p1_retro and p1_malefic:
        return "MARKET CRASH / FLUID PANIC", f"The aggressive retrograde status of {p1_name} exerts an intense, negative cross-axis Vedha onto {p2_name}. Major risk off liquidation.", "market-crash"
    elif p1_malefic:
        return "BEARISH REVERSAL / PRESSURE", f"Malefic alignment detected via transiting {p1_name} striking {p2_name}. Operating margins are projected to encounter localized policy or structural headwinds.", "market-crash"
    elif p1_name == "Jupiter" and not p2_combust:
        return "EUPHORIC BULL RUN", f"Benefic expansion wave as Jupiter throws a supportive alignment onto {p2_name}. Institutional FII velocity is aggressively positive.", "bull-run"
    else:
        return "STABLE ACCUMULATION PHASE", f"Standard energetic configuration between {p1_name} and {p2_name}. Accumulate on index pullbacks.", "neutral-accumulation"

def compute_panchang_parameters(year, month, day):
    """Calculates authentic astronomical values for localized day-trading metrics."""
    jd = swe.julday(year, month, day, 5.5 / 24.0) # Calculated at sunrise standard calibration
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    
    sun_pos, _ = swe.calc_ut(jd, swe.SUN, flags)
    moon_pos, _ = swe.calc_ut(jd, swe.MOON, flags)
    
    sun_lon, moon_lon = sun_pos[0], moon_pos[0]
    
    # Authentic Tithi Calculation (12-degree elongation slices)
    elongation = (moon_lon - sun_lon) % 360
    tithi_num = int(elongation / 12) + 1
    tithi_name = f"Tithi {tithi_num}" if tithi_num <= 15 else f"Krishna Tithi {tithi_num - 15}"
    if tithi_num == 15: tithi_name = "Poornima (Full Moon Peak Liquidity)"
    if tithi_num == 30: tithi_name = "Amavasya (New Moon Multi-Asset Reset)"
    
    # Nakshatra Calculation (13°20' structural division segments)
    nak_num = int(moon_lon / (13 + 1/3)) + 1
    nak_names = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
    nak_name = nak_names[min(nak_num - 1, 26)]
    
    return tithi_name, nak_name, elongation
# =====================================================================
# 4. VIEW CONTROLLERS AND LOGICAL INTERFACE ROUTINES
# =====================================================================
st.sidebar.title("Configuration Center")
view_mode = st.sidebar.radio("Analysis Horizon Selection", ["Long-Term Investor (Macro Yearly View)", "Intraday & Swing Trader (Micro Date View)"])

current_date = datetime.date.today()
analysis_year = st.sidebar.selectbox("Calendar Tracking Horizon", range(2025, 2035), index=(2026 - 2025))

# Parse and process states based on user horizontal timeframe selection
if view_mode == "Long-Term Investor (Macro Yearly View)":
    st.header(f"🦅 Macro-Financial Astrological Matrix Forecast Portfolio — Year {analysis_year}")
    st.markdown("#### Excludes volatile Lunar variables to establish clean, macro long-term strategic structural trends.")
    
    # Process sequential snapshots across the yearly timeframe
    months_to_track = [1, 4, 7, 10] # Quarterly tracking parameters
    quarters = ["Q1 Opening Trends", "Q2 Operational Shifts", "Q3 Macro Re-alignment", "Q4 Year-End Ingress Matrix"]
    
    for m_idx, month in enumerate(months_to_track):
        st.markdown(f"## 📊 Phase Matrix: {quarters[m_idx]} (Data Point: 1st of {calendar.month_name[month]})")
        data_points = calculate_sidereal_ephemeris(analysis_year, month, 1)
        sun_lon = data_points["Sun"]["lon"]
        
        cols = st.columns(3)
        col_selector = 0
        
        for p_name in ["Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
            p_data = data_points[p_name]
            is_combust = abs(p_data["lon"] - sun_lon) < 10 if p_name not in ["Rahu", "Ketu"] else False
            
            # Algorithmic interpretation logic mapping to structural portfolio text
            dignity = "Neutral"
            trend_class = "neutral-accumulation"
            title_signal = "STRATEGIC HOLD / ACCUMULATE"
            
            if EXALTED[p_name] == p_data["sign_idx"]:
                dignity = "EXALTED (Peak Fundamental Outperformance)"
                trend_class = "bull-run"
                title_signal = "STRONG AGGRESSIVE ACCUMULATION / RALLY"
            elif DEBILITATED[p_name] == p_data["sign_idx"]:
                dignity = "DEBILITATED (High Capital Risk/Structural Bleeding)"
                trend_class = "market-crash"
                title_signal = "HIGH CAPITAL RISK / COMPRESSION / DISRUPT"
                
            if p_data["is_retro"]:
                dignity += " [RETROGRADE - High Velocity Dynamic Alteration]"
                if trend_class != "market-crash": trend_class = "high-volatility"
                
            with cols[col_selector]:
                st.markdown(f"""
                <div class="{trend_class}">
                    <h4 style='margin:0 0 8px 0;'>{p_name} in {p_data['sign_name']}</h4>
                    <strong>Signal Matrix:</strong> {title_signal}<br>
                    <strong>Dignity State:</strong> {dignity}<br>
                    <hr style='border:0; border-top:1px solid rgba(255,255,255,0.1); margin:8px 0;'>
                    <strong>Core Equity Vector:</strong> {FINANCE_SECTORS[p_name]['equity']}<br>
                    <strong>Commodity Baseline:</strong> {FINANCE_SECTORS[p_name]['commodity']}<br>
                    <strong>Cryptocurrency Core:</strong> {FINANCE_SECTORS[p_name]['crypto']}
                </div>
                """, unsafe_allow_html=True)
            
            col_selector = (col_selector + 1) % 3

else:
    st.header("⚡ Intraday & Swing Sector Intelligence Confluence Matrix")
    target_date = st.date_input("Target Trading Execution Date Selection", current_date)
    
    # Process high-precision structural tracking logs for the specific date
    y, m, d = target_date.year, target_date.month, target_date.day
    sidereal_snapshot = calculate_sidereal_ephemeris(y, m, d)
    tropical_snapshot = calculate_tropical_ephemeris(y, m, d)
    tithi, nakshatra, moon_elongation = compute_panchang_parameters(y, m, d)
    
    # Render localized Panchang data framework
    st.markdown("### 🏛️ Real-Time Auspicious Technical Day-Trading Constraints (Panchang Confluence)")
    p_col1, p_col2, p_col3 = st.columns(3)
    with p_col1:
        st.metric("Lunar Tithi Variable", tithi)
    with p_col2:
        st.metric("Active Nakshatra Node", nakshatra)
    with p_col3:
        # Determine sentiment via moon distance rules
        sentiment = "High Liquidity Distribution" if moon_elongation > 180 else "Subdued Accumulation Drive"
        st.metric("Volume/Velocity Baseline Context", sentiment)
        
    st.markdown("---")
    st.markdown("### 🏹 Active Strategic Alignment and Sector Projections")
    
    # Compute active cross-axis interactions
    sun_lon = sidereal_snapshot["Sun"]["lon"]
    
    for main_p in ["Mars", "Mercury", "Jupiter", "Venus", "Saturn"]:
        main_data = sidereal_snapshot[main_p]
        is_combust = abs(main_data["lon"] - sun_lon) < 12
        
        # Check if heavy outer planets cast a cross alignment
        trigger_p = "Saturn" if main_p != "Saturn" else "Mars"
        trigger_data = sidereal_snapshot[trigger_p]
        
        sig_title, desc_text, styling = evaluate_vedha_intersections(
            trigger_p, trigger_data["sign_idx"], main_p, main_data["sign_idx"],
            trigger_data["is_retro"], is_combust
        )
        
        # Compute concurrent Western financial technical indicators
        western_notes = "No major geometric aspect currently active."
        w_diff = abs(tropical_snapshot[main_p] - tropical_snapshot[trigger_p])
        if w_diff > 180: w_diff = 360 - w_diff
        if abs(w_diff - 90) < 5:
            western_notes = f"WARNING: Western Geo-Square active with {trigger_p}. Volatility spike predicted."
        elif abs(w_diff - 120) < 5:
            western_notes = f"BULLISH CONFLUENCE: Western Geo-Trine active with {trigger_p}. Enhanced institutional alpha flow."
            
        st.markdown(f"""
        <div class="{styling}">
            <h3 style='margin:0 0 5px 0; color:inherit;'>Sector Node: {main_p} Governance Matrix</h3>
            <strong>Predicted Vector Target: {sig_title}</strong><br>
            <p style='margin:8px 0;'><strong>Vedic Alignment Insight:</strong> {desc_text}</p>
            <div class="panchang-box">
                <strong>Western Cross-Market Metric:</strong> {western_notes}<br>
                <strong>Impact Sectors:</strong> {FINANCE_SECTORS[main_p]['equity']} | 
                <strong>Commodities:</strong> {FINANCE_SECTORS[main_p]['commodity']} | 
                <strong>Crypto Context:</strong> {FINANCE_SECTORS[main_p]['crypto']}
            </div>
        </div>
        """, unsafe_allow_html=True)

# =====================================================================
# 6. COMPREHENSIVE RISK MANAGEMENT POLICY DECREE
# =====================================================================
st.markdown("---")
st.markdown("""
<div style="background-color: #161b22; padding: 20px; border-radius: 8px; border: 1px solid #30363d; font-size:12px; color: #8b949e; text-align: justify;">
    <strong>PROPRIETARY DATA INTEL PROTOCOL & RISK DISCLAIMER:</strong> This analytical interface serves purely as an automated, confluenced time-series projection model aggregating calculations mapped from Swiss Ephemeris data alongside traditional multi-axis planetary tracking formulas. Under no circumstances does this predictive model represent financial, legal, execution-grade investment, or market-timing advice. Astrological alignment vectors serve as mathematical filters to isolate cyclical institutional investor sentiment trends and do not override systemic liquidity factors, macro-economic rate adjustments, or physical company ledger statements. Users execute short-term intraday margin trades or long-term portfolio asset deployments completely at their own risk. Position-sizing discipline remains mandatory across all regimes.
</div>
""", unsafe_allow_html=True)
