"""Colombia Internal SnD: monthly Production, Imports and Consumption (bags, Oct-Sep crop year) from
Database/colombia_snd.csv (long: series, crop_year, cm, bags; cm 1 = Oct). Exports are not stored here: they come from
Aggregated Exports (origin Colombia), so each month has one number; edits made here are saved into Aggregated Exports'
manual entries, so either Edit page changes the same figure. Everything else is calculated:

  Net exports   = Exports - Imports
  Stocks change = Production - Net exports - Consumption

View: the monthly stocks-change table (data bars, like the desk's Excel), then any series through the Aggregated Exports
charts (seasonal range, cumulative, rolling, table, full-year totals, YTD), then the crop-year balance.
Edit Mode: type over any month of the four inputs; saves go to the data branch like the other SnD pages.
"""
import io
from pathlib import Path

import pandas as pd
import streamlit as st

import exports_view as ev
import ghstore as gh

CSV = Path(__file__).resolve().parent.parent / "Database" / "colombia_snd.csv"
CSV_PATH = "Database/colombia_snd.csv"                             # path in the repo
INPUTS = ["Production", "Exports", "Imports", "Consumption"]
SERIES = ["Stocks change", "Production", "Exports", "Imports", "Net exports", "Consumption"]
MONTHS = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"]
START = 10                                                         # crop year starts in October
POS, NEG = "rgba(31,157,111,.38)", "rgba(201,74,74,.38)"           # data bars: COT ice green / red
AXIS = "rgba(43,74,138,.35)"

CSS = """
<style>
.cl-wrap { overflow-x: auto; }
table.cl { border-collapse: separate; border-spacing: 0; width: 100%; font-size: 12px; font-variant-numeric: tabular-nums; }
table.cl th { padding: 6px 8px; text-align: center; white-space: nowrap; }
table.cl td { padding: 3px 8px; text-align: right; white-space: nowrap; color: #1a1a2e;
  background-repeat: no-repeat; background-position: center; background-size: 100% 100%, 100% 64%; }
table.cl td.lbl { text-align: left; }
table.cl td.tot { font-weight: 700; border-left: 1px solid rgba(43,74,138,.22) !important; }
table.cl th.tot { border-left: 1px solid rgba(43,74,138,.22) !important; }
table.cl td.neg { color: #b03a3a; }
table.cl tr.est td.lbl { font-style: italic; }
</style>
"""


# ── Data ──────────────────────────────────────────────────────────────────────
def stored() -> pd.DataFrame:
    """The inputs kept in colombia_snd.csv - the latest saved version (data branch when a token is set, else the local file)."""
    d = pd.read_csv(io.StringIO(gh.text_of(CSV_PATH, CSV)), dtype={"crop_year": str})
    d = d[d["series"] != "Exports"].dropna(subset=["bags"])
    d["cm"] = d["cm"].astype(int)
    return d


def agg_exports(years) -> pd.DataFrame:
    """Colombia exports from Aggregated Exports (manual > history > TDM), re-labelled onto the Oct-Sep crop year,
    limited to the crop years the other inputs cover."""
    a = ev.dx.combine()
    a = a[a["origin"] == "Colombia"]
    y0 = a["year"] - (a["month"] < START).astype(int)
    out = pd.DataFrame({"series": "Exports", "crop_year": [f"{y % 100:02d}/{(y + 1) % 100:02d}" for y in y0],
                        "cm": ((a["month"] - START) % 12 + 1).astype(int).values, "bags": a["bags"].round().values})
    return out[out["crop_year"].isin(years)]


def load() -> pd.DataFrame:
    """series, crop_year, cm, bags for all four inputs: the stored three plus exports from Aggregated Exports."""
    d = stored()
    return pd.concat([d, agg_exports(set(d["crop_year"]))], ignore_index=True)


def wide(d: pd.DataFrame, name: str) -> pd.DataFrame:
    """crop year x crop month (1-12) in bags for an input or a calculated series. NaN = missing."""
    def one(s):
        x = d[d["series"] == s]
        years = sorted(d["crop_year"].unique())
        return x.pivot_table(index="crop_year", columns="cm", values="bags", aggfunc="sum").reindex(index=years, columns=range(1, 13))
    if name in INPUTS:
        return one(name)
    nx = one("Exports") - one("Imports")
    if name == "Net exports":
        return nx
    return one("Production") - nx - one("Consumption")             # Stocks change


def complete_months(piv: pd.DataFrame) -> pd.DataFrame:
    """Drop trailing crop years with no data at all (e.g. a row added in Edit but left empty)."""
    keep = piv.notna().any(axis=1)
    return piv.loc[keep[keep].index.min():keep[keep].index.max()] if keep.any() else piv


# ── Stocks-change table with data bars ────────────────────────────────────────
def _bar(v, lo_abs, hi_abs):
    """Inline background for one cell: a thin axis line plus a green (right of axis) or red (left of axis) bar."""
    if pd.isna(v) or (lo_abs + hi_abs) == 0:
        return ""
    tot = lo_abs + hi_abs
    a = lo_abs / tot * 100
    w = abs(v) / tot * 100
    left, right, col = (a, a + w, POS) if v >= 0 else (a - w, a, NEG)
    axis = (f"linear-gradient(90deg, transparent calc({a:.2f}% - .5px), {AXIS} calc({a:.2f}% - .5px), "
            f"{AXIS} calc({a:.2f}% + .5px), transparent calc({a:.2f}% + .5px))")
    bar = (f"linear-gradient(90deg, transparent {left:.2f}%, {col} {left:.2f}%, {col} {right:.2f}%, "
           f"transparent {right:.2f}%)")
    return f" style='background-image:{axis},{bar}'"


def bar_table(piv: pd.DataFrame, title: str, desc: str = ""):
    piv = complete_months(piv)
    m = piv.to_numpy(dtype=float)
    lo, hi = max(0.0, -pd.Series(m.ravel()).min()), max(0.0, pd.Series(m.ravel()).max())
    tot = piv.sum(axis=1, min_count=1)
    tlo, thi = max(0.0, -tot.min()), max(0.0, tot.max())
    head = "<tr><th>Year</th>" + "".join(f"<th>{mn}</th>" for mn in MONTHS) + "<th class='tot'>Total</th></tr>"
    rows = []
    for y in piv.index:
        part = piv.loc[y].notna().sum() < 12
        cells = []
        for cm in range(1, 13):
            v = piv.loc[y, cm]
            txt = "" if pd.isna(v) else f"{v:,.0f}"
            cells.append(f"<td class='{'neg' if v < 0 else ''}'{_bar(v, lo, hi)}>{txt}</td>")
        t = tot[y]
        cells.append(f"<td class='tot{' neg' if t < 0 else ''}'{_bar(t, tlo, thi)}>{'' if pd.isna(t) else f'{t:,.0f}'}</td>")
        rows.append(f"<tr class='{'est' if part else ''}'><td class='lbl'>{y}{'*' if part else ''}</td>{''.join(cells)}</tr>")
    d = f"<div class='card-desc'>{desc}</div>" if desc else ""
    st.markdown(f"<div class='chart-head'>{title}</div>{d}<div class='cl-wrap'><table class='cl tbl'>{head}{''.join(rows)}</table></div>",
                unsafe_allow_html=True)


# ── Crop-year balance (Brazil Internal SnD look) ──────────────────────────────
LAYOUT = [("Production", "b"), ("Exports", ""), ("Imports", ""), ("Net exports", "b"), ("Consumption", ""), ("Stocks change", "bal")]


def _long(cy: str) -> str:
    """'14/15' -> '2014/15', the label the SnD helpers (sparklines, estimates) expect."""
    return f"20{cy}"


PROJ_YEARS = 5                                                     # complete crop years behind the seasonal shares
BIG = """
table.snd { font-size: 13.5px !important; }
table.snd td, table.snd th.y { padding: 5px 13px !important; }
table.snd th.y { font-size: 11.5px !important; }
table.snd td.lbl { min-width: 130px; }
table.snd td.pj, table.snd th.pj { background: rgba(201,138,31,.07) !important; font-style: italic; color: #7a5212 !important; }
table.snd th.pj { border-bottom-color: rgba(201,138,31,.35) !important; }
table.snd tr.bal td.pj.neg { color: #b03a3a !important; }
"""


def projection(d: pd.DataFrame) -> dict:
    """Full-year forecast for the running crop year, per input, in bags: YTD / the share of the year those same months made
    up on average over the last PROJ_YEARS complete crop years (seasonal share). An input already complete keeps its total.
    Net exports and stocks change follow from the four. {} when the latest crop year is complete."""
    out = {}
    latest = complete_months(wide(d, "Production")).index[-1]
    for s in INPUTS:
        p = wide(d, s)
        if latest not in p.index:
            return {}
        row = p.loc[latest]
        k = int(row.notna().cumprod().sum())                       # months in from October, no gaps
        if k == 0:
            return {}
        if k == 12:
            out[s] = float(row.sum())
            continue
        full = [y for y in p.index if y != latest and p.loc[y].notna().all()][-PROJ_YEARS:]
        if not full:
            return {}
        share = float((p.loc[full, list(range(1, k + 1))].sum(axis=1) / p.loc[full].sum(axis=1)).mean())
        out[s] = float(row[list(range(1, k + 1))].sum()) / share
        out[f"_k_{s}"] = k
    if all(out.get(f"_k_{s}") is None for s in INPUTS):
        return {}                                                  # latest year already complete: nothing to project
    out["Net exports"] = out["Exports"] - out["Imports"]
    out["Stocks change"] = out["Production"] - out["Net exports"] - out["Consumption"]
    return out


def balance_table(d: pd.DataFrame):
    """Crop-year totals, transposed (series down, crop years across) in the SnD table style, m bags, plus a full-year
    forecast column for the running crop year."""
    import snd
    import tableedit
    sums = {c: complete_months(wide(d, c)).sum(axis=1, min_count=1) / 1e6 for c, _k in LAYOUT}
    years = sums["Production"].index.tolist()
    n = complete_months(wide(d, "Stocks change")).notna().sum(axis=1)
    part = {y: n.get(y, 12) < 12 for y in years}
    proj = projection(d)
    pj_lab = f"{years[-1]}F"
    ncol = len(years) + 2 + bool(proj)
    out = [f"<tr class='comm'><th colspan='{ncol}'>Colombia<span class='crop'>Oct–Sep · m bags</span></th></tr>",
           "<tr><th class='y first'></th>" + "".join(f"<th class='y{' fc' if part[y] else ''}'>{y}{'*' if part[y] else ''}</th>" for y in years)
           + (f"<th class='y pj'>{pj_lab}</th>" if proj else "") + "<th class='y spark-h'>Trend</th></tr>"]
    for label, kind in LAYOUT:
        s = sums[label]
        neg = lambda v: kind == "bal" and pd.notna(v) and v < -0.0049     # noqa: E731
        cells = "".join(f"<td class='{('fc ' if part[y] else '') + ('neg' if neg(s[y]) else '')}'>{snd.fnum(s[y], 2)}</td>" for y in years)
        if proj:
            v = proj[label] / 1e6
            cells += f"<td class='pj{' neg' if neg(v) else ''}'>{snd.fnum(v, 2)}</td>"
        pts = [(_long(y), s[y]) for y in years]
        spark = snd.sparkline_balance(pts, label) if kind == "bal" else snd.sparkline(pts, label, "plain")
        out.append(f"<tr class='{kind}'><td class='lbl'>{label}</td>{cells}<td class='spark-td'>{spark}</td></tr>")
    tableedit.editable_table(f"<div class='snd-wrap'><table class='snd'>{''.join(out)}</table></div>", tableedit.css_of(snd.CSS) + BIG,
                             "cl_bal_tbl", 0, editable=False)
    note = "* = crop year still running (months so far) · Stocks change = Production − Net exports − Consumption"
    if proj:
        ks = sorted({proj[f"_k_{s}"] for s in INPUTS if f"_k_{s}" in proj})
        upto = MONTHS[ks[0] - 1] if len(ks) == 1 else "latest month"
        note += (f" · <b>{pj_lab}</b> = full-year forecast: YTD (Oct–{upto}) ÷ the share of the year those months made up, "
                 f"average of the last {PROJ_YEARS} complete crop years; consumption = its yearly figure")
    st.markdown(f"<div class='card-desc'>{note}</div>", unsafe_allow_html=True)


# ── View (reuses the Aggregated Exports charts) ───────────────────────────────
def _ctx(piv_bags: pd.DataFrame, label: str, unit: str, span: str) -> dict:
    """The same context dict exports_view builds, for one Colombia series."""
    factor, fmt = ev.UNITS[unit]
    piv = complete_months(piv_bags) * factor
    years = piv.index.tolist()
    latest_cy = years[-1]
    valid = piv.loc[latest_cy].dropna().index
    common = int(valid.max()) if len(valid) else 12
    ytd = piv[list(range(1, common + 1))].sum(axis=1, min_count=1)
    n_show = {"Last 5": 5, "Last 10": 10, "All": len(years)}[span]
    return dict(parts={}, gbe=1.0, comm=label, unit=unit, span=span, fmt=fmt, piv=piv, years=years, latest_cy=latest_cy,
                prev_cy=years[-2] if len(years) >= 2 else None, common=common, ref=[y for y in years if y != latest_cy][-10:],
                ytd=ytd, yoy=ytd.pct_change(fill_method=None) * 100, cut=f"{MONTHS[0]}–{MONTHS[common - 1]}",
                shown=years[-n_show:], sc=f"{label} · {unit}", sig=(label, unit, latest_cy, common))


def _explorer(d: pd.DataFrame):
    ev.seed("cl_span", "All")
    ev.seed("cl_series", "Production")
    lab = lambda name: (lambda v: f"{name} · {v}")                   # noqa: E731
    with st.container(key="mc_bar", horizontal=True, vertical_alignment="center"):
        series = st.selectbox("Series", SERIES, key="cl_series", format_func=lab("Series"), label_visibility="collapsed", width=230)
        span = st.selectbox("Years", ["Last 5", "Last 10", "All"], key="cl_span", format_func=lab("Years"),
                            label_visibility="collapsed", width=145)
        unit = st.selectbox("Unit", list(ev.UNITS), key="cl_unit", format_func=lab("Unit"), label_visibility="collapsed", width=170)
    ctx = _ctx(wide(d, series), series, unit, span)
    saved = ev.MONTHS, ev.START, ev.TITLE                           # the exports charts read these module globals
    ev.MONTHS, ev.START, ev.TITLE = MONTHS, START, "Colombia {comm} · {kind}"
    try:
        ev._charts(ctx, {})
        if series == "Stocks change":                              # YoY %, vs-10y-avg and full-year pace make no sense for a
            with st.container(border=True, key="mc_card_stocks"):  # flow that swings around zero: the data-bar table instead
                bar_table(wide(d, "Stocks change"), "Colombia monthly stocks change",
                          "bags · Production − (Exports − Imports) − Consumption · * = crop year still running")
            return
        t_col, p_col, y_col = st.columns([2.9, 1, 1], gap="small")
        with t_col, st.container(border=True, key="mc_card_table"):
            ev._table(ctx)
        with p_col, st.container(border=True, key="mc_card_pace"):
            ev._pace(ctx, {})
        with y_col, st.container(border=True, key="mc_card_ytd"):
            ev._ytd(ctx)
    finally:
        ev.MONTHS, ev.START, ev.TITLE = saved


def render(mode_slot=None):
    import theme
    st.markdown(ev.CSS + CSS, unsafe_allow_html=True)
    with (mode_slot or st.sidebar), st.container(key="mode_nav"):
        mode = theme.mode_switch("cl_mode")
    if st.session_state.get("en_flash"):
        st.toast(st.session_state.pop("en_flash"))
    d = load()
    if mode == "Edit":
        render_edit(d)
        return
    st.markdown("<div class='mc-hero-t'>Colombia Internal SnD</div>", unsafe_allow_html=True)
    balance_table(d)
    ev.section("Series")
    _explorer(d)


# ── Edit Mode ─────────────────────────────────────────────────────────────────
def _next_cy(cy: str) -> str:
    y = int(cy[:2]) + 1
    return f"{y % 100:02d}/{(y + 1) % 100:02d}"


def _grid(d: pd.DataFrame, series: str) -> pd.DataFrame:
    years = sorted(d["crop_year"].unique())
    years.append(_next_cy(years[-1]))                              # one empty row to start the next crop year
    p = wide(d, series).reindex(years)
    g = pd.DataFrame({MONTHS[cm - 1]: [ev._fmt0(p.loc[y, cm]) for y in years] for cm in range(1, 13)}, index=years)
    g.index.name = "Year"
    return g


def _grid_annual(d: pd.DataFrame) -> pd.DataFrame:
    """Consumption is typed as one yearly number per crop year (spread evenly over the 12 months on save)."""
    years = sorted(d["crop_year"].unique())
    years.append(_next_cy(years[-1]))
    tot = wide(d, "Consumption").reindex(years).sum(axis=1, min_count=1)
    g = pd.DataFrame({"Annual": [ev._fmt0(tot[y]) for y in years]}, index=years)
    g.index.name = "Year"
    return g


def _changes_annual(d: pd.DataFrame, before: pd.DataFrame, after: pd.DataFrame) -> list:
    """An edited yearly consumption -> one change per month (annual / 12). Cleared -> the 12 months removed."""
    p = wide(d, "Consumption")
    out = []
    for y in before.index:
        a, b = before.loc[y, "Annual"], after.loc[y, "Annual"]
        if str(a or "").strip() == str(b or "").strip():
            continue
        try:
            new = ev._num(b)
        except ValueError:
            raise ValueError(f"Consumption {y}: numbers only (commas are fine).") from None
        if new is not None and new < 0:
            raise ValueError(f"Consumption {y}: values cannot be negative.")
        for cm in range(1, 13):
            old = p.loc[y, cm] if y in p.index and pd.notna(p.loc[y, cm]) else None
            out.append(("Consumption", y, cm, old, None if new is None else new / 12))
    return out


def _changes(series, before: pd.DataFrame, after: pd.DataFrame) -> list:
    """[(series, crop_year, cm, old, new)] for every edited cell. Raises ValueError on non-numbers or negatives."""
    out = []
    for y in before.index:
        for cm in range(1, 13):
            a, b = before.loc[y, MONTHS[cm - 1]], after.loc[y, MONTHS[cm - 1]]
            if str(a or "").strip() == str(b or "").strip():
                continue
            try:
                old, new = ev._num(a), ev._num(b)
            except ValueError:
                raise ValueError(f"{series} {y} {MONTHS[cm - 1]}: numbers only (commas are fine).") from None
            if new is not None and new < 0:
                raise ValueError(f"{series} {y} {MONTHS[cm - 1]}: values cannot be negative.")
            if old != new:
                out.append((series, y, cm, old, new))
    return out


def _apply(d: pd.DataFrame, changes: list) -> pd.DataFrame:
    cells = {(s, y, int(cm)): b for s, y, cm, b in zip(d["series"], d["crop_year"], d["cm"], d["bags"])}
    for s, y, cm, _old, new in changes:
        if new is None:
            cells.pop((s, y, cm), None)
        else:
            cells[(s, y, cm)] = new
    out = pd.DataFrame([(s, y, cm, int(round(b))) for (s, y, cm), b in cells.items()], columns=["series", "crop_year", "cm", "bags"])
    order = {s: i for i, s in enumerate(INPUTS)}
    return out.sort_values(["series", "crop_year", "cm"], key=lambda c: c.map(order) if c.name == "series" else c).reset_index(drop=True)


def _save(changes: list, reason: str):
    lines = [f"{s} {y} {MONTHS[cm - 1]}: {'' if o is None else f'{o:,.0f}'} -> {'' if n is None else f'{n:,.0f}'}"
             for s, y, cm, o, n in changes]
    msg = f"Colombia SnD | {len(changes)} change(s)" + (f" | {reason}" if reason else "") + "\n\n" + "\n".join(lines)

    def apply(text):
        cur = pd.read_csv(io.StringIO(text), dtype={"crop_year": str})
        cur = cur[cur["series"] != "Exports"]                       # exports live in Aggregated Exports
        return _apply(cur, changes).to_csv(index=False, lineterminator="\n"), None
    gh.commit(CSV_PATH, apply, msg, default=CSV.read_text(encoding="utf-8"))


def _editor(d: pd.DataFrame, series: str, editable: bool, epoch: int) -> list:
    """One input's grid; returns its unsaved changes. Consumption is one yearly number per crop year; Exports are the
    Aggregated Exports figures (saved back there)."""
    annual = series == "Consumption"
    linked = series == "Exports"
    g = _grid_annual(d) if annual else _grid(d, series)
    with st.container():                                           # no card: its padding would cost the grid ~30px
        st.markdown(f"<div class='card-title'>{series}, bags"
                    + ("<span class='pill'>yearly · saved as 1/12 per month</span>" if annual else "")
                    + ("<span class='pill'>shared with Aggregated Exports</span>" if linked else "") + "</div>",
                    unsafe_allow_html=True)
        cfg = ({"Annual": st.column_config.TextColumn("Annual", alignment="right", width=100)} if annual else
               {mn: st.column_config.TextColumn(mn, alignment="right", width=65) for mn in MONTHS})   # fits 1,800,000
        cfg["_index"] = st.column_config.TextColumn("Year", width=40)
        after = st.data_editor(g, column_config=cfg, disabled=not editable, width="content", row_height=22,   # compact: fits
                               height=len(g) * 22 + 38, key=f"cl_ed_{series}_{epoch}")                    # without scrolling
        try:
            return _changes_annual(d, g, after) if annual else _changes(series, g, after)
        except ValueError as ex:
            st.error(str(ex))
            return []


def _save_exports(changes: list):
    """Colombia export edits -> Aggregated Exports manual entries (calendar year / month). A cleared month drops the manual
    entry, so the history / TDM figure shows again."""
    rows = []
    for _s, cy, cm, old, new in changes:
        month = (cm + START - 2) % 12 + 1
        year = 2000 + int(cy[:2]) + (month < START)
        rows.append(("Colombia", year, month, old, new))
    ev._save_manual(rows)


def render_edit(d: pd.DataFrame):
    """All four inputs on one page (Production / Exports monthly, Imports monthly, Consumption yearly), one Save."""
    editable = gh.enabled()
    st.markdown("<div class='mc-hero-t'>Colombia Internal SnD · Edit Mode</div>", unsafe_allow_html=True)
    if not editable:
        st.markdown("<div class='card-desc'>Read-only: add github_token in Secrets to edit.</div>", unsafe_allow_html=True)
    epoch = st.session_state.get("cl_epoch", 0)
    bar = st.container()                                           # Save / Discard, filled once every grid is read
    changes = []
    l, r = st.columns(2, gap="small")
    with l:
        changes += _editor(d, "Production", editable, epoch)
        changes += _editor(d, "Imports", editable, epoch)
    with r:
        changes += _editor(d, "Exports", editable, epoch)
        changes += _editor(d, "Consumption", editable, epoch)
    if editable:
        with bar:
            bc = st.columns([1, 1, 3, 2], vertical_alignment="center")
            reason = bc[2].text_input("Reason", key=f"cl_reason_{epoch}", placeholder="Reason (optional)",
                                      label_visibility="collapsed")
            if bc[0].button(f"Save ({len(changes)})" if changes else "Save", type="primary", disabled=not changes,
                            key="cl_save", width="stretch"):
                try:
                    with st.spinner("Saving..."):
                        exp = [c for c in changes if c[0] == "Exports"]
                        rest = [c for c in changes if c[0] != "Exports"]
                        if exp:
                            _save_exports(exp)
                        if rest:
                            _save(rest, reason.strip())
                except Exception as ex:                                # GitHubError or network
                    st.error(f"GitHub save failed: {ex}")
                else:
                    st.session_state["cl_epoch"] = epoch + 1
                    st.session_state["en_flash"] = f"Colombia SnD: {len(changes)} month(s) saved."
                    st.rerun()
            if bc[1].button("Discard", disabled=not changes, key="cl_discard", width="stretch"):
                st.session_state["cl_epoch"] = epoch + 1
                st.rerun()
    if editable:
        with st.expander("Save history", expanded=False):
            try:
                items = gh.history(CSV_PATH)
            except Exception as ex:
                st.markdown(f"<div class='card-desc'>Not available: {ex}</div>", unsafe_allow_html=True)
                items = []
            for ts, msg in items:
                if msg.startswith("Colombia SnD |"):
                    head, _, body = msg.partition("\n\n")
                    st.markdown(f"<div class='card-desc'><b>{pd.Timestamp(ts).tz_convert(ev.TZ):%d %b %H:%M}</b> · "
                                f"{head.split('|', 1)[1].strip()}<br>{body.replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
