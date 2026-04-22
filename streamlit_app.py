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

# --- Custom Premium Style ( 저작권 표시 포함 ) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&family=Pretendard:wght@400;600;700;800&display=swap');
    * { font-family: 'Pretendard', sans-serif; }
    
    .stApp {
        background: linear-gradient(135deg, #f8fafc 0%, #ffffff 50%, #f1f5f9 100%);
        color: #1e293b;
    }
    
    .hero-title {
        font-family: 'Outfit', sans-serif; font-size: 4.8rem; font-weight: 900; text-align: center;
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
        margin-top: 100px; margin-bottom: 5px; letter-spacing: -2px;
    }
    
    .hero-subtitle {
        text-align: center; color: #64748b; font-size: 1.5rem; font-weight: 500; margin-bottom: 60px;
    }
    
    .login-card {
        background: white; border: 1px solid #e2e8f0; border-radius: 40px;
        padding: 50px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.05);
        max-width: 500px; margin: 0 auto;
        display: flex; flex-direction: column; align-items: center;
    }
    
    /* Footer Copyright */
    .copyright-footer {
        position: fixed;
        bottom: 20px;
        right: 30px;
        color: #94a3b8;
        font-size: 0.85rem;
        font-family: 'Outfit', sans-serif;
        font-weight: 500;
        letter-spacing: 0.5px;
    }
    
    .stTextInput>div>div>input {
        border-radius: 16px !important; border: 1px solid #cbd5e1 !important;
        text-align: center; padding: 15px !important;
    }
    
    .stButton>button {
        background: #2563eb !important; color: white !important; font-weight: 800 !important;
        border-radius: 16px !important; padding: 16px !important; width: 100% !important;
        transition: 0.3s !important; border: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- UI & Auth ---

def show_landing():
    st.markdown("<h1 class='hero-title'>DATA INTEL PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p class='hero-subtitle'>Smart & Secure Data Workflows</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #0f172a; margin-bottom: 40px; font-weight: 800;'>시스템 보안 인증</h2>", unsafe_allow_html=True)
        
        mode = st.radio("", ["마스터 패스워드", "개인 라이선스"], horizontal=True, key="login_mode", label_visibility="collapsed")
        
        settings = load_json(SETTINGS_FILE, {"master_password": "0303"})
        users = load_json(USERS_FILE, [])
        
        if mode == "마스터 패스워드":
            pwd = st.text_input("PASSWORD", type="password", placeholder="Master Password", label_visibility="collapsed")
            if st.button("🚀 AUTHORIZE"):
                if pwd == settings["master_password"]:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "admin"
                    st.rerun()
                else: st.error("Password Mismatch.")
        else:
            lic = st.text_input("LICENSE", type="password", placeholder="Your License Key", label_visibility="collapsed")
            if st.button("🚀 VERIFY"):
                user = next((u for u in users if u["license"] == lic), None)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "user"
                    st.session_state.current_user = user
                    st.rerun()
                else: st.error("Invalid License.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Developer Copyright Footer
    st.markdown("""
        <div class="copyright-footer">
            © 2026 Seeun Park. All rights reserved.
        </div>
    """, unsafe_allow_html=True)

def show_main_app():
    # (Full app logic remains preserved)
    with st.sidebar:
        st.markdown("### 💎 Data Intel PRO")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()
    st.markdown("<h1>Main Application</h1>", unsafe_allow_html=True)

def main():
    if not st.session_state.authenticated: show_landing()
    else: show_main_app()

if __name__ == "__main__": main()
