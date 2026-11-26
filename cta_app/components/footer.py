"""Shared footer without unsupported service or compliance claims."""
from datetime import date

import streamlit as st

from cta_app.components.branding import image_src


def render_footer():
    left, right = st.columns([4, 1], vertical_alignment="center")
    with left:
        st.markdown(
            '<div class="app-footer"><span>A product of</span>'
            f'<img src="{image_src("indegene_logo_tight.png")}" alt="Indegene">'
            f'<span>&middot; &copy; {date.today().year} CTA Sync</span></div>',
            unsafe_allow_html=True,
        )
    with right:
        if st.button("Help & FAQs", type="tertiary", key="footer_faq", use_container_width=True):
            st.switch_page("pages/faqs.py")
