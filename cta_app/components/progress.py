"""Accessible workflow progress using the shared page theme."""
import streamlit as st

TOTAL_STEPS = 4

def render_progress_bar():
    current = st.session_state.current_step
    names = ["Upload assets", "Campaign details", "Review", "Validation"]
    descriptions = ["Add campaign & reference files", "Name your campaign", "Confirm your inputs", "Review findings & export"]
    steps = []
    for number, name in enumerate(names, 1):
        state = "completed" if number < current else "active" if number == current else ""
        aria = ' aria-current="step"' if number == current else ""
        marker = "&#10003;" if number < current else str(number)
        steps.append(f'<div class="workflow-step {state}"{aria}><strong>{marker}</strong>{name}<small>{descriptions[number - 1]}</small></div>')
    st.markdown(f'<p class="workflow-status">STEP {current} OF {TOTAL_STEPS} &middot; {names[current - 1]}</p>', unsafe_allow_html=True)
    st.markdown('<nav class="workflow-steps" aria-label="Validation progress">' + "".join(steps) + '</nav>', unsafe_allow_html=True)
