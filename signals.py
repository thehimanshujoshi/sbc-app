import streamlit as st
import pandas as pd
import swisseph as swe
import math
from datetime import datetime, timedelta

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Astro-Gann Intraday System",
    page_icon="⚡",
    layout="wide"
)

# ==========================================
# CONSTANTS & ASTRO CONFIG
# ==========================================
MUMBAI_LAT = 18.9229
MUMBAI_LON = 72.8343

# Set Swiss Ephemeris to Sidereal Mode (Vedic) using Lahiri Ayanamsa
swe.set_sid_mode(swe.SIDM_LAHIRI)

ASPECTS = [0, 30, 45, 60, 90, 120, 135, 150, 180]
ORB = 0.25  # Tight margin for exact minute interception

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", 
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", 
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", 
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", 
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

# ==========================================
# CORE ASTRO & GANN FUNCTIONS
# ==========================================
def calculate_gann_square_of_9(price):
    """Calculates exact Support & Resistance using Gann Math"""
    if price <= 0:
        return [], []
    root = math.sqrt(price)
    resistances = [round((root + i*0.125)**2, 2) for i in range(1, 5)]
    supports = [round((root - i*0.125)**2, 2) for i in range(1, 5)]
    return sorted(supports), sorted(resistances)

def get_julian_day(dt_utc):
    """Converts UTC datetime to Julian Day for Swiss Ephemeris"""
    year, month, day = dt_utc.year, dt_utc.month, dt_utc.day
    hour_float = dt_utc.hour + (dt_utc.minute / 60.0) + (dt_utc.second / 3600.0)
    return swe.julday(year, month, day, hour_float)

def get_vedic_panchang(dt_utc):
    """Calculates the Vedic Tithi and Nakshatra for the day"""
    jd = get_julian_day(dt_utc)
    
    # Calculate Sidereal Moon & Sun
    moon_data, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL)
    sun_data, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SIDEREAL)
    
    moon_lon = moon_data[0]
    sun_lon = sun_data[0]
    
    # Nakshatra (13 degrees 20 mins per Nakshatra)
    nakshatra_idx = int(moon_lon / 13.3333)
    nakshatra = NAKSHATRAS[nakshatra_idx]
    
    # Tithi (12 degrees per Tithi)
    tithi_angle = (moon_lon - sun_lon) % 360
    tithi = int(tithi_angle / 12) + 1
    
    return nakshatra, tithi

def get_exact_vedic_positions(datetime_ist):
    """Calculates exact Sidereal Lagna, Moon, and Sun for Mumbai"""
    dt_utc = datetime_ist - timedelta(hours=5, minutes=30)
    jd = get_julian_day(dt_utc)
    
    # Lagna (Ascendant) using Placidus house system & Sidereal flag
    cusps, ascmc = swe.houses_ex(jd, MUMBAI_LAT, MUMBAI_LON, b'P', swe.FLG_SIDEREAL)
    lagna_lon = ascmc[0] 
    
    # Moon & Sun
    moon_data, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL)
    sun_data, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SIDEREAL)
    
    return lagna_lon, moon_data[0], sun_data[0]

def check_micro_timing(datetime_ist):
    """Checks if Mumbai Lagna aspects Moon or Sun"""
    lagna_lon, moon_lon, sun_lon = get_exact_vedic_positions(datetime_ist)
    
    # Check Lagna vs Moon
    diff_moon = min(abs(lagna_lon - moon_lon), 360 - abs(lagna_lon - moon_lon))
    for aspect in ASPECTS:
        if abs(diff_moon - aspect) <= ORB:
            action = "LONG (Buy)" if aspect in [60, 120] else "SHORT (Sell)" if aspect in [90, 180] else "VOLATILITY / BREAKOUT"
            return f"Lagna {aspect}° Moon", action, "⭐⭐⭐⭐"
            
    # Check Lagna vs Sun
    diff_sun = min(abs(lagna_lon - sun_lon), 360 - abs(lagna_lon - sun_lon))
    for aspect in ASPECTS:
        if abs(diff_sun - aspect) <= ORB:
            action = "LONG (Buy)" if aspect in [60, 120] else "SHORT (Sell)" if aspect in [90, 180] else "REVERSAL"
            return f"Lagna {aspect}° Sun", action, "⭐⭐⭐⭐⭐"
            
    return None

# ==========================================
# STREAMLIT UI DESIGN
# ==========================================
st.title("⚡ Institutional Astro-Gann Trading System")
st.markdown("""
This quantitative tool blends **Swiss Ephemeris Micro-Timings (Mumbai Coordinates)** with **W.D. Gann Square of 9 Price Levels** to pinpoint exact intraday market reversals.
""")

# Sidebar Inputs
st.sidebar.header("📊 Trade Parameters")
selected_date = st.sidebar.date_input("Select Trading Date:", datetime.today().date())
opening_price = st.sidebar.number_input("Nifty Opening Price (at 09:15 AM):", min_value=0.0, value=24000.00, step=10.0)
generate_btn = st.sidebar.button("Generate Trading Plan", type="primary")

st.sidebar.markdown("---")
st.sidebar.info("""
**How to use:**
1. Wait for the exact time generated.
2. Check if the price is reacting near a Gann Support/Resistance line.
3. Trade the breakout/reversal with a tight stop-loss.
""")

# Main Execution Logic
if generate_btn:
    st.markdown("---")
    
    # 1. Calculate & Display Panchang Sentiment
    market_open_ist = datetime.combine(selected_date, datetime.strptime("09:15", "%H:%M").time())
    dt_utc_open = market_open_ist - timedelta(hours=5, minutes=30)
    nakshatra, tithi = get_vedic_panchang(dt_utc_open)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🕉️ Daily Vedic Sentiment")
        st.write(f"**Lunar Tithi:** {tithi}")
        st.write(f"**Nakshatra:** {nakshatra}")
        if nakshatra in ["Krittika", "Ashlesha", "Ardra", "Jyeshtha", "Mula"]:
            st.warning("⚠️ Volatile/Aggressive Nakshatra detected today. Expect fake-outs and sharp spikes.")
        else:
            st.success("✅ Stable Nakshatra. Standard trend following expected.")
            
    # 2. Calculate & Display Gann Levels
    with col2:
        st.subheader("🎯 Gann Square of 9 Levels")
        supports, resistances = calculate_gann_square_of_9(opening_price)
        st.write(f"**Calculated from Open:** `{opening_price}`")
        st.write(f"🟢 **Resistances (R1 to R4):** {', '.join([str(x) for x in resistances])}")
        st.write(f"🔴 **Supports (S1 to S4):** {', '.join([str(x) for x in supports])}")

    st.markdown("---")
    st.subheader("⏱️ Mumbai Micro-Timing Schedule")
    
    # 3. Generate Minute-by-Minute Schedule
    with st.spinner("Calculating celestial horizon geometry..."):
        market_close_ist = datetime.combine(selected_date, datetime.strptime("15:30", "%H:%M").time())
        current_time = market_open_ist
        
        results = []
        last_trigger_time = None
        
        while current_time <= market_close_ist:
            trigger = check_micro_timing(current_time)
            if trigger:
                # 12 min cooldown
                if last_trigger_time is None or (current_time - last_trigger_time).seconds > 720:
                    results.append({
                        'Time (IST)': current_time.strftime('%I:%M %p'),
                        'Signal Type': trigger[0],
                        'Expected Action': trigger[1],
                        'Strength': trigger[2]
                    })
                    last_trigger_time = current_time
            current_time += timedelta(minutes=1)

        # Display Dataframe
        if results:
            df = pd.DataFrame(results)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No major Astro-Lagna timing alignments detected during market hours today.")
            
    st.markdown("---")
    st.caption("Powered by `pyswisseph` NASA Jet Propulsion ephemeris. Timings adjusted accurately for Mumbai Stock Exchange local horizon.")
