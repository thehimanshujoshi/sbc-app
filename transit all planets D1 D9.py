import streamlit as st
import swisseph as swe
import pandas as pd
import datetime
import pytz
from dateutil.relativedelta import relativedelta

# Configure Streamlit page layout
st.set_page_config(page_title="Navamsha Transit Timeline", layout="wide")

# --- Constants and Setup ---
ZODIAC_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

PLANETS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, 
    "Mercury": swe.MERCURY, "Venus": swe.VENUS, "Jupiter": swe.JUPITER, 
    "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE, "Ketu": "KETU"
}

IST = pytz.timezone('Asia/Kolkata')
swe.set_sid_mode(swe.SIDM_LAHIRI) # Set Ayanamsa to Lahiri

def get_planet_pos(planet_name, date_obj):
    """Calculates sidereal longitude and speed for a given datetime."""
    utc_date = date_obj.astimezone(pytz.utc)
    jd = swe.julday(utc_date.year, utc_date.month, utc_date.day, utc_date.hour + utc_date.minute/60.0)
    
    if planet_name == "Ketu":
        pos, _ = swe.calc_ut(jd, PLANETS["Rahu"], swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        longitude = (pos[0] + 180.0) % 360.0
        speed = pos[3]
    else:
        pos, _ = swe.calc_ut(jd, PLANETS[planet_name], swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        longitude = pos[0]
        speed = pos[3]
        
    return longitude, speed

def get_navamsha_info(longitude):
    """Returns the sign name and absolute index of the Navamsha."""
    navamsha_index = int(longitude / (360.0 / 108.0))
    sign_index = navamsha_index % 12
    return ZODIAC_SIGNS[sign_index], navamsha_index

def find_exact_transit_time(planet_name, start_t, end_t, start_nav_idx):
    """Binary search to find the exact minute a planet changes Navamsha."""
    while (end_t - start_t).total_seconds() > 60: # 1-minute precision
        mid_t = start_t + (end_t - start_t) / 2
        lon, _ = get_planet_pos(planet_name, mid_t)
        _, mid_nav_idx = get_navamsha_info(lon)
        
        if mid_nav_idx == start_nav_idx:
            start_t = mid_t
        else:
            end_t = mid_t
    return end_t

def calculate_single_planet_transits(planet_name, start_date, end_date):
    """Calculates highly accurate Navamsha transits for a single planet."""
    transits = []
    
    # Step size: 6 hours for most, 1 hour for Moon to catch quick changes
    step_hours = 1 if planet_name == "Moon" else 6 
    
    current_date = start_date
    lon, speed = get_planet_pos(planet_name, current_date)
    current_sign, current_nav_idx = get_navamsha_info(lon)
    entry_date = current_date
    current_motion = "Retrograde" if speed < 0 else "Direct"
    
    while current_date <= end_date:
        next_date = current_date + datetime.timedelta(hours=step_hours)
        if next_date > end_date:
            break
            
        next_lon, next_speed = get_planet_pos(planet_name, next_date)
        next_sign, next_nav_idx = get_navamsha_info(next_lon)
        next_motion = "Retrograde" if next_speed < 0 else "Direct"
        
        # If the Navamsha changes, find the exact minute
        if current_nav_idx != next_nav_idx:
            exact_transit_time = find_exact_transit_time(planet_name, current_date, next_date, current_nav_idx)
            
            duration = (exact_transit_time - entry_date).total_seconds() / 86400.0
            
            transits.append({
                "Planet": planet_name,
                "Navamsha Sign": current_sign,
                "Motion": current_motion,
                "Entry Datetime Obj": entry_date, # Hidden column for sorting
                "Entry Date": entry_date.strftime("%d %b %Y, %I:%M %p"),
                "Exit Date": exact_transit_time.strftime("%d %b %Y, %I:%M %p"),
                "Duration (Days)": round(duration, 2)
            })
            
            # Reset for the new Navamsha
            current_sign, current_nav_idx = next_sign, next_nav_idx
            entry_date = exact_transit_time
            current_motion = next_motion
            
        current_date = next_date
        
    # Append the final ongoing transit segment
    duration = (end_date - entry_date).total_seconds() / 86400.0
    transits.append({
        "Planet": planet_name,
        "Navamsha Sign": f"{current_sign} (Ongoing)",
        "Motion": current_motion,
        "Entry Datetime Obj": entry_date,
        "Entry Date": entry_date.strftime("%d %b %Y, %I:%M %p"),
        "Exit Date": end_date.strftime("%d %b %Y, %I:%M %p"),
        "Duration (Days)": round(duration, 2)
    })
    
    return transits

# --- Streamlit UI ---
st.title("🪐 Precision Navamsha Transit Timeline")
st.markdown("Select your dates and toggle planets below to view a combined, chronological timeline of exact Navamsha shifts (Lahiri Ayanamsa, Mumbai Time).")

# Layout: Date selection and duration
col1, col2 = st.columns(2)
with col1:
    selected_start_date = st.date_input("Select Start Date", datetime.date.today())
with col2:
    duration_options = {
        "1 Week": relativedelta(weeks=1),
        "2 Weeks": relativedelta(weeks=2),
        "3 Weeks": relativedelta(weeks=3),
        "1 Month": relativedelta(months=1),
        "3 Months": relativedelta(months=3),
        "6 Months": relativedelta(months=6),
        "1 Year": relativedelta(years=1)
    }
    selected_duration = st.selectbox("Select Timeline Duration", list(duration_options.keys()), index=3)

# Modern Filter Chips (Multiselect acts as interactive chips)
selected_planets = st.multiselect(
    "Select Planets to Track", 
    options=list(PLANETS.keys()), 
    default=["Sun", "Moon", "Saturn"] # Default selection
)

# Execution
if st.button("Generate Timeline Timeline"):
    if not selected_planets:
        st.warning("Please select at least one planet.")
    else:
        # Construct actual datetime boundaries
        start_datetime = IST.localize(datetime.datetime.combine(selected_start_date, datetime.time.min))
        end_datetime = start_datetime + duration_options[selected_duration]
        
        all_transits = []
        
        with st.spinner(f"Calculating highly precise transits..."):
            for planet in selected_planets:
                planet_transits = calculate_single_planet_transits(planet, start_datetime, end_datetime)
                all_transits.extend(planet_transits)
                
        # Convert to DataFrame
        df = pd.DataFrame(all_transits)
        
        if not df.empty:
            # Sort chronologically by the exact entry datetime
            df = df.sort_values(by="Entry Datetime Obj")
            
            # Drop the hidden datetime object column used for sorting
            df = df.drop(columns=["Entry Datetime Obj"])
            
            # Display results
            st.markdown(f"### Chronological Timeline: {start_datetime.strftime('%d %b %Y')} to {end_datetime.strftime('%d %b %Y')}")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Highlight special rules if Saturn is tracked
            if "Saturn" in selected_planets:
                st.info("**Saturn Note:** Saturn spends roughly 3-4 months in a Navamsha. If you see it going 'Retrograde', it may regress into a previous Navamsha sign before turning 'Direct' again.")
