import io
import os
import time
from datetime import datetime
from email import policy
from email.parser import BytesParser
from io import BytesIO
from html import escape

import pandas as pd
import streamlit as st
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from cta_app.components.file_uploader import render_file_uploader
from cta_app.components.footer import render_footer
from cta_app.components.progress import render_progress_bar
from cta_app.core.assets import get_base64_image, resolve_asset_path
from cta_app.core.config import SESSION_DEFAULTS
from cta_app.domain.columns import find_column
from cta_app.components.review import render_input_review
from cta_app.domain.cta_matching import extract_campaign_ctas
from cta_app.domain.validation import generate_cta_data, generate_cta_data_multi
from cta_app.services.qa_export import build_qa_workbook
from cta_app.ui.styles import render_cta_sync_styles

AUDIENCE_OPTIONS = ["", "Healthcare Professionals", "Patients", "Caregivers"]

STATUS_LABELS = {
    "passed": "✓ Passed",
    "warning": "! Warning",
    "failed": "✕ Failed",
    "missing": "? Missing",
}


def _page_heading(eyebrow: str, title: str, text: str) -> None:
    st.markdown(
        f'<div class="page-head"><div class="eyebrow">{eyebrow}</div>'
        f"<h2>{title}</h2><p>{text}</p></div>",
        unsafe_allow_html=True,
    )


def _nav_row(back_label: str | None, next_label: str, next_disabled: bool = False) -> tuple[bool, bool]:
    back_col, _, next_col = st.columns([1, 2, 1])
    back = bool(back_label) and back_col.button(back_label, type="secondary", use_container_width=True)
    forward = next_col.button(next_label, type="primary", use_container_width=True, disabled=next_disabled)
    return back, forward


def _summary_value(value: str) -> str:
    if value:
        return f"<dd>{escape(value)}</dd>"
    return '<dd class="empty">Not specified</dd>'


def render_cta_sync_page():
    render_cta_sync_styles()

    for key, value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value

    render_progress_bar()

    # ══════════════════════════════════════════════════════════════════════════
    #  Step 1 — Upload
    # ══════════════════════════════════════════════════════════════════════════
    if st.session_state.current_step == 1:
        with st.container():
            _page_heading(
                "Step 1 of 4",
                "Upload campaign assets",
                "Add the campaign files to check and the Claravine tracking sheets to compare them against.",
            )
            render_file_uploader()
            claravine_stored = bool(st.session_state.get(
                "claravine_files_data"))

            # ── Where you load the claravine/CSV file ──────────────────────────────────

            if claravine_stored:
                first_bytes = next(
                    iter(st.session_state.claravine_files_data.values())
                )
                try:
                    csv_df = pd.read_csv(BytesIO(first_bytes))
                except Exception:
                    csv_df = None
                    st.warning("The Claravine file could not be read as a CSV.")

                # ── Now safely extract campaign name ───────────────────────────────────
                if csv_df is not None:
                    # Normalize column names (strip spaces, lowercase)
                    csv_df.columns = csv_df.columns.str.strip().str.lower()

                    campaign_col = find_column(csv_df.columns, "campaign name")

                    if campaign_col is not None:
                        campaign_values = (
                            csv_df[campaign_col].dropna().unique().tolist()
                        )
                        campaign_values = [
                            str(v).strip() for v in campaign_values if str(v).strip()
                        ]

                        if len(campaign_values) == 1:
                            st.session_state.campaign_name = campaign_values[0]
                            # st.success(f"✅ Campaign: **{campaign_values[0]}**")

                        elif len(campaign_values) > 1:
                            st.info(
                                "This Claravine file covers more than one campaign. Choose the one to validate."
                            )
                            chosen = st.selectbox(
                                "Campaign",
                                options=campaign_values,
                                key="campaign_name_selector",
                            )
                            st.session_state.campaign_name = chosen

                    else:
                        st.caption(
                            "No campaign name column was found in the Claravine file; "
                            "you can enter the name in the next step."
                        )

            _, forward = _nav_row(
                None,
                "Continue",
                next_disabled=not (st.session_state.campaign_files_data and claravine_stored),
            )
            if forward:
                st.session_state.cta_data = None
                st.session_state.current_step = 2
                st.rerun()

        render_footer()

    # ══════════════════════════════════════════════════════════════════════════
    #  Step 2 — Campaign Details
    # ══════════════════════════════════════════════════════════════════════════
    elif st.session_state.current_step == 2:
        _page_heading(
            "Step 2 of 4",
            "Campaign details",
            "Name this review so the report is easy to identify. The other details are optional.",
        )
        with st.container(border=True):
            left, right = st.columns(2)
            with left:
                campaign_name = st.text_input("Campaign name *", value=st.session_state.campaign_name, placeholder="Enter a campaign name")
                indication = st.text_input("Indication", value=st.session_state.indication, placeholder="Optional")
            with right:
                brand_name = st.text_input("Brand / product", value=st.session_state.brand_name, placeholder="Optional")
                audience = st.selectbox(
                    "Target audience",
                    AUDIENCE_OPTIONS,
                    index=AUDIENCE_OPTIONS.index(st.session_state.audience or ""),
                    format_func=lambda option: option or "Not specified",
                )
        back, forward = _nav_row("Back", "Continue", next_disabled=not campaign_name.strip())
        if back or forward:
            st.session_state.campaign_name = campaign_name.strip()
            st.session_state.brand_name = brand_name
            st.session_state.indication = indication
            st.session_state.audience = audience
            st.session_state.current_step = 1 if back else 3
            st.rerun()
        render_footer()

    elif st.session_state.current_step == 3:
        with st.container():
            _page_heading(
                "Step 3 of 4",
                "Review and confirm",
                "Check the campaign details, files and column mapping before validation starts.",
            )
            st.markdown(
                '<div class="card"><dl class="summary-grid">'
                f"<div><dt>Campaign</dt>{_summary_value(st.session_state.campaign_name)}</div>"
                f"<div><dt>Brand / product</dt>{_summary_value(st.session_state.brand_name)}</div>"
                f"<div><dt>Indication</dt>{_summary_value(st.session_state.indication)}</div>"
                f"<div><dt>Target audience</dt>{_summary_value(st.session_state.audience)}</div>"
                "</dl></div>",
                unsafe_allow_html=True,
            )

            inputs_ready = render_input_review()

            back, forward = _nav_row(
                "Back",
                "Start validation",
                next_disabled=not (inputs_ready and st.session_state.campaign_name),
            )
            if back:
                st.session_state.current_step = 2
                st.rerun()
            if forward:
                # Mapping may have changed since a previous run.
                st.session_state.pop("cta_data_by_csv", None)
                st.session_state.current_step = 4
                st.rerun()

        render_footer()

    # ══════════════════════════════════════════════════════════════════════════
    #  Step 4 — Validation Results
    # ══════════════════════════════════════════════════════════════════════════
    elif st.session_state.current_step == 4:

        with st.container():

            # ── Progress animation + run validation ───────────────────────
            if not st.session_state.get("cta_data_by_csv"):

                _page_heading(
                    "Step 4 of 4",
                    "Validating your campaign",
                    "CTA Sync is extracting CTAs, resolving tracking links and comparing them with Claravine.",
                )
                with st.status("Running validation…", expanded=True) as status:
                    st.write("Extracting CTAs from campaign assets")
                    st.write("Resolving tracking and landing-page URLs")
                    st.write(f"Matching against {len(st.session_state.csv_dfs)} Claravine file(s)")
                    started = time.time()
                    st.session_state.cta_data_by_csv = generate_cta_data_multi(
                        st.session_state.campaign_files_data,
                        st.session_state.csv_dfs,
                        st.session_state.col_name,
                        st.session_state.col_url,
                        st.session_state.col_lp,
                    )
                    st.session_state.validation_time = round(time.time() - started, 2)
                    status.update(label="Validation complete", state="complete")
                st.rerun()

            # ── Display results ───────────────────────────────────────────
            else:
                results_by_csv = st.session_state.cta_data_by_csv

                csv_names = list(results_by_csv.keys())
                if len(csv_names) > 1:
                    summary_bits = []
                    for n in csv_names:
                        rs = results_by_csv[n]
                        p = sum(1 for r in rs if r.get("status") == "passed")
                        f = sum(
                            1 for r in rs if r.get("status") in ("failed", "missing")
                        )
                        summary_bits.append(f"<b>{escape(n)}</b>: {p} passed, {f} failed")
                    st.markdown(
                        '<div class="alert-info">Validated against '
                        f"{len(csv_names)} Claravine files &middot; "
                        + " &nbsp;|&nbsp; ".join(summary_bits)
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                    selected_csv = st.selectbox(
                        "Claravine reference",
                        csv_names,
                        key="selected_claravine_csv",
                    )
                else:
                    selected_csv = csv_names[0]

                cta_data = results_by_csv[selected_csv]

                # CHANGE 3: sync checkbox state from widget keys back into cta_data
                # so counts always reflect current checked state
                for c in cta_data:
                    widget_key = f"cta_{c.get('id', c['text'][:20])}"
                    if widget_key in st.session_state:
                        c["checked"] = st.session_state[widget_key]

                total = len(cta_data)
                # FIX 2: waived counts as failed
                waived = sum(1 for c in cta_data if not c.get("checked", True))
                active = [c for c in cta_data if c.get("checked", True)]
                passed = sum(1 for c in active if c["status"] == "passed")
                warnings = sum(1 for c in active if c["status"] == "warning")
                failed = (
                    sum(1 for c in active if c["status"] in ("failed", "missing"))
                    + waived
                )
                quality_score = (
                    int((((passed * 1) + (warnings * 0.5)) / total) * 100)
                    if total > 0
                    else 0
                )

                campaign_name = st.session_state.get(
                    "campaign_name", "Campaign Validation"
                )
                val_time = st.session_state.get("validation_time", None)
                time_str = f"{val_time:.1f}s" if val_time is not None else "—"
                pass_rate = round(passed / total * 100) if total else 0
                meta = [
                    st.session_state.get("brand_name"),
                    st.session_state.get("audience"),
                    f"{total} CTAs checked",
                    f"Completed in {time_str}",
                    datetime.now().strftime("%d %b %Y"),
                ]
                st.markdown(
                    '<section class="report-head"><div><div class="eyebrow">Step 4 of 4 &middot; Validation report</div>'
                    f"<h1>{escape(campaign_name)}</h1><div class=\"report-meta\">"
                    + "".join(f"<span>{escape(m)}</span>" for m in meta if m)
                    + "</div></div>"
                    f'<div class="report-score"><div class="value">{pass_rate}%</div>'
                    '<div class="label">of CTAs passed all checks</div>'
                    f'<div class="score-track"><div class="score-fill" style="width:{pass_rate}%"></div></div>'
                    "</div></section>"
                    '<div class="stat-row">'
                    f'<div class="stat total"><span>Total CTAs</span><strong>{total}</strong></div>'
                    f'<div class="stat ok"><span>Passed</span><strong>{passed}</strong></div>'
                    f'<div class="stat warn"><span>Warnings</span><strong>{warnings}</strong></div>'
                    f'<div class="stat bad"><span>Failed or waived</span><strong>{failed}</strong></div>'
                    "</div>",
                    unsafe_allow_html=True,
                )

                st.markdown(
                    '<div class="page-head"><h2>Findings</h2>'
                    "<p>Review each finding and its suggested fix. Untick a row in the Export column to leave it out of the report.</p></div>",
                    unsafe_allow_html=True,
                )
                filter_labels = {
                    "all": f"All {total}",
                    "passed": f"Passed {passed}",
                    "warning": f"Warnings {warnings}",
                    "failed": f"Failed {failed}",
                }
                if "results_filter" not in st.session_state:
                    st.session_state.results_filter = st.session_state.filter
                st.session_state.filter = (
                    st.segmented_control(
                        "Show",
                        list(filter_labels),
                        format_func=filter_labels.get,
                        key="results_filter",
                        label_visibility="collapsed",
                    )
                    or "all"
                )

                # ── CTA scrollable table ──────────────────────────────────
                source_column, search_column = st.columns([1, 2])
                sources = list(dict.fromkeys(c.get("source", "") for c in cta_data if c.get("source")))
                with source_column:
                    selected_source = st.selectbox("Campaign asset", ["All campaign assets", *sources], key="results_source")
                with search_column:
                    query = st.text_input("Search findings", placeholder="CTA name, URL, or issue", key="results_search").strip().lower()

                chosen = st.session_state.filter
                if chosen == "all":
                    filtered_ctas = cta_data
                elif chosen == "failed":
                    filtered_ctas = [
                        c
                        for c in cta_data
                        if c["status"] in ("failed", "missing")
                        or not c.get("checked", True)
                    ]
                else:
                    filtered_ctas = [
                        c
                        for c in cta_data
                        if c["status"] == chosen and c.get("checked", True)
                    ]

                if selected_source != "All campaign assets":
                    filtered_ctas = [c for c in filtered_ctas if c.get("source") == selected_source]
                if query:
                    filtered_ctas = [c for c in filtered_ctas if query in " ".join(str(c.get(k, "")) for k in ("text", "url", "issues", "matched_name")).lower()]

                def display_status(c):
                    if not c.get("checked", True):
                        return "✕ Waived"
                    return STATUS_LABELS.get(c["status"], "—")

                if filtered_ctas:

                    def esc(v, limit=None):
                        s = str(v) if v is not None else "—"
                        if limit:
                            s = s[:limit]
                        return s

                    # ── Build flat list for data_editor ──────────────────────
                    def _format_issues_for_cell(cta: dict) -> str:
                        issue_list = cta.get("issues", [])
                        if not issue_list:
                            return (
                                cta["pass_reason"]
                                if cta.get("pass_reason")
                                else "—"
                            )

                        prefix_multiple = len(issue_list) > 1
                        lines = []
                        for index, raw in enumerate(issue_list, 1):
                            if isinstance(raw, dict):
                                reason = (raw.get("reason") or "").strip()
                                fix = (raw.get("fix") or "").strip()
                            else:
                                reason, fix = str(raw).strip(), ""
                            label = f"{index}. " if prefix_multiple else ""
                            lines.append(f"{label}{reason}")
                            if fix:
                                lines.append(f"   Fix: {fix}")
                        return "\n".join(lines)

                    table_rows = []
                    for cta in filtered_ctas:
                        issues_str = _format_issues_for_cell(cta)

                        table_rows.append(
                            {
                                "Export": True,  # ← checkbox column
                                "CTA Text": esc(cta["text"], 80),
                                "URL": esc(cta["url"]),
                                "CSV Match": esc(cta.get("matched_name", "—"))
                                + " (via "
                                + esc(cta.get("matched_by", "—"))
                                + ")",
                                "Source File": esc(cta.get("source", "—")),
                                "Reason & Fix": issues_str,
                                "Status": display_status(cta),
                                "_cta_ref": cta,  # hidden ref, dropped before display
                            }
                        )

                    display_df = pd.DataFrame(table_rows).drop(columns=["_cta_ref"])

                    edited_df = st.data_editor(
                        display_df,
                        use_container_width=True,
                        height=520,  # scrollable
                        hide_index=True,
                        row_height=92,
                        column_config={
                            "Export": st.column_config.CheckboxColumn(
                                "Export",
                                help="Check to include this row in the Excel export",
                                default=True,
                                width="small",
                            ),
                            "CTA Text": st.column_config.TextColumn(
                                "CTA Text", width="medium", disabled=True
                            ),
                            "URL": st.column_config.TextColumn(
                                "URL", width="medium", disabled=True
                            ),
                            "CSV Match": st.column_config.TextColumn(
                                "CSV Match", width="medium", disabled=True
                            ),
                            "Source File": st.column_config.TextColumn(
                                "Source File", width="medium", disabled=True
                            ),
                            "Reason & Fix": st.column_config.TextColumn(
                                "Reason & Fix",
                                width="large",
                                disabled=True,
                                help=(
                                    "Each numbered line is one issue, with its "
                                    "suggested fix on the next line."
                                ),
                            ),
                            "Status": st.column_config.TextColumn(
                                "Status", width="small", disabled=True
                            ),
                        },
                        disabled=[
                            "CTA Text",
                            "URL",
                            "CSV Match",
                            "Source File",
                            "Reason & Fix",
                            "Status",
                        ],
                    )

                    # ── Store checked rows back into session_state for export ─
                    selected_mask = edited_df["Export"] == True
                    st.session_state["export_selected_ctas"] = [
                        table_rows[i]["_cta_ref"]
                        for i in edited_df[selected_mask].index
                    ]

                    sel_count = selected_mask.sum()
                    total_count = len(filtered_ctas)
                    st.caption(
                        f"{sel_count} of {total_count} rows selected for export"
                    )

                else:
                    st.session_state["export_selected_ctas"] = []
                    st.info("No CTAs match this filter.")

                # ─── ACTION BUTTONS ───────────────────────────────────────────
                col1, _, col2 = st.columns([1, 1, 1])

                with col1:
                    if st.button(
                            "Start a new validation",
                            type="secondary",
                            use_container_width=True,
                    ):
                        keys_to_clear = [
                            "current_step",
                            "campaign_name",
                            "brand_name",
                            "indication",
                            "audience",
                            "campaign_files",
                            "claravine_file",
                            "cta_data",
                            "cta_data_by_csv",
                            "selected_claravine_csv",
                            "filter",
                            "results_filter",
                            "results_source",
                            "results_search",
                            "campaign_id",
                            "html_ctas",
                            "claravine_data",
                            "res_df",
                            "csv_df",
                            "csv_dfs",
                            "col_name",
                            "col_url",
                            "col_lp",
                            "name_col",
                            "url_col",
                            "lp_col",
                            "campaign_files_data",
                            "claravine_files_data",
                            "claravine_file_data",
                            "claravine_file_name",
                            "claravine_file_size",
                            "export_selected_ctas",
                        ]
                        for k in keys_to_clear:
                            st.session_state.pop(k, None)
                        st.session_state.campaign_uploader_key = (
                            st.session_state.get("campaign_uploader_key", 0) + 1
                        )
                        st.session_state.claravine_uploader_key = (
                            st.session_state.get("claravine_uploader_key", 0) + 1
                        )
                        st.rerun()

                with col2:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_name = campaign_name.replace(" ", "_")

                    active_csv_df = st.session_state.get("csv_dfs", {}).get(
                        selected_csv
                    )
                    if active_csv_df is not None:
                        qa_buffer, qa_email_name = build_qa_workbook(
                            st.session_state.campaign_files_data,
                            active_csv_df,
                            st.session_state.get("export_selected_ctas", cta_data),
                            st.session_state.get("col_name", ""),
                            campaign_name=campaign_name
                        )
                        download_name = (
                            f"Claravine QA Report - {qa_email_name}.xlsx"
                            if qa_email_name
                            else f"Claravine_QA_{safe_name}_{timestamp}.xlsx"
                        )
                        st.download_button(
                            label="Export QA report (.xlsx)",
                            data=qa_buffer,
                            file_name=download_name,
                            mime=(
                                "application/vnd.openxmlformats-officedocument."
                                "spreadsheetml.sheet"
                            ),
                            type="primary",
                            use_container_width=True
                        )
                    else:
                        st.warning(
                            "No rows selected. Tick at least one row in the table above."
                        )

                st.caption("Review required: a matching result does not establish that the Claravine reference itself is correct.")
                render_footer()