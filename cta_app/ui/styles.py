"""Presentation styling shared across CTA Sync screens."""
import streamlit as st

CTA_SYNC_CSS = """
<style>
:root {
  --brand:#0c4da2; --brand-dark:#093b7d; --bar:#074ca8;
  --cyan:#16c1f3; --magenta:#ed0677;
  --ink:#14233c; --muted:#5b6b82; --line:#e3e8ef; --canvas:#f6f8fb; --surface:#ffffff; --tint:#eef4fc;
  --ok:#1f7a52; --ok-bg:#eaf6f0; --warn:#9a6200; --warn-bg:#fff6e5; --bad:#b42318; --bad-bg:#fdeeec;
  --radius:12px;
}
.stApp {background:var(--canvas); color:var(--ink);}
[data-testid="stHeader"] {background:transparent;}
[data-testid="stMainBlockContainer"] {max-width:1240px; padding:1.25rem 2.5rem 2.5rem;}
section[data-testid="stSidebar"] {display:none;}
h1,h2,h3,h4,h5 {color:var(--ink); letter-spacing:-.02em;}
h1 {font-size:2rem !important; line-height:1.2 !important; font-weight:650 !important;}
h2 {font-size:1.4rem !important; font-weight:620 !important;}
h3 {font-size:1.1rem !important; font-weight:620 !important;}
p {line-height:1.6;} a {color:var(--brand);}
.eyebrow {font-size:11px; font-weight:700; letter-spacing:.12em; text-transform:uppercase; color:var(--brand); margin-bottom:8px;}

/* App bar: the banner's own blue is reused so the logo sits seamlessly */
[data-testid="stHorizontalBlock"]:has(.app-bar) {background:var(--bar); border-radius:var(--radius); padding:12px 20px; margin-bottom:22px; min-height:80px; align-items:center; box-shadow:0 1px 0 rgba(20,35,60,.06);}
/* Streamlit pulls markdown up with a negative bottom margin, which made the logo overflow the bar */
[data-testid="stHorizontalBlock"]:has(.app-bar) [data-testid="stElementContainer"],
[data-testid="stHorizontalBlock"]:has(.app-bar) [data-testid="stMarkdown"],
[data-testid="stHorizontalBlock"]:has(.app-bar) [data-testid="stMarkdownContainer"] {margin:0 !important;}
[data-testid="stHorizontalBlock"]:has(.app-bar) [data-testid="stVerticalBlock"] {gap:0;}
.app-bar {display:flex; align-items:center; justify-content:space-between; gap:20px; height:56px;}
.app-bar-logo {height:56px; width:auto; display:block; border-radius:4px;}
.app-bar-user {text-align:right; color:#cfe0f7; font-size:12px; line-height:1.35;}
.app-bar-user strong {display:block; color:#fff; font-size:14px; font-weight:600;}
[data-testid="stHorizontalBlock"]:has(.app-bar) button {background:transparent; color:#fff; border:1px solid rgba(255,255,255,.45);}
[data-testid="stHorizontalBlock"]:has(.app-bar) button:hover {background:rgba(255,255,255,.12); border-color:#fff; color:#fff;}

/* Standalone brand header (help page) */
.brand-header {display:flex; align-items:center; gap:20px; flex-wrap:wrap; margin-bottom:18px;}
.brand-header .banner {height:52px; border-radius:8px;}
.brand-header .indegene {height:30px;}
.brand-divider {width:1px; height:30px; background:var(--line);}
.brand-rule {display:none;}

/* Page heading for each step */
.page-head {margin:4px 0 18px;}
.page-head h2 {margin:0 0 4px; padding:0;}
.page-head p {margin:0; color:var(--muted); font-size:14px;}

/* Stepper */
.workflow-steps {display:grid; grid-template-columns:repeat(4,1fr); background:var(--surface); border:1px solid var(--line); border-radius:var(--radius); margin:0 0 26px; overflow:hidden;}
.workflow-step {padding:14px 16px; color:var(--muted); font-size:13px; border-right:1px solid var(--line); position:relative;}
.workflow-step:last-child {border-right:0;}
.workflow-step strong {display:inline-flex; align-items:center; justify-content:center; border-radius:50%; background:#edf1f6; color:var(--muted); width:24px; height:24px; margin-right:8px; font-size:12px;}
.workflow-step.active {color:var(--ink); font-weight:600;}
.workflow-step.active::after {content:""; position:absolute; left:0; right:0; bottom:0; height:3px; background:var(--brand);}
.workflow-step.active strong {background:var(--brand); color:#fff;}
.workflow-step.completed {color:var(--ink);}
.workflow-step.completed strong {background:var(--tint); color:var(--brand);}
.workflow-step small {display:block; padding-left:32px; font-size:11px; color:var(--muted); margin-top:3px; font-weight:400;}

/* Cards and inputs */
[data-testid="stForm"] {padding:24px; border:1px solid var(--line); border-radius:var(--radius); background:var(--surface);}
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] .upload-heading) {background:var(--surface);}
.card {background:var(--surface); border:1px solid var(--line); border-radius:var(--radius); padding:20px 24px; margin-bottom:18px;}
.summary-grid {display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:18px;}
.summary-grid dt {font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); margin-bottom:4px;}
.summary-grid dd {margin:0; font-size:15px; font-weight:600; color:var(--ink); overflow-wrap:anywhere;}
.summary-grid dd.empty {color:#9aa7b8; font-weight:400;}
.upload-heading {margin:0 0 14px;}
.upload-heading h3 {margin:0 0 4px; padding:0; font-size:16px;}
.upload-heading p {font-size:12px; color:var(--muted); margin:0;}
.upload-heading .eyebrow {margin-bottom:6px;}
[data-testid="stFileUploader"] section {background:#f9fbfd; border:1px dashed #b8c7da; border-radius:10px; min-height:110px; padding:18px;}
[data-testid="stFileUploader"] section:hover {border-color:var(--brand); background:var(--tint);}
[data-testid="stFileUploader"] button {background:var(--surface); color:var(--brand); border:1px solid #c6d3e5;}
.file-info {background:#f6f9fc; border:1px solid var(--line); padding:9px 12px; border-radius:8px; margin:6px 0; overflow-wrap:anywhere;}
.file-info-text {font-size:12px; color:#304b6a;}
[data-testid="stTextInput"] input,[data-testid="stSelectbox"] [data-baseweb="select"] > div {background:var(--surface); border-radius:8px; color:var(--ink);}

/* Buttons */
.stButton button,.stDownloadButton button,[data-testid="stFormSubmitButton"] button {min-height:42px; border-radius:8px; font-weight:600; font-size:14px; transition:background .15s ease, border-color .15s ease;}
button[kind="primary"],button[kind="primaryFormSubmit"] {background:var(--brand); border-color:var(--brand); color:#fff;}
button[kind="primary"]:hover,button[kind="primaryFormSubmit"]:hover {background:var(--brand-dark); border-color:var(--brand-dark); color:#fff;}
button[kind="secondary"],button[kind="secondaryFormSubmit"] {background:var(--surface); border:1px solid #cad5e4; color:var(--brand);}
button[kind="secondary"]:hover {border-color:var(--brand); color:var(--brand-dark);}
button:disabled {opacity:.45;}
button:focus-visible,a:focus-visible,input:focus-visible {outline:3px solid var(--cyan) !important; outline-offset:2px;}

/* Metrics and tables */
[data-testid="stMetric"] {background:var(--surface); border:1px solid var(--line); border-radius:10px; padding:16px 18px;}
[data-testid="stMetricLabel"] {color:var(--muted); font-size:12px;}
[data-testid="stMetricValue"] {color:var(--ink); font-size:28px;}
[data-testid="stDataFrame"],[data-testid="stExpander"] {border:1px solid var(--line); border-radius:10px; background:var(--surface); overflow:hidden;}

/* Results */
.report-head {display:flex; justify-content:space-between; align-items:center; gap:28px; background:var(--surface); border:1px solid var(--line); border-radius:var(--radius); padding:24px 28px; margin-bottom:16px;}
.report-head h1 {margin:0 0 6px; padding:0; font-size:1.7rem !important;}
.report-meta {display:flex; flex-wrap:wrap; gap:6px 18px; color:var(--muted); font-size:13px;}
.report-score {min-width:200px; text-align:right;}
.report-score .value {font-size:2.4rem; font-weight:700; color:var(--ink); line-height:1;}
.report-score .label {font-size:12px; color:var(--muted); margin:6px 0 8px;}
.score-track {height:6px; background:#edf1f6; border-radius:999px; overflow:hidden;}
.score-fill {height:100%; background:var(--brand); border-radius:999px;}
.stat-row {display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin-bottom:24px;}
.stat {background:var(--surface); border:1px solid var(--line); border-radius:10px; padding:14px 18px; border-top:3px solid var(--line);}
.stat span {display:block; font-size:12px; color:var(--muted);}
.stat strong {font-size:26px; color:var(--ink);}
.stat.ok {border-top-color:var(--ok);} .stat.warn {border-top-color:#e0a52b;} .stat.bad {border-top-color:var(--bad);} .stat.total {border-top-color:var(--brand);}
[data-testid="stSegmentedControl"] button[aria-checked="true"],[data-testid="stButtonGroup"] button[kind="segmented_controlActive"] {background:var(--tint); color:var(--brand); border-color:var(--brand);}

/* Messages */
.alert-info,.alert-warning,.alert-success {padding:12px 16px; border-radius:8px; font-size:13px; margin:12px 0; border:1px solid;}
.alert-info {background:var(--tint); color:#254d80; border-color:#d5e2f4;}
.alert-warning {background:var(--warn-bg); color:#7c5a22; border-color:#eeddb7;}
.alert-success {background:var(--ok-bg); color:#1f5e43; border-color:#cfe7da;}

/* Footer */
[data-testid="stHorizontalBlock"]:has(.app-footer) {border-top:1px solid var(--line); margin-top:36px; padding-top:14px; align-items:center;}
.app-footer {display:flex; align-items:center; gap:12px; flex-wrap:wrap; color:var(--muted); font-size:12px;}
.app-footer img {height:18px; width:auto;}
button[kind="tertiary"] {color:var(--brand); font-weight:600; justify-content:flex-end;}
button[kind="tertiary"]:hover {color:var(--brand-dark); text-decoration:underline;}

/* Admin and generic hero */
.workspace-hero {background:var(--surface); border:1px solid var(--line); border-radius:var(--radius); padding:24px 28px; margin-bottom:22px;}
.workspace-hero h1 {margin:0 0 6px; padding:0;}
.workspace-hero p {color:var(--muted); margin:0; max-width:680px; font-size:14px;}

/* Login */
.login-panel {background:var(--bar); border-radius:16px; padding:36px 40px; color:#fff; min-height:470px; display:flex; flex-direction:column;}
.login-panel .banner {width:100%; max-width:380px; height:auto; margin:-8px 0 0 -10px;}
.login-panel h1 {color:#fff; font-size:2.1rem !important; margin:22px 0 10px; padding:0;}
.login-panel p {color:#d4e3f8; font-size:15px; margin:0;}
.login-points {display:grid; gap:0; margin-top:auto; padding-top:28px;}
.login-points span {border-top:1px solid rgba(255,255,255,.18); padding:12px 0; color:#e4eefb; font-size:13px;}
.login-points b {color:#7fdcf7; font-weight:600; margin-right:10px;}
.login-card-head {margin:12px 0 18px;}
.login-card-head img {height:30px; width:auto; margin-bottom:26px;}
.login-card-head h2 {margin:0 0 4px; padding:0;}
.login-card-head p {margin:0; color:var(--muted); font-size:14px;}

@media(max-width:760px) {
  [data-testid="stMainBlockContainer"] {padding:1rem;}
  .app-bar-logo {height:42px;} .app-bar-user {display:none;}
  .workflow-steps {grid-template-columns:repeat(2,1fr);}
  .workflow-step {padding:12px; border-bottom:1px solid var(--line);}
  .workflow-step small {padding-left:0;}
  .summary-grid,.stat-row {grid-template-columns:repeat(2,minmax(0,1fr));}
  .report-head {flex-direction:column; align-items:flex-start;}
  .report-score {text-align:left; width:100%;}
  .login-panel {min-height:0; padding:26px;}
  h1 {font-size:1.7rem !important;}
}
@media(prefers-reduced-motion:reduce) {button {transition:none !important;}}
</style>
"""


def render_cta_sync_styles() -> None:
    st.markdown(CTA_SYNC_CSS, unsafe_allow_html=True)
