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

FIXED_STARS = [
    "Algol", "Alcyone", "Aldebaran", "Rigel", "Capella", "Betelgeuse", 
    "Sirius", "Procyon", "Regulus", "Spica", "Arcturus", "Antares", 
    "Vega", "Altair", "Fomalhaut"
]

ASPECT_TARGETS = {
    0: "Conjunction (0°)", 
    90: "Quadrant / Square (90°)", 
    120: "Trine (120°)", 
    240: "Trine (240°)", 
    270: "Quadrant / Square (270°)"
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
def get_location_data(city_name):
    """Fetches Timezone, Latitude, and Longitude based on city name."""
    geolocator = Nominatim(user_agent="astrology_app")
    try:
        location = geolocator.geocode(city_name)
        if location:
            tf = TimezoneFinder()
            tz_name = tf.timezone_at(lng=location.longitude, lat=location.latitude)
            return pytz.timezone(tz_name), location.address, location.latitude, location.longitude
    except:
        pass
    return None, None, 0.0, 0.0

def get_planet_pos(name, date_obj, system_flag, flag_extra=0):
    utc_date = date_obj.astimezone(pytz.utc)
    jd = swe.julday(utc_date.year, utc_date.month, utc_date.day, utc_date.hour + utc_date.minute/60.0)
    
    calc_flag = system_flag | flag_extra | swe.FLG_SPEED
    
    if name in FIXED_STARS:
        try:
            pos, _ = swe.fixstar2_ut(name, jd, calc_flag)
            return pos[0], pos[1], pos[3]
        except:
            return 0.0, 0.0, 0.0
            
    if name == "Ketu":
        pos, _ = swe.calc_ut(jd, PLANETS["Rahu"], calc_flag)
        return (pos[0] + 180.0) % 360.0, -pos[1], pos[3]
        
    pos, _ = swe.calc_ut(jd, PLANETS[name], calc_flag)
    return pos[0], pos[1], pos[3]

def get_astrological_status(name, longitude, speed, date_obj, system_flag):
    d1_index = int(longitude / 30.0)
    d1_sign = ZODIAC_SIGNS[d1_index]
    nav_abs_index = int(longitude / (360.0 / 108.0))
    d9_sign = ZODIAC_SIGNS[nav_abs_index % 12]
    
    is_vargottama = (d1_sign == d9_sign)
    is_pushkar = (nav_abs_index % 9) in PUSHKAR_RULES.get(d1_index, [])
    
    if name in ["Sun", "Moon"] or name in FIXED_STARS:
        motion = "Direct"
    elif name in ["Rahu", "Ketu"]:
        motion = "Retrograde"
    else:
        motion = "Retrograde" if speed < 0 else "Direct"
        
    is_combust = False
    if name not in ["Sun", "Rahu", "Ketu"] and name not in FIXED_STARS:
        sun_lon, _, _ = get_planet_pos("Sun", date_obj, system_flag)
        angular_dist = min((longitude - sun_lon) % 360, (sun_lon - longitude) % 360)
        limit = COMBUSTION_LIMITS.get(name)
        if isinstance(limit, dict): limit = limit[motion]
        if angular_dist <= limit: is_combust = True
            
    return {
        "D1": d1_sign, "D9": d9_sign, "Nav_Idx": nav_abs_index,
        "Motion": motion, "Vargottama": is_vargottama, "Pushkar": is_pushkar, "Combust": is_combust
    }

def find_exact_transit_time(name, start_t, end_t, start_nav_idx, sys_flag):
    while (end_t - start_t).total_seconds() > 60:
        mid_t = start_t + (end_t - start_t) / 2
        lon, _, _ = get_planet_pos(name, mid_t, sys_flag)
        if int(lon / (360.0 / 108.0)) == start_nav_idx:
            start_t = mid_t
        else:
            end_t = mid_t
    return end_t

def find_exact_zero_cross(name, start_t, end_t, sys_flag, flag_extra):
    while (end_t - start_t).total_seconds() > 60:
        mid_t = start_t + (end_t - start_t) / 2
        _, lat1, _ = get_planet_pos(name, start_t, sys_flag, flag_extra)
        _, mid_lat, _ = get_planet_pos(name, mid_t, sys_flag, flag_extra)
        if lat1 * mid_lat <= 0:
            end_t = mid_t
        else:
            start_t = mid_t
    return end_t

def calculate_lat_dec_extremes(name, start_date, end_date, sys_flag):
    if name in ["Rahu", "Ketu"]: return []
    events, data = [], []
    current_date = start_date
    
    while current_date <= end_date:
        _, ecl_lat, _ = get_planet_pos(name, current_date, sys_flag)
        _, eq_dec, _ = get_planet_pos(name, current_date, sys_flag, swe.FLG_EQUATORIAL)
        data.append((current_date, ecl_lat, eq_dec))
        current_date += datetime.timedelta(days=1)
        
    for i in range(1, len(data) - 1):
        prev_d, prev_lat, prev_dec = data[i-1]
        curr_d, curr_lat, curr_dec = data[i]
        next_d, next_lat, next_dec = data[i+1]
        
        if prev_lat * curr_lat <= 0:
            events.append({"Type": "Lat Zero Cross", "Value": "0.00°", "Date": find_exact_zero_cross(name, prev_d, curr_d, sys_flag, 0)})
        if prev_dec * curr_dec <= 0:
            events.append({"Type": "Dec Zero Cross", "Value": "0.00°", "Date": find_exact_zero_cross(name, prev_d, curr_d, sys_flag, swe.FLG_EQUATORIAL)})
            
        if (prev_lat < curr_lat and curr_lat > next_lat) or (prev_lat > curr_lat and curr_lat < next_lat):
            peak_val, peak_time, scan_time = curr_lat, curr_d, prev_d
            while scan_time <= next_d:
                _, scan_lat, _ = get_planet_pos(name, scan_time, sys_flag)
                if (prev_lat < curr_lat and scan_lat > peak_val) or (prev_lat > curr_lat and scan_lat < peak_val):
                    peak_val, peak_time = scan_lat, scan_time
                scan_time += datetime.timedelta(hours=1)
            label = "Lat Max" if prev_lat < curr_lat else "Lat Min"
            events.append({"Type": label, "Value": f"{peak_val:.4f}°", "Date": peak_time})
            
    events = sorted(events, key=lambda x: x["Date"])
    for e in events: e["Date_Str"] = e["Date"].strftime("%d %b %Y, %I:%M %p")
    return events

def find_exact_aspect(planet, star, target_angle, start_t, end_t, sys_flag):
    while (end_t - start_t).total_seconds() > 60:
        mid_t = start_t + (end_t - start_t) / 2
        p_lon, _, _ = get_planet_pos(planet, mid_t, sys_flag)
        s_lon, _, _ = get_planet_pos(star, mid_t, sys_flag)
        mid_angle = (p_lon - s_lon) % 360.0
        
        diff_start = ((get_planet_pos(planet, start_t, sys_flag)[0] - get_planet_pos(star, start_t, sys_flag)[0]) % 360.0 - target_angle)
        diff_mid = (mid_angle - target_angle)
        
        if diff_start > 180: diff_start -= 360
        elif diff_start < -180: diff_start += 360
        if diff_mid > 180: diff_mid -= 360
        elif diff_mid < -180: diff_mid += 360

        if diff_start * diff_mid <= 0: end_t = mid_t
        else: start_t = mid_t
    return end_t

def calculate_star_aspects(planets, stars, start_date, end_date, sys_flag):
    aspects = []
    valid_planets = [p for p in planets if p not in ["Rahu", "Ketu"]]
    
    for planet in valid_planets:
        for star in stars:
            curr_d = start_date
            while curr_d <= end_date:
                next_d = curr_d + datetime.timedelta(days=1)
                p_lon1, _, _ = get_planet_pos(planet, curr_d, sys_flag)
                s_lon1, _, _ = get_planet_pos(star, curr_d, sys_flag)
                p_lon2, _, _ = get_planet_pos(planet, next_d, sys_flag)
                s_lon2, _, _ = get_planet_pos(star, next_d, sys_flag)
                
                angle1 = (p_lon1 - s_lon1) % 360.0
                angle2 = (p_lon2 - s_lon2) % 360.0
                
                for target in ASPECT_TARGETS.keys():
                    diff1 = angle1 - target
                    diff2 = angle2 - target
                    if diff1 > 180: diff1 -= 360
                    elif diff1 < -180: diff1 += 360
                    if diff2 > 180: diff2 -= 360
                    elif diff2 < -180: diff2 += 360
                    
                    if diff1 * diff2 <= 0:
                        exact_time = find_exact_aspect(planet, star, target, curr_d, next_d, sys_flag)
                        if start_date <= exact_time <= end_date:
                            aspects.append({
                                "Exact_Time_Obj": exact_time,
                                "Planet": planet,
                                "Fixed Star": star,
                                "Alignment / Aspect": ASPECT_TARGETS[target],
                                "Date/Time (Exact)": exact_time.strftime("%d %b %Y, %I:%M %p")
                            })
                curr_d = next_d
                
    df = pd.DataFrame(aspects)
    if not df.empty:
        df = df.sort_values(by="Exact_Time_Obj").drop(columns=["Exact_Time_Obj"])
    return df

def get_datetime_from_jd(jd, local_tz):
    y, m, d, h = swe.revjul(jd)
    hours = int(h)
    mins = int((h - hours) * 60)
    secs = int((((h - hours) * 60) - mins) * 60)
    utc_dt = datetime.datetime(y, m, d, hours, mins, secs, tzinfo=pytz.utc)
    return utc_dt.astimezone(local_tz)

def calculate_eclipses(start_date, end_date, sys_flag_output, local_tz, visibility_mode, lat, lon):
    """Panchang Engine: Calculates global eclipse, then checks local horizon visibility."""
    eclipses = []
    utc_start = start_date.astimezone(pytz.utc)
    utc_end = end_date.astimezone(pytz.utc)
    jd_start = swe.julday(utc_start.year, utc_start.month, utc_start.day, utc_start.hour + utc_start.minute/60.0)
    jd_end = swe.julday(utc_end.year, utc_end.month, utc_end.day, utc_end.hour + utc_end.minute/60.0)

    geopos = (lon, lat, 0.0)

    # Solar Eclipses
    jd = jd_start
    while True:
        try:
            tret, _ = swe.sol_eclipse_when_glob(jd, swe.FLG_SWIEPH, 0, False)
            if tret[0] > jd_end or tret[0] == 0: break
            
            is_visible = True
            if "Local" in visibility_mode:
                # Panchang rule: Is the eclipse magnitude > 0 at this specific location?
                try:
                    _, attr = swe.sol_eclipse_how(tret[0], swe.FLG_SWIEPH, geopos)
                    if attr[0] <= 0.0: is_visible = False
                except:
                    is_visible = False

            if is_visible:
                max_dt = get_datetime_from_jd(tret[0], local_tz)
                sun_lon, _, _ = get_planet_pos("Sun", max_dt, sys_flag_output)
                status = get_astrological_status("Sun", sun_lon, 1.0, max_dt, sys_flag_output)
                
                eclipses.append({
                    "Date_Obj": max_dt,
                    "Eclipse Type": "☀️ Solar Eclipse",
                    "Max Time (Local)": max_dt.strftime("%d %b %Y, %I:%M %p"),
                    "Core Sign (D1)": status["D1"],
                    "Sub-Division (D9)": status["D9"]
                })
            jd = tret[0] + 5 # Jump past eclipse to avoid double counting
        except:
            break
            
    # Lunar Eclipses
    jd = jd_start
    while True:
        try:
            tret, _ = swe.lun_eclipse_when(jd, swe.FLG_SWIEPH, 0, False)
            if tret[0] > jd_end or tret[0] == 0: break
            
            is_visible = True
            if "Local" in visibility_mode:
                # Panchang rule for Lunar: Is it night time / moon above horizon?
                try:
                    _, attr = swe.lun_eclipse_how(tret[0], swe.FLG_SWIEPH, geopos)
                    if attr[0] <= 0.0: is_visible = False
                except:
                    is_visible = False

            if is_visible:
                max_dt = get_datetime_from_jd(tret[0], local_tz)
                moon_lon, _, _ = get_planet_pos("Moon", max_dt, sys_flag_output)
                status = get_astrological_status("Moon", moon_lon, 1.0, max_dt, sys_flag_output)
                
                eclipses.append({
                    "Date_Obj": max_dt,
                    "Eclipse Type": "🌕 Lunar Eclipse",
                    "Max Time (Local)": max_dt.strftime("%d %b %Y, %I:%M %p"),
                    "Core Sign (D1)": status["D1"],
                    "Sub-Division (D9)": status["D9"]
                })
            jd = tret[0] + 5
        except:
            break
            
    df = pd.DataFrame(eclipses)
    if not df.empty:
        df = df.sort_values(by="Date_Obj").drop(columns=["Date_Obj"])
    return df
# --- UI Setup ---
st.sidebar.header("⚙️ Settings")
astrology_system = st.sidebar.radio("Astrology System", ["Vedic (Lahiri Ayanamsa)", "Western (Tropical)"])

location_input = st.sidebar.text_input("Enter City", "Mumbai, India")
local_tz, formatted_address, loc_lat, loc_lon = get_location_data(location_input)

if not local_tz: local_tz = pytz.utc

sys_flag = swe.FLG_SWIEPH
if "Vedic" in astrology_system:
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    sys_flag |= swe.FLG_SIDEREAL

# Main Page Header
st.title("Transit Pro Engine")

col1, col2 = st.columns(2)
with col1: selected_start = st.date_input("Start Date", datetime.date.today())
with col2:
    durations = {"1 Month": 1, "3 Months": 3, "6 Months": 6, "1 Year": 12, "2 Years": 24, "5 Years": 60}
    selected_dur = st.selectbox("Timeline Duration", list(durations.keys()), index=3)

st.markdown("### Select Celestial Bodies to Track")
selected_planets = st.pills("Planets", options=list(PLANETS.keys()), default=["Sun", "Moon", "Saturn"], selection_mode="multi", label_visibility="collapsed")
selected_stars = st.pills("Prominent Fixed Stars (Yogataras)", options=FIXED_STARS, selection_mode="multi", label_visibility="collapsed")

selected_bodies = []
if selected_planets: selected_bodies.extend(selected_planets)
if selected_stars: selected_bodies.extend(selected_stars)

if st.button("Generate Master Timeline", type="primary"):
    if not selected_bodies:
        st.warning("Please select at least one celestial body.")
    else:
        start_dt = local_tz.localize(datetime.datetime.combine(selected_start, datetime.time.min))
        end_dt = start_dt + relativedelta(months=durations[selected_dur])
        
        csv_data = {}
        
        # --- 1. Orbital Extremes ---
        st.markdown("---")
        st.subheader("🪐 Orbital Extremes (Ecliptic Lat & Equatorial Dec)")
        bodies_for_extremes = [b for b in selected_bodies if b not in ["Rahu", "Ketu"]]
        if bodies_for_extremes:
            cols = st.columns(len(bodies_for_extremes) if len(bodies_for_extremes) < 4 else 4)
            for idx, body in enumerate(bodies_for_extremes):
                with cols[idx % 4]:
                    with st.expander(f"{body} Data", expanded=False):
                        events = calculate_lat_dec_extremes(body, start_dt, end_dt, sys_flag)
                        if not events: st.write("No extremes in this timeframe.")
                        else:
                            for e in events: st.markdown(f"**{e['Type']}**: {e['Value']} <br> <small>{e['Date_Str']}</small>", unsafe_allow_html=True)
        else:
            st.info("No bodies selected that possess ecliptic latitude variations (e.g., Nodes).")

        # --- 2. Main Transit Table ---
        st.markdown("---")
        st.subheader(f"Timeline: {'Navamsha (D9)' if 'Vedic' in astrology_system else '9th Harmonic (Novile)'} Shifts")
        with st.spinner("Crunching ephemeris data..."):
            all_transits = []
            for body in selected_bodies:
                curr_date = start_dt
                lon, _, speed = get_planet_pos(body, curr_date, sys_flag)
                status = get_astrological_status(body, lon, speed, curr_date, sys_flag)
                entry_date = curr_date
                
                while curr_date <= end_dt:
                    next_date = curr_date + datetime.timedelta(hours=6)
                    if next_date > end_dt: break
                    
                    next_lon, _, next_speed = get_planet_pos(body, next_date, sys_flag)
                    next_status = get_astrological_status(body, next_lon, next_speed, next_date, sys_flag)
                    
                    if (status["Nav_Idx"] != next_status["Nav_Idx"] or status["Motion"] != next_status["Motion"] or status["Combust"] != next_status["Combust"]):
                        exact_time = next_date
                        if status["Nav_Idx"] != next_status["Nav_Idx"]:
                            exact_time = find_exact_transit_time(body, curr_date, next_date, status["Nav_Idx"], sys_flag)
                        
                        tags = []
                        if status["Vargottama"]: tags.append("🌟 Varg")
                        if status["Pushkar"]: tags.append("🌸 Pushkar")
                        if status["Combust"]: tags.append("🔥 Combust")
                        
                        all_transits.append({
                            "Entry_Obj": entry_date,
                            "Body": body,
                            "Motion": status["Motion"],
                            "Sign": status["D1"],
                            "Sub-Division": status["D9"],
                            "Special Status": " | ".join(tags) if tags else "-",
                            "Entry Date": entry_date.strftime("%d %b %Y, %I:%M %p"),
                            "Exit Date": exact_time.strftime("%d %b %Y, %I:%M %p")
                        })
                        status = next_status
                        entry_date = exact_time
                    curr_date = next_date
                    
            df_transits = pd.DataFrame(all_transits)
            if not df_transits.empty:
                df_transits = df_transits.sort_values(by="Entry_Obj").drop(columns=["Entry_Obj"])
                st.dataframe(df_transits, use_container_width=True, hide_index=True, column_config={"Entry Date": st.column_config.TextColumn("Entry Date", width="medium"), "Exit Date": st.column_config.TextColumn("Exit Date", width="medium")})
                csv_data["Transits"] = df_transits.to_csv(index=False).encode('utf-8')
            else:
                st.info("No major shifts found in the specified timeframe.")

        # --- 3. Planet-Star Aspect Table ---
        if selected_planets and selected_stars:
            st.markdown("---")
            st.subheader("✨ Stellar Alignments (Planet to Fixed Star Aspects)")
            with st.spinner("Calculating high-precision star aspects..."):
                df_aspects = calculate_star_aspects(selected_planets, selected_stars, start_dt, end_dt, sys_flag)
                if not df_aspects.empty:
                    st.dataframe(df_aspects, use_container_width=True, hide_index=True, column_config={"Date/Time (Exact)": st.column_config.TextColumn("Date/Time (Exact)", width="medium")})
                    csv_data["Stellar_Aspects"] = df_aspects.to_csv(index=False).encode('utf-8')
                else:
                    st.info("No exact alignments (0°, 90°, 120°) between selected planets and stars during this timeframe.")

        # --- 4. Eclipse Tracker (Panchang Engine) ---
        st.markdown("---")
        col_A, col_B = st.columns([2, 1])
        with col_A:
            st.subheader("🌑 Eclipse Radar (Panchang Engine)")
        with col_B:
            # DEFAULT is now set to Local (index 0)
            visibility_mode = st.radio("Eclipse Search Mode", ["Local (Panchang Visibility)", "Global (Anywhere on Earth)"], index=0, label_visibility="collapsed", horizontal=True)

        with st.spinner("Scanning for eclipses..."):
            df_eclipses = calculate_eclipses(start_dt, end_dt, sys_flag, local_tz, visibility_mode, loc_lat, loc_lon)
            if not df_eclipses.empty:
                st.dataframe(
                    df_eclipses, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={"Max Time (Local)": st.column_config.TextColumn("Max Time (Local)", width="medium")}
                )
                csv_data["Eclipses"] = df_eclipses.to_csv(index=False).encode('utf-8')
            else:
                if "Local" in visibility_mode:
                    st.success(f"No Solar or Lunar Eclipses are visibly occurring in {formatted_address} during this timeframe.")
                else:
                    st.success("No Solar or Lunar Eclipses occur globally during this timeframe.")
                    
        # --- Export Data Buttons ---
        if csv_data:
            st.markdown("---")
            st.markdown("### 📥 Download Reports")
            dl_cols = st.columns(len(csv_data))
            for i, (name, file_bytes) in enumerate(csv_data.items()):
                with dl_cols[i]:
                    st.download_button(label=f"Download {name} (CSV)", data=file_bytes, file_name=f"{name.lower()}_report.csv", mime="text/csv")
