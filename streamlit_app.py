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
st.set_page_config(page_title="Data Intel PRO | Enterprise", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

# --- Session State ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_role' not in st.session_state: st.session_state.user_role = "user"
if 'current_user' not in st.session_state: st.session_state.current_user = None

# --- Custom Premium Style ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&family=Pretendard:wght@400;600;700;800&display=swap');
    * { font-family: 'Pretendard', sans-serif; }
    .stApp { background: linear-gradient(135deg, #f8fafc 0%, #ffffff 50%, #f1f5f9 100%); }
    .hero-title {
        font-family: 'Outfit', sans-serif; font-size: 4.8rem; font-weight: 900; text-align: center;
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
        margin-top: 60px; margin-bottom: 5px;
    }
    .login-card {
        background: white; border: 1px solid #e2e8f0; border-radius: 40px;
        padding: 50px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.05);
        max-width: 520px; margin: 0 auto; display: flex; flex-direction: column; align-items: center;
    }
    .premium-card {
        background: white; padding: 25px; border-radius: 20px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; margin-bottom: 20px;
    }
    .stButton>button {
        background: #2563eb !important; color: white !important; font-weight: 800 !important;
        border-radius: 16px !important; padding: 14px !important;
    }
    .stTextInput>div>div>input { border-radius: 12px !important; border: 1px solid #cbd5e1 !important; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- Logic Modules ---

def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def fuzzy_match_logic(key, targets, threshold=0.6):
    matches = difflib.get_close_matches(str(key), [str(t) for t in targets], n=1, cutoff=threshold)
    return matches[0] if matches else None

# --- Auth UI ---

def show_landing():
    st.markdown("<h1 class='hero-title'>DATA INTEL PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b; font-size: 1.4rem; margin-bottom: 50px;'>Enterprise Data Intelligence Suite</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; font-weight: 800; margin-bottom: 30px;'>Authentication</h2>", unsafe_allow_html=True)
        
        mode = st.radio("", ["Master Access", "User Login"], horizontal=True, label_visibility="collapsed")
        
        settings = load_json(SETTINGS_FILE, {"master_password": "0303"})
        users = load_json(USERS_FILE, [])
        
        if mode == "Master Access":
            pwd = st.text_input("PASSWORD", type="password", placeholder="Enter Master Password", label_visibility="collapsed")
            if st.button("AUTHORIZE AS ADMIN"):
                if pwd == settings["master_password"]:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "admin"
                    add_log("ADMIN", "Admin Login Success")
                    st.rerun()
                else: st.error("Password Mismatch.")
        else:
            lic = st.text_input("LICENSE KEY", type="password", placeholder="Enter Key", label_visibility="collapsed")
            if st.button("VERIFY & ENTER"):
                user = next((u for u in users if u["license"] == lic), None)
                if user:
                    expiry = datetime.strptime(user["expiry"], "%Y-%m-%d")
                    if expiry < datetime.now():
                        st.error(f"만료됨: {user['expiry']}")
                    else:
                        st.session_state.authenticated = True
                        st.session_state.user_role = "user"
                        st.session_state.current_user = user
                        add_log(user["name"], "User Login Success")
                        st.rerun()
                else: st.error("Invalid Key.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="position: fixed; bottom: 20px; right: 30px; color: #cbd5e1;">© 2026 Seeun Park. All rights reserved.</div>', unsafe_allow_html=True)

# --- Main Application ---

def show_main_app():
    with st.sidebar:
        st.markdown(f"### 💎 Data Intel PRO")
        if st.button("Logout"):
            add_log(st.session_state.current_user["name"] if st.session_state.current_user else "ADMIN", "Logout")
            st.session_state.authenticated = False
            st.rerun()
        st.divider()
        if st.session_state.user_role == "user":
            st.markdown("#### 👤 My Profile")
            new_k = st.text_input("새 라이선스 키", type="password")
            if st.button("키 변경"):
                users = load_json(USERS_FILE, [])
                for u in users:
                    if u["license"] == st.session_state.current_user["license"]:
                        u["license"] = new_k
                        st.session_state.current_user["license"] = new_k
                        break
                save_json(USERS_FILE, users)
                st.success("변경 완료!")

    st.markdown("<h1 style='color: #0f172a; font-weight: 900; font-size: 2.5rem;'>Expert Suite</h1>", unsafe_allow_html=True)
    
    app_tabs = ["🔗 매칭", "📄 추출", "📊 분석", "📂 병합"]
    if st.session_state.user_role == "admin": app_tabs.append("⚙️ 관리 & 모니터링")
    
    tabs = st.tabs(app_tabs)
    
    # 1. Matching
    with tabs[0]:
        st.markdown('<div class="premium-card">', unsafe_allow_html=True)
        st.markdown("##### 🔗 스마트 매칭")
        b_f = st.file_uploader("원본 업로드", key="b_f")
        r_f = st.file_uploader("참조 업로드", key="r_f")
        if b_f and r_f:
            b_df, r_df = load_file_to_df(b_f), load_file_to_df(r_f)
            b_k = st.selectbox("기준 키", b_df.columns)
            r_k = st.selectbox("매칭 키", r_df.columns)
            r_cols = st.multiselect("필드 선택", [c for c in r_df.columns if c != r_k])
            if st.button("🚀 매칭 실행"):
                res = pd.merge(b_df, r_df[[r_k] + r_cols], left_on=b_k, right_on=r_k, how='left')
                st.dataframe(res.head(100))
                st.download_button("📥 Excel 다운로드", convert_df_to_excel(res), "match.xlsx")
        st.markdown('</div>', unsafe_allow_html=True)

    # 2. Extract
    with tabs[1]:
        e_f = st.file_uploader("가공 대상 업로드", key="e_f")
        if e_f:
            e_df = load_file_to_df(e_f)
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            col_f = st.selectbox("필터 컬럼", e_df.columns)
            val_f = st.text_input("검색어")
            if st.button("📤 추출 실행"):
                res = e_df.copy()
                if val_f: res = res[res[col_f].astype(str).str.contains(val_f, na=False)]
                res = fill_service_small_from_mid(res)
                st.dataframe(res.head(100))
                st.download_button("📥 결과 저장", convert_df_to_excel(res), "extracted.xlsx")
            st.markdown('</div>', unsafe_allow_html=True)

    # Admin Panel (Monitoring & System Password)
    if st.session_state.user_role == "admin":
        with tabs[-1]:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.subheader("📊 시스템 운영 인사이트")
            logs = load_json(LOGS_FILE, [])
            if logs:
                log_df = pd.DataFrame(logs[::-1])
                st.dataframe(log_df.head(10), use_container_width=True)
                st.bar_chart(log_df["user"].value_counts())
            st.markdown('</div>', unsafe_allow_html=True)

            adm_col1, adm_col2 = st.columns(2)
            with adm_col1:
                st.markdown('<div class="premium-card">', unsafe_allow_html=True)
                st.subheader("🛡 관리자 보안 설정")
                new_adm_pwd = st.text_input("마스터 패스워드 변경", type="password", placeholder="New Master PWD")
                if st.button("패스워드 저장"):
                    settings = load_json(SETTINGS_FILE, {"master_password": "0303"})
                    settings["master_password"] = new_adm_pwd
                    save_json(SETTINGS_FILE, settings)
                    add_log("ADMIN", "Master Password Changed")
                    st.success("마스터 패스워드가 변경되었습니다.")
                st.markdown('</div>', unsafe_allow_html=True)

            with adm_col2:
                st.markdown('<div class="premium-card">', unsafe_allow_html=True)
                st.subheader("👥 라이선스 발급")
                with st.form("issue_lic"):
                    u_n = st.text_input("성함/기업")
                    u_d = st.number_input("기간(일)", value=30)
                    if st.form_submit_button("발급"):
                        new_lic = str(uuid.uuid4())[:8].upper()
                        users = load_json(USERS_FILE, [])
                        users.append({"name":u_n, "license":new_lic, "expiry":(datetime.now()+timedelta(days=u_d)).strftime("%Y-%m-%d")})
                        save_json(USERS_FILE, users)
                        add_log("ADMIN", f"License Issued: {u_n}")
                        st.success(f"Key: {new_lic}")
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

# --- Main Entry ---
def main():
    if not st.session_state.authenticated: show_landing()
    else: show_main_app()

if __name__ == "__main__": main()
