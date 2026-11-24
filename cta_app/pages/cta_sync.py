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
from cta_app.components.branding import ASSETS
from cta_app.core.assets import get_base64_image, resolve_asset_path
from cta_app.core.config import SESSION_DEFAULTS
from cta_app.domain.columns import find_column, render_column_mapping
from cta_app.domain.cta_matching import extract_campaign_ctas
from cta_app.domain.validation import generate_cta_data, generate_cta_data_multi
from cta_app.services.qa_export import build_qa_workbook
from cta_app.ui.styles import render_cta_sync_styles

AUDIENCE_OPTIONS = ["", "Healthcare Professionals", "Patients", "Caregivers"]


def render_cta_sync_page():
    render_cta_sync_styles()

    for key, value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value

    hero_logo = get_base64_image(str(ASSETS / "cta_sync.png"))
    st.markdown(
        '<section class="workspace-hero workspace-hero-branded"><div class="hero-copy">'
        '<div class="eyebrow">CTA Sync &middot; Campaign quality workspace</div>'
        '<h1>Every CTA. Checked.</h1>'
        '<p>Bring your campaign assets and Claravine tracking together. '
        'Review links, resolve findings, and export a clear QA report.</p></div>'
        f'<img class="hero-product-logo" src="data:image/png;base64,{hero_logo}" '
        'alt="CTA Sync - Campaign CTA Validation Platform"></section>',
        unsafe_allow_html=True,
    )

    render_progress_bar()

    # ══════════════════════════════════════════════════════════════════════════
    #  Step 1 — Upload
    # ══════════════════════════════════════════════════════════════════════════
    if st.session_state.current_step == 1:
        with st.container():
            st.markdown(
                '<h2 style="color: black; margin-top: 0;"><b>Upload Campaign Assets</b></h2>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="alert-info">📁 Start with your campaign assets and the matching Claravine CSV. You can add multiple files to each panel.</div>',
                unsafe_allow_html=True,
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
                    st.warning("Could not read csv file format.")

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
                            st.warning(
                                "⚠️ Multiple campaign names found in CSV. Please select one:"
                            )
                            chosen = st.selectbox(
                                "Select Campaign Name",
                                options=campaign_values,
                                key="campaign_name_selector",
                            )
                            st.session_state.campaign_name = chosen

                    else:
                        st.warning(
                            "⚠️ No 'campaign name' column (or variant like "
                            "'campaign name -gsk') found in uploaded CSV."
                        )

            if st.session_state.campaign_files_data and claravine_stored:
                col1, col2, col3 = st.columns([2, 1, 1])
                with col3:
                    if st.button(
                        "Next Step →", use_container_width=True, type="primary"
                    ):
                        st.session_state.cta_data = None
                        st.session_state.current_step = 2
                        st.rerun()

        st.markdown('<div class="footer-wrap">', unsafe_allow_html=True)
        render_footer()
        st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  Step 2 — Campaign Details
    # ══════════════════════════════════════════════════════════════════════════
    elif st.session_state.current_step == 2:
        with st.container():
            with st.form("campaign_info_form"):
                st.markdown(
                    '<div class="alert-info">Campaign Name is required. Other '
                    'fields are optional but recommended for better '
                    'tracking.</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<h2 style='color:black;'>Campaign Information</h2>",
                    unsafe_allow_html=True,
                )

                col1, col2 = st.columns(2)
                with col1:
                    campaign_name = st.text_input(
                        "Campaign Name * (Required)",
                        value=st.session_state.campaign_name,
                        placeholder="Q4 2025 Brand Awareness",
                    )
                    indication = st.text_input(
                        "Indication (Optional)",
                        value=st.session_state.indication,
                        placeholder="Type 2 Diabetes",
                    )
                with col2:
                    brand_name = st.text_input(
                        "Brand/Product (Optional)",
                        value=st.session_state.brand_name,
                        placeholder="BrandName™",
                    )
                    audience = st.selectbox(
                        "Target Audience (Optional)",
                        AUDIENCE_OPTIONS,
                        index=AUDIENCE_OPTIONS.index(st.session_state.audience or ""),
                    )

                if audience:
                    st.info(f"Active Campaign Target: **{audience}**")

                st.form_submit_button("Save Campaign Info")

            col1, col2, col3 = st.columns([1, 2, 1])
            if col1.button("← Previous", type="primary"):
                st.session_state.current_step = 1
                st.rerun()
            with col3:
                if st.button(
                    "Next Step →",
                    type="primary",
                    key="btn_next_step",
                    disabled=not campaign_name,
                    use_container_width=True,
                ):
                    st.session_state.campaign_name = campaign_name
                    st.session_state.brand_name = brand_name
                    st.session_state.indication = indication
                    st.session_state.audience = audience
                    st.session_state.current_step = 3
                    st.rerun()

        render_footer()
    # ══════════════════════════════════════════════════════════════════════════
    #  Step 3 — Campaign Summary + Column Mapping
    # ══════════════════════════════════════════════════════════════════════════
    elif st.session_state.current_step == 3:
        with st.container():
            st.markdown("## Review Campaign Summary")
            st.caption("Edit any detail below; changes are saved automatically.")
            col1, col2 = st.columns(2)
            # Separate widget keys: Streamlit drops widget state when a step
            # stops rendering it, which would wipe the shared session values.
            with col1:
                st.session_state.campaign_name = st.text_input(
                    "Campaign Name * (Required)",
                    value=st.session_state.campaign_name,
                    key="review_campaign_name",
                ).strip()
                st.session_state.indication = st.text_input(
                    "Indication (Optional)",
                    value=st.session_state.indication,
                    key="review_indication",
                )
            with col2:
                st.session_state.brand_name = st.text_input(
                    "Brand/Product (Optional)",
                    value=st.session_state.brand_name,
                    key="review_brand_name",
                )
                st.session_state.audience = st.selectbox(
                    "Target Audience (Optional)",
                    AUDIENCE_OPTIONS,
                    index=AUDIENCE_OPTIONS.index(st.session_state.audience or ""),
                    key="review_audience",
                )
            if not st.session_state.campaign_name:
                st.error("❌ Campaign Name is required.")

            st.divider()

            campaign_files = st.session_state.get("campaign_files_data") or {}
            claravine_files = st.session_state.get("claravine_files_data") or {}

            # Parse every uploaded Claravine CSV into its own dataframe.
            # Columns are mapped from the FIRST file; we assume all
            # Claravine files share the same template (typical per campaign).
            if claravine_files and "csv_dfs" not in st.session_state:
                parsed: dict = {}
                for csv_name, raw_bytes in claravine_files.items():
                    df = pd.read_csv(io.BytesIO(raw_bytes))
                    df.columns = df.columns.str.strip()
                    parsed[csv_name] = df
                st.session_state.csv_dfs = parsed
            csv_dfs = st.session_state.get("csv_dfs") or {}

            st.markdown("### Files to Validate")
            m1, m2, m3 = st.columns(3)
            m1.metric("Campaign files", len(campaign_files))
            m2.metric("Claravine files", len(csv_dfs))
            m3.metric("Claravine tracking rows", sum(len(df) for df in csv_dfs.values()))

            files_col, csv_col = st.columns(2)
            with files_col:
                st.markdown("**Campaign assets**")
                for name, data in campaign_files.items():
                    st.markdown(f"- {escape(name)} ({len(data) / 1024:.1f} KB)")
            with csv_col:
                st.markdown("**Claravine files**")
                for name, df in csv_dfs.items():
                    st.markdown(f"- {escape(name)} ({len(df)} rows)")

            if csv_dfs:
                st.divider()
                first_df = next(iter(csv_dfs.values()))
                render_column_mapping(first_df)

                mapped = [
                    st.session_state.col_name,
                    st.session_state.col_url,
                    st.session_state.col_lp,
                ]
                if len(set(mapped)) < len(mapped):
                    st.warning(
                        "⚠️ The same column is mapped more than once. Check the "
                        "mapping before starting validation."
                    )
                for csv_name, df in csv_dfs.items():
                    missing_cols = [c for c in mapped if c not in df.columns]
                    if missing_cols:
                        st.error(
                            f"❌ '{csv_name}' is missing mapped column(s): "
                            f"{', '.join(missing_cols)}. All Claravine files must "
                            "share the same columns."
                        )

                with st.expander("Preview Claravine data (first 5 rows)"):
                    st.dataframe(
                        first_df[list(dict.fromkeys(mapped))].head(5),
                        use_container_width=True,
                        hide_index=True,
                    )

                st.markdown(
                    '<div class="alert-success">✓ Ready to validate! CTA Sync will '
                    f"check every CTA in {len(campaign_files)} campaign file(s) "
                    f"against {len(csv_dfs)} Claravine file(s).</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.warning(
                    "⚠️ No Claravine CSV found. Please go back to Step 1 and "
                    "upload one or more."
                )

            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.button(
                        "← Previous",
                        use_container_width=True,
                        type="primary",
                ):
                    st.session_state.current_step = 2
                    st.rerun()
            with col3:
                # Only allow proceeding if at least one CSV is uploaded and
                # columns mapped
                can_proceed = (
                    bool(st.session_state.campaign_name)
                    and bool(csv_dfs)
                    and bool(campaign_files)
                    and st.session_state.get("col_name") is not None
                    and all(
                        c in df.columns
                        for df in csv_dfs.values()
                        for c in (
                            st.session_state.col_name,
                            st.session_state.col_url,
                            st.session_state.col_lp,
                        )
                    )
                )
                if st.button(
                    "Start Validation →",
                    type="primary",
                    use_container_width=True,
                    disabled=not can_proceed,
                ):
                    # Mapping may have changed since a previous run.
                    st.session_state.pop("cta_data_by_csv", None)
                    st.session_state.current_step = 4
                    st.rerun()

        st.markdown('<div class="footer-wrap">', unsafe_allow_html=True)
        render_footer()
        st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  Step 4 — Validation Results
    # ══════════════════════════════════════════════════════════════════════════
    elif st.session_state.current_step == 4:

        with st.container():

            # ── Progress animation + run validation ───────────────────────
            if not st.session_state.get("cta_data_by_csv"):

                st.markdown("## AI-Powered Validation in Progress")
                stages = [
                    "Extracting CTAs from HTML templates...",
                    "Parsing Claravine tracking URLs...",
                    "Matching against each Claravine file...",
                    "Checking URL parameter compliance...",
                ]
                progress_bar = st.progress(0)
                status_text = st.empty()
                _val_start = time.time()

                for idx, stage in enumerate(stages):
                    status_text.markdown(f"### {stage}")
                    progress_bar.progress(int(((idx + 1) / len(stages)) * 0.8 * 100))
                    time.sleep(0.5)

                status_text.markdown(
                    "### Resolving tracking URLs and matching against Claravine..."
                )
                progress_bar.progress(90)
                with st.spinner("This can take a mooment for campaigns with many CTAs..."):
                    st.session_state.cta_data_by_csv = generate_cta_data_multi(
                        st.session_state.campaign_files_data,
                        st.session_state.csv_dfs,
                        st.session_state.col_name,
                        st.session_state.col_url,
                        st.session_state.col_lp,
                    )
                progress_bar.progress(100)
                status_text.markdown("### Validation Complete")
                time.sleep(0.3)
                st.session_state.validation_time = round(time.time() - _val_start, 2)
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
                        summary_bits.append(f"**{n}** — {p} ✓ / {f} ✗")
                    st.markdown(
                        '<div class="alert-info">Validated against '
                        f"{len(csv_names)} Claravine files: "
                        + " &nbsp;|&nbsp; ".join(summary_bits)
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                    selected_csv = st.selectbox(
                        "Showing results for Claravine file:",
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
                time_str = f"{val_time:.2f}s" if val_time is not None else "—"
                st.markdown(
                    '<section class="workspace-hero"><div class="eyebrow">CTA Sync &middot; Validation report</div>'
                    f'<h1>{escape(campaign_name)}</h1>'
                    f'<p>{total} CTAs reviewed ? Completed in {time_str}</p></section>',
                    unsafe_allow_html=True,
                )
                for column, label, value in zip(
                    st.columns(4),
                    ["Total CTAs", "Passed", "Warnings", "Failed / waived"],
                    [total, passed, warnings, failed],
                ):
                    with column:
                        st.metric(label, value)

                #  Quality score
                # if quality_score >= 95:
                #     quality_msg = "Excellent! Your campaign is ready for launch! 🎉"
                # elif quality_score >= 85:
                #     quality_msg = "Good quality. Review warnings before launch."
                # elif quality_score >= 70:
                #     quality_msg = "Needs attention. Please fix failed CTAs."
                # else:
                #     quality_msg = (
                #         "Critical issues found. Review and fix before proceeding."
                #     )
                # st.markdown(
                #     f'<div class="alert-info"><strong>Quality Score: {quality_score}/100</strong>'
                #     f"<br>{quality_msg}</div>",
                #     unsafe_allow_html=True,
                # )

                # ── Filter buttons ────────────────────────────────────────
                st.markdown("## Detected CTAs — Review & Validate")
                st.caption("Review each finding and its suggested fix. Use the Export column to select rows for export.")

                fc1, fc2, fc3, fc4 = st.columns(4)
                filter_buttons = [
                    (fc1, f"All ({total})", "all"),
                    (fc2, f"✓ Passed ({passed})", "passed"),
                    (fc3, f"Warnings ({warnings})", "warning"),
                    (fc4, f"✗ Failed ({failed})", "failed"),
                ]
                for col, label, key in filter_buttons:
                    with col:
                        btn_type = (
                            "primary" if st.session_state.filter == key else "secondary"
                        )
                        if st.button(
                            label,
                            use_container_width=True,
                            type=btn_type,
                            key=f"flt_{key}",
                        ):
                            st.session_state.filter = key
                            st.rerun()

                # ── CTA scrollable table ──────────────────────────────────
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

                def display_status(c):
                    if not c.get("checked", True):
                        return "❌ Waived / Failed"
                    m = {
                        "passed": "✅ Passed",
                        "warning": "⚠️ Warning",
                        "failed": "❌ Failed",
                        "missing": "🔍 Missing",
                    }
                    return m.get(c["status"], "—")

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
                                "✓ " + cta["pass_reason"]
                                if cta.get("pass_reason")
                                else "—"
                            )

                        status = cta.get("status", "failed")
                        icon = (
                            "⚠️"
                            if status == "warning"
                            else "🔎"
                            if status == "missing"
                            else "❌"
                        )
                        prefix_multiple = len(issue_list) > 1
                        lines = []
                        for index, raw in enumerate(issue_list, 1):
                            if isinstance(raw, dict):
                                reason = (raw.get("reason") or "").strip()
                                fix = (raw.get("fix") or "").strip()
                            else:
                                reason, fix = str(raw).strip(), ""
                            label = f"({index}) " if prefix_multiple else ""
                            lines.append(f"{label}{icon} {reason}")
                            if fix:
                                lines.append(f"   🔧 Fix: {fix}")
                        return "\n".join(lines)

                    table_rows = []
                    for cta in filtered_ctas:
                        issues_str = _format_issues_for_cell(cta)

                        table_rows.append(
                            {
                                "Export": True,  # ← checkbox column
                                "CTA Text": esc(cta["text"], 80),
                                "URL": esc(cta["url"], 120),
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

                    # ── Render interactive table with checkbox ────────────────
                    st.markdown(
                        "##### 📋 CTA Validation Results — check rows to "
                        "include in export"
                    )

                    edited_df = st.data_editor(
                        display_df,
                        use_container_width=True,
                        height=520,  # scrollable
                        hide_index=True,
                        row_height=110,
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
                                "URL", width="large", disabled=True
                            ),
                            "CSV Match": st.column_config.TextColumn(
                                "CSV Match", width="medium", disabled=True
                            ),
                            "Source File": st.column_config.TextColumn(
                                "Source File", width="small", disabled=True
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
                        f"✅ {sel_count} of {total_count} rows selected for export"
                    )

                else:
                    st.session_state["export_selected_ctas"] = []
                    st.info("No CTAs match this filter.")

                # ─── ACTION BUTTONS ───────────────────────────────────────────
                col1, col2, col3 = st.columns(3)

                with col1:
                    if st.button(
                            "🔄 Start New Validation",
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
                            label=f"📥 Export Claravine QA Report",
                            data=qa_buffer,
                            file_name=download_name,
                            mime=(
                                "application/vnd.openxmlformats-officedocument."
                                "spreadsheetml.sheet"
                            ),
                            use_container_width=True
                        )
                    else:
                        st.warning(
                            "⚠️ No rows selected — check at least one row in the table above."
                        )
                with col3:
                    active_ctas = [c for c in cta_data if c.get("checked", True)]
                    checked_count = len(active_ctas)
                    passed_checked = sum(
                        1 for c in active_ctas if c["status"] == "passed"
                    )
                    warnings_checked = sum(
                        1 for c in active_ctas if c["status"] == "warning"
                    )
                    failed_checked = sum(
                        1 for c in active_ctas if c["status"] in ("failed", "missing")
                    )
                    # waived_count = sum(1 for c in cta_data if not c.get("checked", True))

                    if st.button(
                        f"✅ Approve ", type="primary", use_container_width=True
                    ):
                        st.success(f"""✅ Report Generated!""")

                st.markdown('<div class="footer-wrap">', unsafe_allow_html=True)
                render_footer()
                st.markdown("</div>", unsafe_allow_html=True)