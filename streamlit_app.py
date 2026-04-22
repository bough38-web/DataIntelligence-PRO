import streamlit as st
import pandas as pd
import numpy as np
import os
import io
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from app.core.handlers import load_file_to_df, get_sheet_names
from app.core.processors import fill_service_small_from_mid, apply_sorting, apply_dedup
from app.utils.common import clean_text

# --- Paths & Persistence ---
AUTH_DIR = Path.home() / ".dataintelligence_pro"
AUTH_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = AUTH_DIR / "auth_settings.json"
USERS_FILE = AUTH_DIR / "users.json"

DEFAULT_SETTINGS = {"master_password": "0303"}
DEFAULT_USERS = []

# --- Data Persistence Helpers ---
def load_json(path, default):
    if not path.exists():
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f)
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- Page Configuration ---
st.set_page_config(
    page_title="Data Intelligence PRO | Enterprise",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Session State ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = "user"
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# --- Premium Styling ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800;900&display=swap');
    * { font-family: 'Pretendard', sans-serif; }
    
    .stApp { background-color: #f8fafc; }
    
    .hero-section {
        text-align: center;
        padding: 80px 40px;
        background: radial-gradient(circle at top right, #1e293b, #0f172a);
        color: white;
        border-radius: 40px;
        margin-bottom: 40px;
        box-shadow: 0 20px 40px -10px rgba(0,0,0,0.3);
    }
    
    .hero-title {
        font-size: 4.5rem;
        font-weight: 900;
        letter-spacing: -2px;
        background: linear-gradient(135deg, #60a5fa 0%, #2563eb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 15px;
    }
    
    .login-container {
        max-width: 460px;
        margin: -100px auto 50px;
        padding: 45px;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(20px);
        border-radius: 32px;
        box-shadow: 0 30px 60px -12px rgba(0,0,0,0.15);
        border: 1px solid rgba(255,255,255,0.3);
    }
    
    .premium-card {
        background: white;
        padding: 2rem;
        border-radius: 24px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
        border: 1px solid #f1f5f9;
        margin-bottom: 1.5rem;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
        color: white;
        border: none;
        padding: 14px;
        border-radius: 16px;
        font-weight: 700;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px -5px rgba(37,99,235,0.4);
    }
    
    .expert-badge {
        background: #eff6ff;
        color: #1e40af;
        padding: 6px 14px;
        border-radius: 10px;
        font-size: 0.8rem;
        font-weight: 700;
        display: inline-block;
        margin-right: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# --- Auth Modules ---

def show_landing():
    st.markdown("""
        <div class="hero-section">
            <h1 class="hero-title">Data Intelligence PRO</h1>
            <p style="font-size: 1.3rem; color: #94a3b8; max-width: 700px; margin: 0 auto;">
                인공지능 기반의 정밀 데이터 엔진. 복잡한 엑셀 수식과 반복 업무를 혁신적인 워크플로우로 자동화합니다.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #0f172a; margin-bottom: 30px;'>보안 접속 (Security Login)</h2>", unsafe_allow_html=True)
        
        login_tab = st.radio("로그인 방식", ["마스터 패스워드", "개인 라이선스"], horizontal=True)
        
        settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        users = load_json(USERS_FILE, DEFAULT_USERS)
        
        if login_tab == "마스터 패스워드":
            pwd = st.text_input("패스워드", type="password", placeholder="Master Password (0303)")
            if st.button("🚀 시스템 가동"):
                if pwd == settings["master_password"]:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "admin"
                    st.success("관리자 권한으로 인증되었습니다.")
                    time.sleep(0.5)
                    st.rerun()
                else: st.error("비밀번호가 올바르지 않습니다.")
        else:
            license_key = st.text_input("라이선스 키", type="password", placeholder="Your Private License Key")
            if st.button("🚀 라이선스 인증"):
                user = next((u for u in users if u["license"] == license_key), None)
                if user:
                    expiry = datetime.strptime(user["expiry"], "%Y-%m-%d")
                    if expiry < datetime.now():
                        st.error("❌ 라이선스 기간이 만료되었습니다. 관리자에게 문의하세요.")
                    else:
                        st.session_state.authenticated = True
                        st.session_state.user_role = "user"
                        st.session_state.current_user = user
                        st.success(f"✅ {user['name']}님, 인증 성공!")
                        time.sleep(0.5)
                        st.rerun()
                else: st.error("유효하지 않은 라이선스 키입니다.")
        
        st.markdown("</div>", unsafe_allow_html=True)

# --- Admin Panel ---
def show_admin_panel():
    st.markdown('<div class="premium-card">', unsafe_allow_html=True)
    st.header("⚙️ 시스템 관리자 패널")
    
    a_tabs = st.tabs(["🛡 보안 설정", "👥 사용자/라이선스 관리", "📊 사용 통계"])
    
    with a_tabs[0]:
        st.subheader("마스터 패스워드 변경")
        settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        new_pwd = st.text_input("새로운 마스터 패스워드", value=settings["master_password"])
        if st.button("설정 저장"):
            settings["master_password"] = new_pwd
            save_json(SETTINGS_FILE, settings)
            st.success("패스워드가 업데이트되었습니다.")
            
    with a_tabs[1]:
        users = load_json(USERS_FILE, DEFAULT_USERS)
        st.subheader("새로운 사용자 등록")
        with st.form("user_reg"):
            c1, c2 = st.columns(2)
            u_name = c1.text_input("이름")
            u_phone = c2.text_input("연락처 (010-...)")
            u_license = c1.text_input("고유 라이선스 키 (Password)")
            u_expiry = c2.date_input("만료 일자", value=datetime.now() + timedelta(days=365))
            if st.form_submit_button("사용자 추가"):
                if u_name and u_license:
                    users.append({
                        "name": u_name, "phone": u_phone, "license": u_license,
                        "expiry": u_expiry.strftime("%Y-%m-%d"),
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    save_json(USERS_FILE, users)
                    st.success(f"{u_name}님 등록 완료.")
                    st.rerun()
        
        st.divider()
        st.subheader("라이선스 현황")
        if users:
            df = pd.DataFrame(users)
            st.dataframe(df, use_container_width=True)
            if st.button("🗑 모든 데이터 초기화"):
                save_json(USERS_FILE, [])
                st.rerun()
        else: st.info("등록된 사용자가 없습니다.")
    st.markdown('</div>', unsafe_allow_html=True)

# --- Main App Modules ---
def show_main_app():
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.current_user['name'] if st.session_state.current_user else 'Master Admin'}")
        st.caption(f"Status: {st.session_state.user_role.upper()} ACCESS")
        if st.button("🚪 안전 로그아웃"):
            st.session_state.authenticated = False
            st.rerun()
        st.divider()
        st.markdown("#### 🛠 시스템 엔진")
        st.success("AI Core v2.8 Active")
        st.success("Safe Memory Enabled")

    st.markdown('<h1 style="font-size: 3rem; font-weight: 900; color: #0f172a;">Data Intelligence PRO</h1>', unsafe_allow_html=True)
    
    app_tabs = ["🔗 스마트 매칭 (Matching)", "📄 정밀 추출 (Extract)", "📂 스마트 병합 (Merge)", "📊 심층 분석 (Insight)", "🛠 데이터 변환 (Transform)"]
    if st.session_state.user_role == "admin":
        app_tabs.append("⚙️ 어드민 (Admin)")
        
    t = st.tabs(app_tabs)
    
    # --- 1. Matching ---
    with t[0]:
        st.subheader("🔗 스마트 매칭 (Smart Matching)")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🟢 원본 (Base)")
            b_f = st.file_uploader("원본 업로드", type=['xlsx','csv','xls'], key="bf")
            if b_f:
                b_df = load_file_to_df(b_f)
                b_k = st.selectbox("기준 키 (Key)", b_df.columns, key="bk")
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🟡 참조 (Ref)")
            r_f = st.file_uploader("참조 업로드", type=['xlsx','csv','xls'], key="rf")
            if r_f:
                r_df = load_file_to_df(r_f)
                r_k = st.selectbox("매칭 키 (Match)", r_df.columns, key="rk")
                all_r = [c for c in r_df.columns if c != r_k]
                sc1, sc2 = st.columns(2)
                if sc1.button("전체 선택"): st.session_state.m_cols = all_r
                if sc2.button("전체 해제"): st.session_state.m_cols = []
                r_cols = st.multiselect("필드 선택", all_r, key="m_cols", default=st.session_state.get('m_cols', []))
            st.markdown('</div>', unsafe_allow_html=True)
        
        if b_f and r_f:
            if st.button("🚀 데이터 매칭 실행"):
                with st.spinner("Processing..."):
                    res = pd.merge(b_df, r_df[[r_k] + r_cols], left_on=b_k, right_on=r_k, how='left')
                    st.success("완료!")
                    st.dataframe(res.head(100))
                    st.download_button("📥 Excel 다운로드", convert_df_to_excel(res), "match.xlsx")

    # --- 2. Extract ---
    with t[1]:
        st.subheader("📄 정밀 추출 (Precision Extract)")
        e_f = st.file_uploader("가공 대상 업로드", type=['xlsx','csv','xls'], key="ef")
        if e_f:
            e_df = load_file_to_df(e_f)
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            ec1, ec2 = st.columns([1, 2])
            with ec1:
                col_f = st.selectbox("필터 컬럼", e_df.columns)
                val_f = st.text_input("검색어 (콤마 구분)")
            with ec2:
                all_e = list(e_df.columns)
                if st.button("전체 선택", key="e_all"): st.session_state.e_cols = all_e
                e_cols = st.multiselect("출력 컬럼", all_e, key="e_cols", default=st.session_state.get('e_cols', all_e))
            
            if st.button("📤 추출 실행"):
                res = e_df[e_cols].copy()
                if val_f:
                    vals = [v.strip() for v in val_f.split(",")]
                    res = res[res[col_f].astype(str).str.contains("|".join(vals), na=False)]
                st.dataframe(res.head(100))
                st.download_button("📥 결과 저장", convert_df_to_excel(res), "extract.xlsx")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- 3. Merge ---
    with t[2]:
        st.subheader("📂 스마트 병합 (Smart Merge)")
        m_files = st.file_uploader("병합할 파일들을 선택하세요", accept_multiple_files=True, key="mf")
        if m_files:
            if st.button("🚀 대량 통합 실행"):
                all_dfs = [load_file_to_df(f) for f in m_files]
                final = pd.concat(all_dfs, ignore_index=True)
                st.success(f"{len(m_files)}개 파일 통합 완료!")
                st.download_button("📥 통합 결과 저장", convert_df_to_excel(final), "merged.xlsx")

    # --- 4. Insight ---
    with t[3]:
        st.subheader("📊 심층 분석 (Insight)")
        a_f = st.file_uploader("분석용 파일 업로드", key="af")
        if a_f:
            a_df = load_file_to_df(a_f)
            st.table(pd.DataFrame([{"컬럼": c, "타입": str(a_df[c].dtype), "Null": a_df[c].isna().sum()} for c in a_df.columns]))
            sel_c = st.selectbox("분포 확인 컬럼", a_df.columns)
            st.bar_chart(a_df[sel_c].value_counts().head(20))

    # --- 5. Admin ---
    if st.session_state.user_role == "admin":
        with t[-1]:
            show_admin_panel()

# --- Main Entry ---
def main():
    if not st.session_state.authenticated:
        show_landing()
    else:
        show_main_app()

if __name__ == "__main__":
    main()
