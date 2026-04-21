import streamlit as st
import pandas as pd
import os
import io
from app.core.handlers import load_file_to_df, get_sheet_names, extract_columns_fast, extract_unique_values_fast
from app.core.processors import apply_advanced_conditions, fill_service_small_from_mid, apply_sorting, apply_dedup
from app.utils.common import clean_text

# --- Page Configuration ---
st.set_page_config(
    page_title="Data Intelligence PRO - Web",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling ---
st.markdown("""
    <style>
    .main {
        background-color: #f4f8fb;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        background-color: #2563eb;
        color: white;
        font-weight: bold;
    }
    .expert-card {
        background-color: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        color: #1e40af;
    }
    </style>
    """, unsafe_allow_html=True)

# --- App Logic ---

def main():
    st.title("🚀 Data Intelligence PRO")
    st.sidebar.title("Menu")
    
    tabs = st.tabs(["🏠 홈", "🔗 데이터 매칭", "📄 단일 파일 추출", "📂 병합", "📈 데이터 분석"])
    
    # --- Home Tab ---
    with tabs[0]:
        st.header("최첨단 알고리즘 기반 데이터 통합 솔루션")
        st.info("웹 브라우저에서 편리하게 데이터를 매칭하고 정밀하게 추출하세요.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("주요 기능")
            st.markdown("""
            - **🔗 데이터 매칭**: 두 데이터를 키 기준으로 병합 (VLOOKUP)
            - **📄 단일 파일 추출**: 필터링, 정렬, 중복제거를 포함한 정밀 추출
            - **📂 병합**: 동일 규격의 여러 파일을 하나의 통합본으로 결합
            - **📈 데이터 분석**: 데이터 분포, 빈도, 통계 자동 리포팅
            """)
        
        with col2:
            st.markdown('<div class="expert-card"><b>🚀 전문가 기법 TOP 10</b><br><br>'
                        '• 키 컬럼 정규화 및 데이터 타입 강제 변환<br>'
                        '• 참조 데이터 중복 제거 (VLOOKUP 최적화)<br>'
                        '• 정규식(Regex) 활용 패턴 기반 정밀 추출<br>'
                        '• 서비스(소) 결측치 자동 추론 채움 기술<br>'
                        '• 고유값 빈도 분석 및 데이터 품질 검증</div>', unsafe_allow_html=True)

    # --- Matching Tab ---
    with tabs[1]:
        st.header("🔗 데이터 매칭 (VLOOKUP)")
        c1, c2 = st.columns(2)
        
        with c1:
            base_file = st.file_uploader("1. 원본 데이터 선택", type=['csv', 'xlsx', 'xls'])
            if base_file:
                sheets = get_sheet_names(base_file)
                base_sheet = st.selectbox("원본 시트", ["(기본)"] + sheets if sheets else ["(기본)"])
                base_df = load_file_to_df(base_file, sheet_name=None if base_sheet == "(기본)" else base_sheet)
                base_key = st.selectbox("원본 기준 컬럼(Key)", base_df.columns)
        
        with c2:
            ref_file = st.file_uploader("2. 참조 데이터 선택", type=['csv', 'xlsx', 'xls'])
            if ref_file:
                sheets = get_sheet_names(ref_file)
                ref_sheet = st.selectbox("참조 시트", ["(기본)"] + sheets if sheets else ["(기본)"])
                ref_df = load_file_to_df(ref_file, sheet_name=None if ref_sheet == "(기본)" else ref_sheet)
                ref_key = st.selectbox("참조 기준 컬럼(Key)", ref_df.columns)
                ref_cols = st.multiselect("가져올 참조 컬럼 선택", [c for c in ref_df.columns if c != ref_key])
        
        if base_file and ref_file:
            if st.button("🚀 매칭 실행"):
                with st.spinner("처리 중..."):
                    # Normalization
                    base_df[base_key] = base_df[base_key].astype(str).str.strip()
                    ref_df[ref_key] = ref_df[ref_key].astype(str).str.strip()
                    
                    # Deduplicate Ref
                    ref_subset = ref_df[[ref_key] + ref_cols].drop_duplicates(subset=[ref_key])
                    
                    # Join
                    result = pd.merge(base_df, ref_subset, left_on=base_key, right_on=ref_key, how='left')
                    if base_key != ref_key:
                        result.drop(columns=[ref_key], inplace=True)
                    
                    st.success(f"매칭 완료! 총 {len(result):,}행")
                    st.dataframe(result.head(100))
                    
                    csv = result.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                    st.download_button("📥 결과 다운로드 (CSV)", csv, "matching_result.csv", "text/csv")

    # --- Single Extraction Tab ---
    with tabs[2]:
        st.header("📄 단일 파일 추출")
        f = st.file_uploader("추출할 파일 업로드", type=['csv', 'xlsx', 'xls'])
        if f:
            sheets = get_sheet_names(f)
            sheet = st.selectbox("시트 선택", ["(기본)"] + sheets if sheets else ["(기본)"], key="single_sheet")
            df = load_file_to_df(f, sheet_name=None if sheet == "(기본)" else sheet)
            
            col_sel = st.multiselect("출력 컬럼 선택", df.columns, default=list(df.columns))
            
            st.divider()
            st.subheader("🚀 전문가 옵션")
            fill_svc = st.checkbox("서비스(소) 자동 채움", value=True)
            
            if st.button("📤 추출 및 다운로드"):
                processed = df[col_sel].copy()
                if fill_svc:
                    processed = fill_service_small_from_mid(processed)
                
                csv = processed.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button("📥 추출 결과 다운로드", csv, "extract_result.csv", "text/csv")
                st.dataframe(processed.head(100))

    # --- Merge Tab ---
    with tabs[3]:
        st.header("📂 여러 파일 병합")
        files = st.file_uploader("병합할 파일들 업로드 (다중 선택 가능)", type=['csv', 'xlsx', 'xls'], accept_multiple_files=True)
        if files:
            st.write(f"업로드된 파일: {len(files)}개")
            if st.button("🚀 병합 실행"):
                frames = []
                progress = st.progress(0)
                for i, file in enumerate(files):
                    df = load_file_to_df(file)
                    frames.append(df)
                    progress.progress((i + 1) / len(files))
                
                final_df = pd.concat(frames, ignore_index=True)
                st.success(f"병합 완료! 총 {len(final_df):,}행")
                csv = final_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button("📥 병합 결과 다운로드", csv, "merged_result.csv", "text/csv")

    # --- Analysis Tab ---
    with tabs[4]:
        st.header("📈 데이터 분석")
        f_ana = st.file_uploader("분석할 파일 업로드", type=['csv', 'xlsx', 'xls'], key="ana_file")
        if f_ana:
            df_ana = load_file_to_df(f_ana)
            st.write(f"전체 데이터 수: {len(df_ana):,}행")
            
            col_ana = st.selectbox("분석할 컬럼 선택", df_ana.columns)
            if col_ana:
                stats_col1, stats_col2 = st.columns(2)
                with stats_col1:
                    st.write("### 기본 통계")
                    st.write(f"- 고유값 수: {df_ana[col_ana].nunique():,}개")
                    st.write(f"- 결측치 수: {df_ana[col_ana].isna().sum():,}개")
                
                with stats_col2:
                    st.write("### 빈도 분석 (TOP 10)")
                    freq = df_ana[col_ana].value_counts().head(10)
                    st.bar_chart(freq)

if __name__ == "__main__":
    main()
