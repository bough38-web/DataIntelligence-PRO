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
LOGS_FILE = AUTH_DIR / "logs.json"

def load_json(path, default):
    if not path.exists(): return default
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

def add_log(user_name, action):
    logs = load_json(LOGS_FILE, [])
    logs.append({"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "user": user_name, "action": action})
    save_json(LOGS_FILE, logs[-1000:])

# --- Page Config ---
st.set_page_config(page_title="Data Intel PRO | Enterprise", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

# --- Session State ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_role' not in st.session_state: st.session_state.user_role = "user"
if 'current_user' not in st.session_state: st.session_state.current_user = None

# --- Custom Master Style ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&family=Pretendard:wght@400;600;700;800&display=swap');
    * { font-family: 'Pretendard', sans-serif; }
    .stApp { background: linear-gradient(135deg, #f8fafc 0%, #ffffff 50%, #f1f5f9 100%); color: #1e293b; }
    .hero-title {
        font-family: 'Outfit', sans-serif; font-size: 4.8rem; font-weight: 900; text-align: center;
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
        margin-top: 80px; margin-bottom: 5px; letter-spacing: -2px;
    }
    .hero-subtitle { text-align: center; color: #64748b; font-size: 1.5rem; font-weight: 500; margin-bottom: 60px; }
    .login-card {
        background: white; border: 1px solid #e2e8f0; border-radius: 40px;
        padding: 60px 50px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.05);
        max-width: 550px; margin: 0 auto; display: flex; flex-direction: column; align-items: center;
    }
    .premium-card {
        background: white; padding: 25px; border-radius: 24px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #f1f5f9; margin-bottom: 20px;
    }
    .badge { padding: 4px 12px; border-radius: 100px; font-size: 0.75rem; font-weight: 700; }
    .badge-req { background: #fee2e2; color: #ef4444; }
    .badge-active { background: #dcfce7; color: #16a34a; }
    
    .stButton>button {
        background: #2563eb !important; color: white !important; font-weight: 800 !important;
        border-radius: 16px !important; padding: 16px !important; width: 100% !important; border: none !important;
    }
    .stTextInput>div>div>input { border-radius: 16px !important; border: 1px solid #cbd5e1 !important; text-align: center; padding: 15px !important; }
    .copyright { position: fixed; bottom: 20px; right: 30px; color: #cbd5e1; font-size: 0.85rem; font-family: 'Outfit', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# --- Business Logic ---

def fuzzy_match_logic(key, targets, threshold=0.6):
    matches = difflib.get_close_matches(str(key), [str(t) for t in targets], n=1, cutoff=threshold)
    return matches[0] if matches else None

def get_health_score(df):
    if df is None or df.empty: return 0
    total = df.size
    nulls = df.isnull().sum().sum()
    return round(100 - (nulls / total * 100), 1) if total > 0 else 0

def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- Auth UI ---

def show_landing():
    st.markdown("<h1 class='hero-title'>DATA INTEL PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p class='hero-subtitle'>Smart Data Workflows for Enterprise Teams</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #0f172a; margin-bottom: 40px; font-weight: 800;'>보안 인증 로그인</h2>", unsafe_allow_html=True)
        
        mode = st.radio("", ["마스터 어드민", "라이선스 사용자"], horizontal=True, label_visibility="collapsed")
        
        settings = load_json(SETTINGS_FILE, {"master_password": "0303"})
        users = load_json(USERS_FILE, [])
        
        if mode == "마스터 어드민":
            pwd = st.text_input("PASSWORD", type="password", placeholder="Master Password", label_visibility="collapsed")
            if st.button("🚀 어드민 접속"):
                if pwd == settings["master_password"]:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "admin"
                    add_log("ADMIN", "Admin Login Success")
                    st.rerun()
                else: st.error("접속 정보가 일치하지 않습니다.")
        else:
            lic = st.text_input("LICENSE KEY", type="password", placeholder="Your Private Key", label_visibility="collapsed")
            if st.button("🚀 라이선스 인증"):
                user = next((u for u in users if u["license"] == lic), None)
                if user:
                    expiry = datetime.strptime(user["expiry"], "%Y-%m-%d")
                    if expiry < datetime.now():
                        st.error(f"만료된 라이선스입니다. (만료일: {user['expiry']})")
                        if st.button("🆘 연장 요청하기"):
                            for u in users:
                                if u["license"] == lic: u["req_ext"] = True
                            save_json(USERS_FILE, users)
                            st.success("연장 요청이 전송되었습니다. 관리자가 확인 후 연장해 드립니다.")
                    else:
                        st.session_state.authenticated = True
                        st.session_state.user_role = "user"
                        st.session_state.current_user = user
                        add_log(user["name"], "User Login Success")
                        st.rerun()
                else: st.error("유효하지 않은 라이선스 키입니다.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="copyright">© 2026 Seeun Park. All rights reserved.</div>', unsafe_allow_html=True)

# --- Main Application ---

def show_main_app():
    with st.sidebar:
        st.markdown(f"### 💎 Data Intel PRO")
        st.caption(f"접속자: {st.session_state.current_user['name'] if st.session_state.current_user else '관리자'}")
        if st.button("로그아웃"):
            add_log(st.session_state.current_user["name"] if st.session_state.current_user else "ADMIN", "Logout")
            st.session_state.authenticated = False
            st.rerun()
        st.divider()
        if st.session_state.user_role == "user":
            st.markdown("#### 👤 내 정보 관리")
            new_k = st.text_input("라이선스 키(비밀번호) 변경", type="password")
            if st.button("저장"):
                users = load_json(USERS_FILE, [])
                for u in users:
                    if u["license"] == st.session_state.current_user["license"]:
                        u["license"] = new_k
                        st.session_state.current_user["license"] = new_k
                        break
                save_json(USERS_FILE, users)
                st.success("변경되었습니다!")

    st.markdown("<h1 style='color: #0f172a; font-weight: 900; font-size: 2.5rem;'>Expert Workspace</h1>", unsafe_allow_html=True)
    
    app_tabs = ["🔗 스마트 매칭", "📄 정밀 추출", "📊 심층 분석", "📂 스마트 병합"]
    if st.session_state.user_role == "admin": app_tabs.append("⚙️ 관리 & 모니터링")
    
    tabs = st.tabs(app_tabs)
    
    # 1. Matching
    with tabs[0]:
        with st.expander("❓ [도움말] 스마트 매칭 사용법"):
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
            use_fuzzy = st.checkbox("지능형 유사도 매칭 (Fuzzy Match)")
            if st.button("🚀 매칭 엔진 가동"):
                with st.spinner("AI 엔진 연산 중..."):
                    d1, d2 = b_df.copy(), r_df.copy()
                    if use_fuzzy:
                        targets = d2[r_k].unique()
                        d1[b_k] = d1[b_k].apply(lambda x: fuzzy_match_logic(x, targets) or x)
                    res = pd.merge(d1, d2[[r_k] + r_cols], left_on=b_k, right_on=r_k, how='left')
                    st.success("데이터 매칭이 완료되었습니다!")
                    st.dataframe(res.head(100))
                    st.download_button("📥 Excel 다운로드", convert_df_to_excel(res), "matched_expert.xlsx")
                    add_log(st.session_state.current_user["name"] if st.session_state.current_user else "ADMIN", "Performed Matching")

    # 2. Extract
    with tabs[1]:
        e_f = st.file_uploader("가공 대상 업로드", key="e_f")
        if e_f:
            e_df = load_file_to_df(e_f)
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            ec1, ec2 = st.columns([1, 2])
            col_f = ec1.selectbox("필터 컬럼", e_df.columns)
            val_f = ec1.text_input("검색어 (쉼표 구분)")
            sel_e = ec2.multiselect("출력 컬럼", e_df.columns, default=list(e_df.columns))
            if st.button("📤 정밀 추출 및 AI 보정"):
                with st.spinner("보정 중..."):
                    res = e_df[sel_e].copy()
                    if val_f:
                        vals = [v.strip() for v in val_f.split(",")]
                        res = res[res[col_f].astype(str).str.contains("|".join(vals), na=False)]
                    res = fill_service_small_from_mid(res)
                    st.success("추출 및 AI 보정이 완료되었습니다!")
                    st.dataframe(res.head(100))
                    st.download_button("📥 결과 저장", convert_df_to_excel(res), "extracted_expert.xlsx")
                    add_log(st.session_state.current_user["name"] if st.session_state.current_user else "ADMIN", "Performed Extraction")
            st.markdown('</div>', unsafe_allow_html=True)

    # 3. Insight
    with tabs[2]:
        a_f = st.file_uploader("분석 파일 업로드", key="a_f")
        if a_f:
            a_df = load_file_to_df(a_f)
            score = get_health_score(a_df)
            st.markdown(f"### 🏥 데이터 건강 점수: <span style='color: #16a34a; font-weight: 800;'>{score}점</span>", unsafe_allow_html=True)
            st.divider()
            st.subheader("📊 데이터 분포 분석")
            st.bar_chart(a_df.iloc[:, 0].value_counts().head(15))

    # 5. Admin (Integrated Audit)
    if st.session_state.user_role == "admin":
        with tabs[-1]:
            # Monitoring Section
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.subheader("📊 시스템 운영 모니터링")
            logs = load_json(LOGS_FILE, [])
            if logs:
                log_df = pd.DataFrame(logs[::-1])
                st.dataframe(log_df.head(20), use_container_width=True)
                st.divider()
                st.subheader("📈 사용자별 접속 빈도")
                st.bar_chart(log_df["user"].value_counts())
            st.markdown('</div>', unsafe_allow_html=True)

            # Control Section
            adm_c1, adm_c2 = st.columns(2)
            with adm_c1:
                st.markdown('<div class="premium-card">', unsafe_allow_html=True)
                st.subheader("🔐 보안 설정")
                new_adm_p = st.text_input("마스터 패스워드 변경", type="password")
                if st.button("패스워드 저장"):
                    sets = load_json(SETTINGS_FILE, {"master_password":"0303"})
                    sets["master_password"] = new_adm_p
                    save_json(SETTINGS_FILE, sets)
                    add_log("ADMIN", "Master Password Changed")
                    st.success("변경 완료!")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with adm_c2:
                st.markdown('<div class="premium-card">', unsafe_allow_html=True)
                st.subheader("👥 사용자 및 라이선스 관리")
                with st.form("lic_gen"):
                    u_n = st.text_input("사용자 이름")
                    u_d = st.number_input("사용 일수", value=30)
                    if st.form_submit_button("라이선스 자동 발급"):
                        new_lic = str(uuid.uuid4())[:8].upper()
                        usrs = load_json(USERS_FILE, [])
                        usrs.append({"name":u_n, "license":new_lic, "expiry":(datetime.now()+timedelta(days=u_d)).strftime("%Y-%m-%d"), "req_ext":False})
                        save_json(USERS_FILE, usrs)
                        add_log("ADMIN", f"Issued License to {u_n}")
                        st.success(f"Key: {new_lic}")
                        st.rerun()
                
                st.divider()
                usrs = load_json(USERS_FILE, [])
                for i, u in enumerate(usrs):
                    col_i, col_a = st.columns([2, 1])
                    with col_i:
                        st.write(f"**{u['name']}** (`{u['license']}`)")
                        st.caption(f"만료: {u['expiry']}")
                        if u.get("req_ext"): st.markdown("<span class='badge badge-req'>🆘 연장 요청 중</span>", unsafe_allow_html=True)
                    with col_a:
                        if st.button("연장", key=f"e_{i}"):
                            exp = datetime.strptime(u["expiry"], "%Y-%m-%d")
                            u["expiry"] = (exp + timedelta(days=30)).strftime("%Y-%m-%d")
                            u["req_ext"] = False
                            save_json(USERS_FILE, usrs)
                            add_log("ADMIN", f"Extended License for {u['name']}")
                            st.rerun()
                        if st.button("삭제", key=f"d_{i}"):
                            usrs.pop(i)
                            save_json(USERS_FILE, usrs)
                            add_log("ADMIN", f"Deleted User {u['name']}")
                            st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

# --- Entry ---
def main():
    if not st.session_state.authenticated: show_landing()
    else: show_main_app()

if __name__ == "__main__": main()
