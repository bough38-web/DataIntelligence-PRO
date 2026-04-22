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

# --- Advanced UI Styling ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&family=Pretendard:wght@400;600;700;800&display=swap');
    * { font-family: 'Pretendard', sans-serif; }
    .stApp { background: linear-gradient(135deg, #f8fafc 0%, #ffffff 50%, #f1f5f9 100%); color: #1e293b; }
    .hero-title {
        font-family: 'Outfit', sans-serif; font-size: 5rem; font-weight: 900; text-align: center;
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
        margin-top: 70px; margin-bottom: 10px; letter-spacing: -2px;
    }
    .hero-sub { text-align: center; color: #64748b; font-size: 1.4rem; font-weight: 500; margin-bottom: 50px; }
    .login-card {
        background: white; border: 1px solid #e2e8f0; border-radius: 40px;
        padding: 50px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.05);
        max-width: 550px; margin: 0 auto;
    }
    .premium-card {
        background: white; padding: 25px; border-radius: 20px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #f1f5f9; margin-bottom: 20px;
    }
    .stButton>button {
        background: #2563eb !important; color: white !important; font-weight: 800 !important;
        border-radius: 16px !important; padding: 16px !important; width: 100% !important; border: none !important;
    }
    .stTextInput>div>div>input { border-radius: 16px !important; border: 1px solid #cbd5e1 !important; text-align: center; height: 55px !important; font-size: 1.1rem !important; }
    .footer { position: fixed; bottom: 20px; right: 30px; color: #cbd5e1; font-size: 0.85rem; }
    </style>
    """, unsafe_allow_html=True)

# --- Business Logic ---
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
    st.markdown("<h1 class='hero-title'>DATA INTEL PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p class='hero-sub'>Next-Gen Intelligence for Modern Teams</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #0f172a; margin-bottom: 40px; font-weight: 800;'>보안 인증 로그인</h2>", unsafe_allow_html=True)
        
        mode = st.radio("", ["라이선스 사용자", "관리자 모드"], horizontal=True, label_visibility="collapsed")
        
        settings = load_json(SETTINGS_FILE, {"master_password": "0303"})
        users = load_json(USERS_FILE, [])
        
        if mode == "관리자 모드":
            pwd = st.text_input("ADMIN PASSWORD", type="password", placeholder="마스터 암호를 입력하세요", label_visibility="collapsed")
            if st.button("🚀 어드민 포털 입장"):
                if pwd == settings["master_password"]:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "admin"
                    add_log("ADMIN", "Admin Login Success")
                    st.rerun()
                else: st.error("정보가 일치하지 않습니다.")
        else:
            in_name = st.text_input("사용자 이름", placeholder="성함 (예: 박희본)", label_visibility="collapsed").strip()
            in_lic = st.text_input("라이선스 번호", type="password", placeholder="발급된 라이선스 번호", label_visibility="collapsed").strip()
            if st.button("🚀 서비스 로그인"):
                user = next((u for u in users if u["name"] == in_name and u["license"] == in_lic), None)
                if user:
                    expiry = datetime.strptime(user["expiry"], "%Y-%m-%d")
                    if expiry < datetime.now():
                        st.error(f"라이선스가 만료되었습니다. (만료일: {user['expiry']})")
                    else:
                        st.session_state.authenticated = True
                        st.session_state.user_role = "user"
                        st.session_state.current_user = user
                        add_log(in_name, "User Login Success")
                        st.toast(f"🎉 {in_name}님, 환영합니다!")
                        time.sleep(1)
                        st.rerun()
                else: st.error("성함 또는 라이선스 번호가 정확하지 않습니다.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="footer">© 2026 Seeun Park. All rights reserved.</div>', unsafe_allow_html=True)

# --- Main App ---

def show_main_app():
    with st.sidebar:
        st.markdown(f"### 💎 Data Intel PRO")
        st.caption(f"Member: {st.session_state.current_user['name'] if st.session_state.current_user else 'ADMIN'}")
        if st.button("Logout"):
            add_log(st.session_state.current_user["name"] if st.session_state.current_user else "ADMIN", "Logout")
            st.session_state.authenticated = False
            st.rerun()
        st.divider()
        if st.session_state.user_role == "user":
            st.markdown("#### 👤 내 보안 설정")
            new_p = st.text_input("라이선스 번호 변경", type="password")
            if st.button("변경 저장"):
                users = load_json(USERS_FILE, [])
                for u in users:
                    if u["license"] == st.session_state.current_user["license"]:
                        u["license"] = new_p
                        st.session_state.current_user["license"] = new_p
                        break
                save_json(USERS_FILE, users)
                st.success("보안 정보가 업데이트되었습니다!")

    st.markdown("<h1 style='color: #0f172a; font-weight: 900; font-size: 2.5rem;'>Expert Suite</h1>", unsafe_allow_html=True)
    
    app_tabs = ["🔗 스마트 매칭", "📄 정밀 추출", "📊 심층 분석", "📂 스마트 병합"]
    if st.session_state.user_role == "admin": app_tabs.append("⚙️ 관리자 컨트롤 센터")
    
    tabs = st.tabs(app_tabs)
    
    # Matching
    with tabs[0]:
        st.markdown('<div class="premium-card">', unsafe_allow_html=True)
        st.markdown("##### 🔗 지능형 데이터 매칭")
        b_f = st.file_uploader("원본 데이터 업로드", key="b_f")
        r_f = st.file_uploader("참조 데이터 업로드", key="r_f")
        if b_f and r_f:
            b_df, r_df = load_file_to_df(b_f), load_file_to_df(r_f)
            b_k = st.selectbox("기준 키", b_df.columns)
            r_k = st.selectbox("매칭 키", r_df.columns)
            r_cols = st.multiselect("추가할 컬럼", [c for c in r_df.columns if c != r_k])
            if st.button("🚀 실행"):
                res = pd.merge(b_df, r_df[[r_k] + r_cols], left_on=b_k, right_on=r_k, how='left')
                st.dataframe(res.head(100))
                st.download_button("📥 Excel 다운로드", convert_df_to_excel(res), "matched.xlsx")
        st.markdown('</div>', unsafe_allow_html=True)

    # Admin Control
    if st.session_state.user_role == "admin":
        with tabs[-1]:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.subheader("📊 서비스 가동 현황")
            logs = load_json(LOGS_FILE, [])
            if logs:
                st.dataframe(pd.DataFrame(logs[::-1]).head(15), use_container_width=True)
                st.bar_chart(pd.DataFrame(logs)["user"].value_counts())
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.subheader("👥 사용자 라이선스 발급")
            with st.form("reg_form"):
                c1, c2, c3 = st.columns(3)
                u_n = c1.text_input("성함 (예: 박희본)")
                u_p = c2.text_input("휴대폰 번호")
                u_d = c3.number_input("사용 일수", value=30)
                if st.form_submit_button("✅ 신규 유저 등록"):
                    new_lic = str(uuid.uuid4())[:8].upper()
                    users = load_json(USERS_FILE, [])
                    users.append({"name":u_n, "phone":u_p, "license":new_lic, "expiry":(datetime.now()+timedelta(days=u_d)).strftime("%Y-%m-%d")})
                    save_json(USERS_FILE, users)
                    add_log("ADMIN", f"Registered: {u_n}")
                    st.success(f"[{u_n}] 등록 완료! 라이선스 번호: {new_lic}")
                    st.rerun()
            
            st.divider()
            users = load_json(USERS_FILE, [])
            for i, u in enumerate(users):
                c_info, c_act = st.columns([3, 1.5])
                c_info.write(f"**{u['name']}** | {u.get('phone','-')} | `{u['license']}` | 만료: {u['expiry']}")
                with c_act:
                    ca1, ca2 = st.columns(2)
                    if ca1.button("연장", key=f"e_{i}"):
                        exp = datetime.strptime(u["expiry"], "%Y-%m-%d")
                        u["expiry"] = (exp + timedelta(days=30)).strftime("%Y-%m-%d")
                        save_json(USERS_FILE, users)
                        st.rerun()
                    if ca2.button("삭제", key=f"d_{i}"):
                        users.pop(i)
                        save_json(USERS_FILE, users)
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# --- Entry ---
def main():
    if not st.session_state.authenticated: show_landing()
    else: show_main_app()

if __name__ == "__main__": main()
