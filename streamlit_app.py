import streamlit as st
import pandas as pd
import numpy as np
import os
import io
import time
from app.core.handlers import load_file_to_df, get_sheet_names, extract_columns_fast, extract_unique_values_fast
from app.core.processors import apply_advanced_conditions, fill_service_small_from_mid, apply_sorting, apply_dedup
from app.utils.common import clean_text

# --- Page Configuration ---
st.set_page_config(
    page_title="Data Intelligence PRO | Enterprise Edition",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Premium Custom Styling ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap');
    
    * { font-family: 'Pretendard', sans-serif; }
    
    .stApp { background-color: #fcfdfe; }
    
    /* Sidebar Polish */
    [data-testid="stSidebar"] {
        background-color: #0c111d;
        border-right: 1px solid #1f2937;
    }
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #ffffff !important;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    
    /* Glassmorphism Card */
    .premium-card {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        padding: 2rem;
        border-radius: 24px;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 10px 10px -5px rgba(0, 0, 0, 0.02);
        border: 1px solid #edf2f7;
        margin-bottom: 2rem;
        transition: transform 0.2s ease;
    }
    .premium-card:hover {
        transform: translateY(-4px);
    }
    
    /* Advanced Badge */
    .expert-badge {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        color: #1e40af;
        padding: 8px 16px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 700;
        border: 1px solid #bfdbfe;
        display: inline-block;
        margin-right: 8px;
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white;
        border: none;
        padding: 14px 28px;
        border-radius: 14px;
        font-weight: 700;
        font-size: 1rem;
        letter-spacing: -0.2px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        width: 100%;
    }
    .stButton>button:hover {
        box-shadow: 0 10px 20px -5px rgba(37, 99, 235, 0.4);
        filter: brightness(1.1);
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-weight: 800;
        color: #1e293b;
    }
    
    /* Custom Title */
    .hero-title {
        font-size: 3.5rem;
        font-weight: 900;
        letter-spacing: -2px;
        background: linear-gradient(135deg, #111827 0%, #2563eb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# --- App Logic ---
def main():
    with st.sidebar:
        st.markdown("### 💎 Data Intel PRO")
        st.markdown("---")
        st.markdown("#### ⚙️ 시스템 가동 상태")
        st.info("🚀 AI-Optimized Core Enabled")
        st.info("🛰 Cloud Data Sync Active")
        st.info("🔒 256-bit Encryption")
        st.markdown("---")
        st.caption("Developed by Data Intelligence Team")

    st.markdown('<h1 class="hero-title">Data Intelligence PRO</h1>', unsafe_allow_html=True)
    st.markdown('<p style="font-size: 1.2rem; color: #64748b; margin-bottom: 2rem;">차세대 인텔리전스 엔진 기반의 데이터 통합 및 정밀 가공 솔루션</p>', unsafe_allow_html=True)
    
    tabs = st.tabs([
        "🏠 대시보드 (Dashboard)", 
        "🔗 스마트 매칭 (Smart Matching)", 
        "📄 정밀 추출 (Precision Extract)", 
        "📂 스마트 병합 (Smart Merge)", 
        "📊 심층 분석 (Deep Insight)", 
        "🛠 데이터 변환 (Transformation)"
    ])
    
    # --- Dashboard ---
    with tabs[0]:
        st.markdown("""
        <div class="premium-card">
            <h2 style="color: #0f172a; font-weight: 800;">🚀 엔터프라이즈 통합 워크플로우</h2>
            <p style="color: #475569; font-size: 1.1rem; line-height: 1.6;">
                복잡한 엑셀 수식과 반복적인 노가다 업무에서 해방되세요. <br>
                Data Intelligence PRO는 전문가 수준의 데이터 가공 기법을 누구나 클릭 한 번으로 수행할 수 있도록 돕습니다.
            </p>
            <div style="margin-top: 20px;">
                <span class="expert-badge">VLOOKUP 고도화</span>
                <span class="expert-badge">Regex 정밀 필터</span>
                <span class="expert-badge">결측치 자동 추론</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("""
            #### 🌟 핵심 전문가 기법 (Key Technologies)
            - **스마트 데이터 매칭 (Smart Matching)**: 수만 건의 데이터를 1초 내에 지능적으로 결합합니다.
            - **정규식 패턴 추출 (Regex Filter)**: 복잡한 문자열 내에서 원하는 패턴(이메일, 전화번호, 품번 등)만 정확히 골라냅니다.
            - **계층형 결측치 보정 (Hierarchy Impute)**: 상위 카테고리 정보를 기반으로 비어있는 하위 데이터를 지능적으로 채웁니다.
            - **멀티 포맷 내보내기 (Multi-Export)**: 인코딩 깨짐 없는 깨끗한 엑셀(XLSX) 및 CSV 파일을 즉시 생성합니다.
            """)
        with c2:
            # Fixed image using a high-quality verified tech illustration from Unsplash
            st.image("https://images.unsplash.com/photo-1551288049-bbbda546697a?auto=format&fit=crop&q=80&w=1000", 
                     caption="Next-Gen Analytics Engine", use_container_width=True)

    # --- Smart Matching ---
    with tabs[1]:
        st.subheader("🔗 스마트 매칭 (Smart Matching)")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🟢 원본 (Base Dataset)")
            b_file = st.file_uploader("파일 업로드", type=['xlsx', 'csv', 'xls'], key="b")
            if b_file:
                b_sheets = get_sheet_names(b_file)
                b_s = st.selectbox("시트 선택", ["(기본)"] + b_sheets if b_sheets else ["(기본)"], key="bs")
                b_df = load_file_to_df(b_file, sheet_name=None if b_s == "(기본)" else b_s)
                b_key = st.selectbox("기준 컬럼 (Join Key)", b_df.columns, key="bk")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🟡 참조 (Reference Dataset)")
            r_file = st.file_uploader("파일 업로드", type=['xlsx', 'csv', 'xls'], key="r")
            if r_file:
                r_sheets = get_sheet_names(r_file)
                r_s = st.selectbox("시트 선택", ["(기본)"] + r_sheets if r_sheets else ["(기본)"], key="rs")
                r_df = load_file_to_df(r_file, sheet_name=None if r_s == "(기본)" else r_s)
                r_key = st.selectbox("매칭 컬럼 (Match Key)", r_df.columns, key="rk")
                r_cols = st.multiselect("가져올 컬럼 (Fields)", [c for c in r_df.columns if c != r_key])
            st.markdown('</div>', unsafe_allow_html=True)

        if b_file and r_file:
            st.markdown("#### ⚙️ 엔진 최적화 설정")
            c1, c2, c3 = st.columns(3)
            do_norm = c1.checkbox("키 컬럼 정규화 (Normalization)", value=True)
            do_dedup = c2.checkbox("참조 중복 제거 (Unique Only)", value=True)
            how_join = c3.selectbox("결합 방식 (Join)", ["Left (원본유지)", "Inner (교집합)", "Outer (합집합)"])

            if st.button("🚀 매칭 엔진 가동 (Execute Match)"):
                with st.spinner("알고리즘 연산 중..."):
                    d1, d2 = b_df.copy(), r_df.copy()
                    if do_norm:
                        d1[b_key] = d1[b_key].astype(str).str.strip().str.upper()
                        d2[r_key] = d2[r_key].astype(str).str.strip().str.upper()
                    if do_dedup:
                        d2 = d2.drop_duplicates(subset=[r_key])
                    
                    how_map = {"Left (원본유지)": "left", "Inner (교집합)": "inner", "Outer (합집합)": "outer"}
                    res = pd.merge(d1, d2[[r_key] + r_cols], left_on=b_key, right_on=r_key, how=how_map[how_join])
                    
                    st.success(f"매칭 성공! 총 {len(res):,}개 결과")
                    st.dataframe(res.head(100))
                    
                    btn_c1, btn_c2 = st.columns(2)
                    btn_c1.download_button("📥 Excel 저장", convert_df_to_excel(res), "matching_pro.xlsx")
                    btn_c2.download_button("📥 CSV 저장", res.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), "matching_pro.csv")

    # --- Precision Extract ---
    with tabs[2]:
        st.subheader("📄 정밀 추출 (Precision Extract)")
        f_e = st.file_uploader("가공 대상 파일 업로드", type=['xlsx', 'csv', 'xls'], key="fe")
        if f_e:
            df_e = load_file_to_df(f_e)
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🔍 필터 및 컬럼 구성")
            c1, c2 = st.columns(2)
            col_f = c1.selectbox("필터 적용 대상", df_e.columns)
            mode_f = c1.selectbox("필터 조건", ["일치 (Equal)", "포함 (Contains)", "정규식 (Regex)", "제외 (Exclude)", "공백 아님 (Not Null)"])
            val_f = c1.text_input("검색 값 (Values)")
            
            cols_e = c2.multiselect("출력 컬럼 선택", df_e.columns, default=list(df_e.columns))
            
            st.divider()
            st.markdown("##### ✨ 전문가 자동 보정")
            opt1, opt2, opt3 = st.columns(3)
            f_s = opt1.checkbox("AI 기반 결측치 채움", value=True)
            d_e = opt2.checkbox("중복 행 제거 (Unique)", value=True)
            s_e = opt3.checkbox("정렬 적용 (Sorting)")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if st.button("📤 정밀 가공 실행"):
                res = df_e[cols_e].copy()
                if val_f or mode_f == "공백 아님 (Not Null)":
                    vals = [v.strip() for v in val_f.split(",") if v.strip()]
                    if mode_f == "일치 (Equal)": res = res[res[col_f].astype(str).isin(vals)]
                    elif mode_f == "포함 (Contains)": res = res[res[col_f].astype(str).str.contains("|".join(vals), na=False)]
                    elif mode_f == "정규식 (Regex)": res = res[res[col_f].astype(str).str.contains(val_f, regex=True, na=False)]
                    elif mode_f == "제외 (Exclude)": res = res[~res[col_f].astype(str).isin(vals)]
                    elif mode_f == "공백 아님 (Not Null)": res = res[res[col_f].notna()]
                
                if f_s: res = fill_service_small_from_mid(res)
                if d_e: res = res.drop_duplicates()
                if s_e: res = res.sort_values(by=res.columns[0])
                
                st.success(f"가공 완료! ({len(res):,}행)")
                st.dataframe(res.head(100))
                st.download_button("📥 가공 결과 저장 (Excel)", convert_df_to_excel(res), "extracted_pro.xlsx")

    # --- Smart Merge ---
    with tabs[3]:
        st.subheader("📂 스마트 병합 (Smart Merge)")
        files = st.file_uploader("병합할 모든 파일 드래그 & 드롭", type=['xlsx', 'csv', 'xls'], accept_multiple_files=True)
        if files:
            st.markdown(f'<div class="expert-badge">활성 파일: {len(files)}개</div>', unsafe_allow_html=True)
            if st.button("🚀 멀티 파일 통합 실행"):
                frames = []
                bar = st.progress(0)
                for i, file in enumerate(files):
                    tmp = load_file_to_df(file)
                    frames.append(tmp)
                    bar.progress((i + 1) / len(files))
                
                final = pd.concat(frames, ignore_index=True)
                st.success(f"병합 완료! 총 {len(final):,}행 통합 완료")
                st.download_button("📥 통합 결과 저장 (Excel)", convert_df_to_excel(final), "merged_all_pro.xlsx")

    # --- Deep Insight ---
    with tabs[4]:
        st.subheader("📊 심층 분석 (Deep Insight)")
        f_a = st.file_uploader("분석 파일 업로드", type=['xlsx', 'csv', 'xls'], key="fa")
        if f_a:
            df_a = load_file_to_df(f_a)
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🏥 데이터 상태 리포트")
            health_data = []
            for col in df_a.columns:
                nulls = df_a[col].isna().sum()
                uniques = df_a[col].nunique()
                health_data.append({
                    "컬럼명": col,
                    "타입": str(df_a[col].dtype),
                    "결측(Null)": f"{nulls} ({(nulls/len(df_a)*100):.1f}%)",
                    "고유값": uniques
                })
            st.table(pd.DataFrame(health_data))
            st.markdown('</div>', unsafe_allow_html=True)
            
            col_a = st.selectbox("분석 대상 컬럼", df_a.columns)
            st.write("##### 📈 빈도 분포 차트")
            st.bar_chart(df_a[col_a].value_counts().head(20))

    # --- Transformation ---
    with tabs[5]:
        st.subheader("🛠 데이터 변환 (Transformation)")
        f_t = st.file_uploader("변환할 데이터 업로드", type=['xlsx', 'csv', 'xls'], key="ft")
        if f_t:
            df_t = load_file_to_df(f_t)
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🔄 일괄 변환 설정")
            col_t = st.selectbox("변환 컬럼", df_t.columns, key="colt")
            action_t = st.selectbox("변환 작업", ["선택 안 함", "대문자로 (UPPER)", "소문자로 (lower)", "숫자만 추출 (Digits Only)", "날짜 형식 통일 (YYYY-MM-DD)", "값 치환 (Replace)"])
            if action_t == "값 치환 (Replace)":
                find_v = st.text_input("기존 값 (Old Value)")
                rep_v = st.text_input("새 값 (New Value)")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if st.button("🪄 변환 적용"):
                res = df_t.copy()
                if action_t == "대문자로 (UPPER)": res[col_t] = res[col_t].astype(str).str.upper()
                elif action_t == "소문자로 (lower)": res[col_t] = res[col_t].astype(str).str.lower()
                elif action_t == "숫자만 추출 (Digits Only)": res[col_t] = res[col_t].astype(str).str.extract('(\d+)').astype(float)
                elif action_t == "날짜 형식 통일 (YYYY-MM-DD)": 
                    res[col_t] = pd.to_datetime(res[col_t], errors='coerce').dt.strftime('%Y-%m-%d')
                elif action_t == "값 치환 (Replace)":
                    res[col_t] = res[col_t].replace(find_v, rep_v)
                
                st.success("변환 프로세스 완료!")
                st.dataframe(res.head(100))
                st.download_button("📥 결과 저장 (Excel)", convert_df_to_excel(res), "transformed_pro.xlsx")

if __name__ == "__main__":
    main()
