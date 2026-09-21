import streamlit as st
import pandas as pd
import numpy as np
import joblib
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import os
from io import BytesIO
from fpdf import FPDF
from google import genai
from google.genai import types

# ---------------------------------------------------------
# GEMINI API KEY CONFIGURATION
# ---------------------------------------------------------
GEMINI_API_KEY = "AQ.Ab8RN6LZIPxftYiMLe3jfr4NkUo91tf0a52RqBmy2OyiZKc16g"

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="AtEase - Operational Readiness & Stress Risk Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# SQLITE DATABASE INITIALIZATION & MANAGEMENT
# ---------------------------------------------------------
DB_PATH = "at_ease_tactical.db"

def init_db():
    with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                name TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS batch_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uploaded_by TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_records INTEGER,
                high_risk_count INTEGER,
                moderate_risk_count INTEGER,
                low_risk_count INTEGER
            )
        ''')
        conn.commit()

def seed_default_users():
    with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            default_users = [
                ("commander_admin", "adminpassword123", "Command Commander", "Col. Sharma"),
                ("medic_officer", "medicpassword123", "Medical Officer", "Dr. Verma"),
                ("soldier_test", "password123", "Personnel", "Rifleman Singh")
            ]
            cursor.executemany("INSERT OR IGNORE INTO users (username, password, role, name) VALUES (?, ?, ?, ?)", default_users)
            conn.commit()

init_db()
seed_default_users()

# ---------------------------------------------------------
# SESSION STATE INITIALIZATION
# ---------------------------------------------------------
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'user_fullname' not in st.session_state:
    st.session_state.user_fullname = None
if 'app_started' not in st.session_state:
    st.session_state.app_started = False

# ---------------------------------------------------------
# ADVANCED MILITARY HUD STYLING
# ---------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@500;700&display=swap');

    .stApp {
        background-color: #05070b;
        color: #f8fafc;
        font-family: 'Rajdhani', sans-serif;
    }
    
    @keyframes hudPulse {
        0% { box-shadow: 0 0 15px rgba(14, 165, 233, 0.1), inset 0 0 15px rgba(14, 165, 233, 0.1); border-color: #0369a1; }
        50% { box-shadow: 0 0 35px rgba(56, 189, 248, 0.4), inset 0 0 25px rgba(56, 189, 248, 0.2); border-color: #38bdf8; }
        100% { box-shadow: 0 0 15px rgba(14, 165, 233, 0.1), inset 0 0 15px rgba(14, 165, 233, 0.1); border-color: #0369a1; }
    }

    .hud-welcome-card {
        animation: hudPulse 4s infinite ease-in-out;
        background: linear-gradient(135deg, #0b132b 0%, #05070b 100%);
        padding: 40px 30px;
        border-radius: 12px;
        border: 2px solid #0284c7;
        text-align: center;
    }

    .hud-title {
        font-family: 'Share Tech Mono', monospace;
        font-size: 3.8rem;
        font-weight: 900;
        color: #ffffff;
        text-transform: uppercase;
        letter-spacing: 4px;
        margin: 0;
        text-shadow: 0 0 10px rgba(56, 189, 248, 0.8), 0 0 20px rgba(56, 189, 248, 0.5);
    }

    .hud-subtitle {
        font-family: 'Share Tech Mono', monospace;
        color: #38bdf8;
        font-size: 0.95rem;
        font-weight: 700;
        margin-top: 10px;
        letter-spacing: 5px;
        text-transform: uppercase;
    }

    .header-container {
        background: linear-gradient(90deg, #0b132b 0%, #05070b 100%);
        padding: 20px 24px;
        border-radius: 8px;
        border: 1px solid #0284c7;
        box-shadow: 0 0 20px rgba(2, 132, 199, 0.15);
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .header-title {
        font-family: 'Share Tech Mono', monospace;
        color: #ffffff;
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: 2px;
    }
    .header-subtitle {
        font-family: 'Rajdhani', sans-serif;
        color: #94a3b8;
        font-size: 0.9rem;
        margin-top: 2px;
    }

    .kpi-card {
        background-color: #0b132b;
        border-radius: 8px;
        padding: 20px;
        border: 1px solid #1e293b;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    .kpi-title {
        color: #94a3b8;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .kpi-value {
        color: #38bdf8;
        font-size: 2.2rem;
        font-weight: 700;
        margin-top: 8px;
        font-family: 'Share Tech Mono', monospace;
    }

    .stTabs [data-baseweb="tab-list"] { gap: 12px; border-bottom: 1px solid #1e293b; }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        background-color: #0b132b;
        border-radius: 6px 6px 0px 0px;
        color: #94a3b8;
        font-weight: 600;
        padding: 0px 24px;
        border: 1px solid #1e293b;
        border-bottom: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        border-color: #0284c7 !important;
    }

    [data-testid="stForm"] {
        background-color: #0b132b;
        border-radius: 10px;
        border: 1px solid #1e293b;
        padding: 24px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# ROBUST MODEL LOADER (WITH FALLBACK)
# ---------------------------------------------------------
@st.cache_resource
def load_model():
    model_path = 'xgboost_stress_model.pkl'
    if os.path.exists(model_path):
        try:
            return joblib.load(model_path)
        except Exception:
            pass
    
    # Fallback dummy model class if pkl file is missing
    class DummyModel:
        def predict(self, X):
            return np.array([2 if (row.get('phq9_score', 10) > 12 or row.get('avg_sleep_hours', 6) < 4.5) else (1 if row.get('phq9_score', 5) > 8 else 0) for _, row in X.iterrows()])
        def predict_proba(self, X):
            preds = self.predict(X)
            probs = []
            for p in preds:
                if p == 2:
                    probs.append([0.1, 0.2, 0.7])
                elif p == 1:
                    probs.append([0.2, 0.6, 0.2])
                else:
                    probs.append([0.75, 0.2, 0.05])
            return np.array(probs)
    return DummyModel()

model = load_model()

# ---------------------------------------------------------
# PDF REPORT GENERATOR FUNCTION
# ---------------------------------------------------------
def create_pdf_report(eval_data, raw_inputs, username):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    pdf.set_fill_color(11, 19, 43)
    pdf.rect(0, 0, 210, 35, 'F')
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 18)
    pdf.set_xy(10, 10)
    pdf.cell(0, 10, "ATEASE // OPERATIONAL READINESS REPORT", 0, 1, 'L')
    
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(148, 163, 184)
    pdf.set_xy(10, 20)
    pdf.cell(0, 10, f"Issued for Personnel: {username} | Confidential Stress Telemetry Receipt", 0, 1, 'L')
    
    pdf.ln(15)
    pdf.set_fill_color(240, 244, 248)
    pdf.set_draw_color(2, 132, 199)
    pdf.rect(10, 42, 190, 25, 'DF')
    
    pdf.set_text_color(15, 23, 42)
    pdf.set_font("helvetica", "B", 11)
    pdf.set_xy(15, 46)
    pdf.cell(0, 6, f"ASSESSED RISK TIER: {eval_data['risk_tier'].upper()}", 0, 1)
    
    pdf.set_font("helvetica", "", 10)
    pdf.set_xy(15, 54)
    pdf.cell(0, 6, f"High Stress Risk Probability: {eval_data['high_prob']}%", 0, 1)
    
    pdf.ln(15)
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(11, 19, 43)
    pdf.cell(0, 8, "1. Evaluated Personnel Telemetry Metrics", 0, 1)
    
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(51, 65, 85)
    
    metrics_list = [
        ("Posting Type", str(raw_inputs.get('posting_type', 'N/A'))),
        ("Rank Group", str(raw_inputs.get('rank_group', 'N/A'))),
        ("Years of Service", str(raw_inputs.get('years_service', 'N/A'))),
        ("Days in Field (Last 6 Months)", str(raw_inputs.get('days_in_field', 'N/A'))),
        ("Night Shifts Last Month", str(raw_inputs.get('night_shifts_last_month', 'N/A'))),
        ("Months Since Last Leave", str(raw_inputs.get('months_since_last_leave', 'N/A'))),
        ("Leave Rejections Count", str(raw_inputs.get('leave_rejections_count', 'N/A'))),
        ("PHQ-9 Depression Score", f"{eval_data['phq9']} / 27"),
        ("GAD-7 Anxiety Score", f"{eval_data['gad7']} / 21"),
        ("Average Daily Sleep", f"{eval_data['sleep']} Hours")
    ]
    
    for label, val in metrics_list:
        pdf.cell(100, 7, f"- {label}:", 0, 0)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(90, 7, val, 0, 1)
        pdf.set_font("helvetica", "", 10)
        
    pdf.ln(5)
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(11, 19, 43)
    pdf.cell(0, 8, "2. Recommended Command Action Protocols", 0, 1)
    
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(51, 65, 85)
    
    if eval_data['risk_tier'] == "High Risk":
        actions = [
            "- Immediate priority schedule for clinical psychological evaluation.",
            "- Fast-track administrative leave processing within 7 days.",
            "- Restructure night shift intensity and operational field duty immediately."
        ]
    elif eval_data['risk_tier'] == "Moderate Risk":
        actions = [
            "- Schedule routine medical evaluation within the next 14 days.",
            "- Monitor sleep deficit and continuous field exposure closely.",
            "- Review upcoming leave queue and deployment rotation schedule."
        ]
    else:
        actions = [
            "- Standard operational clearance verified.",
            "- Maintain regular duty cycle with standard monitoring.",
            "- Re-assess on 60-day standard operational cycle."
        ]
        
    for act in actions:
        pdf.cell(0, 6, act, 0, 1)
        
    pdf.ln(15)
    pdf.set_font("helvetica", "I", 8)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 5, "AtEase Tactical Telemetry System - Encrypted Secure Channel", 0, 1, 'C')
    
    return bytes(pdf.output())

# ---------------------------------------------------------
# BATCH CSV PRE-VALIDATION ENGINE
# ---------------------------------------------------------
def validate_batch_csv(df):
    errors = []
    warnings = []
    required_cols = [
        'posting_type', 'rank_group', 'years_service', 'days_in_field', 
        'night_shifts_last_month', 'months_since_last_leave', 'leave_rejections_count', 
        'transfers_last_3_years', 'phq9_score', 'gad7_score', 'avg_sleep_hours', 'self_reported_mood'
    ]
    
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        errors.append(f"Missing required columns: {', '.join(missing)}")
        return False, errors, warnings

    if (df['phq9_score'] < 0).any() or (df['phq9_score'] > 27).any():
        errors.append("Invalid PHQ-9 Score detected: must be between 0 and 27.")
    if (df['gad7_score'] < 0).any() or (df['gad7_score'] > 21).any():
        errors.append("Invalid GAD-7 Score detected: must be between 0 and 21.")
    if (df['avg_sleep_hours'] < 0).any() or (df['avg_sleep_hours'] > 24).any():
        errors.append("Invalid sleep hours detected: must be between 0 and 24.")
    if (df['days_in_field'] < 0).any() or (df['days_in_field'] > 365).any():
        warnings.append("Unusual 'days_in_field' values detected (>365 days). Please verify.")

    if df[required_cols].isnull().any().any():
        errors.append("Dataset contains missing (NaN) values in required feature columns.")

    if errors:
        return False, errors, warnings
    return True, [], warnings

# ---------------------------------------------------------
# STAGE 1: AUTHENTICATION GATE
# ---------------------------------------------------------
if not st.session_state.authenticated:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 1.3, 1])
    
    with col_m:
        st.markdown("""
        <div class="hud-welcome-card">
            <div style="font-size: 2.2rem; margin-bottom: 5px;">🛡️</div>
            <div class="hud-title">AtEase</div>
            <div class="hud-subtitle">// Secure Tactical Telemetry Gateway</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        auth_tab_login, auth_tab_register = st.tabs(["🔐 Secure Login", "📝 New Registration"])
        
        with auth_tab_login:
            with st.form("login_form"):
                login_user = st.text_input("Username / Personnel ID")
                login_pass = st.text_input("Secure Passcode", type="password")
                login_submit = st.form_submit_button("AUTHENTICATE & PROCEED", use_container_width=True)
                
                if login_submit:
                    with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT password, role, name FROM users WHERE username = ?", (login_user,))
                        row = cursor.fetchone()
                    
                    if row and row[0] == login_pass:
                        st.session_state.authenticated = True
                        st.session_state.current_user = login_user
                        st.session_state.user_role = row[1]
                        st.session_state.user_fullname = row[2]
                        st.success(f"Access Granted. Welcome, {row[2]}!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials or clearance level.")
                        
            st.caption("Demo credentials: `commander_admin` / `adminpassword123`, `medic_officer` / `medicpassword123`, or `soldier_test` / `password123`")

        with auth_tab_register:
            with st.form("register_form"):
                reg_user = st.text_input("Choose Username / ID")
                reg_name = st.text_input("Full Name / Rank & Name")
                reg_pass = st.text_input("Create Passcode", type="password")
                reg_role = st.selectbox("Select Clearance Role", ["Personnel", "Medical Officer", "Command Commander"])
                reg_submit = st.form_submit_button("REGISTER SECURE PROFILE", use_container_width=True)
                
                if reg_submit:
                    if not reg_user or not reg_pass or not reg_name:
                        st.error("Please fill out all required fields.")
                    else:
                        try:
                            with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
                                cursor = conn.cursor()
                                cursor.execute("INSERT INTO users (username, password, role, name) VALUES (?, ?, ?, ?)",
                                               (reg_user, reg_pass, reg_role, reg_name))
                                conn.commit()
                            st.success("Registration successful! You can now log in via the Secure Login tab.")
                        except sqlite3.IntegrityError:
                            st.error("Username already registered in system telemetry.")

# ---------------------------------------------------------
# STAGE 2: HUD WELCOME SCREEN
# ---------------------------------------------------------
elif st.session_state.authenticated and not st.session_state.app_started:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    
    with col_m:
        st.markdown(f"""
        <div class="hud-welcome-card">
            <div style="font-size: 1.5rem; margin-bottom: 5px;">🛡️</div>
            <div class="hud-title">AtEase</div>
            <div class="hud-subtitle">// Operational Readiness & Telemetry HUD</div>
            <hr style="border-color: #1e293b; margin: 30px 0;">
            <p style="color: #94a3b8; font-size: 1rem; line-height: 1.6; margin-bottom: 10px; letter-spacing: 0.5px;">
                Secure session established for <b>{st.session_state.user_fullname}</b> ({st.session_state.user_role}).
            </p>
            <p style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 30px;">
                Advanced military-grade predictive analytics platform engineered for tactical stress tracking and psychological readiness.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("⚡ INITIALIZE COMMAND INTERFACE", use_container_width=True):
            st.session_state.app_started = True
            st.rerun()

# ---------------------------------------------------------
# STAGE 3: MAIN OPERATIONAL DASHBOARD
# ---------------------------------------------------------
else:
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"""
        <div class="header-container" style="margin-bottom: 12px;">
            <div>
                <div class="header-title">🛡️ ATEASE // COMMAND TELEMETRY</div>
                <div class="header-subtitle">Operator: <b>{st.session_state.user_fullname}</b> | Clearance: <b>{st.session_state.user_role}</b></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_h2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔒 LOGOUT SESSION", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.session_state.user_role = None
            st.session_state.user_fullname = None
            st.session_state.app_started = False
            st.rerun()

    if st.session_state.user_role == "Personnel":
        tab1, tab4 = st.tabs(["👤 Individual Evaluator", "💬 Confidential AI Support"])
        tabs_mode = "Personnel"
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "👤 Individual Evaluator", 
            "📂 Batch Unit Assessment", 
            "📊 Unit Analytics",
            "💬 Confidential AI Support"
        ])
        tabs_mode = "Admin"

    # ==========================================
    # TAB 1: INDIVIDUAL EVALUATOR
    # ==========================================
    with tab1:
        st.markdown("### Individual Risk Profile Assessment")
        st.caption("Input deployment profile, duty trends, and health scores to generate predictive stress probabilities.")

        with st.form("individual_form"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("#### 🎖️ Deployment Profile")
                posting_type = st.selectbox("Posting Type", ['counter_insurgency', 'border_outpost', 'urban_security', 'headquarters', 'training_centre'])
                rank_group = st.selectbox("Rank / Category", ['Constable', 'NCO', 'JCO', 'Officer'])
                years_service = st.number_input("Years of Service", min_value=0, max_value=40, value=5)
                days_in_field = st.number_input("Days in Field (Last 6 Months)", min_value=0, max_value=200, value=120)

            with col2:
                st.markdown("#### 📋 Operational Workload")
                night_shifts = st.number_input("Night Shifts (Last Month)", min_value=0, max_value=30, value=15)
                months_leave = st.number_input("Months Since Last Leave", min_value=0.0, max_value=24.0, value=8.0, step=0.5)
                leave_rejections = st.number_input("Leave Rejections Count", min_value=0, max_value=10, value=1)
                transfers = st.number_input("Transfers in Last 3 Years", min_value=0, max_value=10, value=2)

            with col3:
                st.markdown("#### 🧠 Health & Psychological Scores")
                phq9 = st.slider("PHQ-9 Depression Score (0-27)", min_value=0, max_value=27, value=14)
                gad7 = st.slider("GAD-7 Anxiety Score (0-21)", min_value=0, max_value=21, value=12)
                avg_sleep = st.slider("Average Daily Sleep Hours", min_value=2.0, max_value=10.0, value=5.0, step=0.5)
                mood = st.select_slider(
                    "Self-Reported Mood Index", 
                    options=[1, 2, 3, 4, 5], 
                    value=2,
                    format_func=lambda x: {1: "1 - Critical", 2: "2 - Low", 3: "3 - Neutral", 4: "4 - Good", 5: "5 - Optimal"}[x]
                )

            submit_button = st.form_submit_button(label="EXECUTE RISK EVALUATION", use_container_width=True)

        if submit_button:
            input_dict = {
                'posting_type': posting_type, 'rank_group': rank_group, 'years_service': years_service,
                'days_in_field': days_in_field, 'night_shifts_last_month': night_shifts, 'months_since_last_leave': months_leave,
                'leave_rejections_count': leave_rejections, 'transfers_last_3_years': transfers,
                'phq9_score': phq9, 'gad7_score': gad7, 'avg_sleep_hours': avg_sleep, 'self_reported_mood': mood
            }
            input_data = pd.DataFrame([input_dict])

            prediction = model.predict(input_data)[0]
            probabilities = model.predict_proba(input_data)[0]
            high_risk_prob = round(probabilities[2] * 100, 1)

            eval_summary = {
                'risk_tier': {0: "Low Risk", 1: "Moderate Risk", 2: "High Risk"}[prediction],
                'high_prob': high_risk_prob, 'phq9': phq9, 'gad7': gad7, 'sleep': avg_sleep,
                'months_leave': months_leave, 'posting': posting_type
            }

            st.session_state['latest_eval'] = eval_summary
            st.session_state['latest_raw_inputs'] = input_dict

            st.markdown("---")
            st.markdown("### Assessment Result & Triage Actions")

            res_col1, res_col2 = st.columns([1, 1.2])

            with res_col1:
                if prediction == 2:
                    st.error("### 🚨 HIGH STRESS RISK TIER DETECTED")
                    st.markdown("""
                    **Command Action Plan:**
                    - **Immediate:** Priority schedule for clinical psychological evaluation.
                    - **Rotation:** Fast-track administrative leave processing within 7 days.
                    - **Deployment:** Restructure night shift intensity and operational field duty.
                    """)
                elif prediction == 1:
                    st.warning("### ⚠️ MODERATE STRESS RISK TIER")
                    st.markdown("""
                    **Command Action Plan:**
                    - **Monitoring:** Schedule routine medical evaluation.
                    - **Workload:** Track sleep deficit and continuous field days over the next 14 days.
                    """)
                else:
                    st.success("### ✅ LOW STRESS RISK TIER")
                    st.markdown("""
                    **Command Action Plan:**
                    - **Status:** Standard operational clearance.
                    - **Follow-up:** Re-assess on 60-day standard cycle.
                    """)

                pdf_bytes = create_pdf_report(eval_summary, input_dict, st.session_state.user_fullname)
                st.download_button(
                    label="📥 DOWNLOAD TACTICAL REPORT (PDF)",
                    data=pdf_bytes,
                    file_name="AtEase_Readiness_Receipt.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

            with res_col2:
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=high_risk_prob,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "High Stress Risk Probability (%)", 'font': {'size': 16, 'color': '#f8fafc'}},
                    number={'suffix': "%", 'font': {'color': '#f8fafc'}},
                    gauge={
                        'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#94a3b8"},
                        'bar': {'color': "#f8fafc"},
                        'bgcolor': "#0b132b",
                        'borderwidth': 1,
                        'bordercolor': "#1e293b",
                        'steps': [
                            {'range': [0, 35], 'color': "#10b981"},
                            {'range': [35, 70], 'color': "#f59e0b"},
                            {'range': [70, 100], 'color': "#ef4444"}
                        ],
                    }
                ))
                fig_gauge.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "#f8fafc"}, height=250, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_gauge, use_container_width=True)

            st.markdown("---")
            st.markdown("### 📊 Individual Psychological & Operational Breakdown")

            ind_col1, ind_col2 = st.columns(2)

            with ind_col1:
                st.markdown("##### 1. Personal Stress Footprint (Normalized Radar)")
                radar_metrics = {
                    'Depression (PHQ-9)': round((phq9 / 27) * 100, 1),
                    'Anxiety (GAD-7)': round((gad7 / 21) * 100, 1),
                    'Sleep Deficit': round(((10 - avg_sleep) / 8) * 100, 1),
                    'Field Exposure': round((days_in_field / 200) * 100, 1),
                    'Night Shift Load': round((night_shifts / 30) * 100, 1),
                    'Leave Delay': round(min((months_leave / 24) * 100, 100), 1)
                }

                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=list(radar_metrics.values()), theta=list(radar_metrics.keys()), fill='toself',
                    name='Individual Profile', line_color='#0284c7', fillcolor='rgba(2, 132, 199, 0.3)'
                ))
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(color='#94a3b8')), angularaxis=dict(tickfont=dict(color='#f8fafc'))),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "#f8fafc"}, height=350, margin=dict(l=40, r=40, t=20, b=20)
                )
                st.plotly_chart(fig_radar, use_container_width=True)

            with ind_col2:
                st.markdown("##### 2. Key Stress Drivers Identified")
                drivers = {
                    'Sleep Deficit': max(0, (8.0 - avg_sleep) * 12.5),
                    'Depression Score (PHQ-9)': (phq9 / 27) * 100,
                    'Anxiety Score (GAD-7)': (gad7 / 21) * 100,
                    'Field Deployment Duty': (days_in_field / 200) * 100,
                    'Leave Rejection History': (leave_rejections / 10) * 100,
                    'Night Shift Load': (night_shifts / 30) * 100
                }
                df_drivers = pd.DataFrame(list(drivers.items()), columns=['Stress Driver', 'Impact Level (%)']).sort_values(by='Impact Level (%)', ascending=True)

                fig_bar = px.bar(df_drivers, x='Impact Level (%)', y='Stress Driver', orientation='h', color='Impact Level (%)', color_continuous_scale='Reds')
                fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "#f8fafc"}, height=350, margin=dict(l=20, r=20, t=20, b=20), coloraxis_showscale=False)
                st.plotly_chart(fig_bar, use_container_width=True)

    # ==========================================
    # TAB 2: BATCH UNIT ASSESSMENT (Admin / Medic Only)
    # ==========================================
    if tabs_mode == "Admin":
        with tab2:
            st.markdown("### Batch Unit Records Evaluation")
            st.caption("Upload unit deployment records. The pre-validation engine automatically verifies data integrity prior to model execution.")

            sample_df = pd.DataFrame([
                {'personnel_id': 'CAPF_101', 'posting_type': 'border_outpost', 'rank_group': 'Constable', 'years_service': 6, 'days_in_field': 130, 'night_shifts_last_month': 18, 'months_since_last_leave': 9.0, 'leave_rejections_count': 2, 'transfers_last_3_years': 3, 'phq9_score': 16, 'gad7_score': 14, 'avg_sleep_hours': 4.5, 'self_reported_mood': 2},
                {'personnel_id': 'CAPF_102', 'posting_type': 'headquarters', 'rank_group': 'Officer', 'years_service': 14, 'days_in_field': 30, 'night_shifts_last_month': 4, 'months_since_last_leave': 3.0, 'leave_rejections_count': 0, 'transfers_last_3_years': 1, 'phq9_score': 3, 'gad7_score': 2, 'avg_sleep_hours': 7.5, 'self_reported_mood': 5},
                {'personnel_id': 'CAPF_103', 'posting_type': 'counter_insurgency', 'rank_group': 'NCO', 'years_service': 9, 'days_in_field': 160, 'night_shifts_last_month': 22, 'months_since_last_leave': 12.0, 'leave_rejections_count': 3, 'transfers_last_3_years': 4, 'phq9_score': 20, 'gad7_score': 18, 'avg_sleep_hours': 3.5, 'self_reported_mood': 1}
            ])

            col_df, col_up = st.columns([1, 2])
            with col_df:
                st.download_button(
                    label="📄 Download Standard CSV Template",
                    data=sample_df.to_csv(index=False),
                    file_name="sample_personnel_template.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with col_up:
                uploaded_file = st.file_uploader("Upload Unit Dataset", type=["csv"], label_visibility="collapsed")

            if uploaded_file is not None:
                df_uploaded = pd.read_csv(uploaded_file)
                
                is_valid, errors, warnings = validate_batch_csv(df_uploaded)

                if warnings:
                    for warn in warnings:
                        st.warning(f"⚠️ **Pre-validation Warning:** {warn}")

                if not is_valid:
                    st.error("❌ **Batch CSV Validation Failed:**")
                    for err in errors:
                        st.markdown(f"- {err}")
                else:
                    required_cols = [
                        'posting_type', 'rank_group', 'years_service', 'days_in_field', 
                        'night_shifts_last_month', 'months_since_last_leave', 'leave_rejections_count', 
                        'transfers_last_3_years', 'phq9_score', 'gad7_score', 'avg_sleep_hours', 'self_reported_mood'
                    ]
                    feature_df = df_uploaded[required_cols]
                    preds = model.predict(feature_df)
                    probs = model.predict_proba(feature_df)

                    risk_map = {0: 'Low Risk', 1: 'Moderate Risk', 2: 'High Risk'}
                    df_uploaded['Predicted Risk Tier'] = [risk_map[p] for p in preds]
                    df_uploaded['High Risk Prob (%)'] = [round(p[2] * 100, 1) for p in probs]

                    st.success("✅ Pre-validation Passed & Batch Assessment Executed Successfully!")

                    high_count = int((preds == 2).sum())
                    mod_count = int((preds == 1).sum())
                    low_count = int((preds == 0).sum())

                    try:
                        with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO batch_history (uploaded_by, total_records, high_risk_count, moderate_risk_count, low_risk_count) VALUES (?, ?, ?, ?, ?)",
                                           (st.session_state.current_user, len(df_uploaded), high_count, mod_count, low_count))
                            conn.commit()
                    except Exception:
                        pass

                    k1, k2, k3, k4 = st.columns(4)
                    k1.markdown(f'<div class="kpi-card"><div class="kpi-title">Total Personnel</div><div class="kpi-value">{len(df_uploaded)}</div></div>', unsafe_allow_html=True)
                    k2.markdown(f'<div class="kpi-card"><div class="kpi-title">🚨 High Risk</div><div class="kpi-value" style="color: #ef4444;">{high_count}</div></div>', unsafe_allow_html=True)
                    k3.markdown(f'<div class="kpi-card"><div class="kpi-title">⚠️ Moderate Risk</div><div class="kpi-value" style="color: #f59e0b;">{mod_count}</div></div>', unsafe_allow_html=True)
                    k4.markdown(f'<div class="kpi-card"><div class="kpi-title">✅ Low Risk</div><div class="kpi-value" style="color: #10b981;">{low_count}</div></div>', unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.download_button(
                        label="📥 DOWNLOAD PROCESSED UNIT ASSESSMENT (CSV)",
                        data=df_uploaded.to_csv(index=False),
                        file_name="processed_unit_stress_assessment.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.dataframe(df_uploaded, use_container_width=True)
                    st.session_state['processed_df'] = df_uploaded

        # ==========================================
        # TAB 3: EXTENDED UNIT ANALYTICS
        # ==========================================
        with tab3:
            st.markdown("### Extended Operational Intelligence Dashboard")

            if 'processed_df' in st.session_state:
                df_analytics = st.session_state['processed_df']

                selected_tiers = st.multiselect("Filter Analytics by Risk Tier:", options=['Low Risk', 'Moderate Risk', 'High Risk'], default=['Low Risk', 'Moderate Risk', 'High Risk'])
                filtered_df = df_analytics[df_analytics['Predicted Risk Tier'].isin(selected_tiers)]

                a1, a2 = st.columns(2)
                with a1:
                    st.markdown("##### 1. Unit Stress Breakdown (Donut Chart)")
                    fig_pie = px.pie(filtered_df, names='Predicted Risk Tier', color='Predicted Risk Tier', color_discrete_map={'High Risk': '#ef4444', 'Moderate Risk': '#f59e0b', 'Low Risk': '#10b981'}, hole=0.45)
                    fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "#f8fafc"}, height=320, margin=dict(l=20, r=20, t=20, b=20))
                    st.plotly_chart(fig_pie, use_container_width=True)

                with a2:
                    st.markdown("##### 2. Stress Risk by Posting Environment")
                    fig_posting = px.histogram(filtered_df, x='posting_type', color='Predicted Risk Tier', barmode='stack', color_discrete_map={'High Risk': '#ef4444', 'Moderate Risk': '#f59e0b', 'Low Risk': '#10b981'}, labels={'posting_type': 'Posting Type', 'count': 'Personnel Count'})
                    fig_posting.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "#f8fafc"}, height=320, margin=dict(l=20, r=20, t=20, b=20))
                    st.plotly_chart(fig_posting, use_container_width=True)

                st.markdown("---")
                b1, b2 = st.columns(2)
                with b1:
                    st.markdown("##### 3. Leave Deficit vs. Stress Risk Tier")
                    fig_box = px.box(filtered_df, x='Predicted Risk Tier', y='months_since_last_leave', color='Predicted Risk Tier', color_discrete_map={'High Risk': '#ef4444', 'Moderate Risk': '#f59e0b', 'Low Risk': '#10b981'}, labels={'months_since_last_leave': 'Months Since Last Leave'})
                    fig_box.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "#f8fafc"}, height=320, margin=dict(l=20, r=20, t=20, b=20))
                    st.plotly_chart(fig_box, use_container_width=True)

                with b2:
                    st.markdown("##### 4. Depression (PHQ-9) vs. Sleep Deficit Correlation")
                    fig_scatter = px.scatter(filtered_df, x='avg_sleep_hours', y='phq9_score', size='gad7_score', color='Predicted Risk Tier', color_discrete_map={'High Risk': '#ef4444', 'Moderate Risk': '#f59e0b', 'Low Risk': '#10b981'}, labels={'avg_sleep_hours': 'Avg Daily Sleep (Hours)', 'phq9_score': 'PHQ-9 Depression Score', 'gad7_score': 'GAD-7 Anxiety'})
                    fig_scatter.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "#f8fafc"}, height=320, margin=dict(l=20, r=20, t=20, b=20))
                    st.plotly_chart(fig_scatter, use_container_width=True)

            else:
                st.info("💡 Upload unit records in the 'Batch Unit Assessment' tab to populate all analytics charts.")

    # ==========================================
    # TAB 4: INTERACTIVE LLM THERAPIST
    # ==========================================
    with tab4:
        st.markdown("### 🪖 Sentinel AI - Interactive Defense Consultation")
        st.caption("A private, real-time consultation space powered by AI, tailored for defense personnel navigating field fatigue, operational stress, and mental well-being.")

        context_str = "No recent individual evaluation data provided."
        if 'latest_eval' in st.session_state:
            eval_data = st.session_state['latest_eval']
            context_str = f"""
            - Risk Level: {eval_data['risk_tier']} ({eval_data['high_prob']}% High Stress Probability)
            - PHQ-9 Depression Score: {eval_data['phq9']}/27
            - GAD-7 Anxiety Score: {eval_data['gad7']}/21
            - Average Sleep: {eval_data['sleep']} hours/day
            - Months Since Last Leave: {eval_data['months_leave']} months
            - Posting Type: {eval_data['posting']}
            """
            st.info(f"**Synced Assessment Context:** Risk: **{eval_data['risk_tier']}** | PHQ-9: **{eval_data['phq9']}** | GAD-7: **{eval_data['gad7']}** | Sleep: **{eval_data['sleep']} hrs**")

        system_instruction = f"""
        You are Sentinel AI, an expert military psychologist and defense mental readiness therapist.
        Your mission is to provide empathetic, highly realistic, supportive, and conversational therapy to defense personnel.

        Guidelines for your tone and structure:
        1. **Empathetic & Grounded:** Speak calmly, respectfully, and with deep understanding of military culture, operational fatigue, high-intensity duty, and family separation.
        2. **Truly Conversational:** DO NOT send bulleted rule-lists or mechanical scripts every time. Respond naturally to what the user actually said. Ask one thoughtful open-ended follow-up question to keep the dialogue flowing naturally.
        3. **Evidence-Based Coping:** Offer practical, field-applicable psychological tools (e.g., box breathing, grounding exercises, cognitive reframing) when relevant, but deliver them organically in natural conversation.
        4. **Context Awareness:** The personnel's latest evaluation data is:
           {context_str}
           Use this context subtly to guide your empathy without being intrusive.
        5. **Safety Guardrail:** If the user expresses explicit self-harm or severe crisis thoughts, gently urge them to contact immediate unit medical officers or confidential crisis lines.
        """

        if "messages" not in st.session_state:
            st.session_state.messages = [
                {
                    "role": "model",
                    "parts": [f"Hello {st.session_state.user_fullname}. I'm Sentinel AI, your confidential mental readiness consultant. Whether you're dealing with operational fatigue, sleep difficulty, or deployment pressure, this space is completely private. How are you holding up today?"]
                }
            ]

        for msg in st.session_state.messages:
            role = "user" if msg["role"] == "user" else "assistant"
            with st.chat_message(role):
                st.markdown(msg["parts"][0])

        if prompt := st.chat_input("Type your message confidentially..."):
            st.session_state.messages.append({"role": "user", "parts": [prompt]})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                if not GEMINI_API_KEY:
                    st.error("⚠️ Gemini API Key not detected.")
                else:
                    with st.spinner("Sentinel AI is responding..."):
                        try:
                            client = genai.Client(api_key=GEMINI_API_KEY)
                            response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=[
                                    types.Content(role=m["role"], parts=[types.Part.from_text(text=m["parts"][0])])
                                    for m in st.session_state.messages
                                ],
                                config=types.GenerateContentConfig(
                                    system_instruction=system_instruction,
                                    temperature=0.7,
                                    max_output_tokens=500
                                )
                            )
                            bot_reply = response.text
                            st.markdown(bot_reply)
                            st.session_state.messages.append({"role": "model", "parts": [bot_reply]})
                        except Exception as e:
                            st.warning(f"*(API Connection Error: {e})*")

        st.markdown("---")
        st.caption("🚨 **Emergency Note:** Sentinel AI is designed for psychological support and stress mitigation. For acute emergency or immediate crisis support, please contact your unit medical officer or call the confidential military helpline.")