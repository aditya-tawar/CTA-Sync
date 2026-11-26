from html import escape
import streamlit as st
from cta_app.domain.cta_matching import ACCEPTED_CAMPAIGN_TYPES


def render_file_uploader():
    # ── Session-state defaults ────────────────────────────────────────
    # Must come BEFORE any widget or callback that reads these keys
    if "campaign_files_data" not in st.session_state:
        st.session_state.campaign_files_data = {}   # {filename: bytes}
    if "claravine_files_data" not in st.session_state:
        st.session_state.claravine_files_data = {}  # {filename: bytes}
    if "campaign_uploader_key" not in st.session_state:
        st.session_state.campaign_uploader_key = 0
    if "claravine_uploader_key" not in st.session_state:
        st.session_state.claravine_uploader_key = 0

    # ── Removal callback – campaign files ────────────────────────────
    # FIX: Always bump campaign_uploader_key (not only when last file removed)
    # so the widget fully resets and cannot re-add the removed file on next rerun.
    def remove_campaign(filename: str):
        st.session_state.campaign_files_data.pop(filename, None)
        st.session_state.html_ctas = [
            cta for cta in st.session_state.get("html_ctas", [])
            if cta.get("source") != filename
        ]
        st.session_state.campaign_uploader_key += 1
        st.toast(f"Removed {filename}", icon="✅")



    # ═════════════════════════════════════════════════════════════════
    #  Upload columns
    # ═════════════════════════════════════════════════════════════════
    upcol1, upcol2 = st.columns(2)

    # ─────────────────────────────────────────────────────────────────
    #  Left column – HTML campaign files
    # ─────────────────────────────────────────────────────────────────
    with upcol1, st.container(border=True):
        st.markdown('<div class="upload-heading"><div class="eyebrow">01 &middot; Campaign</div><h3>Campaign assets</h3><p>Upload one or more HTML, HTM or EML files.</p></div>', unsafe_allow_html=True)
        campaign_files = st.file_uploader(
            "Campaign files", label_visibility="collapsed", accept_multiple_files=True, type=ACCEPTED_CAMPAIGN_TYPES,
            key=f"campaign_up_{st.session_state.campaign_uploader_key}",
        )
        st.session_state.campaign_files = campaign_files

        # FIX: Only ADD new files — never wipe campaign_files_data based on
        # widget state. After a key bump the widget is empty but stored files
        # should remain until explicitly removed via the Remove button.
        if campaign_files:
            for f in campaign_files:
                if f.name not in st.session_state.campaign_files_data:
                    f.seek(0)
                    st.session_state.campaign_files_data[f.name] = f.read()

        # Display stored files with Remove buttons
        if st.session_state.campaign_files_data:
            for filename in list(st.session_state.campaign_files_data.keys()):
                c1, c2 = st.columns([3, 1])
                size = len(st.session_state.campaign_files_data[filename])
                with c1:
                    st.markdown(
                        f'<div class="file-info">'
                        f'<span class="file-info-text"><b>{escape(filename)}</b> ({size / 1024:.1f} KB)</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with c2:
                    st.button(
                        "Remove",
                        key=f"remove_campaign_{filename}",
                        on_click=remove_campaign,
                        args=(filename,),type='secondary'
                    )

        st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────
    #  Right column – Claravine CSV
    # ─────────────────────────────────────────────────────────────────
    def remove_claravine(filename: str):
        st.session_state.claravine_files_data.pop(filename, None)
        st.session_state.pop("csv_dfs", None)
        st.session_state.pop("cta_data_by_csv", None)
        st.session_state.claravine_uploader_key += 1
        st.toast(f"Removed {filename}", icon="✅")

    with upcol2, st.container(border=True):
        st.markdown('<div class="upload-heading"><div class="eyebrow">02 &middot; Reference</div><h3>Claravine tracking sheets</h3><p>Upload one or more Claravine CSV files.</p></div>', unsafe_allow_html=True)
        claravine_files = st.file_uploader(
            "Claravine CSV files", label_visibility="collapsed", type=["csv"], accept_multiple_files=True,
            key=f"claravine_up_{st.session_state.claravine_uploader_key}",
        )

        st.session_state.claravine_file = claravine_files

        # Append-only: keep previously stored files even after widget reset.
        if claravine_files:
            for f in claravine_files:
                if f.name not in st.session_state.claravine_files_data:
                    f.seek(0)
                    st.session_state.claravine_files_data[f.name] = f.read()
                    # Any new CSV invalidates cached parses / results.
                    st.session_state.pop("csv_dfs", None)
                    st.session_state.pop("cta_data_by_csv", None)

        claravine_stored = bool(st.session_state.claravine_files_data)

        if claravine_stored:
            for filename in list(st.session_state.claravine_files_data.keys()):
                size = len(st.session_state.claravine_files_data[filename])
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(
                        f'<div class="file-info">'
                        f'<span class="file-info-text">'
                        f'<b>{escape(filename)}</b> ({size / 1024:.1f} KB)</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with c2:
                    st.button(
                        "Remove",
                        key=f"remove_claravine_{filename}",
                        on_click=remove_claravine,
                        args=(filename,),
                        type='secondary',
                    )

    if not claravine_stored or not st.session_state.campaign_files_data:
        st.caption("To continue, add at least one campaign asset and one Claravine CSV.")
    else:
        st.caption(f"Ready for review: {len(st.session_state.campaign_files_data)} campaign asset(s) and {len(st.session_state.claravine_files_data)} reference file(s).")
