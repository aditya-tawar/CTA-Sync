"""Shared Indegene and CTA Sync branding."""
from functools import lru_cache
from html import escape
from pathlib import Path

import streamlit as st

from cta_app.core.assets import get_base64_image

ASSETS = Path(__file__).resolve().parents[2] / "assets"


@lru_cache(maxsize=None)
def image_src(filename: str) -> str:
    return f"data:image/png;base64,{get_base64_image(str(ASSETS / filename))}"


def render_app_bar(username: str, role: str) -> None:
    """Left half of the signed-in app bar; the caller places the logout button beside it."""
    st.markdown(
        '<div class="app-bar">'
        f'<img class="app-bar-logo" src="{image_src("cta_sync_banner.png")}" '
        'alt="CTA Sync - Campaign CTA Validation Platform">'
        f'<div class="app-bar-user">{escape(role.title())}'
        f'<strong>{escape(username)}</strong></div></div>',
        unsafe_allow_html=True,
    )


def render_brand_header() -> None:
    st.markdown(
        '<div class="brand-header" aria-label="CTA Sync by Indegene">'
        f'<img class="banner" src="{image_src("cta_sync_banner.png")}" alt="CTA Sync">'
        '<span class="brand-divider" aria-hidden="true"></span>'
        f'<img class="indegene" src="{image_src("indegene_logo_tight.png")}" alt="Indegene">'
        '</div>',
        unsafe_allow_html=True,
    )
