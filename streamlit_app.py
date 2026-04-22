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

# --- UI Styling ---
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * { font-family: 'Pretendard', sans-serif; }
    [data-testid="stAppViewContainer"] > section:nth-child(2) > div:nth-child(1) > div > div {
        display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 100vh;
    }
    .stApp { background-color: #fcfcfd; }
    .login-card {
        background: #ffffff; border: 1px solid #f1f5f9; border-radius: 32px;
        padding: 50px 40px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.05);
        width: 100%; max-width: 420px; text-align: center;
    }
    .stButton, .stButton > button { width: 100% !important; }
    .stButton > button {
        background: #2563eb !important; color: white !important; font-weight: 700 !important;
        border-radius: 14px !important; padding: 15px !important; border: none !important;
    }
    .hero-title { font-size: 3.5rem; font-weight: 800; color: #1e40af; text-align: center; margin-bottom: 0px; }
    .hero-sub { color: #64748b; font-size: 1rem; text-align: center; margin-bottom: 2.5rem; }
    .stRadio > div { justify-content: center; gap: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- Helper Functions (Fix Prob 1) ---
def safe_merge(left_df, right_df, left_on, right_on, selected_cols):
    # Fix Problem 1: Ensure keys are the same type (string) for accurate matching
    l_copy = left_df.copy()
    r_copy = right_df.copy()
    l_copy[left_on] = l_copy[left_on].astype(str).str.strip()
    r_copy[right_on] = r_copy[right_on].astype(str).str.strip()
    
    res = pd.merge(l_copy, r_copy[[right_on] + selected_cols], left_on=left_on, right_on=right_on, how='left')
    return res

def convert_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False)
    return output.getvalue()

# --- Auth ---
def show_landing():
    st.markdown("<h1 class='hero-title'>DATA INTEL PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p class='hero-sub'>Precision Intelligence for Modern Enterprise</p>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1, 1.5, 1])
    with center_col:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h4 style='margin-bottom: 30px; font-weight: 800; color: #0f172a;'>보안 인증 로그인</h4>", unsafe_allow_html=True)
        mode = st.radio("", ["라이선스 사용자", "관리자 접속"], horizontal=True, label_visibility="collapsed")
        users = load_json(USERS_FILE, [])
        settings = load_json(SETTINGS_FILE, {"master_password": "0303"})
        
        if mode == "관리자 접속":
            pwd = st.text_input("ADMIN PWD", type="password", placeholder="마스터 암호", label_visibility="collapsed")
            if st.button("🚀 시스템 접속"):
                if pwd == settings["master_password"]:
                    st.session_state.authenticated, st.session_state.user_role = True, "admin"
                    add_log("ADMIN", "Login")
                    st.rerun()
                else: st.error("정보 불일치")
        else:
            in_name = st.text_input("NAME", placeholder="성함 (예: 홍길동)", label_visibility="collapsed").strip()
            in_lic = st.text_input("KEY", type="password", placeholder="라이선스 번호", label_visibility="collapsed").strip()
            if st.button("🚀 시스템 접속"):
                # Fix Problem 2: Authentication logic handles duplicates by picking the valid one
                user = next((u for u in users if u["name"] == in_name and u["license"] == in_lic), None)
                if user:
                    exp = datetime.strptime(user["expiry"], "%Y-%m-%d")
                    if exp < datetime.now(): st.error("만료됨")
                    else:
                        st.session_state.authenticated, st.session_state.user_role, st.session_state.current_user = True, "user", user
                        add_log(in_name, "Login")
                        st.rerun()
                else: st.error("정보 불일치")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Main ---
def show_main_app():
    with st.sidebar:
        st.markdown(f"### 💎 Data Intel")
        st.caption(f"User: {st.session_state.current_user['name'] if st.session_state.current_user else 'ADMIN'}")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()
        st.divider()

    st.markdown("<h2 style='font-weight: 800; color: #1e293b; margin-bottom: 2rem;'>Expert Workspace</h2>", unsafe_allow_html=True)
    tabs = st.tabs(["🔗 스마트 매칭", "📄 정밀 추출", "📊 심층 분석", "📂 스마트 병합"] + (["⚙️ 관리"] if st.session_state.user_role == "admin" else []))
    
    with tabs[0]:
        st.markdown('<div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #f1f5f9;">', unsafe_allow_html=True)
        st.markdown("##### 🔗 지능형 데이터 매칭")
        b_f = st.file_uploader("원본 파일", key="b_f")
        r_f = st.file_uploader("참조 파일", key="r_f")
        if b_f and r_f:
            b_df, r_df = load_file_to_df(b_f), load_file_to_df(r_f)
            b_k, r_k = st.selectbox("기준 키", b_df.columns), st.selectbox("매칭 키", r_df.columns)
            r_cols = st.multiselect("컬럼", [c for c in r_df.columns if c != r_k])
            if st.button("🚀 실행"):
                # Problem 1 Solved: Safe Merge
                res = safe_merge(b_df, r_df, b_k, r_k, r_cols)
                st.dataframe(res.head(100))
                st.download_button("📥 Excel 다운로드", convert_to_excel(res), "result.xlsx")
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.user_role == "admin":
        with tabs[-1]:
            st.subheader("Admin Control")
            users = load_json(USERS_FILE, [])
            with st.form("reg"):
                c1, c2, c3 = st.columns(3)
                u_n, u_p, u_d = c1.text_input("이름"), c2.text_input("휴대폰"), c3.number_input("일수", value=30)
                if st.form_submit_button("등록"):
                    # Fix Problem 2: Duplicate check
                    if any(u["name"] == u_n for u in users):
                        st.warning("이미 등록된 이름입니다. 기존 정보가 유지되거나 갱신될 수 있습니다.")
                    new_lic = str(uuid.uuid4())[:8].upper()
                    users.append({"name":u_n, "phone":u_p, "license":new_lic, "expiry":(datetime.now()+timedelta(days=u_d)).strftime("%Y-%m-%d")})
                    save_json(USERS_FILE, users)
                    st.success(f"Key: {new_lic}")
                    st.rerun()

def main():
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False
    if not st.session_state.authenticated: show_landing()
    else: show_main_app()

if __name__ == "__main__": main()
