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

# --- Dictionaries & Data ---
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

# --- Core Math ---
def get_sbc_nakshatra(lon):
    if 276.6667 <= lon < 280.8889: return "Abhijit", 21
    elif lon >= 280.8889: return SBC_NAKSHATRAS[math.floor(lon / 13.333333) + 1], math.floor(lon / 13.333333) + 1
    else: return SBC_NAKSHATRAS[math.floor(lon / 13.333333)], math.floor(lon / 13.333333)

def get_planet_data(jd, planet_id):
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    if planet_id == "KETU":
        pos, _ = swe.calc_ut(jd, swe.MEAN_NODE, flags)
        return (pos[0] + 180.0) % 360.0, pos[3] 
    else:
        pos, _ = swe.calc_ut(jd, planet_id, flags)
        return pos[0], pos[3]

def get_vedha_type(speed, planet_name):
    if planet_name in ["Rahu", "KETU"]: return "Right (Retrograde)" 
    elif planet_name in ["Sun", "Moon"]: return "Left (Direct)" 
    elif speed < 0: return "Right (Retrograde)"
    elif 0 < speed < 0.2: return "Frontal (Stationary)"
    else: return "Left (Direct)"

def calculate_snapshot(jd, native_n_idx):
    data = []
    total_score = 50 
    planet_keys = list(PLANETS.keys()) + ["KETU"]
    for p_name in planet_keys:
        p_id = PLANETS[p_name] if p_name != "KETU" else "KETU"
        lon, speed = get_planet_data(jd, p_id)
        
        transiting_nak, transiting_idx = get_sbc_nakshatra(lon)
        vedha_dir = get_vedha_type(speed, p_name)
        distance = (transiting_idx - native_n_idx + 28) % 28
        
        is_benefic = p_name in BENEFICS
        sign = 1 if is_benefic else -1
        
        impact_text, score_impact, bg_color = "No Vedha", 0, ""
        
        if distance == 14: 
            impact_text, score_impact = "🔥 FRONTAL VEDHA", 15 * sign
            bg_color = "#D1FAE5" if is_benefic else "#FEE2E2"
        elif distance == 0:
            impact_text, score_impact = "⚡ DIRECT CONJUNCTION", 20 * sign
            bg_color = "#A7F3D0" if is_benefic else "#FECACA"
        elif distance in [1, 27]:
            impact_text, score_impact = f"⚠️ ADJACENT ({vedha_dir})", 10 * sign
            bg_color = "#ECFDF5" if is_benefic else "#FFF7ED"
        
        total_score += score_impact
        score_disp = f"+{score_impact}%" if score_impact > 0 else f"{score_impact}%" if score_impact < 0 else "-"
        
        data.append({
            "Planet": f"{p_name} ({'Benefic' if is_benefic else 'Malefic'})",
            "Nakshatra": transiting_nak,
            "Motion": vedha_dir,
            "Impact": impact_text,
            "Score Effect": score_disp,
            "_bg": bg_color,
            "raw_planet": p_name,
            "is_benefic": is_benefic,
            "is_hit": impact_text != "No Vedha"
        })
    return max(0, min(100, total_score)), data

# --- Share Market Logic ---
def get_market_intel(data):
    pos = []
    neg = []
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

# --- PDF Generator ---
def clean(text): return text.encode('ascii', 'ignore').decode('ascii')

def generate_pdf(nak, pada, date_str, score, data, intel, is_long_term=False, chart_desc=""):
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
    pdf.cell(200, 8, txt=clean("Share Market & Sector Analysis (Personalized):"), ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 7, txt=clean(intel))
    
    if not is_long_term:
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 8, txt=clean("Active Planetary Strikes (Vedhas):"), ln=True)
        pdf.set_font("Arial", size=10)
        for d in data:
            if d['is_hit']:
                pdf.cell(200, 7, txt=clean(f"> {d['raw_planet']}: {d['Impact']} ({d['Score Effect']})"), ln=True)

    return pdf.output(dest='S').encode('latin-1')

# --- UI Setup ---
st.title("🕉️ Sarvatobhadra Chakra (SBC) Engine")
st.markdown("Strict Lahiri Ayanamsa • Stock Market Forecasting • 9-Planet Vedha")

# --- SIDEBAR ---
st.sidebar.header("👤 1. Subject Profile")
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
    col1, col2 = st.columns(2)
    with col1: target_date = st.date_input("Target Date", datetime.date.today())
    with col2: target_time = st.time_input("Exact Time", datetime.time(12, 0))
    tz_str = st.selectbox("Timezone", ["Asia/Kolkata", "UTC", "America/New_York"], index=0)

    local = pytz.timezone(tz_str)
    dt_utc = local.localize(datetime.datetime.combine(target_date, target_time)).astimezone(pytz.utc)
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60.0)

    final_score, data = calculate_snapshot(jd, native_n_idx)
    market_intel = get_market_intel(data)
    
    st.markdown("---")
    st.markdown(f"<h1 style='text-align: center; color: {'#059669' if final_score >= 60 else '#D97706' if final_score >=40 else '#EF4444'};'>Energy Score: {final_score}%</h1>", unsafe_allow_html=True)
    
    df = pd.DataFrame(data)
    display_df = df.drop(columns=['_bg', 'raw_planet', 'is_benefic', 'is_hit'])
    styled_df = display_df.style.apply(lambda r: [df.loc[r.name, '_bg']] * len(r), axis=1)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    pdf_bytes = generate_pdf(target_nak, target_pada, str(target_date), final_score, data, market_intel)
    st.download_button(label="📥 Download Detailed PDF & Market Report", data=pdf_bytes, file_name=f"SBC_{target_nak}_{target_date}.pdf", mime="application/pdf", type="primary")

# --- LONG TERM MODE ---
elif view_mode == "Long-Term Forecast":
    st.markdown("### 📈 Long-Term Energy & Market Trend")
    col1, col2 = st.columns(2)
    with col1: start_date = st.date_input("Start Date", datetime.date.today())
    with col2: duration = st.selectbox("Duration", ["1 Week", "2 Weeks", "1 Month", "2 Months", "3 Months", "6 Months", "1 Year"], index=2)
    
    days_map = {"1 Week": 7, "2 Weeks": 14, "1 Month": 30, "2 Months": 60, "3 Months": 90, "6 Months": 180, "1 Year": 365}
    total_days = days_map[duration]
    
    with st.spinner(f"Simulating {total_days} days of planetary orbits..."):
        trend_data = []
        local = pytz.timezone("Asia/Kolkata")
        
        for i in range(total_days):
            eval_date = start_date + datetime.timedelta(days=i)
            dt_utc = local.localize(datetime.datetime.combine(eval_date, datetime.time(12,0))).astimezone(pytz.utc)
            jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60.0)
            
            score, daily_data = calculate_snapshot(jd, native_n_idx)
            trend_data.append({"Date": eval_date, "Score": score, "daily_data": daily_data})
            
        df_trend = pd.DataFrame(trend_data)
        st.line_chart(df_trend.set_index("Date")["Score"], color="#4338CA")
        
        avg_score = int(df_trend["Score"].mean())
        best_day = df_trend.loc[df_trend["Score"].idxmax()]
        worst_day = df_trend.loc[df_trend["Score"].idxmin()]
        
        st.info(f"**Trend Summary:** Your average score over this {duration} period is **{avg_score}%**. The most auspicious day is {best_day['Date']} ({best_day['Score']}%). The most cautious day is {worst_day['Date']} ({worst_day['Score']}%).")
        
        # Get market intel for the best day as a highlight
        highlight_intel = get_market_intel(best_day['daily_data'])
        pdf_bytes = generate_pdf(target_nak, target_pada, f"{start_date} to {start_date + datetime.timedelta(days=total_days)}", avg_score, [], highlight_intel, is_long_term=True, chart_desc=f"Average Score: {avg_score}%\nBest Day: {best_day['Date']}\nWorst Day: {worst_day['Date']}")
        
        st.download_button(label="📥 Download Long-Term Trend & Market PDF", data=pdf_bytes, file_name=f"SBC_Forecast_{target_nak}.pdf", mime="application/pdf", type="primary")
