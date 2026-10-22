"""Shared look for the SnD apps (Coffee and Cocoa): strict light theme (CSS hard-codes colours, the repo's
.streamlit/config.toml pins base="light") and the optional password gate."""
import streamlit as st

CSS = """
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
.st-key-co_basis_nav { display: flex; justify-content: flex-end; }
.st-key-snd_page div[role="radiogroup"], .st-key-co_page div[role="radiogroup"] { padding: 2px; }
.st-key-snd_page div[role="radiogroup"] label, .st-key-co_page div[role="radiogroup"] label { padding: 2px 11px !important; }
.st-key-snd_page div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p,
.st-key-co_page div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 11px !important; }
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
.snd-head .t.edit { color: #c2410c !important; }
.page-title, .snd-head .t { color: #0a2463 !important; font-weight: 700; font-size: 1.15rem; margin: 0 0 4px 0; letter-spacing: -.01em; }
.card-title, .chart-head { color: #0a2463; font-weight: 600; font-size: .9rem; margin-bottom: 4px; letter-spacing: -.005em; }
.st-key-edit_bar { position: fixed !important; bottom: 20px; left: 50%; transform: translateX(-50%); z-index: 1000; width: auto !important;
  max-width: 92vw; flex-wrap: nowrap !important; align-items: center !important; justify-content: center !important; gap: 10px !important;
  background: rgba(255,255,255,.55); -webkit-backdrop-filter: blur(22px) saturate(180%); backdrop-filter: blur(22px) saturate(180%);
  border: 1px solid rgba(255,255,255,.7); border-radius: 999px; padding: 8px 10px 8px 20px !important;
  box-shadow: 0 10px 34px rgba(10,36,99,.16), 0 1px 3px rgba(10,36,99,.08), inset 0 1px 0 rgba(255,255,255,.8); animation: ebup .22s ease-out; }
@keyframes ebup { from { opacity: 0; transform: translate(-50%, 14px); } to { opacity: 1; transform: translate(-50%, 0); } }
.st-key-edit_bar > div { margin: 0 !important; align-self: center !important; }
.st-key-edit_bar [data-testid="stMarkdownContainer"], .st-key-edit_bar [data-testid="stMarkdownContainer"] p { margin: 0 !important; display: flex; align-items: center; height: 32px; }
.eb-n { font-size: 13px; font-weight: 600; color: #0a2463; white-space: nowrap; display: inline-flex; align-items: center; gap: 8px; line-height: 1; }
.eb-n::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: #f59e0b; box-shadow: 0 0 8px rgba(245,158,11,.9); }
.st-key-edit_bar input { background: rgba(255,255,255,.7) !important; color: #0f172a !important; }
.st-key-edit_bar [data-baseweb="input"] { border-radius: 999px !important; border: none !important; overflow: hidden; }
.st-key-edit_bar button { height: 32px !important; min-height: 32px !important; border-radius: 999px !important; }
.st-key-edit_bar button[kind="secondary"] { background: rgba(255,255,255,.5) !important; border: 1px solid rgba(10,36,99,.15) !important; }
.st-key-edit_bar button[kind="secondary"] p { color: #0a2463 !important; }
.st-key-edit_bar button[kind="primary"] { background: #d9822b !important; border: none !important; box-shadow: 0 2px 10px rgba(217,130,43,.35); }
.st-key-edit_bar button[kind="primary"] p { color: #ffffff !important; font-weight: 700 !important; }
.st-key-edit_bar_idle { display: none !important; }
.st-key-edit_bar button p { font-size: 12.5px !important; }
.st-key-edit_bar [data-baseweb="input"], .st-key-edit_bar [data-baseweb="base-input"] { min-height: 32px !important; height: 32px !important; }
.st-key-edit_bar input { height: 32px !important; padding: 0 12px !important; font-size: 12.5px !important; }
.grp-hero { text-align: center; color: #0a2463; font-size: .8rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; margin: 18px 0 6px; }
.grp-hero span { display: none; color: #64748b; font-size: .72rem; font-weight: 400; letter-spacing: .02em; text-transform: none; font-style: italic; margin-top: 1px; }
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

/* Edit toolbar: orange Save pill (with pending count), quiet Undo, rounded reason box */
.st-key-snd_save button, .st-key-br_save button { background: #c2410c !important; border: 0 !important; border-radius: 999px !important;
    min-height: 34px; box-shadow: 0 2px 6px rgba(194,65,12,.25); }
.st-key-snd_save button p, .st-key-br_save button p { color: #ffffff !important; font-weight: 600; font-size: 12.5px; }
.st-key-snd_save button:disabled, .st-key-br_save button:disabled { background: #f1d3c2 !important; box-shadow: none; }
.st-key-snd_undo button, .st-key-br_undo button { background: #ffffff !important; border: 1px solid #e3e7f0 !important;
    border-radius: 999px !important; min-height: 34px; }
.st-key-snd_undo button p, .st-key-br_undo button p { color: #5a6688 !important; font-size: 12.5px; }
.st-key-snd_undo button:hover, .st-key-br_undo button:hover { border-color: #c2410c !important; }
[class*="st-key-snd_reason"] [data-baseweb="input"], [class*="st-key-br_reason"] [data-baseweb="input"] {
    background: #ffffff !important; border: 1px solid #e3e7f0 !important; border-radius: 999px !important; min-height: 34px; }
[class*="st-key-snd_reason"] input, [class*="st-key-br_reason"] input { background: #ffffff !important; font-size: 12.5px; padding-left: 14px; }

.st-key-snd_save button, .st-key-br_save button, .st-key-snd_undo button, .st-key-br_undo button { padding: 0 20px !important; }
/* Mode (View/Edit): orange, like the calendar's Entry tab */
.st-key-mode_nav div[role="radiogroup"] label:has(input:checked) { background: #d9822b !important; }
.st-key-mode_nav [data-testid="stRadio"], .st-key-mode_nav [role="radiogroup"] { margin-left: auto; }
.st-key-mode_nav { display: flex; justify-content: flex-end; }
.st-key-mode_nav [data-testid="stButton"] { margin-left: auto; width: auto; }
[class*="_mode_to_"] button { border-radius: 999px !important; min-height: 27px !important; height: 27px; padding: 0 14px !important; font-weight: 600 !important;
  letter-spacing: .02em; transition: box-shadow .2s, transform .2s; }
[class*="_mode_to_"] button p { font-size: 12px !important; font-weight: 600 !important; }
[class*="_mode_to_edit"] button { background: linear-gradient(180deg, #ffffff, #fff4e8) !important; color: #c2410c !important;
  border: 1px solid rgba(217,130,43,.5) !important; box-shadow: 0 0 0 3px rgba(217,130,43,.09), 0 3px 12px rgba(217,130,43,.22); }
[class*="_mode_to_edit"] button:hover { box-shadow: 0 0 0 4px rgba(217,130,43,.14), 0 4px 16px rgba(217,130,43,.32); transform: translateY(-1px); }
[class*="_mode_to_view"] button { background: linear-gradient(180deg, #ffffff, #eef2fb) !important; color: #0a2463 !important;
  border: 1px solid rgba(10,36,99,.32) !important; box-shadow: 0 0 0 3px rgba(10,36,99,.06), 0 3px 12px rgba(10,36,99,.16); }
[class*="_mode_to_view"] button:hover { box-shadow: 0 0 0 4px rgba(10,36,99,.10), 0 4px 16px rgba(10,36,99,.26); transform: translateY(-1px); }
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
/* Cocoa edit toolbar: same pills as the coffee pages */
.st-key-co_save button { background: #c2410c !important; border: 0 !important; border-radius: 999px !important; min-height: 34px;
    box-shadow: 0 2px 6px rgba(194,65,12,.25); padding: 0 20px !important; }
.st-key-co_save button p { color: #ffffff !important; font-weight: 600; font-size: 12.5px; }
.st-key-co_save button:disabled { background: #f1d3c2 !important; box-shadow: none; }
.st-key-co_undo button { background: #ffffff !important; border: 1px solid #e3e7f0 !important; border-radius: 999px !important;
    min-height: 34px; padding: 0 20px !important; }
.st-key-co_undo button p { color: #5a6688 !important; font-size: 12.5px; }
.st-key-co_undo button:hover { border-color: #c2410c !important; }
[class*="st-key-co_reason"] [data-baseweb="input"] { background: #ffffff !important; border: 1px solid #e3e7f0 !important;
    border-radius: 999px !important; min-height: 34px; }
[class*="st-key-co_reason"] input { background: #ffffff !important; font-size: 12.5px; padding-left: 14px; }
</style>
"""


def mode_switch(key: str) -> str:
    """A single soft-glow button: shows 'Edit' while viewing and 'View' while editing. Returns the current mode."""
    cur = st.session_state.get(key, "View")
    nxt = "Edit" if cur == "View" else "View"

    def flip():
        st.session_state[key] = nxt
    st.button(f"{nxt} Mode", key=f"{key}_to_{nxt.lower()}", on_click=flip)
    return cur


def gate(title: str):
    """If Secrets has [auth] password, ask for it before showing anything: the Edit mode can push to GitHub, so a public URL must not be enough."""
    try:
        pw = st.secrets.get("auth", {}).get("password")
    except Exception:
        pw = None
    if not pw or st.session_state.get("_authed"):
        return
    st.markdown(f"<div class='page-title' style='margin-top:12vh'>{title}</div>", unsafe_allow_html=True)
    typed = st.text_input("Password", type="password", key="_pw_input")
    if typed and typed == pw:
        st.session_state["_authed"] = True
        st.rerun()
    elif typed:
        st.error("Wrong password.")
    st.stop()
