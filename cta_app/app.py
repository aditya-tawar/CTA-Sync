"""Main Streamlit application shell."""

from __future__ import annotations

import os
import time

import streamlit as st

from streamlit_cookies_manager import CookieManager

from cta_app.core.assets import resolve_asset_path
from cta_app.components.branding import render_brand_header
from cta_app.ui.styles import render_cta_sync_styles
from cta_app.pages.admin import render_admin_console
from cta_app.pages.cta_sync import render_cta_sync_page
from cta_app.services.auth import initialize_users, verify_credentials

SESSION_TIMEOUT_SECONDS = 6000

def configure_page() -> None:
    render_cta_sync_styles()


def initialize_session_state() -> None:
    defaults = {
        "logged_in": False,
        "username": "",
        "role": "",
        "login_timestamp": 0,
        "page": "home",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

APP_STATE_KEYS_TO_CLEAR_ON_LOGOUT = (
    "current_step",
    "campaign_name",
    "brand_name",
    "indication",
    "audience",
    "campaign_id",
    "campaign_files",
    "campaign_files_data",
    "claravine_file",
    "claravine_files_data",
    "claravine_file_data",
    "claravine_file_name",
    "claravine_file_size",
    "csv_df",
    "csv_dfs",
    "col_name",
    "col_url",
    "col_lp",
    "cta_data",
    "cata_data_by_csv",
    "selected_claravine_csv",
    "html_ctas",
    "claravine_data",
    "res_df",
    "filter",
    "export_selected_ctas",
    "validation_time",
)


def clear_login_state(cookies: CookieManager) -> None:
    for cookie_key in ("login_timestamp", "username", "role"):
        cookies.pop(cookie_key, None)
    st.session_state.logged_in = False
    st.session_state.login_timestamp = 0
    st.session_state.username = ""
    st.session_state.role = ""

    for key in APP_STATE_KEYS_TO_CLEAR_ON_LOGOUT:
        st.session_state.pop(key, None)

    st.session_state["campaign_uploader_key"] = (
        st.session_state.get("campaign_uploader_key", 0) + 1
    )
    st.session_state["claravine_uploader_key"] = (
        st.session_state.get("claravine_uploader_key", 0) + 1
    )


def restore_session_from_cookies(cookies: CookieManager) -> None:
    if st.session_state.logged_in or "login_timestamp" not in cookies:
        return

    try:
        login_timestamp = float(cookies["login_timestamp"])
        if time.time() - login_timestamp >= SESSION_TIMEOUT_SECONDS:
            raise ValueError("Expired")

        st.session_state.logged_in = True
        st.session_state.login_timestamp = login_timestamp
        st.session_state.username = cookies.get("username", "")
        st.session_state.role = cookies.get("role", "")
    except Exception:
        clear_login_state(cookies)


def check_session_timeout(cookies: CookieManager) -> None:
    if (
        st.session_state.logged_in
        and st.session_state.login_timestamp > 0
        and time.time() - st.session_state.login_timestamp > SESSION_TIMEOUT_SECONDS
    ):
        clear_login_state(cookies)
        st.warning("⏰ Session expired. Please log in again.")
        st.rerun()


def login_user(cookies: CookieManager, username: str, role: str) -> None:
    login_timestamp = time.time()
    st.session_state.logged_in = True
    st.session_state.username = username
    st.session_state.role = role
    st.session_state.login_timestamp = login_timestamp
    cookies["login_timestamp"] = str(login_timestamp)
    cookies["username"] = username
    cookies["role"] = role


def logout_user(cookies: CookieManager) -> None:
    clear_login_state(cookies)
    st.rerun()


def render_logo(width: int = 250) -> None:
    logo_path = resolve_asset_path("assets/indegene_logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=width)
    else:
        st.warning(f"Logo not found. Current directory: {os.getcwd()}")


def render_logout_button(cookies: CookieManager) -> None:
    if st.button("🚪 Logout", type="secondary", key="logout", use_container_width=True):
        logout_user(cookies)


def render_authenticated_app(cookies: CookieManager) -> None:
    header_left, header_right = st.columns([9, 1])
    with header_left:
        render_brand_header()
    with header_right:
        render_logout_button(cookies)

    st.markdown('<div class="brand-rule"></div>', unsafe_allow_html=True)
    if st.session_state.role == "admin":
        render_admin_console()
    elif st.session_state.role == "user":
        render_cta_sync_page()
    else:
        st.error("❌ Unknown role detected. Contact support.")
        logout_user(cookies)


def render_login_form(cookies: CookieManager) -> None:
    render_brand_header()
    st.markdown('<div class="brand-rule"></div>', unsafe_allow_html=True)
    story, form_column = st.columns([1.15, 1], gap="large")
    with story:
        st.markdown(
            '<section class="login-story"><div class="eyebrow">Indegene &middot; CTA Sync</div>'
            '<h1>Confidence in<br>every campaign.</h1>'
            '<p>A clearer path from campaign assets to validated links.</p>'
            '<div class="feature-list"><span>01 &nbsp; Bring HTML, email, and tracking together</span>'
            '<span>02 &nbsp; Find destination and tracking mismatches</span>'
            '<span>03 &nbsp; Share a detailed Excel QA report</span></div></section>',
            unsafe_allow_html=True,
        )
    with form_column:
        st.subheader("Welcome back")
        st.caption("Sign in to your campaign validation workspace.")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign in", use_container_width=True, type="primary")
        st.caption("Need access? Contact your platform administrator.")

    if not submitted:
        return

    if not username or not password:
        st.warning("Please enter both username and password")
        return

    success, role = verify_credentials(username, password)
    if not success:
        st.error("❌ Invalid username or password")
        return

    login_user(cookies, username, role or "user")
    st.success(f"✅ Welcome, {username}!")
    st.rerun()


def run_app() -> None:
    configure_page()
    initialize_users()

    cookies = CookieManager()
    if not cookies.ready():
        st.stop()

    initialize_session_state()
    restore_session_from_cookies(cookies)
    check_session_timeout(cookies)

    if st.session_state.logged_in:
        render_authenticated_app(cookies)
    else:
        render_login_form(cookies)
