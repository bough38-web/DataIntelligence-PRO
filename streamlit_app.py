import streamlit as st
import pandas as pd
import numpy as np
import os
import io
import time
import json
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
st.set_page_config(page_title="Data Intel PRO | Enterprise", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

# --- Session State ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_role' not in st.session_state: st.session_state.user_role = "user"
if 'current_user' not in st.session_state: st.session_state.current_user = None

# --- Global Style ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&family=Pretendard:wght@400;600;700;800&display=swap');
    * { font-family: 'Pretendard', sans-serif; }
    
    .stApp {
        background: linear-gradient(135deg, #f8fafc 0%, #ffffff 50%, #f1f5f9 100%);
        color: #1e293b;
    }
    
    .hero-title {
        font-family: 'Outfit', sans-serif; font-size: 4.8rem; font-weight: 900; text-align: center;
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
        margin-top: 80px; margin-bottom: 5px; letter-spacing: -2px;
    }
    
    .hero-subtitle {
        text-align: center; color: #64748b; font-size: 1.5rem; font-weight: 500; margin-bottom: 60px;
    }
    
    .login-card {
        background: white; border: 1px solid #e2e8f0; border-radius: 40px;
        padding: 50px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.05);
        max-width: 520px; margin: 0 auto;
        display: flex; flex-direction: column; align-items: center;
    }
    
    .copyright-footer {
        position: fixed; bottom: 20px; right: 30px;
        color: #cbd5e1; font-size: 0.85rem; font-family: 'Outfit', sans-serif;
    }
    
    .premium-card {
        background: white; padding: 25px; border-radius: 24px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #f1f5f9; margin-bottom: 20px;
    }
    
    .stTextInput>div>div>input {
        border-radius: 16px !important; border: 1px solid #cbd5e1 !important;
        text-align: center; padding: 15px !important;
    }
    
    .stButton>button {
        background: #2563eb !important; color: white !important; font-weight: 800 !important;
        border-radius: 16px !important; padding: 16px !important; width: 100% !important;
    }
    
    .stRadio > div { display: flex; justify-content: center; gap: 30px; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- Logic Modules ---

def get_health_score(df):
    if df is None or df.empty: return 0
    total = df.size
    nulls = df.isnull().sum().sum()
    score = 100 - (nulls / total * 100) if total > 0 else 0
    return round(score, 1)

def fuzzy_match_logic(key, targets, threshold=0.6):
    matches = difflib.get_close_matches(str(key), [str(t) for t in targets], n=1, cutoff=threshold)
    return matches[0] if matches else None

def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# --- Auth & Landing ---

def show_landing():
    st.markdown("<h1 class='hero-title'>DATA INTEL PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p class='hero-subtitle'>Smart & Secure Data Workflows</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #0f172a; margin-bottom: 40px; font-weight: 800;'>시스템 보안 인증</h2>", unsafe_allow_html=True)
        
        mode = st.radio("", ["마스터 패스워드", "개인 라이선스"], horizontal=True, key="login_mode", label_visibility="collapsed")
        
        settings = load_json(SETTINGS_FILE, {"master_password": "0303"})
        users = load_json(USERS_FILE, [])
        
        if mode == "마스터 패스워드":
            pwd = st.text_input("PASSWORD", type="password", placeholder="Master Secret", label_visibility="collapsed")
            if st.button("🚀 AUTHORIZE"):
                if pwd == settings["master_password"]:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "admin"
                    st.rerun()
                else: st.error("패스워드 불일치")
        else:
            lic = st.text_input("LICENSE", type="password", placeholder="License Key", label_visibility="collapsed")
            if st.button("🚀 VERIFY"):
                user = next((u for u in users if u["license"] == lic), None)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "user"
                    st.session_state.current_user = user
                    st.rerun()
                else: st.error("유효하지 않은 라이선스")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="copyright-footer">© 2026 Seeun Park. All rights reserved.</div>', unsafe_allow_html=True)

# --- Main App (Full Functional Logic) ---

def show_main_app():
    with st.sidebar:
        st.markdown("### 💎 Data Intel PRO")
        st.caption(f"Access: {st.session_state.user_role.upper()}")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()
        st.divider()
        st.success("Expert Suite Active")

    st.markdown("<h1 style='color: #0f172a; font-weight: 900; font-size: 2.5rem;'>Intelligence Suite</h1>", unsafe_allow_html=True)
    
    tabs = st.tabs(["🔗 스마트 매칭", "📄 정밀 추출", "📊 심층 분석", "📂 스마트 병합", "⚙️ 시스템 관리"])
    
    # 1. Matching
    with tabs[0]:
        with st.expander("❓ [가이드] 스마트 매칭 사용법"):
            st.info("원본과 참조 파일을 올리고 기준 키를 선택하세요. 유사도 매칭을 켜면 오타도 교정됩니다.")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            b_f = st.file_uploader("원본 업로드", key="b_f")
            if b_f:
                b_df = load_file_to_df(b_f)
                b_k = st.selectbox("기준 키", b_df.columns, key="b_k")
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            r_f = st.file_uploader("참조 업로드", key="r_f")
            if r_f:
                r_df = load_file_to_df(r_f)
                r_k = st.selectbox("매칭 키", r_df.columns, key="r_k")
                r_cols = st.multiselect("가져올 필드", [c for c in r_df.columns if c != r_k])
            st.markdown('</div>', unsafe_allow_html=True)
        if b_f and r_f:
            use_fuzzy = st.checkbox("지능형 유사도 매칭")
            if st.button("🚀 매칭 실행"):
                with st.spinner("연산 중..."):
                    d1, d2 = b_df.copy(), r_df.copy()
                    if use_fuzzy:
                        targets = d2[r_k].unique()
                        d1[b_k] = d1[b_k].apply(lambda x: fuzzy_match_logic(x, targets) or x)
                    res = pd.merge(d1, d2[[r_k] + r_cols], left_on=b_k, right_on=r_k, how='left')
                    st.success("매칭 완료!")
                    st.dataframe(res.head(100))
                    st.download_button("📥 다운로드", convert_df_to_excel(res), "matched.xlsx")

    # 2. Extract
    with tabs[1]:
        e_f = st.file_uploader("가공 파일 업로드", key="e_f")
        if e_f:
            e_df = load_file_to_df(e_f)
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            c_f = st.selectbox("필터 컬럼", e_df.columns)
            v_f = st.text_input("검색어 (쉼표 구분)")
            do_ai = st.checkbox("AI 결측치 채움", value=True)
            if st.button("📤 추출 실행"):
                res = e_df.copy()
                if v_f:
                    vals = [v.strip() for v in v_f.split(",")]
                    res = res[res[c_f].astype(str).str.contains("|".join(vals), na=False)]
                if do_ai: res = fill_service_small_from_mid(res)
                st.success("완료!")
                st.dataframe(res.head(100))
                st.download_button("📥 저장", convert_df_to_excel(res), "extracted.xlsx")
            st.markdown('</div>', unsafe_allow_html=True)

    # 3. Insight
    with tabs[2]:
        a_f = st.file_uploader("분석 파일 업로드", key="a_f")
        if a_f:
            a_df = load_file_to_df(a_f)
            st.markdown(f"### 🏥 데이터 건강 점수: {get_health_score(a_df)}점")
            st.bar_chart(a_df.iloc[:, 0].value_counts().head(10))

    # 4. Merge
    with tabs[3]:
        m_fs = st.file_uploader("병합할 파일 다중 선택", accept_multiple_files=True)
        if m_fs:
            if st.button("🚀 통합 파일 생성"):
                all_dfs = [load_file_to_df(f) for f in m_fs]
                final = pd.concat(all_dfs, ignore_index=True)
                st.success(f"{len(m_fs)}개 파일 통합 완료")
                st.download_button("📥 통합 결과 저장", convert_df_to_excel(final), "merged.xlsx")

    # 5. Admin
    if st.session_state.user_role == "admin":
        with tabs[4]:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.subheader("⚙️ 어드민 패널")
            with st.form("admin_u"):
                u_n = st.text_input("사용자 이름")
                u_l = st.text_input("라이선스 키")
                if st.form_submit_button("등록"):
                    users = load_json(USERS_FILE, [])
                    users.append({"name":u_n, "license":u_l, "expiry":(datetime.now()+timedelta(days=365)).strftime("%Y-%m-%d")})
                    save_json(USERS_FILE, users)
                    st.success("등록 완료")
                    st.rerun()
            st.dataframe(pd.DataFrame(load_json(USERS_FILE, [])))
            st.markdown('</div>', unsafe_allow_html=True)

# --- Main Entry ---
def main():
    if not st.session_state.authenticated: show_landing()
    else: show_main_app()

if __name__ == "__main__": main()
