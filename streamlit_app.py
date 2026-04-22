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

# ==========================================
# 1. 시스템 환경 및 경로 설정 (System Setup)
# ==========================================
ROOT_DIR = Path(__file__).parent.absolute()
if str(ROOT_DIR) not in sys.path: sys.path.append(str(ROOT_DIR))

# 데이터 저장 경로 (홈 디렉토리 기반 영구 보존)
AUTH_DIR = Path.home() / ".dataintelligence_pro"
try:
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
except:
    AUTH_DIR = ROOT_DIR / ".data" # 폴백 경로
    AUTH_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_FILE = AUTH_DIR / "auth_settings.json"
USERS_FILE = AUTH_DIR / "users.json"
LOGS_FILE = AUTH_DIR / "logs.json"

# --- 핵심 모듈 임포트 (데이터 엔진) ---
try:
    from app.core.handlers import load_file_to_df
except ImportError:
    def load_file_to_df(f):
        if f.name.endswith('xlsx'): return pd.read_excel(f, engine='openpyxl')
        return pd.read_csv(f)

# ==========================================
# 2. 데이터 관리 유틸리티 (Data Utils)
# ==========================================
def load_json(path, default):
    if not path.exists(): return default
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return default

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
    except: pass

def add_log(user_name, action):
    logs = load_json(LOGS_FILE, [])
    logs.append({"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "user": user_name, "action": action})
    save_json(LOGS_FILE, logs[-1000:])

def convert_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False)
    return output.getvalue()

# ==========================================
# 3. 디자인 시스템 (Premium CSS)
# ==========================================
st.set_page_config(page_title="Data Intel PRO | Enterprise", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

COMMON_STYLE = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&family=Pretendard:wght@400;600;700;800&display=swap');
    * { font-family: 'Pretendard', sans-serif; }
    
    /* [랜딩 전용] 절대 정중앙 & 슬림 카드 */
    .landing-wrapper {
        display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 100vh;
    }
    .login-card {
        background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.4); border-radius: 40px; padding: 55px 45px;
        box-shadow: 0 30px 80px -15px rgba(0, 0, 0, 0.1); width: 100%; max-width: 420px; text-align: center;
        animation: fadeInUp 1s ease-out;
    }
    @keyframes fadeInUp { from { opacity:0; transform: translateY(30px); } to { opacity:1; transform: translateY(0); } }

    /* UI 요소 공통 */
    .stButton > button {
        background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%) !important; color: white !important;
        font-weight: 800 !important; border-radius: 16px !important; padding: 15px !important; width: 100% !important; border: none !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(37,99,235,0.3) !important; }
    
    .stTextInput > div > div > input { border-radius: 14px !important; border: 1.5px solid #e2e8f0 !important; text-align: center; height: 52px !important; }
    .stRadio > div { justify-content: center; gap: 25px; margin-bottom: 20px; }
    
    .hero-title {
        font-family: 'Outfit', sans-serif; font-size: 4rem; font-weight: 900;
        background: linear-gradient(135deg, #0f172a 0%, #2563eb 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -3px; text-align: center; margin-bottom: 0px;
    }
    .hero-sub { color: #64748b; font-size: 1.1rem; font-weight: 500; text-align: center; margin-bottom: 2.5rem; }
    </style>
"""
st.markdown(COMMON_STYLE, unsafe_allow_html=True)

# ==========================================
# 4. 비즈니스 로직 (Core Engine)
# ==========================================
def safe_match(base_df, ref_df, b_key, r_key, target_cols):
    b_copy, r_copy = base_df.copy(), ref_df.copy()
    b_copy[b_key] = b_copy[b_key].astype(str).str.strip()
    r_copy[r_key] = r_copy[r_key].astype(str).str.strip()
    return pd.merge(b_copy, r_copy[[r_key] + target_cols], left_on=b_key, right_on=r_key, how='left')

# ==========================================
# 5. 화면 구성 (Views)
# ==========================================

def show_landing():
    st.markdown("<div class='landing-wrapper'>", unsafe_allow_html=True)
    st.markdown("<h1 class='hero-title'>DATA INTEL PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p class='hero-sub'>Expert Intelligence for Modern Enterprise</p>", unsafe_allow_html=True)
    
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown("<h3 style='margin-bottom: 30px; font-weight: 800; color: #0f172a;'>Security Authentication</h3>", unsafe_allow_html=True)
    
    mode = st.radio("", ["라이선스 사용자", "관리자 접속"], horizontal=True, label_visibility="collapsed")
    users = load_json(USERS_FILE, [])
    settings = load_json(SETTINGS_FILE, {"master_password": "0303"})

    if mode == "관리자 접속":
        pwd = st.text_input("ADMIN PWD", type="password", placeholder="마스터 암호", label_visibility="collapsed")
        if st.button("🚀 UNLOCK SYSTEM"):
            if pwd == settings["master_password"]:
                st.session_state.authenticated = True
                st.session_state.user_role = "admin"
                st.session_state.current_user = {"name": "ADMIN"}
                add_log("ADMIN", "Admin Login")
                st.rerun()
            else: st.error("정보 불일치")
    else:
        in_name = st.text_input("USER NAME", placeholder="성함 (예: 홍길동)", label_visibility="collapsed").strip()
        in_lic = st.text_input("KEY", type="password", placeholder="라이선스 번호", label_visibility="collapsed").strip()
        if st.button("🚀 SIGN IN TO PRO"):
            user = next((u for u in users if u["name"] == in_name and u["license"] == in_lic), None)
            if user:
                exp = datetime.strptime(user["expiry"], "%Y-%m-%d")
                if exp < datetime.now(): st.error("기간 만료")
                else:
                    st.session_state.authenticated, st.session_state.user_role, st.session_state.current_user = True, "user", user
                    add_log(in_name, "User Login")
                    st.rerun()
            else: st.error("정보 불일치")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def show_main_app():
    # 세션 안정성 검사
    if not st.session_state.get('authenticated', False) or st.session_state.get('current_user') is None:
        st.session_state.authenticated = False
        st.rerun()

    with st.sidebar:
        st.markdown(f"### 💎 Data Intel PRO")
        st.caption(f"접속: {st.session_state.current_user.get('name', 'USER')}")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()
        st.divider()
        if st.session_state.user_role == "user":
            st.markdown("#### 내 계정 설정")
            new_k = st.text_input("키 변경", type="password")
            if st.button("저장"):
                us = load_json(USERS_FILE, [])
                for u in us:
                    if u["license"] == st.session_state.current_user["license"]: u["license"] = new_k
                save_json(USERS_FILE, us)
                st.success("변경 완료")

    st.markdown("<h2 style='font-weight: 800; color: #1e293b; margin-bottom: 2rem;'>Expert Workspace</h2>", unsafe_allow_html=True)
    
    app_tabs = ["🔗 스마트 매칭", "📄 정밀 추출", "📊 심층 분석", "📂 스마트 병합"]
    if st.session_state.user_role == "admin": app_tabs.append("⚙️ 관리 & 모니터링")
    tabs = st.tabs(app_tabs)
    
    # 1. 스마트 매칭 (Fix: DataType)
    with tabs[0]:
        st.markdown('<div style="background: white; padding: 28px; border-radius: 20px; border: 1px solid #f1f5f9; box-shadow: 0 4px 6px rgba(0,0,0,0.02);">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            b_f = st.file_uploader("원본 파일", key="b_f")
            if b_f:
                b_df = load_file_to_df(b_f)
                b_k = st.selectbox("기준 키 컬럼", b_df.columns)
        with col2:
            r_f = st.file_uploader("참조 파일", key="r_f")
            if r_f:
                r_df = load_file_to_df(r_f)
                r_k = st.selectbox("매칭 키 컬럼", r_df.columns)
                r_cols = st.multiselect("가져올 컬럼 선택", [c for c in r_df.columns if c != r_k])
        if b_f and r_f:
            if st.button("🚀 지능형 매칭 실행"):
                res = safe_match(b_df, r_df, b_k, r_k, r_cols)
                st.dataframe(res.head(100), use_container_width=True)
                st.download_button("📥 결과 Excel 다운로드", convert_to_excel(res), "match_result.xlsx")
        st.markdown('</div>', unsafe_allow_html=True)

    # 5. 관리자 (Fix: Monitoring & Management)
    if st.session_state.user_role == "admin":
        with tabs[-1]:
            st.subheader("📊 실시간 활동 모니터링")
            logs = load_json(LOGS_FILE, [])
            if logs:
                st.dataframe(pd.DataFrame(logs[::-1]).head(15), use_container_width=True)
                st.bar_chart(pd.DataFrame(logs)["user"].value_counts())
            
            st.divider()
            st.subheader("👥 사용자 라이선스 제어")
            with st.form("reg_u"):
                c1, c2, c3 = st.columns(3)
                u_n, u_p, u_d = c1.text_input("성함"), c2.text_input("휴대폰"), c3.number_input("일수", value=30)
                if st.form_submit_button("✅ 신규 등록"):
                    new_lic = str(uuid.uuid4())[:8].upper()
                    us = load_json(USERS_FILE, [])
                    us.append({"name":u_n, "phone":u_p, "license":new_lic, "expiry":(datetime.now()+timedelta(days=u_d)).strftime("%Y-%m-%d")})
                    save_json(USERS_FILE, us)
                    add_log("ADMIN", f"Registered: {u_n}")
                    st.success(f"[{u_n}] 키: {new_lic}")
                    st.rerun()
            
            # 사용자 목록 관리
            us = load_json(USERS_FILE, [])
            for i, u in enumerate(us):
                ci, ca = st.columns([3, 1.5])
                ci.write(f"**{u['name']}** | {u.get('phone','-')} | `{u['license']}` | 만료: {u['expiry']}")
                with ca:
                    b1, b2 = st.columns(2)
                    if b1.button("연장", key=f"e_{i}"):
                        cur_exp = datetime.strptime(u["expiry"], "%Y-%m-%d")
                        u["expiry"] = (cur_exp + timedelta(days=30)).strftime("%Y-%m-%d")
                        save_json(USERS_FILE, us)
                        st.rerun()
                    if b2.button("삭제", key=f"d_{i}"):
                        us.pop(i)
                        save_json(USERS_FILE, us)
                        st.rerun()

# ==========================================
# 6. 진입점 (Entry Point)
# ==========================================
def main():
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False
    if 'current_user' not in st.session_state: st.session_state.current_user = None
    if 'user_role' not in st.session_state: st.session_state.user_role = "user"

    if not st.session_state.authenticated: show_landing()
    else: show_main_app()

if __name__ == "__main__": main()
