import streamlit as st
import swisseph as swe
import pandas as pd
import datetime
import pytz

# Configure Streamlit page layout
st.set_page_config(page_title="Navamsha Transit Tracker", layout="wide")

# --- Constants and Setup ---
# Zodiac signs for mapping
ZODIAC_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

# Map planet names to Swiss Ephemeris constants
PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Rahu": swe.MEAN_NODE, # Mean North Node
    "Ketu": "KETU"         # Calculated as exactly opposite to Rahu
}

def get_navamsha_sign(longitude):
    """Calculate the Navamsha (D9) sign based on sidereal longitude."""
    # 108 Navamshas in 360 degrees (3 degrees 20 minutes each)
    navamsha_index = int(longitude / (360.0 / 108.0))
    sign_index = navamsha_index % 12
    return ZODIAC_SIGNS[sign_index]

def calculate_transits(planet_name, year):
    """Calculate Navamsha transits for a given planet and year."""
    # Set Ayanamsa to Lahiri
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    
    # Setup timezone for Mumbai, India
    ist = pytz.timezone('Asia/Kolkata')
    
    start_date = datetime.datetime(year, 1, 1, 0, 0, 0)
    end_date = datetime.datetime(year, 12, 31, 23, 59, 59)
    
    # We will step through the year day by day (using 0.5 day steps for better precision)
    current_date = start_date
    step_hours = 12 
    if planet_name == "Moon":
        step_hours = 2 # Moon moves very fast, needs higher resolution
        
    transits = []
    current_navamsha = None
    entry_date = None
    current_motion = None # 'Direct' or 'Retrograde'
    
    while current_date <= end_date:
        # Convert date to UTC for Swiss Ephemeris
        utc_date = ist.localize(current_date).astimezone(pytz.utc)
        
        # Calculate Julian Day
        jd = swe.julday(utc_date.year, utc_date.month, utc_date.day, 
                        utc_date.hour + utc_date.minute/60.0)
        
        # Calculate Planet Position
        if planet_name == "Ketu":
            # Ketu is exactly 180 degrees from Rahu
            pos, ret = swe.calc_ut(jd, PLANETS["Rahu"], swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
            longitude = (pos[0] + 180.0) % 360.0
            speed = pos[3] # Speed remains the same magnitude
        else:
            pos, ret = swe.calc_ut(jd, PLANETS[planet_name], swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
            longitude = pos[0]
            speed = pos[3]
            
        navamsha_sign = get_navamsha_sign(longitude)
        
        # Determine Retrograde status (Nodes are always considered retrograde in general practice, 
        # but true/mean node speed can fluctuate. We'll use speed < 0)
        motion = "Retrograde" if speed < 0 else "Direct"
        
        # Check for change in sign or retrograde status
        if current_navamsha != navamsha_sign:
            if current_navamsha is not None:
                duration = (current_date - entry_date).days + ((current_date - entry_date).seconds / 86400.0)
                transits.append({
                    "Navamsha Sign": current_navamsha,
                    "Motion": current_motion,
                    "Entry Date": entry_date.strftime("%d %b %Y, %H:%M IST"),
                    "Exit Date": current_date.strftime("%d %b %Y, %H:%M IST"),
                    "Duration (Days)": round(duration, 2)
                })
            
            current_navamsha = navamsha_sign
            current_motion = motion
            entry_date = current_date
            
        current_date += datetime.timedelta(hours=step_hours)
        
    # Append the last ongoing transit till the end of the year
    if current_navamsha is not None:
        duration = (end_date - entry_date).days + ((end_date - entry_date).seconds / 86400.0)
        transits.append({
            "Navamsha Sign": f"{current_navamsha} (Ongoing)",
            "Motion": current_motion,
            "Entry Date": entry_date.strftime("%d %b %Y, %H:%M IST"),
            "Exit Date": "End of Year",
            "Duration (Days)": round(duration, 2)
        })
        
    return pd.DataFrame(transits)

# --- Streamlit UI ---
st.title("🪐 Vedic Astrology: Navamsha Transit Generator")
st.markdown("Generates a detailed tabular list of a planet's Navamsha (D9) transits for a given year using Lahiri Ayanamsa. Calculations are based on Mumbai, India (IST).")

# Sidebar inputs
st.sidebar.header("Transit Parameters")
selected_planet = st.sidebar.selectbox("Select Planet", list(PLANETS.keys()), index=6) # Default to Saturn
selected_year = st.sidebar.number_input("Enter Year", min_value=1900, max_value=2100, value=2026)

if st.sidebar.button("Generate Transits"):
    with st.spinner(f"Calculating {selected_planet} Navamsha transits for {selected_year}..."):
        df_transits = calculate_transits(selected_planet, selected_year)
        
        st.subheader(f"Results for {selected_planet} in {selected_year}")
        
        # Display as a modern dataframe
        st.dataframe(df_transits, use_container_width=True, hide_index=True)
        
        # Special Information Section for Saturn
        if selected_planet == "Saturn":
            st.markdown("---")
            st.subheader("🪐 Note on Saturn's Retrograde and Navamsha Stay")
            st.info("""
            **How Retrograde Affects Saturn's Navamsha Stay:**
            * **Extended Duration:** Saturn is the slowest moving traditional planet, spending roughly 2.5 years in a core zodiac sign. In a Navamsha (a 3°20' slice), it typically spends about **3 to 4 months** while in direct motion.
            * **Re-entry:** When Saturn goes **Retrograde (Vakra)**, its apparent motion reverses. If retrograde happens near the border of a Navamsha, Saturn will exit its current Navamsha, slide back into the previous one, and stay there for several months before turning direct and re-entering the subsequent Navamsha. 
            * **Intense Results:** Astrologically, a retrograde Saturn in a specific Navamsha delays core themes associated with that D9 sign and forces a re-evaluation of its karmic lessons. You can identify these phases in the table above by looking for the "Retrograde" label in the Motion column.
            """)
