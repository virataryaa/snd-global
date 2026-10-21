import streamlit as st

st.set_page_config(page_title="Cocoa SnD", layout="wide", initial_sidebar_state="expanded")

import cocoa  # noqa: E402  (after set_page_config)
import theme  # noqa: E402

st.markdown(theme.CSS, unsafe_allow_html=True)
theme.gate("Cocoa SnD")

with st.sidebar:
    st.markdown("<div class='sb-title'>Cocoa SnD</div>", unsafe_allow_html=True)

cocoa.render()
