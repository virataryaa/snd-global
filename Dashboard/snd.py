"""Coffee SnD: the 'SnD ETG' table (Arabica, Robusta, Global) from the inputs in Database/coffee_snd.csv.

Inputs are each origin's production and the consumption, per crop year (Jul-Jun), in million 60 kg bags. Everything else is
worked out here the way the Excel sheet does: production = sum of the origins, balance = production - consumption,
end stock = last year's end stock + balance (the first year's end stock is an input), S/U = end stock / consumption.
"""
import html
import io
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ghstore as gh

ROOT = Path(__file__).resolve().parent.parent
CSV, META, NOTES = ROOT / "Database" / "coffee_snd.csv", ROOT / "Database" / "coffee_snd_meta.json", ROOT / "Database" / "coffee_snd_notes.csv"
CSV_PATH, META_PATH = "Database/coffee_snd.csv", "Database/coffee_snd_meta.json"            # paths in the repo
ORIGINS = {
    "Arabica": ["Brazil", "Colombia", "Honduras", "Super 5", "Ethiopia", "Peru", "Others"],
    "Robusta": ["Vietnam", "Brazil", "Indonesia", "India", "Uganda", "Cote d'Ivoire", "Others"],
}
TZ = "Europe/Amsterdam"
NAVY, TEAL, GREEN, RED, AMBER, GREY = "#0a2463", "#1f8a9c", "#1f9d6f", "#c0392b", "#b7791f", "#94a3b8"
INK, AXIS, GRID = "#0f172a", "#64748b", "rgba(15,23,42,0.06)"

CSS = """
<style>
.snd-wrap { background: #ffffff; border: 1px solid #e6e9f0; border-radius: 12px; padding: 4px 6px 8px; margin-bottom: 14px;
            box-shadow: 0 1px 2px rgba(15,23,42,.04); overflow-x: auto; }
table.snd { border-collapse: separate; border-spacing: 0; width: 100%; font-size: 12.5px; color: #0f172a;
            font-variant-numeric: tabular-nums; letter-spacing: .005em; }
table.snd td, table.snd th { padding: 3px 12px; text-align: right; white-space: nowrap; line-height: 1.35; }
table.snd td.lbl { text-align: left; color: #475569; padding-left: 14px; min-width: 190px; }
table.snd td { border: 0; border-bottom: 1px solid #f1f3f7; }
table.snd th { border: 0; }
/* title strip + context line */
table.snd tr.meta td { color: #64748b; font-size: 11.5px; border-bottom: 0; padding: 6px 12px 10px; }
table.snd tr.meta td.lbl { color: #94a3b8; }
/* commodity header: label left, a thin accent rule under it */
table.snd tr.comm th { text-align: left; font-size: 12px; font-weight: 700; color: #ffffff; letter-spacing: .12em; text-transform: uppercase;
                       padding: 7px 14px; background: linear-gradient(90deg, #0a1d4d 0%, #0a2463 100%); }
table.snd tr.gap td { border: 0; height: 12px; padding: 0; }
/* year header */
table.snd th.y { font-size: 11.5px; font-weight: 600; color: #0a2463; padding: 6px 12px; background: #eef2fb; border-bottom: 1px solid #dbe4f7; }
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
table.snd td.note { position: relative; cursor: help; }
table.snd td.note::after { content: ""; position: absolute; top: 0; right: 0; border-style: solid; border-width: 0 6px 6px 0;
                           border-color: transparent #a855f7 transparent transparent; }
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


@st.cache_data(ttl=600)
def load():
    df = pd.read_csv(CSV)
    meta = json.loads(META.read_text(encoding="utf-8"))
    notes = pd.read_csv(NOTES) if NOTES.exists() else pd.DataFrame(columns=["commodity", "item", "year", "note"])
    years = sorted(df["year"].unique(), key=ystart)
    return df, meta, {(r.commodity, r.item, r.year): r.note for r in notes.itertuples()}, years


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


def snd_table(df, meta, notes, years, shown, comm_frames, glob, combo) -> str:
    """The sheet's layout, quietly: Brazil Combo line, then Arabica / Robusta / Global blocks."""
    ncol = len(shown) + 1

    def shaded(comm, y):
        return bool(comm) and is_estimate(y)

    def starred(comm, y):
        return bool(comm) and is_estimate(y)

    def head(comm=None):
        cells = "".join(f"<th class='y{' fc' if shaded(comm, y) else ''}'>{y}{'*' if starred(comm, y) else ''}</th>" for y in shown)
        return f"<tr><th class='y first'></th>{cells}</tr>"

    def tr(label, vals, kind="", fmt=fnum, comm=None, item=None, neg_red=False):
        cells = ""
        for y in shown:
            v = vals[y]
            cls = []
            if shaded(comm, y):
                cls.append("fc")
            if neg_red and pd.notna(v) and v < -0.049:
                cls.append("neg")
            title = ""
            nt = notes.get((comm, item, y)) if comm else None
            if nt:
                cls.append("note")
                title = f" title='{html.escape(nt, quote=True)}'"
            cells += f"<td class='{' '.join(cls)}'{title}>{fmt(v)}</td>"
        return f"<tr class='{kind}'><td class='lbl'>{label}</td>{cells}</tr>"

    out = [f"<tr class='meta'><td class='lbl'>Brazil combo</td>{''.join(f'<td>{combo[y]:.1f}</td>' for y in shown)}</tr>"]
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
    out.append(tr("Production", glob.loc["Production Global"], "b"))
    out.append(tr("Consumption", glob.loc["Consumption Global"], "b"))
    out.append(tr("Balance", glob.loc["Global Balance"], "bal", neg_red=True))
    start = years.index(shown[0]) % 2                                 # the sheet pairs 2016/17 + 2017/18, 2018/19 + 2019/20, ...
    lab, val = {}, {}
    for i, y in enumerate(shown):
        if (i + start) % 2 == 0 and i + 1 < len(shown):
            lab[y] = f"{y[:4]}/{shown[i + 1][5:7]}"                  # 2016/17 + 2017/18 -> 2016/18
            val[y] = glob.loc["Global Balance", y] + glob.loc["Global Balance", shown[i + 1]]
    out.append("<tr class='soft'><td class='lbl'>2 year cycle</td>" + "".join(f"<td>{lab.get(y, '')}</td>" for y in shown) + "</tr>")
    out.append("<tr class='b'><td class='lbl'>2 year balance</td>"
               + "".join(f"<td class='{'neg' if val.get(y, 0) < -0.049 else ''}'>{fnum(val[y]) if y in val else ''}</td>" for y in shown) + "</tr>")
    out.append(tr("Demand change", glob.loc["Global demand chg"], "soft", fpct))
    out.append(tr("Combined end season stock", glob.loc["Combined End Season Stock"], ""))
    out.append(tr("Combined S/U", glob.loc["Combined S/U"], "soft", fpct))
    return f"<div class='snd-wrap'><table class='snd'>{''.join(out)}</table></div>"


# ── Charts ────────────────────────────────────────────────────────────────────
def _style(fig, height=230, fmt=",.1f", legend=True):
    fig.update_layout(template="plotly_white", height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=INK, size=11), margin=dict(t=4, b=24, l=8, r=8), hovermode="x unified",
                      legend=dict(orientation="h", x=0, y=1.14, bgcolor="rgba(0,0,0,0)", font=dict(size=10.5)) if legend else None,
                      showlegend=legend, bargap=0.35,
                      xaxis=dict(color=AXIS, showgrid=False, type="category", tickfont=dict(size=10),
                                 tickangle=0, tickvals=None),
                      yaxis=dict(gridcolor=GRID, color=AXIS, hoverformat=fmt, zeroline=True, zerolinecolor="rgba(15,23,42,0.18)",
                                 tickfont=dict(size=10)))
    return fig


def charts(a, r, glob, shown):
    c1, c2, c3 = st.columns(3, gap="small")
    short = {y: y[2:] for y in shown}                                # 2024/25 -> 24/25 on the axes
    with c1, st.container(border=True):
        st.markdown("<div class='chart-head'>Balance</div><div class='card-desc'>m bags</div>", unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=[short[y] for y in shown], y=a.loc["Balance", shown], name="Arabica", marker_color=NAVY, marker_line_width=0))
        fig.add_trace(go.Bar(x=[short[y] for y in shown], y=r.loc["Balance", shown], name="Robusta", marker_color=AMBER, marker_line_width=0))
        st.plotly_chart(_style(fig).update_layout(barmode="group"), width="stretch", key="c_bal")
    with c2, st.container(border=True):
        st.markdown("<div class='chart-head'>Stocks to use</div><div class='card-desc'>end stock / consumption</div>", unsafe_allow_html=True)
        fig = go.Figure()
        for nm, ser, col in [("Arabica", a.loc["S/U", shown], NAVY), ("Robusta", r.loc["S/U", shown], AMBER),
                             ("Combined", glob.loc["Combined S/U", shown], TEAL)]:
            fig.add_trace(go.Scatter(x=[short[y] for y in shown], y=ser, name=nm, mode="lines+markers", line=dict(color=col, width=2.2)))
        st.plotly_chart(_style(fig, fmt=".1%").update_layout(yaxis_tickformat=".0%"), width="stretch", key="c_su")
    with c3, st.container(border=True):
        st.markdown("<div class='chart-head'>Global production and consumption</div><div class='card-desc'>m bags</div>", unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=[short[y] for y in shown], y=glob.loc["Production Global", shown], name="Production", marker_color="#c3cbe0"))
        fig.add_trace(go.Scatter(x=[short[y] for y in shown], y=glob.loc["Consumption Global", shown], name="Consumption", mode="lines+markers",
                                 line=dict(color=NAVY, width=2.4)))
        st.plotly_chart(_style(fig), width="stretch", key="c_glob")


# ── Edit view: the main table, with the inputs editable ────────────────────────────────────────────────────
def calc_table(comm, fr, glob, shown, meta) -> str:
    """The calculated rows of one commodity, shown under its editable inputs (they move as you type)."""
    shaded = star = is_estimate

    def tr(label, vals, kind, fmt, neg=False):
        cells = "".join(f"<td class='{'fc ' if shaded(y) else ''}{'neg' if neg and pd.notna(vals[y]) and vals[y] < -0.049 else ''}'>{fmt(vals[y])}</td>"
                        for y in shown)
        return f"<tr class='{kind}'><td class='lbl'>{label}</td>{cells}</tr>"

    head = "<tr><th class='y first'></th>" + "".join(f"<th class='y{' fc' if shaded(y) else ''}'>{y}{'*' if star(y) else ''}</th>" for y in shown) + "</tr>"
    rows = [tr("Production", fr.loc["Production"], "b", fnum), tr("Consumption %", fr.loc["Consumption %"], "soft", fpct),
            tr("Balance", fr.loc["Balance"], "bal", fnum, True), tr("End season stock", fr.loc["End Season Stock"], "", fnum),
            tr("S/U", fr.loc["S/U"], "soft", lambda v: fpct(v, 1 if comm == "Arabica" else 0))]
    if comm == "Robusta":
        rows.append(tr("Robusta demand share", glob.loc["Robusta demand share"], "soft", lambda v: fpct(v, 0)))
    return f"<div class='snd-wrap' style='border-radius:0 0 8px 8px;margin-top:0'><table class='snd'>{head}{''.join(rows)}</table></div>"


def render_edit(df, meta, years, shown, editable):
    """Edit mode: each commodity's inputs as an editable grid in the table's layout; the calculated rows below it follow the edits live.
    One Save for both commodities."""
    live = df
    changes_all, keys = [], []
    grids = {}
    for comm in ORIGINS:
        items = ORIGINS[comm] + ["Consumption"]
        d = df[df["commodity"] == comm].pivot_table(index="item", columns="year", values="value", aggfunc="sum").reindex(index=items, columns=shown)
        g = d.map(_fmt)
        st.markdown(f"<div class='snd-bar'>{comm}</div>", unsafe_allow_html=True)
        cols = {y: st.column_config.TextColumn(f"{y}{'*' if is_estimate(y) else ''}", alignment="right", width=86) for y in shown}
        cols["_index"] = st.column_config.TextColumn("", width=120)
        key = f"snd_edit_{comm}_{len(shown)}"
        keys.append(key)
        after = st.data_editor(g, column_config=cols, disabled=not editable, width="stretch", row_height=28,
                               height=len(g) * 28 + 40, key=key)
        grids[comm] = (g, after)
        try:
            ch = [(comm, it, y, _num(g.loc[it, y]), _num(after.loc[it, y])) for it in items for y in shown
                  if _num(g.loc[it, y]) != _num(after.loc[it, y])]
        except ValueError:
            st.error("Numbers only.")
            return
        changes_all += ch
        live = _apply_changes(live, ch)
        fr = block(live, meta, comm, years)
        grids[comm] += (fr,)
        glob = global_block(grids["Arabica"][2], fr, years) if comm == "Robusta" else None
        st.markdown(calc_table(comm, fr, glob, shown, meta), unsafe_allow_html=True)   # calculated rows under their grid, from the edits
    if any(c[4] is not None and c[4] < 0 for c in changes_all):
        st.error("Values cannot be negative.")
        changes_all = []
    if not editable:
        st.markdown("<div class='card-desc'>Read-only: add github_token in Secrets to edit.</div>", unsafe_allow_html=True)
        return
    bc = st.columns([1, 1, 6], vertical_alignment="center")
    save = bc[0].button("Save", type="primary", disabled=not changes_all, width="stretch", key="snd_save")
    if bc[1].button("Undo", disabled=not changes_all, width="stretch", key="snd_undo"):
        for k in keys:
            st.session_state.pop(k, None)
        st.rerun()
    if changes_all:
        bc[2].markdown(f"<div class='card-desc' style='margin:0'>{len(changes_all)} unsaved cell(s) - the rows under each grid already show the result.</div>",
                       unsafe_allow_html=True)
    if save:
        try:
            with st.spinner("Saving..."):
                _save_inputs(changes_all)
        except (gh.GitHubError, Exception) as ex:
            st.error(f"GitHub save failed: {ex}")
        else:
            for k in keys:
                st.session_state.pop(k, None)
            st.session_state["en_flash"] = f"Saved {len(changes_all)} change(s)."
            st.rerun()


# ── Page ──────────────────────────────────────────────────────────────────────
def render():
    st.markdown(CSS, unsafe_allow_html=True)
    df, meta, notes, years = load()
    with st.sidebar:
        st.markdown("<div class='sb-sep'></div>", unsafe_allow_html=True)
        span = st.radio("Years", ["Last 10", "All"], horizontal=True, key="snd_span")
        mode = st.radio("Mode", ["View", "Edit"], horizontal=True, key="snd_mode")
    shown = years[-10:] if span == "Last 10" else years
    if st.session_state.get("en_flash"):
        st.toast(st.session_state.pop("en_flash"))
    a, r = block(df, meta, "Arabica", years), block(df, meta, "Robusta", years)
    glob = global_block(a, r, years)
    combo = a.loc["Brazil"] + r.loc["Brazil"]
    st.markdown("<div class='snd-head'><span class='t'>Coffee SnD</span><span class='s'>Jul–Jun · million 60 kg bags · * estimate"
                + (" · editing inputs" if mode == "Edit" else "") + "</span></div>", unsafe_allow_html=True)
    if mode == "Edit":
        render_edit(df, meta, years, shown, gh.enabled())
        return
    st.markdown(snd_table(df, meta, notes, years, shown, {"Arabica": a, "Robusta": r}, glob, combo), unsafe_allow_html=True)
    charts(a, r, glob, shown)


# ── Entry ─────────────────────────────────────────────────────────────────────
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


def _save_inputs(changes):
    lines = [f"{c} {it} {y}: {_fmt(o) or '-'} -> {_fmt(n) or '-'}" for c, it, y, o, n in changes]
    msg = f"Coffee SnD | {len(changes)} change(s)\n\n" + "\n".join(lines)

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


def render_entry():
    st.markdown(CSS, unsafe_allow_html=True)
    if st.session_state.get("en_flash"):
        st.toast(st.session_state.pop("en_flash"))
    st.markdown("<div class='page-title'>Entry</div>", unsafe_allow_html=True)
    df, meta, notes, years = load()
    editable = gh.enabled()
    comm = st.radio("Commodity", list(ORIGINS), horizontal=True, label_visibility="collapsed", key="en_comm")
    items = ORIGINS[comm] + ["Consumption"]
    d = df[df["commodity"] == comm].pivot_table(index="item", columns="year", values="value", aggfunc="sum").reindex(index=items, columns=years)
    g = d.map(_fmt)
    with st.container(border=True):
        st.markdown(f"<div class='card-title'>{comm} inputs <span class='pill'>m bags</span></div>", unsafe_allow_html=True)
        cols = {y: st.column_config.TextColumn(f"{y}{'*' if is_estimate(y) else ''}", alignment="right", width=82) for y in years}
        cols["_index"] = st.column_config.TextColumn("", width=110)
        key = f"en_grid_{comm}"
        after = st.data_editor(g, column_config=cols, disabled=not editable, width="content", row_height=28,
                               height=len(g) * 28 + 48, key=key)
        if not editable:
            st.markdown("<div class='card-desc'>Read-only: add github_token in Secrets to edit.</div>", unsafe_allow_html=True)
        else:
            changes = []
            try:
                for it in items:
                    for y in years:
                        o, n = _num(g.loc[it, y]), _num(after.loc[it, y])
                        if o != n:
                            changes.append((comm, it, y, o, n))
            except ValueError:
                st.error("Numbers only.")
                changes = []
            if any(c[4] is not None and c[4] < 0 for c in changes):
                st.error("Values cannot be negative.")
                changes = []
            bc = st.columns([1, 1, 4], vertical_alignment="center")
            save = bc[0].button("Save", type="primary", disabled=not changes, width="stretch", key="en_save")
            if bc[1].button("Undo", disabled=not changes, width="stretch", key="en_undo"):
                st.session_state.pop(key, None)
                st.rerun()
            if changes:
                bc[2].markdown(f"<div class='card-desc' style='margin:0'>{len(changes)} unsaved cell(s).</div>", unsafe_allow_html=True)
            if save:
                try:
                    with st.spinner("Saving..."):
                        _save_inputs(changes)
                except (gh.GitHubError, Exception) as ex:
                    st.error(f"GitHub save failed: {ex}")
                else:
                    st.session_state.pop(key, None)
                    st.session_state["en_flash"] = f"Saved {len(changes)} change(s)."
                    st.rerun()

    with st.container(border=True):
        st.markdown(f"<div class='card-title'>{comm} settings</div>", unsafe_allow_html=True)
        gc = st.columns([1.3, 1, 5], vertical_alignment="bottom")
        op_old = float(meta["opening_stock"][comm])
        op = gc[0].number_input(f"End stock {years[0]} (m bags)", min_value=0.0, value=op_old, step=0.1, format="%.1f",
                                key=f"en_open_{comm}", disabled=not editable)
        if gc[1].button("Save", disabled=(not editable) or abs(op - op_old) < 1e-9, width="stretch", key=f"en_set_{comm}"):
            try:
                with st.spinner("Saving..."):
                    def mut(m):
                        m["opening_stock"][comm] = round(float(op), 4)
                    _save_meta(f"{comm} opening stock", f"{op_old:g}", f"{op:g}", mut)
            except (gh.GitHubError, Exception) as ex:
                st.error(f"GitHub save failed: {ex}")
            else:
                st.session_state["en_flash"] = f"{comm} settings saved."
                st.rerun()

    if editable:
        with st.expander("Save history", expanded=False):
            try:
                items_h = gh.history(CSV_PATH) + gh.history(META_PATH)
            except Exception as ex:
                st.markdown(f"<div class='card-desc'>Not available: {ex}</div>", unsafe_allow_html=True)
                return
            rows = []
            for ts, msg in sorted(items_h, key=lambda x: x[0], reverse=True):
                when = pd.Timestamp(ts).tz_convert(TZ)
                first, _, body = msg.partition("\n")
                if first.startswith("Coffee SnD |"):
                    for ln in [x for x in body.splitlines() if x.strip()]:
                        what, _, vals = ln.partition(": ")
                        o, _, n = vals.partition(" -> ")
                        rows.append((when, what, o, n, "Dashboard"))
                elif first.startswith("Setting |"):
                    what, _, vals = first[len("Setting | "):].partition(": ")
                    o, _, n = vals.partition(" -> ")
                    rows.append((when, what, o, n, "Dashboard"))
                else:
                    rows.append((when, first[:60], "", "", "Local push"))
            body = "".join(f"<tr><td class='ts'>{w:%d %b %H:%M}</td><td class='dt'>{what}</td><td>{o}</td><td class='b'>{n}</td>"
                           f"<td class='ts'>{via}</td></tr>" for w, what, o, n, via in rows[:20])
            st.markdown("<table class='dtab'><tr class='sub'><th>Saved at</th><th>What</th><th>Old</th><th>New</th><th>Via</th></tr>"
                        f"{body}</table>", unsafe_allow_html=True)
