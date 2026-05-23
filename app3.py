import streamlit as st
import pandas as pd
import datetime
import pytz
import math

# Load Libraries Safely
try:
    import swisseph as swe
except ImportError:
    st.error("⚠️ 'pyswisseph' is missing. Please update requirements.txt on GitHub!")
    st.stop()
try:
    from fpdf import FPDF
except ImportError:
    st.error("⚠️ 'fpdf' is missing. Please update requirements.txt on GitHub!")
    st.stop()

st.set_page_config(page_title="SBC Astro Engine", page_icon="🕉️", layout="wide")
swe.set_sid_mode(swe.SIDM_LAHIRI) # Strict Lahiri Ayanamsa

# --- Session State Initialization ---
if "target_date" not in st.session_state:
    st.session_state.target_date = datetime.date.today()

# --- Dictionaries & Data ---
RASHIS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

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
    "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE 
}
BENEFICS = ["Moon", "Mercury", "Jupiter", "Venus"]
MALEFICS = ["Sun", "Mars", "Saturn", "Rahu", "KETU"]

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
# Planetary Advisories (Remedies & Enhancements)
ADVISORY_DB = {
    "Sun": {
        "type": "Malefic",
        "health": "High risk of fever, eye strain, or blood pressure issues. Avoid prolonged sun exposure and stay hydrated.",
        "wealth": "Avoid arguments with superiors, bosses, or government officials. Delay filing taxes or important govt paperwork if possible.",
        "spiritual": "Offer Arghya (water) to Lord Surya in the morning. Chant the Gayatri Mantra or Aditya Hrudayam Stotram."
    },
    "Mars": {
        "type": "Malefic",
        "health": "Risk of cuts, burns, inflammation, or sudden accidents. Drive cautiously and avoid impulsive physical risks.",
        "wealth": "Strictly avoid impulsive trades, heavy speculation, or real estate disputes. Temper will cause financial loss.",
        "spiritual": "Recite Hanuman Chalisa. Donate red lentils (masoor dal) or offer sweet roti to stray dogs."
    },
    "Saturn": {
        "type": "Malefic",
        "health": "Lethargy, joint pains, or flare-ups of chronic diseases. Ensure adequate rest and avoid heavy physical exertion.",
        "wealth": "Expect delays in execution or blockages in deals. Strictly stick to long-term budgeting and avoid machinery/oil sector stocks.",
        "spiritual": "Light a mustard oil lamp under a Peepal tree after sunset. Chant 'Om Sham Shanaishcharaye Namah'."
    },
    "Rahu": {
        "type": "Malefic",
        "health": "Anxiety, misdiagnosis, food poisoning, or sleep disturbances. Stick to home-cooked food.",
        "wealth": "High chances of getting scammed or trapped in crypto/speculative illusions. Do not trust sudden 'get-rich-quick' schemes today.",
        "spiritual": "Chant Durga Saptashati or Bhairav Chalisa. Feed black dogs or donate black sesame seeds."
    },
    "KETU": {
        "type": "Malefic",
        "health": "Unexplained aches, viral infections, or feelings of detachment/depression. Avoid over-medicating.",
        "wealth": "Apathy towards market portfolio. Keep away from micro-cap/pharma volatile trades to prevent unseen losses.",
        "spiritual": "Worship Lord Ganesha. Donate multi-colored blankets or feed street dogs. Excellent day for deep meditation."
    },
    "Moon": {
        "type": "Benefic",
        "wealth": "Excellent energy for quick trades in FMCG, shipping, or liquid assets. Mind is calm and intuitive for financial decisions.",
        "spiritual": "Meditate near water bodies. Worship Lord Shiva (offer milk on Shivling) and show respect to motherly figures."
    },
    "Mercury": {
        "type": "Benefic",
        "wealth": "Perfect timing for signing contracts, business meetings, networking, and trading in IT/Banking sectors. Communication is your asset today.",
        "spiritual": "Chant Vishnu Sahasranama or 'Om Bum Buddhaya Namah'. Feed green grass/spinach to cows."
    },
    "Jupiter": {
        "type": "Benefic",
        "wealth": "Highly auspicious for long-term investments, banking, and buying gold. Expansion and divine grace protect your assets.",
        "spiritual": "Visit a temple, read scriptures, or listen to spiritual discourses. Respect your Gurus and donate yellow sweets/chana dal."
    },
    "Venus": {
        "type": "Benefic",
        "wealth": "Auspicious for luxury sectors, auto, textiles, and entertainment. Good day for purchasing vehicles or enjoying financial comforts.",
        "spiritual": "Worship Goddess Lakshmi or Durga. Wear clean, perfumed clothes to attract positive aura. Donate white sweets."
    }
}
# --- Core Math ---
def jd_to_date_str(jd, tz_str="Asia/Kolkata"):
    y, m, d, h = swe.revjul(jd, swe.GREG_CAL)
    h_int = int(h)
    m_int = int((h - h_int) * 60)
    s_int = int((((h - h_int) * 60) - m_int) * 60)
    dt_utc = datetime.datetime(y, m, d, h_int, m_int, s_int, tzinfo=pytz.utc)
    dt_loc = dt_utc.astimezone(pytz.timezone(tz_str))
    return dt_loc.strftime("%d %b %y, %I:%M %p")

def get_sbc_nakshatra(lon):
    if 276.6667 <= lon < 280.8889: return "Abhijit", 21
    elif lon >= 280.8889: return SBC_NAKSHATRAS[math.floor(lon / 13.333333) + 1], math.floor(lon / 13.333333) + 1
    else: return SBC_NAKSHATRAS[math.floor(lon / 13.333333)], math.floor(lon / 13.333333)

def get_nak_boundaries(lon):
    if 276.6667 <= lon < 280.8889:
        return 276.6667, 280.8889
    elif lon >= 280.8889:
        idx = math.floor(lon / 13.333333)
        return max(280.8889, idx * 13.333333), (idx + 1) * 13.333333
    else:
        idx = math.floor(lon / 13.333333)
        return idx * 13.333333, min(276.6667, (idx + 1) * 13.333333)

def get_rashi_and_navamsha(lon):
    rashi_idx = math.floor(lon / 30)
    navamsha_idx = math.floor(lon / 3.33333333) % 12
    return RASHIS[rashi_idx], RASHIS[navamsha_idx]

def get_planet_data(jd, planet_id):
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    if planet_id == "KETU":
        pos, _ = swe.calc_ut(jd, swe.MEAN_NODE, flags)
        return (pos[0] + 180.0) % 360.0, pos[3] 
    else:
        pos, _ = swe.calc_ut(jd, planet_id, flags)
        return pos[0], pos[3]

def get_transit_dates(jd, p_name, tz_str="Asia/Kolkata"):
    p_id = PLANETS[p_name] if p_name != "KETU" else "KETU"
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    def get_l(t):
        if p_id == "KETU":
            pos, _ = swe.calc_ut(t, swe.MEAN_NODE, flags)
            return (pos[0] + 180.0) % 360.0
        else:
            pos, _ = swe.calc_ut(t, p_id, flags)
            return pos[0]
    
    start_bound, end_bound = get_nak_boundaries(get_l(jd))
    def in_bnd(t): return start_bound <= get_l(t) < end_bound

    e_jd, x_jd = jd, jd
    for _ in range(1500):
        e_jd -= 1.0
        if not in_bnd(e_jd): break
    for _ in range(25):
        e_jd += 0.04166
        if in_bnd(e_jd): break
        
    for _ in range(1500):
        x_jd += 1.0
        if not in_bnd(x_jd): break
    for _ in range(25):
        x_jd -= 0.04166
        if in_bnd(x_jd): break
        
    return jd_to_date_str(e_jd, tz_str), jd_to_date_str(x_jd, tz_str)

def get_vedha_type(speed, planet_name):
    if planet_name in ["Rahu", "KETU"]: return "Right (Retrograde)" 
    elif planet_name in ["Sun", "Moon"]: return "Left (Direct)" 
    elif speed < 0: return "Right (Retrograde)"
    elif 0 < speed < 0.2: return "Frontal (Stationary)"
    else: return "Left (Direct)"

def calculate_snapshot(jd, native_n_idx, target_nak):
    data = []
    total_score = 50 
    planet_keys = list(PLANETS.keys()) + ["KETU"]
    for p_name in planet_keys:
        p_id = PLANETS[p_name] if p_name != "KETU" else "KETU"
        lon, speed = get_planet_data(jd, p_id)
        
        transiting_nak, transiting_idx = get_sbc_nakshatra(lon)
        rashi, navamsha = get_rashi_and_navamsha(lon)
        
        vedha_dir = get_vedha_type(speed, p_name)
        distance = (transiting_idx - native_n_idx + 28) % 28
        
        is_benefic = p_name in BENEFICS
        sign = 1 if is_benefic else -1
        
        impact_text, score_impact, bg_color = "No Vedha", 0, "" 
        
        if distance == 14: 
            impact_text, score_impact = "🔥 FRONTAL VEDHA", 15 * sign
            bg_color = "background-color: #D1FAE5; color: #065F46;" if is_benefic else "background-color: #FEE2E2; color: #991B1B;"
        elif distance == 0:
            impact_text, score_impact = "⚡ DIRECT CONJUNCTION", 20 * sign
            bg_color = "background-color: #A7F3D0; color: #065F46;" if is_benefic else "background-color: #FECACA; color: #991B1B;"
        elif distance in [1, 27]:
            impact_text, score_impact = f"⚠️ ADJACENT", 10 * sign
            bg_color = "background-color: #ECFDF5; color: #047857;" if is_benefic else "background-color: #FFF7ED; color: #C2410C;"
        
        total_score += score_impact
        score_disp = f"+{score_impact}%" if score_impact > 0 else f"{score_impact}%" if score_impact < 0 else "-"
        
        action_text = f"Casting {vedha_dir} onto {target_nak}" if impact_text != "No Vedha" else "Safe Distance"
        position_text = f"{transiting_nak} Nakshatra\n{rashi} Rashi | {navamsha} Navamsha"
        
        start_lon, end_lon = get_nak_boundaries(lon)
        span = end_lon - start_lon
        prog = 50
        if span > 0:
            prog = ((lon - start_lon) / span) * 100
            if speed < 0 or p_name in ["Rahu", "KETU"]:
                prog = 100 - prog
            prog = max(0, min(100, int(prog)))
        
        data.append({
            "Planet & Nature": f"{p_name}\n({('Benefic' if is_benefic else 'Malefic')})",
            "Current Position": position_text,
            "Action on You": action_text,
            "Impact & Score": f"{impact_text} ({score_disp})",
            "_bg": bg_color,
            "raw_planet": p_name,
            "is_benefic": is_benefic,
            "is_hit": impact_text != "No Vedha",
            "progress": prog
        })
    return max(0, min(100, total_score)), data
def get_market_intel(data):
    pos, neg = [], []
    for d in data:
        if not d['is_hit']: continue
        p = d['raw_planet']
        
        if p == "Sun": sec = "PSU Stocks, Govt Bonds, Pharma, Gold"
        elif p == "Moon": sec = "FMCG, Shipping, Liquids, Silver"
        elif p == "Mars": sec = "Real Estate, Defense, Copper, Heavy Metals"
        elif p == "Mercury": sec = "IT, Telecom, Banking, Green Tech"
        elif p == "Jupiter": sec = "Finance, Banks, Education, Yellow Metals"
        elif p == "Venus": sec = "Auto, Luxury, Entertainment, Textiles"
        elif p == "Saturn": sec = "Oil & Gas, Coal, Steel, Heavy Machinery"
        elif p == "Rahu": sec = "AI, Crypto, Tech, Foreign Equities"
        elif p == "KETU": sec = "Biotech, Niche Pharma, Micro-Tech"
        else: sec = "General Market"

        if d['is_benefic']: pos.append(f"- {p}: FAVORABLE for {sec}")
        else: neg.append(f"- {p}: HIGHLY VOLATILE / AVOID {sec}")
        
    res = "--- SECTORS FAVORABLE FOR YOU TODAY ---\n"
    res += "\n".join(pos) if pos else "No major benefic alignments protecting specific sectors for you today."
    res += "\n\n--- SECTORS TO AVOID / VOLATILE FOR YOU ---\n"
    res += "\n".join(neg) if neg else "No major malefic threats to specific sectors for you today."
    return res

def display_advisory(data, current_jd, tz_str="Asia/Kolkata"):
    hits = [d for d in data if d['is_hit']]
    if not hits: return
    
    st.markdown("### 🛡️ Astrological Advisory & Remedies")
    for hit in hits:
        p_name = hit['raw_planet']
        adv = ADVISORY_DB.get(p_name)
        if not adv: continue
        
        prog = hit.get('progress', 50)
        rem = 100 - prog
        entry_dt, exit_dt = get_transit_dates(current_jd, p_name, tz_str)
        
        if adv["type"] == "Malefic":
            st.error(f"**🔴 {p_name} is impacting you negatively ({hit['Impact & Score'].split('(')[0].strip()})**")
            st.markdown(f"""
            <div style="margin-top: -10px; margin-bottom: 15px; padding: 0 10px;">
                <div style="display: flex; justify-content: space-between; font-size: 13px; color: #991B1B; font-weight: 600; margin-bottom: 5px;">
                    <span style="text-align: left;">⏳ Elapsed: {prog}%<br><span style="font-size: 11px; font-weight: normal; color: #B91C1C;">Entered: {entry_dt}</span></span>
                    <span style="text-align: right;">Remaining: {rem}% ⌛<br><span style="font-size: 11px; font-weight: normal; color: #B91C1C;">Exits: {exit_dt}</span></span>
                </div>
                <div style="background-color: #FEE2E2; border-radius: 5px; height: 8px; width: 100%; border: 1px solid #FCA5A5; overflow: hidden;">
                    <div style="background-color: #DC2626; width: {prog}%; height: 100%;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"- **Health:** {adv['health']}")
            st.markdown(f"- **Wealth/Actions:** {adv['wealth']}")
            st.markdown(f"- **Spiritual Remedy:** {adv['spiritual']}")
        else:
            st.success(f"**🟢 {p_name} is blessing you ({hit['Impact & Score'].split('(')[0].strip()})**")
            st.markdown(f"""
            <div style="margin-top: -10px; margin-bottom: 15px; padding: 0 10px;">
                <div style="display: flex; justify-content: space-between; font-size: 13px; color: #065F46; font-weight: 600; margin-bottom: 5px;">
                    <span style="text-align: left;">⏳ Elapsed: {prog}%<br><span style="font-size: 11px; font-weight: normal; color: #047857;">Entered: {entry_dt}</span></span>
                    <span style="text-align: right;">Remaining: {rem}% ⌛<br><span style="font-size: 11px; font-weight: normal; color: #047857;">Exits: {exit_dt}</span></span>
                </div>
                <div style="background-color: #D1FAE5; border-radius: 5px; height: 8px; width: 100%; border: 1px solid #6EE7B7; overflow: hidden;">
                    <div style="background-color: #059669; width: {prog}%; height: 100%;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"- **Wealth/Actions (To Maximize):** {adv['wealth']}")
            st.markdown(f"- **Spiritual Enhancement:** {adv['spiritual']}")

def clean(text): return text.replace('\n', ' ').encode('ascii', 'ignore').decode('ascii')

def generate_pdf(nak, pada, date_str, score, data, intel, is_long_term=False, chart_desc="", trend_data=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    title = "SBC Long-Term Forecast" if is_long_term else "SBC Daily Analysis"
    pdf.cell(200, 10, txt=clean(title), ln=True, align='C')
    
    pdf.set_font("Arial", size=12)
    pdf.ln(5)
    pdf.cell(200, 8, txt=clean(f"Native Profile: {nak} (Pada {pada})"), ln=True)
    pdf.cell(200, 8, txt=clean(f"Date/Range: {date_str}"), ln=True)
    pdf.cell(200, 8, txt=clean(f"Conclusive Energy Score: {score}%"), ln=True)
    
    if is_long_term:
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 8, txt=clean("Trend Summary:"), ln=True)
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 8, txt=clean(chart_desc))
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 8, txt=clean("Share Market & Sector Analysis:"), ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 7, txt=clean(intel))
    
    if not is_long_term:
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 8, txt=clean("Detailed Planetary Strikes (Vedhas):"), ln=True)
        pdf.set_font("Arial", size=9)
        for d in data:
            if d['is_hit']:
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(200, 6, txt=clean(f"[{d['Impact & Score']}] {d['Planet & Nature']} is {d['Action on You']}"), ln=True, fill=True)
                pdf.cell(200, 6, txt=clean(f"     Location: {d['Current Position']}"), ln=True)
                pdf.ln(2)
    else:
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 8, txt=clean("Daily Energy Breakdown:"), ln=True)
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(95, 8, "Date", border=1, fill=True)
        pdf.cell(95, 8, "Energy Score", border=1, fill=True)
        pdf.ln()
        
        pdf.set_font("Arial", size=10)
        if trend_data:
            for td in trend_data:
                pdf.cell(95, 8, txt=clean(td['Date'].strftime("%d %B %Y")), border=1)
                pdf.cell(95, 8, txt=clean(f"{td['Score']}%"), border=1)
                pdf.ln()

    return pdf.output(dest='S').encode('latin-1')
# --- UI Setup ---
st.title("🕉️ Sarvatobhadra Chakra (SBC) Engine")
st.markdown("Strict Lahiri Ayanamsa • Stock Market Forecasting • 9-Planet Vedha")

# --- SIDEBAR ---
st.sidebar.header("👤 1. Subject Profile")

profile_choice = st.sidebar.radio("Select Profile:", ["INDEX (Mrigashira 2)", "Me (Revati 3)", "Custom Profile"], index=0)

if profile_choice == "INDEX (Mrigashira 2)":
    target_nak, target_pada = "Mrigashira", 2
    native_n_idx = SBC_NAKSHATRAS.index(target_nak)
    st.sidebar.success(f"**Active Profile:** INDEX")
elif profile_choice == "Me (Revati 3)":
    target_nak, target_pada = "Revati", 3
    native_n_idx = SBC_NAKSHATRAS.index(target_nak)
    st.sidebar.success(f"**Active Profile:** Me")
else:
    profile_type = st.sidebar.radio("Target by:", ["First Name Syllable", "Birth Nakshatra"])
    if profile_type == "First Name Syllable":
        syllable = st.sidebar.selectbox("First Sound of Name", list(AKSHARA_MAP.keys()))
        target_nak, target_pada = AKSHARA_MAP[syllable]
        native_n_idx = SBC_NAKSHATRAS.index(target_nak)
        st.sidebar.success(f"**Mapped:** {target_nak} (Pada {target_pada})")
    else:
        target_nak = st.sidebar.selectbox("Select Nakshatra", SBC_NAKSHATRAS, index=4)
        target_pada = st.sidebar.selectbox("Select Pada", [1, 2, 3, 4], index=0)
        native_n_idx = SBC_NAKSHATRAS.index(target_nak)

st.sidebar.markdown("---")
st.sidebar.header("👁️ 2. View Mode")
view_mode = st.sidebar.radio("Select Layout:", ["Exact Time (Default)", "Long-Term Forecast"])

# --- EXACT TIME MODE ---
if view_mode == "Exact Time (Default)":
    st.markdown("### 🗓️ Date & Time Navigation")
    c1, c2, c3, c4 = st.columns([1, 2, 1, 2])
    
    with c1:
        if st.button("◀ Prev Day", use_container_width=True):
            st.session_state.target_date -= datetime.timedelta(days=1)
    with c2:
        st.session_state.target_date = st.date_input("Target Date", st.session_state.target_date, label_visibility="collapsed")
    with c3:
        if st.button("Next Day ▶", use_container_width=True):
            st.session_state.target_date += datetime.timedelta(days=1)
    with c4:
        target_time = st.time_input("Exact Time", datetime.time(12, 0), label_visibility="collapsed")

    target_date = st.session_state.target_date
    tz_str = st.selectbox("Timezone", ["Asia/Kolkata", "UTC", "America/New_York"], index=0)
    local = pytz.timezone(tz_str)
    dt_utc = local.localize(datetime.datetime.combine(target_date, target_time)).astimezone(pytz.utc)
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60.0)

    # --- Quick Weekly / Monthly Toggles ---
    st.markdown("---")
    st.markdown("### ⚡ Quick Forecasts (From Selected Date)")
    t1, t2 = st.columns(2)
    with t1: show_7 = st.toggle("📅 Show Next 7 Days Forecast")
    with t2: show_30 = st.toggle("📅 Show Next 30 Days Forecast")
    
    if show_7 or show_30:
        span = 30 if show_30 else 7
        with st.spinner(f"Calculating {span}-Day Quick Trend..."):
            quick_trend = []
            for i in range(span):
                eval_dt = target_date + datetime.timedelta(days=i)
                dt_u = local.localize(datetime.datetime.combine(eval_dt, target_time)).astimezone(pytz.utc)
                j_day = swe.julday(dt_u.year, dt_u.month, dt_u.day, dt_u.hour + dt_u.minute/60.0)
                score, _ = calculate_snapshot(j_day, native_n_idx, target_nak)
                quick_trend.append({"Date": eval_dt, "Score": score})
            st.line_chart(pd.DataFrame(quick_trend).set_index("Date")["Score"], color="#10B981")
    st.markdown("---")

    final_score, data = calculate_snapshot(jd, native_n_idx, target_nak)
    market_intel = get_market_intel(data)
    
    st.markdown(f"<h1 style='text-align: center; color: {'#059669' if final_score >= 60 else '#D97706' if final_score >=40 else '#EF4444'};'>Energy Score: {final_score}%</h1>", unsafe_allow_html=True)
    
    st.subheader("📑 Detailed Planetary Matrix")
    df = pd.DataFrame(data)
    display_df = df.drop(columns=['_bg', 'raw_planet', 'is_benefic', 'is_hit', 'progress'], errors='ignore')
    
    styled_df = display_df.style.apply(lambda r: [df.loc[r.name, '_bg']] * len(r), axis=1)
    st.dataframe(styled_df, use_container_width=True, hide_index=True, column_config={
        "Current Position": st.column_config.TextColumn(width="medium"),
        "Action on You": st.column_config.TextColumn(width="medium")
    })
    
    display_advisory(data, jd, tz_str)

    pdf_bytes = generate_pdf(target_nak, target_pada, str(target_date), final_score, data, market_intel)
    st.download_button(label="📥 Download Detailed PDF & Market Report", data=pdf_bytes, file_name=f"SBC_{target_nak}_{target_date}.pdf", mime="application/pdf", type="primary")

# --- LONG TERM MODE ---
elif view_mode == "Long-Term Forecast":
    st.markdown("### 📈 Master Forecast (Automatic 10-Year Simulation)")
    st.markdown("Just pick a starting date. The engine will instantly forecast all periods up to 10 years!")
    start_date = st.date_input("Master Start Date", datetime.date.today())
    
    total_days = 3652 # 10 Years automatically set
    
    with st.spinner("Simulating 10 Years of precise planetary astronomy... (Takes 2-3 seconds)"):
        trend_data = []
        local = pytz.timezone("Asia/Kolkata")
        
        for i in range(total_days):
            eval_date = start_date + datetime.timedelta(days=i)
            dt_utc = local.localize(datetime.datetime.combine(eval_date, datetime.time(12,0))).astimezone(pytz.utc)
            jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60.0)
            
            score, daily_data = calculate_snapshot(jd, native_n_idx, target_nak)
            trend_data.append({"Date": eval_date, "Score": score, "daily_data": daily_data})
        df_trend = pd.DataFrame(trend_data)
        
        avg_score = int(df_trend["Score"].mean())
        best_day = df_trend.loc[df_trend["Score"].idxmax()]
        worst_day = df_trend.loc[df_trend["Score"].idxmin()]
        
        # ==========================================
        # 17-BUCKET AT A GLANCE DASHBOARD
        # ==========================================
        st.markdown("---")
        st.markdown("### 📊 Comprehensive Period Analysis")
        
        periods = [
            ("Next 1 Week", 7), ("Next 2 Weeks", 14), ("Next 3 Weeks", 21),
            ("Next 1 Month", 30), ("Next 3 Months", 90), ("Next 6 Months", 180),
            ("Next 9 Months", 270), ("Next 1 Year", 365), ("Next 2 Years", 730),
            ("Next 3 Years", 1095), ("Next 4 Years", 1461), ("Next 5 Years", 1826),
            ("Next 6 Years", 2191), ("Next 7 Years", 2557), ("Next 8 Years", 2922),
            ("Next 9 Years", 3287), ("Next 10 Years", 3652)
        ]
        
        cols = st.columns(4)
        col_idx = 0
        
        for name, p_days in periods:
            bucket_df = df_trend.iloc[0:p_days]
            
            if not bucket_df.empty:
                b_avg = int(bucket_df["Score"].mean())
                b_best = bucket_df.loc[bucket_df["Score"].idxmax()]
                b_worst = bucket_df.loc[bucket_df["Score"].idxmin()]
                
                from_dt = bucket_df["Date"].iloc[0].strftime("%d %b %Y")
                to_dt = bucket_df["Date"].iloc[-1].strftime("%d %b %Y")
                
                if b_avg >= 60:
                    bg_color, border_color, status = "#F0FDF4", "#BBF7D0", "🟢 Auspicious"
                elif b_avg >= 40:
                    bg_color, border_color, status = "#FFFBEB", "#FEF3C7", "🟡 Neutral"
                else:
                    bg_color, border_color, status = "#FEF2F2", "#FECACA", "🔴 Cautious"
                    
                with cols[col_idx % 4]:
                    st.markdown(f"""
                    <div style="background-color: {bg_color}; padding: 12px; border-radius: 8px; border: 1px solid {border_color}; margin-bottom: 12px;">
                        <h5 style="margin-top: 0; margin-bottom: 2px; color: #333;">{name}</h5>
                        <p style="margin: 0 0 8px 0; font-size: 10px; color: #666; font-weight: 600;">{from_dt} - {to_dt}</p>
                        <h3 style="margin: 0; color: #111;">{b_avg}% <span style="font-size: 12px; font-weight: normal;">{status}</span></h3>
                        <p style="margin-top: 8px; margin-bottom: 0; font-size: 11px; color: #555;">
                        <b>B:</b> {b_best['Date'].strftime('%d %b %y')} ({b_best['Score']}%)<br>
                        <b>W:</b> {b_worst['Date'].strftime('%d %b %y')} ({b_worst['Score']}%)
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                col_idx += 1
        # ==========================================

        st.markdown("---")
        st.subheader("🔍 Deep Dive: Inspect Any Specific Day")
        
        day_options = [td["Date"].strftime("%d %B %Y") for td in trend_data]
        selected_day = st.selectbox("Select a day from the 10-year span to view exact strikes:", day_options, index=0)
        
        for td in trend_data:
            if td["Date"].strftime("%d %B %Y") == selected_day:
                st.markdown(f"**Score for {selected_day}: {td['Score']}%**")
                
                df_daily = pd.DataFrame(td['daily_data'])
                display_daily = df_daily.drop(columns=['_bg', 'raw_planet', 'is_benefic', 'is_hit', 'progress'], errors='ignore')
                styled_daily = display_daily.style.apply(lambda r: [df_daily.loc[r.name, '_bg']] * len(r), axis=1)
                
                st.dataframe(styled_daily, use_container_width=True, hide_index=True, column_config={
                    "Current Position": st.column_config.TextColumn(width="medium"),
                    "Action on You": st.column_config.TextColumn(width="medium")
                })
                
                # Recreate target JD for deep dive to fetch correct exact transit dates
                dt_utc = local.localize(datetime.datetime.combine(td["Date"], datetime.time(12,0))).astimezone(pytz.utc)
                target_jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60.0)
                
                display_advisory(td['daily_data'], target_jd, "Asia/Kolkata")
                break

        highlight_intel = get_market_intel(best_day['daily_data'])
        pdf_desc = f"Average Score (10 Yrs): {avg_score}%\nBest Day: {best_day['Date'].strftime('%d %B %Y')}\nWorst Day: {worst_day['Date'].strftime('%d %B %Y')}"
        
        pdf_bytes = generate_pdf(target_nak, target_pada, f"{start_date} to {start_date + datetime.timedelta(days=total_days)}", avg_score, [], highlight_intel, is_long_term=True, chart_desc=pdf_desc, trend_data=trend_data)
        
        st.download_button(label="📥 Download Master 10-Year PDF Report", data=pdf_bytes, file_name=f"SBC_Master_Forecast_{target_nak}.pdf", mime="application/pdf", type="primary")
