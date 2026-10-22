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


LIMIT_ROWS = ("consumption", "s/u", "stock/use", "stocks to use", "stu", "production", "closing stock", "end season stock",
              "stock proxy", "grind", "stat crop", "total")
_SKIP = ("change", "share", "first", "growth", "chg", "%", "carry", "smuggl", "held")
_TR = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_TH = re.compile(r"<th class='y([^']*)'>(.*?)</th>", re.S)


def _num(t):
    t = t.replace(",", "").replace("%", "").strip()
    neg = t.startswith("(") and t.endswith(")")
    try:
        v = float(t.strip("()"))
    except ValueError:
        return None
    return -v if neg else v


def mark_limits(live: str, n: int = 10, edge: float = 0.05) -> str:
    """Edit mode: forecast years and changed cells in level rows (consumption, S/U, production, stocks, grind) are checked against the
    previous n actual years of the same row. Past the 10y high/low -> 'lim hi|lo' (red shine); within 5% of the range from an
    end -> 'edge'. A hover title gives the record, the year it was set and the gap."""
    years, est = [], []
    out, pos = [], 0
    for tr in _TR.finditer(live):
        ths = _TH.findall(tr.group(1))
        if ths:
            years = [re.sub(r"<[^>]+>|\*", "", t).strip() for c, t in ths if "spark" not in c and "first" not in c]
            est = ["fc" in c or "*" in t for c, t in ths if "spark" not in c and "first" not in c]
            continue
        cells = [m for m in _TD.finditer(tr.group(1)) if "spark-td" not in (m.group(1) or "").split()]
        if len(cells) != len(years) + 1:
            continue
        label = _text(cells[0].group(3)).lower()
        if not any(k in label for k in LIMIT_ROWS) or any(k in label for k in _SKIP):
            continue
        vals = [_num(_text(m.group(3))) for m in cells[1:]]
        base = tr.start(1)
        for j, m in enumerate(cells[1:]):
            cls = m.group(1) or ""
            v = vals[j]
            if v is None or not (est[j] or {"mv", "chg"} & set(cls.split())):
                continue
            hist = [(years[i], vals[i]) for i in range(j) if not est[i] and vals[i] is not None][-n:]
            if len(hist) < 5:
                continue
            (ylo, lo), (yhi, hi) = min(hist, key=lambda p: p[1]), max(hist, key=lambda p: p[1])
            rng = hi - lo or abs(hi) or 1
            if v > hi:
                add, tip = "lim hi", f"Above 10y high {hi:,.1f} ({yhi}) by {v - hi:,.1f}"
            elif v < lo:
                add, tip = "lim lo", f"Below 10y low {lo:,.1f} ({ylo}) by {lo - v:,.1f}"
            elif v >= hi - edge * rng:
                add, tip = "edge", f"Near 10y high {hi:,.1f} ({yhi})"
            elif v <= lo + edge * rng:
                add, tip = "edge", f"Near 10y low {lo:,.1f} ({ylo})"
            else:
                continue
            out.append(live[pos:base + m.start()])
            out.append(f"<td class='{(cls + ' ' + add).strip()}'{m.group(2)} title='{tip} · range {lo:,.1f}–{hi:,.1f}'>{m.group(3)}</td>")
            pos = base + m.end()
    out.append(live[pos:])
    return "".join(out)


def editable_table(html: str, css: str, key: str, epoch: int, editable: bool = True, edits=None):
    return _COMP(html=html, css=css, editable=editable, epoch=epoch, edits=edits or {}, key=key, default={})
