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

# --- Path & Persistence Setup ---
ROOT_DIR = Path(__file__).parent.absolute()
if str(ROOT_DIR) not in sys.path: sys.path.append(str(ROOT_DIR))

try:
    from app.core.handlers import load_file_to_df
except ImportError:
    def load_file_to_df(f):
        if f.name.endswith('xlsx'): return pd.read_excel(f, engine='openpyxl')
        return pd.read_csv(f)

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

# --- UI Styling ---
st.set_page_config(page_title="Data Intel PRO", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * { font-family: 'Pretendard', sans-serif; }
    .stApp { background-color: #f8fafc; }
    .login-card {
        background: white; border-radius: 30px; padding: 50px 40px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.06); width: 100%; max-width: 420px;
    }
    .hero-title { font-weight: 800; font-size: 3.5rem; color: #1e3a8a; text-align: center; margin-bottom: 0px; }
    .hero-sub { color: #64748b; font-size: 1.1rem; text-align: center; margin-bottom: 2rem; }
    .stButton > button {
        background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%) !important;
        color: white !important; font-weight: 700 !important; border-radius: 14px !important; border: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Core Engine ---
def safe_match(b_df, r_df, b_k, r_k, cols):
    b_c, r_c = b_df.copy(), r_df.copy()
    b_c[b_k] = b_c[b_k].astype(str).str.strip()
    r_c[r_k] = r_c[r_k].astype(str).str.strip()
    return pd.merge(b_c, r_c[[r_k] + cols], left_on=b_k, right_on=r_k, how='left')

def convert_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False)
    return output.getvalue()

# --- Landing ---
def show_landing():
    _, center_col, _ = st.columns([1, 1.4, 1])
    with center_col:
        st.write("")
        st.markdown("<h1 class='hero-title'>DATA INTEL PRO</h1>", unsafe_allow_html=True)
        st.markdown("<p class='hero-sub'>Expert Intelligence for Enterprise</p>", unsafe_allow_html=True)
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center; margin-bottom:25px;'>보안 인증 로그인</h3>", unsafe_allow_html=True)
        mode = st.radio("", ["라이선스 사용자", "관리자 접속"], horizontal=True, label_visibility="collapsed")
        users = load_json(USERS_FILE, [])
        settings = load_json(SETTINGS_FILE, {"master_password": "0303"})
        
        if mode == "관리자 접속":
            pwd = st.text_input("ADMIN PWD", type="password", placeholder="마스터 암호", label_visibility="collapsed")
            if st.button("🚀 시스템 접속"):
                if pwd == settings["master_password"]:
                    st.session_state.authenticated, st.session_state.user_role = True, "admin"
                    st.session_state.current_user = {"name": "ADMIN"}
                    add_log("ADMIN", "Login Success")
                    st.rerun()
                else: st.error("정보 불일치")
        else:
            in_name = st.text_input("NAME", placeholder="성함 (예: 홍길동)", label_visibility="collapsed").strip()
            in_lic = st.text_input("LICENSE", type="password", placeholder="라이선스 번호", label_visibility="collapsed").strip()
            if st.button("🚀 SIGN IN"):
                user = next((u for u in users if u["name"] == in_name and u["license"] == in_lic), None)
                if user:
                    st.session_state.authenticated, st.session_state.user_role, st.session_state.current_user = True, "user", user
                    add_log(in_name, "Login Success")
                    st.rerun()
                else: st.error("정보 불일치")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Workspace ---
def show_main_app():
    with st.sidebar:
        st.markdown(f"### 💎 Data Intel PRO")
        st.caption(f"접속: {st.session_state.current_user.get('name', 'USER')}")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()
        st.divider()

    st.markdown("<h2 style='font-weight: 800; color: #1e293b; margin-bottom: 2rem;'>Expert Workspace</h2>", unsafe_allow_html=True)
    tabs = st.tabs(["🔗 스마트 매칭", "📄 정밀 추출", "📊 심층 분석", "📂 스마트 병합"] + (["⚙️ 어드민 패널"] if st.session_state.user_role == "admin" else []))
    
    with tabs[0]: # 매칭
        st.markdown('<div style="background:white; padding:25px; border-radius:20px; border:1px solid #f1f5f9;">', unsafe_allow_html=True)
        st.markdown("#### 🔗 지능형 데이터 매칭")
        c1, c2 = st.columns(2)
        b_f = c1.file_uploader("원본 파일", key="match_b")
        r_f = c2.file_uploader("참조 파일", key="match_r")
        if b_f and r_f:
            b_df, r_df = load_file_to_df(b_f), load_file_to_df(r_f)
            b_k = c1.selectbox("원본 기준 키", b_df.columns, key="b_k")
            r_k = c2.selectbox("참조 매칭 키", r_df.columns, key="r_k")
            r_cols = st.multiselect("가져올 컬럼 선택", [c for c in r_df.columns if c != r_k])
            if st.button("🚀 매칭 실행하기"):
                res = safe_match(b_df, r_df, b_k, r_k, r_cols)
                st.dataframe(res.head(100), use_container_width=True)
                st.download_button("📥 Excel 다운로드", convert_to_excel(res), "match_result.xlsx")
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]: # 추출 (Simple Placeholder for now)
        st.markdown("#### 📄 정밀 데이터 추출")
        f = st.file_uploader("추출할 파일 업로드", key="ext_f")
        if f:
            df = load_file_to_df(f)
            st.dataframe(df.head(50))
            st.info("전문가용 추출 엔진이 활성화되었습니다.")

    with tabs[2]: # 분석
        st.markdown("#### 📊 심층 데이터 분석")
        f = st.file_uploader("분석할 파일 업로드", key="ana_f")
        if f:
            df = load_file_to_df(f)
            st.write(df.describe())
            st.bar_chart(df.select_dtypes(include=[np.number]).iloc[:, :5])

    with tabs[3]: # 병합
        st.markdown("#### 📂 스마트 데이터 병합")
        files = st.file_uploader("병합할 파일들 업로드 (복수 가능)", accept_multiple_files=True, key="mrg_f")
        if files:
            dfs = [load_file_to_df(f) for f in files]
            if st.button("🚀 모든 파일 병합"):
                res = pd.concat(dfs, axis=0, ignore_index=True)
                st.success(f"{len(files)}개 파일 병합 완료")
                st.dataframe(res.head(100))
                st.download_button("📥 병합 결과 다운로드", convert_to_excel(res), "merged.xlsx")

    if st.session_state.user_role == "admin":
        with tabs[-1]:
            st.subheader("📊 실시간 활동 모니터링")
            logs = load_json(LOGS_FILE, [])
            if logs:
                st.dataframe(pd.DataFrame(logs[::-1]).head(20), use_container_width=True)
                st.line_chart(pd.DataFrame(logs).groupby("timestamp").size())
            
            st.divider()
            st.subheader("👥 사용자 라이선스 관리")
            with st.form("reg_user"):
                c1, c2, c3 = st.columns(3)
                u_n, u_p, u_d = c1.text_input("성함"), c2.text_input("휴대폰"), c3.number_input("기간(일)", value=30)
                if st.form_submit_button("✅ 신규 유저 등록"):
                    new_k = str(uuid.uuid4())[:8].upper()
                    us = load_json(USERS_FILE, [])
                    us.append({"name":u_n, "phone":u_p, "license":new_k, "expiry":(datetime.now()+timedelta(days=u_d)).strftime("%Y-%m-%d")})
                    save_json(USERS_FILE, us)
                    add_log("ADMIN", f"Registered: {u_n}")
                    st.success(f"[{u_n}] 등록 완료. 키: {new_k}")
                    st.rerun()
            
            # 유저 목록 (연장/삭제)
            us = load_json(USERS_FILE, [])
            for i, u in enumerate(us):
                ci, ca = st.columns([3, 1])
                ci.write(f"**{u['name']}** (`{u['license']}`) | 만료: {u['expiry']}")
                with ca:
                    b1, b2 = st.columns(2)
                    if b1.button("연장", key=f"ex_{i}"):
                        cur = datetime.strptime(u["expiry"], "%Y-%m-%d")
                        u["expiry"] = (cur + timedelta(days=30)).strftime("%Y-%m-%d")
                        save_json(USERS_FILE, us)
                        st.rerun()
                    if b2.button("삭제", key=f"dl_{i}"):
                        us.pop(i)
                        save_json(USERS_FILE, us)
                        st.rerun()

def main():
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False
    if 'current_user' not in st.session_state: st.session_state.current_user = None
    if 'user_role' not in st.session_state: st.session_state.user_role = "user"
    if not st.session_state.authenticated: show_landing()
    else: show_main_app()

if __name__ == "__main__": main()
