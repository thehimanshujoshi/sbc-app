import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta, datetime as dt
import calendar
import swisseph as swe

st.set_page_config(page_title="Alpha Astro-Finance Terminal", page_icon="🦅", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .main { background-color: #060911; color: #f0f6fc; }
    h1, h2, h3, h4 { color: #d4af37 !important; font-family: 'Inter', sans-serif; }
    .oracle-card { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 15px; }
    .grid-box { border: 1px solid #444; text-align: center; padding: 5px; font-size: 10px; background: #161b22; min-height: 55px; }
    .signal-rise { border-left: 6px solid #2ea043; background: rgba(46,160,67,0.1); }
    .signal-fall { border-left: 6px solid #f85149; background: rgba(248,81,73,0.1); }
    .signal-warn { border-left: 6px solid #ffa657; background: rgba(212,175,55,0.1); }
    .ist-badge { font-size: 11px; color: #8b949e; background: #21262d; padding: 2px 6px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

PLANETS = {swe.SUN: "Sun", swe.MARS: "Mars", swe.MERCURY: "Mercury", swe.JUPITER: "Jupiter", swe.VENUS: "Venus", swe.SATURN: "Saturn", swe.TRUE_NODE: "Rahu"}
ZODIAC_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]

EXALTED = {"Sun": 0, "Mars": 9, "Mercury": 5, "Jupiter": 3, "Venus": 11, "Saturn": 6, "Rahu": 1, "Ketu": 7}
DEBILITATED = {"Sun": 6, "Mars": 3, "Mercury": 11, "Jupiter": 9, "Venus": 5, "Saturn": 0, "Rahu": 7, "Ketu": 1}

EQUITY_SECTORS = {"NIFTY 50 / Broader Index": "Multi", "Public Sector Undertakings (PSUs)": "Sun", "Defence Manufacturing": "Mars", "Information Technology (IT)": "Mercury", "Banking & Financials": "Jupiter", "Automobile Manufacturing": "Venus", "Oil & Gas Exploration": "Saturn", "Artificial Intelligence & EVs": "Rahu", "Pharmaceuticals & Cyber": "Ketu"}
COMMODITIES = {"Gold Spot / Bullion": "Gold_Multi", "Crude Oil Brent/WTI": "Crude_Multi", "Silver Spot": "Venus", "Copper": "Mars"}
CRYPTOCURRENCIES = {"Bitcoin (BTC)": "Rahu", "Ethereum (ETH)": "Mercury", "Solana (SOL)": "Mercury", "Privacy Tokens": "Ketu"}

PHONETIC_DB = {'A': 0, 'CH': 0, 'L': 1, 'E': 2, 'VA': 3, 'VI': 3, 'VU': 3, 'VE': 3, 'VO': 3, 'KA': 4, 'KI': 4, 'KU': 4, 'KE': 4, 'KO': 4, 'G': 5, 'M': 9, 'TA': 10, 'TI': 10, 'PA': 12, 'PI': 12, 'PU': 12, 'PE': 12, 'PO': 12, 'R': 13, 'TH': 15, 'N': 21, 'Y': 22, 'BH': 24}

BACKTEST_SCENARIOS = {"2008 Lehman Brothers Crash": datetime.date(2008, 9, 15), "2020 COVID Market Crash": datetime.date(2020, 3, 23), "2000 Dot-Com Bubble Peak": datetime.date(2000, 3, 10), "2021 Bitcoin All-Time High Phase": datetime.date(2021, 11, 10)}

def get_ist_julian_day(date_obj):
    dt_str = f"{date_obj.strftime('%Y-%m-%d')} 09:30:00"
    utc_dt = dt.strptime(dt_str, "%Y-%m-%d %H:%M:%S") - timedelta(hours=5, minutes=30)
    return swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)

@st.cache_data(ttl=3600)
def compute_astro_metrics(date_obj):
    jd = get_ist_julian_day(date_obj)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    sid_flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    trop_flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    eq_flags = swe.FLG_SWIEPH | swe.FLG_EQUATORIAL
    
    metrics = {}
    sun_pos, _ = swe.calc_ut(jd, swe.SUN, sid_flags)
    sun_lon = sun_pos[0]
    sun_eq, _ = swe.calc_ut(jd, swe.SUN, eq_flags)
    metrics["Sun_Declination"] = sun_eq[1]
    
    for p_id, p_name in PLANETS.items():
        pos_s, _ = swe.calc_ut(jd, p_id, sid_flags)
        pos_t, _ = swe.calc_ut(jd, p_id, trop_flags)
        pos_e, _ = swe.calc_ut(jd, p_id, eq_flags)
        
        lon, lat, speed_lat = pos_s[0], pos_s[1], pos_s[4]
        sign_idx = int(lon / 30)
        nak_idx = int(lon / (13 + 1/3))
        
        is_combust = abs(lon - sun_lon) <= 10 if p_name != "Sun" else False
        if abs(lon - sun_lon) > 180: is_combust = (360 - abs(lon - sun_lon)) <= 10
        
        metrics[p_name] = {
            "lon": lon, "sign_idx": sign_idx, "sign_name": ZODIAC_SIGNS[sign_idx],
            "nak_idx": min(nak_idx, 26), "nak_name": NAKSHATRAS[min(nak_idx, 26)],
            "deg": lon % 30, "lat": lat, "speed_lat": speed_lat, "declination": pos_e[1],
            "is_retro": pos_s[3] < 0 and p_name not in ["Sun", "Rahu"], "is_combust": is_combust,
            "tropical_lon": pos_t[0]
        }
        
    r_data = metrics["Rahu"]
    k_lon = (r_data["lon"] + 180) % 360
    metrics["Ketu"] = {
        "lon": k_lon, "sign_idx": int(k_lon/30), "sign_name": ZODIAC_SIGNS[int(k_lon/30)],
        "nak_idx": min(int(k_lon/(13+1/3)), 26), "nak_name": NAKSHATRAS[min(int(k_lon/(13+1/3)), 26)],
        "deg": k_lon % 30, "lat": -r_data["lat"], "speed_lat": -r_data["speed_lat"], "declination": -r_data["declination"],
        "is_retro": True, "is_combust": False, "tropical_lon": (r_data["tropical_lon"] + 180) % 360
    }
    return metrics

def calculate_ashtakavarga(planet, sign_idx):
    base_score = 4
    if sign_idx in [0, 4, 8]: base_score += 2
    if sign_idx in [3, 7, 11]: base_score -= 1
    if planet == "Jupiter" and sign_idx == 3: base_score = 8
    return min(max(base_score, 1), 8)
def scan_future_boundaries(asset_name, mapping_id, anchor_date, horizon=90):
    events = []
    if mapping_id == "Multi" or asset_name == "NIFTY 50 / Broader Index": target_planets = ["Mars", "Venus"]
    elif mapping_id == "Gold_Multi": target_planets = ["Sun", "Jupiter", "Venus"]
    elif mapping_id == "Crude_Multi": target_planets = ["Mars", "Saturn"]
    else: target_planets = [mapping_id]
        
    for d in range(1, horizon + 1):
        t_date = anchor_date + timedelta(days=d)
        p_date = t_date - timedelta(days=1)
        t_metrics, p_metrics = compute_astro_metrics(t_date), compute_astro_metrics(p_date)
        
        for p in target_planets:
            tm, pm = t_metrics[p], p_metrics[p]
            
            if tm["sign_idx"] != pm["sign_idx"]:
                sig = "RISE" if tm["sign_idx"] == EXALTED.get(p) else "FALL" if tm["sign_idx"] == DEBILITATED.get(p) else "VOLATILE"
                events.append({"date": t_date, "signal": sig, "planet": p, "title": f"{p} Rashi Ingress -> {tm['sign_name']}", "desc": "Critical sector boundaries resetting. Historic trigger for gap ups/downs."})
                
            if tm["nak_idx"] != pm["nak_idx"]:
                events.append({"date": t_date, "signal": "VOLATILE", "planet": p, "title": f"{p} Nakshatra Transition -> {tm['nak_name']}", "desc": "Micro-level algorithmic adjustment date. Clean shift in momentum."})
                
            if pm["speed_lat"] < 0 and tm["speed_lat"] >= 0:
                events.append({"date": t_date, "signal": "RISE", "planet": p, "title": f"{p} Minimum Latitude Crossover", "desc": "Latitude hits absolute minimum and curves upward. Selling momentum exhausted."})
            elif pm["lat"] * tm["lat"] < 0:
                events.append({"date": t_date, "signal": "VOLATILE", "planet": p, "title": f"{p} Zero-Degree Latitude Crossing", "desc": "Equatorial plane trajectory crossing. Drastic liquidity realignment."})
                
    return events

anchor_2026 = datetime.date(2026, 5, 23)
min_allowed = anchor_2026 - timedelta(days=365*50)
max_allowed = anchor_2026 + timedelta(days=365*50)

st.sidebar.markdown("## Date Framework Parameters")
execution_date = st.sidebar.date_input("Select Base Analytical Date (IST)", value=anchor_2026, min_value=min_allowed, max_value=max_allowed)

view_selection = st.sidebar.radio("Execution Layer Workspace", ["Advance Forecasting & Asset Scanners", "Intraday Trader Dashboard", "Historical Backtesting Engine"])
metrics_now = compute_astro_metrics(execution_date)

if view_selection == "Advance Forecasting & Asset Scanners":
    st.title("🔭 Advance Horizon Multi-Asset Predictive Oracle")
    category = st.radio("Asset Repository Mode", ["Equities & Indexes", "Commodity Complex", "Cryptocurrencies"], horizontal=True)
    company_query = st.text_input("Corporate Phonetic Search Engine (Type Company Ticker Name e.g. TATA, RELIANCE)", "").upper()
    
    db = EQUITY_SECTORS if category == "Equities & Indexes" else COMMODITIES if category == "Commodity Complex" else CRYPTOCURRENCIES
    selected_asset = st.selectbox("Isolate Active Target Index", options=list(db.keys()))
    mapped_planet = db[selected_asset]
    
    if company_query:
        first_char = company_query[:2] if company_query[:2] in PHONETIC_DB else company_query[0] if company_query else 'A'
        target_nak_idx = PHONETIC_DB.get(first_char, 0)
        st.warning(f"🎯 Phonetic Matching Active: Target string '{company_query}' resolved to phonetic anchor Nakshatra: **{NAKSHATRAS[target_nak_idx]}**")
        
    horizon_days = st.slider("Target Forward Predictive Horizon Scope", 30, 180, 90, step=30)
    
    if st.button("Execute Predictive Scanning Engine", type="primary"):
        timeline = scan_future_boundaries(selected_asset, mapped_planet, execution_date, horizon=horizon_days)
        if not timeline:
            st.info("Smooth orbital integration without critical boundary re-allocations during this window.")
        else:
            for item in sorted(timeline, key=lambda x: x['date']):
                sig = item['signal']
                card_style = "oracle-card signal-rise" if sig == "RISE" else "oracle-card signal-fall" if sig == "FALL" else "oracle-card signal-warn"
                badge = "🟩 EXPECTED RISE / BULL RUN" if sig == "RISE" else "🟥 EXPECTED FALL / CRASH" if sig == "FALL" else "🟨 MOMENTUM INTERRUPT / VOLATILITY"
                
                st.markdown(f"""
                <div class="{card_style}">
                    <span class="ist-badge">Execution Date: {item['date'].strftime('%d %b %Y')} (IST)</span>
                    <h3 style='margin:10px 0 5px 0;'>{item['title']}</h3>
                    <strong>System Action: {badge}</strong>
                    <p style='margin-top:8px; color:#c9d1d9;'>{item['desc']} Governed via orbital calculations on <b>{item['planet']}</b>.</p>
                </div>
                """, unsafe_allow_html=True)

elif view_selection == "Intraday Trader Dashboard":
    st.title("⚡ High-Frequency Micro-Execution Intraday Confluence Ledger")
    st.markdown(f"### Current Global Solar Anomaly Index (Sun Declination: `{metrics_now['Sun_Declination']:.4f}°`)")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("#### Real-Time Ashtakavarga Multipliers")
        score_data = [{"Planet Node": p, "Ashtakavarga Score": f"{calculate_ashtakavarga(p, metrics_now[p]['sign_idx'])} / 8 Bindus"} for p in ["Sun", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]]
        st.table(pd.DataFrame(score_data))
        
    with col2:
        st.markdown("#### Graphical Sarvatobhadra Chakra Tactical Grid Mapping")
        grid_html = "<div style='display: grid; grid-template-columns: repeat(9, 1fr); gap: 4px; border:2px solid #d4af37; padding:10px; background:#060911;'>"
        for idx in range(81):
            cell_content = "🎯 Node Corner" if idx in [0, 8, 72, 80] else "🪐 Vedha Axis" if idx % 7 == 0 else ""
            for p_name, p_data in metrics_now.items():
                if p_name != "Sun_Declination" and (idx % 27) == p_data["nak_idx"]:
                    cell_content += f"<span style='color:#d4af37; font-weight:bold;'>[{p_name[:3]}]</span><br>"
            grid_html += f"<div class='grid-box'>{cell_content or '•'}</div>"
        grid_html += "</div>"
        st.markdown(grid_html, unsafe_allow_html=True)

else:
    st.title("🗄️ Institutional Backtesting Verification Engine")
    selected_scenario = st.selectbox("Select Historical Anchor Point Scenario", options=list(BACKTEST_SCENARIOS.keys()))
    historical_target = BACKTEST_SCENARIOS[selected_scenario]
    
    st.info(f"Setting analytical clock parameters to target scenario date: **{historical_target.strftime('%d %B %Y')} (IST Benchmark Open)**")
    hist_metrics = compute_astro_metrics(historical_target)
    
    hist_records = [{"Planet Node": p, "Sidereal Sign": hist_metrics[p]["sign_name"], "Nakshatra Node": hist_metrics[p]["nak_name"], "Latitude": f"{hist_metrics[p]['lat']:.4f}°", "Declination": f"{hist_metrics[p]['declination']:.4f}°", "Is Retrograde": hist_metrics[p]["is_retro"], "Is Combust": hist_metrics[p]["is_combust"]} for p in ["Sun", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]]
    st.dataframe(pd.DataFrame(hist_records), use_container_width=True)
