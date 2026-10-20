"""Scenarios: two tools on one page, picked from a sidebar Tool switch.

1. What-if: change production by origin or consumption (percent or m bags), for the crop years you pick, and read the balance and stocks.
2. Sensitivity: flex one origin (or consumption) in one crop year by a step size you choose and see what stocks-to-use, the balance or the
   end stock do, plus a heatmap of that origin against its commodity's consumption. Nothing here is saved or changes the data.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analytics
import snd
from analytics import _fig, card
from snd import AMBER, GREEN, NAVY, ORIGINS, RED, block, fnum, fpct, global_block, ystart

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
    vals = {k: float(st.session_state.get(_skey(k, unit)) or 0.0) for k in ALL_KEYS if k.startswith(keep)}
    vals = {k: v for k, v in vals.items() if abs(v) > 1e-9}
    return {"years": list(sel), ("pct" if unit == "%" else "abs"): vals}


def _reset():
    for unit in UNITS:
        for k in ALL_KEYS:
            st.session_state[_skey(k, unit)] = 0.0


def _chart_years(years, show_all):
    """Last 3 actual years plus every upcoming (estimate) year, unless 'All' is picked."""
    if show_all:
        return years
    actual = [y for y in years if not snd.is_estimate(y)]
    est = [y for y in years if snd.is_estimate(y)]
    return actual[-3:] + est


# ── what-if ──────────────────────────────────────────────────────────────────────────────────────────────────
def whatif(df, meta, years):
    est = [y for y in years if snd.is_estimate(y)] or years[-1:]
    opts = years[-6:]
    st.session_state.setdefault("sc_years", est[:2])
    st.session_state.setdefault("sc_scope", "Combined")

    with st.sidebar:
        st.markdown("<div class='sb-label'>Change in</div>", unsafe_allow_html=True)
        unit = st.radio("Change in", UNITS, horizontal=True, key="sc_unit", label_visibility="collapsed")
        st.markdown("<div class='sb-label'>Apply to crop years</div>", unsafe_allow_html=True)
        sel = st.multiselect("Apply to crop years", opts, key="sc_years", label_visibility="collapsed")
        st.button("Reset", key="sc_reset", on_click=_reset, width="stretch")

    scope = st.radio("Commodity", SCOPES, horizontal=True, key="sc_scope")
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
                    start = float(st.session_state.get(key) or 0.0)       # always an explicit number: without one the box shows its minimum
                    if unit == "m bags":                                 # absolute change in million bags
                        lim = 20.0 if it == "Consumption" else 30.0
                        col.number_input(it, min_value=-lim, max_value=lim, value=start, step=0.5, format="%.1f", key=key)
                    elif it == "Consumption":
                        col.number_input("Consumption", min_value=-10.0, max_value=10.0, value=start, step=0.5, format="%.1f", key=key)
                    else:
                        col.number_input(it, min_value=-50.0, max_value=50.0, value=start, step=1.0, format="%.0f", key=key)
    with right, st.container(border=True):
        card("Result")
        st.markdown(f"<div class='snd-wrap' style='width:100%;margin:4px 0 0'><table class='snd' style='width:100%'>{head}{''.join(rows)}</table></div>",
                    unsafe_allow_html=True)

    span_l, span_r = st.columns([5, 1], vertical_alignment="center")
    span_r.radio("Range", ["Recent", "All"], horizontal=True, key="sc_bar_span", label_visibility="collapsed")
    chart_years = _chart_years(years, st.session_state.get("sc_bar_span") == "All")
    short = [y[2:] for y in chart_years]
    for title, fn, k, color, fmt, key in (("Balance, m bags", bal, 1, AMBER, ",.1f", "sc_bar_bal"),
                                           ("Stocks to use, %", su, 100, NAVY, ".1f", "sc_bar_su")):
        with st.container(border=True):
            bv = (fn(scope, *base)[chart_years] * k).values
            sv = (fn(scope, *scen)[chart_years] * k).values
            fig = go.Figure()
            fig.add_trace(go.Bar(x=short, y=bv, name="Base", marker_color="#c3cbe0", marker_line_width=0,
                                 text=[f"{v:.1f}" for v in bv], textposition="outside", textfont=dict(size=8.5)))
            fig.add_trace(go.Bar(x=short, y=sv, name="Scenario", marker_color=color, marker_line_width=0,
                                 text=[f"{v:.1f}" for v in sv], textposition="outside", textfont=dict(size=8.5)))
            _fig(fig, height=230, fmt=fmt).update_layout(barmode="group", bargap=0.3, legend=dict(orientation="h", x=0, y=1.15, font=dict(size=10)))
            card(title)
            st.plotly_chart(fig, width="stretch", key=key)


# ── sensitivity ──────────────────────────────────────────────────────────────────────────────────────────────
SOFT_RED, SOFT_MID, SOFT_GREEN = "#d79a93", "#f6f3ea", "#8fbfa3"


@st.cache_data(ttl=600, show_spinner="Computing sensitivity grid...")
def sensitivity_heatmap(df, meta, years, key, year, n, step, unit, metric):
    """A grid of the flexed item against its commodity's consumption (or, if Consumption was flexed, against its largest origin):
    every combination of the two, stepped the same way as the bar chart above (m bags or percent), with the given metric in each cell."""
    comm, item = key.split("|")
    if item == "Consumption":
        x_key, y_key = key, f"{comm}|{ORIGINS[comm][0]}"
    else:
        x_key, y_key = key, f"{comm}|Consumption"
    x_label, y_label = x_key.split("|")[1], y_key.split("|")[1]
    scope = st.session_state.get("sc_scope", "Combined")
    fn, scale, fmt = {"S/U": (su, 100, "{:.1f}"), "Balance": (bal, 1, "{:+.1f}"), "End stock": (stock, 1, "{:.1f}")}[metric]

    def base_val(k):
        c, it = k.split("|")
        rows_ = (df["commodity"] == c) & (df["item"] == it) & (df["year"] == year)
        return float(df.loc[rows_, "value"].iloc[0])

    def stepped(base, k):
        return max(base + k * step, 0.0) if unit == "m bags" else max(base * (1 + k * step / 100), 0.0)

    xb, yb = base_val(x_key), base_val(y_key)
    xr_mask = (df["commodity"] == x_key.split("|")[0]) & (df["item"] == x_key.split("|")[1]) & (df["year"] == year)
    yr_mask = (df["commodity"] == y_key.split("|")[0]) & (df["item"] == y_key.split("|")[1]) & (df["year"] == year)
    steps = list(range(-n, n + 1))
    labels = [f"{k * step:+.0f}m" if unit == "m bags" else f"{k * step:+.0f}%" for k in steps]
    z = []
    for yk in steps:
        row = []
        for xk in steps:
            scen = df.copy()
            scen.loc[xr_mask, "value"] = stepped(xb, xk)
            scen.loc[yr_mask, "value"] = stepped(yb, yk)
            a, r, g = run(scen, meta, years, {})
            row.append(float(fn(scope, a, r, g)[year]) * scale)
        z.append(row)
    if metric == "Balance":                               # deficit vs surplus: red below zero, green above it
        hm_kw = dict(colorscale=[[0, SOFT_RED], [0.5, SOFT_MID], [1, SOFT_GREEN]], zmid=0)
    else:                                                  # S/U, End stock: one shade, low to high, no colour at the low end
        hm_kw = dict(colorscale=[[0, "#ffffff"], [1, "#a9cfb8"]])
    fig = go.Figure(go.Heatmap(z=z, x=labels, y=labels, **hm_kw,
                               xgap=2, ygap=2,
                               text=[[fmt.format(v) for v in row] for row in z], texttemplate="%{text}", textfont=dict(size=8.5, color="#3a3a3c"),
                               hovertemplate=f"{x_label} %{{x}}, {y_label} %{{y}}: %{{z:.1f}}<extra></extra>",
                               colorbar=dict(thickness=7, tickfont=dict(size=8), outlinewidth=0)))
    zero = n                                                # steps.index(0): the base case, no change on either axis
    last = len(steps) - 1
    for x0, x1, y0, y1 in [(zero - 0.5, zero + 0.5, -0.5, last + 0.5), (-0.5, last + 0.5, zero - 0.5, zero + 0.5)]:
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, line=dict(color="rgba(100,116,139,.55)", width=1.25),
                      fillcolor="rgba(0,0,0,0)", layer="above")
    fig.update_layout(template="plotly_white", height=260, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      margin=dict(t=4, b=28, l=50, r=6), font=dict(color="#1d1d1f", size=9.5),
                      xaxis=dict(title=f"{x_label} change", type="category", tickfont=dict(size=8.5), constrain="domain",
                                 showline=True, linewidth=1, linecolor="rgba(0,0,0,.15)", mirror=True),
                      yaxis=dict(title=f"{y_label} change", type="category", tickfont=dict(size=8.5), constrain="domain",
                                 scaleanchor="x", scaleratio=1,
                                 showline=True, linewidth=1, linecolor="rgba(0,0,0,.15)", mirror=True))
    return fig, x_label, y_label


def sensitivity(df, meta, years):
    st.session_state.setdefault("sc_scope", "Combined")
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

    with st.sidebar:
        st.markdown("<div class='sb-sep'></div>", unsafe_allow_html=True)
        st.markdown("<div class='sb-label'>Commodity</div>", unsafe_allow_html=True)
        st.radio("Commodity", SCOPES, horizontal=True, key="sc_scope", label_visibility="collapsed")
        st.markdown("<div class='sb-label'>Flex</div>", unsafe_allow_html=True)
        key = st.selectbox("Flex", options, format_func=label, key="sn_origin", label_visibility="collapsed")
        st.markdown("<div class='sb-label'>Crop year</div>", unsafe_allow_html=True)
        year = st.selectbox("Crop year", cyears, key="sn_year", label_visibility="collapsed")

    c = st.columns([1.3, 1.2, 1.4], gap="small", vertical_alignment="bottom")
    unit = c[0].radio("Step in", ["m bags", "%"], horizontal=True, key="sn_unit")
    skey = f"sn_step_{unit}"
    step = c[1].number_input("Step value (in Mn)" if unit == "m bags" else "Step value (%)", min_value=0.1,
                             value=float(st.session_state.get(skey) or (5.0 if unit == "m bags" else 10.0)),
                             step=0.5 if unit == "m bags" else 1.0, format="%.1f", key=skey) or (5.0 if unit == "m bags" else 10.0)
    n = int(c[2].number_input("Steps each side", min_value=1, max_value=8, value=int(st.session_state.get("sn_n") or 5), step=1, key="sn_n") or 5)

    h1, h2, h3 = st.columns(3, gap="small")
    for col, metric, key_sfx in ((h1, "S/U", "su"), (h2, "Balance", "bal"), (h3, "End stock", "stock")):
        with col, st.container(border=True):
            fig, x_label, y_label = sensitivity_heatmap(df, meta, years, key, year, n, step, unit, metric)
            card(f"{x_label} vs {y_label}: {'balance (deficit / surplus)' if metric == 'Balance' else metric} at {year}")
            st.plotly_chart(fig, width="stretch", key=f"sn_heat_{key_sfx}")


def page():
    """The Scenarios section: What-if."""
    st.markdown(snd.CSS + analytics.CSS + CSS, unsafe_allow_html=True)
    df, meta, _notes, years = snd.load()
    st.markdown("<div class='snd-head'><span class='t'>Scenarios</span></div>", unsafe_allow_html=True)
    whatif(df, meta, years)


def sensitivity_page():
    """The Sensitivity section, beneath Scenarios in the sidebar."""
    st.markdown(snd.CSS + analytics.CSS + CSS, unsafe_allow_html=True)
    df, meta, _notes, years = snd.load()
    st.markdown("<div class='snd-head'><span class='t'>Sensitivity</span></div>", unsafe_allow_html=True)
    sensitivity(df, meta, years)
