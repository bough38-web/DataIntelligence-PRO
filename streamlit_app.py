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

def load_json(path, default):
    if not path.exists(): return default
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

# --- Page Config ---
st.set_page_config(page_title="Data Intel PRO | Commercial", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

# --- Session State ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_role' not in st.session_state: st.session_state.user_role = "user"
if 'current_user' not in st.session_state: st.session_state.current_user = None

# --- Commercial Premium Style ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&family=Pretendard:wght@400;600;700;800&display=swap');
    * { font-family: 'Pretendard', sans-serif; }
    
    .stApp { background: #f8fafc; color: #1e293b; }
    
    .hero-title {
        font-family: 'Outfit', sans-serif; font-size: 4.8rem; font-weight: 900; text-align: center;
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
        margin-top: 60px; margin-bottom: 5px; letter-spacing: -2px;
    }
    
    .login-card {
        background: white; border: 1px solid #e2e8f0; border-radius: 32px;
        padding: 50px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.05);
        max-width: 550px; margin: 0 auto; display: flex; flex-direction: column; align-items: center;
    }
    
    .premium-card {
        background: white; padding: 25px; border-radius: 20px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; margin-bottom: 20px;
    }
    
    .copyright-footer {
        position: fixed; bottom: 20px; right: 30px; color: #cbd5e1; font-size: 0.85rem; font-family: 'Outfit', sans-serif;
    }
    
    /* Button Customization */
    .stButton>button {
        background: #2563eb !important; color: white !important; font-weight: 800 !important;
        border-radius: 14px !important; padding: 14px !important; width: 100% !important;
        transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3) !important; }
    
    .stTextInput>div>div>input { border-radius: 12px !important; border: 1px solid #e2e8f0 !important; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- Logic Modules ---

def get_health_score(df):
    if df is None or df.empty: return 0
    total = df.size
    nulls = df.isnull().sum().sum()
    return round(100 - (nulls / total * 100), 1) if total > 0 else 0

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
    st.markdown("<p style='text-align: center; color: #64748b; font-size: 1.4rem; margin-bottom: 50px;'>The Future of Data Intelligence</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; font-weight: 800; margin-bottom: 30px;'>Secure Enterprise Login</h2>", unsafe_allow_html=True)
        
        mode = st.radio("", ["Master Admin", "Commercial User"], horizontal=True, label_visibility="collapsed")
        
        settings = load_json(SETTINGS_FILE, {"master_password": "0303"})
        users = load_json(USERS_FILE, [])
        
        if mode == "Master Admin":
            pwd = st.text_input("ADMIN PASSWORD", type="password", placeholder="0303", label_visibility="collapsed")
            if st.button("AUTHORIZE ADMIN"):
                if pwd == settings["master_password"]:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "admin"
                    st.rerun()
                else: st.error("Access Denied.")
        else:
            lic = st.text_input("LICENSE KEY", type="password", placeholder="Enter your key", label_visibility="collapsed")
            if st.button("VERIFY LICENSE"):
                user = next((u for u in users if u["license"] == lic), None)
                if user:
                    expiry = datetime.strptime(user["expiry"], "%Y-%m-%d")
                    if expiry < datetime.now(): st.error("Expired License.")
                    else:
                        st.session_state.authenticated = True
                        st.session_state.user_role = "user"
                        st.session_state.current_user = user
                        st.rerun()
                else: st.error("Invalid License Key.")
        
        st.markdown("<p style='color: #94a3b8; font-size: 0.8rem; margin-top: 30px;'>Professional Grade Suite v4.0</p>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="copyright-footer">© 2026 Seeun Park. All rights reserved.</div>', unsafe_allow_html=True)

# --- Main Application ---

def show_main_app():
    with st.sidebar:
        st.markdown(f"### 💎 Data Intel PRO")
        st.caption(f"Member: {st.session_state.current_user['name'] if st.session_state.current_user else 'ADMIN'}")
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.rerun()
        st.divider()
        if st.session_state.user_role == "user":
            st.markdown("#### 👤 내 정보 관리")
            new_key = st.text_input("라이선스 키 변경", type="password")
            if st.button("키 변경 저장"):
                users = load_json(USERS_FILE, [])
                for u in users:
                    if u["license"] == st.session_state.current_user["license"]:
                        u["license"] = new_key
                        st.session_state.current_user["license"] = new_key
                        break
                save_json(USERS_FILE, users)
                st.success("라이선스 키가 변경되었습니다.")

    st.markdown("<h1 style='color: #0f172a; font-weight: 900; font-size: 2.5rem;'>Expert Workspace</h1>", unsafe_allow_html=True)
    
    app_tabs = ["🔗 스마트 매칭", "📄 정밀 추출", "📊 심층 분석", "📂 스마트 병합"]
    if st.session_state.user_role == "admin": app_tabs.append("⚙️ 어드민")
    
    tabs = st.tabs(app_tabs)
    
    # 1. Matching
    with tabs[0]:
        with st.expander("❓ 사용법 안내", expanded=False):
            st.info("원본과 참조 파일을 업로드하고 기준 키를 선택하세요. 지능형 유사도를 켜면 오타도 교정됩니다.")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🟢 원본 (Base)")
            b_f = st.file_uploader("원본 업로드", key="b_f")
            if b_f:
                b_df = load_file_to_df(b_f)
                b_k = st.selectbox("기준 키", b_df.columns, key="b_k")
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🟡 참조 (Ref)")
            r_f = st.file_uploader("참조 업로드", key="r_f")
            if r_f:
                r_df = load_file_to_df(r_f)
                r_k = st.selectbox("매칭 키", r_df.columns, key="r_k")
                r_cols = st.multiselect("가져올 컬럼", [c for c in r_df.columns if c != r_k])
            st.markdown('</div>', unsafe_allow_html=True)
        if b_f and r_f:
            use_fuzzy = st.checkbox("지능형 유사도 매칭 가동")
            if st.button("🚀 매칭 연산 시작"):
                with st.spinner("AI 엔진이 분석 중입니다..."):
                    d1, d2 = b_df.copy(), r_df.copy()
                    if use_fuzzy:
                        targets = d2[r_k].unique()
                        d1[b_k] = d1[b_k].apply(lambda x: fuzzy_match_logic(x, targets) or x)
                    res = pd.merge(d1, d2[[r_k] + r_cols], left_on=b_k, right_on=r_k, how='left')
                    st.success("매칭 완료!")
                    st.dataframe(res.head(100))
                    st.download_button("📥 Excel 다운로드", convert_df_to_excel(res), "matched_expert.xlsx")

    # 2. Extract
    with tabs[1]:
        e_f = st.file_uploader("추출용 파일 업로드", key="e_f")
        if e_f:
            e_df = load_file_to_df(e_f)
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            ec1, ec2 = st.columns([1, 2])
            col_f = ec1.selectbox("필터 기준", e_df.columns)
            val_f = ec1.text_input("검색어 (쉼표 구분)")
            sel_e = ec2.multiselect("출력 컬럼", e_df.columns, default=list(e_df.columns))
            if st.button("📤 추출 및 AI 보정"):
                res = e_df[sel_e].copy()
                if val_f:
                    vals = [v.strip() for v in val_f.split(",")]
                    res = res[res[col_f].astype(str).str.contains("|".join(vals), na=False)]
                res = fill_service_small_from_mid(res)
                st.success("완료!")
                st.dataframe(res.head(100))
                st.download_button("📥 결과 저장", convert_df_to_excel(res), "extracted.xlsx")
            st.markdown('</div>', unsafe_allow_html=True)

    # 3. Insight
    with tabs[2]:
        a_f = st.file_uploader("분석 대상 업로드", key="a_f")
        if a_f:
            a_df = load_file_to_df(a_f)
            st.markdown(f"### 🏥 데이터 건강 점수: {get_health_score(a_df)}점")
            st.bar_chart(a_df.iloc[:, 0].value_counts().head(10))

    # 4. Merge
    with tabs[3]:
        m_fs = st.file_uploader("병합할 파일 다중 선택", accept_multiple_files=True)
        if m_fs:
            if st.button("🚀 스마트 병합 실행"):
                all_dfs = [load_file_to_df(f) for f in m_fs]
                final = pd.concat(all_dfs, ignore_index=True)
                st.success("통합 완료")
                st.download_button("📥 결과 다운로드", convert_df_to_excel(final), "merged.xlsx")

    # 5. Admin (Commercial Controls)
    if st.session_state.user_role == "admin":
        with tabs[-1]:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.subheader("⚙️ 라이선스 통합 관리")
            with st.form("auto_gen"):
                st.markdown("##### 🆕 라이선스 즉시 발급")
                u_name = st.text_input("사용자 이름")
                u_days = st.number_input("사용 기간(일)", min_value=1, value=365)
                if st.form_submit_button("자동 발급"):
                    new_key = str(uuid.uuid4())[:8].upper()
                    users = load_json(USERS_FILE, [])
                    users.append({
                        "name": u_name,
                        "license": new_key,
                        "expiry": (datetime.now() + timedelta(days=u_days)).strftime("%Y-%m-%d")
                    })
                    save_json(USERS_FILE, users)
                    st.success(f"[{u_name}] 라이선스 발급 완료: {new_key}")
                    st.rerun()
            
            st.divider()
            st.subheader("👥 사용자 계정 제어")
            users = load_json(USERS_FILE, [])
            for i, u in enumerate(users):
                c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                c1.write(f"**{u['name']}**")
                c2.write(f"`{u['license']}`")
                c3.write(f"만료: {u['expiry']}")
                if c4.button("초기화", key=f"reset_{i}"):
                    u["license"] = "1234" # Default Reset
                    save_json(USERS_FILE, users)
                    st.warning(f"{u['name']}님의 키가 1234로 초기화됨")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# --- Entry ---
def main():
    if not st.session_state.authenticated: show_landing()
    else: show_main_app()

if __name__ == "__main__": main()
