"""Cocoa visuals: Botanical vs Statistical comparison (on the SnD page), the Analysis section and the Scenarios section.
Same chart style and helpers as the coffee pages (snd._style / _bars / _line, analytics.card)."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import cocoa
import snd
from analytics import _fig, card
from snd import AMBER, GREEN, GREY, NAVY, RED, TEAL, fnum, fpct

ORIGIN_COLORS = ["#1f3b73", "#5b74a8", "#2a8c8c", "#c9973f", "#2e8b57", "#7b5ea7", "#8fa3cf", "#ddb86a", "#8a94a6"]


def _x(years):
    return [y[2:] for y in years]


def _est(years):
    return [cocoa.is_est(y) for y in years]


# ── Analysis ─────────────────────────────────────────────────────────────────────────────────────────────────
def analysis_page():
    st.markdown(snd.CSS, unsafe_allow_html=True)
    S, years = cocoa.load()
    left, right = st.columns([3, 1], vertical_alignment="center")
    left.markdown("<div class='snd-head'><span class='t'>Cocoa analysis</span></div>", unsafe_allow_html=True)
    with right.container(key="co_basis_nav"):
        basis = st.radio("Basis", ["Botanical", "Statistical"], horizontal=True, key="co_an_basis", label_visibility="collapsed")
    T = cocoa.balance(S, years, basis)
    x, est = _x(years), _est(years)

    cells = snd._grid([("Supply &amp; demand", "", 3), ("Balance &amp; stocks", "", 3)])
    with cells[0], st.container(border=True):
        card("Supply vs grind")
        fig = go.Figure()
        snd._bars(fig, x, T.loc["Total"], "Supply (origins × 0.99)", NAVY, est)
        snd._line(fig, x, T.loc["Grind"], "Grind", AMBER)
        st.plotly_chart(_fig(fig, height=260, fmt=",.0f"), width="stretch", key="co_an_supply")
    with cells[3], st.container(border=True):
        card("SnD balance")
        fig = go.Figure(go.Bar(x=x, y=T.loc["SnD"], name="SnD", hovertemplate="SnD: %{y:,.0f}<extra></extra>",
                               marker=dict(color=[GREEN if v >= 0 else RED for v in T.loc["SnD"].fillna(0)],
                                           opacity=[1 for e in est], line_width=0)))
        st.plotly_chart(_fig(fig, height=260, fmt=",.0f", legend=False), width="stretch", key="co_an_snd")

    with cells[4], st.container(border=True):
        card("Stock proxy and stock / grind")
        fig = go.Figure()
        snd._bars(fig, x, T.loc["Stock proxy"], "Stock", TEAL, est)
        snd._line(fig, x, T.loc["STU"] * 100, "STU %", NAVY, right=True, pct=True)
        st.plotly_chart(snd._y2(_fig(fig, height=260, fmt=",.0f")), width="stretch", key="co_an_stock")
    with cells[1], st.container(border=True):
        card("Origin mix")
        fig = go.Figure()
        names = [("IC Total", "Ivory Coast"), ("GH Total", "Ghana")] + list(cocoa.OTHERS)
        for (key, name), col in zip(names, ORIGIN_COLORS):
            fig.add_trace(go.Bar(x=x, y=T.loc[key], name=name, marker=dict(color=col, line_width=0),
                                 hovertemplate=name + ": %{y:,.0f}<extra></extra>"))
        st.plotly_chart(_fig(fig, height=260, fmt=",.0f").update_layout(barmode="stack"), width="stretch", key="co_an_mix")

    with cells[2], st.container(border=True):
        card("Ivory Coast and Ghana: main vs mid crop")
        fig = go.Figure()
        for key, name, col in (("IC Main", "IC main", NAVY), ("IC Mid", "IC mid", "#6f86bd"), ("GH Main", "GH main", AMBER), ("GH Mid", "GH mid", "#e0bd75")):
            fig.add_trace(go.Bar(x=x, y=T.loc[key], name=name, marker=dict(color=col, line_width=0),
                                 offsetgroup="IC" if key.startswith("IC") else "GH", hovertemplate=name + ": %{y:,.0f}<extra></extra>"))
        st.plotly_chart(_fig(fig, height=260, fmt=",.0f").update_layout(barmode="stack"), width="stretch", key="co_an_mainmid")
    with cells[5], st.container(border=True):
        card("Share of grind")
        fig = go.Figure()
        snd._line(fig, x, T.loc["IVC/GH share"] * 100, "IVC + GH", NAVY, pct=True)
        snd._line(fig, x, T.loc["Main %"] * 100, "Main crops", TEAL, pct=True)
        st.plotly_chart(_fig(fig, height=260, fmt=",.1f").update_layout(yaxis=dict(ticksuffix="%")), width="stretch", key="co_an_share")


# ── Scenarios ────────────────────────────────────────────────────────────────────────────────────────────────
LEVERS = {"Ivory Coast crop": ["IC Main Tree", "IC Mid Tree"], "Ghana crop": ["GH Main Tree", "GH Mid Tree"],
          "Other origins": [c for c, _ in cocoa.OTHERS], "Grind": ["Grind"]}


def scenario_page():
    st.markdown(snd.CSS, unsafe_allow_html=True)
    S, years = cocoa.load()
    left, right = st.columns([3, 1], vertical_alignment="center")
    left.markdown("<div class='snd-head'><span class='t'>Cocoa scenarios</span></div>", unsafe_allow_html=True)
    with right.container(key="co_basis_nav"):
        basis = st.radio("Basis", ["Botanical", "Statistical"], horizontal=True, key="co_sc_basis", label_visibility="collapsed")
    with st.container(border=True):
        default = [y for y in years if cocoa.is_est(y)] or years[-1:]
        apply_to = st.multiselect("Apply to crop years", years, default=default, format_func=lambda y: y[2:], key="co_sc_years")
        cols = st.columns(len(LEVERS))
        chg = {k: cols[i].number_input(f"{k} (k t)", min_value=-3000.0, max_value=3000.0, value=0.0, step=10.0, format="%.0f",
                                       key=f"co_sc_{i}") for i, k in enumerate(LEVERS)}
        if st.button("Reset", key="co_sc_reset"):
            for i in range(len(LEVERS)):
                st.session_state[f"co_sc_{i}"] = 0.0
            st.rerun()
    S2 = S.copy()
    for lever, series in LEVERS.items():                       # a k-tonne change, spread over the lever's parts by their size
        series = [s for s in series if s in S2.index]
        for y in apply_to:
            parts = S2.loc[series, y].fillna(0)
            tot = parts.sum()
            share = parts / tot if tot else pd.Series(1 / len(series), index=series)
            S2.loc[series, y] = parts + chg[lever] * share
    B0, B1 = cocoa.balance(S, years, basis), cocoa.balance(S2, years, basis)
    x, est = _x(years), _est(years)

    r = st.columns(2, gap="small")
    with r[0], st.container(border=True):
        card("SnD: base vs scenario")
        fig = go.Figure()
        snd._bars(fig, x, B0.loc["SnD"], "Base", GREY, est)
        snd._bars(fig, x, B1.loc["SnD"], "Scenario", NAVY, est)
        st.plotly_chart(_fig(fig, height=300, fmt=",.0f").update_layout(barmode="group"), width="stretch", key="co_sc_snd")
    with r[1], st.container(border=True):
        card("Stock / grind: base vs scenario")
        fig = go.Figure()
        snd._line(fig, x, B0.loc["STU"] * 100, "Base", GREY, pct=True, dash="dot")
        snd._line(fig, x, B1.loc["STU"] * 100, "Scenario", NAVY, pct=True)
        st.plotly_chart(_fig(fig, height=300, fmt=",.1f").update_layout(yaxis=dict(ticksuffix="%")), width="stretch", key="co_sc_stu")

    rows = [("Total ×0.99", "Total", 0), ("Grind", "Grind", 0), ("SnD", "SnD", 0), ("Stock", "Stock proxy", 0), ("STU", "STU", "p1")]
    n = len(years) + 1
    head = (f"<tr class='comm'><th colspan='{n}'>Scenario vs base · {basis}<span class='crop'>k tonnes</span></th></tr>"
            "<tr><th class='y first'></th>" + "".join(f"<th class='y{' fc' if e else ''}'>{y}</th>" for y, e in zip(x, est)) + "</tr>")
    body = ""
    for lab, key, f in rows:
        fmt = (lambda v: fpct(v, 1)) if f == "p1" else (lambda v: fnum(v, 0))
        body += f"<tr class='b'><td class='lbl'>{lab} scenario</td>" + "".join(
            f"<td class='{'fc' if e else ''}'>{fmt(v)}</td>" for v, e in zip(B1.loc[key], est)) + "</tr>"
        d = B1.loc[key] - B0.loc[key]
        body += "<tr class='soft'><td class='lbl'>vs base</td>" + "".join(
            f"<td class='{'fc ' if e else ''}{'neg' if pd.notna(v) and v < -1e-9 else ''}'>"
            f"{(fpct(v, 1) if f == 'p1' else fnum(v, 0)) if pd.notna(v) and abs(v) > 1e-9 else '–'}</td>" for v, e in zip(d, est)) + "</tr>"
    st.markdown(f"<div class='snd-wrap'><table class='snd'>{head}{body}</table></div>", unsafe_allow_html=True)
    st.markdown("<div class='card-desc' style='margin-top:6px'>Changes are in k tonnes for each chosen year: a crop change is spread over "
                "main and mid (and other origins over their countries) by size; stock then rolls forward from there.</div>", unsafe_allow_html=True)
