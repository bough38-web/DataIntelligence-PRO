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
# 1. 시스템 아키텍처 및 설정 (System Architecture)
# ==========================================
ROOT_DIR = Path(__file__).parent.absolute()
if str(ROOT_DIR) not in sys.path: sys.path.append(str(ROOT_DIR))

# 데이터 영속성 (SaaS Level Persistence)
AUTH_DIR = Path.home() / ".dataintelligence_pro"
AUTH_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE, USERS_FILE, LOGS_FILE = AUTH_DIR/"auth_settings.json", AUTH_DIR/"users.json", AUTH_DIR/"logs.json"

def load_json(path, default):
    if not path.exists(): return default
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

def add_log(user_name, action, details=""):
    logs = load_json(LOGS_FILE, [])
    logs.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user_name, "action": action, "details": details
    })
    save_json(LOGS_FILE, logs[-2000:])

# --- Core Handler Integration ---
try:
    from app.core.handlers import load_file_to_df
except ImportError:
    def load_file_to_df(f):
        if f.name.endswith('xlsx'): return pd.read_excel(f, engine='openpyxl')
        return pd.read_csv(f)

# ==========================================
# 2. 디자인 시스템 (사용자 제공 프리미엄 UI)
# ==========================================
st.set_page_config(page_title="Data Intel PRO", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

PROFESSIONAL_STYLE = """
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    /* 기본 배경 및 폰트 설정 */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Pretendard', sans-serif;
        background: radial-gradient(circle at top right, #f1f5f9, #e2e8f0);
    }

    /* 상단 메뉴바/헤더 숨기기 (더 깔끔한 랜딩을 위해) */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* 메인 컨테이너 중앙 정렬 */
    .main-center-wrapper {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding-top: 5vh;
    }

    /* 타이틀 섹션 */
    .hero-container {
        text-align: center;
        margin-bottom: 2.5rem;
    }
    .hero-title {
        font-size: 3.5rem; 
        font-weight: 900; 
        color: #0f172a;
        letter-spacing: -0.05em; 
        margin-bottom: 0.5rem;
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-sub { 
        color: #64748b; 
        font-size: 1.2rem; 
        font-weight: 400;
        letter-spacing: -0.02em;
    }

    /* 슬림 프리미엄 카드 */
    .login-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 24px;
        padding: 40px 40px;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        width: 100%;
        max-width: 400px;
    }

    /* 입력창 및 라디오 버튼 커스텀 */
    .stTextInput > div > div > input {
        border-radius: 12px !important;
        border: 1px solid #e2e8f0 !important;
        height: 50px !important;
        font-size: 0.95rem !important;
        background-color: #f8fafc !important;
        transition: all 0.2s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
    }

    /* 버튼 스타일링 */
    .stButton > button {
        background: #0f172a !important; /* 다크 네이비 테마 */
        color: #ffffff !important;
        border-radius: 12px !important;
        padding: 12px 24px !important;
        width: 100% !important;
        font-weight: 600 !important;
        border: none !important;
        height: 50px !important;
        margin-top: 10px;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        background: #1e293b !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    }

    /* 라디오 버튼 중앙 정렬 */
    div[data-testid="stRadio"] > div {
        justify-content: center;
        gap: 20px;
    }
</style>
"""

# ==========================================
# 3. 데이터 지능형 엔진 (Intelligence Engine)
# ==========================================
def enterprise_match(b_df, r_df, b_k, r_k, cols, fuzzy=False):
    b_c, r_c = b_df.copy(), r_df.copy()
    b_c[b_k] = b_c[b_k].astype(str).str.strip()
    r_c[r_k] = r_c[r_k].astype(str).str.strip()
    
    if fuzzy:
        def get_best_match(val, targets):
            m = difflib.get_close_matches(val, targets, n=1, cutoff=0.7)
            return m[0] if m else None
        r_targets = r_c[r_k].unique().tolist()
        b_c['match_key'] = b_c[b_k].apply(lambda x: get_best_match(x, r_targets))
        res = pd.merge(b_c, r_c[[r_k] + cols], left_on='match_key', right_on=r_k, how='left')
    else:
        res = pd.merge(b_c, r_c[[r_k] + cols], left_on=b_k, right_on=r_k, how='left')
    return res

def convert_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False)
    return output.getvalue()

# ==========================================
# 4. 화면 로직 (System Views)
# ==========================================

def show_landing():
    # 1. 사용자 제공 스타일 적용
    st.markdown(PROFESSIONAL_STYLE, unsafe_allow_html=True)
    
    # 2. 레이아웃 배치
    _, center_col, _ = st.columns([0.5, 2, 0.5])
    
    with center_col:
        st.markdown('<div class="main-center-wrapper">', unsafe_allow_html=True)
        
        # 헤더 섹션
        st.markdown('''
            <div class="hero-container">
                <h1 class="hero-title">DATA INTEL PRO</h1>
                <p class="hero-sub">Expert Intelligence for Enterprise</p>
            </div>
        ''', unsafe_allow_html=True)
        
        # 로그인 카드 섹션
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; font-weight:700; color:#475569; margin-bottom:20px;'>SECURE ACCESS</p>", unsafe_allow_html=True)
        
        mode = st.radio("Access Mode", ["사용자 접속", "관리자 모드"], horizontal=True, label_visibility="collapsed")
        
        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        
        # 실제 데이터베이스 로드
        users = load_json(USERS_FILE, [])
        settings = load_json(SETTINGS_FILE, {"master_password": "0303"})
        
        # 실제 인증 로직 결합
        if mode == "관리자 모드":
            pwd = st.text_input("ADMIN PWD", type="password", placeholder="Master Password", label_visibility="collapsed")
            if st.button("Authenticate System"):
                if pwd == settings["master_password"]: 
                    st.session_state.authenticated = True
                    st.session_state.user_role = "admin"
                    st.session_state.current_user = {"name": "ADMIN"}
                    add_log("ADMIN", "System Unlock")
                    st.rerun()
                else:
                    st.error("Invalid Credential")
        else:
            name = st.text_input("NAME", placeholder="Full Name", label_visibility="collapsed")
            key = st.text_input("LICENSE", type="password", placeholder="License Key", label_visibility="collapsed")
            if st.button("Sign In to Workspace"):
                u = next((x for x in users if x["name"] == name and x["license"] == key), None)
                if u:
                    if datetime.strptime(u["expiry"], "%Y-%m-%d") < datetime.now(): 
                        st.error("만료된 라이선스입니다.")
                    else:
                        st.session_state.authenticated, st.session_state.user_role, st.session_state.current_user = True, "user", u
                        add_log(name, "Login Success")
                        st.rerun()
                else: 
                    st.error("인증 정보가 올바르지 않습니다.")
                
        st.markdown('</div>', unsafe_allow_html=True) 
        
        # 하단 푸터
        st.markdown("<p style='margin-top:30px; color:#94a3b8; font-size:0.8rem;'>© 2026 Data Intel Pro. All rights reserved.</p>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True) 

def show_main_app():
    # 워크스페이스 전용 헤더 보이기 복구 (선택 사항)
    st.markdown("<style>header {visibility: visible;}</style>", unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown(f"### 💎 Data Intel PRO")
        st.info(f"User: {st.session_state.current_user.get('name')}")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()
        st.divider()

    st.markdown("<h2 style='font-weight: 900; color: #1e293b; margin-bottom: 2rem;'>Intelligence Workspace</h2>", unsafe_allow_html=True)
    tabs = st.tabs(["🔗 지능형 매칭", "📄 정밀 추출", "📊 심층 분석", "📂 스마트 병합"] + (["⚙️ 어드민 시스템"] if st.session_state.user_role == "admin" else []))
    
    with tabs[0]:
        st.markdown('<div style="background: white; border: 1px solid #f1f5f9; border-radius: 18px; padding: 20px;">', unsafe_allow_html=True)
        st.markdown("#### 🔗 데이터 결합 및 유사도 매칭")
        c1, c2 = st.columns(2)
        b_f, r_f = c1.file_uploader("원본(Base)", key="m_b"), c2.file_uploader("참조(Ref)", key="m_r")
        if b_f and r_f:
            b_df, r_df = load_file_to_df(b_f), load_file_to_df(r_f)
            bk, rk = c1.selectbox("기준 열", b_df.columns), c2.selectbox("매칭 열", r_df.columns)
            r_cols = st.multiselect("추가할 데이터", [c for c in r_df.columns if c != rk])
            use_fuzzy = st.checkbox("유사도 기반 매칭(Fuzzy Match) 사용")
            if st.button("🚀 지능형 매칭 실행"):
                with st.spinner("데이터 분석 중..."):
                    res = enterprise_match(b_df, r_df, bk, rk, r_cols, fuzzy=use_fuzzy)
                    st.dataframe(res.head(100), use_container_width=True)
                    st.download_button("📥 다운로드(Excel)", convert_to_excel(res), "result.xlsx")
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]:
        st.markdown('<div style="background: white; border: 1px solid #f1f5f9; border-radius: 18px; padding: 20px;">', unsafe_allow_html=True)
        st.markdown("#### 📄 조건별 데이터 정밀 추출")
        f = st.file_uploader("추출 파일 업로드", key="ex_f")
        if f:
            df = load_file_to_df(f)
            col = st.selectbox("필터 기준 열", df.columns)
            val = st.text_input("필터 키워드 (공백 시 전체)")
            if st.button("🚀 정밀 추출"):
                res = df[df[col].astype(str).str.contains(val)] if val else df
                st.dataframe(res, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[2]:
        st.markdown('<div style="background: white; border: 1px solid #f1f5f9; border-radius: 18px; padding: 20px;">', unsafe_allow_html=True)
        st.markdown("#### 📊 데이터 품질 보고서 및 시각화")
        f = st.file_uploader("분석 파일 업로드", key="an_f")
        if f:
            df = load_file_to_df(f)
            st.write("##### 🧐 품질 요약")
            c1, c2, c3 = st.columns(3)
            c1.metric("전체 행", len(df))
            c2.metric("결측치(Null)", df.isnull().sum().sum())
            c3.metric("중복 행", df.duplicated().sum())
            st.area_chart(df.select_dtypes(include=[np.number]).iloc[:, :3])
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[3]:
        st.markdown('<div style="background: white; border: 1px solid #f1f5f9; border-radius: 18px; padding: 20px;">', unsafe_allow_html=True)
        st.markdown("#### 📂 스마트 데이터 병합 (Multi-File)")
        files = st.file_uploader("병합할 파일 다중 선택", accept_multiple_files=True, key="mr_f")
        if files:
            dfs = [load_file_to_df(f) for f in files]
            dedup = st.checkbox("중복 행 제거")
            if st.button("🚀 모든 파일 병합"):
                res = pd.concat(dfs, axis=0, ignore_index=True)
                if dedup: res = res.drop_duplicates()
                st.dataframe(res.head(100), use_container_width=True)
                st.download_button("📥 병합 결과 다운로드", convert_to_excel(res), "merged.xlsx")
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.user_role == "admin":
        with tabs[-1]:
            st.subheader("🕵️‍♂️ 모니터링 & 라이선스 관리")
            with st.form("add"):
                c1, c2, c3 = st.columns(3)
                u_n, u_p, u_d = c1.text_input("성함"), c2.text_input("연락처"), c3.number_input("일수", 30)
                if st.form_submit_button("✅ 신규 사용자 등록"):
                    key = str(uuid.uuid4())[:8].upper()
                    us = load_json(USERS_FILE, [])
                    us.append({"name":u_n, "phone":u_p, "license":key, "expiry":(datetime.now()+timedelta(days=u_d)).strftime("%Y-%m-%d")})
                    save_json(USERS_FILE, us)
                    st.success(f"[{u_n}] 등록 키: {key}"); st.rerun()
            
            us = load_json(USERS_FILE, [])
            for i, u in enumerate(us):
                col_i, col_a = st.columns([4, 1])
                col_i.write(f"**{u['name']}** | `{u['license']}` | 만료: {u['expiry']}")
                with col_a:
                    b1, b2 = st.columns(2)
                    if b1.button("연장", key=f"e_{i}"):
                        u["expiry"] = (datetime.strptime(u["expiry"], "%Y-%m-%d")+timedelta(days=30)).strftime("%Y-%m-%d")
                        save_json(USERS_FILE, us); st.rerun()
                    if b2.button("삭제", key=f"d_{i}"):
                        us.pop(i); save_json(USERS_FILE, us); st.rerun()

def main():
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False
    if 'current_user' not in st.session_state: st.session_state.current_user = None
    if 'user_role' not in st.session_state: st.session_state.user_role = "user"
    if not st.session_state.authenticated: show_landing()
    else: show_main_app()

if __name__ == "__main__": main()
