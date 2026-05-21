import streamlit as st
import pandas as pd
import datetime
import pytz
import math

try:
    import swisseph as swe
except ImportError:
    st.error("⚠️ The 'pyswisseph' library is missing. Please ensure you created the requirements.txt file on GitHub!")
    st.stop()

st.set_page_config(page_title="SBC Astro Engine", page_icon="🕉️", layout="wide")
swe.set_sid_mode(swe.SIDM_LAHIRI)

# --- 28 Nakshatra System (SBC includes Abhijit) ---
SBC_NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", 
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", 
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", 
    "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", 
    "Abhijit", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", 
    "Uttara Bhadrapada", "Revati"
]

PLANETS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, 
    "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, 
    "Venus": swe.VENUS, "Saturn": swe.SATURN, 
    "Rahu": swe.MEAN_NODE 
}

# --- Full 108 Akshara (Syllable) to Nakshatra/Pada Mapping ---
# Format: "Syllable": ("Nakshatra", Pada)
AKSHARA_MAP = {
    "Chu": ("Ashwini", 1), "Che": ("Ashwini", 2), "Cho": ("Ashwini", 3), "La": ("Ashwini", 4),
    "Li": ("Bharani", 1), "Lu": ("Bharani", 2), "Le": ("Bharani", 3), "Lo": ("Bharani", 4),
    "A": ("Krittika", 1), "I": ("Krittika", 2), "U": ("Krittika", 3), "Ea": ("Krittika", 4),
    "O": ("Rohini", 1), "Va": ("Rohini", 2), "Vi": ("Rohini", 3), "Vu": ("Rohini", 4),
    "Ve": ("Mrigashira", 1), "Vo": ("Mrigashira", 2), "Ka": ("Mrigashira", 3), "Ki": ("Mrigashira", 4),
    "Ku": ("Ardra", 1), "Gha": ("Ardra", 2), "Ng": ("Ardra", 3), "Chha": ("Ardra", 4),
    "Ke": ("Punarvasu", 1), "Ko": ("Punarvasu", 2), "Ha": ("Punarvasu", 3), "Hi": ("Punarvasu", 4),
    "Hu": ("Pushya", 1), "He": ("Pushya", 2), "Ho": ("Pushya", 3), "Da": ("Pushya", 4),
    "Di": ("Ashlesha", 1), "Du": ("Ashlesha", 2), "De": ("Ashlesha", 3), "Do": ("Ashlesha", 4),
    "Ma": ("Magha", 1), "Mi": ("Magha", 2), "Mu": ("Magha", 3), "Me": ("Magha", 4),
    "Mo": ("Purva Phalguni", 1), "Ta": ("Purva Phalguni", 2), "Ti": ("Purva Phalguni", 3), "Tu": ("Purva Phalguni", 4),
    "Te": ("Uttara Phalguni", 1), "To": ("Uttara Phalguni", 2), "Pa": ("Uttara Phalguni", 3), "Pi": ("Uttara Phalguni", 4),
    "Pu": ("Hasta", 1), "Sha": ("Hasta", 2), "Na": ("Hasta", 3), "Tha": ("Hasta", 4),
    "Pe": ("Chitra", 1), "Po": ("Chitra", 2), "Ra": ("Chitra", 3), "Ri": ("Chitra", 4),
    "Ru": ("Swati", 1), "Re": ("Swati", 2), "Ro": ("Swati", 3), "Taa": ("Swati", 4),
    "Tii": ("Vishakha", 1), "Tuu": ("Vishakha", 2), "Tee": ("Vishakha", 3), "Too": ("Vishakha", 4),
    "Naa": ("Anuradha", 1), "Nee": ("Anuradha", 2), "Nuu": ("Anuradha", 3), "Nee": ("Anuradha", 4),
    "No": ("Jyeshtha", 1), "Ya": ("Jyeshtha", 2), "Yi": ("Jyeshtha", 3), "Yu": ("Jyeshtha", 4),
    "Ye": ("Mula", 1), "Yo": ("Mula", 2), "Ba": ("Mula", 3), "Bi": ("Mula", 4),
    "Bu": ("Purva Ashadha", 1), "Dhaa": ("Purva Ashadha", 2), "Bha": ("Purva Ashadha", 3), "Dha": ("Purva Ashadha", 4),
    "Be": ("Uttara Ashadha", 1), "Bo": ("Uttara Ashadha", 2), "Ja": ("Uttara Ashadha", 3), "Ji": ("Uttara Ashadha", 4),
    "Ju": ("Shravana", 1), "Je": ("Shravana", 2), "Jo": ("Shravana", 3), "Gha": ("Shravana", 4),
    "Ga": ("Dhanishta", 1), "Gi": ("Dhanishta", 2), "Gu": ("Dhanishta", 3), "Ge": ("Dhanishta", 4),
    "Go": ("Shatabhisha", 1), "Sa": ("Shatabhisha", 2), "Si": ("Shatabhisha", 3), "Su": ("Shatabhisha", 4),
    "Se": ("Purva Bhadrapada", 1), "So": ("Purva Bhadrapada", 2), "Daa": ("Purva Bhadrapada", 3), "Dii": ("Purva Bhadrapada", 4),
    "Duu": ("Uttara Bhadrapada", 1), "Thaa": ("Uttara Bhadrapada", 2), "Jha": ("Uttara Bhadrapada", 3), "Naa": ("Uttara Bhadrapada", 4),
    "De": ("Revati", 1), "Do": ("Revati", 2), "Cha": ("Revati", 3), "Chi": ("Revati", 4)
}

def get_sbc_nakshatra(lon):
    if 276.6667 <= lon < 280.8889:
        return "Abhijit", 21
    elif lon >= 280.8889:
        regular_idx = math.floor(lon / 13.333333)
        return SBC_NAKSHATRAS[regular_idx + 1], regular_idx + 1
    else:
        regular_idx = math.floor(lon / 13.333333)
        return SBC_NAKSHATRAS[regular_idx], regular_idx

def get_planet_data(jd, planet_id):
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
    if planet_name in ["Rahu", "KETU"]: return "Right (Retrograde)" 
    elif planet_name in ["Sun", "Moon"]: return "Left (Direct)" 
    else:
        if speed < 0: return "Right (Retrograde)"
        elif speed > 0 and speed < 0.2: return "Frontal (Stationary)"
        else: return "Left (Direct)"

st.title("🕉️ Sarvatobhadra Chakra (SBC) Engine")
st.markdown("Strict Lahiri Ayanamsa • 9-Planet Vedha • 28 Nakshatra System")

# --- SIDEBAR: Profile Setup ---
st.sidebar.header("👤 Subject Profile")
profile_type = st.sidebar.radio("Target by:", ["First Name Syllable", "Birth Nakshatra"])

native_n_idx = 0
target_nak = ""
target_pada = 1

if profile_type == "First Name Syllable":
    syllable = st.sidebar.selectbox("First Sound of Name", list(AKSHARA_MAP.keys()))
    target_nak, target_pada = AKSHARA_MAP[syllable]
    native_n_idx = SBC_NAKSHATRAS.index(target_nak)
    st.sidebar.success(f"**Mapped to:** {target_nak} (Pada {target_pada})")
else:
    target_nak = st.sidebar.selectbox("Select Nakshatra", SBC_NAKSHATRAS, index=4)
    target_pada = st.sidebar.selectbox("Select Pada", [1, 2, 3, 4], index=0)
    native_n_idx = SBC_NAKSHATRAS.index(target_nak)

st.sidebar.markdown("---")
st.sidebar.header("🗓️ Time Settings")
target_date = st.sidebar.date_input("Target Date", datetime.date.today())
target_time = st.sidebar.time_input("Exact Time", datetime.time(12, 0))
tz_str = st.sidebar.selectbox("Timezone", ["Asia/Kolkata", "UTC", "America/New_York"], index=0)

# --- MAIN APP LOGIC ---
st.markdown(f"### 🔭 Transiting Planetary Vedhas on **{target_nak} (Pada {target_pada})**")
st.markdown("Displays which planets are actively striking or aspecting your target Nakshatra right now.")

local = pytz.timezone(tz_str)
dt_unaware = datetime.datetime.combine(target_date, target_time)
dt_aware = local.localize(dt_unaware)
dt_utc = dt_aware.astimezone(pytz.utc)

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
    display_df = df.drop(columns=['_bg'])
    
    styled_df = display_df.style.apply(
        lambda row: [df.loc[row.name, '_bg']] * len(row), 
        axis=1
    ).set_properties(**{'text-align': 'center', 'border': '1px solid #E2E8F0', 'padding': '10px'})
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

st.info("💡 **How to read this:** In Sarvatobhadra Chakra, malefic planets (Saturn, Mars, Rahu, Ketu, Sun) casting Vedha (Frontal, Left, or Right) onto your Nakshatra indicate obstacles. Benefics (Jupiter, Venus, Mercury, Moon) casting Vedha indicate support and success.")
