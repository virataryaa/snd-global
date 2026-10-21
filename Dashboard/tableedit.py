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


_TD = re.compile(r"<td(?: class='([^']*)')?([^>]*)>(.*?)</td>", re.S)


def _text(cell: str) -> str:
    return re.sub(r"<[^>]+>", "", cell.split("<span class='rev-dot", 1)[0]).strip()


def mark_moved(live: str, ref: str) -> str:
    """Compare the live table (with unsaved edits) to the saved one cell by cell; calculated cells whose number moved get class 'mv'.
    Both tables come from the same layout, so their <td>s pair up in order."""
    a, b = list(_TD.finditer(live)), list(_TD.finditer(ref))
    if len(a) != len(b):
        return live
    out, pos = [], 0
    for m, n in zip(a, b):
        cls = m.group(1) or ""
        if "spark-td" in cls.split() or "ed" in cls.split() or _text(m.group(3)) == _text(n.group(3)):
            continue
        out.append(live[pos:m.start()])
        out.append(f"<td class='{(cls + ' mv').strip()}'{m.group(2)}>{m.group(3)}</td>")
        pos = m.end()
    out.append(live[pos:])
    return "".join(out)


def editable_table(html: str, css: str, key: str, epoch: int, editable: bool = True, edits=None):
    return _COMP(html=html, css=css, editable=editable, epoch=epoch, edits=edits or {}, key=key, default={})
