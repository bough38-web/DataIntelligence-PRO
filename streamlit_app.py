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

# --- Session State ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_role' not in st.session_state: st.session_state.user_role = "user"
if 'current_user' not in st.session_state: st.session_state.current_user = None

# --- MODERN PROFESSIONAL CSS ---
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    * { font-family: 'Pretendard', sans-serif; }
    
    /* Perfect Center */
    .main .block-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 100vh;
        max-width: 100%;
        background-color: #fcfcfd;
        overflow: hidden;
    }
    
    .stApp { background: transparent; }
    
    .hero-container { text-align: center; margin-bottom: 2rem; }
    
    .hero-title {
        font-size: 4rem; font-weight: 800; color: #111827;
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
        letter-spacing: -3px; margin-bottom: 5px;
    }
    .hero-sub { color: #6b7280; font-size: 1.2rem; font-weight: 500; }
    
    /* Clean Solid Card */
    .login-card {
        background: #ffffff;
        border: 1px solid #f1f5f9;
        border-radius: 32px;
        padding: 50px;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.04);
        width: 100%;
        max-width: 460px;
        text-align: center;
    }
    
    .stButton>button {
        background: #2563eb !important;
        color: white !important; font-weight: 700 !important;
        border-radius: 12px !important; padding: 15px !important; width: 100% !important; border: none !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:hover { background: #1d4ed8 !important; transform: translateY(-1px); }
    
    .stTextInput>div>div>input {
        border-radius: 12px !important; border: 1.5px solid #e2e8f0 !important; 
        text-align: center; height: 55px !important; font-size: 1rem !important;
        background-color: #f8fafc !important;
    }
    .stTextInput>div>div>input:focus { border-color: #2563eb !important; background-color: #ffffff !important; }
    
    .footer { position: fixed; bottom: 20px; right: 30px; color: #cbd5e1; font-size: 0.85rem; }
    
    .stRadio > div { justify-content: center; gap: 20px; }
    </style>
    """, unsafe_allow_html=True)

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
    st.markdown("<div class='hero-container'>", unsafe_allow_html=True)
    st.markdown("<h1 class='hero-title'>DATA INTEL PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p class='hero-sub'>Modern Data Intelligence for Enterprise</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown("<h3 style='margin-bottom: 30px; font-weight: 700; color: #111827;'>보안 인증 로그인</h3>", unsafe_allow_html=True)
    
    mode = st.radio("", ["라이선스 사용자", "관리자 접속"], horizontal=True, label_visibility="collapsed")
    
    settings = load_json(SETTINGS_FILE, {"master_password": "0303"})
    users = load_json(USERS_FILE, [])
    
    st.write("")
    
    if mode == "관리자 접속":
        pwd = st.text_input("ADMIN PWD", type="password", placeholder="마스터 암호 입력", label_visibility="collapsed")
        if st.button("🚀 어드민 접속"):
            if pwd == settings["master_password"]:
                st.session_state.authenticated = True
                st.session_state.user_role = "admin"
                add_log("ADMIN", "Admin Access Success")
                st.rerun()
            else: st.error("정보가 일치하지 않습니다.")
    else:
        in_name = st.text_input("USER NAME", placeholder="성함 (예: 홍길동)", label_visibility="collapsed").strip()
        in_lic = st.text_input("LICENSE NUMBER", type="password", placeholder="라이선스 번호", label_visibility="collapsed").strip()
        if st.button("🚀 시스템 로그인"):
            user = next((u for u in users if u["name"] == in_name and u["license"] == in_lic), None)
            if user:
                expiry = datetime.strptime(user["expiry"], "%Y-%m-%d")
                if expiry < datetime.now(): st.error("만료된 라이선스입니다.")
                else:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "user"
                    st.session_state.current_user = user
                    add_log(in_name, "User Login Success")
                    st.rerun()
            else: st.error("이름 또는 번호가 일치하지 않습니다.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="footer">© 2026 Seeun Park. All rights reserved.</div>', unsafe_allow_html=True)

# --- Main Application ---

def show_main_app():
    with st.sidebar:
        st.markdown(f"### 💎 Data Intel")
        st.caption(f"User: {st.session_state.current_user['name'] if st.session_state.current_user else 'ADMIN'}")
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.rerun()
        st.divider()
        if st.session_state.user_role == "user":
            st.markdown("#### 보안 설정")
            new_p = st.text_input("라이선스 키 변경", type="password")
            if st.button("변경 저장"):
                users = load_json(USERS_FILE, [])
                for u in users:
                    if u["license"] == st.session_state.current_user["license"]:
                        u["license"] = new_p
                save_json(USERS_FILE, users)
                st.success("업데이트 완료")

    st.markdown("<h2 style='font-weight: 800; color: #111827; margin-bottom: 2rem;'>Expert Workspace</h2>", unsafe_allow_html=True)
    
    app_tabs = ["🔗 스마트 매칭", "📄 정밀 추출", "📊 심층 분석", "📂 스마트 병합"]
    if st.session_state.user_role == "admin": app_tabs.append("⚙️ 관리 & 모니터링")
    
    tabs = st.tabs(app_tabs)
    
    # Matching
    with tabs[0]:
        st.markdown('<div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #f1f5f9;">', unsafe_allow_html=True)
        st.markdown("##### 🔗 지능형 데이터 매칭")
        b_f = st.file_uploader("원본 업로드", key="b_f")
        r_f = st.file_uploader("참조 업로드", key="r_f")
        if b_f and r_f:
            b_df, r_df = load_file_to_df(b_f), load_file_to_df(r_f)
            b_k = st.selectbox("기준 키", b_df.columns)
            r_k = st.selectbox("매칭 키", r_df.columns)
            r_cols = st.multiselect("가져올 컬럼", [c for c in r_df.columns if c != r_k])
            if st.button("🚀 실행"):
                res = pd.merge(b_df, r_df[[r_k] + r_cols], left_on=b_k, right_on=r_k, how='left')
                st.dataframe(res.head(100))
                st.download_button("📥 Excel 다운로드", convert_df_to_excel(res), "match.xlsx")
        st.markdown('</div>', unsafe_allow_html=True)

    # Admin Control
    if st.session_state.user_role == "admin":
        with tabs[-1]:
            st.subheader("Monitoring")
            logs = load_json(LOGS_FILE, [])
            if logs: st.dataframe(pd.DataFrame(logs[::-1]).head(10), use_container_width=True)
            st.divider()
            st.subheader("Users")
            with st.form("reg"):
                c1, c2, c3 = st.columns(3)
                u_n = c1.text_input("성함")
                u_p = c2.text_input("휴대폰")
                u_d = c3.number_input("일수", value=30)
                if st.form_submit_button("등록"):
                    new_lic = str(uuid.uuid4())[:8].upper()
                    users = load_json(USERS_FILE, [])
                    users.append({"name":u_n, "phone":u_p, "license":new_lic, "expiry":(datetime.now()+timedelta(days=u_d)).strftime("%Y-%m-%d")})
                    save_json(USERS_FILE, users)
                    st.success(f"[{u_n}] 발급 키: {new_lic}")
                    st.rerun()

# --- Entry ---
def main():
    if not st.session_state.authenticated: show_landing()
    else: show_main_app()

if __name__ == "__main__": main()
