"""Coffee SnD: the 'SnD ETG' table (Arabica, Robusta, Global) from the inputs in Database/coffee_snd.csv.

Inputs are each origin's production and the consumption, per crop year (Jul-Jun), in million 60 kg bags. Everything else is
worked out here the way the Excel sheet does: production = sum of the origins, balance = production - consumption,
end stock = last year's end stock + balance (the first year's end stock is an input), S/U = end stock / consumption.
"""
import html
import io
import json
import re
from datetime import date
from pathlib import Path

MODE_SLOT = None   # sidebar container app.py reserves for Mode (above the section nav)

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ghstore as gh

ROOT = Path(__file__).resolve().parent.parent
CSV, META = ROOT / "Database" / "coffee_snd.csv", ROOT / "Database" / "coffee_snd_meta.json"
CSV_PATH, META_PATH = "Database/coffee_snd.csv", "Database/coffee_snd_meta.json"            # paths in the repo
ORIGINS = {
    "Arabica": ["Brazil", "Colombia", "Honduras", "Super 5", "Ethiopia", "Peru", "Others"],
    "Robusta": ["Vietnam", "Brazil", "Indonesia", "India", "Uganda", "Cote d'Ivoire", "Others"],
}
TZ = "Europe/Amsterdam"
NAVY, TEAL, GREEN, RED, AMBER, GREY = "#0a2463", "#1f8a9c", "#1f9d6f", "#c0392b", "#b7791f", "#94a3b8"
INK, AXIS, GRID = "#1d1d1f", "#86868b", "rgba(0,0,0,0.05)"

CSS = """
<style>
.snd-wrap { background: #ffffff; border: 1px solid #e6e9f0; border-radius: 12px; padding: 3px 5px 6px; margin-bottom: 12px;
            box-shadow: 0 1px 2px rgba(15,23,42,.04); overflow-x: auto; width: fit-content; max-width: 100%; }
table.snd { border-collapse: separate; border-spacing: 0; width: auto; font-size: 12px; color: #0f172a;
            font-variant-numeric: tabular-nums; letter-spacing: .005em; }
table.snd td, table.snd th { padding: 2px 9px; text-align: center; white-space: nowrap; line-height: 1.3; }
table.snd td { min-width: 46px; }
table.snd td.lbl { text-align: left; color: #475569; padding-left: 12px; min-width: 150px; }
table.snd td { border: 0; border-bottom: 1px solid #f1f3f7; }
table.snd th { border: 0; }
/* title strip + context line */
table.snd tr.meta td { color: #64748b; font-size: 11.5px; border-bottom: 0; padding: 6px 12px 10px; }
table.snd tr.meta td.lbl { color: #94a3b8; }
/* commodity header: label left, a thin accent rule under it */
table.snd tr.comm th { text-align: left; font-size: 12px; font-weight: 700; color: #ffffff; letter-spacing: .12em; text-transform: uppercase;
                       padding: 5px 12px; background: linear-gradient(90deg, #0a1d4d 0%, #0a2463 100%); }
table.snd tr.gap td { border: 0; height: 8px; padding: 0; }
/* year header */
table.snd th.y { font-size: 11px; font-weight: 600; color: #0a2463; padding: 4px 9px; background: #eef2fb; border-bottom: 1px solid #dbe4f7; }
table.snd th.y.fc { background: #dbe4f7; }
table.snd th.y.first { text-align: left; }
table.snd td.fc { background: #f6f8fd; }
table.snd tr.b td { font-weight: 650; color: #0f172a; }
table.snd tr.b td.lbl { color: #0f172a; }
table.snd tr.bal td { background: #e8eefb; font-weight: 700; border-bottom: 1px solid #dbe4f7; }
table.snd tr.bal td.fc { background: #dfe8f9; }
table.snd tr.bal td.lbl { color: #0a2463; }
table.snd tr.soft td { color: #64748b; }
table.snd tr.soft td.lbl { color: #94a3b8; }
table.snd tr.sep td { border: 0; height: 6px; padding: 0; }
table.snd td.neg { color: #c0392b; }
table.snd td.ed { cursor: text; background: #fffaf5 !important; box-shadow: inset 0 0 0 1px rgba(217,130,43,.28); color: #0a2463 !important; }
table.snd td.ed:hover { box-shadow: inset 0 0 0 1px #9db3e6; background: #f3f6fd; }
table.snd td.ed:focus { outline: none; box-shadow: inset 0 0 0 2px #0a2463; background: #ffffff; }
table.snd td.chg { background: #fff4d6 !important; color: #7a4b00; font-weight: 700; }
table.snd td.mv { background: #fff1e6 !important; color: #9a3412 !important; font-weight: 600; }
table.snd td.rev { position: relative; }
.rev-dot { display: inline-block; width: 3px; height: 3px; border-radius: 50%; margin-left: 4px; vertical-align: middle; background: #94a3b8; }
.rev-dot.up { background: #1f9d6f; }
.rev-dot.down { background: #c0392b; }
.rev-pop { display: none; position: absolute; z-index: 60; top: 100%; right: 0; margin-top: 4px; background: #ffffff; color: #1d1d1f;
           border: 1px solid rgba(0,0,0,.08); border-radius: 8px; padding: 7px 10px; font-size: 10.5px; white-space: nowrap;
           box-shadow: 0 6px 20px rgba(0,0,0,.18); text-align: left; font-weight: 400; letter-spacing: 0; }
table.snd td.rev:hover .rev-pop { display: block; }
.rev-pop .row { padding: 2px 0; }
.rev-pop .row + .row { border-top: 1px solid rgba(0,0,0,.08); }
.rev-pop .dt { color: #86868b; margin-right: 6px; }
.rev-pop .rs { color: #86868b; margin-left: 6px; }
table.snd td.spark-td, table.snd th.spark-h { border-left: 1px solid rgba(0,0,0,.06); padding-left: 10px; }
table.snd th.spark-h { font-size: 9.5px; text-transform: uppercase; letter-spacing: .06em; }
.spark { display: inline-block; width: 48px; height: 13px; vertical-align: middle; }
.spark-wrap { position: relative; display: inline-block; cursor: crosshair; }
/* the table scrolls horizontally, which would clip a popover opening past its right edge — so while any sparkline in it is
   hovered, its wrap stops clipping (:has needs a Chromium-based browser, which Streamlit's always is) and the popover, anchored
   to that exact row, opens to the left of it without being cut off */
.snd-wrap:has(.spark-wrap:hover) { overflow: visible; }
.spark-pop { display: none; position: absolute; z-index: 9999; top: 50%; right: 100%; margin-right: 8px; transform: translateY(-50%);
             background: #ffffff; border: 1px solid rgba(0,0,0,.08); border-radius: 8px; padding: 4px 6px 2px; box-shadow: 0 10px 28px rgba(0,0,0,.22); }
.spark-wrap:hover .spark-pop { display: block; }
.snd-bar { background: linear-gradient(90deg, #0a1d4d 0%, #0a2463 100%); color: #ffffff; font-size: 12px; font-weight: 700;
           letter-spacing: .12em; text-transform: uppercase; padding: 7px 14px; border-radius: 8px 8px 0 0; margin-top: 6px; }
.crop { font-size: 9.5px; font-weight: 500; letter-spacing: .04em; text-transform: none; opacity: .75; margin-left: 10px; }
.snd-head { display: flex; align-items: baseline; gap: 12px; margin: 2px 0 12px; }
.snd-head .t { font-size: 20px; font-weight: 700; color: #0a2463; letter-spacing: -.01em; }
.snd-head .s { font-size: 12px; color: #94a3b8; letter-spacing: .02em; }
</style>
"""


# ── Data ──────────────────────────────────────────────────────────────────────
def ystart(label: str) -> int:
    return int(label[:4])


def next_year(label: str) -> str:
    """'2027/28' -> '2028/29'"""
    s = ystart(label) + 1
    return f"{s}/{str(s + 1)[-2:]}"


def current_crop_year(today=None) -> str:
    """The Jul-Jun crop year today falls in: Oct 2026 -> '2026/27', Mar 2027 -> '2026/27'."""
    t = today or date.today()
    y = t.year if t.month >= 7 else t.year - 1
    return f"{y}/{(y + 1) % 100:02d}"


def is_estimate(year: str) -> bool:
    """A crop year that has not finished yet (the running one and later) is an estimate: starred and shaded."""
    return ystart(year) >= ystart(current_crop_year())


COFFEE_LINE = re.compile(r"^(Arabica|Robusta) (.+) (\d{4}/\d{2}): (.*) -> (.*)$")
REASON = re.compile(r"\| reason: (.*)$")


def _rev_val(t):
    t = t.strip()
    return None if t in ("", "-") else float(t)


@st.cache_data(ttl=300)
def cell_history():
    """{(commodity, item, year): [(when, old, new, reason), ...]} newest first, parsed from the GitHub save history
    (the same commit log Revisions reads) — one entry per saved change to that cell."""
    out = {}
    if not gh.enabled():
        return out
    for ts, msg in gh.history(CSV_PATH):
        first, _, body = msg.partition("\n")
        if not first.startswith("Coffee SnD |"):
            continue
        why = REASON.search(first)
        why = why.group(1).strip() if why else ""
        for ln in body.splitlines():
            m = COFFEE_LINE.match(ln.strip())
            if not m:
                continue
            comm, item, year, old, new = m.groups()
            out.setdefault((comm, item, year), []).append((ts, _rev_val(old), _rev_val(new), why))
    return out


@st.cache_data(ttl=600)
def load():
    df = pd.read_csv(io.StringIO(gh.text_of(CSV_PATH, CSV)))
    meta = json.loads(gh.text_of(META_PATH, META))
    years = sorted(df["year"].unique(), key=ystart)
    return df, meta, cell_history(), years


def block(df, meta, comm, years) -> pd.DataFrame:
    """One commodity's SnD: rows = origins, Production, Consumption, Consumption %, Balance, End Season Stock, S/U."""
    d = df[df["commodity"] == comm]
    piv = d.pivot_table(index="item", columns="year", values="value", aggfunc="sum").reindex(columns=years)
    out = piv.reindex(ORIGINS[comm] + ["Consumption"]).copy()
    prod = out.loc[ORIGINS[comm]].sum(axis=0, min_count=1)
    cons = out.loc["Consumption"]
    bal = prod - cons
    stock, run = [], float(meta["opening_stock"][comm])
    for i, y in enumerate(years):
        run = run if i == 0 else run + (bal[y] if pd.notna(bal[y]) else 0.0)
        stock.append(run)
    out.loc["Production"] = prod
    out.loc["Consumption %"] = cons.pct_change(fill_method=None)
    out.loc["Balance"] = bal
    out.loc["End Season Stock"] = stock
    out.loc["S/U"] = out.loc["End Season Stock"] / cons
    return out


def global_block(a: pd.DataFrame, r: pd.DataFrame, years) -> pd.DataFrame:
    g = pd.DataFrame(columns=years, dtype=float)
    g.loc["Production Global"] = a.loc["Production"] + r.loc["Production"]
    g.loc["Consumption Global"] = a.loc["Consumption"] + r.loc["Consumption"]
    g.loc["Global Balance"] = g.loc["Production Global"] - g.loc["Consumption Global"]
    g.loc["Global demand chg"] = g.loc["Consumption Global"].pct_change(fill_method=None)
    g.loc["Combined End Season Stock"] = a.loc["End Season Stock"] + r.loc["End Season Stock"]
    g.loc["Combined S/U"] = g.loc["Combined End Season Stock"] / g.loc["Consumption Global"]
    g.loc["Robusta demand share"] = r.loc["Consumption"] / g.loc["Consumption Global"]
    return g


# ── Table ─────────────────────────────────────────────────────────────────────
def fnum(v, dec=1):
    if pd.isna(v):
        return ""
    r = round(float(v), dec)
    return f"({abs(r):.{dec}f})" if r < 0 else f"{r:.{dec}f}"


def fpct(v, dec=1):
    return "" if pd.isna(v) else f"{v * 100:.{dec}f}%"


SPARK_W, SPARK_H = 48, 13
DETAIL_W, DETAIL_H = 390, 200


def _spark_detail(pairs, kind, title) -> str:
    """The sparkline's full-size version, shown on hover: crop year on x, value on y, bars throughout.
    kind "growth" (origins, Production, Consumption, End season stock): bars coloured by whether that year is up or down on the year
    before, with the value and the %+/- on top. kind "plain" (S/U, Consumption %, demand-share rows): plain navy bars, value only.
    kind "bal": the Balance row's own red (deficit) / green (surplus) convention, value only."""
    pts = [(y, float(v)) for y, v in pairs if pd.notna(v)]
    if len(pts) < 2:
        return ""
    vals = [v for _, v in pts]
    pad_l, pad_r, pad_t, pad_b = 28, 8, 30, 30            # extra top for the title + value/%, extra bottom for rotated year labels
    plot_w, plot_h = DETAIL_W - pad_l - pad_r, DETAIL_H - pad_t - pad_b
    lo, hi = min(min(vals), 0), max(max(vals), 0)
    rng = (hi - lo) or 1.0
    n = len(pts)
    xs = [pad_l + (i + 0.5) * plot_w / n for i in range(n)]
    bw = plot_w / n * 0.62

    def Y(v):
        return pad_t + plot_h - (v - lo) / rng * plot_h

    zero_y = Y(0)
    svg = f"<svg width='{DETAIL_W}' height='{DETAIL_H}' viewBox='0 0 {DETAIL_W} {DETAIL_H}'>"
    svg += f"<text x='{DETAIL_W / 2:.1f}' y='12' font-size='11' font-weight='600' text-anchor='middle' fill='#0a2463'>{html.escape(title)}</text>"
    for v in (lo, (lo + hi) / 2, hi):
        yy = Y(v)
        svg += f"<line x1='{pad_l}' y1='{yy:.1f}' x2='{DETAIL_W - pad_r}' y2='{yy:.1f}' stroke='rgba(0,0,0,.08)' stroke-width='1'/>"
    for i, (y, _v) in enumerate(pts):                     # every year, small and rotated so they all fit without colliding
        svg += (f"<text x='{xs[i]:.1f}' y='{DETAIL_H - 6}' font-size='7' text-anchor='middle' fill='#64748b' "
                f"transform='rotate(-55 {xs[i]:.1f} {DETAIL_H - 6})'>{y[2:]}</text>")
    for i, (y, v) in enumerate(pts):
        top, bot = sorted([zero_y, Y(v)])
        op = 0.5 if is_estimate(y) else 1
        prev = vals[i - 1] if i > 0 else None
        if kind == "bal":
            color = GREEN if v >= 0 else RED
        elif kind == "growth":
            color = GREY if prev is None else (GREEN if v >= prev else RED)   # no prior year to compare: grey, not a colour claim
        else:
            color = NAVY
        svg += (f"<rect x='{xs[i] - bw / 2:.1f}' y='{top:.1f}' width='{bw:.1f}' height='{max(bot - top, 1):.1f}' "
                f"fill='{color}' opacity='{op}' rx='1.5'/>"
                f"<text x='{xs[i]:.1f}' y='{top - 3:.1f}' font-size='8' text-anchor='middle' fill='#1d1d1f'>{v:,.1f}</text>")
        if kind == "growth" and prev:
            pct = (v / prev - 1) * 100
            arrow, pc = ("▲", GREEN) if pct >= 0 else ("▼", RED)
            svg += f"<text x='{xs[i]:.1f}' y='{top - 11:.1f}' font-size='7.5' text-anchor='middle' fill='{pc}'>{arrow} {abs(pct):.0f}%</text>"
    svg += "</svg>"
    return f"<div class='spark-pop'>{svg}</div>"


def sparkline(pairs, title, kind="growth") -> str:
    """A tiny bar sparkline (Excel-style) over a row's own years. Hover it for the full chart (see _spark_detail)."""
    pts = [(y, float(v)) for y, v in pairs if pd.notna(v)]
    if len(pts) < 2:
        return ""
    vals = [v for _, v in pts]
    hi = max(vals) or 1.0
    pad, n = 1.0, len(pts)
    bw = (SPARK_W - 2 * pad) / n
    bars = ""
    for i, (y, v) in enumerate(pts):
        bh = max(v / hi * (SPARK_H - 2), 0.6)
        x = pad + i * bw + 0.3
        op = 0.5 if is_estimate(y) else 1
        bars += f"<rect x='{x:.1f}' y='{SPARK_H - bh:.1f}' width='{bw - 0.6:.1f}' height='{bh:.1f}' rx='0.4' fill='#5b7fc7' opacity='{op}'/>"
    svg = f"<svg class='spark' viewBox='0 0 {SPARK_W} {SPARK_H}'>{bars}</svg>"
    return f"<span class='spark-wrap'>{svg}{_spark_detail(pts, kind, title)}</span>"


def _rev_chart(revs, title="") -> str:
    """A tiny line chart of the revision history itself: one point per saved change, oldest to newest, by date."""
    chrono = list(reversed(revs))                            # revs is newest-first; the chart reads left to right
    pts = [(chrono[0][0][:10], chrono[0][1])] if chrono[0][1] is not None else []
    pts += [(ts[:10], n) for ts, _o, n, _r in chrono if n is not None]
    if len(pts) < 2:
        return ""
    vals = [v for _, v in pts]
    w, h, pad_x, pad_t, pad_b = 190, 84, 18, 30, 16
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    n = len(pts)
    xs = [pad_x + i * (w - 2 * pad_x) / (n - 1) for i in range(n)]
    ys = [h - pad_b - (v - lo) / rng * (h - pad_t - pad_b) for v in vals]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    dots = "".join(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='2' fill='#0a2463'/>" for x, y in zip(xs, ys))
    labels = "".join(f"<text x='{x:.1f}' y='{y - 5:.1f}' font-size='8' text-anchor='middle' fill='#1d1d1f'>{v:,.1f}</text>"
                     for x, y, v in zip(xs, ys, vals))
    head = f"<text x='{w / 2:.1f}' y='13' font-size='9.5' font-weight='600' text-anchor='middle' fill='#0a2463'>{html.escape(title)}</text>" if title else ""
    return (f"<svg width='{w}' height='{h}' style='display:block;margin-bottom:4px'>{head}"
            f"<polyline points='{poly}' fill='none' stroke='#5b7fc7' stroke-width='1.5'/>{dots}{labels}"
            f"<text x='{xs[0]:.1f}' y='{h - 2}' font-size='7.5' fill='#9a9a9e'>{pts[0][0]}</text>"
            f"<text x='{xs[-1]:.1f}' y='{h - 2}' font-size='7.5' fill='#9a9a9e' text-anchor='end'>{pts[-1][0]}</text></svg>")


def sparkline_balance(pairs, title) -> str:
    """A tiny zero-baseline bar sparkline for the Balance row: green bars above the line (surplus), red below it (deficit);
    forecast years are the same colours, just faded."""
    pts = [(y, float(v)) for y, v in pairs if pd.notna(v)]
    if len(pts) < 2:
        return ""
    vals = [v for _, v in pts]
    m = max(abs(v) for v in vals) or 1.0
    pad, n = 1.0, len(pts)
    bw = (SPARK_W - 2 * pad) / n
    mid = SPARK_H / 2
    bars = ""
    for i, (y, v) in enumerate(pts):
        bh = max(abs(v) / m * (mid - 1.5), 0.6)
        x = pad + i * bw + 0.3
        yy = mid - bh if v >= 0 else mid
        op = 0.5 if is_estimate(y) else 1
        bars += f"<rect x='{x:.1f}' y='{yy:.1f}' width='{bw - 0.6:.1f}' height='{bh:.1f}' rx='0.4' fill='{GREEN if v >= 0 else RED}' opacity='{op}'/>"
    svg = (f"<svg class='spark' viewBox='0 0 {SPARK_W} {SPARK_H}'><line x1='0' y1='{mid}' x2='{SPARK_W}' y2='{mid}' "
          f"stroke='rgba(0,0,0,.18)' stroke-width='0.6'/>{bars}</svg>")
    return f"<span class='spark-wrap'>{svg}{_spark_detail(pts, 'bal', title)}</span>"


def snd_table(df, meta, notes, years, shown, comm_frames, glob, combo, edit=None) -> str:
    """The sheet's layout, quietly: Brazil Combo line, then Arabica / Robusta / Global blocks."""
    ncol = len(shown) + 2                                   # + the trailing Trend sparkline column

    def shaded(comm, y):
        return bool(comm) and is_estimate(y)

    def starred(comm, y):
        return bool(comm) and is_estimate(y)

    def head(comm=None):
        cells = "".join(f"<th class='y{' fc' if shaded(comm, y) else ''}'>{y}{'*' if starred(comm, y) else ''}</th>" for y in shown)
        return f"<tr><th class='y first'></th>{cells}<th class='y spark-h'>Trend</th></tr>"

    def tr(label, vals, kind="", fmt=fnum, comm=None, item=None, neg_red=False, editable=True):
        if edit and not edit.get("all") and not (comm and item and editable):   # "Editable" view: input rows only
            return ""
        cells = ""
        for y in shown:
            v = vals[y]
            cls = []
            if shaded(comm, y):
                cls.append("fc")
            if neg_red and pd.notna(v) and v < -0.049:
                cls.append("neg")
            pop = ""
            is_input_cell = bool(edit and comm and item and editable)     # a cell the component will make contentEditable
            revs = notes.get((comm, item, y)) if comm and not is_input_cell else None   # skip: a contentEditable td's textContent
            if revs:                                                       # would otherwise include the hidden popover's own text
                cls.append("rev")
                last_old, last_new = revs[0][1], revs[0][2]
                dir_cls = "up" if last_old is not None and last_new is not None and last_new > last_old \
                    else "down" if last_old is not None and last_new is not None and last_new < last_old else ""
                rows = "".join(
                    f"<div class='row'><span class='dt'>{ts[:10]}</span>{fnum(o, 1) or '-'} &rarr; {fnum(n, 1) or '-'}"
                    + (f"<span class='rs'>{html.escape(r, quote=True)}</span>" if r else "") + "</div>"
                    for ts, o, n, r in revs[:8])
                pop = f"<span class='rev-dot {dir_cls}'></span><div class='rev-pop'>{_rev_chart(revs, label)}{rows}</div>"
            title = ""
            if edit and comm and item and editable:                      # an input cell: typed over in place
                k = f"{comm}|{item}|{y}"
                b = edit["base"].get(k)
                cls.append("ed")
                if k in edit["changed"]:
                    cls.append("chg")
                title = f" data-k='{html.escape(k, quote=True)}' data-base='{'' if b is None or pd.isna(b) else b}'"
            cells += f"<td class='{' '.join(cls)}'{title}>{fmt(v)}{pop}</td>"
        if kind == "bal":
            spark_html = sparkline_balance([(y, vals[y]) for y in shown], label)
        else:
            spark_html = sparkline([(y, vals[y]) for y in shown], label, "plain" if fmt is fpct else "growth")
        cells += f"<td class='spark-td'>{spark_html}</td>"
        return f"<tr class='{kind}'><td class='lbl'>{label}</td>{cells}</tr>"

    out = []
    for comm, fr in comm_frames.items():
        if comm != "Arabica":
            out.append(f"<tr class='gap'><td colspan='{ncol}'></td></tr>")
        out.append(f"<tr class='comm'><th colspan='{ncol}'>{comm}<span class='crop'>Jul–Jun</span></th></tr>")
        out.append(head(comm))
        for o in ORIGINS[comm]:
            out.append(tr(o, fr.loc[o], comm=comm, item=o))
        out.append(tr("Production", fr.loc["Production"], "b"))
        out.append(tr("Consumption", fr.loc["Consumption"], "b", comm=comm, item="Consumption"))
        if edit:                                                 # the stock roll's starting point, typed like any other input
            y0 = shown[0]
            k = f"{comm}|__open__|{y0}"
            b = edit["base"].get(k)
            cls = "ed" + (" chg" if k in edit["changed"] else "")
            out.append(f"<tr><td class='lbl'>First-year end stock</td><td class='{cls}' data-k='{k}' data-base='{b}'>{fnum(b)}</td>"
                       + "<td></td>" * (len(shown) - 1) + "<td class='spark-td'></td></tr>")
        out.append(tr("Consumption %", fr.loc["Consumption %"], "soft", fpct))
        out.append(tr("Balance", fr.loc["Balance"], "bal", neg_red=True))
        out.append(tr("End season stock", fr.loc["End Season Stock"], ""))
        out.append(tr("S/U", fr.loc["S/U"], "soft", (lambda v: fpct(v, 1 if comm == "Arabica" else 0))))
        if comm == "Robusta":
            out.append(tr("Robusta demand share", glob.loc["Robusta demand share"], "soft", lambda v: fpct(v, 0)))
    if edit and not edit.get("all"):                           # the Global block is all calculated: nothing to edit
        return f"<div class='snd-wrap'><table class='snd'>{''.join(out)}</table></div>"
    out.append(f"<tr class='gap'><td colspan='{ncol}'></td></tr>")
    out.append(f"<tr class='comm'><th colspan='{ncol}'>Global<span class='crop'>Jul–Jun</span></th></tr>")
    out.append(head(None))
    shared = set(ORIGINS["Arabica"]) & set(ORIGINS["Robusta"])             # "Brazil", "Others": in both lists, label which is which
    for comm, fr in comm_frames.items():
        for o in ORIGINS[comm]:
            out.append(tr(f"{o} ({comm[0]})" if o in shared else o, fr.loc[o], comm=comm, item=o, editable=False))
    out.append(tr("Production", glob.loc["Production Global"], "b"))
    out.append(tr("Consumption", glob.loc["Consumption Global"], "b"))
    out.append(tr("Balance", glob.loc["Global Balance"], "bal", neg_red=True))
    out.append(tr("Demand change", glob.loc["Global demand chg"], "soft", fpct))
    out.append(tr("Combined end season stock", glob.loc["Combined End Season Stock"], ""))
    out.append(tr("Combined S/U", glob.loc["Combined S/U"], "soft", fpct))
    out.append(f"<tr class='meta'><td class='lbl'>Brazil combo (Arabica + Robusta)</td>{''.join(f'<td>{combo[y]:.1f}</td>' for y in shown)}"
               f"<td class='spark-td'>{sparkline([(y, combo[y]) for y in shown], 'Brazil combo (Arabica + Robusta)')}</td></tr>")
    return f"<div class='snd-wrap'><table class='snd'>{''.join(out)}</table></div>"


# ── Charts ────────────────────────────────────────────────────────────────────
def _style(fig, height=230, fmt=",.1f", legend=True):
    fig.update_layout(template="plotly_white", height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#1d1d1f", size=11, family="-apple-system, BlinkMacSystemFont, Inter, Segoe UI, sans-serif"), margin=dict(t=4, b=24, l=8, r=8), hovermode="x unified",
                      legend=dict(orientation="h", x=0, y=1.14, bgcolor="rgba(0,0,0,0)", font=dict(size=10.5)) if legend else None,
                      showlegend=legend, bargap=0.35,
                      xaxis=dict(color=AXIS, showgrid=False, type="category", tickfont=dict(size=10),
                                 tickangle=0, tickvals=None),
                      yaxis=dict(gridcolor=GRID, color=AXIS, hoverformat=fmt, zeroline=True, zerolinecolor="rgba(15,23,42,0.18)",
                                 tickfont=dict(size=10)))
    return fig


def _bars(fig, x, y, name, color, est, **kw):
    fig.add_trace(go.Bar(x=x, y=y, name=name, marker=dict(color=color, opacity=[0.55 if e else 1 for e in est], line_width=0),
                         hovertemplate=name + ": %{y:.1f}<extra></extra>", **kw))


def _line(fig, x, y, name, color, right=False, pct=False, dash=None):
    fig.add_trace(go.Scatter(x=x, y=y, name=name, mode="lines+markers", yaxis="y2" if right else "y", line=dict(color=color, width=2.2, dash=dash),
                             marker=dict(size=5), hovertemplate=name + (": %{y:.1f}%" if pct else ": %{y:.1f}") + "<extra></extra>"))


def _y2(fig, suffix="%"):
    return fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, color=AXIS, ticksuffix=suffix, tickfont=dict(size=10)))


def charts(a, r, glob, shown):
    """Global SnD visuals: supply mix, stocks, balance, demand, origins and stocks to use. Estimates are faded."""
    x = [y[2:] for y in shown]                                        # 2024/25 -> 24/25 on the axes
    est = [is_estimate(y) for y in shown]
    rows = [st.columns(2, gap="small") for _ in range(3)]

    with rows[0][0], st.container(border=True):
        st.markdown("<div class='chart-head'>Production: Arabica and Robusta</div>", unsafe_allow_html=True)
        fig = go.Figure()
        _bars(fig, x, a.loc["Production", shown], "Arabica", NAVY, est)
        _bars(fig, x, r.loc["Production", shown], "Robusta", AMBER, est)
        _line(fig, x, r.loc["Production", shown] / glob.loc["Production Global", shown] * 100, "Robusta share (right)", RED, right=True, pct=True)
        st.plotly_chart(_y2(_style(fig, 280).update_layout(barmode="stack")), width="stretch", key="c_prod")
    with rows[0][1], st.container(border=True):
        st.markdown("<div class='chart-head'>End season stocks</div>", unsafe_allow_html=True)
        fig = go.Figure()
        _bars(fig, x, a.loc["End Season Stock", shown], "Arabica", NAVY, est)
        _bars(fig, x, r.loc["End Season Stock", shown], "Robusta", AMBER, est)
        _line(fig, x, glob.loc["Combined S/U", shown] * 100, "Global S/U (right)", RED, right=True, pct=True)
        st.plotly_chart(_y2(_style(fig, 280).update_layout(barmode="stack")), width="stretch", key="c_stock")

    with rows[1][0], st.container(border=True):
        st.markdown("<div class='chart-head'>Balance</div>", unsafe_allow_html=True)
        fig = go.Figure()
        _bars(fig, x, a.loc["Balance", shown], "Arabica", NAVY, est)
        _bars(fig, x, r.loc["Balance", shown], "Robusta", AMBER, est)
        _line(fig, x, glob.loc["Global Balance", shown], "Global", RED)
        st.plotly_chart(_style(fig, 280).update_layout(barmode="group"), width="stretch", key="c_bal")
    with rows[1][1], st.container(border=True):
        st.markdown("<div class='chart-head'>Consumption</div>", unsafe_allow_html=True)
        fig = go.Figure()
        _bars(fig, x, a.loc["Consumption", shown], "Arabica", NAVY, est)
        _bars(fig, x, r.loc["Consumption", shown], "Robusta", AMBER, est)
        _line(fig, x, glob.loc["Global demand chg", shown] * 100, "Growth (right)", RED, right=True, pct=True)
        st.plotly_chart(_y2(_style(fig, 280).update_layout(barmode="stack")), width="stretch", key="c_cons")

    with rows[2][0], st.container(border=True):
        st.markdown("<div class='chart-head'>Production by origin</div>", unsafe_allow_html=True)
        orig = {}
        for comm, fr in (("Arabica", a), ("Robusta", r)):
            for o in ORIGINS[comm]:
                nm = o if o != "Others" else "Others"
                orig[nm] = orig.get(nm, 0) + fr.loc[o, shown].fillna(0)
        order = sorted([o for o in orig if o != "Others"], key=lambda o: -float(orig[o].sum())) + ["Others"]
        pal = [NAVY, AMBER, TEAL, "#3e5c9a", "#d9a441", "#6fb7c4", "#8796c2", "#c9b38a", "#a8b3c7", "#cfd6e4", "#e3e7ef"]
        fig = go.Figure()
        for o, col in zip(order, pal + [GREY] * len(order)):
            _bars(fig, x, orig[o], o, col, est)
        st.plotly_chart(_style(fig, 300).update_layout(barmode="stack", legend=dict(font=dict(size=9.5), y=1.2)), width="stretch", key="c_orig")
    with rows[2][1], st.container(border=True):
        st.markdown("<div class='chart-head'>Stocks to use</div>", unsafe_allow_html=True)
        fig = go.Figure()
        _line(fig, x, a.loc["S/U", shown] * 100, "Arabica", NAVY, pct=True)
        _line(fig, x, r.loc["S/U", shown] * 100, "Robusta", AMBER, pct=True)
        _line(fig, x, glob.loc["Combined S/U", shown] * 100, "Global", RED, pct=True)
        st.plotly_chart(_style(fig, 300).update_layout(yaxis_ticksuffix="%"), width="stretch", key="c_su")


# ── Edit view: the styled table itself, typed over in place ────────────────────────────────────────────────
def _undo():
    st.session_state.pop("snd_new_year", None)
    st.session_state["snd_epoch"] = st.session_state.get("snd_epoch", 0) + 1
    st.session_state["_snd_edits"] = {}
    try:
        st.session_state["snd_tbl"] = {}
    except Exception:
        pass


def render_edit(df, meta, notes, years, shown, editable):
    """Edit mode: the same table, with the input cells (origins, consumption) editable in place. The calculated rows are rebuilt from the
    edits and sent back to the table, so they move as you type. One Save for everything."""
    import tableedit
    epoch = st.session_state.setdefault("snd_epoch", 0)
    edits = st.session_state.get("snd_tbl")                      # the table's own state is dropped when Edit mode is left:
    if edits is None:                                            # fall back to the copy kept below, so pending edits survive a View / Edit switch
        edits = st.session_state.get("_snd_edits", {})
    base = {f"{c}|{it}|{y}": float(v) for c, it, y, v in zip(df["commodity"], df["item"], df["year"], df["value"])}
    nxt = next_year(years[-1])
    extra = st.session_state.get("snd_new_year")               # "+ Crop year": a blank column to the right, saved once filled
    if extra:
        years, shown = years + [extra], shown + [extra]
    base.update({f"{c}|__open__|{shown[0]}": float(meta["opening_stock"][c]) for c in ("Arabica", "Robusta")})
    changes = [(k.split("|")[0], k.split("|")[1], k.split("|")[2], base.get(k), (None if v is None else float(v))) for k, v in edits.items()]
    opens = [c for c in changes if c[1] == "__open__"]           # first-year end stock lives in the meta file, not the CSV
    changes = [c for c in changes if c[1] != "__open__"]
    live_meta = {**meta, "opening_stock": {**meta["opening_stock"], **{c[0]: c[4] for c in opens if c[4] is not None}}}
    live = _apply_changes(df, changes)
    a, r = block(live, live_meta, "Arabica", years), block(live, live_meta, "Robusta", years)
    glob = global_block(a, r, years)
    table = snd_table(live, meta, notes, years, shown, {"Arabica": a, "Robusta": r}, glob, a.loc["Brazil"] + r.loc["Brazil"],
                      edit=dict(base=base, changed=set(edits), all=st.session_state.get("edit_rows") != "Show only editable"))
    if changes or opens:                                         # tint every calculated cell the unsaved edits move
        a0, r0 = block(df, meta, "Arabica", years), block(df, meta, "Robusta", years)
        ref = snd_table(df, meta, notes, years, shown, {"Arabica": a0, "Robusta": r0}, global_block(a0, r0, years),
                        a0.loc["Brazil"] + r0.loc["Brazil"],
                        edit=dict(base=base, changed=set(edits), all=st.session_state.get("edit_rows") != "Show only editable"))
        table = tableedit.mark_moved(table, ref)
    ctrl = st.container()                                        # Save / Undo / Reason sit above the table
    bar = ctrl.container(horizontal=True, vertical_alignment="center", gap="small")   # one compact row, left-aligned
    bar.radio("Rows", ["Show all rows", "Show only editable"], horizontal=True, key="edit_rows", label_visibility="collapsed")
    tableedit.editable_table(table, tableedit.css_of(CSS), "snd_tbl", epoch, editable, edits)
    st.session_state["_snd_edits"] = dict(edits)
    if not editable:
        ctrl.markdown("<div class='card-desc'>Read-only: add github_token in Secrets to edit.</div>", unsafe_allow_html=True)
        return
    n_all = len(changes) + len(opens)
    bad = any(c[4] is not None and c[4] < 0 for c in changes + opens)
    if bad:
        ctrl.error("Values cannot be negative.")


    reason = bar.text_input("Reason", key=f"snd_reason_{epoch}", placeholder="Reason for Change...", width=320,
                              label_visibility="collapsed", max_chars=140, disabled=not n_all)
    bar.button("Undo", disabled=not n_all, width="content", key="snd_undo", on_click=_undo)
    save = bar.button("Save" + (f" · {n_all}" if n_all else ""), type="primary", disabled=(not n_all) or bad,
                      width="content", key="snd_save")
    bar.button("+ Crop year", key="snd_addyr", disabled=bool(extra), width="content",
               on_click=lambda: st.session_state.__setitem__("snd_new_year", nxt))
    if save:
        try:
            with st.spinner("Saving..."):
                if changes:
                    _save_inputs(changes, reason)
                if opens:
                    old = {k: float(v) for k, v in meta["opening_stock"].items()}
                    new = {**old, **{c[0]: float(c[4]) for c in opens if c[4] is not None}}

                    def mut(m):
                        for k, v in new.items():
                            m["opening_stock"][k] = round(float(v), 4)
                    _save_meta("opening stock", old, new, mut)
        except (gh.GitHubError, Exception) as ex:
            ctrl.error(f"GitHub save failed: {ex}")
        else:
            _undo()
            st.session_state["en_flash"] = f"Saved {n_all} change(s)."
            st.rerun()


# ── Page ──────────────────────────────────────────────────────────────────────
def render():
    st.markdown(CSS, unsafe_allow_html=True)
    df, meta, notes, years = load()
    with (MODE_SLOT or st.sidebar), st.container(key="mode_nav"):
        mode = st.radio("Mode", ["View", "Edit"], horizontal=True, key="snd_mode", label_visibility="collapsed")
    shown = years[-7:] if st.session_state.get("yrs_span", "Last 7") == "Last 7" else years
    if st.session_state.get("en_flash"):
        st.toast(st.session_state.pop("en_flash"))
    a, r = block(df, meta, "Arabica", years), block(df, meta, "Robusta", years)
    glob = global_block(a, r, years)
    combo = a.loc["Brazil"] + r.loc["Brazil"]
    head = "<span class='t edit'>Edit Global SnD</span>" if mode == "Edit" else "<span class='t'>Global SnD</span>"
    st.markdown(f"<div class='snd-head'>{head}</div>", unsafe_allow_html=True)
    if mode == "Edit":
        render_edit(df, meta, notes, years, shown, gh.enabled())
        return
    st.markdown(snd_table(df, meta, notes, years, shown, {"Arabica": a, "Robusta": r}, glob, combo), unsafe_allow_html=True)
    charts(a, r, glob, shown)


# ── Saving ────────────────────────────────────────────────────────────────────
def _num(txt):
    if txt is None or (isinstance(txt, float) and pd.isna(txt)):
        return None
    if isinstance(txt, (int, float)):
        return float(txt)
    txt = str(txt).replace(",", "").strip()
    return float(txt) if txt else None


def _fmt(v):
    return "" if v is None or pd.isna(v) else f"{v:g}"


def _apply_changes(d: pd.DataFrame, changes) -> pd.DataFrame:
    """The inputs frame with (commodity, item, year, old, new) changes applied; new = None removes the value."""
    d = d.copy()
    for c, it, y, _o, n in changes:
        d = d[~((d["commodity"] == c) & (d["item"] == it) & (d["year"] == y))]
        if n is not None:
            d = pd.concat([d, pd.DataFrame([{"commodity": c, "item": it, "year": y, "value": n}])], ignore_index=True)
    return d


def clean_reason(txt) -> str:
    """The reason typed with a save, as one short line that the revision log can read back (no ' | ' inside)."""
    return " ".join(str(txt or "").split()).replace(" | ", " / ")[:140]


def _save_inputs(changes, reason=""):
    lines = [f"{c} {it} {y}: {_fmt(o) or '-'} -> {_fmt(n) or '-'}" for c, it, y, o, n in changes]
    reason = clean_reason(reason)
    msg = f"Coffee SnD | {len(changes)} change(s)" + (f" | reason: {reason}" if reason else "") + "\n\n" + "\n".join(lines)

    def apply(text):
        d = _apply_changes(pd.read_csv(io.StringIO(text)), changes)
        order = {(c, it): i for c, its in ORIGINS.items() for i, it in enumerate(its + ["Consumption"])}
        d["_o"] = [order.get((c, it), 99) for c, it in zip(d["commodity"], d["item"])]
        d["_c"] = d["commodity"].map({"Arabica": 0, "Robusta": 1})
        d["_y"] = d["year"].map(ystart)
        d = d.sort_values(["_c", "_o", "_y"]).drop(columns=["_o", "_c", "_y"])
        return d.to_csv(index=False, lineterminator="\n"), None
    new_text, _ = gh.commit(CSV_PATH, apply, msg)
    with open(CSV, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)
    load.clear()
    cell_history.clear()


def _save_meta(label, old, new, mutate):
    msg = f"Setting | {label}: {old} -> {new}"

    def apply(text):
        d = json.loads(text)
        mutate(d)
        return json.dumps(d, indent=2) + "\n", None
    text, _ = gh.commit(META_PATH, apply, msg)
    with open(META, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    load.clear()
