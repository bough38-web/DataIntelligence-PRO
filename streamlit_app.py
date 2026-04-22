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

# --- Soft Premium Style ( 정밀 검증 및 가시성 개선 ) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&family=Pretendard:wght@400;600;700;800&display=swap');
    * { font-family: 'Pretendard', sans-serif; }
    
    /* Light Theme Background */
    .stApp {
        background: linear-gradient(135deg, #f8fafc 0%, #ffffff 50%, #f1f5f9 100%);
        color: #1e293b;
    }
    
    .hero-title {
        font-family: 'Outfit', sans-serif; font-size: 4.5rem; font-weight: 900; text-align: center;
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px; letter-spacing: -1.5px;
    }
    
    .login-card {
        background: white; border: 1px solid #e2e8f0; border-radius: 32px;
        padding: 50px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05);
        max-width: 480px; margin: 0 auto;
    }
    
    .premium-card {
        background: white; padding: 25px; border-radius: 20px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; margin-bottom: 20px;
    }
    
    .guide-box {
        background-color: #f1f5f9; padding: 18px; border-radius: 14px;
        border-left: 5px solid #3b82f6; margin-bottom: 20px; color: #334155; line-height: 1.6;
    }

    .health-score-text { font-size: 3rem; font-weight: 900; color: #16a34a; }
    
    /* Button & Input Clarity */
    .stButton>button {
        background: #2563eb !important; color: white !important; font-weight: 700 !important;
        border-radius: 14px !important; padding: 12px 24px !important; transition: 0.3s !important;
    }
    .stTextInput>div>div>input { border-radius: 12px !important; border: 1px solid #cbd5e1 !important; }
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

# --- Auth UI ---

def show_landing():
    st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)
    st.markdown("<h1 class='hero-title'>DATA INTEL PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b; font-size: 1.4rem; margin-bottom: 50px;'>가장 편안하고 강력한 데이터 가공 솔루션</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #0f172a; margin-bottom: 30px;'>보안 인증 로그인</h2>", unsafe_allow_html=True)
        mode = st.radio("접속 방식 선택", ["마스터 패스워드", "개인 라이선스"], horizontal=True)
        
        settings = load_json(SETTINGS_FILE, {"master_password": "0303"})
        users = load_json(USERS_FILE, [])
        
        if mode == "마스터 패스워드":
            pwd = st.text_input("패스워드", type="password", placeholder="0303")
            if st.button("🚀 시스템 시작"):
                if pwd == settings["master_password"]:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "admin"
                    st.rerun()
                else: st.error("패스워드가 틀렸습니다.")
        else:
            lic = st.text_input("라이선스 키", type="password")
            if st.button("🚀 인증 및 접속"):
                user = next((u for u in users if u["license"] == lic), None)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "user"
                    st.session_state.current_user = user
                    st.rerun()
                else: st.error("유효하지 않은 라이선스입니다.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Main App Modules ---

def show_main_app():
    with st.sidebar:
        st.markdown(f"### 💎 Data Intel PRO")
        st.caption(f"Role: {st.session_state.user_role.upper()}")
        if st.button("🚪 로그아웃"):
            st.session_state.authenticated = False
            st.rerun()
        st.divider()
        st.info("전문가 엔진 v3.5 가동 중")

    st.markdown("<h1 style='color: #0f172a; font-weight: 900;'>Intelligence Suite</h1>", unsafe_allow_html=True)
    
    tabs = st.tabs(["🔗 스마트 매칭", "📄 정밀 추출", "📊 심층 분석", "📂 스마트 병합", "⚙️ 시스템 관리"])
    
    # --- 1. Matching (복구 완료) ---
    with tabs[0]:
        with st.expander("❓ [도움말] 스마트 매칭은 어떻게 하나요?", expanded=False):
            st.markdown("""
            **스마트 매칭**은 엑셀의 VLOOKUP 기능을 자동화합니다. 
            - **원본**: 데이터를 붙일 메인 파일
            - **참조**: 데이터를 가져올 소스 파일
            - **지능형 유사도**: '삼성'과 '삼성전자' 같이 이름이 미세하게 달라도 자동으로 찾아줍니다.
            """)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🟢 원본 파일 (Target)")
            b_f = st.file_uploader("원본 업로드", key="b_f")
            if b_f:
                b_df = load_file_to_df(b_f)
                b_k = st.selectbox("기준 키 컬럼", b_df.columns, key="b_k")
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🟡 참조 파일 (Reference)")
            r_f = st.file_uploader("참조 업로드", key="r_f")
            if r_f:
                r_df = load_file_to_df(r_f)
                r_k = st.selectbox("매칭 키 컬럼", r_df.columns, key="r_k")
                r_cols = st.multiselect("가져올 컬럼 선택", [c for c in r_df.columns if c != r_k])
            st.markdown('</div>', unsafe_allow_html=True)
            
        if b_f and r_f:
            st.markdown("#### ⚙️ 지능형 엔진 옵션")
            col_o1, col_o2 = st.columns(2)
            use_fuzzy = col_o1.checkbox("지능형 유사도 매칭 (Fuzzy Match)", help="오타나 미세한 명칭 차이를 자동으로 보정합니다.")
            do_norm = col_o2.checkbox("키 정규화 자동 적용", value=True)
            
            if st.button("🚀 매칭 가동"):
                with st.spinner("알고리즘 연산 중..."):
                    d1, d2 = b_df.copy(), r_df.copy()
                    if use_fuzzy:
                        targets = d2[r_k].unique()
                        d1[b_k] = d1[b_k].apply(lambda x: fuzzy_match_logic(x, targets) or x)
                    elif do_norm:
                        d1[b_k] = d1[b_k].astype(str).str.strip().str.upper()
                        d2[r_k] = d2[r_k].astype(str).str.strip().str.upper()
                    
                    res = pd.merge(d1, d2[[r_k] + r_cols], left_on=b_k, right_on=r_k, how='left')
                    st.success(f"매칭 성공! 총 {len(res):,}행의 데이터가 결합되었습니다.")
                    st.dataframe(res.head(100))
                    st.download_button("📥 Excel 다운로드", convert_df_to_excel(res), "match_pro.xlsx")

    # --- 2. Extract (복구 완료) ---
    with tabs[1]:
        with st.expander("❓ [도움말] 정밀 추출은 어떻게 하나요?", expanded=False):
            st.markdown("""
            **정밀 추출**은 수만 개의 행 중에서 원하는 데이터만 골라내고 보정합니다.
            - **필터**: 특정 단어나 패턴을 검색합니다. (쉼표로 여러 개 검색 가능)
            - **AI 결측치 채움**: 비어있는 카테고리나 정보를 주변 데이터를 통해 추론하여 채워줍니다.
            """)
        
        e_f = st.file_uploader("가공 대상 업로드", key="e_f")
        if e_f:
            e_df = load_file_to_df(e_f)
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            ec1, ec2 = st.columns([1, 2])
            col_f = ec1.selectbox("필터 적용 대상", e_df.columns)
            val_f = ec1.text_input("검색어 입력 (예: 삼성, 현대, LG)")
            
            all_e = list(e_df.columns)
            sel_e = ec2.multiselect("출력 컬럼 구성", all_e, default=all_e)
            
            st.markdown("##### ✨ 전문가 자동 보정")
            oc1, oc2 = st.columns(2)
            do_ai = oc1.checkbox("AI 기반 결측치 자동 추론 (Impute)", value=True)
            do_dedup = oc2.checkbox("중복 데이터 제거 (Unique Only)", value=True)
            
            if st.button("📤 추출 및 보정 실행"):
                with st.spinner("데이터 가공 중..."):
                    res = e_df[sel_e].copy()
                    if val_f:
                        vals = [v.strip() for v in val_f.split(",")]
                        res = res[res[col_f].astype(str).str.contains("|".join(vals), na=False)]
                    if do_ai: res = fill_service_small_from_mid(res)
                    if do_dedup: res = res.drop_duplicates()
                    st.success(f"가공 완료! {len(res):,}개의 정제된 데이터가 준비되었습니다.")
                    st.dataframe(res.head(100))
                    st.download_button("📥 가공 결과 저장", convert_df_to_excel(res), "extracted_pro.xlsx")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- 3. Insight (복구 완료) ---
    with tabs[2]:
        st.markdown("<div class='guide-box'>이 탭에서는 데이터의 품질을 진단하고, 핵심 요약 보고서를 자동으로 생성합니다.</div>", unsafe_allow_html=True)
        a_f = st.file_uploader("분석용 파일 업로드", key="a_f")
        if a_f:
            a_df = load_file_to_df(a_f)
            score = get_health_score(a_df)
            st.markdown(f"### 🏥 데이터 건강 점수: <span class='health-score-text'>{score}점</span>", unsafe_allow_html=True)
            
            st.divider()
            st.subheader("📋 자동 리포트 (Summary)")
            c1, c2 = st.columns(2)
            p_idx = c1.selectbox("그룹화 기준 컬럼", a_df.columns)
            p_val = c2.selectbox("수치 계산 컬럼", a_df.columns)
            pivot = a_df.groupby(p_idx)[p_val].count().reset_index()
            st.table(pivot.head(10))
            st.bar_chart(a_df[p_idx].value_counts().head(15))

    # --- 4. Merge (복구 완료) ---
    with tabs[3]:
        st.markdown("<div class='guide-box'>여러 개의 엑셀 파일을 하나로 합칩니다. 양식이 달라도 공통 컬럼을 기준으로 병합됩니다.</div>", unsafe_allow_html=True)
        m_fs = st.file_uploader("병합할 파일들을 모두 선택하세요", accept_multiple_files=True)
        if m_fs:
            if st.button("🚀 통합 병합 실행"):
                all_dfs = [load_file_to_df(f) for f in m_fs]
                final = pd.concat(all_dfs, ignore_index=True)
                st.success(f"총 {len(m_fs)}개의 파일이 하나로 통합되었습니다!")
                st.download_button("📥 통합 결과 저장", convert_df_to_excel(final), "merged_pro.xlsx")

    # --- 5. Admin (복구 완료) ---
    if st.session_state.user_role == "admin":
        with tabs[-1]:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.subheader("⚙️ 관리자 설정")
            with st.form("admin_settings"):
                st.markdown("##### 🛡 라이선스 신규 발급")
                c1, c2 = st.columns(2)
                u_n = c1.text_input("사용자 이름")
                u_l = c2.text_input("라이선스 키 (Password)")
                u_e = c2.date_input("만료일 설정", value=datetime.now()+timedelta(days=365))
                if st.form_submit_button("라이선스 생성"):
                    users = load_json(USERS_FILE, [])
                    users.append({"name":u_n, "license":u_l, "expiry":u_e.strftime("%Y-%m-%d")})
                    save_json(USERS_FILE, users)
                    st.success(f"{u_n}님의 라이선스가 발급되었습니다.")
                    st.rerun()
            st.divider()
            st.subheader("현재 사용자 현황")
            st.dataframe(pd.DataFrame(load_json(USERS_FILE, [])), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

# --- Entry ---
def main():
    if not st.session_state.authenticated: show_landing()
    else: show_main_app()

if __name__ == "__main__": main()
