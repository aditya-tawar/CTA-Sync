"""Help for the current CTA Sync workflow."""
import streamlit as st
from cta_app.components.branding import render_brand_header
from cta_app.ui.styles import render_cta_sync_styles

render_cta_sync_styles()
render_brand_header()
st.markdown('<div class="brand-rule"></div>', unsafe_allow_html=True)
if st.button("Back to workspace"):
    st.switch_page("app.py")
st.markdown('<section class="workspace-hero"><div class="eyebrow">CTA Sync help center</div><h1>A little guidance. A clearer review.</h1><p>Answers to common questions about campaign validation.</p></section>', unsafe_allow_html=True)
questions = [
    ("Which files can I upload?", "Upload campaign files in HTML, HTM, or EML format, together with one or more Claravine CSV files."),
    ("How are repeated CTA names matched?", "Repeated CTA labels are paired in their order of appearance with the corresponding Claravine rows. Check the spreadsheet row order when reviewing repeated labels."),
    ("How are email tracking links handled?", "CTA Sync attempts to unwrap tracking and security redirects. When the destination remains hidden, CTA names and occurrence order help identify the corresponding reference row. Review the matching notes for each result."),
    ("Can image CTAs be checked?", "Yes. Linked images are extracted, and image labels can be inferred from alt text or OCR. Review inferred labels before accepting a result."),
    ("Does an accessibility check guarantee a link works?", "No. Definite problems such as a 404 or 410 can fail the check. Timeouts and blocked requests may be inconclusive; open the destination manually when needed."),
    ("What is included in the export?", "The Excel QA report compares campaign and Claravine subjects, CTA labels, URLs, landing pages, and tracking codes, with pass/fail findings and suggested fixes."),
    ("How do I validate corrected files?", "Choose New Validation from the results screen, upload the corrected campaign files and the reference CSVs, and start a fresh review."),
]
for question, answer in questions:
    with st.expander(question):
        st.write(answer)
