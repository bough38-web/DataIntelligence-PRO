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
    [data-testid="stSidebar"] { background-color: #0c111d; border-right: 1px solid #1f2937; }
    .premium-card {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        padding: 2rem;
        border-radius: 24px;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05);
        border: 1px solid #edf2f7;
        margin-bottom: 2rem;
    }
    .expert-badge {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        color: #1e40af;
        padding: 8px 16px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 700;
        border: 1px solid #bfdbfe;
    }
    .stButton>button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white;
        border: none;
        padding: 14px 28px;
        border-radius: 14px;
        font-weight: 700;
        width: 100%;
    }
    .utility-button>button {
        background: #f1f5f9;
        color: #475569;
        padding: 5px 10px;
        font-size: 0.8rem;
        border: 1px solid #e2e8f0;
        width: auto;
    }
    .hero-title {
        font-size: 3.5rem;
        font-weight: 900;
        background: linear-gradient(135deg, #111827 0%, #2563eb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
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
        st.divider()
        st.markdown("#### ⚙️ 시스템 상태")
        st.info("🚀 AI-Optimized Core Enabled")
        st.info("🛰 Cloud Data Sync Active")
        st.divider()
        st.caption("v2.5.5 | Enterprise Edition")

    st.markdown('<h1 class="hero-title">Data Intelligence PRO</h1>', unsafe_allow_html=True)
    st.markdown('<p style="font-size: 1.2rem; color: #64748b; margin-bottom: 2rem;">데이터 통합 및 정밀 가공을 위한 스마트 워크플로우</p>', unsafe_allow_html=True)
    
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
            <p style="color: #475569; font-size: 1.1rem;">직관적인 인터페이스로 복잡한 데이터 업무를 해결하세요.</p>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown("""
            #### 🌟 핵심 전문가 기법
            - **스마트 매칭**: 수만 건의 데이터를 지능적으로 결합
            - **정밀 추출**: 정규식 기반 패턴 필터링
            - **결측치 추론**: 상위 카테고리 기반 하위 데이터 자동 채움
            - **멀티 포맷 내보내기**: 엑셀(XLSX) 및 CSV 즉시 생성
            """)
        with c2:
            svg_code = """
            <div style="display: flex; justify-content: center;">
                <svg viewBox="0 0 500 400" xmlns="http://www.w3.org/2000/svg" style="width: 100%; max-width: 400px; height: auto; filter: drop-shadow(0 10px 15px rgba(0,0,0,0.1));">
                    <rect x="50" y="50" width="400" height="300" rx="20" fill="#f8fafc" stroke="#e2e8f0" stroke-width="2"/>
                    <circle cx="100" cy="90" r="10" fill="#ff5f56"/><circle cx="130" cy="90" r="10" fill="#ffbd2e"/><circle cx="160" cy="90" r="10" fill="#27c93f"/>
                    <rect x="80" y="140" width="340" height="20" rx="10" fill="#e2e8f0"/>
                    <rect x="80" y="180" width="280" height="20" rx="10" fill="#cbd5e1"/>
                    <rect x="80" y="220" width="310" height="20" rx="10" fill="#94a3b8"/>
                    <path d="M100 350 L100 250 L180 280 L260 220 L340 260 L420 180" stroke="#2563eb" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
                    <text x="250" y="380" text-anchor="middle" font-family="sans-serif" font-weight="800" fill="#2563eb" font-size="20">Intelligence Engine</text>
                </svg>
            </div>
            """
            st.components.v1.html(svg_code, height=400)

    # --- Smart Matching ---
    with tabs[1]:
        st.subheader("🔗 스마트 매칭 (Smart Matching)")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🟢 원본 (Base)")
            b_file = st.file_uploader("원본 파일", type=['xlsx', 'csv', 'xls'], key="b")
            if b_file:
                sheets = get_sheet_names(b_file)
                b_s = st.selectbox("시트", ["(기본)"] + sheets if sheets else ["(기본)"], key="bs")
                b_df = load_file_to_df(b_file, sheet_name=None if b_s == "(기본)" else b_s)
                b_key = st.selectbox("기준 컬럼 (Join Key)", b_df.columns, key="bk")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🟡 참조 (Reference)")
            r_file = st.file_uploader("참조 파일", type=['xlsx', 'csv', 'xls'], key="r")
            if r_file:
                sheets = get_sheet_names(r_file)
                r_s = st.selectbox("시트", ["(기본)"] + sheets if sheets else ["(기본)"], key="rs")
                r_df = load_file_to_df(r_file, sheet_name=None if r_s == "(기본)" else r_s)
                r_key = st.selectbox("매칭 컬럼 (Match Key)", r_df.columns, key="rk")
                
                # Select All Columns Feature
                all_cols = [c for c in r_df.columns if c != r_key]
                col_c1, col_c2 = st.columns([3, 1])
                with col_c2:
                    if st.button("전체 선택", key="sel_all_match"): st.session_state.match_cols = all_cols
                    if st.button("전체 해제", key="clear_all_match"): st.session_state.match_cols = []
                
                r_cols = st.multiselect("가져올 컬럼", all_cols, key="match_cols", default=st.session_state.get('match_cols', []))
            st.markdown('</div>', unsafe_allow_html=True)

        if b_file and r_file:
            st.markdown("#### ⚙️ 엔진 최적화")
            c1, c2, c3 = st.columns(3)
            do_norm = c1.checkbox("키 컬럼 정규화", value=True, help="공백 제거 및 대문자 변환")
            do_dedup = c2.checkbox("참조 중복 제거", value=True, help="매칭 시 발생하는 중복 행 방지")
            how_join = c3.selectbox("결합 방식", ["Left (원본유지)", "Inner (교집합)", "Outer (합집합)"])

            if st.button("🚀 매칭 실행"):
                with st.spinner("처리 중..."):
                    d1, d2 = b_df.copy(), r_df.copy()
                    if do_norm:
                        d1[b_key] = d1[b_key].astype(str).str.strip().str.upper()
                        d2[r_key] = d2[r_key].astype(str).str.strip().str.upper()
                    if do_dedup: d2 = d2.drop_duplicates(subset=[r_key])
                    how_map = {"Left (원본유지)": "left", "Inner (교집합)": "inner", "Outer (합집합)": "outer"}
                    res = pd.merge(d1, d2[[r_key] + r_cols], left_on=b_key, right_on=r_key, how=how_map[how_join])
                    st.success(f"매칭 성공! ({len(res):,}행)")
                    st.dataframe(res.head(50))
                    sc1, sc2 = st.columns(2)
                    sc1.download_button("📥 Excel 저장", convert_df_to_excel(res), "match_result.xlsx")
                    sc2.download_button("📥 CSV 저장", res.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), "match_result.csv")

    # --- Precision Extract ---
    with tabs[2]:
        st.subheader("📄 정밀 추출 (Precision Extract)")
        f_e = st.file_uploader("파일 업로드", type=['xlsx', 'csv', 'xls'], key="fe")
        if f_e:
            df_e = load_file_to_df(f_e)
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🔍 필터 및 컬럼 구성")
            c1, c2 = st.columns([2, 3])
            with c1:
                col_f = st.selectbox("필터 적용 대상", df_e.columns)
                mode_f = st.selectbox("필터 조건", ["일치", "포함", "정규식", "제외", "공백 아님"])
                val_f = st.text_input("검색 값")
            
            with c2:
                # Select All Columns Feature
                all_e_cols = list(df_e.columns)
                ec1, ec2 = st.columns([4, 1])
                with ec2:
                    if st.button("전체 선택", key="sel_all_ext"): st.session_state.ext_cols = all_e_cols
                    if st.button("전체 해제", key="clear_all_ext"): st.session_state.ext_cols = []
                cols_e = st.multiselect("출력 컬럼 선택", all_e_cols, key="ext_cols", default=st.session_state.get('ext_cols', all_e_cols))
            
            st.divider()
            st.markdown("##### ✨ 전문가 자동 보정")
            opt1, opt2, opt3 = st.columns(3)
            f_s = opt1.checkbox("AI 기반 결측치 채움", value=True)
            d_e = opt2.checkbox("중복 행 제거", value=True)
            s_e = opt3.checkbox("정렬 적용")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if st.button("📤 정밀 가공 실행"):
                res = df_e[cols_e].copy()
                if val_f or mode_f == "공백 아님":
                    vals = [v.strip() for v in val_f.split(",") if v.strip()]
                    if mode_f == "일치": res = res[res[col_f].astype(str).isin(vals)]
                    elif mode_f == "포함": res = res[res[col_f].astype(str).str.contains("|".join(vals), na=False)]
                    elif mode_f == "정규식": res = res[res[col_f].astype(str).str.contains(val_f, regex=True, na=False)]
                    elif mode_f == "제외": res = res[~res[col_f].astype(str).isin(vals)]
                    elif mode_f == "공백 아님": res = res[res[col_f].notna()]
                if f_s: res = fill_service_small_from_mid(res)
                if d_e: res = res.drop_duplicates()
                if s_e: res = res.sort_values(by=res.columns[0])
                st.success(f"가공 완료! ({len(res):,}행)")
                st.dataframe(res.head(50))
                st.download_button("📥 결과 저장 (Excel)", convert_df_to_excel(res), "extract_result.xlsx")

    # --- Smart Merge ---
    with tabs[3]:
        st.subheader("📂 스마트 병합 (Smart Merge)")
        files = st.file_uploader("병합할 모든 파일 선택", type=['xlsx', 'csv', 'xls'], accept_multiple_files=True)
        if files:
            st.markdown(f'<div class="expert-badge">활성 파일: {len(files)}개</div>', unsafe_allow_html=True)
            if st.button("🚀 통합 병합 실행"):
                frames = []
                bar = st.progress(0)
                for i, file in enumerate(files):
                    tmp = load_file_to_df(file)
                    frames.append(tmp)
                    bar.progress((i + 1) / len(files))
                final = pd.concat(frames, ignore_index=True)
                st.success(f"병합 완료! 총 {len(final):,}행 통합")
                st.download_button("📥 통합 결과 저장 (Excel)", convert_df_to_excel(final), "merged_all.xlsx")

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
                health_data.append({"컬럼명": col, "타입": str(df_a[col].dtype), "결측": f"{nulls} ({(nulls/len(df_a)*100):.1f}%)", "고유값": uniques})
            st.table(pd.DataFrame(health_data))
            st.markdown('</div>', unsafe_allow_html=True)
            col_a = st.selectbox("분석 대상 컬럼", df_a.columns)
            st.bar_chart(df_a[col_a].value_counts().head(20))

    # --- Transformation ---
    with tabs[5]:
        st.subheader("🛠 데이터 변환 (Transformation)")
        f_t = st.file_uploader("변환 대상 파일 업로드", type=['xlsx', 'csv', 'xls'], key="ft")
        if f_t:
            df_t = load_file_to_df(f_t)
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🔄 일괄 변환 설정")
            col_t = st.selectbox("변환 컬럼", df_t.columns, key="colt")
            action_t = st.selectbox("변환 작업", ["선택 안 함", "대문자로", "소문자로", "숫자만 추출", "날짜 형식 통일", "값 치환"])
            if action_t == "값 치환":
                find_v = st.text_input("기존 값")
                rep_v = st.text_input("새 값")
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button("🪄 변환 적용"):
                res = df_t.copy()
                if action_t == "대문자로": res[col_t] = res[col_t].astype(str).str.upper()
                elif action_t == "소문자로": res[col_t] = res[col_t].astype(str).str.lower()
                elif action_t == "숫자만 추출": res[col_t] = res[col_t].astype(str).str.extract('(\d+)').astype(float)
                elif action_t == "날짜 형식 통일": res[col_t] = pd.to_datetime(res[col_t], errors='coerce').dt.strftime('%Y-%m-%d')
                elif action_t == "값 치환": res[col_t] = res[col_t].replace(find_v, rep_v)
                st.success("변환 프로세스 완료!")
                st.dataframe(res.head(100))
                st.download_button("📥 결과 저장 (Excel)", convert_df_to_excel(res), "transformed.xlsx")

if __name__ == "__main__":
    main()
