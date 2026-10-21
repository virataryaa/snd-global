import streamlit as st

st.set_page_config(page_title="Cocoa SnD", layout="wide", initial_sidebar_state="expanded")

import cocoa  # noqa: E402  (after set_page_config)
import cocoa_viz  # noqa: E402
import theme  # noqa: E402

st.markdown(theme.CSS, unsafe_allow_html=True)
theme.gate("Cocoa SnD")

with st.sidebar:
    st.markdown("<div class='sb-title'>Cocoa SnD</div><div class='sb-label'>Section</div>", unsafe_allow_html=True)
    section = st.radio("Section", ["SnD", "Analysis", "Scenarios", "Revisions"], key="co_section", label_visibility="collapsed")

if section == "SnD":
    cocoa.render()
elif section == "Analysis":
    cocoa_viz.analysis_page()
elif section == "Scenarios":
    cocoa_viz.scenario_page()
else:
    cocoa.revisions_page()
