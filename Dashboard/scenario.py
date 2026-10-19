"""Scenarios: two tools on one page.

1. What-if: change production by origin or consumption (percent), for the crop years you pick, and read the balance and stocks.
2. Sensitivity: flex one origin (or consumption) in one crop year by a step size you choose and see what stocks-to-use, the balance or the
   end stock do. Nothing here is saved or changes the data.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analytics
import snd
from analytics import _fig, card
from snd import AMBER, NAVY, ORIGINS, block, fnum, fpct, global_block, ystart

PROD_KEYS = [f"{c}|{o}" for c in ORIGINS for o in ORIGINS[c]]
CONS_KEYS = [f"{c}|Consumption" for c in ORIGINS]
ALL_KEYS = PROD_KEYS + CONS_KEYS
SCOPES = ["Arabica", "Robusta", "Combined"]

CSS = """
<style>
.kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 8px; }
.kpi { background: #ffffff; border: 1px solid #e6e9f0; border-radius: 10px; padding: 9px 13px; box-shadow: 0 1px 2px rgba(15,23,42,.04); }
.kpi .l { font-size: 10px; text-transform: uppercase; letter-spacing: .09em; color: #94a3b8; font-weight: 600; }
.kpi .v { font-size: 22px; font-weight: 700; color: #0a2463; letter-spacing: -.01em; line-height: 1.2; }
.kpi .d { font-size: 11.5px; color: #64748b; }
.kpi .d b.up { color: #1f9d6f; } .kpi .d b.dn { color: #c0392b; }
.sec-title { font-size: 12px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: #0a2463;
             border-bottom: 2px solid #0a2463; padding: 22px 0 5px; margin: 6px 0 12px; }
</style>
"""


UNITS = ["%", "m bags"]


def _skey(k: str, unit: str = "%") -> str:
    """Session key of one input box. Percent and m-bags changes keep separate boxes, so switching does not reinterpret a number."""
    comm, item = k.split("|")
    if unit == "m bags":
        return f"sc_bc_{comm}" if item == "Consumption" else f"sc_b_{comm}_{item}"
    return f"sc_c_{comm}" if item == "Consumption" else f"sc_p_{comm}_{item}"


# ── the maths ──────────────────────────────────────────────────────────────────────────────────────────────
def apply_params(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """params["pct"] scales the inputs (percent), params["abs"] adds to them (m bags); both only in params["years"]."""
    pct, add, yrs = params.get("pct", {}), params.get("abs", {}), set(params.get("years", []))
    keys = [f"{c}|{it}" for c, it in zip(df["commodity"], df["item"])]
    on = np.array([y in yrs for y in df["year"]])
    f = np.where(on, [1 + pct.get(k, 0.0) / 100 for k in keys], 1.0)
    d = np.where(on, [add.get(k, 0.0) for k in keys], 0.0)
    out = df.copy()
    out["value"] = np.maximum(out["value"].to_numpy() * f + d, 0.0)
    return out


def run(df, meta, years, params):
    scen = apply_params(df, params)
    a, r = block(scen, meta, "Arabica", years), block(scen, meta, "Robusta", years)
    return a, r, global_block(a, r, years)


def _comms(scope):
    return list(ORIGINS) if scope == "Combined" else [scope]


def _pick(scope, a, r, g, arabica_row, robusta_row, global_row):
    return {"Arabica": a.loc[arabica_row], "Robusta": r.loc[robusta_row]}.get(scope, g.loc[global_row])


def su(scope, a, r, g):
    return _pick(scope, a, r, g, "S/U", "S/U", "Combined S/U")


def bal(scope, a, r, g):
    return _pick(scope, a, r, g, "Balance", "Balance", "Global Balance")


def stock(scope, a, r, g):
    return _pick(scope, a, r, g, "End Season Stock", "End Season Stock", "Combined End Season Stock")


def current_params(sel, scope, unit="%") -> dict:
    keep = tuple(f"{c}|" for c in _comms(scope))
    vals = {k: float(st.session_state.get(_skey(k, unit), 0.0)) for k in ALL_KEYS if k.startswith(keep)}
    vals = {k: v for k, v in vals.items() if abs(v) > 1e-9}
    return {"years": list(sel), ("pct" if unit == "%" else "abs"): vals}


def _reset():
    for unit in UNITS:
        for k in ALL_KEYS:
            st.session_state[_skey(k, unit)] = 0.0


# ── what-if ──────────────────────────────────────────────────────────────────────────────────────────────────
def whatif(df, meta, years):
    est = [y for y in years if snd.is_estimate(y)] or years[-1:]
    opts = years[-6:]
    st.session_state.setdefault("sc_years", est[:2])
    st.session_state.setdefault("sc_scope", "Combined")

    bar = st.columns([2.4, 1.5, 3.6, 1.1], vertical_alignment="bottom")
    scope = bar[0].radio("Commodity", SCOPES, horizontal=True, key="sc_scope")
    unit = bar[1].radio("Change in", UNITS, horizontal=True, key="sc_unit")
    sel = bar[2].multiselect("Apply to crop years", opts, key="sc_years")
    bar[3].button("Reset", key="sc_reset", on_click=_reset, width="stretch")
    if not sel:
        st.markdown("<div class='an-note'>Pick at least one crop year.</div>", unsafe_allow_html=True)
        return
    comms = _comms(scope)
    params = current_params(sel, scope, unit)
    base = run(df, meta, years, {})
    scen = run(df, meta, years, params)
    first = years.index(min(sel, key=ystart))
    ys, ly = years[first:], max(sel, key=ystart)

    # the result table (built first, shown next to the inputs)
    def cell(new, old, fmt):
        d = new - old
        cls = "" if abs(d) < 0.0005 else ("up" if d > 0 else "dn")
        dl = "" if abs(d) < 0.0005 else f"<span class='dl {cls}'>{('+' if d > 0 else '')}{fmt(d) if fmt is not fpct else format(d * 100, '.1f') + 'pp'}</span>"
        return f"<td>{fmt(new)}{dl}</td>"

    rows = []
    for comm, i in (("Arabica", 0), ("Robusta", 1)):
        if comm not in comms:
            continue
        b, s_ = base[i], scen[i]
        for label, key, f in (("Balance", "Balance", fnum), ("End season stock", "End Season Stock", fnum), ("S/U", "S/U", fpct)):
            rows.append(f"<tr class='{'bal' if key == 'Balance' else ''}'><td class='lbl'>{comm} {label.lower()}</td>"
                        + "".join(cell(s_.loc[key, y], b.loc[key, y], f) for y in ys) + "</tr>")
    if scope == "Combined":
        rows.append("<tr class='bal'><td class='lbl'>Global balance</td>" + "".join(cell(scen[2].loc["Global Balance", y], base[2].loc["Global Balance", y], fnum) for y in ys) + "</tr>")
        rows.append("<tr><td class='lbl'>Combined S/U</td>" + "".join(cell(scen[2].loc["Combined S/U", y], base[2].loc["Combined S/U", y], fpct) for y in ys) + "</tr>")
    head = "<tr><th class='y first'></th>" + "".join(f"<th class='y{' fc' if y in sel else ''}'>{y}</th>" for y in ys) + "</tr>"

    left, right = st.columns([1.25, 1], gap="small")
    with left, st.container(border=True):
        card(f"Change vs base, {unit}")
        for comm in comms:
            if len(comms) > 1:
                st.markdown(f"<div class='sb-label' style='color:#64748b!important;margin:8px 0 2px'>{comm}</div>", unsafe_allow_html=True)
            items = ORIGINS[comm] + ["Consumption"]
            for row in range(0, len(items), 4):
                cols = st.columns(4, gap="small")
                for col, it in zip(cols, items[row:row + 4]):
                    key = _skey(f"{comm}|{it}", unit)
                    st.session_state.setdefault(key, 0.0)
                    if unit == "m bags":                                 # absolute change in million bags
                        lim = 20.0 if it == "Consumption" else 30.0
                        col.number_input(it, min_value=-lim, max_value=lim, step=0.5, format="%.1f", key=key)
                    elif it == "Consumption":
                        col.number_input("Consumption", min_value=-10.0, max_value=10.0, step=0.5, format="%.1f", key=key)
                    else:
                        col.number_input(it, min_value=-50.0, max_value=50.0, step=1.0, format="%.0f", key=key)
    with right, st.container(border=True):
        card("Result")
        st.markdown(f"<div class='snd-wrap' style='width:100%;margin:4px 0 0'><table class='snd' style='width:100%'>{head}{''.join(rows)}</table></div>",
                    unsafe_allow_html=True)

    short = [y[2:] for y in years]                                   # the charts show every crop year
    c1, c2 = st.columns(2, gap="small")
    for col, (title, fn, k, color, fmt, key) in zip((c1, c2), (("Stocks to use, %", su, 100, NAVY, ".1f", "sc_bar_su"),
                                                              ("Balance, m bags", bal, 1, AMBER, ",.1f", "sc_bar_bal"))):
        with col, st.container(border=True):
            fig = go.Figure()
            fig.add_trace(go.Bar(x=short, y=(fn(scope, *base)[years] * k).values, name="Base", marker_color="#c3cbe0", marker_line_width=0))
            fig.add_trace(go.Bar(x=short, y=(fn(scope, *scen)[years] * k).values, name="Scenario", marker_color=color, marker_line_width=0,
                                 text=[f"{v:.1f}" for v in (fn(scope, *scen)[years] * k).values], textposition="outside", textfont=dict(size=8.5)))
            _fig(fig, height=260, fmt=fmt).update_layout(barmode="group", bargap=0.25, legend=dict(orientation="h", x=0, y=1.15, font=dict(size=10)))
            card(title)
            st.plotly_chart(fig, width="stretch", key=key)


# ── sensitivity ──────────────────────────────────────────────────────────────────────────────────────────────
def sensitivity(df, meta, years):
    scope = st.session_state.get("sc_scope", "Combined")
    comms = _comms(scope)
    options = [f"{c}|{it}" for c in comms for it in ORIGINS[c] + ["Consumption"]]
    label = (lambda k: k.replace("|", " · ")) if len(comms) > 1 else (lambda k: k.split("|")[1])
    default = "Robusta|Vietnam" if scope == "Robusta" else "Arabica|Brazil"
    if st.session_state.get("sn_origin") not in options:
        st.session_state["sn_origin"] = default
    cyears = years[-6:]
    cur = snd.current_crop_year()
    if st.session_state.get("sn_year") not in cyears:
        st.session_state["sn_year"] = cur if cur in cyears else cyears[-1]

    st.markdown("<div class='sec-title'>Sensitivity</div>", unsafe_allow_html=True)
    c = st.columns([2.2, 1.3, 1.5, 1.2, 1.2, 2.2], vertical_alignment="bottom")
    key = c[0].selectbox("Flex", options, format_func=label, key="sn_origin")
    year = c[1].selectbox("Crop year", cyears, key="sn_year")
    unit = c[2].radio("Step in", ["m bags", "%"], horizontal=True, key="sn_unit")
    step = c[3].number_input("Step", min_value=0.1, value=5.0 if unit == "m bags" else 10.0, step=0.5 if unit == "m bags" else 1.0,
                             format="%.1f", key=f"sn_step_{unit}")
    n = int(c[4].number_input("Steps each side", min_value=1, max_value=6, value=2, step=1, key="sn_n"))
    metric = c[5].radio("Show", ["S/U", "Balance", "End stock"], horizontal=True, key="sn_metric")

    comm, item = key.split("|")
    rows_ = (df["commodity"] == comm) & (df["item"] == item) & (df["year"] == year)
    base_v = float(df.loc[rows_, "value"].iloc[0])
    res = []
    for k in range(-n, n + 1):
        v = base_v + k * step if unit == "m bags" else base_v * (1 + k * step / 100)
        if v <= 0:
            continue
        scen = df.copy()
        scen.loc[rows_, "value"] = v
        res.append((k, v, run(scen, meta, years, {})))
    fn, scale, fmt = {"S/U": (su, 100, "{:.1f}%"), "Balance": (bal, 1, "{:+.1f}"), "End stock": (stock, 1, "{:.1f}")}[metric]

    def series(f, sc=1):
        return [float(f(scope, *frames)[year]) * sc for _k, _v, frames in res]

    def vlabel(v):
        return f"{v:.1f}m" if unit == "m bags" else f"{(v / base_v - 1) * 100:+.0f}%"

    left, right = st.columns([1.4, 1], gap="small")
    with left, st.container(border=True):
        ys_ = series(fn, scale)
        fig = go.Figure(go.Bar(x=[vlabel(v) for _k, v, _f in res], y=ys_, marker_color=[NAVY if k == 0 else "#c3cbe0" for k, _v, _f in res],
                               marker_line_width=0, text=[fmt.format(v) for v in ys_], textposition="outside", textfont=dict(size=10),
                               hovertemplate="%{x}: %{y:.1f}<extra></extra>"))
        _fig(fig, height=300, legend=False, fmt=".1f").update_layout(hovermode="closest", bargap=0.35, yaxis_ticksuffix="%" if metric == "S/U" else "")
        card(f"{label(key)} {year}: {metric}")
        st.plotly_chart(fig, width="stretch", key="sn_chart")
    with right:
        body = "".join(f"<tr class='{'b' if k == 0 else ''}'><td class='lbl'>{vlabel(v)}{' (ours)' if k == 0 else ''}</td><td>{(v - base_v):+.1f}</td>"
                       f"<td>{s:.1f}%</td><td>{b:+.1f}</td><td>{t:.1f}</td></tr>"
                       for (k, v, _f), s, b, t in zip(res, series(su, 100), series(bal), series(stock)))
        st.markdown("<div class='snd-wrap' style='margin-top:0'><table class='snd'><tr><th class='y first'>Value</th><th class='y'>vs ours</th>"
                    f"<th class='y'>S/U</th><th class='y'>Balance</th><th class='y'>End stock</th></tr>{body}</table></div>", unsafe_allow_html=True)


def page():
    """The Scenarios section."""
    st.markdown(snd.CSS + analytics.CSS + CSS, unsafe_allow_html=True)
    df, meta, _notes, years = snd.load()
    st.markdown("<div class='snd-head'><span class='t'>Scenarios</span></div>", unsafe_allow_html=True)
    whatif(df, meta, years)
    sensitivity(df, meta, years)
