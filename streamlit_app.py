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
    page_title="Data Intelligence PRO | Enterprise",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Pretendard', sans-serif;
    }
    
    .main { background-color: #f8fafc; }
    
    [data-testid="stSidebar"] {
        background-image: linear-gradient(#0f172a, #1e293b);
        color: white;
    }
    [data-testid="stSidebar"] * { color: white !important; }
    
    .premium-card {
        background: white;
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05);
        border: 1px solid #f1f5f9;
        margin-bottom: 1.2rem;
    }
    
    .expert-badge {
        background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
        color: #166534;
        padding: 6px 14px;
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stButton>button {
        background: linear-gradient(90deg, #2563eb, #4f46e5);
        color: white;
        border: none;
        padding: 12px 28px;
        border-radius: 10px;
        font-weight: 600;
        width: 100%;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
    }
    
    .hero-text {
        background: linear-gradient(90deg, #0f172a, #2563eb);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        font-weight: 800;
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
        st.markdown("### 💎 Enterprise Core")
        st.caption("AI-Powered Data Engine")
        st.divider()
        
        st.markdown("#### 🛠 도구 상태 (Tools Status)")
        st.success("✨ 고속 파싱 모드 활성 (Fast Parsing)")
        st.success("✨ 메모리 최적화 (Memory Opt)")
        st.success("✨ 지능형 인코딩 (Smart Encoding)")
        
        st.divider()
        st.info("💡 **PRO Tip**: 여러 파일을 한 번에 처리하려면 '스마트 병합' 탭을 이용하세요.")

    st.markdown('<h1 class="hero-text">Data Intelligence PRO</h1>', unsafe_allow_html=True)
    
    # Updated Tab Names to Korean (English)
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
            <h3>🚀 엔터프라이즈 데이터 워크플로우 (Enterprise Workflow)</h3>
            <p>직장인과 전문가를 위한 고성능 데이터 가공 솔루션입니다. 복잡한 엑셀 수식 없이 클릭만으로 정밀한 결과를 도출하세요.</p>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown("""
            #### 🌟 핵심 전문가 기능 (Core Expert Features)
            - **스마트 매칭 (VLOOKUP Pro)**: 대량 데이터 지능형 결합 및 자동 정규화
            - **정밀 추출 (Regex Filter)**: 패턴 인식 기반 데이터 필터링 및 가공
            - **결측치 추론 (AI Impute)**: 상위 카테고리 기반 하위 데이터 자동 채움
            - **스마트 인코딩 (Auto Encoding)**: 한글 깨짐 방지 및 다국어 인코딩 감지
            """)
        with c2:
            # Fixed image using a more reliable source
            st.image("https://images.unsplash.com/photo-1551288049-bbbda546697a?q=80&w=500&auto=format&fit=crop", caption="Data Intelligence Engine")

    # --- Smart Matching ---
    with tabs[1]:
        st.subheader("🔗 스마트 매칭 (Smart Matching)")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 🟢 원본 데이터 (Target)")
            b_file = st.file_uploader("원본 파일 업로드", type=['xlsx', 'csv', 'xls'], key="b")
            if b_file:
                b_sheets = get_sheet_names(b_file)
                b_s = st.selectbox("시트 선택", ["(기본)"] + b_sheets if b_sheets else ["(기본)"], key="bs")
                b_df = load_file_to_df(b_file, sheet_name=None if b_s == "(기본)" else b_s)
                b_key = st.selectbox("기준 컬럼 (Key Column)", b_df.columns, key="bk")
        
        with col2:
            st.markdown("##### 🟡 참조 데이터 (Reference)")
            r_file = st.file_uploader("참조 파일 업로드", type=['xlsx', 'csv', 'xls'], key="r")
            if r_file:
                r_sheets = get_sheet_names(r_file)
                r_s = st.selectbox("시트 선택", ["(기본)"] + r_sheets if r_sheets else ["(기본)"], key="rs")
                r_df = load_file_to_df(r_file, sheet_name=None if r_s == "(기본)" else r_s)
                r_key = st.selectbox("매칭 컬럼 (Match Column)", r_df.columns, key="rk")
                r_cols = st.multiselect("가져올 데이터 컬럼", [c for c in r_df.columns if c != r_key])

        if b_file and r_file:
            exp = st.expander("⚙️ 고급 매칭 설정 (Advanced Settings)", expanded=True)
            with exp:
                c1, c2, c3 = st.columns(3)
                do_norm = c1.checkbox("데이터 정규화 (Normalization)", value=True)
                do_dedup = c2.checkbox("중복 제거 (Deduplication)", value=True)
                how_join = c3.selectbox("병합 방식 (Join Type)", ["Left (원본유지)", "Inner (교집합)", "Outer (합집합)"])

            if st.button("🚀 매칭 실행 (Run Engine)"):
                with st.spinner("처리 중..."):
                    d1, d2 = b_df.copy(), r_df.copy()
                    if do_norm:
                        d1[b_key] = d1[b_key].astype(str).str.strip().str.upper()
                        d2[r_key] = d2[r_key].astype(str).str.strip().str.upper()
                    if do_dedup:
                        d2 = d2.drop_duplicates(subset=[r_key])
                    
                    how_map = {"Left (원본유지)": "left", "Inner (교집합)": "inner", "Outer (합집합)": "outer"}
                    res = pd.merge(d1, d2[[r_key] + r_cols], left_on=b_key, right_on=r_key, how=how_map[how_join])
                    
                    st.success(f"매칭 완료! ({len(res):,}행)")
                    st.dataframe(res.head(100))
                    
                    c1, c2 = st.columns(2)
                    c1.download_button("📥 Excel 저장 (Save Excel)", convert_df_to_excel(res), "matching_result.xlsx")
                    c2.download_button("📥 CSV 저장 (Save CSV)", res.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), "matching_result.csv")

    # --- Precision Extract ---
    with tabs[2]:
        st.subheader("📄 정밀 추출 (Precision Extract)")
        f_e = st.file_uploader("가공할 파일 업로드", type=['xlsx', 'csv', 'xls'], key="fe")
        if f_e:
            df_e = load_file_to_df(f_e)
            
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🔍 지능형 필터 설정 (Smart Filter)")
            col_f = st.selectbox("필터 적용 대상", df_e.columns)
            mode_f = st.selectbox("필터 조건", ["일치 (Equal)", "포함 (Contains)", "정규식 (Regex)", "제외 (Exclude)", "공백 아님 (Not Null)"])
            val_f = st.text_input("검색어 (Values) - 콤마로 다중 입력 가능")
            
            cols_e = st.multiselect("출력 컬럼 구성 (Select Columns)", df_e.columns, default=list(df_e.columns))
            
            st.markdown("##### ✨ 전문가 자동 보정")
            c1, c2, c3 = st.columns(3)
            f_s = c1.checkbox("카테고리 자동 추론 (AI Impute)", value=True)
            d_e = c2.checkbox("중복 행 제거 (Dedup)", value=True)
            s_e = c3.checkbox("정렬 (Sort)")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if st.button("📤 데이터 정밀 가공 시작"):
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
                
                st.success(f"추출 완료! ({len(res):,}행)")
                st.dataframe(res.head(100))
                st.download_button("📥 가공 결과 저장 (Excel)", convert_df_to_excel(res), "extracted_result.xlsx")

    # --- Smart Merge ---
    with tabs[3]:
        st.subheader("📂 스마트 병합 (Smart Merge)")
        files = st.file_uploader("병합할 모든 파일 선택", type=['xlsx', 'csv', 'xls'], accept_multiple_files=True)
        if files:
            st.markdown(f'<div class="expert-badge">대기 중인 파일: {len(files)}개</div>', unsafe_allow_html=True)
            if st.button("🚀 통합 병합 실행"):
                frames = []
                bar = st.progress(0)
                for i, file in enumerate(files):
                    tmp = load_file_to_df(file)
                    frames.append(tmp)
                    bar.progress((i + 1) / len(files))
                
                final = pd.concat(frames, ignore_index=True)
                st.success(f"병합 완료! 총 {len(final):,}행 통합")
                st.download_button("📥 통합 파일 저장 (Excel)", convert_df_to_excel(final), "merged_all.xlsx")

    # --- Deep Insight ---
    with tabs[4]:
        st.subheader("📊 심층 분석 (Deep Insight)")
        f_a = st.file_uploader("분석 대상 파일 업로드", type=['xlsx', 'csv', 'xls'], key="fa")
        if f_a:
            df_a = load_file_to_df(f_a)
            st.markdown("#### 🏥 데이터 상태 요약 (Health Summary)")
            health_data = []
            for col in df_a.columns:
                nulls = df_a[col].isna().sum()
                uniques = df_a[col].nunique()
                health_data.append({
                    "컬럼명": col,
                    "데이터 타입": str(df_a[col].dtype),
                    "결측치(Null)": f"{nulls} ({(nulls/len(df_a)*100):.1f}%)",
                    "고유값 수": uniques
                })
            st.table(pd.DataFrame(health_data))
            
            col_a = st.selectbox("상세 빈도 분석 컬럼", df_a.columns)
            st.write("##### 📈 분포 차트 (Top 15 Distribution)")
            st.bar_chart(df_a[col_a].value_counts().head(15))

    # --- Transformation ---
    with tabs[5]:
        st.subheader("🛠 데이터 변환 (Transformation)")
        f_t = st.file_uploader("변환 대상 파일 업로드", type=['xlsx', 'csv', 'xls'], key="ft")
        if f_t:
            df_t = load_file_to_df(f_t)
            with st.expander("🔄 일괄 변환 설정", expanded=True):
                col_t = st.selectbox("대상 컬럼 선택", df_t.columns, key="colt")
                action_t = st.selectbox("수행 작업", ["선택 안 함", "대문자로 (UPPER)", "소문자로 (lower)", "숫자만 추출 (Numbers Only)", "날짜 형식 통일 (YYYY-MM-DD)", "값 치환 (Replace)"])
                if action_t == "값 치환 (Replace)":
                    find_v = st.text_input("찾을 값 (Old)")
                    rep_v = st.text_input("바꿀 값 (New)")
            
            if st.button("🪄 변환 마법 적용"):
                res = df_t.copy()
                if action_t == "대문자로 (UPPER)": res[col_t] = res[col_t].astype(str).str.upper()
                elif action_t == "소문자로 (lower)": res[col_t] = res[col_t].astype(str).str.lower()
                elif action_t == "숫자만 추출 (Numbers Only)": res[col_t] = res[col_t].astype(str).str.extract('(\d+)').astype(float)
                elif action_t == "날짜 형식 통일 (YYYY-MM-DD)": 
                    res[col_t] = pd.to_datetime(res[col_t], errors='coerce').dt.strftime('%Y-%m-%d')
                elif action_t == "값 치환 (Replace)":
                    res[col_t] = res[col_t].replace(find_v, rep_v)
                
                st.success("변환 성공!")
                st.dataframe(res.head(100))
                st.download_button("📥 변환 결과 저장 (Excel)", convert_df_to_excel(res), "transformed_result.xlsx")

if __name__ == "__main__":
    main()
