import streamlit as st
import pandas as pd
import numpy as np
import os
import io
import time
import json
import uuid
import difflib
from datetime import datetime, timedelta
from pathlib import Path
from app.core.handlers import load_file_to_df, get_sheet_names
from app.core.processors import fill_service_small_from_mid, apply_sorting, apply_dedup

# --- Persistence Setup ---
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

# --- CSS for Landing Only ---
LANDING_CSS = """
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * { font-family: 'Pretendard', sans-serif; }
    
    /* Absolute Centering */
    .main .block-container {
        padding-top: 10rem !important;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    
    .login-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 28px;
        padding: 45px 40px;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.04);
        width: 100%;
        max-width: 400px;
        display: flex;
        flex-direction: column;
        align-items: center; /* Center items inside the card */
        text-align: center;
    }
    
    /* Radio Centering */
    .stRadio { display: flex; justify-content: center; width: 100%; }
    .stRadio > div { display: flex; justify-content: center; gap: 20px; width: 100%; }
    
    /* Button & Input Full Width Centering */
    .stButton, .stButton > button { width: 100% !important; display: flex; justify-content: center; align-items: center; }
    .stTextInput { width: 100%; }
    
    .stButton>button {
        background: #2563eb !important;
        color: white !important; font-weight: 700 !important;
        border-radius: 12px !important; padding: 14px !important; border: none !important;
        text-align: center;
    }
    .stTextInput>div>div>input {
        border-radius: 12px !important; border: 1px solid #e2e8f0 !important; 
        text-align: center; height: 52px !important; font-size: 0.95rem !important;
    }
    
    .hero-title {
        color: #2563eb; font-weight: 800; letter-spacing: -2.5px; 
        font-size: 3.2rem; margin-bottom: 0px; text-align: center;
    }
    .hero-sub { color: #64748b; font-size: 1rem; margin-bottom: 2.5rem; text-align: center; }
    </style>
"""

# --- Logic ---
def fuzzy_match_logic(key, targets, threshold=0.6):
    matches = difflib.get_close_matches(str(key), [str(t) for t in targets], n=1, cutoff=threshold)
    return matches[0] if matches else None

def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- Auth UI ---

def show_landing():
    st.markdown(LANDING_CSS, unsafe_allow_html=True)
    
    # Hero Section
    st.markdown("<h1 class='hero-title'>DATA INTEL PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p class='hero-sub'>Expert Intelligence for Enterprise</p>", unsafe_allow_html=True)
    
    # Login Card Centering Wrapper
    empty_l, center_col, empty_r = st.columns([1, 1.2, 1])
    
    with center_col:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h4 style='margin-bottom: 30px; font-weight: 800; color: #1e293b; text-align: center;'>보안 인증 로그인</h4>", unsafe_allow_html=True)
        
        mode = st.radio("", ["라이선스 사용자", "관리자 접속"], horizontal=True, label_visibility="collapsed")
        
        settings = load_json(SETTINGS_FILE, {"master_password": "0303"})
        users = load_json(USERS_FILE, [])
        
        st.write("")
        
        if mode == "관리자 접속":
            pwd = st.text_input("ADMIN PWD", type="password", placeholder="마스터 암호", label_visibility="collapsed")
            if st.button("🚀 시스템 접속"):
                if pwd == settings["master_password"]:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "admin"
                    add_log("ADMIN", "Admin Access")
                    st.rerun()
                else: st.error("정보 불일치")
        else:
            in_name = st.text_input("USER NAME", placeholder="성함 (예: 홍길동)", label_visibility="collapsed").strip()
            in_lic = st.text_input("LICENSE", type="password", placeholder="라이선스 번호", label_visibility="collapsed").strip()
            if st.button("🚀 시스템 접속"):
                user = next((u for u in users if u["name"] == in_name and u["license"] == in_lic), None)
                if user:
                    expiry = datetime.strptime(user["expiry"], "%Y-%m-%d")
                    if expiry < datetime.now(): st.error("기간 만료")
                    else:
                        st.session_state.authenticated = True
                        st.session_state.user_role = "user"
                        st.session_state.current_user = user
                        add_log(in_name, "Login Success")
                        st.rerun()
                else: st.error("정보 불일치")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #cbd5e1; font-size: 0.75rem; margin-top: 2.5rem;'>© 2026 Seeun Park. All rights reserved.</p>", unsafe_allow_html=True)

# --- Main Application ---

def show_main_app():
    st.markdown("""<style>@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css'); * { font-family: 'Pretendard', sans-serif; }</style>""", unsafe_allow_html=True)
    with st.sidebar:
        st.markdown(f"### 💎 Data Intel PRO")
        st.caption(f"User: {st.session_state.current_user['name'] if st.session_state.current_user else 'ADMIN'}")
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.rerun()
        st.divider()

    st.markdown("<h2 style='font-weight: 800; color: #1e293b; margin-bottom: 2rem;'>Expert Workspace</h2>", unsafe_allow_html=True)
    tabs = st.tabs(["🔗 매칭", "📄 추출", "📊 분석", "📂 병합"] + (["⚙️ 관리"] if st.session_state.user_role == "admin" else []))
    
    with tabs[0]:
        st.markdown('<div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #f1f5f9;">', unsafe_allow_html=True)
        b_f = st.file_uploader("원본", key="b_f")
        r_f = st.file_uploader("참조", key="r_f")
        if b_f and r_f:
            b_df, r_df = load_file_to_df(b_f), load_file_to_df(r_f)
            b_k = st.selectbox("기준", b_df.columns)
            r_k = st.selectbox("참조", r_df.columns)
            r_cols = st.multiselect("컬럼", [c for c in r_df.columns if c != r_k])
            if st.button("🚀 실행"):
                res = pd.merge(b_df, r_df[[r_k] + r_cols], left_on=b_k, right_on=r_k, how='left')
                st.dataframe(res.head(100))
                st.download_button("📥 Excel 다운로드", convert_df_to_excel(res), "result.xlsx")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Entry ---
def main():
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False
    if not st.session_state.authenticated: show_landing()
    else: show_main_app()

if __name__ == "__main__": main()
