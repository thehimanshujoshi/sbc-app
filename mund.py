import streamlit as st
import pandas as pd
import datetime
import calendar
import swisseph as swe

# ==========================================
# 1. PAGE CONFIGURATION & CUSTOM UI STYLING
# ==========================================
st.set_page_config(
    page_title="Astro-Finance Oracle | SBC Engine",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium CSS Styling
st.markdown("""
<style>
    .main {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    h1, h2, h3 {
        color: #d4af37 !important; /* Premium Gold */
        font-family: 'Helvetica Neue', sans-serif;
    }
    .event-card {
        background-color: #161b22;
        border-left: 5px solid #d4af37;
        padding: 15px;
        margin-bottom: 15px;
        border-radius: 5px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .bullish { color: #2ea043; font-weight: bold; }
    .bearish { color: #f85149; font-weight: bold; }
    .volatile { color: #ffa657; font-weight: bold; }
    .western { border-left: 5px solid #58a6ff; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. ASTROLOGICAL & FINANCIAL CONSTANTS
# ==========================================
# Map PySwissEph planet IDs to Names
PLANETS = {
    swe.SUN: "Sun", swe.MOON: "Moon", swe.MARS: "Mars", 
    swe.MERCURY: "Mercury", swe.JUPITER: "Jupiter", 
    swe.VENUS: "Venus", swe.SATURN: "Saturn", 
    swe.TRUE_NODE: "Rahu" # Ketu is exactly 180 degrees opposite to True Node
}

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Financial Sectors per Planet
FINANCE_SECTORS = {
    "Sun": "PSUs, Govt Bonds, Power, Gold",
    "Moon": "FMCG, Dairy, Retail Sentiment, Liquids",
    "Mars": "Defence, Real Estate, Infra, Copper",
    "Mercury": "IT, Banking, Telecom, E-commerce",
    "Jupiter": "NBFCs, Large-cap Banks, Financial Services",
    "Venus": "Auto, Luxury, Media, Sugar",
    "Saturn": "Oil & Gas, Steel, Heavy Metals, Mining",
    "Rahu": "Aviation, AI, Tech Startups, Crypto",
    "Ketu": "Pharma R&D, Auditing, Deep Tech"
}

# Vedic Dignities (Simplified Index: 0=Aries, 1=Taurus, etc.)
EXALTED = {"Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5, "Jupiter": 3, "Venus": 11, "Saturn": 6, "Rahu": 1, "Ketu": 7}
DEBILITATED = {"Sun": 6, "Moon": 7, "Mars": 3, "Mercury": 11, "Jupiter": 9, "Venus": 5, "Saturn": 0, "Rahu": 7, "Ketu": 1}

# ==========================================
# 3. CORE CALCULATION ENGINE
# ==========================================
@st.cache_data(ttl=3600)
def get_planetary_data(year, month, day):
    """Calculates sidereal (Lahiri) planetary positions for a given date at 00:00 UTC."""
    # Set Sidereal Mode to Lahiri (Chitrapaksha)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    
    # Calculate Julian Day
    jd = swe.julday(year, month, day, 0.0)
    
    # FLG_SIDEREAL gets Vedic positions, FLG_SPEED gets velocity for retrogradation
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    
    data = {}
    for p_id, p_name in PLANETS.items():
        pos, ret = swe.calc_ut(jd, p_id, flags)
        lon = pos[0] # Longitude
        speed = pos[3] # Speed in deg/day
        
        sign_idx = int(lon / 30)
        deg_in_sign = lon % 30
        
        is_retrograde = speed < 0 and p_id not in [swe.SUN, swe.MOON, swe.TRUE_NODE]
        
        data[p_name] = {
            "lon": lon,
            "sign": sign_idx,
            "sign_name": ZODIAC_SIGNS[sign_idx],
            "deg": deg_in_sign,
            "speed": speed,
            "is_retro": is_retrograde
        }
        
    # Calculate Ketu manually (180 degrees from Rahu)
    rahu_lon = data["Rahu"]["lon"]
    ketu_lon = (rahu_lon + 180) % 360
    ketu_sign = int(ketu_lon / 30)
    data["Ketu"] = {
        "lon": ketu_lon,
        "sign": ketu_sign,
        "sign_name": ZODIAC_SIGNS[ketu_sign],
        "deg": ketu_lon % 30,
        "speed": data["Rahu"]["speed"],
        "is_retro": True
    }
    
    return data

def check_combustion(planet_lon, sun_lon, threshold=8):
    """Check if a planet is too close to the Sun."""
    diff = abs(planet_lon - sun_lon)
    if diff > 180: diff = 360 - diff
    return diff <= threshold

def get_western_aspects(p1_lon, p2_lon, orb=2):
    """Calculate standard Western financial aspects."""
    diff = abs(p1_lon - p2_lon)
    if diff > 180: diff = 360 - diff
    
    if abs(diff - 0) <= orb: return "Conjunction"
    if abs(diff - 90) <= orb: return "Square (Tension/Volatility)"
    if abs(diff - 120) <= orb: return "Trine (Liquidity/Growth)"
    if abs(diff - 180) <= orb: return "Opposition (Reversal/Climax)"
    return None

# ==========================================
# 4. APP INTERFACE & LOGIC
# ==========================================
st.title("Astro-Finance Predictive Engine")
st.markdown("### Powered by Sarvatobhadra Chakra & Lahiri Ayanamsa")

# Sidebar Controls
st.sidebar.header("Temporal Controls")
today = datetime.date.today()
selected_year = st.sidebar.selectbox("Select Year", range(2020, 2035), index=(today.year - 2020))
selected_month = st.sidebar.selectbox("Select Month", range(1, 13), index=(today.month - 1), format_func=lambda x: calendar.month_name[x])

st.sidebar.markdown("---")
st.sidebar.info("**Financial Mappings Loaded:**\n"
                "- Mars: Defence/Metals\n"
                "- Jupiter: Banks/NBFCs\n"
                "- Mercury: IT/Telecom\n"
                "- Venus: Auto/Luxury")

# Data Aggregation for the Month
num_days = calendar.monthrange(selected_year, selected_month)[1]
monthly_events = []

with st.spinner("Calculating Planetary Ephemeris..."):
    for day in range(1, num_days + 1):
        date_str = f"{selected_year}-{selected_month:02d}-{day:02d}"
        
        # Get data for today and yesterday to find transits/changes
        curr_data = get_planetary_data(selected_year, selected_month, day)
        
        if day > 1:
            prev_data = get_planetary_data(selected_year, selected_month, day - 1)
        else:
            # Handle month rollover for day 1
            prev_month = 12 if selected_month == 1 else selected_month - 1
            prev_year = selected_year - 1 if selected_month == 1 else selected_year
            prev_days = calendar.monthrange(prev_year, prev_month)[1]
            prev_data = get_planetary_data(prev_year, prev_month, prev_days)

        # 1. Vedic Transits (Sankranti/Gochar)
        for p in curr_data.keys():
            if curr_data[p]["sign"] != prev_data[p]["sign"]:
                event_type = f"{p} enters {curr_data[p]['sign_name']}"
                
                # Exaltation / Debilitation logic
                dignity_str = ""
                trend = "volatile"
                if EXALTED.get(p) == curr_data[p]["sign"]:
                    dignity_str = " -> EXALTED"
                    trend = "bullish"
                elif DEBILITATED.get(p) == curr_data[p]["sign"]:
                    dignity_str = " -> DEBILITATED"
                    trend = "bearish"
                    
                desc = f"Institutional capital rotates regarding {FINANCE_SECTORS.get(p, 'Broader Market')}. {dignity_str}"
                monthly_events.append({"date": date_str, "type": "Transit", "event": event_type, "desc": desc, "trend": trend})
            
            # Retrograde shifts
            if p not in ["Sun", "Moon", "Rahu", "Ketu"]:
                if curr_data[p]["is_retro"] and not prev_data[p]["is_retro"]:
                    monthly_events.append({"date": date_str, "type": "State Change", "event": f"{p} turns Retrograde", "desc": f"Unexpected reversals in {FINANCE_SECTORS[p]}. Highly unpredictable.", "trend": "volatile"})
                elif not curr_data[p]["is_retro"] and prev_data[p]["is_retro"]:
                    monthly_events.append({"date": date_str, "type": "State Change", "event": f"{p} turns Direct", "desc": f"Structural momentum resumes for {FINANCE_SECTORS[p]}.", "trend": "bullish"})

        # 2. Lunar Phases (Poornima/Amavasya)
        sun_lon = curr_data["Sun"]["lon"]
        moon_lon = curr_data["Moon"]["lon"]
        lunar_phase = abs(sun_lon - moon_lon)
        if lunar_phase < 5:
            monthly_events.append({"date": date_str, "type": "Lunar", "event": "Amavasya (New Moon)", "desc": "Market reset. Potential accumulation phase.", "trend": "volatile"})
        elif abs(lunar_phase - 180) < 5:
            monthly_events.append({"date": date_str, "type": "Lunar", "event": "Poornima (Full Moon)", "desc": "Peak liquidity and emotional exhaustion. Possible profit booking.", "trend": "bearish"})

        # 3. Combustion Check
        for p in ["Mars", "Mercury", "Jupiter", "Venus", "Saturn"]:
            is_combust_now = check_combustion(curr_data[p]["lon"], sun_lon)
            was_combust = check_combustion(prev_data[p]["lon"], prev_data["Sun"]["lon"])
            if is_combust_now and not was_combust:
                monthly_events.append({"date": date_str, "type": "Combustion", "event": f"{p} enters Combustion (Asta)", "desc": f"Momentum burnout for {FINANCE_SECTORS[p]}. Regulatory pressure.", "trend": "bearish"})
                
        # 4. Western Aspects (Financial Astrology)
        # Checking just a few heavy hitters for financial markets
        aspect = get_western_aspects(curr_data["Jupiter"]["lon"], curr_data["Saturn"]["lon"])
        if aspect and aspect != get_western_aspects(prev_data["Jupiter"]["lon"], prev_data["Saturn"]["lon"]):
            monthly_events.append({"date": date_str, "type": "Western", "event": f"Jupiter {aspect} Saturn", "desc": "Major macro-economic shift. Clash between growth (Banks) and value (Metals/Oil).", "trend": "volatile"})

# ==========================================
# 5. UI DISPLAY
# ==========================================
st.markdown(f"## Financial Astro-Events for {calendar.month_name[selected_month]} {selected_year}")

if not monthly_events:
    st.success("No major planetary transits, retrograde shifts, or critical alignments detected for this month.")
else:
    # Group events by date
    df_events = pd.DataFrame(monthly_events)
    grouped = df_events.groupby("date")
    
    for date, group in grouped:
        st.markdown(f"### 📅 {date}")
        for _, row in group.iterrows():
            css_class = "event-card"
            if row['type'] == "Western":
                css_class += " western"
                
            trend_class = row['trend']
            trend_symbol = "📈" if trend_class == "bullish" else "📉" if trend_class == "bearish" else "⚠️"
            
            st.markdown(f"""
            <div class="{css_class}">
                <h4 style="margin-top:0;">{trend_symbol} {row['event']} <span style="font-size:12px; color:#8b949e; float:right;">[{row['type']}]</span></h4>
                <p style="margin-bottom:0;"><span class="{trend_class}">Impact:</span> {row['desc']}</p>
            </div>
            """, unsafe_allow_html=True)

# Add a snapshot of current positions at the end of the month
st.markdown("---")
st.markdown(f"### End of Month Ephemeris Snapshot ({calendar.month_name[selected_month]} {num_days})")
end_data = get_planetary_data(selected_year, selected_month, num_days)

display_data = []
for p, data in end_data.items():
    state = "Retrograde" if data['is_retro'] else "Direct"
    if p in ["Sun", "Moon", "Rahu", "Ketu"]: state = "-"
    
    display_data.append({
        "Planet": p,
        "Sign (Lahiri)": data['sign_name'],
        "Degrees": f"{data['deg']:.2f}°",
        "Motion": state,
        "Governs": FINANCE_SECTORS.get(p, "-")
    })

st.dataframe(pd.DataFrame(display_data), use_container_width=True)
