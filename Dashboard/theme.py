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
/* glass sidebar */
[data-testid="stSidebar"] { background: linear-gradient(160deg, rgba(246,248,253,.92) 0%, rgba(233,238,248,.88) 55%, rgba(240,236,246,.9) 100%) !important;
  -webkit-backdrop-filter: blur(24px) saturate(160%); backdrop-filter: blur(24px) saturate(160%);
  border-right: 1px solid rgba(255,255,255,.75) !important; box-shadow: inset -1px 0 0 rgba(10,36,99,.06), 6px 0 28px rgba(10,36,99,.06); }
[data-testid="stSidebar"] div[role="radiogroup"] { background: rgba(255,255,255,.55) !important; border: 1px solid rgba(255,255,255,.85);
  box-shadow: 0 1px 2px rgba(10,36,99,.05), inset 0 1px 0 rgba(255,255,255,.9); -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px); }
[data-testid="stSidebar"] div[role="radiogroup"] label { transition: background .15s; }
[data-testid="stSidebar"] div[role="radiogroup"] label:not(:has(input:checked)):hover { background: rgba(10,36,99,.06) !important; }
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) { background: linear-gradient(180deg, #13307a, #0a2463) !important;
  box-shadow: 0 2px 8px rgba(10,36,99,.28), inset 0 1px 0 rgba(255,255,255,.18); }
[data-testid="stSidebar"] .sb-sep { border-top: 1px solid rgba(10,36,99,.08); box-shadow: 0 1px 0 rgba(255,255,255,.8); }
[data-testid="stSidebar"] [data-testid="stCheckbox"], [data-testid="stSidebar"] .stToggle { background: rgba(255,255,255,.5); border: 1px solid rgba(255,255,255,.85);
  border-radius: 12px; padding: 6px 10px; box-shadow: 0 1px 2px rgba(10,36,99,.04), inset 0 1px 0 rgba(255,255,255,.9); }
[data-testid="stSidebar"] [data-baseweb="checkbox"] [role="checkbox"], [data-testid="stSidebar"] label[data-baseweb="checkbox"] > div:first-child {
  box-shadow: inset 0 1px 2px rgba(10,36,99,.15); }
/* section list: plain vertical nav, no oval container */
.st-key-section div[role="radiogroup"], .st-key-co_section div[role="radiogroup"] { background: none !important; border: 0 !important; box-shadow: none !important;
  -webkit-backdrop-filter: none !important; backdrop-filter: none !important; padding: 0 !important; display: flex !important; flex-direction: column; gap: 2px; width: 100%; }
.st-key-section div[role="radiogroup"] label, .st-key-co_section div[role="radiogroup"] label { border-radius: 9px !important; padding: 6px 12px !important; width: 100%; }
.st-key-section div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p,
.st-key-co_section div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 13px !important; }
[data-testid="stSidebar"] [data-baseweb="checkbox"] p { font-size: 12.5px; color: #3a4466; }

/* Page text and cards */
.snd-head .t.edit { color: #c2410c !important; }
.page-title, .snd-head .t { color: #0a2463 !important; font-weight: 700; font-size: 1.15rem; margin: 0 0 4px 0; letter-spacing: -.01em; }
.card-title, .chart-head { color: #0a2463; font-weight: 600; font-size: .9rem; margin-bottom: 4px; letter-spacing: -.005em; }
.st-key-edit_bar { position: fixed !important; bottom: 20px; left: 50%; transform: translateX(-50%); z-index: 1000; width: auto !important;
  max-width: 92vw; flex-wrap: nowrap !important; align-items: center !important; justify-content: center !important; gap: 10px !important;
  background: rgba(255,255,255,.72); -webkit-backdrop-filter: blur(22px) saturate(180%); backdrop-filter: blur(22px) saturate(180%);
  border: 1px solid rgba(255,255,255,.7); border-radius: 999px; padding: 11px 13px 11px 24px !important;
  box-shadow: 0 0 0 1px rgba(217,130,43,.22), 0 14px 40px rgba(10,36,99,.22), 0 2px 6px rgba(10,36,99,.10), inset 0 1px 0 rgba(255,255,255,.8); animation: ebup .22s ease-out; }
@keyframes ebup { from { opacity: 0; transform: translate(-50%, 14px); } to { opacity: 1; transform: translate(-50%, 0); } }
.st-key-edit_bar > div { margin: 0 !important; align-self: center !important; }
.st-key-edit_bar [data-testid="stMarkdownContainer"], .st-key-edit_bar [data-testid="stMarkdownContainer"] p { margin: 0 !important; display: flex; align-items: center; height: 38px; }
.st-key-edit_bar button p, .st-key-edit_bar input { font-size: 14px !important; }
.eb-n { font-size: 14px; font-weight: 600; color: #0a2463; white-space: nowrap; display: inline-flex; align-items: center; gap: 8px; line-height: 1; }
.eb-n::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: #f59e0b; box-shadow: 0 0 8px rgba(245,158,11,.9); }
.st-key-edit_bar input { background: rgba(255,255,255,.7) !important; color: #0f172a !important; }
.st-key-edit_bar [data-baseweb="input"] { border-radius: 999px !important; border: none !important; overflow: hidden; }
.st-key-edit_bar button { height: 38px !important; min-height: 38px !important; padding: 0 20px !important; border-radius: 999px !important; }
.st-key-edit_bar button[kind="secondary"] { background: rgba(255,255,255,.5) !important; border: 1px solid rgba(10,36,99,.15) !important; }
.st-key-edit_bar button[kind="secondary"] p { color: #0a2463 !important; }
.st-key-edit_bar button[kind="primary"] { background: linear-gradient(180deg, #14857c, #0f766e) !important; border: none !important; box-shadow: 0 2px 10px rgba(15,118,110,.35); }
.st-key-edit_bar button[kind="primary"]:hover { background: #115e59 !important; }
.st-key-edit_bar button[kind="primary"] p { color: #ffffff !important; font-weight: 700 !important; }
[class*="_addyr"] button { border-radius: 999px !important; min-height: 32px !important; height: 32px; padding: 0 18px !important;
  background: linear-gradient(180deg, #ffffff, #f4f6fb) !important; border: 1px dashed rgba(10,36,99,.35) !important; color: #0a2463 !important;
  box-shadow: 0 1px 4px rgba(10,36,99,.08); transition: all .18s; }
[class*="_addyr"] button p { font-size: 12.5px !important; font-weight: 600 !important; }
[class*="_addyr"] button:hover { border-color: #d9822b !important; color: #c2410c !important; box-shadow: 0 0 0 3px rgba(217,130,43,.12), 0 3px 10px rgba(217,130,43,.2); }
[class*="_addyr"] button:hover p { color: #c2410c !important; }
.st-key-edit_bar_idle { display: none !important; }
.st-key-edit_bar button p { font-size: 12.5px !important; }
.st-key-edit_bar [data-baseweb="input"], .st-key-edit_bar [data-baseweb="base-input"] { min-height: 38px !important; height: 38px !important; }
.st-key-edit_bar input { height: 38px !important; padding: 0 12px !important; font-size: 12.5px !important; }
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


# ── Ice theme (same as LSEG COT_ALL / Daily Miner) ────────────────────────────
# Injected last on every run, so it sits over CSS above and over each page's own block (e.g. Aggregated Exports).
# ICE_TABLE is plain CSS so it can also go into the SnD table component's iframe (tableedit.css_of).
FONTS = ("@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@600&family=Inter:wght@400;500;600;700"
         "&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');\n")
HEAD_FONT = "'Plus Jakarta Sans','Inter',system-ui,sans-serif"

ICE_TABLE = f"""
/* icy tables: frosted card, pale gradient headers, hairline rows, zebra, soft hover */
.snd-wrap, .tbl-wrap {{ background: #ffffff !important; border: 1px solid rgba(43,74,138,.12) !important; border-radius: 14px !important;
  box-shadow: 0 1px 2px rgba(10,36,99,.04), 0 8px 24px rgba(10,36,99,.06) !important; }}
table.snd, .tbl, .dtab {{ font-family: 'Inter', system-ui, sans-serif; color: #1a1a2e !important; font-variant-numeric: tabular-nums; }}
table.snd td, .tbl td, .dtab td {{ border-bottom: 1px solid rgba(43,74,138,.07) !important; }}
table.snd th.y, .tbl th, .dtab th, .dtab .sub th {{ background: linear-gradient(180deg, #f7f9fd, #edf2fa) !important; color: #1e3a6e !important;
  font-family: {HEAD_FONT}; font-size: 10.5px !important; font-weight: 700 !important; letter-spacing: .06em;
  border-bottom: 1px solid rgba(43,74,138,.12) !important; }}
table.snd th.y {{ padding: 6px 9px !important; }}
table.snd th.y.first {{ border-radius: 0 !important; }} table.snd th.y:last-child {{ border-radius: 0 !important; }}
table.snd tr.comm th {{ background: linear-gradient(90deg, rgba(43,74,138,.10) 0%, rgba(43,74,138,.035) 55%, rgba(43,74,138,0) 100%) !important;
  color: #0a2463 !important; font-family: {HEAD_FONT}; font-size: 10.5px !important; font-weight: 800 !important; letter-spacing: .14em !important;
  padding: 8px 12px 6px !important; }}
table.snd td.lbl, .tbl td.lbl {{ color: #1e3a6e !important; font-weight: 600; }}
.tbl td.lbl, .tbl td.x, .dtab td.dt {{ background: #f7f9fd !important; border-right: 1px solid rgba(43,74,138,.10) !important; }}
.tbl td.x {{ border-left: 1px solid rgba(43,74,138,.22) !important; }}
table.snd tr:nth-child(even) > td, .tbl tr:nth-child(even) > td, .dtab tr:nth-child(even) > td {{ background-color: #f9fbfe; }}
table.snd tr:hover > td, .tbl tr:hover > td, .dtab tr:hover > td {{ background-color: rgba(43,74,138,.06); }}
table.snd tr.b td {{ background: #f7f9fd !important; }}
table.snd tr.bal td {{ background: #edf2fa !important; color: #0a2463 !important; border-top: 1px solid rgba(43,74,138,.14) !important;
  border-bottom: 1px solid rgba(43,74,138,.14) !important; }}
table.snd tr.soft td, table.snd tr.meta td {{ color: #7a86a8 !important; }}
table.snd td.neg, .tbl td.down {{ color: #c94a4a !important; }}
.tbl td.up {{ color: #1f9d6f !important; }}
.tbl tr.ref td {{ background: #f5f7fc !important; color: #5a6688 !important; }}
.tbl tr.sep td {{ background: rgba(43,74,138,.06) !important; }}
.snd-bar {{ background: linear-gradient(180deg, #f7f9fd, #edf2fa) !important; color: #1e3a6e !important; font-family: {HEAD_FONT};
  font-size: 10.5px !important; font-weight: 800 !important; letter-spacing: .14em !important; padding: 9px 14px !important;
  border: 1px solid rgba(43,74,138,.12); border-bottom: 0; border-radius: 14px 14px 0 0 !important; }}
.snd-bar + .snd-wrap {{ border-radius: 0 0 14px 14px !important; }}
.snd-head .t, .page-title {{ font-family: {HEAD_FONT}; font-weight: 800 !important; color: #0a2463 !important; }}
"""

ICE = f"""
<style>
{FONTS}
:root {{ color-scheme: light !important; }}
html, body, [class*="css"], [data-testid="stAppViewContainer"], .stMarkdown, button, input, textarea {{
  font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif !important; -webkit-font-smoothing: antialiased; }}
.stTabs [data-baseweb="tab"] p, div[role="radiogroup"] label p, [data-testid="stCaptionContainer"],
.chart-head, .card-title, .grp-hero {{ font-family: {HEAD_FONT} !important; letter-spacing: .01em; }}
.chart-head, .card-title {{ font-weight: 700 !important; color: #0a2463 !important; }}
.sb-title {{ font-family: 'Fraunces', Georgia, serif !important; }}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p, .sb-label, .mc-lbl {{ font-family: {HEAD_FONT} !important; font-size: 10.5px !important;
  font-weight: 700 !important; letter-spacing: .14em !important; text-transform: uppercase; color: #7a86a8 !important; }}
[data-testid="stMain"] [data-testid="stWidgetLabel"] p {{ font-family: {HEAD_FONT} !important; font-size: 12.5px !important; font-weight: 600 !important;
  color: #1e3a6e !important; letter-spacing: .01em; }}

/* pill tracks (tabs, radios): frosted glass, soft navy gradient pick, lift on hover */
div[role="radiogroup"], .stTabs [data-baseweb="tab-list"] {{
  background: linear-gradient(160deg, rgba(250,252,255,.97), rgba(236,242,251,.93) 60%, rgba(229,237,249,.9)) !important;
  border: 1px solid rgba(43,74,138,.14) !important; box-shadow: 0 4px 16px rgba(30,58,110,.07), inset 0 1px 0 rgba(255,255,255,.95) !important; }}
div[role="radiogroup"] label:has(input:checked), .stTabs [aria-selected="true"],
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
  background: linear-gradient(180deg, #2b4a8a, #1e3a6e) !important; color: #ffffff !important;
  box-shadow: 0 2px 8px rgba(30,58,110,.28), inset 0 1px 0 rgba(255,255,255,.18) !important; }}
div[role="radiogroup"] label, .stTabs [data-baseweb="tab"] {{ transition: background .15s, transform .15s; }}
div[role="radiogroup"] label:not(:has(input:checked)):hover, .stTabs [data-baseweb="tab"]:not([aria-selected="true"]):hover {{
  background: rgba(43,74,138,.07) !important; transform: translateY(-1px); }}
button[kind="pillsActive"], button[kind="segmented_controlActive"], [data-testid="stBaseButton-pillsActive"] {{
  background: linear-gradient(180deg, #2b4a8a, #1e3a6e) !important; border-color: #1e3a6e !important; }}

/* dropdowns: glass pill, lift on hover, wine focus ring + caret */
[data-testid="stMain"] [data-baseweb="select"], [data-testid="stSidebar"] [data-baseweb="select"] {{ background: transparent !important; box-shadow: none !important; }}
[data-baseweb="select"] > div {{ background: linear-gradient(180deg, rgba(255,255,255,.78), rgba(238,242,250,.62)) !important;
  -webkit-backdrop-filter: blur(14px) saturate(170%); backdrop-filter: blur(14px) saturate(170%);
  border: 1px solid rgba(255,255,255,.9) !important; border-radius: 999px !important; min-height: 34px;
  box-shadow: 0 1px 2px rgba(10,36,99,.06), 0 6px 18px rgba(10,36,99,.08), inset 0 1px 0 rgba(255,255,255,.95); transition: box-shadow .18s, transform .18s; }}
[data-baseweb="select"] > div:hover {{ box-shadow: 0 0 0 3px rgba(10,36,99,.07), 0 8px 22px rgba(10,36,99,.14), inset 0 1px 0 rgba(255,255,255,.95); transform: translateY(-1px); }}
[data-baseweb="select"] > div:focus-within {{ box-shadow: 0 0 0 3px rgba(123,30,58,.16), 0 8px 22px rgba(10,36,99,.14) !important; }}
[data-baseweb="select"] svg {{ fill: #7b1e3a !important; }}
[data-baseweb="select"] > div:has([data-baseweb="tag"]) {{ border-radius: 16px !important; padding: 4px 6px !important; }}
[data-baseweb="tag"] {{ height: 24px !important; margin: 2px 3px !important; border-radius: 8px !important; background: #1e3a6e !important; }}
[data-baseweb="popover"] [data-baseweb="menu"], [data-baseweb="popover"] ul {{
  background: rgba(255,255,255,.82) !important; -webkit-backdrop-filter: blur(18px) saturate(170%); backdrop-filter: blur(18px) saturate(170%);
  border: 1px solid rgba(255,255,255,.9) !important; border-radius: 14px !important; box-shadow: 0 14px 40px rgba(10,36,99,.18) !important; }}
[data-baseweb="popover"] li:hover {{ background: rgba(43,74,138,.07) !important; }}
[data-baseweb="popover"] li[aria-selected="true"] {{ background: rgba(123,30,58,.10) !important; }}

/* cards, charts, expanders, buttons */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]), [class*="st-key-mc_card_"] {{
  background: #ffffff !important; border: 1px solid rgba(43,74,138,.10) !important; border-radius: 18px !important;
  box-shadow: 0 1px 2px rgba(10,36,99,.04), 0 4px 14px rgba(30,58,110,.06), inset 0 1px 0 #ffffff !important; }}
[data-testid="stMain"] [data-testid="stPlotlyChart"] {{ background: #ffffff; border: 1px solid rgba(43,74,138,.10); border-radius: 18px; padding: 6px 8px;
  overflow: hidden; box-shadow: 0 1px 2px rgba(10,36,99,.04), 0 4px 14px rgba(30,58,110,.06), inset 0 1px 0 #ffffff; transition: box-shadow .2s; }}
[data-testid="stMain"] [data-testid="stPlotlyChart"]:hover {{ box-shadow: 0 1px 2px rgba(10,36,99,.05), 0 8px 20px rgba(30,58,110,.09), inset 0 1px 0 #ffffff; }}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stPlotlyChart"], [class*="st-key-mc_card_"] [data-testid="stPlotlyChart"] {{
  border: 0 !important; box-shadow: none !important; padding: 0 !important; background: transparent !important; }}   /* already inside a card */
div[data-testid="stExpander"] {{ background: #ffffff !important; border: 1px solid rgba(43,74,138,.10) !important; border-radius: 12px !important; overflow: hidden; }}
div[data-testid="stExpander"] summary {{ background: linear-gradient(90deg, rgba(43,74,138,.07) 0%, rgba(43,74,138,.025) 55%, rgba(43,74,138,0) 100%) !important; }}
div[data-testid="stExpander"] summary p {{ font-family: {HEAD_FONT} !important; font-size: 13.5px !important; font-weight: 700 !important; color: #0a2463 !important; }}
.stButton > button, .stDownloadButton > button {{ border-radius: 999px; border: 1px solid rgba(43,74,138,.18); background: linear-gradient(180deg, #ffffff, #eef2fa);
  color: #0a2463; font-weight: 600; box-shadow: 0 1px 2px rgba(10,36,99,.06); transition: box-shadow .18s, transform .18s; }}
.stButton > button:hover, .stDownloadButton > button:hover {{ transform: translateY(-1px); box-shadow: 0 8px 20px rgba(10,36,99,.14); border-color: rgba(43,74,138,.35); color: #0a2463; }}
/* use the full width: small side gutters instead of a centred 1500px column */
.block-container {{ max-width: 100% !important; padding-left: 1.6rem !important; padding-right: 1.6rem !important; }}
/* Edit-mode toggles: small, under the mode button */
.st-key-edit_opts {{ margin-top: 4px; }}
.st-key-edit_opts [data-testid="stWidgetLabel"] p, .st-key-edit_opts label p {{ font-size: 11px !important; color: #5a6688 !important; font-weight: 600 !important; }}
/* Sidebar: Aggregated Exports set apart (space above, amber accent) */
.st-key-section div[role="radiogroup"] label:last-of-type {{ margin-top: 22px !important; background: linear-gradient(180deg, #ffffff, #f3f6fc) !important;
  border: 1px solid rgba(43,74,138,.22) !important; border-left: 3px solid #c98a1f !important; box-shadow: 0 2px 10px rgba(30,58,110,.10) !important; }}
.st-key-section div[role="radiogroup"] label:last-of-type div[data-testid="stMarkdownContainer"] p {{ color: #0a2463 !important; font-weight: 700 !important; }}
.st-key-section div[role="radiogroup"] label:last-of-type:has(input:checked) {{ background: linear-gradient(180deg, #2b4a8a, #1e3a6e) !important; }}
.st-key-section div[role="radiogroup"] label:last-of-type:has(input:checked) div[data-testid="stMarkdownContainer"] p {{ color: #ffffff !important; }}
{ICE_TABLE}
</style>
"""

# Chart look: transparent card, Inter, hairline navy grid, COT palette
PALETTE = ["#0a2463", "#1f8a9c", "#c98a1f", "#1f9d6f", "#c94a4a", "#7a4fb0", "#8a94a8", "#e8770a"]


def ice_charts():
    """Register the 'ice' Plotly template and make it the default."""
    import plotly.graph_objects as go
    import plotly.io as pio
    if "ice" not in pio.templates:
        t = go.layout.Template(pio.templates["plotly_white"])
        ax = dict(gridcolor="rgba(10,36,99,0.08)", zerolinecolor="rgba(0,0,0,0.12)", linecolor="rgba(0,0,0,0.08)",
                  tickfont=dict(size=10, color="#4a5578"), title=dict(font=dict(color="#1e3a6e")))
        t.layout.update(font=dict(family="Inter, system-ui, -apple-system, Segoe UI, sans-serif", color="#1a1a2e", size=11),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", colorway=PALETTE, xaxis=ax, yaxis=ax,
                        legend=dict(font=dict(family="Plus Jakarta Sans, Inter, sans-serif", size=10.5, color="#1e3a6e")),
                        hoverlabel=dict(bgcolor="#ffffff", bordercolor="rgba(43,74,138,0.25)",
                                        font=dict(family="Inter, sans-serif", size=11, color="#1a1a2e")))
        pio.templates["ice"] = t
    pio.templates.default = "ice"


def edit_toggles():
    """Edit mode only: two small toggles under the mode button (record flags on by default)."""
    with st.container(key="edit_opts", horizontal=True, horizontal_alignment="right", gap="small"):
        st.session_state.setdefault("lim_flags", True)              # seeded, not value=, so a kept value never clashes
        st.toggle("Record flags", key="lim_flags", help="Red on cells past the 10-year high/low, outline near it")
        st.toggle("Only editable", key="rows_only", help="Hide the calculated rows")


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
