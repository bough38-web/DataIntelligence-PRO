import streamlit as st
import pandas as pd
import numpy as np
import os
import io
import time
import json
import uuid
import difflib
import sys
from datetime import datetime, timedelta
from pathlib import Path

# --- Path Setup ---
ROOT_DIR = Path(__file__).parent.absolute()
if str(ROOT_DIR) not in sys.path: sys.path.append(str(ROOT_DIR))

try:
    from app.core.handlers import load_file_to_df, get_sheet_names
    from app.core.processors import fill_service_small_from_mid, apply_sorting, apply_dedup
except ImportError:
    def load_file_to_df(f): return pd.read_excel(f) if f.name.endswith('xlsx') else pd.read_csv(f)

# --- Persistence ---
AUTH_DIR = Path.home() / ".dataintelligence_pro"
AUTH_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = AUTH_DIR / "auth_settings.json"
USERS_FILE = AUTH_DIR / "users.json"
LOGS_FILE = AUTH_DIR / "logs.json"

def load_json(path, default):
    if not path.exists(): return default
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

def add_log(user_name, action):
    logs = load_json(LOGS_FILE, [])
    logs.append({"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "user": user_name, "action": action})
    save_json(LOGS_FILE, logs[-1000:])

# --- Page Config ---
st.set_page_config(page_title="Data Intel PRO", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

# --- UI Styling (Immersive Premium) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&family=Pretendard:wght@400;600;700;800&display=swap');
    * { font-family: 'Pretendard', sans-serif; }
    [data-testid="stAppViewContainer"] > section:nth-child(2) > div:nth-child(1) > div > div {
        display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 90vh;
    }
    .stApp { background-color: #f8fafc; }
    .login-card {
        background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.4); border-radius: 40px; padding: 60px 50px;
        box-shadow: 0 40px 100px -20px rgba(0, 0, 0, 0.08); width: 100%; max-width: 440px; text-align: center;
    }
    .stButton, .stButton > button { width: 100% !important; }
    .stButton > button {
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%) !important; color: white !important;
        font-weight: 800 !important; font-size: 1.2rem !important; border-radius: 20px !important; padding: 18px !important;
        border: none !important; box-shadow: 0 15px 30px rgba(37, 99, 235, 0.3) !important;
    }
    .brand-title {
        font-family: 'Outfit', sans-serif; font-size: 5rem; font-weight: 900;
        background: linear-gradient(135deg, #0f172a 0%, #2563eb 50%, #60a5fa 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -4px; margin-bottom: 0px;
    }
    .brand-sub { color: #64748b; font-size: 1.2rem; font-weight: 500; text-align: center; margin-bottom: 40px; }
    .stRadio > div { justify-content: center; gap: 30px; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def safe_merge(left_df, right_df, left_on, right_on, selected_cols):
    l_copy, r_copy = left_df.copy(), right_df.copy()
    l_copy[left_on] = l_copy[left_on].astype(str).str.strip()
    r_copy[right_on] = r_copy[right_on].astype(str).str.strip()
    return pd.merge(l_copy, r_copy[[right_on] + selected_cols], left_on=left_on, right_on=right_on, how='left')

def convert_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False)
    return output.getvalue()

# --- Auth ---
def show_landing():
    st.markdown("<h1 class='brand-title'>DATA INTEL PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p class='brand-sub'>Experience the Future of Enterprise Intelligence</p>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1, 1.6, 1])
    with center_col:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h2 style='margin-bottom: 40px; font-weight: 800; color: #0f172a; font-size: 1.8rem;'>인증 포털</h2>", unsafe_allow_html=True)
        mode = st.radio("", ["라이선스 사용자", "관리자 접속"], horizontal=True, label_visibility="collapsed")
        users = load_json(USERS_FILE, [])
        settings = load_json(SETTINGS_FILE, {"master_password": "0303"})
        
        if mode == "관리자 접속":
            pwd = st.text_input("ADMIN PWD", type="password", placeholder="마스터 암호 입력", label_visibility="collapsed")
            if st.button("🚀 UNLOCK SYSTEM"):
                if pwd == settings["master_password"]:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "admin"
                    st.session_state.current_user = {"name": "ADMIN"} # Fix: Set current_user for Admin
                    add_log("ADMIN", "Login")
                    st.rerun()
                else: st.error("정보 불일치")
        else:
            in_name = st.text_input("USER NAME", placeholder="성함 (예: 홍길동)", label_visibility="collapsed").strip()
            in_lic = st.text_input("KEY", type="password", placeholder="라이선스 번호 입력", label_visibility="collapsed").strip()
            if st.button("🚀 SIGN IN TO PRO"):
                user = next((u for u in users if u["name"] == in_name and u["license"] == in_lic), None)
                if user:
                    exp = datetime.strptime(user["expiry"], "%Y-%m-%d")
                    if exp < datetime.now(): st.error("만료됨")
                    else:
                        st.session_state.authenticated = True
                        st.session_state.user_role = "user"
                        st.session_state.current_user = user
                        add_log(in_name, "Login")
                        st.rerun()
                else: st.error("정보 불일치")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Main App ---
def show_main_app():
    # Safety Check: Redirect to landing if state is lost
    if not st.session_state.get('authenticated', False) or st.session_state.get('current_user') is None:
        st.session_state.authenticated = False
        st.rerun()

    with st.sidebar:
        st.markdown(f"### 💎 Data Intel PRO")
        # Safe access to current_user
        user_info = st.session_state.current_user
        st.caption(f"접속: {user_info.get('name', 'UNKNOWN')}")
        
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.rerun()
        st.divider()

    st.markdown("<h2 style='font-weight: 800; color: #1e293b; margin-bottom: 2rem;'>Expert Workspace</h2>", unsafe_allow_html=True)
    tabs = st.tabs(["🔗 매칭", "📄 추출", "📊 분석", "📂 병합"] + (["⚙️ 관리"] if st.session_state.user_role == "admin" else []))
    
    with tabs[0]:
        st.markdown('<div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #f1f5f9;">', unsafe_allow_html=True)
        b_f, r_f = st.file_uploader("원본", key="b_f"), st.file_uploader("참조", key="r_f")
        if b_f and r_f:
            b_df, r_df = load_file_to_df(b_f), load_file_to_df(r_f)
            b_k, r_k = st.selectbox("기준 키", b_df.columns), st.selectbox("매칭 키", r_df.columns)
            r_cols = st.multiselect("가져올 컬럼", [c for c in r_df.columns if c != r_k])
            if st.button("🚀 매칭 실행"):
                res = safe_merge(b_df, r_df, b_k, r_k, r_cols)
                st.dataframe(res.head(100))
                st.download_button("📥 Excel 다운로드", convert_to_excel(res), "result.xlsx")
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.user_role == "admin":
        with tabs[-1]:
            st.subheader("Admin Control Panel")
            users = load_json(USERS_FILE, [])
            with st.form("reg"):
                c1, c2, c3 = st.columns(3)
                u_n, u_p, u_d = c1.text_input("성함"), c2.text_input("휴대폰"), c3.number_input("일수", value=30)
                if st.form_submit_button("✅ 신규 등록"):
                    new_lic = str(uuid.uuid4())[:8].upper()
                    users.append({"name":u_n, "phone":u_p, "license":new_lic, "expiry":(datetime.now()+timedelta(days=u_d)).strftime("%Y-%m-%d")})
                    save_json(USERS_FILE, users)
                    st.success(f"[{u_n}] 키: {new_lic}")
                    st.rerun()

# --- Entry ---
def main():
    # Global Session State Initialization (Fix for AttributeError)
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False
    if 'current_user' not in st.session_state: st.session_state.current_user = None
    if 'user_role' not in st.session_state: st.session_state.user_role = "user"
    
    if not st.session_state.authenticated: show_landing()
    else: show_main_app()

if __name__ == "__main__": main()
