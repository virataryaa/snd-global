import streamlit as st

st.set_page_config(page_title="Global SnD", layout="wide", initial_sidebar_state="expanded")

import analytics  # noqa: E402  (after set_page_config)
import brazil  # noqa: E402
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

/* Sidebar: quiet section switch (Entry stays the one warm accent) */
[data-testid="stSidebarUserContent"] { padding-top: 1.2rem !important; }
[data-testid="stSidebar"] .st-key-sec_nav div[role="radiogroup"] { display: flex; flex-direction: column; align-items: stretch; width: 100%; border-radius: 10px; padding: 3px; gap: 2px; }
[data-testid="stSidebar"] .st-key-sec_nav div[role="radiogroup"] label { padding: 7px 14px !important; }
[data-testid="stSidebar"] .st-key-sec_nav div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 13.5px !important; }
[data-testid="stSidebar"] .st-key-sec_nav div[role="radiogroup"] label:first-of-type:has(input:checked) { background: #fff1e6 !important; }
[data-testid="stSidebar"] .st-key-sec_nav div[role="radiogroup"] label:first-of-type:has(input:checked) p { color: #c2410c !important; }
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
</style>
""",
    unsafe_allow_html=True,
)

# Widgets that are not drawn in a run lose their value (e.g. the Years filter while Entry is open): keep a copy.
KEEP = ["section", "snd_span", "snd_mode", "en_comm", "an_view", "an_su_comm", "an_br_scope", "an_gr_scope", "br_span", "br_mode", "br_view"]
for _k in KEEP:
    if _k not in st.session_state and f"_keep_{_k}" in st.session_state:
        st.session_state[_k] = st.session_state[f"_keep_{_k}"]

with st.sidebar:
    st.markdown("<div class='sb-title'>Global SnD</div>", unsafe_allow_html=True)
    st.markdown("<div class='sb-label'>Section</div>", unsafe_allow_html=True)
    with st.container(key="sec_nav"):
        section = st.radio("Section", ["Entry", "Coffee", "Brazil", "Analytics"], index=1, label_visibility="collapsed", key="section")

if section == "Entry":
    snd.render_entry()
elif section == "Brazil":
    brazil.render()
elif section == "Analytics":
    analytics.render()
else:
    snd.render()

for _k in KEEP:
    if _k in st.session_state:
        st.session_state[f"_keep_{_k}"] = st.session_state[_k]
