"""Streamlit entry point: configure the page before importing UI dependencies."""
import streamlit as st

st.set_page_config(
    page_title="CTA Sync · Indegene",
    page_icon="assets/cta_sync_icon.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from cta_app.app import run_app

if __name__ == "__main__":
    run_app()
