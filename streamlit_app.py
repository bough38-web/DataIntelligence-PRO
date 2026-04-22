import streamlit as st
import pandas as pd
import os
import io
import time
from app.core.handlers import load_file_to_df, get_sheet_names, extract_columns_fast, extract_unique_values_fast
from app.core.processors import apply_advanced_conditions, fill_service_small_from_mid, apply_sorting, apply_dedup
from app.utils.common import clean_text

# --- Page Configuration ---
st.set_page_config(
    page_title="Data Intelligence PRO | Web",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling (Premium Aesthetics) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main {
        background-color: #f8fafc;
    }
    
    /* Premium Sidebar */
    [data-testid="stSidebar"] {
        background-image: linear-gradient(#1e293b, #0f172a);
        color: white;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    /* Card Style */
    .premium-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    
    .expert-badge {
        background-color: #dcfce7;
        color: #166534;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        border: 1px solid #bbf7d0;
    }
    
    .stButton>button {
        background-image: linear-gradient(to right, #2563eb, #7c3aed);
        color: white;
        border: none;
        padding: 10px 24px;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.4);
    }
    
    /* Header */
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(to right, #1e293b, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Session State Helpers ---
if 'history' not in st.session_state:
    st.session_state.history = []

def add_log(msg):
    ts = time.strftime("%H:%M:%S")
    st.session_state.history.append(f"[{ts}] {msg}")

# --- App Layout ---

def main():
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/database.png", width=80)
        st.markdown("### Data Intelligence PRO")
        st.markdown("v2.5.0 Premium Web")
        st.divider()
        
        st.markdown("#### 🚀 전문가 기법 적용")
        st.caption("활성화된 분석 엔진")
        st.success("✅ 키 정규화 엔진")
        st.success("✅ 중복 행 자동 탐지")
        st.success("✅ 지능형 인코딩 감지")
        st.success("✅ Regex 패턴 추출기")
        
        st.divider()
        with st.expander("📝 최근 작업 로그"):
            for log in reversed(st.session_state.history[-10:]):
                st.caption(log)
    
    # Main Content
    st.markdown('<h1 class="main-header">🚀 Data Intelligence PRO</h1>', unsafe_allow_html=True)
    
    tabs = st.tabs(["🏠 홈", "🔗 데이터 매칭", "📄 단일 파일 추출", "📂 파일 병합", "📈 심층 분석"])
    
    # --- Home Tab ---
    with tabs[0]:
        st.markdown("""
        <div class="premium-card">
            <h2>환영합니다!</h2>
            <p>최첨단 데이터 추출 및 통합 엔진을 웹 브라우저에서 직접 경험하세요.</p>
            <div style="display: flex; gap: 10px; margin-top: 20px;">
                <span class="expert-badge">AI 기반 추론</span>
                <span class="expert-badge">실시간 파싱</span>
                <span class="expert-badge">엔터프라이즈 보안</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.info("#### 🔗 데이터 매칭\n키 값을 기준으로 두 데이터를 지능적으로 결합합니다. (VLOOKUP Pro)")
        with c2:
            st.warning("#### 📄 정밀 추출\n고급 필터와 정규식을 사용하여 원하는 데이터만 골라냅니다.")
        with c3:
            st.success("#### 📂 파일 병합\n다양한 규격의 파일들을 하나의 표준 데이터로 통합합니다.")

    # --- Matching Tab ---
    with tabs[1]:
        st.subheader("🔗 고도화된 데이터 매칭 (Match Engine v3)")
        
        with st.container():
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("##### 1. 원본 데이터 (Base)")
                base_f = st.file_uploader("파일 선택", type=['xlsx', 'csv', 'xls'], key="base")
                if base_f:
                    sheets = get_sheet_names(base_f)
                    b_sheet = st.selectbox("시트", ["(기본)"] + sheets if sheets else ["(기본)"], key="b_s")
                    b_df = load_file_to_df(base_f, sheet_name=None if b_sheet == "(기본)" else b_sheet)
                    b_key = st.selectbox("매칭 기준 컬럼 (ID)", b_df.columns, key="b_k")
            
            with col2:
                st.markdown("##### 2. 참조 데이터 (Reference)")
                ref_f = st.file_uploader("파일 선택", type=['xlsx', 'csv', 'xls'], key="ref")
                if ref_f:
                    sheets = get_sheet_names(ref_f)
                    r_sheet = st.selectbox("시트", ["(기본)"] + sheets if sheets else ["(기본)"], key="r_s")
                    r_df = load_file_to_df(ref_f, sheet_name=None if r_sheet == "(기본)" else r_sheet)
                    r_key = st.selectbox("매칭 기준 컬럼 (ID)", r_df.columns, key="r_k")
                    r_cols = st.multiselect("가져올 컬럼 선택", [c for c in r_df.columns if c != r_key])
            st.markdown('</div>', unsafe_allow_html=True)
            
        if base_f and ref_f:
            st.markdown("#### ⚙️ 매칭 옵션")
            opt1, opt2 = st.columns(2)
            with opt1:
                norm_keys = st.checkbox("키 컬럼 정규화 (공백/대소문자 처리)", value=True)
            with opt2:
                dedup_ref = st.checkbox("참조 데이터 중복 제거 (VLOOKUP 스타일)", value=True)
                
            if st.button("🚀 지능형 매칭 실행"):
                with st.spinner("알고리즘 연산 중..."):
                    df1 = b_df.copy()
                    df2 = r_df.copy()
                    
                    if norm_keys:
                        df1[b_key] = df1[b_key].astype(str).str.strip().str.upper()
                        df2[r_key] = df2[r_key].astype(str).str.strip().str.upper()
                    
                    if dedup_ref:
                        df2 = df2.drop_duplicates(subset=[r_key])
                        
                    res = pd.merge(df1, df2[[r_key] + r_cols], left_on=b_key, right_on=r_key, how='left')
                    if b_key != r_key: res.drop(columns=[r_key], inplace=True)
                    
                    add_log(f"매칭 완료: {len(res)}건")
                    st.success(f"매칭 완료! ({len(res):,}행)")
                    st.dataframe(res.head(50))
                    
                    csv = res.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                    st.download_button("📥 결과 다운로드", csv, "matched_data.csv", "text/csv")

    # --- Single Extraction Tab ---
    with tabs[2]:
        st.subheader("📄 정밀 데이터 추출 (Expert Filter)")
        f_ext = st.file_uploader("추출용 파일 업로드", type=['xlsx', 'csv', 'xls'], key="ext")
        if f_ext:
            sheets = get_sheet_names(f_ext)
            e_s = st.selectbox("시트", ["(기본)"] + sheets if sheets else ["(기본)"], key="e_s")
            df_e = load_file_to_df(f_ext, sheet_name=None if e_s == "(기본)" else e_s)
            
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🔍 필터링 조건 설정")
            
            with st.expander("필터링 규칙 추가"):
                col_f = st.selectbox("필터 컬럼", df_e.columns)
                mode_f = st.selectbox("조건 방식", ["일치 (Equals)", "포함 (Contains)", "정규식 (Regex)", "시작하는 말", "끝나는 말"])
                val_f = st.text_input("값 (여러 개일 경우 콤마로 구분)")
                
            col_sel = st.multiselect("출력할 컬럼 선택", df_e.columns, default=list(df_e.columns))
            
            st.markdown("##### 🚀 전문가 처리")
            c1, c2, c3 = st.columns(3)
            with c1: fill_svc = st.checkbox("서비스(소) 자동 채움", value=True, key="f_s_w")
            with c2: dedup_e = st.checkbox("중복 행 제거", key="d_e_w")
            with c3: sort_e = st.checkbox("정렬 적용", key="s_e_w")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if st.button("📤 정밀 추출 실행"):
                with st.spinner("데이터 가공 중..."):
                    res = df_e[col_sel].copy()
                    
                    # Apply Simple Filter if value exists
                    if val_f:
                        vals = [x.strip() for x in val_f.split(",")]
                        if mode_f == "일치 (Equals)":
                            res = res[res[col_f].astype(str).isin(vals)]
                        elif mode_f == "포함 (Contains)":
                            res = res[res[col_f].astype(str).str.contains("|".join(vals), na=False)]
                        elif mode_f == "정규식 (Regex)":
                            res = res[res[col_f].astype(str).str.contains(val_f, regex=True, na=False)]
                    
                    if fill_svc:
                        res = fill_service_small_from_mid(res)
                    if dedup_e:
                        res = res.drop_duplicates()
                        
                    add_log(f"단일 추출 완료: {len(res)}건")
                    st.success(f"추출 완료! ({len(res):,}행)")
                    st.dataframe(res.head(50))
                    csv = res.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                    st.download_button("📥 추출 결과 다운로드", csv, "extracted_data.csv", "text/csv")

    # --- Merge Tab ---
    with tabs[3]:
        st.subheader("📂 다중 파일 통합 (Merge Engine)")
        files = st.file_uploader("병합할 모든 파일 선택", type=['xlsx', 'csv', 'xls'], accept_multiple_files=True)
        if files:
            st.markdown(f'<div class="expert-badge">대기 중인 파일: {len(files)}개</div>', unsafe_allow_html=True)
            if st.button("🚀 통합 병합 시작"):
                frames = []
                bar = st.progress(0)
                for i, file in enumerate(files):
                    tmp = load_file_to_df(file)
                    frames.append(tmp)
                    bar.progress((i + 1) / len(files))
                
                final = pd.concat(frames, ignore_index=True)
                st.success(f"통합 완료! 총 {len(final):,}행 데이터가 병합되었습니다.")
                csv = final.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button("📥 통합 파일 다운로드", csv, "merged_data_pro.csv", "text/csv")

    # --- Analysis Tab ---
    with tabs[4]:
        st.subheader("📈 심층 데이터 분석 (Insight Engine)")
        f_a = st.file_uploader("분석용 파일 업로드", type=['xlsx', 'csv', 'xls'], key="ana")
        if f_a:
            df_a = load_file_to_df(f_a)
            col_a = st.selectbox("분석 대상 컬럼", df_a.columns)
            
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("전체 데이터", f"{len(df_a):,}건")
            c2.metric("고유 값", f"{df_a[col_a].nunique():,}건")
            c3.metric("결측치", f"{df_a[col_a].isna().sum():,}건")
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.write("#### 📊 빈도수 분석 (TOP 15)")
            top15 = df_a[col_a].value_counts().head(15)
            st.bar_chart(top15)
            
            st.write("#### 📝 데이터 미리보기 (상위 100건)")
            st.dataframe(df_a.head(100))

if __name__ == "__main__":
    main()
