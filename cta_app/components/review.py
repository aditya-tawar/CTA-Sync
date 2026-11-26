"""Review campaign inputs before running network-dependent validation."""
from io import BytesIO

import pandas as pd
import streamlit as st

from cta_app.domain.columns import render_column_mapping


def render_input_review() -> bool:
    campaigns = st.session_state.get("campaign_files_data") or {}
    references = st.session_state.get("claravine_files_data") or {}
    parsed = {}
    errors = []
    for name, content in references.items():
        try:
            frame = pd.read_csv(BytesIO(content))
            frame.columns = frame.columns.str.strip()
            if frame.empty:
                errors.append(f"{name}: the CSV contains no data rows.")
            elif len(set(frame.columns)) != len(frame.columns):
                errors.append(f"{name}: column headers are not unique after trimming spaces.")
            else:
                parsed[name] = frame
        except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
            errors.append(f"{name}: unable to read CSV ({exc}).")
    st.session_state.csv_dfs = parsed
    st.subheader("Files & comparison scope")
    cols = st.columns(3)
    for col, label, count in zip(cols, ["Campaign assets", "Claravine references", "Reference rows"], [len(campaigns), len(references), sum(len(df) for df in parsed.values())]):
        col.metric(label, count)
    inventory = ([{"File": name, "Type": "Campaign", "Details": f"{len(data) / 1024:.1f} KB"} for name, data in campaigns.items()] +
                 [{"File": name, "Type": "Claravine CSV", "Details": f"{len(df)} rows"} for name, df in parsed.items()])
    if inventory:
        st.dataframe(pd.DataFrame(inventory), use_container_width=True, hide_index=True)
    st.caption("Each campaign asset is compared with every Claravine CSV separately. Results are grouped by reference file.")
    if not campaigns:
        errors.append("Add at least one campaign asset in Upload assets.")
    if not references:
        errors.append("Add at least one Claravine CSV in Upload assets.")
    if parsed:
        st.subheader("Confirm column mappings")
        st.caption("Check these selections carefully. The same mapping is applied to all reference files.")
        first = next(iter(parsed.values()))
        render_column_mapping(first)
        mapped = [st.session_state.col_name, st.session_state.col_url, st.session_state.col_lp]
        if len(set(mapped)) != 3:
            errors.append("Choose three different columns for CTA name, tracking link, and landing page.")
        for name, frame in parsed.items():
            missing = [col for col in mapped if col not in frame.columns]
            if missing:
                errors.append(f"{name}: missing mapped columns: {', '.join(missing)}.")
            else:
                blanks = frame[mapped].replace(r"^\s*$", pd.NA, regex=True).isna().any(axis=1).sum()
                if blanks:
                    st.warning(f"{name}: {blanks} row(s) have a blank mapped value. These may affect matching or report checks.")
                with st.expander(f"Preview: {name}"):
                    st.dataframe(frame[list(dict.fromkeys(mapped))].head(5), use_container_width=True, hide_index=True)
    for error in errors:
        st.error(error)
    ready = bool(campaigns and parsed and len(parsed) == len(references) and not errors)
    if ready:
        st.success("Inputs are ready. Start validation to compare CTAs and tracking details.")
    return ready
