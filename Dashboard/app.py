import streamlit as st

st.set_page_config(page_title="Coffee SnD", layout="wide", initial_sidebar_state="expanded")

import analytics  # noqa: E402  (after set_page_config)
import brazil  # noqa: E402
import revisions  # noqa: E402
import scenario  # noqa: E402
import snd  # noqa: E402

# Strict light theme shared with the Commodity Calendar app: CSS hard-codes colours (no
# prefers-color-scheme) and the repo's .streamlit/config.toml pins base="light".
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@600&family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], [data-testid="stAppViewContainer"], .stMarkdown, button, input, textarea {
    font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif !important; -webkit-font-smoothing: antialiased; }
[data-testid="stAppViewContainer"], [data-testid="stMain"], .main { background: #fafafa !important; }
/* Streamlit's top bar overlays the page: keep it short and see-through so content can start just below it */
[data-testid="stHeader"] { background: transparent !important; height: 2.6rem !important; min-height: 0 !important; }
[data-testid="stSidebar"] { background: #f0f2f8 !important; border-right: 1px solid #dfe3ee; width: 240px !important; min-width: 240px !important; max-width: 240px !important; }
h1, h2, h3, h4, h5, h6 { color: #0a2463 !important; letter-spacing: -.01em; }
body, .main { color: #1a1a2e; }
.block-container { padding-top: 2.9rem; max-width: 1500px; }

/* Radio as pill / segmented control */
div[role="radiogroup"] { background: #eef0f6; padding: 4px; border-radius: 999px; gap: 2px; display: inline-flex; flex-wrap: wrap; }
div[role="radiogroup"] label { background: transparent !important; border-radius: 999px !important; padding: 4px 12px !important; margin: 0 !important; }
div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child { display: none; }
div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 12px !important; color: #5a6688 !important; }
div[role="radiogroup"] label:has(input:checked) { background: #0a2463 !important; }
div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #ffffff !important; font-weight: 600; }

/* Pills / segmented controls: quiet when off, solid navy when picked */
button[kind="pills"], button[kind="segmented_control"] {
    background: #ffffff !important; border: 1px solid #dfe3ee !important; border-radius: 999px !important;
    min-height: 26px !important; padding: 1px 11px !important; }
button[kind="pills"] p, button[kind="segmented_control"] p { color: #3a4466 !important; font-size: 11.5px !important; }
button[kind="pills"]:hover, button[kind="segmented_control"]:hover { border-color: #9db3e6 !important; }
button[kind="pillsActive"], button[kind="segmented_controlActive"] {
    background: #0a2463 !important; border: 1px solid #0a2463 !important; border-radius: 999px !important;
    min-height: 26px !important; padding: 1px 11px !important; }
button[kind="pillsActive"] p, button[kind="segmented_controlActive"] p { color: #ffffff !important; font-size: 11.5px !important; }

/* Selects: white bg, dark text */
[data-baseweb="popover"] [data-baseweb="menu"] { background: #ffffff !important; }
[data-baseweb="popover"] [data-baseweb="menu"] li, [data-baseweb="popover"] [data-baseweb="menu"] li * { color: #1a1a2e !important; }
[data-baseweb="select"] { background: #ffffff !important; }
[data-baseweb="select"] > div { background: #ffffff !important; color: #1a1a2e !important; border-color: #e3e7f0 !important; }

/* multiselect chips: navy chip, white text and x */
[data-baseweb="tag"] { background: #0a2463 !important; }
[data-baseweb="tag"] span, [data-baseweb="tag"] div { color: #ffffff !important; }
[data-baseweb="tag"] svg { fill: #ffffff !important; }

/* Pill tabs (Streamlit's tab strip clips overflow, which crops the track) */
.stTabs, .stTabs > div, .stTabs [data-baseweb="tab-list"] { overflow: visible !important; }
.stTabs [data-baseweb="tab-list"] { background: #eef0f6; padding: 4px; border-radius: 999px; gap: 2px; width: fit-content;
                                    max-width: 100%; flex-wrap: wrap; margin: 0 0 2px; }
.stTabs [data-baseweb="tab"] { border-radius: 999px; padding: 3px 14px; height: auto; min-height: 0; background: transparent; }
.stTabs [data-baseweb="tab"] p { font-size: 13px !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 6px !important; }
/* page-level switches (e.g. Global / Brazil): slimmer track */
.st-key-snd_page div[role="radiogroup"] { padding: 2px; }
.st-key-snd_page div[role="radiogroup"] label { padding: 2px 11px !important; }
.st-key-snd_page div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 11px !important; }
[data-testid="stMain"] [data-testid="stVerticalBlock"] { gap: .55rem; }
.stTabs [aria-selected="true"] { background: #0a2463 !important; color: #ffffff !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

/* Sidebar */
[data-testid="stSidebarUserContent"] { padding-top: 1rem !important; }
.sb-title { font-family: 'Fraunces', Georgia, serif; font-size: 1.5rem; font-weight: 600; color: #0a2463 !important; margin-bottom: 10px; }
.sb-label, [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    font-size: 10.5px !important; font-weight: 700; color: #0a2463 !important; text-transform: uppercase; letter-spacing: .11em; margin: 10px 0 6px; }
.sb-sep { border-top: 1px solid #e0e4ee; margin: 14px 0 10px; }
[data-testid="stSidebar"] [data-baseweb="checkbox"] p { font-size: 12.5px; color: #3a4466; }

/* Page text and cards */
.page-title, .snd-head .t { color: #0a2463 !important; font-weight: 700; font-size: 1.15rem; margin: 0 0 4px 0; letter-spacing: -.01em; }
.card-title, .chart-head { color: #0a2463; font-weight: 600; font-size: .9rem; margin-bottom: 4px; letter-spacing: -.005em; }
.card-desc { color: #5a6688; font-size: .8rem; margin-top: -4px; margin-bottom: 8px; }
.pill { display: inline-block; background: #eef0f6; color: #5a6688; font-size: 10.5px; font-weight: 600;
        padding: 1px 8px; border-radius: 999px; margin-left: 6px; vertical-align: middle; }
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]), .snd-wrap {
    background: #ffffff; border: 1px solid #e3e7f0 !important; border-radius: 14px; box-shadow: 0 1px 3px rgba(10,36,99,0.06); }
.snd-wrap { padding: 10px 14px 14px; }

/* Compact tables (save history) */
.dtab { width: auto; border-collapse: collapse; font-size: 11.5px; line-height: 1.15; background: #ffffff; }
.dtab th { text-align: center; padding: 3px 8px; font-weight: 600; white-space: nowrap; color: #5a6688; border-bottom: 1px solid #e3e7f0; }
.dtab .sub th { background: #ffffff; color: #5a6688; }
.dtab td { text-align: right; padding: 2px 8px; border-bottom: 1px solid #f1f3f8; white-space: nowrap; color: #1a1a2e; }
.dtab td.dt { text-align: center; background: #fafbfd; }
.dtab td.b { font-weight: 700; }
.dtab td.ts { font-size: 10.5px; color: #8a94a8; text-align: left; }

/* SnD table: hairlines, navy year header, typography does the work */
table.snd { color: #1a1a2e !important; font-size: 12.5px !important; }
table.snd td { border-bottom: 1px solid #f1f3f8 !important; padding: 5px 10px !important; }
table.snd td.lbl { color: #3a4466 !important; }
table.snd tr.comm th { background: none !important; color: #0a2463 !important; font-size: 11px !important; letter-spacing: .08em !important;
    padding: 14px 12px 4px !important; border-bottom: 0 !important; }
table.snd th.y { background: #0a2463 !important; color: #ffffff !important; font-weight: 600 !important; padding: 7px 10px !important; border-bottom: 2px solid #b08d57 !important; }
table.snd th.y.first { border-radius: 8px 0 0 0; }
table.snd th.y:last-child { border-radius: 0 8px 0 0; }
table.snd td.fc { background: none !important; }
table.snd tr.b td { background: #fafbfd !important; }
table.snd tr.bal td { background: #eef1f8 !important; border-top: 1px solid #e3e7f0 !important; border-bottom: 1px solid #e3e7f0 !important; }
table.snd tr.bal td.lbl { color: #0a2463 !important; }
table.snd tr.soft td, table.snd tr.soft td.lbl, table.snd tr.meta td, table.snd tr.meta td.lbl { color: #8a94a8 !important; }
table.snd td.neg { color: #c94a4a !important; }
.snd-bar { background: none !important; color: #0a2463 !important; letter-spacing: .08em !important; font-size: 11px !important; padding: 10px 0 4px !important; }

/* Mode (View/Edit): orange, like the calendar's Entry tab */
.st-key-mode_nav div[role="radiogroup"] label:has(input:checked) { background: #d9822b !important; }
.st-key-mode_nav [data-testid="stRadio"], .st-key-mode_nav [role="radiogroup"] { margin-left: auto; }
.st-key-mode_nav { display: flex; justify-content: flex-end; }
/* Analysis page (Global / Brazil Internal): muted red so it reads without a caption */
.st-key-an_page_nav div[role="radiogroup"] label:has(input:checked) { background: #a0414b !important; }

/* Sensitivity's controls row: compact, everything on one line */
.st-key-sn_controls { padding: 6px 12px !important; }
.st-key-sn_controls [data-testid="stWidgetLabel"] p { font-size: 9px !important; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; color: #8a94a8 !important; margin-bottom: 0 !important; }
.st-key-sn_controls div[role="radiogroup"] { padding: 2px !important; }
.st-key-sn_controls div[role="radiogroup"] label { padding: 1px 7px !important; }
.st-key-sn_controls div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 10.5px !important; }
.st-key-sn_controls [data-baseweb="input"], .st-key-sn_controls [data-baseweb="select"] > div { min-height: 25px !important; font-size: 11.5px !important; }
.st-key-sn_controls button { padding: 2px 8px !important; min-height: 25px !important; font-size: 11.5px !important; }
.st-key-sn_controls [data-testid="stVerticalBlock"] { gap: 0.35rem !important; }
</style>
""",
    unsafe_allow_html=True,
)


def _gate():
    """If Secrets has [auth] password, ask for it before showing anything: the Edit mode can push to GitHub, so a public URL must not be enough."""
    try:
        pw = st.secrets.get("auth", {}).get("password")
    except Exception:
        pw = None
    if not pw or st.session_state.get("_authed"):
        return
    st.markdown("<div class='page-title' style='margin-top:12vh'>Coffee SnD</div>", unsafe_allow_html=True)
    typed = st.text_input("Password", type="password", key="_pw_input")
    if typed and typed == pw:
        st.session_state["_authed"] = True
        st.rerun()
    elif typed:
        st.error("Wrong password.")
    st.stop()


_gate()

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
