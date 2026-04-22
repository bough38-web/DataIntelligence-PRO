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
    from app.core.handlers import load_file_to_df
except ImportError:
    def load_file_to_df(f):
        if f.name.endswith('xlsx'): return pd.read_excel(f, engine='openpyxl')
        return pd.read_csv(f)

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

# --- Page Config ---
st.set_page_config(page_title="Data Intel PRO", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

# --- ROBUST UI STYLING ---
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * { font-family: 'Pretendard', sans-serif; }
    
    .stApp { background-color: #f8fafc; }
    
    /* Centering Container */
    .main-center-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        width: 100%;
        margin-top: 5vh;
    }
    
    /* Clean White Card */
    .login-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 30px;
        padding: 50px 40px;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.05);
        width: 100%;
        max-width: 420px;
        text-align: center;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%) !important;
        color: white !important; font-weight: 700 !important;
        border-radius: 12px !important; padding: 14px !important; width: 100% !important; border: none !important;
    }
    
    .stTextInput > div > div > input {
        border-radius: 12px !important; border: 1px solid #e2e8f0 !important; 
        text-align: center; height: 50px !important;
    }
    
    .hero-title {
        color: #1e3a8a; font-weight: 800; font-size: 3.5rem; letter-spacing: -2.5px;
        text-align: center; margin-bottom: 5px;
    }
    .hero-sub { color: #64748b; font-size: 1.1rem; text-align: center; margin-bottom: 2rem; }
    
    .stRadio > div { justify-content: center; gap: 20px; }
    </style>
""", unsafe_allow_html=True)

def convert_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False)
    return output.getvalue()

# --- Auth ---
def show_landing():
    # Use standard Streamlit columns for horizontal centering
    _, center_col, _ = st.columns([1, 1.5, 1])
    
    with center_col:
        st.markdown("<div class='main-center-container'>", unsafe_allow_html=True)
        st.markdown("<h1 class='hero-title'>DATA INTEL PRO</h1>", unsafe_allow_html=True)
        st.markdown("<p class='hero-sub'>Expert Intelligence for Enterprise</p>", unsafe_allow_html=True)
        
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='margin-bottom: 25px; font-weight: 700; color: #1e293b;'>보안 인증 로그인</h3>", unsafe_allow_html=True)
        
        mode = st.radio("", ["라이선스 사용자", "관리자 접속"], horizontal=True, label_visibility="collapsed")
        users = load_json(USERS_FILE, [])
        settings = load_json(SETTINGS_FILE, {"master_password": "0303"})
        
        if mode == "관리자 접속":
            pwd = st.text_input("ADMIN PWD", type="password", placeholder="마스터 암호", label_visibility="collapsed")
            if st.button("🚀 시스템 접속"):
                if pwd == settings["master_password"]:
                    st.session_state.authenticated, st.session_state.user_role = True, "admin"
                    st.session_state.current_user = {"name": "ADMIN"}
                    st.rerun()
                else: st.error("정보 불일치")
        else:
            in_name = st.text_input("USER NAME", placeholder="성함 (예: 홍길동)", label_visibility="collapsed").strip()
            in_lic = st.text_input("LICENSE", type="password", placeholder="라이선스 번호", label_visibility="collapsed").strip()
            if st.button("🚀 시스템 접속"):
                user = next((u for u in users if u["name"] == in_name and u["license"] == in_lic), None)
                if user:
                    st.session_state.authenticated, st.session_state.user_role, st.session_state.current_user = True, "user", user
                    st.rerun()
                else: st.error("정보 불일치")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

def show_main_app():
    with st.sidebar:
        st.markdown(f"### 💎 Data Intel")
        st.caption(f"접속: {st.session_state.current_user.get('name', 'USER')}")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()

    st.markdown("<h2 style='font-weight: 800; color: #1e293b; margin-bottom: 2rem;'>Expert Workspace</h2>", unsafe_allow_html=True)
    tabs = st.tabs(["🔗 매칭", "📄 추출", "📊 분석", "📂 병합"] + (["⚙️ 관리"] if st.session_state.user_role == "admin" else []))
    
    with tabs[0]:
        st.markdown('<div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #f1f5f9;">', unsafe_allow_html=True)
        b_f, r_f = st.file_uploader("원본", key="b_f"), st.file_uploader("참조", key="r_f")
        if b_f and r_f:
            b_df, r_df = load_file_to_df(b_f), load_file_to_df(r_f)
            b_k, r_k = st.selectbox("기준 키", b_df.columns), st.selectbox("매칭 키", r_df.columns)
            r_cols = st.multiselect("컬럼", [c for c in r_df.columns if c != r_k])
            if st.button("🚀 실행"):
                b_df[b_k] = b_df[b_k].astype(str).str.strip()
                r_df[r_k] = r_df[r_k].astype(str).str.strip()
                res = pd.merge(b_df, r_df[[r_k] + r_cols], left_on=b_k, right_on=r_k, how='left')
                st.dataframe(res.head(100))
                st.download_button("📥 다운로드", convert_to_excel(res), "result.xlsx")
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

def main():
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False
    if 'current_user' not in st.session_state: st.session_state.current_user = None
    if 'user_role' not in st.session_state: st.session_state.user_role = "user"
    if not st.session_state.authenticated: show_landing()
    else: show_main_app()

if __name__ == "__main__": main()
