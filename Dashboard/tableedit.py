"""The editable SnD table: a small Streamlit component (Dashboard/snd_table_component) that shows the styled HTML table and lets the
input cells be typed over in place. Edits come back as {key: number|None}; the page recalculates and sends the table again."""
import re
from pathlib import Path

import streamlit.components.v1 as components

_COMP = components.declare_component("snd_table", path=str(Path(__file__).resolve().parent / "snd_table_component"))
FONT = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');\n"


def css_of(style_block: str) -> str:
    """The CSS text of a '<style>...</style>' string, with the font import in front."""
    return FONT + re.sub(r"</?style>", "", style_block)


def editable_table(html: str, css: str, key: str, epoch: int, editable: bool = True):
    return _COMP(html=html, css=css, editable=editable, epoch=epoch, key=key, default={})
