"""Shared Indegene visual system for every application page."""
import streamlit as st

CTA_SYNC_CSS = """
<style>
:root { --brand:#144da0; --cyan:#13b9df; --pink:#eb008b; --ink:#182b49; --muted:#63758c; --line:#dce5ef; }
.stApp { background:radial-gradient(ellipse at top right,#eaf5ff 0,transparent 45%),#f5f8fc; color:var(--ink); }
[data-testid="stHeader"] { background:rgba(245,248,252,.95); }
section[data-testid="stSidebar"] { display:none; }
[data-testid="stMainBlockContainer"] { max-width:1320px; padding:1.5rem 2.5rem 3rem; }
h1,h2,h3,h4,h5 { color:var(--ink); letter-spacing:-.025em; }
h1 { font-size:2.4rem !important; } h2 { font-size:1.65rem !important; }
p,label { line-height:1.6; }
a { color:var(--brand); }
[data-testid="stForm"], [data-testid="stExpander"] { background:white; border:1px solid var(--line); border-radius:16px; padding:24px; box-shadow:0 4px 18px #183c6810; }
[data-testid="stTextInput"] input, [data-testid="stSelectbox"] [data-baseweb="select"] > div { background:white; color:var(--ink); border-radius:9px; }
.stButton button, .stDownloadButton button, [data-testid="stFormSubmitButton"] button { border-radius:9px; min-height:42px; font-weight:600; transition:background .15s ease, box-shadow .15s ease; }
button[kind="primary"],button[kind="primaryFormSubmit"] { background:var(--brand); border:1px solid var(--brand); color:white; }
button[kind="primary"]:hover,button[kind="primaryFormSubmit"]:hover { background:#103e80; border-color:#103e80; }
button[kind="secondary"] { background:white; border:1px solid #c6d4e5; color:var(--brand); }
button:focus-visible,a:focus-visible { outline:3px solid var(--cyan) !important; outline-offset:3px; }
button:disabled { opacity:.5; }
.brand-header { display:flex; align-items:center; gap:24px; min-height:76px; flex-wrap:wrap; }
.indegene-brand { width:190px; height:auto; object-fit:contain; }
.brand-divider { width:1px; height:46px; background:var(--line); }
.cta-sync-brand { width:270px; max-width:100%; height:auto; border-radius:10px; }
@media(max-width:700px) { .brand-header { gap:12px; } .indegene-brand { width:140px; } .cta-sync-brand { width:230px; } .brand-divider { display:none; } }
.brand-rule { height:3px; background:linear-gradient(90deg,var(--brand) 0 72%,var(--cyan) 72% 92%,var(--pink) 92%); margin:10px 0 24px; border-radius:4px; }
.eyebrow { color:var(--brand); text-transform:uppercase; letter-spacing:.16em; font-size:11px; font-weight:700; margin-bottom:12px; }
.workspace-hero { background:linear-gradient(115deg,#ffffff 55%,#edf6ff); border:1px solid var(--line); border-radius:20px; padding:34px 38px; margin-bottom:20px; border-left:5px solid var(--cyan); box-shadow:0 8px 28px #144da008; }
.workspace-hero h1 { margin:0 0 6px; padding:0; } .workspace-hero p { color:var(--muted); margin:0; max-width:680px; }
.workspace-hero-branded { display:flex; align-items:center; justify-content:space-between; gap:32px; }
.hero-copy { flex:1; min-width:0; }
.hero-product-logo { width:340px; max-width:38%; height:auto; border-radius:14px; box-shadow:0 12px 24px #144da01c; }
@media(max-width:800px) { .workspace-hero-branded { flex-direction:column; align-items:flex-start; gap:20px; } .hero-product-logo { width:340px; max-width:100%; } }
.login-story { background:linear-gradient(140deg,#103c7c,#144da0); color:white; border-radius:22px; padding:48px 40px; min-height:390px; }
.login-story h1 { color:white; font-size:2.8rem !important; line-height:1.15; margin:20px 0; }
.login-story p { color:#e0edff; } .login-story .eyebrow { color:#75e1f8; }
.feature-list { margin-top:32px; display:grid; gap:15px; color:#e0edff; }
.feature-list span { border-top:1px solid #ffffff30; padding-top:12px; }
.file-info { background:#edf5fc; padding:12px 14px; border-radius:9px; margin:8px 0; border:1px solid #dae8f5; overflow-wrap:anywhere; }
.file-info-text { color:var(--ink); font-size:13px; }
[data-testid="stFileUploader"] section { background:white; border:1px dashed #8faaca; border-radius:14px; padding:22px; }
[data-testid="stFileUploader"] section:hover { border-color:var(--brand); background:#f0f7ff; }
[data-testid="stFileUploader"] button { background:white; color:var(--brand); border:1px solid #bdcee2; }
.content-box,.review-summary,.stat-card { background:white; padding:24px; border-radius:14px; border:1px solid var(--line); margin-bottom:18px; }
.stat-number { font-size:38px; font-weight:700; } .stat-label { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; }
.alert-info,.alert-warning,.alert-success { padding:14px 18px; border-radius:10px; margin:16px 0; font-size:14px; border:1px solid; }
.alert-info { background:#edf6fc; color:#174b78; border-color:#cce4f4; }
.alert-warning { background:#fff8e9; color:#79581b; border-color:#f2dfad; }
.alert-success { background:#edf8f2; color:#216547; border-color:#cce7da; }
.cta-passed,.cta-warning,.cta-failed { padding:20px; margin:14px 0; border-radius:12px; background:white; border:1px solid var(--line); border-left:4px solid; }
.cta-passed { border-left-color:#25835b; } .cta-warning { border-left-color:#c48a1d; } .cta-failed { border-left-color:#ce475d; }
.cta-title { font-weight:650; color:var(--ink); } .cta-url { font-family:monospace; overflow-wrap:anywhere; font-size:13px; background:#f2f6fa; padding:10px; border-radius:6px; color:#425a75; }
.cta-source { font-size:12px; color:var(--muted); } .cta-issues { padding:12px; background:#fff8e9; border-radius:8px; margin-top:12px; }
.workflow-steps { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin:0 0 28px; }
.workflow-step { padding:16px; border:1px solid var(--line); background:white; border-radius:12px; color:var(--muted); font-size:13px; }
.workflow-step strong { display:inline-flex; width:26px; height:26px; align-items:center; justify-content:center; background:#edf1f7; border-radius:50%; margin-right:8px; }
.workflow-step.active { border-color:var(--brand); color:var(--brand); background:#edf4ff; box-shadow:inset 0 -3px 0 var(--brand); }
.workflow-step.active strong { background:var(--brand); color:white; } .workflow-step.completed strong { background:#def3f9; color:#17617a; }
.app-footer { border-top:1px solid var(--line); margin-top:28px; padding-top:18px; color:var(--muted); font-size:12px; display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; }
[data-testid="stMetric"] { background:white; border:1px solid var(--line); border-radius:14px; padding:18px 22px; margin-bottom:20px; }
[data-testid="stMetricLabel"] { color:var(--muted); }
[data-testid="stMetricValue"] { color:var(--brand); }
[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; }
@media(max-width:700px) { [data-testid="stMainBlockContainer"] { padding:1rem; } .workspace-hero,.login-story { padding:24px; } .workflow-steps { grid-template-columns:repeat(2,1fr); } .workflow-step { padding:10px; } h1 { font-size:1.9rem !important; } }
/* Native Streamlit containers keep controls and their card backgrounds together. */
[data-testid="stVerticalBlockBorderWrapper"] > div { border-radius:16px; }
[data-testid="stVerticalBlockBorderWrapper"]:has(.upload-heading) { background:#fff; border-radius:16px; box-shadow:0 4px 20px #183c6808; }
.upload-heading { display:flex; align-items:center; gap:12px; margin:0 0 10px; }
.upload-icon { display:flex; align-items:center; justify-content:center; width:42px; height:42px; flex-shrink:0; background:#edf4ff; color:var(--brand); border-radius:12px; font-size:12px; font-weight:800; letter-spacing:.04em; }
.upload-icon.reference { background:#fff0f8; color:#a60061; }
.upload-heading h3 { font-size:1.05rem; margin:0; padding:0; }
.upload-heading p { margin:2px 0 0; color:var(--muted); font-size:12px; }
[data-testid="stFileUploader"] section { min-height:120px; background:#f8fbff; }
[data-testid="stFileUploader"] section small { color:#63758c; }
.workflow-step small { display:block; padding-left:38px; margin-top:4px; color:var(--muted); font-size:11px; }
.workflow-status { color:var(--muted); font-size:12px; margin:0 0 10px; letter-spacing:.02em; }
[data-testid="stMetric"] { border-top:3px solid var(--cyan); box-shadow:0 4px 16px #183c6808; }
.stButton button:hover, .stDownloadButton button:hover { box-shadow:0 3px 10px #144da018; }
@media(prefers-reduced-motion:reduce) { .stButton button,.stDownloadButton button { transition:none; } }
@media(max-width:700px) { .workspace-hero-branded { padding:24px; } .workflow-step small { padding-left:0; } }
</style>
"""

def render_cta_sync_styles() -> None:
    st.markdown(CTA_SYNC_CSS, unsafe_allow_html=True)
