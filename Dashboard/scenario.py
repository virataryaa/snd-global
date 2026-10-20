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
from snd import AMBER, GREEN, NAVY, ORIGINS, RED, block, global_block, ystart

PROD_KEYS = [f"{c}|{o}" for c in ORIGINS for o in ORIGINS[c]]
CONS_KEYS = [f"{c}|Consumption" for c in ORIGINS]
ALL_KEYS = PROD_KEYS + CONS_KEYS
SCOPES = ["Arabica", "Robusta", "Combined"]
SENS_SCOPES = ["Arabica", "Robusta"]                      # Sensitivity: no Combined, for now

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


def _origin_contrib(df, meta, years, scope, params, year):
    """One Balance waterfall bar per origin that's actually been changed, applied cumulatively, for one crop year."""
    unit_key = "pct" if "pct" in params else "abs"
    changed = params.get(unit_key, {})
    if not changed:
        return None
    base = run(df, meta, years, {})
    base_bal = float(bal(scope, *base)[year])
    order = [f"{c}|{it}" for c in ORIGINS for it in ORIGINS[c] + ["Consumption"] if f"{c}|{it}" in changed]
    multi = len({k.split("|")[0] for k in order}) > 1
    active, running, names, deltas = {}, base_bal, [], []
    for key in order:
        active[key] = changed[key]
        a, r, g = run(df, meta, years, {"years": [year], unit_key: dict(active)})
        new_bal = float(bal(scope, a, r, g)[year])
        comm, item = key.split("|")
        names.append(f"{comm} {_disp(item)}" if multi else _disp(item))
        deltas.append(new_bal - running)
        running = new_bal
    return base_bal, names, deltas, running


def _waterfall_fig(base_bal, names, deltas, running):
    xs, bases, h, colors, texts = ["Base"], [0.0], [base_bal], [NAVY], [f"{base_bal:+.1f}"]
    r_ = base_bal
    for name, d in zip(names, deltas):
        xs.append(name)
        bases.append(min(r_, r_ + d))
        h.append(abs(d))
        colors.append(GREEN if d >= 0 else RED)
        texts.append(f"{d:+.1f}")
        r_ += d
    xs.append("Scenario")
    bases.append(0.0)
    h.append(running)
    colors.append(NAVY)
    texts.append(f"{running:+.1f}")
    fig = go.Figure(go.Bar(x=xs, y=h, base=bases, marker_color=colors, marker_line_width=0,
                           text=texts, textposition="outside", textfont=dict(size=10),
                           hovertemplate="%{x}: %{text}<extra></extra>"))
    return _fig(fig, height=300, legend=False).update_layout(hovermode="closest", bargap=0.3)


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

    scope = st.radio("Commodity", SCOPES, horizontal=True, key="sc_scope", label_visibility="collapsed")
    if not sel:
        st.markdown("<div class='an-note'>Pick at least one crop year.</div>", unsafe_allow_html=True)
        return
    comms = _comms(scope)
    params = current_params(sel, scope, unit)
    base = run(df, meta, years, {})
    scen = run(df, meta, years, params)

    with st.container(border=True):
        card(f"Change vs base, {unit}")
        for comm in comms:
            if len(comms) > 1:
                st.markdown(f"<div class='sb-label' style='color:#64748b!important;margin:8px 0 2px'>{comm}</div>", unsafe_allow_html=True)
            items = ORIGINS[comm] + ["Consumption"]
            cols = st.columns(len(items), gap="small")
            for col, it in zip(cols, items):
                key = _skey(f"{comm}|{it}", unit)
                start = float(st.session_state.get(key) or 0.0)       # always an explicit number: without one the box shows its minimum
                if unit == "m bags":                                 # absolute change in million bags
                    lim = 20.0 if it == "Consumption" else 30.0
                    col.number_input(it, min_value=-lim, max_value=lim, value=start, step=0.5, format="%.1f", key=key)
                elif it == "Consumption":
                    col.number_input("Consumption", min_value=-10.0, max_value=10.0, value=start, step=0.5, format="%.1f", key=key)
                else:
                    col.number_input(it, min_value=-50.0, max_value=50.0, value=start, step=1.0, format="%.0f", key=key)

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

    ly = max(sel, key=ystart)
    wf = _origin_contrib(df, meta, years, scope, params, ly)
    if wf:
        with st.container(border=True):
            card(f"Balance waterfall at {ly}: base to scenario, by origin")
            st.plotly_chart(_waterfall_fig(*wf), width="stretch", key="wf_chart")


# ── sensitivity ──────────────────────────────────────────────────────────────────────────────────────────────
SOFT_RED, SOFT_MID, SOFT_GREEN = "#d79a93", "#f6f3ea", "#8fbfa3"


def _sensitivity_grid(df, meta, years, key, y_key, year, n, step, unit, progress=None):
    """The flexed item against the second item you picked to pair it with (any other origin or Consumption): every combination of the
    two, stepped in m bags or percent, with all three metrics read off the same model run (one run per cell, not one per metric)."""
    x_key = key
    x_label, y_label = _disp(x_key.split("|")[1]), _disp(y_key.split("|")[1])
    unit_label = "%" if unit == "%" else "Bags"

    def axis_title(k):
        comm, item = k.split("|")
        return f"{comm} Consumption Change ({unit_label})" if item == "Consumption" else f"{item} Crop Change ({unit_label})"

    x_axis, y_axis = axis_title(x_key), axis_title(y_key)
    scope = st.session_state.get("sc_scope", "Combined")

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
    dec = 0 if step == int(step) else 1                       # a 0.5 step rounded to whole numbers was showing duplicate "+0" labels
    labels = [f"{k * step:+.{dec}f}m" if unit == "m bags" else f"{k * step:+.{dec}f}%" for k in steps]
    z = {"S/U": [], "Balance": [], "End stock": []}
    total, done = len(steps) ** 2, 0
    for yk in steps:
        rows = {m: [] for m in z}
        for xk in steps:
            scen = df.copy()
            scen.loc[xr_mask, "value"] = stepped(xb, xk)
            scen.loc[yr_mask, "value"] = stepped(yb, yk)
            a, r, g = run(scen, meta, years, {})
            rows["S/U"].append(float(su(scope, a, r, g)[year]) * 100)
            rows["Balance"].append(float(bal(scope, a, r, g)[year]))
            rows["End stock"].append(float(stock(scope, a, r, g)[year]))
            done += 1
            if progress is not None:
                progress.progress(done / total, text=f"Running the sensitivity grid... {done}/{total}")
        for m in z:
            z[m].append(rows[m])
    return {"z": z, "labels": labels, "x_label": x_label, "y_label": y_label, "x_axis": x_axis, "y_axis": y_axis}


def _heatmap_fig(z, labels, x_axis, y_axis, metric, big=False):
    """A coloured grid: green/red shading by cell, same convention as the bars did (Balance diverges at zero; S/U and End stock compare
    to the base case, the middle cell, since they have no natural zero)."""
    fmt = {"S/U": "{:.1f}", "Balance": "{:+.1f}", "End stock": "{:.1f}"}[metric]
    n = (len(labels) - 1) // 2                              # the middle label is the base case, no change on either axis
    last = len(labels) - 1
    ref = 0.0 if metric == "Balance" else z[n][n]
    zdev = [[v - ref for v in row] for row in z]

    sz = 13 if big else 10
    fig = go.Figure(go.Heatmap(z=zdev, x=labels, y=labels, zmid=0, colorscale=[[0, SOFT_RED], [0.5, SOFT_MID], [1, SOFT_GREEN]],
                               showscale=False, xgap=2, ygap=2,
                               text=[[fmt.format(v) for v in row] for row in z], texttemplate="%{text}", textfont=dict(size=sz, color="#000000"),
                               customdata=z, hovertemplate=f"{x_axis} %{{x}}, {y_axis} %{{y}}: %{{customdata:.1f}}<extra></extra>"))
    for x0, x1, y0, y1 in [(n - 0.5, n + 0.5, -0.5, last + 0.5), (-0.5, last + 0.5, n - 0.5, n + 0.5)]:
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, line=dict(color="#000000", width=1.5),
                      fillcolor="rgba(0,0,0,0)", layer="above")
    fig.update_layout(template="plotly_white", height=480 if big else 325, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      margin=dict(t=4, b=34, l=60, r=6), font=dict(color="#1d1d1f", size=sz + 1),
                      xaxis=dict(title=dict(text=x_axis, font=dict(color="#0a2463")), type="category",
                                 tickfont=dict(size=sz), constrain="domain", showline=True, linewidth=1, linecolor="rgba(0,0,0,.15)", mirror=True),
                      yaxis=dict(title=dict(text=y_axis, font=dict(color="#0a2463")), type="category",
                                 tickfont=dict(size=sz), constrain="domain", scaleanchor="x", scaleratio=1,
                                 showline=True, linewidth=1, linecolor="rgba(0,0,0,.15)", mirror=True))
    return fig


def _disp(item):
    return "Overall Consumption" if item == "Consumption" else item


def sensitivity(df, meta, years):
    st.session_state.setdefault("sc_scope", "Arabica")
    scope = st.session_state.get("sc_scope", "Arabica")
    if scope not in SENS_SCOPES:                           # e.g. left over as "Combined" from Scenarios
        scope = st.session_state["sc_scope"] = "Arabica"
    comms = _comms(scope)
    options = [f"{c}|{it}" for c in comms for it in ORIGINS[c] + ["Consumption"]]
    label = (lambda k: f"{k.split('|')[0]} · {_disp(k.split('|')[1])}") if len(comms) > 1 else (lambda k: _disp(k.split("|")[1]))
    default = "Robusta|Vietnam" if scope == "Robusta" else "Arabica|Brazil"
    if st.session_state.get("sn_origin") not in options:
        st.session_state["sn_origin"] = default
    cyears = years[-6:]
    if st.session_state.get("sn_yr") not in cyears:
        st.session_state["sn_yr"] = cyears[-1]            # latest crop year by default

    with st.container(border=True, key="sn_controls"):
        st.radio("Commodity", SENS_SCOPES, horizontal=True, key="sc_scope", label_visibility="collapsed")
        c = st.columns([0.8, 0.8, 0.85, 1.0, 1.0, 0.75, 0.75], gap="small", vertical_alignment="bottom")
        unit = c[0].radio("Step in", ["%", "m bags"], horizontal=True, key="sn_unit")
        skey = f"sn_step_{unit}"
        step = c[1].number_input("Step (Mn)" if unit == "m bags" else "Step (%)", min_value=0.1,
                                 value=float(st.session_state.get(skey) or (5.0 if unit == "m bags" else 1.0)),
                                 step=0.5 if unit == "m bags" else 1.0, format="%.1f", key=skey) or (5.0 if unit == "m bags" else 1.0)
        n = int(c[2].number_input("Steps each side", min_value=1, max_value=8, value=int(st.session_state.get("sn_n") or 5), step=1, key="sn_n") or 5)
        key = c[3].selectbox("Flex", options, format_func=label, key="sn_origin")
        comm, item = key.split("|")
        vs_options = [o for o in options if o != key]                 # every other origin or Consumption, to pair against Flex
        vs_default = f"{comm}|{ORIGINS[comm][0]}" if item == "Consumption" else f"{comm}|Consumption"
        if vs_default not in vs_options:
            vs_default = vs_options[0]
        if st.session_state.get("sn_vs") not in vs_options:
            st.session_state["sn_vs"] = vs_default
        y_key = c[4].selectbox("vs", vs_options, format_func=label, key="sn_vs")
        year = c[5].selectbox("Crop year", cyears, key="sn_yr")
        compute = c[6].button("Compute", key="sn_compute", type="primary", width="stretch")

    sig = (key, y_key, year, n, step, unit, scope)
    if compute:
        prog = st.progress(0.0, text="Running the sensitivity grid...")
        st.session_state["sn_result"] = {"sig": sig, **_sensitivity_grid(df, meta, years, key, y_key, year, n, step, unit, progress=prog)}
        prog.empty()

    result = st.session_state.get("sn_result")
    if not result or result["sig"] != sig:
        st.markdown("<div class='an-note'>Pick Flex, Crop year, Step and Steps each side, then press Compute &mdash; it's a heavy grid, so it "
                    "only runs on demand.</div>", unsafe_allow_html=True)
        return
    z, labels, x_label, y_label = result["z"], result["labels"], result["x_label"], result["y_label"]
    x_axis, y_axis = result["x_axis"], result["y_axis"]

    def heat_title(text):
        st.markdown(f"<div class='chart-head' style='text-align:center'>{text}</div>", unsafe_allow_html=True)

    for metric, title, key_sfx in (("Balance", "balance (deficit / surplus)", "bal"), ("End stock", "End stock", "stock"), ("S/U", "S/U", "su")):
        with st.container(border=True):
            heat_title(f"{x_label} vs {y_label}: {title} at {year}")
            st.plotly_chart(_heatmap_fig(z[metric], labels, x_axis, y_axis, metric, big=True), width="stretch", key=f"sn_heat_{key_sfx}")


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
