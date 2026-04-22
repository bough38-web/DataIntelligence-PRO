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
PRESETS_FILE = AUTH_DIR / "presets.json"

# --- JSON Helpers ---
def load_json(path, default):
    if not path.exists(): return default
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

# --- Page Config ---
st.set_page_config(page_title="Data Intel PRO | Expert", page_icon="💎", layout="wide")

# --- Session State ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_role' not in st.session_state: st.session_state.user_role = "user"
if 'current_user' not in st.session_state: st.session_state.current_user = None

# --- Custom Premium Style ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800;900&display=swap');
    * { font-family: 'Pretendard', sans-serif; }
    .stApp { background-color: #f8fafc; }
    .guide-box { background-color: #f1f5f9; padding: 20px; border-radius: 15px; border-left: 5px solid #2563eb; margin-bottom: 20px; }
    .health-score { font-size: 2.5rem; font-weight: 800; color: #16a34a; }
    .premium-card { background: white; padding: 25px; border-radius: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- Logic Modules ---

def get_health_score(df):
    if df is None: return 0
    total_cells = df.size
    null_cells = df.isnull().sum().sum()
    score = 100 - (null_cells / total_cells * 100) if total_cells > 0 else 0
    return round(score, 1)

def fuzzy_match(key, targets, threshold=0.6):
    matches = difflib.get_close_matches(str(key), [str(t) for t in targets], n=1, cutoff=threshold)
    return matches[0] if matches else None

def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# --- UI Sections ---

def show_landing():
    st.markdown("<h1 style='text-align: center; font-size: 4rem; font-weight: 900; background: linear-gradient(135deg, #0f172a, #2563eb); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>Data Intelligence PRO</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="premium-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>Security Login</h3>", unsafe_allow_html=True)
        pwd = st.text_input("Enter Password (0303)", type="password")
        if st.button("🚀 Start Engine"):
            settings = load_json(SETTINGS_FILE, {"master_password": "0303"})
            if pwd == settings["master_password"]:
                st.session_state.authenticated = True
                st.session_state.user_role = "admin"
                st.rerun()
            else: st.error("Invalid Password.")
        st.markdown('</div>', unsafe_allow_html=True)

def show_main():
    with st.sidebar:
        st.title("💎 Data Intel PRO")
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.rerun()
        st.divider()
        st.markdown("#### ⚡️ Expert Mode Active")

    app_tabs = ["🔗 매칭 (Match)", "📄 추출 (Extract)", "📊 분석 (Insight)", "📂 병합 (Merge)", "⚙️ 설정 (Admin)"]
    tabs = st.tabs(app_tabs)

    # --- 1. Matching (Fuzzy + Guide) ---
    with tabs[0]:
        with st.expander("❓ [초보자 가이드] 스마트 매칭 사용법", expanded=False):
            st.markdown("""
            1. **원본 파일**을 업로드하세요 (예: 판매 내역).
            2. **참조 파일**을 업로드하세요 (예: 단가표).
            3. 두 파일에서 **공통된 이름**(품번, 이름 등)을 선택하세요.
            4. `유사도 매칭`을 켜면 오타가 있어도 자동으로 찾아줍니다!
            """)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            b_f = st.file_uploader("원본 파일 업로드", key="match_b")
            if b_f:
                b_df = load_file_to_df(b_f)
                b_k = st.selectbox("원본 기준 키", b_df.columns)
                st.metric("데이터 상태", f"{get_health_score(b_df)}점")
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            r_f = st.file_uploader("참조 파일 업로드", key="match_r")
            if r_f:
                r_df = load_file_to_df(r_f)
                r_k = st.selectbox("참조 매칭 키", r_df.columns)
                r_cols = st.multiselect("가져올 컬럼", [c for c in r_df.columns if c != r_k])
            st.markdown('</div>', unsafe_allow_html=True)

        if b_f and r_f:
            st.markdown("#### ⚙️ 지능형 옵션")
            col_opt1, col_opt2 = st.columns(2)
            use_fuzzy = col_opt1.checkbox("지능형 유사도 매칭 (Fuzzy Match)", help="오타가 있어도 유사한 값을 찾습니다.")
            do_norm = col_opt2.checkbox("키 정규화 (대문자/공백제거)", value=True)

            if st.button("🚀 데이터 매칭 실행"):
                with st.spinner("전문가 엔진 가동 중..."):
                    d1, d2 = b_df.copy(), r_df.copy()
                    if use_fuzzy:
                        st.info("유사도 계산 중... 시간이 조금 더 걸릴 수 있습니다.")
                        targets = d2[r_k].unique()
                        d1[b_k] = d1[b_k].apply(lambda x: fuzzy_match(x, targets) or x)
                    elif do_norm:
                        d1[b_k] = d1[b_k].astype(str).str.strip().str.upper()
                        d2[r_k] = d2[r_k].astype(str).str.strip().str.upper()
                    
                    res = pd.merge(d1, d2[[r_k] + r_cols], left_on=b_k, right_on=r_k, how='left')
                    st.success("매칭 완료!")
                    st.dataframe(res.head(50))
                    st.download_button("📥 결과 다운로드 (Excel)", convert_df_to_excel(res), "matched.xlsx")

    # --- 2. Extract (Presets + Guide) ---
    with tabs[1]:
        with st.expander("❓ [초보자 가이드] 정밀 추출 사용법", expanded=False):
            st.markdown("""
            1. 가공할 파일을 올리고 **필터링할 컬럼**을 고르세요.
            2. 검색어에 원하는 단어를 넣으세요 (여러 개는 콤마로 구분).
            3. `AI 결측치 채움`을 켜면 비어있는 카테고리를 자동으로 채워줍니다.
            """)
        
        e_f = st.file_uploader("가공 대상 파일 업로드", key="ext_f")
        if e_f:
            e_df = load_file_to_df(e_f)
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            ec1, ec2 = st.columns([1, 2])
            col_f = ec1.selectbox("필터 컬럼", e_df.columns)
            val_f = ec1.text_input("검색 값 (콤마로 구분)")
            
            all_cols = list(e_df.columns)
            sel_cols = ec2.multiselect("출력 컬럼", all_cols, default=all_cols)
            
            st.markdown("##### ✨ 전문가 옵션")
            oc1, oc2, oc3 = st.columns(3)
            do_ai = oc1.checkbox("AI 결측치 자동 채움", value=True)
            do_dedup = oc2.checkbox("중복 행 제거", value=True)
            
            if st.button("📤 추출 및 보정 실행"):
                res = e_df[sel_cols].copy()
                if val_f:
                    vals = [v.strip() for v in val_f.split(",")]
                    res = res[res[col_f].astype(str).str.contains("|".join(vals), na=False)]
                if do_ai: res = fill_service_small_from_mid(res)
                if do_dedup: res = res.drop_duplicates()
                st.success("가공 완료!")
                st.dataframe(res.head(50))
                st.download_button("📥 가공 결과 저장", convert_df_to_excel(res), "extracted.xlsx")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- 3. Insight (Health + Pivot + Guide) ---
    with tabs[2]:
        with st.expander("❓ [초보자 가이드] 분석 및 리포트 사용법", expanded=False):
            st.markdown("""
            1. 파일을 올리면 자동으로 **데이터 건강 점수**가 계산됩니다.
            2. 아래 `자동 리포트` 섹션에서 데이터 요약 표를 확인하세요.
            """)
        
        a_f = st.file_uploader("분석용 파일 업로드", key="ans_f")
        if a_f:
            a_df = load_file_to_df(a_f)
            score = get_health_score(a_df)
            st.markdown(f"### 🏥 데이터 건강 점수: <span class='health-score'>{score}점</span>", unsafe_allow_html=True)
            
            st.divider()
            st.subheader("📋 자동 요약 리포트 (Auto Pivot)")
            c1, c2 = st.columns(2)
            p_idx = c1.selectbox("기준 행 (Group By)", a_df.columns)
            p_val = c2.selectbox("수치 컬럼 (Value)", a_df.columns)
            pivot = a_df.groupby(p_idx)[p_val].count().reset_index()
            st.table(pivot.head(10))
            st.bar_chart(a_df[p_idx].value_counts().head(10))

    # --- 4. Merge ---
    with tabs[3]:
        m_fs = st.file_uploader("병합할 파일들을 선택 (멀티 선택)", accept_multiple_files=True)
        if m_fs:
            if st.button("🚀 통합 파일 생성"):
                dfs = [load_file_to_df(f) for f in m_fs]
                final = pd.concat(dfs, ignore_index=True)
                st.success(f"{len(m_fs)}개 파일 병합 완료!")
                st.download_button("📥 통합 결과 다운로드", convert_df_to_excel(final), "merged.xlsx")

    # --- 5. Admin ---
    with tabs[4]:
        st.subheader("🔑 시스템 관리")
        users = load_json(USERS_FILE, [])
        with st.form("reg"):
            st.markdown("##### 라이선스 발급")
            c1, c2 = st.columns(2)
            n = c1.text_input("이름")
            l = c2.text_input("라이선스 키")
            if st.form_submit_button("등록"):
                users.append({"name":n, "license":l, "expiry":(datetime.now()+timedelta(days=365)).strftime("%Y-%m-%d")})
                save_json(USERS_FILE, users)
                st.success("등록 완료")
        st.dataframe(pd.DataFrame(users))

# --- Main Entry ---
def main():
    if not st.session_state.authenticated: show_landing()
    else: show_main()

if __name__ == "__main__": main()
