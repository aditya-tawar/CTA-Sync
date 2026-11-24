"""Shared Indegene and CTA Sync branding."""
from pathlib import Path

import streamlit as st

from cta_app.core.assets import get_base64_image

ASSETS = Path(__file__).resolve().parents[2] / "assets"


def render_brand_header() -> None:
    """Keep both original brand assets together across application screens."""
    indegene = get_base64_image(str(ASSETS / "indegene_logo.png"))
    cta_sync = get_base64_image(str(ASSETS / "cta_sync.png"))
    st.markdown(
        '<div class="brand-header" aria-label="CTA Sync by Indegene">'
        f'<img class="indegene-brand" src="data:image/png;base64,{indegene}" alt="Indegene">'
        '<span class="brand-divider" aria-hidden="true"></span>'
        f'<img class="cta-sync-brand" src="data:image/png;base64,{cta_sync}" alt="CTA Sync - Campaign CTA Validation Platform">'
        '</div>',
        unsafe_allow_html=True,
    )
