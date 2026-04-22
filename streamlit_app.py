import streamlit as st
import pandas as pd
import numpy as np
import io
import json
import json
import uuid
import difflib
import sys
from datetime import datetime, timedelta
from pathlib import Path
from app.core import database

# ==========================================
# 1. 시스템 아키텍처 및 설정 (System Architecture)
# ==========================================
ROOT_DIR = Path(__file__).parent.absolute()
if str(ROOT_DIR) not in sys.path: sys.path.append(str(ROOT_DIR))

# 데이터 영속성 (SaaS Level Persistence)
AUTH_DIR = Path.home() / ".dataintelligence_pro"
AUTH_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = AUTH_DIR/"auth_settings.json"

# --- Core Handler Integration ---
try:
    from app.core.handlers import load_file_to_df
except ImportError:
    def load_file_to_df(f):
        if f.name.endswith('xlsx'): return pd.read_excel(f, engine='openpyxl')
        return pd.read_csv(f)

# ==========================================
# 2. 디자인 시스템 (사용자 제공 프리미엄 UI)
# ==========================================
st.set_page_config(page_title="Data Intel PRO", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

PROFESSIONAL_STYLE = """
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    /* 기본 배경 및 폰트 설정 */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Pretendard', sans-serif;
        background: radial-gradient(circle at top right, #f1f5f9, #e2e8f0);
    }

    /* 상단 메뉴바/헤더 숨기기 (더 깔끔한 랜딩을 위해) */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* 메인 컨테이너 중앙 정렬 */
    .main-center-wrapper {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding-top: 5vh;
    }

    /* 타이틀 섹션 */
    .hero-container {
        text-align: center;
        margin-bottom: 2.5rem;
    }
    .hero-title {
        font-size: 3.5rem; 
        font-weight: 900; 
        color: #0f172a;
        letter-spacing: -0.05em; 
        margin-bottom: 0.5rem;
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-sub { 
        color: #64748b; 
        font-size: 1.2rem; 
        font-weight: 400;
        letter-spacing: -0.02em;
    }

    /* 슬림 프리미엄 카드 - Streamlit 컨테이너에 직접 적용 */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255, 255, 255, 0.95) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 24px !important;
        padding: 20px 15px !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important;
        width: 100% !important;
        max-width: 320px !important;
        margin: 0 auto !important;
    }
    
    /* 중앙 정렬을 위한 컨테이너 래퍼 */
    .stApp > header {
        background-color: transparent !important;
    }

    /* 입력창 및 라디오 버튼 커스텀 */
    .stTextInput > div > div > input {
        border-radius: 8px !important;
        border: 1px solid #e2e8f0 !important;
        height: 40px !important;
        font-size: 0.9rem !important;
        background-color: #f8fafc !important;
        transition: all 0.2s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
    }

    /* 버튼 스타일링 */
    .stButton > button {
        background: #0f172a !important; /* 다크 네이비 테마 */
        color: #ffffff !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        width: 100% !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        border: none !important;
        height: 40px !important;
        margin-top: 10px;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        background: #1e293b !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    }

    /* 라디오 버튼 중앙 정렬 */
    div[data-testid="stRadio"] > div {
        justify-content: center;
        gap: 20px;
    }
</style>
"""

# ==========================================
# 3. 데이터 지능형 엔진 (Intelligence Engine)
# ==========================================
def enterprise_match(b_df, r_df, b_k, r_k, cols, fuzzy=False):
    b_c, r_c = b_df.copy(), r_df.copy()
    b_c[b_k] = b_c[b_k].astype(str).str.strip()
    r_c[r_k] = r_c[r_k].astype(str).str.strip()
    
    if fuzzy:
        def get_best_match(val, targets):
            m = difflib.get_close_matches(val, targets, n=1, cutoff=0.7)
            return m[0] if m else None
        r_targets = r_c[r_k].unique().tolist()
        b_c['match_key'] = b_c[b_k].apply(lambda x: get_best_match(x, r_targets))
        res = pd.merge(b_c, r_c[[r_k] + cols], left_on='match_key', right_on=r_k, how='left')
    else:
        res = pd.merge(b_c, r_c[[r_k] + cols], left_on=b_k, right_on=r_k, how='left')
    return res

def convert_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False)
    return output.getvalue()

# ==========================================
# 4. 화면 로직 (System Views)
# ==========================================

def show_landing():
    # 1. 사용자 제공 스타일 적용
    st.markdown(PROFESSIONAL_STYLE, unsafe_allow_html=True)
    
    # 2. 레이아웃 배치 (중앙 컨테이너 폭 축소)
    _, center_col, _ = st.columns([1.5, 1.2, 1.5])
    
    with center_col:
        st.markdown('<div class="main-center-wrapper">', unsafe_allow_html=True)
        
        # 헤더 섹션
        st.markdown('''
            <div class="hero-container">
                <h1 class="hero-title">DATA INTEL PRO</h1>
                <p class="hero-sub">Expert Intelligence for Enterprise</p>
            </div>
        ''', unsafe_allow_html=True)
        
        # 로그인 카드 섹션 (Streamlit Native Container)
        with st.container(border=True):
            st.markdown("<p style='text-align:center; font-weight:700; color:#475569; margin-bottom:15px; font-size:1.0rem;'>SECURE ACCESS</p>", unsafe_allow_html=True)
            
            mode = st.radio("Access Mode", ["사용자 접속", "무료체험 가입", "관리자 모드"], horizontal=True, label_visibility="collapsed")
            
            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            
            # 설정 파일 연동
            settings = {"master_password": "0303"}
            if SETTINGS_FILE.exists():
                try:
                    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                        settings = json.load(f)
                except: pass
            
            if mode == "사용자 접속":
                name = st.text_input("NAME", placeholder="Full Name", label_visibility="collapsed")
                key = st.text_input("LICENSE", type="password", placeholder="License Key", label_visibility="collapsed")
                if st.button("Sign In to Workspace", use_container_width=True):
                    u = database.get_user_by_license(name, key)
                    if u:
                        if datetime.strptime(u["expiry"], "%Y-%m-%d") < datetime.now(): 
                            st.error("만료된 라이선스입니다.")
                        else:
                            st.session_state.authenticated, st.session_state.user_role, st.session_state.current_user = True, "user", u
                            database.add_log(name, "Login Success")
                            st.rerun()
                    else: 
                        st.error("인증 정보가 올바르지 않습니다.")
            elif mode == "관리자 모드":
                pwd = st.text_input("ADMIN PWD", type="password", placeholder="Master Password", label_visibility="collapsed")
                if st.button("Authenticate System", use_container_width=True):
                    if pwd == settings["master_password"]: 
                        st.session_state.authenticated = True
                        st.session_state.user_role = "admin"
                        st.session_state.current_user = {"name": "ADMIN"}
                        database.add_log("ADMIN", "System Unlock")
                        st.rerun()
                    else:
                        st.error("Invalid Credential")
            elif mode == "무료체험 가입":
                st.markdown("<p style='font-size:0.9rem; color:#64748b; text-align:center;'>7일 무료 체험을 시작합니다.</p>", unsafe_allow_html=True)
                reg_name = st.text_input("REG_NAME", placeholder="Full Name (이름)", label_visibility="collapsed")
                reg_phone = st.text_input("REG_PHONE", placeholder="Phone Number (연락처)", label_visibility="collapsed")
                if st.button("가입 및 라이선스 발급", use_container_width=True):
                    if len(reg_name) < 2 or len(reg_phone) < 10:
                        st.error("올바른 이름과 연락처를 입력해주세요.")
                    else:
                        if database.get_user_by_phone(reg_phone):
                            st.error("이미 무료체험이 등록된 연락처입니다.")
                        else:
                            key = str(uuid.uuid4())[:8].upper()
                            expiry = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
                            database.create_user(reg_name, reg_phone, key, expiry)
                            database.add_log(reg_name, "Registered (7-day trial)")
                            st.success("🎉 가입이 완료되었습니다! (7일 무료 체험)")
                            st.markdown("👇 **아래 발급된 라이선스 키를 복사해 주세요.**")
                            st.code(key, language=None)
                            st.info("위 키를 복사한 후 상단의 **'사용자 접속'** 탭을 눌러 로그인해 주세요.")
        
        # 하단 푸터
        st.markdown("<p style='text-align:center; margin-top:30px; color:#94a3b8; font-size:0.8rem;'>© 2026 Data Intel Pro. All rights reserved.</p>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

def show_main_app():
    global settings
    # Load or initialize settings (including pricing)
    default_settings = {"master_password": "0303", "price_basic": 39000, "price_pro": 99000, "price_enterprise": 1080000}
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except:
            settings = default_settings
    else:
        settings = default_settings
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    # 워크스페이스 전용 헤더 보이기 복구 (선택 사항)
    st.markdown("<style>header {visibility: visible;}</style>", unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown(f"### 💎 Data Intel PRO")
        
        user = st.session_state.current_user
        role = st.session_state.user_role
        
        st.info(f"👤 접속자: {user.get('name')}")
        
        if role == "user":
            expiry_str = user.get("expiry", "")
            if expiry_str:
                try:
                    expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
                    days_left = (expiry_date - datetime.now()).days
                    if days_left <= 7:
                        st.warning(f"⏳ 만료 예정: {expiry_str} (D-{days_left})\\n\\n기간이 얼마 남지 않았습니다.")
                    else:
                        st.success(f"✅ 라이선스 유효: ~{expiry_str} (D-{days_left})")
                except:
                    pass
            
            with st.expander("💬 라이선스 연장 문의"):
                st.markdown("**[ 이메일 문의 ]**")
                st.code("bough38@gmail.com")
                st.markdown("**[ 카카오톡 문의 ]**")
                qr_url = "https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=mailto:bough38@gmail.com"
                st.image(qr_url, caption="QR 코드를 스캔해주세요", width=150)
                st.caption("기타 연장 및 추가 문의는 위 연락처로 부탁드립니다.")
                
            with st.expander("💳 정기 결제 및 라이선스 구매"):
                st.markdown("<p style='font-size:0.85rem; color:#64748b;'>정식 요금제를 결제하여 즉시 라이선스를 연장하세요.</p>", unsafe_allow_html=True)
                plan = st.selectbox("요금제 선택", ["1개월 이용권 (₩39,000)", "6개월 이용권 (₩190,000)", "1년 이용권 (₩350,000)"])
                
                with st.form("payment_form"):
                    st.text_input("카드 번호", placeholder="0000-0000-0000-0000")
                    c1, c2 = st.columns(2)
                    c1.text_input("유효기간", placeholder="MM/YY")
                    c2.text_input("CVC", type="password", placeholder="***")
                    st.text_input("카드 비밀번호 앞 2자리", type="password", placeholder="**")
                    
                    if st.form_submit_button("💳 토스페이먼츠 안전결제", use_container_width=True):
                        days_to_add = 30 if "1개월" in plan else (180 if "6개월" in plan else 365)
                        amount = 39000 if "1개월" in plan else (190000 if "6개월" in plan else 350000)
                        
                        # DB에서 유저 정보 업데이트
                        u = database.get_user_by_license(user["name"], user["license"])
                        if u:
                            current_expiry = datetime.strptime(u["expiry"], "%Y-%m-%d")
                            if current_expiry < datetime.now():
                                current_expiry = datetime.now()
                            new_expiry = current_expiry + timedelta(days=days_to_add)
                            new_expiry_str = new_expiry.strftime("%Y-%m-%d")
                            
                            # SQLite DB 업데이트
                            database.update_user_expiry(user["license"], new_expiry_str)
                            
                            # 결제 기록 저장 (토스 모의 결제 키 발급)
                            payment_key = f"toss_mock_{uuid.uuid4().hex[:8]}"
                            order_id = f"order_{uuid.uuid4().hex[:12]}"
                            database.record_payment(u["id"], amount, payment_key, order_id, plan)
                            database.add_log(user["name"], f"Purchased {plan} ({amount} KRW)")
                            
                            # 세션 강제 업데이트
                            st.session_state.current_user["expiry"] = new_expiry_str
                        
                        st.success(f"결제가 성공적으로 처리되었습니다! 라이선스가 {days_to_add}일 연장되었습니다.")
                        st.balloons()
                        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()
        st.divider()

    st.markdown("<h2 style='font-weight: 900; color: #1e293b; margin-bottom: 2rem;'>Intelligence Workspace</h2>", unsafe_allow_html=True)
    tabs = st.tabs(["🔗 지능형 매칭", "📄 정밀 추출", "📊 심층 분석", "📂 스마트 병합", "💰 요금제"] + (["⚙️ 어드민 시스템"] if st.session_state.user_role == "admin" else []))
    
    with tabs[0]:
        st.markdown('<div style="background: white; border: 1px solid #f1f5f9; border-radius: 18px; padding: 20px;">', unsafe_allow_html=True)
        st.markdown("#### 🔗 데이터 결합 및 유사도 매칭")
        c1, c2 = st.columns(2)
        b_f, r_f = c1.file_uploader("원본(Base)", key="m_b"), c2.file_uploader("참조(Ref)", key="m_r")
        if b_f and r_f:
            b_df, r_df = load_file_to_df(b_f), load_file_to_df(r_f)
            bk, rk = c1.selectbox("기준 열", b_df.columns), c2.selectbox("매칭 열", r_df.columns)
            r_cols = st.multiselect("추가할 데이터", [c for c in r_df.columns if c != rk])
            use_fuzzy = st.checkbox("유사도 기반 매칭(Fuzzy Match) 사용")
            if st.button("🚀 지능형 매칭 실행"):
                with st.spinner("데이터 분석 중..."):
                    res = enterprise_match(b_df, r_df, bk, rk, r_cols, fuzzy=use_fuzzy)
                    st.dataframe(res.head(100), use_container_width=True)
                    st.download_button("📥 다운로드(Excel)", convert_to_excel(res), "result.xlsx")
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]:
        st.markdown('<div style="background: white; border: 1px solid #f1f5f9; border-radius: 18px; padding: 20px;">', unsafe_allow_html=True)
        st.markdown("#### 📄 조건별 데이터 정밀 추출")
        f = st.file_uploader("추출 파일 업로드", key="ex_f")
        if f:
            df = load_file_to_df(f)
            col = st.selectbox("필터 기준 열", df.columns)
            val = st.text_input("필터 키워드 (공백 시 전체)")
            if st.button("🚀 정밀 추출"):
                res = df[df[col].astype(str).str.contains(val)] if val else df
                st.dataframe(res, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[2]:
        st.markdown('<div style="background: white; border: 1px solid #f1f5f9; border-radius: 18px; padding: 20px;">', unsafe_allow_html=True)
        st.markdown("#### 📊 데이터 품질 보고서 및 시각화")
        f = st.file_uploader("분석 파일 업로드", key="an_f")
        if f:
            df = load_file_to_df(f)
            st.write("##### 🧐 품질 요약")
            c1, c2, c3 = st.columns(3)
            c1.metric("전체 행", len(df))
            c2.metric("결측치(Null)", df.isnull().sum().sum())
            c3.metric("중복 행", df.duplicated().sum())
            st.area_chart(df.select_dtypes(include=[np.number]).iloc[:, :3])
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[3]:
        st.markdown('<div style="background: white; border: 1px solid #f1f5f9; border-radius: 18px; padding: 20px;">', unsafe_allow_html=True)
        st.markdown("#### 📂 스마트 데이터 병합 (Multi-File)")
        files = st.file_uploader("병합할 파일 다중 선택", accept_multiple_files=True, key="mr_f")
        if files:
            dfs = [load_file_to_df(f) for f in files]
            dedup = st.checkbox("중복 행 제거")
            if st.button("🚀 모든 파일 병합"):
                res = pd.concat(dfs, axis=0, ignore_index=True)
                if dedup: res = res.drop_duplicates()
                st.dataframe(res.head(100), use_container_width=True)
                st.download_button("📥 병합 결과 다운로드", convert_to_excel(res), "merged.xlsx")
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.user_role == "admin":
        with tabs[-1]:
            st.subheader("🕵️‍♂️ 관리자 대시보드 (KPI & 사용자 제어)")
            
            # 메트릭 대시보드
            metrics = database.get_metrics()
            col1, col2, col3 = st.columns(3)
            col1.metric("총 결제 수익 (KRW)", f"₩{metrics['revenue']:,}")
            col2.metric("활성 사용자 (Active)", f"{metrics['active_users']}명")
            col3.metric("누적 사용자 (Total)", f"{metrics['total_users']}명")
            
            st.divider()
            
            # 관리자 전용 가격 편집 폼
            with st.expander("💲 가격 설정 관리"):
                c1, c2, c3 = st.columns(3)
                new_basic = c1.number_input("Basic (월)", min_value=0, value=int(settings.get("price_basic", 39000)), step=1000)
                new_pro = c2.number_input("Professional (월)", min_value=0, value=int(settings.get("price_pro", 99000)), step=1000)
                new_enterprise = c3.number_input("Enterprise (년)", min_value=0, value=int(settings.get("price_enterprise", 1080000)), step=5000)
                if st.button("💾 가격 저장", use_container_width=True):
                    # 업데이트 후 파일에 저장
                    settings["price_basic"] = new_basic
                    settings["price_pro"] = new_pro
                    settings["price_enterprise"] = new_enterprise
                    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                        json.dump(settings, f, ensure_ascii=False, indent=2)
                    st.success("가격 정보가 저장되었습니다.")
                    # 세션 업데이트
                    st.session_state.price_basic = new_basic
                    st.session_state.price_pro = new_pro
                    st.session_state.price_enterprise = new_enterprise
                    st.rerun()
            
            st.markdown("#### 👥 실시간 회원 관리")
            users_list = database.get_all_users()
            if users_list:
                df = pd.DataFrame(users_list)
                df = df[['id', 'name', 'phone', 'license', 'expiry', 'role', 'created_at']]
                
                # data_editor로 시각화 (수정은 막아두고 UI만)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                st.markdown("##### 🛠 수동 연장 컨트롤")
                col_i, col_a = st.columns([3, 1])
                target_license = col_i.selectbox("사용자 라이선스 선택", [u['license'] for u in users_list])
                if col_a.button("선택 회원 30일 연장", use_container_width=True):
                    for u in users_list:
                        if u['license'] == target_license:
                            current = datetime.strptime(u['expiry'], "%Y-%m-%d")
                            if current < datetime.now(): current = datetime.now()
                            database.update_user_expiry(target_license, (current + timedelta(days=30)).strftime("%Y-%m-%d"))
                            database.add_log("ADMIN", f"Extended license {target_license} by 30 days")
                            st.success("연장 완료!"); st.rerun()

def main():
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False
    if 'current_user' not in st.session_state: st.session_state.current_user = None
    if 'user_role' not in st.session_state: st.session_state.user_role = "user"
    if not st.session_state.authenticated: show_landing()
    else: show_main_app()

if __name__ == "__main__": main()
