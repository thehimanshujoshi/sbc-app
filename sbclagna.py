import streamlit as st
import pandas as pd
import swisseph as swe
from datetime import datetime, timedelta
import pytz

# ---------------------------------------------------------
# 1. SETUP & CONSTANTS
# ---------------------------------------------------------
# CRITICAL: Force built-in Moshier ephemeris to prevent cloud crashes
swe.set_ephe_path('') 
swe.set_sid_mode(swe.SIDM_LAHIRI)

IST = pytz.timezone('Asia/Kolkata')
LATITUDE = 18.9220  # Mumbai NSE/BSE
LONGITUDE = 72.8277

sbc_matrix = [
    ["A (Vowel)", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Aa (Vowel)"],
    ["Bharani", "Ta (TCS)", "Tha", "Da", "Dha", "Na", "Pa", "Pha", "Magha"],
    ["Ashwini", "Cha", "Vrshabha", "Mithuna", "Karka", "Simha", "Kanya", "Ba (Bajaj)", "Purva Phalguni"],
    ["Revati", "Kha", "Mesha", "O (Vowel)", "U (Vowel)", "I (Vowel)", "Tula", "Bha", "Uttara Phalguni"],
    ["Uttara Bhadrapada", "Ka", "Meena", "Au (Vowel)", "Brahma", "Ae (Vowel)", "Vrishchika", "Ma (M&M)", "Hasta"],
    ["Purva Bhadrapada", "Ha", "Kumbha", "Am (Vowel)", "Ah (Vowel)", "E (Vowel)", "Dhanu", "Ya", "Chitra"],
    ["Shatabhisha", "Sa (SBI)", "Makara", "Ra (Reliance)", "La", "Va", "Sha", "Ra", "Swati"],
    ["Dhanishta", "Gha", "Ga", "Ccha", "Ca", "Nga", "Jha", "Ja", "Vishakha"],
    ["Uu (Vowel)", "Shravana", "Abhijit", "Uttara Ashadha", "Purva Ashadha", "Mula", "Jyeshtha", "Anuradha", "Ii (Vowel)"]
]

def build_coord_map(matrix):
    coords = {}
    for r in range(9):
        for c in range(9):
            element = matrix[r][c]
            base = element.split(" ")[0]
            coords[base] = (r, c)
            coords[element] = (r, c)
    return coords

SBC_COORDS = build_coord_map(sbc_matrix)

# ---------------------------------------------------------
# 2. CORE ASTRONOMY ENGINE
# ---------------------------------------------------------
def get_julian_day(dt):
    utc_dt = dt.astimezone(pytz.utc)
    return swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, 
                      utc_dt.hour + utc_dt.minute/60.0 + utc_dt.second/3600.0)

def get_planet_pos(jd, planet_id):
    # FLG_MOSEPH prevents the black screen crash
    pos, _ = swe.calc_ut(jd, planet_id, swe.FLG_MOSEPH | swe.FLG_SIDEREAL)
    return pos[0]

def get_lagna(jd, lat, lon):
    cusps, ascmc = swe.houses_ex(jd, lat, lon, b'P', swe.FLG_SIDEREAL)
    return ascmc[0]

def get_nakshatra_pada(longitude):
    nak_length = 13.333333
    pada_length = 3.333333
    nak_index = int(longitude / nak_length)
    pada = int((longitude % nak_length) / pada_length) + 1
    return nak_index, pada

# ---------------------------------------------------------
# 3. TRADING SCANNER
# ---------------------------------------------------------
def scan_trading_day(date):
    market_open = IST.localize(datetime.combine(date, datetime.strptime("09:15", "%H:%M").time()))
    market_close = IST.localize(datetime.combine(date, datetime.strptime("15:30", "%H:%M").time()))
    
    timeline = []
    current_time = market_open
    prev_lagna_sign, prev_pada = None, None
    
    # Cap the loop to prevent infinite freezing
    max_iterations = 400 
    loops = 0

    while current_time <= market_close and loops < max_iterations:
        loops += 1
        jd = get_julian_day(current_time)
        
        lagna_deg = get_lagna(jd, LATITUDE, LONGITUDE)
        lagna_sign = int(lagna_deg / 30)
        
        moon_deg = get_planet_pos(jd, swe.MOON)
        moon_nak, moon_pada = get_nakshatra_pada(moon_deg)
        
        mars_deg = get_planet_pos(jd, swe.MARS)
        sookshma_vedha = abs(moon_deg - mars_deg) < 0.05
        
        event = None
        if prev_lagna_sign is not None and lagna_sign != prev_lagna_sign:
            event = f"LAGNA SHIFT to Sign {lagna_sign} (15-30 min volatility)"
        if prev_pada is not None and moon_pada != prev_pada:
            event = f"MOON PADA SHIFT to Pada {moon_pada} (Intraday Reversal Risk)"
        if sookshma_vedha:
            event = "SOOKSHMA VEDHA: Moon-Mars Alignment"
            
        if event:
            timeline.append({
                "Time": current_time.strftime("%H:%M"),
                "Event": event,
                "Moon Deg": round(moon_deg, 2),
                "Lagna Deg": round(lagna_deg, 2)
            })
            
        prev_lagna_sign, prev_pada = lagna_sign, moon_pada
        current_time += timedelta(minutes=1)
        
    return timeline

# ---------------------------------------------------------
# 4. STREAMLIT FRONTEND
# ---------------------------------------------------------
st.set_page_config(page_title="SBC Intraday", layout="wide")
st.title("SBC Intraday Precision Timer")

selected_date = st.date_input("Select Trading Date", datetime.now(IST).date())

if st.button("Generate Timing Points"):
    with st.spinner("Calculating Ephemeris..."):
        events = scan_trading_day(selected_date)
        if events:
            st.table(events)
        else:
            st.write("No major shifts during market hours.")

st.divider()
st.subheader("Current SBC Grid")
st.dataframe(pd.DataFrame(sbc_matrix), use_container_width=True)
