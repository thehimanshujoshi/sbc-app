import streamlit as st
import swisseph as swe
import pandas as pd
import datetime
import pytz
from dateutil.relativedelta import relativedelta
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

st.set_page_config(page_title="Pro Astrological Transit Tracker", layout="wide")

# --- Constants & Astrological Rules ---
ZODIAC_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

PLANETS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, 
    "Mercury": swe.MERCURY, "Venus": swe.VENUS, "Jupiter": swe.JUPITER, 
    "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE, "Ketu": "KETU"
}

# Combustion degrees (Standard Vedic)
COMBUSTION_LIMITS = {
    "Moon": 12, "Mars": 17, "Jupiter": 11, "Saturn": 15,
    "Mercury": {"Direct": 14, "Retrograde": 12},
    "Venus": {"Direct": 10, "Retrograde": 8}
}

# Pushkar Navamsha Indices (0-indexed within the 9 Navamshas of a sign)
# Fire (Aries, Leo, Sag): 7th (Libra) & 9th (Sag) Navamsha
# Earth (Taurus, Virgo, Cap): 3rd (Pisces) & 5th (Taurus) Navamsha
# Air (Gemini, Libra, Aqua): 6th (Pisces) & 8th (Taurus) Navamsha
# Water (Cancer, Scorpio, Pisces): 1st (Cancer) & 3rd (Virgo) Navamsha
PUSHKAR_RULES = {
    0: [6, 8], 4: [6, 8], 8: [6, 8],       # Fire
    1: [2, 4], 5: [2, 4], 9: [2, 4],       # Earth
    2: [5, 7], 6: [5, 7], 10: [5, 7],      # Air
    3: [0, 2], 7: [0, 2], 11: [0, 2]       # Water
}

# --- Core Functions ---
@st.cache_data
def get_location_tz(city_name):
    """Fetches timezone based on city name."""
    geolocator = Nominatim(user_agent="astrology_app")
    location = geolocator.geocode(city_name)
    if location:
        tf = TimezoneFinder()
        tz_name = tf.timezone_at(lng=location.longitude, lat=location.latitude)
        return pytz.timezone(tz_name), location.address
    return None, None

def get_planet_pos(planet_name, date_obj, system_flag):
    """Calculates longitude and speed."""
    utc_date = date_obj.astimezone(pytz.utc)
    jd = swe.julday(utc_date.year, utc_date.month, utc_date.day, utc_date.hour + utc_date.minute/60.0)
    
    if planet_name == "Ketu":
        pos, _ = swe.calc_ut(jd, PLANETS["Rahu"], system_flag)
        longitude = (pos[0] + 180.0) % 360.0
        speed = pos[3]
    else:
        pos, _ = swe.calc_ut(jd, PLANETS[planet_name], system_flag)
        longitude = pos[0]
        speed = pos[3]
        
    return longitude, speed

def get_astrological_status(planet_name, longitude, speed, date_obj, system_flag):
    """Determines D1 Sign, D9 Sign, Vargottama, Pushkar, and Combustion."""
    # D1 & D9 Signs
    d1_index = int(longitude / 30.0)
    d1_sign = ZODIAC_SIGNS[d1_index]
    
    navamsha_absolute_index = int(longitude / (360.0 / 108.0))
    d9_index = navamsha_absolute_index % 12
    d9_sign = ZODIAC_SIGNS[d9_index]
    
    # Internal Navamsha index within the specific D1 sign (0 to 8)
    internal_nav_index = navamsha_absolute_index % 9
    
    # Vargottama & Pushkar
    is_vargottama = (d1_sign == d9_sign)
    is_pushkar = internal_nav_index in PUSHKAR_RULES.get(d1_index, [])
    
    # Motion
    motion = "Retrograde" if speed < 0 else "Direct"
    if planet_name in ["Rahu", "Ketu"]:
        motion = "Retrograde" # Nodes are almost always considered retrograde natively
        
    # Combustion (Astangata)
    is_combust = False
    if planet_name not in ["Sun", "Rahu", "Ketu"]:
        sun_lon, _ = get_planet_pos("Sun", date_obj, system_flag)
        angular_dist = min((longitude - sun_lon) % 360, (sun_lon - longitude) % 360)
        
        limit = COMBUSTION_LIMITS.get(planet_name)
        if isinstance(limit, dict):
            limit = limit[motion]
            
        if angular_dist <= limit:
            is_combust = True
            
    return {
        "D1_Sign": d1_sign, "D9_Sign": d9_sign, "D9_Absolute_Idx": navamsha_absolute_index,
        "Motion": motion, "Vargottama": is_vargottama, "Pushkar": is_pushkar, "Combust": is_combust
    }

def find_exact_transit_time(planet, start_t, end_t, start_nav_idx, sys_flag):
    """Binary search for the exact minute a planet changes Navamsha."""
    while (end_t - start_t).total_seconds() > 60:
        mid_t = start_t + (end_t - start_t) / 2
        lon, _ = get_planet_pos(planet, mid_t, sys_flag)
        mid_nav_idx = int(lon / (360.0 / 108.0))
        
        if mid_nav_idx == start_nav_idx:
            start_t = mid_t
        else:
            end_t = mid_t
    return end_t

def calculate_transits(planets, start_date, end_date, sys_flag):
    all_transits = []
    
    for planet in planets:
        step_hours = 1 if planet == "Moon" else 6 
        current_date = start_date
        
        lon, speed = get_planet_pos(planet, current_date, sys_flag)
        status = get_astrological_status(planet, lon, speed, current_date, sys_flag)
        entry_date = current_date
        
        while current_date <= end_date:
            next_date = current_date + datetime.timedelta(hours=step_hours)
            if next_date > end_date:
                break
                
            next_lon, next_speed = get_planet_pos(planet, next_date, sys_flag)
            next_status = get_astrological_status(planet, next_lon, next_speed, next_date, sys_flag)
            
            # Record transit if Navamsha, Motion, or Combustion changes
            if (status["D9_Absolute_Idx"] != next_status["D9_Absolute_Idx"] or 
                status["Motion"] != next_status["Motion"] or 
                status["Combust"] != next_status["Combust"]):
                
                exact_time = next_date
                # Only binary search if it's a sign change (motion/combustion changes are slower, 6 hrs is fine)
                if status["D9_Absolute_Idx"] != next_status["D9_Absolute_Idx"]:
                    exact_time = find_exact_transit_time(planet, current_date, next_date, status["D9_Absolute_Idx"], sys_flag)
                
                duration = (exact_time - entry_date).total_seconds() / 86400.0
                
                # Format Tags
                tags = []
                if status["Vargottama"]: tags.append("🌟 Vargottama")
                if status["Pushkar"]: tags.append("🌸 Pushkar")
                if status["Combust"]: tags.append("🔥 Combust")
                
                all_transits.append({
                    "Planet": planet,
                    "Rashi (D1)": status["D1_Sign"],
                    "Navamsha (D9)": status["D9_Sign"],
                    "Motion": status["Motion"],
                    "Status": " | ".join(tags) if tags else "-",
                    "Entry_Obj": entry_date,
                    "Entry": entry_date.strftime("%d %b %Y, %I:%M %p"),
                    "Exit": exact_time.strftime("%d %b %Y, %I:%M %p"),
                    "Days": round(duration, 2)
                })
                
                status = next_status
                entry_date = exact_time
                
            current_date = next_date
            
    df = pd.DataFrame(all_transits)
    if not df.empty:
        df = df.sort_values(by="Entry_Obj").drop(columns=["Entry_Obj"])
    return df

# --- UI Setup ---
st.sidebar.header("⚙️ Settings")
astrology_system = st.sidebar.radio("Astrology System", ["Vedic (Lahiri Ayanamsa)", "Western (Tropical)"])

location_input = st.sidebar.text_input("Enter City", "Mumbai, India")
local_tz, formatted_address = get_location_tz(location_input)

if not local_tz:
    st.sidebar.error("Location not found. Defaulting to UTC.")
    local_tz = pytz.utc
else:
    st.sidebar.success(f"Detected: {formatted_address} ({local_tz})")

sys_flag = swe.FLG_SWIEPH
if "Vedic" in astrology_system:
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    sys_flag |= swe.FLG_SIDEREAL

# Main Page
col1, col2 = st.columns(2)
with col1:
    selected_start = st.date_input("Start Date", datetime.date.today())
with col2:
    durations = {"1 Month": 1, "3 Months": 3, "6 Months": 6, "1 Year": 12}
    selected_dur = st.selectbox("Timeline Duration", list(durations.keys()), index=0)

selected_planets = st.multiselect("Filter Planets", list(PLANETS.keys()), default=["Venus", "Jupiter", "Saturn"])

if st.button("Generate Pro Timeline"):
    if not selected_planets:
        st.warning("Select at least one planet.")
    else:
        start_dt = local_tz.localize(datetime.datetime.combine(selected_start, datetime.time.min))
        end_dt = start_dt + relativedelta(months=durations[selected_dur])
        
        with st.spinner("Crunching ephemeris data..."):
            df = calculate_transits(selected_planets, start_dt, end_dt, sys_flag)
            
            if df.empty:
                st.info("No major transits or status changes found in this timeframe.")
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
