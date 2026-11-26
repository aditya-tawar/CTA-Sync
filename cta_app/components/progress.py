"""Compact, accessible wizard progress."""
import streamlit as st

TOTAL_STEPS = 4

def render_progress_bar():
    current = st.session_state.current_step
    names = ["Upload assets", "Campaign details", "Review & confirm", "Results"]
    details = ["Campaigns and references", "Context for your review", "Files and column mappings", "Findings and report"]
    items = []
    for number, (name, detail) in enumerate(zip(names, details), 1):
        state = "active" if number == current else "completed" if number < current else ""
        aria = ' aria-current="step"' if number == current else ""
        marker = "&#10003;" if number < current else str(number)
        items.append(f'<div class="workflow-step {state}"{aria}><strong>{marker}</strong>{name}<small>{detail}</small></div>')
    st.markdown('<nav class="workflow-steps" aria-label="Campaign validation steps">' + "".join(items) + '</nav>', unsafe_allow_html=True)
