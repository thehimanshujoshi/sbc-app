import streamlit as st
import swisseph as swe
from datetime import datetime, timedelta
import pytz

# ---------------------------------------------------------
# 1. EPHEMERIS SETUP & CONSTANTS
# ---------------------------------------------------------
# Set sidereal mode for Vedic Astrology (Lahiri Ayanamsa)
swe.set_sid_mode(swe.SIDM_LAHIRI)

IST = pytz.timezone('Asia/Kolkata')
# Coordinates for NSE/BSE (Mumbai)
LATITUDE = 18.9220
LONGITUDE = 72.8277

# SBC Alphabet Mapping (Example subset for Vedha hits)
SBC_ALPHABETS = {
    "Ta": ["TCS", "TATAMOTORS", "TATASTEEL"],
    "Ra": ["RELIANCE", "RAILTEL"],
    "In": ["INFY", "INDUSINDBK"]
}

# ---------------------------------------------------------
# 2. CORE ASTRONOMICAL FUNCTIONS
# ---------------------------------------------------------

def get_julian_day(dt):
    """Converts a timezone-aware datetime to Julian Day for Swisseph."""
    utc_dt = dt.astimezone(pytz.utc)
    return swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, 
                      utc_dt.hour + utc_dt.minute/60.0 + utc_dt.second/3600.0)

def get_planet_pos(jd, planet_id):
    """Returns sidereal longitude of a planet."""
    # swe.calc_ut returns (longitude, latitude, distance, speed in long, speed in lat, speed in dist)
    pos, _ = swe.calc_ut(jd, planet_id, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
    return pos[0]

def get_lagna(jd, lat, lon):
    """Calculates the transiting Ascendant (Lagna) degree."""
    # b'P' is Placidus house system; we just need the Ascendant (index 0)
    cusps, ascmc = swe.houses_ex(jd, lat, lon, b'P', swe.FLG_SIDEREAL)
    return ascmc[0]

def get_nakshatra_pada(longitude):
    """Calculates Nakshatra (0-26) and Pada (1-4) from a given longitude."""
    nak_length = 13.333333  # 13° 20'
    pada_length = 3.333333  # 3° 20'
    
    nak_index = int(longitude / nak_length)
    pada = int((longitude % nak_length) / pada_length) + 1
    return nak_index, pada

# ---------------------------------------------------------
# 3. TRADING DAY SCANNER (The Precision Engine)
# ---------------------------------------------------------

@st.cache_data(ttl=3600)
def scan_trading_day(date):
    """
    Scans the Indian trading day (9:15 AM to 3:30 PM) minute-by-minute 
    to pinpoint Lagna shifts, Pada changes, and exact degree alignments.
    """
    market_open = IST.localize(datetime.combine(date, datetime.strptime("09:15", "%H:%M").time()))
    market_close = IST.localize(datetime.combine(date, datetime.strptime("15:30", "%H:%M").time()))
    
    timeline = []
    current_time = market_open
    
    # Trackers for state changes
    prev_lagna_sign = None
    prev_pada = None
    
    while current_time <= market_close:
        jd = get_julian_day(current_time)
        
        # 1. Transiting Lagna (The "Minute Hand")
        lagna_deg = get_lagna(jd, LATITUDE, LONGITUDE)
        lagna_sign = int(lagna_deg / 30)
        
        # 2. Moon's Nakshatra Pada
        moon_deg = get_planet_pos(jd, swe.MOON)
        moon_nak, moon_pada = get_nakshatra_pada(moon_deg)
        
        # 3. Exact Degree Hits (Example: Mars)
        mars_deg = get_planet_pos(jd, swe.MARS)
        degree_diff = abs(moon_deg - mars_deg)
        sookshma_vedha = degree_diff < 0.05 # Mathematically aligned within ~3 arc-minutes
        
        # Record significant shifts
        event = None
        if prev_lagna_sign is not None and lagna_sign != prev_lagna_sign:
            event = f"LAGNA SHIFT to Sign {lagna_sign} (Look for 15-30 min volatility)"
            
        if prev_pada is not None and moon_pada != prev_pada:
            event = f"MOON PADA SHIFT to Pada {moon_pada} (High probability of Intraday Reversal)"
            
        if sookshma_vedha:
            event = "SOOKSHMA VEDHA: Exact Moon-Mars Alignment (Expect Sudden Price Action)"
            
        if event:
            timeline.append({
                "Time": current_time.strftime("%H:%M"),
                "Event": event,
                "Moon Degree": round(moon_deg, 2),
                "Lagna Degree": round(lagna_deg, 2)
            })
            
        prev_lagna_sign = lagna_sign
        prev_pada = moon_pada
        
        # Advance by 1 minute
        current_time += timedelta(minutes=1)
        
    return timeline

# ---------------------------------------------------------
# 4. STREAMLIT UI INTEGRATION
# ---------------------------------------------------------

st.title("SBC Intraday Precision Timer")

# Get today's date (or allow user selection)
selected_date = st.date_input("Select Trading Date", datetime.now(IST).date())

if st.button("Generate Intraday Timing Points"):
    with st.spinner("Calculating Ephemeris Data..."):
        events = scan_trading_day(selected_date)
        
        if events:
            st.subheader("Critical Intraday Reversal & Volatility Times")
            st.table(events)
            
            # Alphabet hit logic display
            st.markdown("### Stock Alphabet Hits (Swara/Varna)")
            st.info("Cross-reference the above times with your SBC grid for specific stocks:")
            for syllable, stocks in SBC_ALPHABETS.items():
                st.write(f"**{syllable}**: {', '.join(stocks)}")
        else:
            st.write("No major planetary shifts detected during market hours today.")
