import streamlit as st
import pandas as pd
import datetime
import pytz
import math

# Try to load the professional Swiss Ephemeris library
try:
    import swisseph as swe
except ImportError:
    st.error("⚠️ The 'pyswisseph' library is missing. Please ensure you created the requirements.txt file on GitHub!")
    st.stop()

# --- Page Config ---
st.set_page_config(page_title="SBC Astro Engine", page_icon="🕉️", layout="wide")

# Set strict Lahiri Ayanamsa
swe.set_sid_mode(swe.SIDM_LAHIRI)

# --- 28 Nakshatra System (SBC uses Abhijit) ---
SBC_NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", 
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", 
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", 
    "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", 
    "Abhijit", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", 
    "Uttara Bhadrapada", "Revati"
]

# Planet IDs for Swisseph
PLANETS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, 
    "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, 
    "Venus": swe.VENUS, "Saturn": swe.SATURN, 
    "Rahu": swe.MEAN_NODE # Ketu is 180 degrees from Rahu
}

# SBC Alphabet Mapping (Simplified English Phonetics)
AKSHARA_MAP = {
    "A": "Krittika", "I": "Rohini", "U": "Mrigashira", "E": "Ardra", 
    "O": "Punarvasu", "Va": "Pushya", "Vi": "Ashlesha", "Vu": "Magha",
    "Ve": "Purva Phalguni", "Vo": "Uttara Phalguni", "Ka": "Hasta", 
    "Ki": "Chitra", "Ku": "Swati", "Ke": "Vishakha", "Ko": "Anuradha", 
    "Ha": "Jyeshtha", "Hi": "Mula", "Hu": "Purva Ashadha", "He": "Uttara Ashadha", 
    "Ho": "Abhijit", "Da": "Shravana", "Di": "Dhanishta", "Du": "Shatabhisha", 
    "De": "Purva Bhadrapada", "Do": "Uttara Bhadrapada", "Ma": "Revati",
    "Mi": "Ashwini", "Mu": "Bharani"
}

# --- Astrological Math ---
def get_sbc_nakshatra(lon):
    """Calculates the 28-Nakshatra system including Abhijit for SBC mapping."""
    if 276.6667 <= lon < 280.8889:
        return "Abhijit", 21
    elif lon >= 280.8889:
        regular_idx = math.floor(lon / 13.333333)
        return SBC_NAKSHATRAS[regular_idx + 1], regular_idx + 1
    else:
        regular_idx = math.floor(lon / 13.333333)
        return SBC_NAKSHATRAS[regular_idx], regular_idx

def get_planet_data(jd, planet_id):
    """Gets Sidereal (Lahiri) longitude and speed (direct/retrograde)"""
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    if planet_id == "KETU":
        pos, ret = swe.calc_ut(jd, swe.MEAN_NODE, flags)
        lon = (pos[0] + 180.0) % 360.0
        speed = pos[3] 
    else:
        pos, ret = swe.calc_ut(jd, planet_id, flags)
        lon = pos[0]
        speed = pos[3]
    return lon, speed

def get_vedha_type(speed, planet_name):
    if planet_name in ["Rahu", "KETU"]:
        return "Right (Retrograde)" 
    elif planet_name in ["Sun", "Moon"]:
        return "Left (Direct)" 
    else:
        if speed < 0:
            return "Right (Retrograde)"
        elif speed > 0 and speed < 0.2: 
            return "Frontal (Stationary)"
        else:
            return "Left (Direct)"

# --- UI Setup ---
st.title("🕉️ Sarvatobhadra Chakra (SBC) Engine")
st.markdown("Strict Lahiri Ayanamsa • 9-Planet Vedha • 28 Nakshatra System")

# --- SIDEBAR: Profile Setup ---
st.sidebar.header("👤 Subject Profile")
st.sidebar.markdown("Choose how to target the SBC:")
profile_type = st.sidebar.radio("Target by:", ["Birth Nakshatra", "First Name Syllable"])

native_n_idx = 0
target_nak = ""

if profile_type == "Birth Nakshatra":
    target_nak = st.sidebar.selectbox("Select Nakshatra", SBC_NAKSHATRAS, index=4)
    native_n_idx = SBC_NAKSHATRAS.index(target_nak)
else:
    syllable = st.sidebar.selectbox("First Sound of Name", list(AKSHARA_MAP.keys()))
    target_nak = AKSHARA_MAP[syllable]
    native_n_idx = SBC_NAKSHATRAS.index(target_nak)
    st.sidebar.info(f"Maps to Nakshatra: **{target_nak}**")

st.sidebar.markdown("---")
st.sidebar.header("🗓️ Time Settings")
target_date = st.sidebar.date_input("Target Date", datetime.date.today())
target_time = st.sidebar.time_input("Exact Time", datetime.time(12, 0))
tz_str = st.sidebar.selectbox("Timezone", ["Asia/Kolkata", "UTC", "America/New_York"], index=0)

# --- MAIN APP LOGIC ---
st.markdown(f"### 🔭 Transiting Planetary Vedhas on **{target_nak}**")
st.markdown("Displays which planets are actively striking or aspecting your target Nakshatra right now.")

# Convert local time to UTC for Swiss Ephemeris
local = pytz.timezone(tz_str)
dt_unaware = datetime.datetime.combine(target_date, target_time)
dt_aware = local.localize(dt_unaware)
dt_utc = dt_aware.astimezone(pytz.utc)

# Swisseph Julian Date
jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60.0)

with st.spinner("Calculating orbital mechanics..."):
    data = []
    
    planet_keys = list(PLANETS.keys()) + ["KETU"]
    for p_name in planet_keys:
        p_id = PLANETS[p_name] if p_name != "KETU" else "KETU"
        lon, speed = get_planet_data(jd, p_id)
        
        transiting_nak, transiting_idx = get_sbc_nakshatra(lon)
        vedha_direction = get_vedha_type(speed, p_name)
        
        distance = (transiting_idx - native_n_idx + 28) % 28
        
        is_vedha = "No"
        bg_color = ""
        
        if distance == 14: 
            is_vedha = "🔥 FRONTAL VEDHA"
            bg_color = "background-color: #FEE2E2; color: #991B1B; font-weight: bold;"
        elif distance == 0:
            is_vedha = "⚡ DIRECT CONJUNCTION"
            bg_color = "background-color: #FEF3C7; color: #92400E; font-weight: bold;"
        elif distance in [1, 27]:
            is_vedha = f"⚠️ ADJACENT ({vedha_direction})"
            bg_color = "background-color: #F0F9FF; color: #0369A1;"
        
        data.append({
            "Planet": p_name,
            "Current Nakshatra (28)": transiting_nak,
            "Motion / Vedha Cast": vedha_direction,
            "Impact on You": is_vedha,
            "_bg": bg_color
        })

    df = pd.DataFrame(data)

    # Cleaned up Styling function to prevent column mismatch
    display_df = df.drop(columns=['_bg'])
    
    styled_df = display_df.style.apply(
        lambda row: [df.loc[row.name, '_bg']] * len(row), 
        axis=1
    ).set_properties(**{'text-align': 'center', 'border': '1px solid #E2E8F0', 'padding': '10px'})
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

st.info("💡 **How to read this:** In Sarvatobhadra Chakra, malefic planets (Saturn, Mars, Rahu, Ketu, Sun) casting Vedha (Frontal, Left, or Right) onto your Nakshatra indicate obstacles. Benefics (Jupiter, Venus, Mercury, Moon) casting Vedha indicate support and success.")
