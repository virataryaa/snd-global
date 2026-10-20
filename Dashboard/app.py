import streamlit as st

st.set_page_config(page_title="Global SnD", layout="wide", initial_sidebar_state="expanded")

import analytics  # noqa: E402  (after set_page_config)
import brazil  # noqa: E402
import revisions  # noqa: E402
import scenario  # noqa: E402
import snd  # noqa: E402

# Strict light theme: CSS hard-codes colours, no prefers-color-scheme,
# and .streamlit/config.toml pins base="light".
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], [data-testid="stAppViewContainer"], .stMarkdown, button, input, textarea { font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif !important; }
[data-testid="stAppViewContainer"], [data-testid="stMain"], .main { background: #f7f8fb !important; }
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #08153d 0%, #0a2463 100%) !important; border-right: 0; }
[data-testid="stSidebar"] * { color: #c9d3ea; }
h1, h2, h3, h4, h5, h6 { color: #0a2463 !important; letter-spacing: -.01em; }
body, .main { color: #0f172a; }
.block-container { padding-top: 2rem; max-width: 1500px; }

/* Radio as a slim segmented control */
div[role="radiogroup"] { background: #eef1f6; padding: 3px; border-radius: 9px; gap: 2px; display: inline-flex; flex-wrap: wrap; }
div[role="radiogroup"] label { background: transparent !important; border-radius: 7px !important; padding: 3px 12px !important; margin: 0 !important; }
div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child { display: none; }
div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 12px !important; color: #64748b; }
div[role="radiogroup"] label:has(input:checked) { background: #0a2463 !important; }
div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #ffffff !important; font-weight: 600; }

[data-baseweb="popover"] [data-baseweb="menu"] { background: #ffffff !important; }
[data-baseweb="popover"] [data-baseweb="menu"] li, [data-baseweb="popover"] [data-baseweb="menu"] li * { color: #0f172a !important; }
[data-baseweb="select"] { background: #ffffff !important; }
[data-baseweb="select"] > div { background: #ffffff !important; color: #0f172a !important; border-color: #e6e9f0 !important; }

.card-desc { color: #94a3b8; font-size: 0.76rem; margin-top: -4px; margin-bottom: 6px; }
.chart-head { color: #0f172a; font-weight: 600; font-size: 0.86rem; margin-bottom: 0; letter-spacing: .005em; }
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {
    background: #ffffff; border: 1px solid #e6e9f0 !important; border-radius: 12px; box-shadow: 0 1px 2px rgba(15,23,42,.04); }

/* Sidebar: quiet section switch */
[data-testid="stSidebarUserContent"] { padding-top: 1.2rem !important; }
[data-testid="stSidebar"] .st-key-sec_nav div[role="radiogroup"] { display: flex; flex-direction: column; align-items: stretch; width: 100%; border-radius: 10px; padding: 3px; gap: 2px; }
[data-testid="stSidebar"] .st-key-sec_nav div[role="radiogroup"] label { padding: 7px 14px !important; }
[data-testid="stSidebar"] .st-key-sec_nav div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 13.5px !important; }
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { font-size: 10px !important; font-weight: 600; letter-spacing: .1em;
    text-transform: uppercase; color: #8fa3d1 !important; }
[data-testid="stSidebar"] div[role="radiogroup"] { background: rgba(255,255,255,.08); }
[data-testid="stSidebar"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { color: #c9d3ea !important; }
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) { background: #ffffff !important; }
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #0a2463 !important; font-weight: 600; }
[data-testid="stSidebar"] div[role="radiogroup"] { display: flex; flex-wrap: wrap; width: 100%; }
.sb-sep { border-top: 1px solid rgba(255,255,255,.12); margin: 12px 0 10px; }
.sb-label { font-size: 10px; color: #8fa3d1 !important; text-transform: uppercase; letter-spacing: .1em; margin: 8px 0 6px; font-weight: 600; }
.sb-title { font-size: 1.1rem; font-weight: 700; color: #ffffff !important; letter-spacing: -.01em; margin-bottom: 0; }
.page-title { color: #0a2463; font-weight: 700; font-size: 1.15rem; margin: 0 0 8px 0; letter-spacing: -.01em; }
.card-title { color: #0f172a; font-weight: 600; font-size: 0.9rem; margin-bottom: 4px; }
.pill { display: inline-block; background: #eef1f6; color: #64748b; font-size: 10.5px; font-weight: 600;
        padding: 1px 8px; border-radius: 999px; margin-left: 6px; vertical-align: middle; }

/* Compact tables (save history) */
.dtab { width: auto; border-collapse: collapse; font-size: 11.5px; line-height: 1.15; background: #ffffff; }
.dtab th { text-align: center; padding: 3px 8px; font-weight: 600; white-space: nowrap; color: #64748b; border-bottom: 1px solid #e6e9f0; }
.dtab .sub th { background: #ffffff; color: #64748b; }
.dtab td { text-align: right; padding: 2px 8px; border-bottom: 1px solid #f1f3f7; white-space: nowrap; color: #0f172a; }
.dtab td.dt { text-align: center; background: #f7f8fb; }
.dtab td.b { font-weight: 700; }
.dtab td.ts { font-size: 10.5px; color: #94a3b8; text-align: left; }

/* ── Polish: light, quiet, Apple-like. Later rules override the ones above. ── */
html, body, [class*="css"], [data-testid="stAppViewContainer"], .stMarkdown, button, input, textarea {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Inter', 'Segoe UI', sans-serif !important; -webkit-font-smoothing: antialiased; }
[data-testid="stAppViewContainer"], [data-testid="stMain"], .main { background: #f5f5f7 !important; }
.block-container { padding-top: 2.4rem; }
[data-testid="stSidebar"] { background: rgba(255,255,255,.72) !important; backdrop-filter: saturate(180%) blur(20px);
    border-right: 1px solid rgba(0,0,0,.06) !important; }
[data-testid="stSidebar"] * { color: #1d1d1f; }
.sb-title { color: #1d1d1f !important; font-size: 1.05rem; font-weight: 600; }
.sb-label, [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { color: #86868b !important; letter-spacing: .06em; }
.sb-sep { border-top: 1px solid rgba(0,0,0,.06); }
/* segmented controls: grey track, white raised pill */
div[role="radiogroup"], [data-testid="stSidebar"] div[role="radiogroup"] { background: rgba(118,118,128,.12) !important; border-radius: 10px; padding: 2px; }
div[role="radiogroup"] label { border-radius: 8px !important; transition: background .15s ease; }
div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { color: #3a3a3c !important; font-weight: 500; }
div[role="radiogroup"] label:has(input:checked), [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    background: #ffffff !important; box-shadow: 0 1px 3px rgba(0,0,0,.12), 0 0 0 .5px rgba(0,0,0,.04); }
div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #0a2463 !important; font-weight: 600; }
[data-testid="stSidebar"] .st-key-sec_nav div[role="radiogroup"] { background: transparent !important; padding: 0; }
[data-testid="stSidebar"] .st-key-sec_nav div[role="radiogroup"] label:has(input:checked) { background: rgba(10,36,99,.08) !important; box-shadow: none; }
/* cards */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]), .snd-wrap {
    background: #ffffff; border: 0 !important; border-radius: 18px; box-shadow: 0 1px 2px rgba(0,0,0,.04), 0 8px 24px rgba(0,0,0,.04); }
.snd-wrap { padding: 10px 14px 14px; }
.chart-head { color: #1d1d1f; font-weight: 600; font-size: .9rem; letter-spacing: -.01em; }
.snd-head .t, .page-title { color: #1d1d1f !important; font-weight: 700; letter-spacing: -.02em; font-size: 26px; }
h1, h2, h3, h4, h5, h6 { color: #1d1d1f !important; }
/* table: no colour bands, hairlines, typography does the work */
table.snd { color: #1d1d1f !important; font-size: 12.5px !important; }
table.snd td { border-bottom: 1px solid rgba(0,0,0,.05) !important; padding: 5px 10px !important; }
table.snd td.lbl { color: #3a3a3c !important; }
table.snd tr.comm th { background: none !important; color: #0a2463 !important; font-size: 11px !important; letter-spacing: .08em !important; padding: 14px 12px 4px !important;
    border-bottom: 0 !important; }
table.snd th.y { background: none !important; color: #86868b !important; font-weight: 500 !important; border-bottom: 1px solid rgba(0,0,0,.08) !important; }
table.snd td.fc { background: none !important; }
table.snd tr.b td { background: rgba(0,0,0,.03) !important; }
table.snd tr.bal td { background: rgba(0,0,0,.08) !important; border-top: 1px solid rgba(0,0,0,.08) !important; border-bottom: 1px solid rgba(0,0,0,.08) !important; }
table.snd tr.bal td.lbl { color: #1d1d1f !important; }
table.snd tr.soft td, table.snd tr.soft td.lbl { color: #86868b !important; }
table.snd tr.meta td, table.snd tr.meta td.lbl { color: #86868b !important; }
table.snd td.neg { color: #d70015 !important; }
.snd-bar { background: none !important; color: #0a2463 !important; letter-spacing: .08em !important; font-size: 11px !important; padding: 10px 0 4px !important; }

/* ── Navy accents ── */
div[role="radiogroup"] label:has(input:checked), [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked),
[data-testid="stSidebar"] .st-key-sec_nav div[role="radiogroup"] label:has(input:checked) {
    background: linear-gradient(180deg, #16338a 0%, #0a2463 100%) !important; box-shadow: 0 2px 6px rgba(10,36,99,.28) !important; }
div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #ffffff !important; }
table.snd th.y { background: #0a2463 !important; color: #ffffff !important; font-weight: 600 !important; padding: 7px 10px !important; border-bottom: 0 !important; }
table.snd th.y.first { border-radius: 8px 0 0 8px; }
table.snd th.y:last-child { border-radius: 0 8px 8px 0; }
table.snd tr.bal td { background: rgba(15,23,42,.09) !important; }
table.snd tr.bal td.lbl { color: #0a2463 !important; }
/* Mode (View/Edit): deep dark orange instead of navy */
.st-key-mode_nav div[role="radiogroup"] label:has(input:checked) {
    background: linear-gradient(180deg, #c2410c 0%, #7c2d12 100%) !important; box-shadow: 0 2px 6px rgba(124,45,18,.35) !important; }
.st-key-mode_nav div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #ffffff !important; }
/* Sensitivity's controls row: compact, everything on one line */
.st-key-sn_controls { padding: 6px 12px !important; }
.st-key-sn_controls [data-testid="stWidgetLabel"] p { font-size: 9px !important; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; color: #94a3b8 !important; margin-bottom: 0 !important; }
.st-key-sn_controls div[role="radiogroup"] { padding: 2px !important; }
.st-key-sn_controls div[role="radiogroup"] label { padding: 1px 7px !important; }
.st-key-sn_controls div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 10.5px !important; }
.st-key-sn_controls [data-baseweb="input"], .st-key-sn_controls [data-baseweb="select"] > div { min-height: 25px !important; font-size: 11.5px !important; }
.st-key-sn_controls button { padding: 2px 8px !important; min-height: 25px !important; font-size: 11.5px !important; }
.st-key-sn_controls [data-testid="stVerticalBlock"] { gap: 0.35rem !important; }

/* multiselect pills: dark chip, so the text and the x must be white too */
[data-baseweb="tag"] { background: #0a2463 !important; }
[data-baseweb="tag"] span, [data-baseweb="tag"] div { color: #ffffff !important; }
[data-baseweb="tag"] svg { fill: #ffffff !important; }
</style>
""",
    unsafe_allow_html=True,
)

# Widgets that are not drawn in a run lose their value (e.g. the Years filter while another section is open): keep a copy.
def _gate():
    """If Secrets has [auth] password, ask for it before showing anything: the Edit mode can push to GitHub, so a public URL must not be enough."""
    try:
        pw = st.secrets.get("auth", {}).get("password")
    except Exception:
        pw = None
    if not pw or st.session_state.get("_authed"):
        return
    st.markdown("<div class='page-title' style='margin-top:12vh'>Global SnD</div>", unsafe_allow_html=True)
    typed = st.text_input("Password", type="password", key="_pw_input")
    if typed and typed == pw:
        st.session_state["_authed"] = True
        st.rerun()
    elif typed:
        st.error("Wrong password.")
    st.stop()


_gate()

KEEP = (["section", "snd_page", "snd_span", "snd_mode", "an_view", "an_br_scope", "an_br_start", "br_span", "br_mode", "rv_set",
         "sc_bar_span", "sc_years", "sc_scope", "sn_origin", "sn_vs", "sn_year", "sn_unit", "sn_step_m bags", "sn_step_%", "sn_n"]
        + [scenario._skey(k, u) for k in scenario.ALL_KEYS for u in scenario.UNITS] + ["sc_unit"])
for _k in KEEP:
    if _k not in st.session_state and f"_keep_{_k}" in st.session_state:
        st.session_state[_k] = st.session_state[f"_keep_{_k}"]

with st.sidebar:
    st.markdown("<div class='sb-title'>Global SnD</div>", unsafe_allow_html=True)
    st.markdown("<div class='sb-label'>Section</div>", unsafe_allow_html=True)
    with st.container(key="sec_nav"):
        section = st.radio("Section", ["SnD", "Analysis", "Scenarios", "Sensitivity", "Revisions"], index=0, label_visibility="collapsed", key="section")

if section == "SnD":
    _old = {"Brazil": "Brazil Internal SnD", "Coffee": "Global SnD", "AgriAcies format": "Brazil Internal SnD"}   # old labels
    if st.session_state.get("snd_page") in _old:
        st.session_state["snd_page"] = _old[st.session_state["snd_page"]]
    page = st.radio("Page", ["Global SnD", "Brazil Internal SnD"], horizontal=True, key="snd_page", label_visibility="collapsed")
    if page == "Global SnD":
        snd.render()
    else:
        brazil.render("Brazil SnD")
elif section == "Analysis":
    analytics.render()
elif section == "Scenarios":
    scenario.page()
elif section == "Sensitivity":
    scenario.sensitivity_page()
else:
    revisions.render()

for _k in KEEP:
    if _k in st.session_state:
        st.session_state[f"_keep_{_k}"] = st.session_state[_k]
