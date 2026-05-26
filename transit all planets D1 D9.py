import streamlit as st
import swisseph as swe
import pandas as pd
import datetime
import pytz
from dateutil.relativedelta import relativedelta
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

# Configure for responsive wide layout
st.set_page_config(page_title="Pro Astrological Engine", layout="wide")

# --- Constants & Astrological Rules ---
ZODIAC_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

PLANETS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, 
    "Mercury": swe.MERCURY, "Venus": swe.VENUS, "Jupiter": swe.JUPITER, 
    "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE, "Ketu": "KETU"
}

COMBUSTION_LIMITS = {
    "Moon": 12, "Mars": 17, "Jupiter": 11, "Saturn": 15,
    "Mercury": {"Direct": 14, "Retrograde": 12},
    "Venus": {"Direct": 10, "Retrograde": 8}
}

PUSHKAR_RULES = {
    0: [6, 8], 4: [6, 8], 8: [6, 8],
    1: [2, 4], 5: [2, 4], 9: [2, 4],
    2: [5, 7], 6: [5, 7], 10: [5, 7],
    3: [0, 2], 7: [0, 2], 11: [0, 2]
}

# --- Core Functions ---
@st.cache_data
def get_location_tz(city_name):
    geolocator = Nominatim(user_agent="astrology_app")
    try:
        location = geolocator.geocode(city_name)
        if location:
            tf = TimezoneFinder()
            tz_name = tf.timezone_at(lng=location.longitude, lat=location.latitude)
            return pytz.timezone(tz_name), location.address
    except:
        pass
    return None, None

def get_planet_pos(planet_name, date_obj, system_flag, flag_extra=0):
    """Calculates longitude/latitude/declination and speed."""
    utc_date = date_obj.astimezone(pytz.utc)
    jd = swe.julday(utc_date.year, utc_date.month, utc_date.day, utc_date.hour + utc_date.minute/60.0)
    
    calc_flag = system_flag | flag_extra
    
    if planet_name == "Ketu":
        pos, _ = swe.calc_ut(jd, PLANETS["Rahu"], calc_flag)
        # Ketu is exactly 180 degrees opposite Rahu
        longitude = (pos[0] + 180.0) % 360.0
        latitude = -pos[1] # Latitude is opposite
        speed = pos[3]
    else:
        pos, _ = swe.calc_ut(jd, PLANETS[planet_name], calc_flag)
        longitude = pos[0]
        latitude = pos[1]
        speed = pos[3]
        
    return longitude, latitude, speed

def get_astrological_status(planet_name, longitude, speed, date_obj, system_flag):
    """Determines D1/D9 Signs, Vargottama, Pushkar, Combustion, and Correct Motion."""
    d1_index = int(longitude / 30.0)
    d1_sign = ZODIAC_SIGNS[d1_index]
    
    nav_abs_index = int(longitude / (360.0 / 108.0))
    d9_sign = ZODIAC_SIGNS[nav_abs_index % 12]
    
    is_vargottama = (d1_sign == d9_sign)
    is_pushkar = (nav_abs_index % 9) in PUSHKAR_RULES.get(d1_index, [])
    
    # CORRECTED RETROGRADE LOGIC
    if planet_name in ["Sun", "Moon"]:
        motion = "Direct"
    elif planet_name in ["Rahu", "Ketu"]:
        motion = "Retrograde"
    else:
        motion = "Retrograde" if speed < 0 else "Direct"
        
    is_combust = False
    if planet_name not in ["Sun", "Rahu", "Ketu"]:
        sun_lon, _, _ = get_planet_pos("Sun", date_obj, system_flag)
        angular_dist = min((longitude - sun_lon) % 360, (sun_lon - longitude) % 360)
        limit = COMBUSTION_LIMITS.get(planet_name)
        if isinstance(limit, dict): limit = limit[motion]
        if angular_dist <= limit: is_combust = True
            
    return {
        "D1": d1_sign, "D9": d9_sign, "Nav_Idx": nav_abs_index,
        "Motion": motion, "Vargottama": is_vargottama, "Pushkar": is_pushkar, "Combust": is_combust
    }

def calculate_lat_dec_extremes(planet, start_date, end_date, sys_flag):
    """Finds zero crossovers, max, and min for Ecliptic Latitude & Equatorial Declination."""
    events = []
    current_date = start_date
    
    # Calculate positions daily to find trends
    data = []
    while current_date <= end_date:
        _, ecl_lat, _ = get_planet_pos(planet, current_date, sys_flag)
        _, eq_dec, _ = get_planet_pos(planet, current_date, sys_flag, swe.FLG_EQUATORIAL)
        data.append((current_date, ecl_lat, eq_dec))
        current_date += datetime.timedelta(days=1)
        
    # Analyze array for crossovers and extremes (Simplified for performance)
    for i in range(1, len(data) - 1):
        prev_d, prev_lat, prev_dec = data[i-1]
        curr_d, curr_lat, curr_dec = data[i]
        next_d, next_lat, next_dec = data[i+1]
        
        # Ecliptic Latitude Zero Crossover
        if prev_lat * curr_lat <= 0:
            events.append({"Type": "Lat Zero Cross", "Value": 0.0, "Date": curr_d.strftime("%d %b %Y, %I:%M %p")})
            
        # Equatorial Declination Zero Crossover
        if prev_dec * curr_dec <= 0:
            events.append({"Type": "Dec Zero Cross", "Value": 0.0, "Date": curr_d.strftime("%d %b %Y, %I:%M %p")})
            
        # Latitude Local Max/Min
        if prev_lat < curr_lat and curr_lat > next_lat:
            events.append({"Type": "Lat Max", "Value": round(curr_lat, 4), "Date": curr_d.strftime("%d %b %Y, %I:%M %p")})
        elif prev_lat > curr_lat and curr_lat < next_lat:
            events.append({"Type": "Lat Min", "Value": round(curr_lat, 4), "Date": curr_d.strftime("%d %b %Y, %I:%M %p")})
            
    return events

# --- UI Setup ---
st.sidebar.header("⚙️ Settings")
astrology_system = st.sidebar.radio("Astrology System", ["Vedic (Lahiri Ayanamsa)", "Western (Tropical)"])

location_input = st.sidebar.text_input("Enter City", "Mumbai, India")
local_tz, formatted_address = get_location_tz(location_input)

if not local_tz:
    local_tz = pytz.utc

sys_flag = swe.FLG_SWIEPH
if "Vedic" in astrology_system:
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    sys_flag |= swe.FLG_SIDEREAL

# Main Page Header
st.title("Pro Astrological Engine")

# Responsive Data Selection layout
col1, col2 = st.columns(2)
with col1:
    selected_start = st.date_input("Start Date", datetime.date.today())
with col2:
    durations = {"1 Month": 1, "3 Months": 3, "6 Months": 6, "1 Year": 12}
    selected_dur = st.selectbox("Timeline Duration", list(durations.keys()), index=0)

st.markdown("### Select Planets to Track")
# Modern Pill Selection (Replaces Multiselect)
selected_planets = st.pills(
    "Planets", 
    options=list(PLANETS.keys()), 
    default=["Sun", "Moon", "Saturn"], 
    selection_mode="multi",
    label_visibility="collapsed"
)

if st.button("Generate Timeline & Data", type="primary"):
    if not selected_planets:
        st.warning("Please select at least one planet.")
    else:
        start_dt = local_tz.localize(datetime.datetime.combine(selected_start, datetime.time.min))
        end_dt = start_dt + relativedelta(months=durations[selected_dur])
        
        # --- 1. Generate Advanced Latitude/Declination Data ---
        st.markdown("---")
        st.subheader("🪐 Orbital Extremes (Ecliptic Latitude & Equatorial Declination)")
        
        # Use columns to display cards for each selected planet responsively
        cols = st.columns(len(selected_planets))
        for idx, planet in enumerate(selected_planets):
            with cols[idx]:
                with st.expander(f"{planet} Data", expanded=True):
                    events = calculate_lat_dec_extremes(planet, start_dt, end_dt, sys_flag)
                    if not events:
                        st.write("No extremes or zero crosses in this timeframe.")
                    else:
                        for e in events:
                            st.markdown(f"**{e['Type']}**: {e['Value']}° <br> <small>{e['Date']}</small>", unsafe_allow_html=True)

        # --- 2. Generate Main Transit Table ---
        st.markdown("---")
        st.subheader("Navamsha Transit Timeline")
        
        with st.spinner("Crunching ephemeris data..."):
            all_transits = []
            for planet in selected_planets:
                current_date = start_dt
                lon, _, speed = get_planet_pos(planet, current_date, sys_flag)
                status = get_astrological_status(planet, lon, speed, current_date, sys_flag)
                
                while current_date <= end_dt:
                    next_date = current_date + datetime.timedelta(hours=6)
                    if next_date > end_dt: break
                    
                    next_lon, _, next_speed = get_planet_pos(planet, next_date, sys_flag)
                    next_status = get_astrological_status(planet, next_lon, next_speed, next_date, sys_flag)
                    
                    if (status["Nav_Idx"] != next_status["Nav_Idx"] or 
                        status["Motion"] != next_status["Motion"] or 
                        status["Combust"] != next_status["Combust"]):
                        
                        tags = []
                        if status["Vargottama"]: tags.append("🌟 Varg")
                        if status["Pushkar"]: tags.append("🌸 Pushkar")
                        if status["Combust"]: tags.append("🔥 Combust")
                        
                        all_transits.append({
                            "Planet": planet,
                            "Motion": status["Motion"],
                            "D1 Sign": status["D1"],
                            "D9 Navamsha": status["D9"],
                            "Special Status": " | ".join(tags) if tags else "-",
                            "Date/Time": next_date.strftime("%d %b %Y, %I:%M %p")
                        })
                        status = next_status
                    current_date = next_date
                    
            df = pd.DataFrame(all_transits)
            
            # Responsive Dataframe display
            if not df.empty:
                st.dataframe(
                    df, 
                    use_container_width=True, # Ensures it expands to full width
                    hide_index=True,
                    column_config={
                        "Special Status": st.column_config.TextColumn("Special Status", width="medium"),
                        "Date/Time": st.column_config.TextColumn("Date/Time", width="medium")
                    }
                )
            else:
                st.info("No major shifts found.")
