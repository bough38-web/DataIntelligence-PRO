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

# --- Custom Premium Style (Integrated) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&family=Pretendard:wght@400;600;700;800&display=swap');
    * { font-family: 'Pretendard', 'Outfit', sans-serif; }
    
    /* Landing Theme */
    .stApp[data-test-script-state="running"]::before { content: ""; } /* Placeholder for animation */
    
    .hero-title {
        font-family: 'Outfit', sans-serif; font-size: 5rem; font-weight: 900; text-align: center;
        background: linear-gradient(135deg, #60a5fa 0%, #2563eb 50%, #3b82f6 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -2px;
    }
    
    .login-card {
        background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(25px);
        border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 32px;
        padding: 50px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        max-width: 500px; margin: 0 auto;
    }
    
    .premium-card {
        background: white; padding: 25px; border-radius: 24px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #f1f5f9; margin-bottom: 20px;
        color: #0f172a;
    }
    
    .guide-box {
        background-color: #f1f5f9; padding: 15px; border-radius: 12px;
        border-left: 4px solid #2563eb; margin-bottom: 15px; font-size: 0.9rem;
    }

    /* Override for App Mode */
    .app-mode .stApp { background: #f8fafc !important; color: #0f172a !important; }
    </style>
    """, unsafe_allow_html=True)

# --- Logic Modules ---

def get_health_score(df):
    if df is None: return 0
    total_cells = df.size
    null_cells = df.isnull().sum().sum()
    score = 100 - (null_cells / total_cells * 100) if total_cells > 0 else 0
    return round(score, 1)

def fuzzy_match_logic(key, targets, threshold=0.6):
    matches = difflib.get_close_matches(str(key), [str(t) for t in targets], n=1, cutoff=threshold)
    return matches[0] if matches else None

def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# --- Auth UI ---

def show_landing():
    st.markdown("<style>.stApp { background: radial-gradient(circle at 0% 0%, #0f172a 0%, #1e293b 50%, #0f172a 100%); color: white; }</style>", unsafe_allow_html=True)
    st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)
    st.markdown("<h1 class='hero-title'>DATA INTEL PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 1.4rem; margin-bottom: 50px;'>Enterprise Data Intelligence Suite</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        mode = st.radio("Access Mode", ["Master Password", "Private License"], horizontal=True)
        
        settings = load_json(SETTINGS_FILE, {"master_password": "0303"})
        users = load_json(USERS_FILE, [])
        
        if mode == "Master Password":
            pwd = st.text_input("Password", type="password", placeholder="Master Secret (0303)")
            if st.button("AUTHORIZE"):
                if pwd == settings["master_password"]:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "admin"
                    st.rerun()
                else: st.error("Access Denied.")
        else:
            lic = st.text_input("License Key", type="password", placeholder="Your Unique Key")
            if st.button("VERIFY"):
                user = next((u for u in users if u["license"] == lic), None)
                if user:
                    expiry = datetime.strptime(user["expiry"], "%Y-%m-%d")
                    if expiry < datetime.now(): st.error("Expired License.")
                    else:
                        st.session_state.authenticated = True
                        st.session_state.user_role = "user"
                        st.session_state.current_user = user
                        st.rerun()
                else: st.error("Invalid License.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Main App UI ---

def show_main_app():
    st.markdown("<style>.stApp { background: #f8fafc !important; color: #0f172a !important; }</style>", unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown(f"### 💎 Data Intel PRO")
        st.caption(f"Status: {st.session_state.user_role.upper()} ACCESS")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()
        st.divider()
        st.success("Expert Engine v3.0 Active")

    st.markdown("<h1 style='color: #0f172a; font-weight: 900; font-size: 2.5rem;'>Intelligence Suite</h1>", unsafe_allow_html=True)
    
    app_tabs = ["🔗 스마트 매칭", "📄 정밀 추출", "📊 심층 분석", "📂 스마트 병합"]
    if st.session_state.user_role == "admin": app_tabs.append("⚙️ 관리자")
    
    t = st.tabs(app_tabs)
    
    # --- Tab 1: Matching ---
    with t[0]:
        with st.expander("❓ [초보자 가이드] 사용 방법 보기"):
            st.info("원본과 참조 파일을 올리고 공통 컬럼을 선택하세요. '유사도 매칭'을 켜면 오타가 있어도 자동으로 연결됩니다.")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🟢 원본 데이터")
            b_f = st.file_uploader("원본 업로드", key="b_f")
            if b_f:
                b_df = load_file_to_df(b_f)
                b_k = st.selectbox("기준 키 (Key)", b_df.columns, key="b_k")
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🟡 참조 데이터")
            r_f = st.file_uploader("참조 업로드", key="r_f")
            if r_f:
                r_df = load_file_to_df(r_f)
                r_k = st.selectbox("매칭 키 (Match)", r_df.columns, key="r_k")
                r_cols = st.multiselect("가져올 필드", [c for c in r_df.columns if c != r_k])
            st.markdown('</div>', unsafe_allow_html=True)
            
        if b_f and r_f:
            st.markdown("#### ⚙️ 지능형 옵션")
            opt_c1, opt_c2 = st.columns(2)
            use_fuzzy = opt_c1.checkbox("지능형 유사도 매칭 (Fuzzy Match)")
            do_norm = opt_c2.checkbox("키 정규화 (대문자/공백제거)", value=True)
            
            if st.button("🚀 매칭 가동"):
                with st.spinner("전문가 엔진이 데이터를 분석 중입니다..."):
                    d1, d2 = b_df.copy(), r_df.copy()
                    if use_fuzzy:
                        targets = d2[r_k].unique()
                        d1[b_k] = d1[b_k].apply(lambda x: fuzzy_match_logic(x, targets) or x)
                    elif do_norm:
                        d1[b_k] = d1[b_k].astype(str).str.strip().str.upper()
                        d2[r_k] = d2[r_k].astype(str).str.strip().str.upper()
                    
                    res = pd.merge(d1, d2[[r_k] + r_cols], left_on=b_k, right_on=r_k, how='left')
                    st.success(f"매칭 완료! ({len(res):,}행)")
                    st.dataframe(res.head(100))
                    st.download_button("📥 Excel 다운로드", convert_df_to_excel(res), "matched_expert.xlsx")

    # --- Tab 2: Extract ---
    with t[1]:
        with st.expander("❓ [초보자 가이드] 사용 방법 보기"):
            st.info("특정 단어가 포함된 행만 골라내거나, AI 기능을 통해 비어있는 카테고리를 자동으로 채울 수 있습니다.")
        
        e_f = st.file_uploader("가공 대상 업로드", key="e_f")
        if e_f:
            e_df = load_file_to_df(e_f)
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            ec1, ec2 = st.columns([1, 2])
            col_f = ec1.selectbox("필터 컬럼", e_df.columns)
            val_f = ec1.text_input("검색어 (콤마로 구분)")
            all_e = list(e_df.columns)
            sel_e = ec2.multiselect("출력 컬럼", all_e, default=all_e)
            
            st.markdown("##### ✨ 전문가 보정")
            oc1, oc2 = st.columns(2)
            do_ai = oc1.checkbox("AI 결측치 자동 채움 (Impute)", value=True)
            do_dedup = oc2.checkbox("중복 행 제거 (Dedup)", value=True)
            
            if st.button("📤 추출 실행"):
                res = e_df[sel_e].copy()
                if val_f:
                    vals = [v.strip() for v in val_f.split(",")]
                    res = res[res[col_f].astype(str).str.contains("|".join(vals), na=False)]
                if do_ai: res = fill_service_small_from_mid(res)
                if do_dedup: res = res.drop_duplicates()
                st.success("추출 완료!")
                st.dataframe(res.head(100))
                st.download_button("📥 결과 저장", convert_df_to_excel(res), "extracted_expert.xlsx")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- Tab 3: Insight ---
    with t[2]:
        a_f = st.file_uploader("분석용 파일 업로드", key="a_f")
        if a_f:
            a_df = load_file_to_df(a_f)
            score = get_health_score(a_df)
            st.markdown(f"### 🏥 데이터 건강 점수: <span style='color: #16a34a; font-weight: 800;'>{score}점</span>", unsafe_allow_html=True)
            st.divider()
            st.subheader("📋 자동 요약 리포트")
            c1, c2 = st.columns(2)
            p_idx = c1.selectbox("그룹화 기준", a_df.columns)
            p_val = c2.selectbox("수치 (Count)", a_df.columns)
            pivot = a_df.groupby(p_idx)[p_val].count().reset_index()
            st.table(pivot.head(10))
            st.bar_chart(a_df[p_idx].value_counts().head(15))

    # --- Tab 4: Merge ---
    with t[3]:
        m_fs = st.file_uploader("여러 파일을 선택하세요", accept_multiple_files=True)
        if m_fs:
            if st.button("🚀 통합 파일 생성"):
                all_dfs = [load_file_to_df(f) for f in m_fs]
                final = pd.concat(all_dfs, ignore_index=True)
                st.success(f"{len(m_fs)}개 파일 통합 완료!")
                st.download_button("📥 통합 결과 저장", convert_df_to_excel(final), "merged_expert.xlsx")

    # --- Tab 5: Admin ---
    if st.session_state.user_role == "admin":
        with t[-1]:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.subheader("⚙️ 어드민 패널")
            with st.form("admin_user"):
                st.markdown("##### 신규 라이선스 발급")
                c1, c2 = st.columns(2)
                u_n = c1.text_input("사용자 이름")
                u_l = c2.text_input("고유 키 (License)")
                u_e = c2.date_input("만료일", value=datetime.now()+timedelta(days=365))
                if st.form_submit_button("등록"):
                    users = load_json(USERS_FILE, [])
                    users.append({"name":u_n, "license":u_l, "expiry":u_e.strftime("%Y-%m-%d")})
                    save_json(USERS_FILE, users)
                    st.success("등록 완료")
                    st.rerun()
            st.divider()
            st.subheader("사용자 현황")
            st.dataframe(pd.DataFrame(load_json(USERS_FILE, [])))
            st.markdown('</div>', unsafe_allow_html=True)

# --- Entry ---
def main():
    if not st.session_state.authenticated: show_landing()
    else: show_main_app()

if __name__ == "__main__": main()
