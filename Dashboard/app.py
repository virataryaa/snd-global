import streamlit as st

st.set_page_config(page_title="Coffee SnD", layout="wide", initial_sidebar_state="expanded")

import analytics  # noqa: E402  (after set_page_config)
import brazil  # noqa: E402
import revisions  # noqa: E402
import scenario  # noqa: E402
import snd  # noqa: E402
import theme  # noqa: E402

# Strict light theme shared with the Commodity Calendar app: CSS hard-codes colours (no
# prefers-color-scheme) and the repo's .streamlit/config.toml pins base="light".
st.markdown(theme.CSS, unsafe_allow_html=True)


theme.gate("Coffee SnD")

# Widgets that are not drawn in a run lose their value (e.g. the Years filter while another tab is open): keep a copy.
KEEP = (["snd_page", "snd_span", "snd_mode", "an_page", "an_view", "an_br_scope", "an_br_start", "br_span", "br_mode", "rv_set",
         "sc_bar_span", "sc_years", "sc_scope", "sn_origin", "sn_vs", "sn_yr", "sn_unit", "sn_step_m bags", "sn_step_%", "sn_n"]
        + [scenario._skey(k, u) for k in scenario.ALL_KEYS for u in scenario.UNITS] + ["sc_unit"])
for _k in KEEP:
    if _k not in st.session_state and f"_keep_{_k}" in st.session_state:
        st.session_state[_k] = st.session_state[f"_keep_{_k}"]

with st.sidebar:
    st.markdown("<div class='sb-title'>Coffee SnD</div>", unsafe_allow_html=True)
    st.markdown("<div class='sb-sep'></div><div class='sb-label'>Section</div>", unsafe_allow_html=True)
    section = st.radio("Section", ["SnD", "Analysis", "Scenarios", "Sensitivity", "Revisions"],
                       key="section", label_visibility="collapsed")


def _snd():
    _old = {"Brazil": "Brazil Internal SnD", "Coffee": "Global SnD", "AgriAcies format": "Brazil Internal SnD"}   # old labels
    if st.session_state.get("snd_page") in _old:
        st.session_state["snd_page"] = _old[st.session_state["snd_page"]]
    # one row: page switch on the left, Mode (View / Edit) on the right — SnD / Brazil draw Mode into that slot
    left, right = st.columns([3, 1], vertical_alignment="center")
    page = left.radio("Page", ["Global SnD", "Brazil Internal SnD"], horizontal=True, key="snd_page", label_visibility="collapsed")
    snd.MODE_SLOT = brazil.MODE_SLOT = right.container()
    if page == "Global SnD":
        snd.render()
    else:
        brazil.render("Brazil SnD")


# only the chosen section runs (its own sidebar controls are added below the section switch)
{"SnD": _snd, "Analysis": analytics.render, "Scenarios": scenario.page,
 "Sensitivity": scenario.sensitivity_page, "Revisions": revisions.render}[section]()

for _k in KEEP:
    if _k in st.session_state:
        st.session_state[f"_keep_{_k}"] = st.session_state[_k]
