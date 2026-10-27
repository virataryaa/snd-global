import sys
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Coffee SnD", layout="wide", initial_sidebar_state="expanded")

# Aggregated Exports (history + TDM + Entry) lives in its own folder; appended so SnD's own modules win on a name clash
sys.path.append(str(Path(__file__).resolve().parent.parent / "Coffee Aggregated Tradeflows" / "Dashboard"))

import importlib  # noqa: E402

import analytics  # noqa: E402  (after set_page_config)
import brazil  # noqa: E402
import colombia  # noqa: E402
import data as _ex_data  # noqa: E402
import exports_view as ev  # noqa: E402
import origins as _ex_origins  # noqa: E402


def _fresh(mod):
    """Streamlit only reloads modules under Dashboard/ when a push lands; the exports modules live next door, so reload them
    here when their file changed (or once per process, for a module loaded before this check existed)."""
    m = Path(mod.__file__).stat().st_mtime
    if getattr(mod, "_mtime", None) != m:
        mod = importlib.reload(mod)
        mod._mtime = m
    return mod


_ex_origins, _ex_data = _fresh(_ex_origins), _fresh(_ex_data)
ev = _fresh(ev)
_ex_data.TEXT = ev.manual_text   # a reloaded data.py loses the hook; put it back
import revisions  # noqa: E402
import scenario  # noqa: E402
import snd  # noqa: E402
import theme  # noqa: E402

# Strict light theme shared with the Commodity Calendar app: CSS hard-codes colours (no
# prefers-color-scheme) and the repo's .streamlit/config.toml pins base="light".
st.markdown(theme.CSS, unsafe_allow_html=True)
theme.ice_charts()


theme.gate("Coffee SnD")

# Widgets that are not drawn in a run lose their value (e.g. the Years filter while another tab is open): keep a copy.
KEEP = (["snd_page", "snd_span", "snd_mode", "an_page", "an_view", "an_br_scope", "an_br_start", "br_span", "yrs_span", "lim_flags", "rows_only", "br_mode", "rv_set",
         "sc_bar_span", "sc_years", "sc_scope", "sn_origin", "sn_vs", "sn_yr", "sn_unit", "sn_step_m bags", "sn_step_%", "sn_n"]
        + [scenario._skey(k, u) for k in scenario.ALL_KEYS for u in scenario.UNITS] + ["sc_unit"]
        + ["cl_mode", "cl_series", "cl_span", "cl_unit"]
        + ["ex_mode", "mc_ch_comm", "mc_ch_unit", "mc_ch_span", "mc_cy_basis", "mc_pj_method", "mc_view", "mc_cumview",
           "mc_roll", "mc_stackview", "en_origin", "en_years"] + [f"mc_origin_{c}" for c in ev.COMMS])
for _k in KEEP:
    if _k not in st.session_state and f"_keep_{_k}" in st.session_state:
        st.session_state[_k] = st.session_state[f"_keep_{_k}"]

st.session_state["yrs_span"] = "All"   # coffee always shows every crop year (no switch)

with st.sidebar:
    st.markdown("<div class='sb-title'>Coffee SnD</div>", unsafe_allow_html=True)
    st.markdown("<div class='sb-sep'></div><div class='sb-label'>Section</div>", unsafe_allow_html=True)
    section = st.radio("Section", ["SnD", "Analysis", "Scenarios", "Sensitivity", "Revisions", "Exports"],
                       format_func=lambda s: {"Analysis": "Insights", "Scenarios": "What-if", "Sensitivity": "Stress test", "Revisions": "Change log",
                                              "Exports": "Aggregated Exports"}.get(s, s), key="section", label_visibility="collapsed")


def _snd():
    _old = {"Brazil": "Brazil Internal SnD", "Coffee": "Global SnD", "AgriAcies format": "Brazil Internal SnD"}   # old labels
    if st.session_state.get("snd_page") in _old:
        st.session_state["snd_page"] = _old[st.session_state["snd_page"]]
    # one row: page switch on the left, Mode (View / Edit) on the right — SnD / Brazil draw Mode into that slot
    left, right = st.columns([3, 1], vertical_alignment="center")
    page = left.radio("Page", ["Global SnD", "Brazil Internal SnD", "Colombia Internal SnD"], horizontal=True, key="snd_page",
                      label_visibility="collapsed")
    snd.MODE_SLOT = brazil.MODE_SLOT = right.container()
    if page == "Global SnD":
        snd.render()
    elif page == "Brazil Internal SnD":
        brazil.render("Brazil SnD")
    else:
        colombia.render(snd.MODE_SLOT)


def _exports():
    # charts (history + TDM + manual) in View; Edit Mode = the Entry page (manual months, TDM shares), same switch as SnD
    head, right = st.columns([4, 1], vertical_alignment="center")
    with right, st.container(key="mode_nav"):
        mode = theme.mode_switch("ex_mode")
    ev.render(head) if mode == "View" else ev.render_entry(head)


# only the chosen section runs (its own sidebar controls are added below the section switch)
{"SnD": _snd, "Analysis": analytics.render, "Scenarios": scenario.page,
 "Sensitivity": scenario.sensitivity_page, "Revisions": revisions.render, "Exports": _exports}[section]()
st.markdown(theme.ICE, unsafe_allow_html=True)   # last, so the ice look sits over every page's own CSS

for _k in KEEP:
    if _k in st.session_state:
        st.session_state[f"_keep_{_k}"] = st.session_state[_k]
