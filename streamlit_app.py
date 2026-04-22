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

# --- Setup ---
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
    logs.append({"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "user": user_name, "action": action, "details": details})
    save_json(LOGS_FILE, logs[-1000:])

# --- UI Styling ---
st.set_page_config(page_title="Data Intel PRO", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * { font-family: 'Pretendard', sans-serif; }
    .stApp { background-color: #f8fafc; }
    .login-card { background: white; border-radius: 35px; padding: 50px; box-shadow: 0 25px 60px rgba(0,0,0,0.06); width: 100%; max-width: 420px; }
    .hero-title { font-weight: 800; font-size: 3.5rem; color: #1e3a8a; text-align: center; margin-bottom: 0px; }
    .hero-sub { color: #64748b; font-size: 1.1rem; text-align: center; margin-bottom: 2.5rem; }
    .stButton > button { background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%) !important; color: white !important; font-weight: 700 !important; border-radius: 14px !important; border: none !important; }
    .section-card { background: white; padding: 25px; border-radius: 20px; border: 1px solid #f1f5f9; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- Core Logic ---
def convert_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False)
    return output.getvalue()

# --- Views ---
def show_landing():
    _, cc, _ = st.columns([1, 1.4, 1])
    with cc:
        st.write("")
        st.markdown("<h1 class='hero-title'>DATA INTEL PRO</h1>", unsafe_allow_html=True)
        st.markdown("<p class='hero-sub'>Expert Intelligence for Enterprise</p>", unsafe_allow_html=True)
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center; margin-bottom:25px;'>보안 인증 로그인</h3>", unsafe_allow_html=True)
        mode = st.radio("", ["사용자 로그인", "관리자 접속"], horizontal=True, label_visibility="collapsed")
        users = load_json(USERS_FILE, [])
        settings = load_json(SETTINGS_FILE, {"master_password": "0303"})
        
        if mode == "관리자 접속":
            pwd = st.text_input("ADMIN PWD", type="password", placeholder="마스터 암호", label_visibility="collapsed")
            if st.button("🚀 시스템 접속"):
                if pwd == settings["master_password"]:
                    st.session_state.authenticated, st.session_state.user_role = True, "admin"
                    st.session_state.current_user = {"name": "ADMIN"}
                    add_log("ADMIN", "Login")
                    st.rerun()
                else: st.error("정보 불일치")
        else:
            n, k = st.text_input("NAME", placeholder="성함"), st.text_input("KEY", type="password", placeholder="라이선스 키")
            if st.button("🚀 로그인"):
                u = next((x for x in users if x["name"] == n and x["license"] == k), None)
                if u:
                    st.session_state.authenticated, st.session_state.user_role, st.session_state.current_user = True, "user", u
                    add_log(n, "Login")
                    st.rerun()
                else: st.error("정보 불일치")
        st.markdown('</div>', unsafe_allow_html=True)

def show_main_app():
    with st.sidebar:
        st.markdown(f"### 💎 Data Intel PRO")
        st.caption(f"접속: {st.session_state.current_user.get('name', 'USER')}")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()
        st.divider()

    st.markdown("<h2 style='font-weight: 800; color: #1e293b; margin-bottom: 2rem;'>Expert Workspace</h2>", unsafe_allow_html=True)
    tabs = st.tabs(["🔗 스마트 매칭", "📄 정밀 추출", "📊 심층 분석", "📂 스마트 병합"] + (["⚙️ 어드민"] if st.session_state.user_role == "admin" else []))
    
    with tabs[0]: # 매칭
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### 🔗 데이터 유사도 매칭")
        c1, c2 = st.columns(2)
        bf, rf = c1.file_uploader("원본", key="m_b"), c2.file_uploader("참조", key="m_r")
        if bf and rf:
            b_df, r_df = load_file_to_df(bf), load_file_to_df(rf)
            bk, rk = c1.selectbox("기준 키", b_df.columns), c2.selectbox("매칭 키", r_df.columns)
            cols = st.multiselect("컬럼", [c for c in r_df.columns if c != rk])
            if st.button("🚀 매칭 실행"):
                b_df[bk], r_df[rk] = b_df[bk].astype(str).str.strip(), r_df[rk].astype(str).str.strip()
                res = pd.merge(b_df, r_df[[rk] + cols], left_on=bk, right_on=rk, how='left')
                st.dataframe(res.head(100), use_container_width=True)
                st.download_button("📥 다운로드", convert_to_excel(res), "match.xlsx")
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]: # 추출
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### 📄 조건별 데이터 정밀 추출")
        f = st.file_uploader("파일 업로드", key="ex_f")
        if f:
            df = load_file_to_df(f)
            col = st.selectbox("필터 기준", df.columns)
            val = st.text_input("키워드")
            if st.button("🚀 추출"):
                res = df[df[col].astype(str).str.contains(val)] if val else df
                st.dataframe(res, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[2]: # 분석
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### 📊 데이터 분석 리포트")
        f = st.file_uploader("파일 업로드", key="an_f")
        if f:
            df = load_file_to_df(f)
            st.write(df.describe())
            st.area_chart(df.select_dtypes(include=[np.number]).iloc[:, :3])
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[3]: # 병합 (RECOVERED)
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### 📂 스마트 데이터 병합 (Multi-File)")
        files = st.file_uploader("병합할 모든 파일 업로드", accept_multiple_files=True, key="mr_f")
        if files:
            dfs = [load_file_to_df(f) for f in files]
            st.info(f"총 {len(files)}개 파일이 로드되었습니다.")
            dedup = st.checkbox("중복 행 자동 제거 (Exact Duplicates)")
            if st.button("🚀 모든 파일 병합 실행"):
                with st.spinner("지능형 병합 중..."):
                    res = pd.concat(dfs, axis=0, ignore_index=True)
                    if dedup: res = res.drop_duplicates()
                    st.success(f"병합 완료! 총 {len(res)}행 생성됨.")
                    st.dataframe(res.head(100), use_container_width=True)
                    st.download_button("📥 병합 결과 다운로드", convert_to_excel(res), "merged_result.xlsx")
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.user_role == "admin":
        with tabs[-1]:
            st.subheader("🕵️‍♂️ 활동 모니터링")
            logs = load_json(LOGS_FILE, [])
            if logs: st.dataframe(pd.DataFrame(logs[::-1]).head(30), use_container_width=True)
            
            st.divider()
            st.subheader("🔑 라이선스 관리")
            with st.form("add"):
                c1, c2, c3 = st.columns(3)
                u_n, u_p, u_d = c1.text_input("성함"), c2.text_input("휴대폰"), c3.number_input("일수", 30)
                if st.form_submit_button("✅ 신규 등록"):
                    key = str(uuid.uuid4())[:8].upper()
                    us = load_json(USERS_FILE, [])
                    us.append({"name":u_n, "phone":u_p, "license":key, "expiry":(datetime.now()+timedelta(days=u_d)).strftime("%Y-%m-%d")})
                    save_json(USERS_FILE, us)
                    st.success(f"등록됨: {key}"); st.rerun()
            
            us = load_json(USERS_FILE, [])
            for i, u in enumerate(us):
                col_i, col_a = st.columns([4, 1])
                col_i.write(f"**{u['name']}** | {u.get('phone')} | `{u['license']}` | 만료: {u['expiry']}")
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
