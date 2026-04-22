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
# 2. 디자인 시스템 (Enterprise UI)
# ==========================================
st.set_page_config(page_title="Data Intel PRO", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * { font-family: 'Pretendard', sans-serif; }
    .stApp { background-color: #fcfcfd; }
    .login-card { background: white; border-radius: 35px; padding: 55px; box-shadow: 0 25px 70px rgba(0,0,0,0.07); width: 100%; max-width: 440px; }
    .hero-title { font-weight: 900; font-size: 3.8rem; color: #0f172a; text-align: center; letter-spacing: -3px; }
    .hero-sub { color: #64748b; font-size: 1.1rem; text-align: center; margin-bottom: 3rem; }
    .stButton > button {
        background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%) !important; color: white !important;
        font-weight: 800 !important; border-radius: 16px !important; padding: 16px !important; border: none !important;
    }
    .status-card { background: white; border: 1px solid #f1f5f9; border-radius: 18px; padding: 20px; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 데이터 지능형 엔진 (Intelligence Engine)
# ==========================================
def enterprise_match(b_df, r_df, b_k, r_k, cols, fuzzy=False):
    b_c, r_c = b_df.copy(), r_df.copy()
    b_c[b_k] = b_c[b_k].astype(str).str.strip()
    r_c[r_k] = r_c[r_k].astype(str).str.strip()
    
    if fuzzy:
        # 전문가용 유사도 매칭 로직
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
    _, cc, _ = st.columns([1, 1.4, 1])
    with cc:
        st.write("")
        st.markdown("<h1 class='hero-title'>DATA INTEL PRO</h1>", unsafe_allow_html=True)
        st.markdown("<p class='hero-sub'>Enterprise-Grade Intelligence Suite</p>", unsafe_allow_html=True)
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center; margin-bottom:30px; font-weight:800;'>보안 게이트웨이</h3>", unsafe_allow_html=True)
        mode = st.radio("", ["사용자 로그인", "관리자 접속"], horizontal=True, label_visibility="collapsed")
        
        users = load_json(USERS_FILE, [])
        settings = load_json(SETTINGS_FILE, {"master_password": "0303"})
        
        if mode == "관리자 접속":
            pwd = st.text_input("ADMIN", type="password", placeholder="마스터 키 입력", label_visibility="collapsed")
            if st.button("🚀 시스템 잠금 해제"):
                if pwd == settings["master_password"]:
                    st.session_state.authenticated, st.session_state.user_role = True, "admin"
                    st.session_state.current_user = {"name": "ADMIN"}
                    add_log("ADMIN", "System Unlock")
                    st.rerun()
                else: st.error("접근 권한이 없습니다.")
        else:
            n, k = st.text_input("NAME", placeholder="성함"), st.text_input("KEY", type="password", placeholder="라이선스 키")
            if st.button("🚀 로그인"):
                u = next((x for x in users if x["name"] == n and x["license"] == k), None)
                if u:
                    if datetime.strptime(u["expiry"], "%Y-%m-%d") < datetime.now(): st.error("만료된 라이선스입니다.")
                    else:
                        st.session_state.authenticated, st.session_state.user_role, st.session_state.current_user = True, "user", u
                        add_log(n, "Login Success")
                        st.rerun()
                else: st.error("인증 정보가 올바르지 않습니다.")
        st.markdown('</div>', unsafe_allow_html=True)

def show_main_app():
    with st.sidebar:
        st.markdown(f"### 💎 Data Intel PRO")
        st.info(f"User: {st.session_state.current_user.get('name')}")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()
        st.divider()

    st.markdown("<h2 style='font-weight: 900; color: #1e293b; margin-bottom: 2rem;'>Intelligence Workspace</h2>", unsafe_allow_html=True)
    tabs = st.tabs(["🔗 지능형 매칭", "📄 정밀 추출", "📊 심층 분석", "📂 스마트 병합"] + (["⚙️ 어드민 시스템"] if st.session_state.user_role == "admin" else []))
    
    with tabs[0]: # 매칭
        st.markdown('<div class="status-card">', unsafe_allow_html=True)
        st.markdown("#### 🔗 데이터 결합 및 유사도 매칭")
        c1, c2 = st.columns(2)
        b_f, r_f = c1.file_uploader("원본(Base)", key="m_b"), c2.file_uploader("참조(Ref)", key="m_r")
        if b_f and r_f:
            b_df, r_df = load_file_to_df(b_f), load_file_to_df(r_f)
            bk, rk = c1.selectbox("기준 열", b_df.columns), c2.selectbox("매칭 열", r_df.columns)
            r_cols = st.multiselect("추가할 데이터", [c for c in r_df.columns if c != rk])
            use_fuzzy = st.checkbox("유사도 기반 매칭(Fuzzy Match) 사용", help="글자가 정확히 일치하지 않아도 가장 비슷한 데이터를 찾습니다.")
            if st.button("🚀 지능형 매칭 실행"):
                with st.spinner("데이터 분석 중..."):
                    res = enterprise_match(b_df, r_df, bk, rk, r_cols, fuzzy=use_fuzzy)
                    st.dataframe(res.head(100), use_container_width=True)
                    st.download_button("📥 결과 다운로드(Excel)", convert_to_excel(res), "result.xlsx")
                    add_log(st.session_state.current_user.get('name'), "Data Matching", f"{len(res)} rows")
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]: # 추출
        st.markdown('<div class="status-card">', unsafe_allow_html=True)
        st.markdown("#### 📄 조건별 데이터 정밀 추출")
        f = st.file_uploader("추출 파일 업로드", key="ex_f")
        if f:
            df = load_file_to_df(f)
            col = st.selectbox("추출 기준 열", df.columns)
            val = st.text_input("필터 키워드 (공백 시 전체)")
            if st.button("🚀 정밀 추출"):
                res = df[df[col].astype(str).str.contains(val)] if val else df
                st.success(f"{len(res)}건 추출 완료")
                st.dataframe(res, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[2]: # 분석
        st.markdown('<div class="status-card">', unsafe_allow_html=True)
        st.markdown("#### 📊 데이터 품질 보고서 및 시각화")
        f = st.file_uploader("분석 파일 업로드", key="an_f")
        if f:
            df = load_file_to_df(f)
            st.write("##### 🧐 데이터 품질 요약")
            c1, c2, c3 = st.columns(3)
            c1.metric("전체 행", len(df))
            c2.metric("결측치(Null)", df.isnull().sum().sum())
            c3.metric("중복 행", df.duplicated().sum())
            st.write("##### 📈 주요 수치 시각화")
            st.area_chart(df.select_dtypes(include=[np.number]).iloc[:, :3])
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.user_role == "admin":
        with tabs[-1]:
            st.subheader("🕵️‍♂️ 시스템 모니터링 & 제어")
            logs = load_json(LOGS_FILE, [])
            if logs:
                ldf = pd.DataFrame(logs[::-1])
                st.dataframe(ldf.head(30), use_container_width=True)
                st.download_button("📥 로그 전체 다운로드", ldf.to_csv(index=False).encode('utf-8-sig'), "system_logs.csv")
            
            st.divider()
            st.subheader("🔑 라이선스 관리")
            with st.form("add"):
                c1, c2, c3 = st.columns(3)
                u_n, u_p, u_d = c1.text_input("성함"), c2.text_input("연락처"), c3.number_input("일수", 30)
                if st.form_submit_button("✅ 신규 사용자 등록"):
                    key = str(uuid.uuid4())[:8].upper()
                    us = load_json(USERS_FILE, [])
                    us.append({"name":u_n, "phone":u_p, "license":key, "expiry":(datetime.now()+timedelta(days=u_d)).strftime("%Y-%m-%d")})
                    save_json(USERS_FILE, us)
                    st.success(f"[{u_n}] 키: {key}")
                    st.rerun()
            
            # 사용자 관리 리스트
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
    if not st.session_state.authenticated: show_landing()
    else: show_main_app()

if __name__ == "__main__": main()
