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
table.snd td, table.snd th { padding: 2px 9px; text-align: right; white-space: nowrap; line-height: 1.3; }
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
table.snd td.ed { cursor: text; }
table.snd td.ed:hover { box-shadow: inset 0 0 0 1px #9db3e6; background: #f3f6fd; }
table.snd td.ed:focus { outline: none; box-shadow: inset 0 0 0 2px #0a2463; background: #ffffff; }
table.snd td.chg { background: #fff4d6 !important; color: #7a4b00; font-weight: 700; }
table.snd td.rev { position: relative; }
.rev-dot { display: inline-block; width: 5px; height: 5px; border-radius: 50%; margin-left: 5px; vertical-align: middle; }
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
/* fixed (not absolute) so it escapes the table's horizontal-scroll clipping and always lands fully on screen, on the right */
.spark-pop { display: none; position: fixed; z-index: 9999; top: 50%; right: 24px; transform: translateY(-50%);
             background: #ffffff; border: 1px solid rgba(0,0,0,.08); border-radius: 8px; padding: 4px 6px 2px; box-shadow: 0 10px 28px rgba(0,0,0,.22); }
.spark-wrap:hover .spark-pop { display: block; }
.snd-bar { background: linear-gradient(90deg, #0a1d4d 0%, #0a2463 100%); color: #ffffff; font-size: 12px; font-weight: 700;
           letter-spacing: .12em; text-transform: uppercase; padding: 7px 14px; border-radius: 8px 8px 0 0; margin-top: 6px; }
.snd-head { display: flex; align-items: baseline; gap: 12px; margin: 2px 0 12px; }
.snd-head .t { font-size: 20px; font-weight: 700; color: #0a2463; letter-spacing: -.01em; }
.snd-head .s { font-size: 12px; color: #94a3b8; letter-spacing: .02em; }
</style>
"""


# ── Data ──────────────────────────────────────────────────────────────────────
def ystart(label: str) -> int:
    return int(label[:4])


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
    df = pd.read_csv(CSV)
    meta = json.loads(META.read_text(encoding="utf-8"))
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
DETAIL_W, DETAIL_H = 270, 140


def _spark_detail(pairs, kind="line") -> str:
    """The sparkline's full-size version, shown on hover: crop year on x, value on y, with gridlines and labels."""
    pts = [(y, float(v)) for y, v in pairs if pd.notna(v)]
    if len(pts) < 2:
        return ""
    vals = [v for _, v in pts]
    pad_l, pad_r, pad_t, pad_b = 28, 8, 16, 28           # extra top for value labels, extra bottom for rotated year labels
    plot_w, plot_h = DETAIL_W - pad_l - pad_r, DETAIL_H - pad_t - pad_b
    lo, hi = (min(min(vals), 0), max(max(vals), 0)) if kind == "bar" else (min(vals), max(vals))
    rng = (hi - lo) or 1.0
    n = len(pts)
    xs = [pad_l + i * plot_w / (n - 1) for i in range(n)]

    def Y(v):
        return pad_t + plot_h - (v - lo) / rng * plot_h

    svg = f"<svg width='{DETAIL_W}' height='{DETAIL_H}' viewBox='0 0 {DETAIL_W} {DETAIL_H}'>"
    for v in (lo, (lo + hi) / 2, hi):
        yy = Y(v)
        svg += (f"<line x1='{pad_l}' y1='{yy:.1f}' x2='{DETAIL_W - pad_r}' y2='{yy:.1f}' stroke='rgba(0,0,0,.08)' stroke-width='1'/>"
                f"<text x='{pad_l - 4}' y='{yy + 3:.1f}' font-size='8' text-anchor='end' fill='#64748b'>{v:.1f}</text>")
    step = max(round(n / 7), 1)                          # thin out the year labels so "16/17" etc. don't collide
    for i, (y, _v) in enumerate(pts):
        if i % step == 0 or i == n - 1:
            svg += (f"<text x='{xs[i]:.1f}' y='{DETAIL_H - 6}' font-size='7.5' text-anchor='middle' fill='#64748b' "
                    f"transform='rotate(-40 {xs[i]:.1f} {DETAIL_H - 6})'>{y[2:]}</text>")
    if kind == "bar":
        zero_y, bw = Y(0), plot_w / n * 0.6
        for i, (y, v) in enumerate(pts):
            top, bot = sorted([zero_y, Y(v)])
            op = 0.5 if is_estimate(y) else 1
            lbl_y = top - 3 if v >= 0 else bot + 8
            svg += (f"<rect x='{xs[i] - bw / 2:.1f}' y='{top:.1f}' width='{bw:.1f}' height='{max(bot - top, 1):.1f}' "
                    f"fill='{GREEN if v >= 0 else RED}' opacity='{op}' rx='1.5'/>"
                    f"<text x='{xs[i]:.1f}' y='{lbl_y:.1f}' font-size='7' text-anchor='middle' fill='#1d1d1f'>{v:+.1f}</text>")
    else:
        ys = [Y(v) for v in vals]
        split = next((i for i, (y, _) in enumerate(pts) if is_estimate(y)), n)
        solid_end = max(split, 1)
        solid = " ".join(f"{xs[i]:.1f},{ys[i]:.1f}" for i in range(solid_end))
        dotted = " ".join(f"{xs[i]:.1f},{ys[i]:.1f}" for i in range(solid_end - 1, n)) if solid_end < n else ""
        svg += f"<polyline points='{solid}' fill='none' stroke='#2a4a9e' stroke-width='2' stroke-linejoin='round' stroke-linecap='round'/>"
        if dotted:
            svg += (f"<polyline points='{dotted}' fill='none' stroke='#2a4a9e' stroke-width='2' stroke-dasharray='3,2.5' "
                    f"stroke-linejoin='round' stroke-linecap='round'/>")
        for i in range(n):
            svg += (f"<circle cx='{xs[i]:.1f}' cy='{ys[i]:.1f}' r='2.2' fill='#0a2463'/>"
                    f"<text x='{xs[i]:.1f}' y='{ys[i] - 5:.1f}' font-size='7' text-anchor='middle' fill='#1d1d1f'>{vals[i]:.1f}</text>")
    svg += "</svg>"
    return f"<div class='spark-pop'>{svg}</div>"


def sparkline(pairs) -> str:
    """A tiny line sparkline (Excel-style) over a row's own years: reads better at this size than thin bars do. The forecast years
    (is_estimate) draw as a dotted continuation of the same line, same as the dotted estimate convention on the full charts."""
    pts = [(y, float(v)) for y, v in pairs if pd.notna(v)]
    if len(pts) < 2:
        return ""
    vals = [v for _, v in pts]
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    pad, n = 1.5, len(pts)
    xs = [pad + i * (SPARK_W - 2 * pad) / (n - 1) for i in range(n)]
    ys = [SPARK_H - pad - (v - lo) / rng * (SPARK_H - 2 * pad) for v in vals]
    split = next((i for i, (y, _) in enumerate(pts) if is_estimate(y)), n)   # first forecast point, if any
    solid_end = max(split, 1)
    solid = " ".join(f"{xs[i]:.1f},{ys[i]:.1f}" for i in range(solid_end))
    dotted = " ".join(f"{xs[i]:.1f},{ys[i]:.1f}" for i in range(solid_end - 1, n)) if solid_end < n else ""
    svg = f"<svg class='spark' viewBox='0 0 {SPARK_W} {SPARK_H}'>"
    svg += f"<polyline points='{solid}' fill='none' stroke='#5b7fc7' stroke-width='1.3' stroke-linejoin='round' stroke-linecap='round'/>"
    if dotted:
        svg += (f"<polyline points='{dotted}' fill='none' stroke='#5b7fc7' stroke-width='1.3' stroke-dasharray='1.8,1.6' "
                f"stroke-linejoin='round' stroke-linecap='round'/>")
    svg += f"<circle cx='{xs[-1]:.1f}' cy='{ys[-1]:.1f}' r='1.6' fill='#0a2463'/></svg>"
    return f"<span class='spark-wrap'>{svg}{_spark_detail(pts, 'line')}</span>"


def sparkline_balance(pairs) -> str:
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
    return f"<span class='spark-wrap'>{svg}{_spark_detail(pts, 'bar')}</span>"


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
        cells = ""
        for y in shown:
            v = vals[y]
            cls = []
            if shaded(comm, y):
                cls.append("fc")
            if neg_red and pd.notna(v) and v < -0.049:
                cls.append("neg")
            pop = ""
            revs = notes.get((comm, item, y)) if comm else None
            if revs:
                cls.append("rev")
                last_old, last_new = revs[0][1], revs[0][2]
                dir_cls = "up" if last_old is not None and last_new is not None and last_new > last_old \
                    else "down" if last_old is not None and last_new is not None and last_new < last_old else ""
                rows = "".join(
                    f"<div class='row'><span class='dt'>{ts[:10]}</span>{fnum(o, 1) or '-'} &rarr; {fnum(n, 1) or '-'}"
                    + (f"<span class='rs'>{html.escape(r, quote=True)}</span>" if r else "") + "</div>"
                    for ts, o, n, r in revs[:8])
                pop = f"<span class='rev-dot {dir_cls}'></span><div class='rev-pop'>{rows}</div>"
            title = ""
            if edit and comm and item and editable:                      # an input cell: typed over in place
                k = f"{comm}|{item}|{y}"
                b = edit["base"].get(k)
                cls.append("ed")
                if k in edit["changed"]:
                    cls.append("chg")
                title = f" data-k='{html.escape(k, quote=True)}' data-base='{'' if b is None or pd.isna(b) else b}'"
            cells += f"<td class='{' '.join(cls)}'{title}>{fmt(v)}{pop}</td>"
        spark = sparkline_balance if kind == "bal" else sparkline
        cells += f"<td class='spark-td'>{spark([(y, vals[y]) for y in shown])}</td>"
        return f"<tr class='{kind}'><td class='lbl'>{label}</td>{cells}</tr>"

    out = []
    for comm, fr in comm_frames.items():
        if comm != "Arabica":
            out.append(f"<tr class='gap'><td colspan='{ncol}'></td></tr>")
        out.append(f"<tr class='comm'><th colspan='{ncol}'>{comm}</th></tr>")
        out.append(head(comm))
        for o in ORIGINS[comm]:
            out.append(tr(o, fr.loc[o], comm=comm, item=o))
        out.append(tr("Production", fr.loc["Production"], "b"))
        out.append(tr("Consumption", fr.loc["Consumption"], "b", comm=comm, item="Consumption"))
        out.append(tr("Consumption %", fr.loc["Consumption %"], "soft", fpct))
        out.append(tr("Balance", fr.loc["Balance"], "bal", neg_red=True))
        out.append(tr("End season stock", fr.loc["End Season Stock"], ""))
        out.append(tr("S/U", fr.loc["S/U"], "soft", (lambda v: fpct(v, 1 if comm == "Arabica" else 0))))
        if comm == "Robusta":
            out.append(tr("Robusta demand share", glob.loc["Robusta demand share"], "soft", lambda v: fpct(v, 0)))
    out.append(f"<tr class='gap'><td colspan='{ncol}'></td></tr>")
    out.append(f"<tr class='comm'><th colspan='{ncol}'>Global</th></tr>")
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
               f"<td class='spark-td'>{sparkline([(y, combo[y]) for y in shown])}</td></tr>")
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
def _opening_controls(meta, years, editable):
    """The first year's end stock (where the stock roll starts), per commodity."""
    with st.expander("First-year end stock", expanded=False):
        c = st.columns([1.2, 1.2, 1, 4], vertical_alignment="bottom")
        old = {k: float(v) for k, v in meta["opening_stock"].items()}
        new = {k: c[i].number_input(f"{k} {years[0]} (m bags)", min_value=0.0, value=old[k], step=0.1, format="%.1f",
                                    key=f"os_{k}", disabled=not editable) for i, k in enumerate(["Arabica", "Robusta"])}
        if c[2].button("Save", disabled=(not editable) or all(abs(new[k] - old[k]) < 1e-9 for k in new), width="stretch", key="os_save"):
            try:
                with st.spinner("Saving..."):
                    def mut(m):
                        for k, v in new.items():
                            m["opening_stock"][k] = round(float(v), 4)
                    _save_meta("opening stock", old, new, mut)
            except (gh.GitHubError, Exception) as ex:
                st.error(f"GitHub save failed: {ex}")
            else:
                st.session_state["en_flash"] = "Opening stock saved."
                st.rerun()


def _undo():
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
    changes = [(k.split("|")[0], k.split("|")[1], k.split("|")[2], base.get(k), (None if v is None else float(v))) for k, v in edits.items()]
    live = _apply_changes(df, changes)
    a, r = block(live, meta, "Arabica", years), block(live, meta, "Robusta", years)
    glob = global_block(a, r, years)
    table = snd_table(live, meta, notes, years, shown, {"Arabica": a, "Robusta": r}, glob, a.loc["Brazil"] + r.loc["Brazil"],
                      edit=dict(base=base, changed=set(edits)))
    tableedit.editable_table(table, tableedit.css_of(CSS), "snd_tbl", epoch, editable, edits)
    st.session_state["_snd_edits"] = dict(edits)
    if not editable:
        st.markdown("<div class='card-desc'>Read-only: add github_token in Secrets to edit.</div>", unsafe_allow_html=True)
        return
    bad = any(c[4] is not None and c[4] < 0 for c in changes)
    if bad:
        st.error("Values cannot be negative.")
    bc = st.columns([1, 1, 5, 3], vertical_alignment="center")
    save = bc[0].button("Save", type="primary", disabled=(not changes) or bad, width="stretch", key="snd_save")
    bc[1].button("Undo", disabled=not changes, width="stretch", key="snd_undo", on_click=_undo)
    reason = bc[2].text_input("Reason", key=f"snd_reason_{epoch}", placeholder="Reason for the change, shown in Revisions (e.g. CCS adjustment, weather shock)",
                              label_visibility="collapsed", max_chars=140, disabled=not changes)
    if changes:
        bc[3].markdown(f"<div class='card-desc' style='margin:0'>{len(changes)} unsaved change(s)</div>", unsafe_allow_html=True)
    if save:
        try:
            with st.spinner("Saving..."):
                _save_inputs(changes, reason)
        except (gh.GitHubError, Exception) as ex:
            st.error(f"GitHub save failed: {ex}")
        else:
            _undo()
            st.session_state["en_flash"] = f"Saved {len(changes)} change(s)."
            st.rerun()
    _opening_controls(meta, years, True)


# ── Page ──────────────────────────────────────────────────────────────────────
def render():
    st.markdown(CSS, unsafe_allow_html=True)
    df, meta, notes, years = load()
    with st.sidebar:
        st.markdown("<div class='sb-sep'></div>", unsafe_allow_html=True)
        with st.container(key="mode_nav"):
            mode = st.radio("Mode", ["View", "Edit"], horizontal=True, key="snd_mode")
    shown = years
    if st.session_state.get("en_flash"):
        st.toast(st.session_state.pop("en_flash"))
    a, r = block(df, meta, "Arabica", years), block(df, meta, "Robusta", years)
    glob = global_block(a, r, years)
    combo = a.loc["Brazil"] + r.loc["Brazil"]
    st.markdown("<div class='snd-head'><span class='t'>Global SnD</span><span class='s'>Jul–Jun · m bags · * estimate</span></div>", unsafe_allow_html=True)
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
