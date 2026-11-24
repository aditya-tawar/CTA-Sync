"""Claravine column detection and mapping UI."""

from __future__ import annotations

import re

import pandas as pd
import streamlit as st


def find_column(columns, *prefixes):
    """Return the first column whose normalized name starts with any prefix."""

    def normalize_column_name(value):
        return re.sub(r"[^a-z0-9]", "", str(value).lower())

    normalized_prefixes = [normalize_column_name(prefix) for prefix in prefixes]
    for column in columns:
        normalized_column = normalize_column_name(column)
        if any(normalized_column.startswith(prefix) for prefix in normalized_prefixes):
            return column
    return None


def guess_col(columns, *keyword_groups):
    for keywords in keyword_groups:
        for column in columns:
            if all(keyword in column.lower().strip() for keyword in keywords):
                return column
    return columns[0]


def infer_claravine_columns(columns: list[str]) -> tuple[str, str, str]:
    name_col = guess_col(
        columns, ["call", "action"], ["cta", "name"], ["link", "name"], ["name"]
    )
    url_col = guess_col(
        columns, ["final", "url"], ["cta", "url"], ["email", "url"], ["link"], ["url"]
    )
    lp_col = guess_col(
        columns, ["landing", "url"], ["landing"], ["destination", "url"], ["final"]
    )

    used_columns = {name_col}
    if url_col in used_columns:
        url_col = next((column for column in columns if column not in used_columns), columns[0])
    used_columns.add(url_col)
    if lp_col in used_columns:
        lp_col = next((column for column in columns if column not in used_columns), columns[0])

    return name_col, url_col, lp_col


def render_column_mapping(csv_df: pd.DataFrame):
    columns = csv_df.columns.tolist()
    name_guess, url_guess, lp_guess = infer_claravine_columns(columns)

    st.markdown("#### Map Claravine CSV Columns")
    name_area, url_area, lp_area = st.columns(3)
    with name_area:
        st.caption("CTA Name column")
        name_col = st.selectbox(
            "CTA Name",
            columns,
            index=columns.index(name_guess),
            key="name_col",
            label_visibility="collapsed",
        )
    with url_area:
        st.caption("Email CTA URL column")
        url_col = st.selectbox(
            "Email URL",
            columns,
            index=columns.index(url_guess),
            key="url_col",
            label_visibility="collapsed",
        )
    with lp_area:
        st.caption("Landing Page URL column")
        lp_col = st.selectbox(
            "Landing Page URL",
            columns,
            index=columns.index(lp_guess),
            key="lp_col",
            label_visibility="collapsed",
        )

    st.session_state.col_name = name_col
    st.session_state.col_url = url_col
    st.session_state.col_lp = lp_col
    return name_col, url_col, lp_col

