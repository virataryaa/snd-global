import streamlit as st

st.set_page_config(page_title="Global SnD", layout="wide", initial_sidebar_state="expanded")

import snd  # noqa: E402  (after set_page_config)

# Strict light theme (same as Cecafe Daily / Coffee Exports): CSS hard-codes colours, no prefers-color-scheme,
# and .streamlit/config.toml pins base="light".
st.markdown(
    """
<style>
[data-testid="stAppViewContainer"], [data-testid="stMain"], .main { background: #fafafa !important; }
[data-testid="stHeader"] { background: #fafafa !important; }
[data-testid="stSidebar"] { background: #f0f2f8 !important; border-right: 1px solid #dfe3ee; }
h1, h2, h3, h4, h5, h6 { color: #0a2463 !important; }
body, .main { color: #1a1a2e; }
.block-container { padding-top: 2.2rem; }

/* Radio as pill / segmented control */
div[role="radiogroup"] { background: #eef0f6; padding: 4px; border-radius: 999px; gap: 2px; display: inline-flex; flex-wrap: wrap; }
div[role="radiogroup"] label { background: transparent !important; border-radius: 999px !important; padding: 4px 12px !important; margin: 0 !important; }
div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child { display: none; }
div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 12px !important; color: #5a6688; }
div[role="radiogroup"] label:has(input:checked) { background: #0a2463 !important; }
div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #ffffff !important; font-weight: 600; }

[data-baseweb="popover"] [data-baseweb="menu"] { background: #ffffff !important; }
[data-baseweb="popover"] [data-baseweb="menu"] li, [data-baseweb="popover"] [data-baseweb="menu"] li * { color: #1a1a2e !important; }
[data-baseweb="select"] { background: #ffffff !important; }
[data-baseweb="select"] > div { background: #ffffff !important; color: #1a1a2e !important; }

.card-desc { color: #5a6688; font-size: 0.82rem; margin-top: -6px; margin-bottom: 10px; }
.chart-head { color: #0a2463; font-weight: 600; font-size: 0.95rem; margin-bottom: 0; }
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {
    background: #ffffff; border: 1px solid #e3e7f0 !important; border-radius: 12px; box-shadow: 0 1px 3px rgba(10,36,99,0.06); }

/* Section selector in the sidebar: large stacked pills; Entry (first) is dark orange when selected */
[data-testid="stSidebarUserContent"] { padding-top: 1rem !important; }
[data-testid="stSidebar"] .st-key-sec_nav div[role="radiogroup"] { display: flex; flex-direction: column; align-items: stretch; width: 100%; border-radius: 22px; padding: 5px; gap: 3px; }
[data-testid="stSidebar"] .st-key-sec_nav div[role="radiogroup"] label { padding: 8px 18px !important; }
[data-testid="stSidebar"] .st-key-sec_nav div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 15px !important; }
[data-testid="stSidebar"] .st-key-sec_nav div[role="radiogroup"] label:first-of-type:has(input:checked) { background: #c2410c !important; }
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { font-size: 10.5px !important; font-weight: 700; letter-spacing: .08em;
    text-transform: uppercase; color: #0a2463 !important; }
[data-testid="stSidebar"] div[role="radiogroup"] { display: flex; flex-wrap: wrap; width: 100%; border-radius: 16px; }
.sb-sep { border-top: 1px solid #dfe3ee; margin: 10px 0 8px; }
.sb-label { font-size: 11px; color: #7a86a8; text-transform: uppercase; letter-spacing: .06em; margin: 6px 0 4px; }
.sb-title { font-family: 'Fraunces', Georgia, serif; font-size: 1.5rem; font-weight: 600; color: #0a2463; margin-bottom: 2px; }
.page-title { color: #0a2463; font-weight: 700; font-size: 1.25rem; margin: 0 0 6px 0; }
.card-title { color: #0a2463; font-weight: 700; font-size: 1rem; margin-bottom: 2px; }
.pill { display: inline-block; background: #e6e9f2; color: #0a2463; font-size: 11px; font-weight: 600;
        padding: 1px 8px; border-radius: 999px; margin-left: 6px; vertical-align: middle; }
.mc-hero-t { color: #ffffff; font-size: 20px; font-weight: 700; letter-spacing: .01em; line-height: 1.3;
    background: linear-gradient(135deg, #050f2c 0%, #0a1d4d 100%); border-radius: 14px;
    padding: 16px 22px; margin-bottom: 10px; box-shadow: 0 2px 10px rgba(10,36,99,.18); }

/* Compact tables (save history) */
.dtab { width: auto; border-collapse: collapse; font-size: 11.5px; line-height: 1.15; background: #ffffff; }
.dtab th { text-align: center; padding: 2px 8px; font-weight: 600; white-space: nowrap; }
.dtab .sub th { background: #0a2463; color: #ffffff; }
.dtab td { text-align: right; padding: 1px 8px; border-bottom: 1px solid #eef0f6; white-space: nowrap; color: #1a1a2e; }
.dtab td.dt { text-align: center; background: #f0f2f8; }
.dtab td.b { font-weight: 700; background: #f6f7fb; }
.dtab td.ts { font-size: 10.5px; font-style: italic; color: #7a86a8; text-align: left; }
</style>
""",
    unsafe_allow_html=True,
)

# Widgets that are not drawn in a run lose their value (e.g. the Years filter while Entry is open): keep a copy.
KEEP = ["section", "snd_span", "en_comm"]
for _k in KEEP:
    if _k not in st.session_state and f"_keep_{_k}" in st.session_state:
        st.session_state[_k] = st.session_state[f"_keep_{_k}"]

with st.sidebar:
    st.markdown("<div class='sb-title'>Global SnD</div>", unsafe_allow_html=True)
    st.markdown("<div class='sb-label'>Section</div>", unsafe_allow_html=True)
    with st.container(key="sec_nav"):
        section = st.radio("Section", ["Entry", "Coffee"], index=1, label_visibility="collapsed", key="section")

if section == "Entry":
    snd.render_entry()
else:
    snd.render()

for _k in KEEP:
    if _k in st.session_state:
        st.session_state[f"_keep_{_k}"] = st.session_state[_k]
