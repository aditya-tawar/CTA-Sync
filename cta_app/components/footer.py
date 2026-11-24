"""Shared branded footer."""
from datetime import date
import streamlit as st

def render_footer():
    st.markdown(f'<footer class="app-footer"><span>&copy; {date.today().year} CTA Sync by Indegene</span><span>Campaign validation, with clarity.</span></footer>', unsafe_allow_html=True)
    if st.button("Help & frequently asked questions", key="footer_faq"):
        st.switch_page("pages/faqs.py")
