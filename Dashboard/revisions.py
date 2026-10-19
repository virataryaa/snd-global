"""Revisions: every change saved on the dashboard (Coffee SnD inputs and Brazil inputs), with its effect, read from the GitHub save history.

Each save is one commit whose message lists the cells changed ("Arabica Brazil 2026/27: 50 -> 55"), so the log needs no database of its own.
"""
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analytics
import brazil
import ghstore as gh
import snd
from analytics import _fig, card
from snd import GREEN, NAVY, RED, fnum, ystart

COFFEE_LINE = re.compile(r"^(Arabica|Robusta) (.+) (\d{4}/\d{2}): (.*) -> (.*)$")
BRAZIL_LINE = re.compile(r"^(.+) (\d{4}/\d{2}): (.*) -> (.*)$")
# effect of a Brazil input on Brazil's closing stock (+ builds stock, - draws it); the rest has no direct sign
BRAZIL_SIGN = {"Arabica production": 1, "Conillon production": 1, "Arabica exports": -1, "Green exports": -1, "Soluble exports": -1,
               "Arabica consumption": -1, "Conillon consumption": -1}


def _val(t):
    t = t.strip()
    return np.nan if t in ("", "-") else float(t)


def _rows(dataset):
    """[(when, group, item, year, old, new, effect)] for one dataset, newest first."""
    out = []
    if dataset == "Coffee SnD":
        path, head, rx = snd.CSV_PATH, "Coffee SnD |", COFFEE_LINE
    else:
        path, head, rx = brazil.INP_PATH, "Brazil SnD |", BRAZIL_LINE
    for ts, msg in gh.history(path):
        first, _, body = msg.partition("\n")
        if not first.startswith(head):
            continue
        for ln in body.splitlines():
            m = rx.match(ln.strip())
            if not m:
                continue
            if dataset == "Coffee SnD":
                comm, item, year, old, new = m.groups()
                sign = -1 if item == "Consumption" else 1
            else:
                comm, (item, year, old, new) = "Brazil", m.groups()
                sign = BRAZIL_SIGN.get(item, np.nan)
            o, n = _val(old), _val(new)
            out.append((pd.Timestamp(ts), comm, item, year, o, n, sign * (np.nan_to_num(n) - np.nan_to_num(o))))
    return pd.DataFrame(out, columns=["when", "group", "item", "year", "old", "new", "effect"])


def render():
    st.markdown(snd.CSS + analytics.CSS, unsafe_allow_html=True)
    st.markdown("<div class='snd-head'><span class='t'>Revisions</span><span class='s'>every saved change to the inputs, from the GitHub save log</span></div>",
                unsafe_allow_html=True)
    dataset = st.radio("Dataset", ["Coffee SnD", "Brazil SnD"], horizontal=True, key="rv_set", label_visibility="collapsed")
    if not gh.enabled():
        st.markdown("<div class='an-note'>The revision log is read from the GitHub save history. Add github_token in Secrets to see it.</div>", unsafe_allow_html=True)
        return
    try:
        rv = _rows(dataset)
    except Exception as ex:
        st.markdown(f"<div class='an-note'>Not available: {ex}</div>", unsafe_allow_html=True)
        return
    if rv.empty:
        st.markdown("<div class='an-note'>No revisions saved yet. Every change saved in Edit mode is logged here.</div>", unsafe_allow_html=True)
        return
    unit = "balance" if dataset == "Coffee SnD" else "Brazil closing stock"
    left, right = st.columns(2, gap="small")
    with left, st.container(border=True):
        g = rv.dropna(subset=["effect"]).groupby("year", as_index=False)["effect"].sum()
        g = g.sort_values("year", key=lambda s: s.map(ystart))
        fig = go.Figure(go.Bar(x=g["year"], y=g["effect"], marker_color=[GREEN if v >= 0 else RED for v in g["effect"]], marker_line_width=0,
                               text=[f"{v:+.1f}" for v in g["effect"]], textposition="outside"))
        _fig(fig, height=300, legend=False).update_layout(hovermode="closest")
        card(f"Net effect of our revisions on the {unit}", "m bags · by crop year · more supply or less use raises it")
        st.plotly_chart(fig, width="stretch", key="rv_net")
    with right, st.container(border=True):
        c1, c2, c3 = st.columns(3)
        groups = sorted(rv["group"].unique())
        group = c1.selectbox("Commodity" if dataset == "Coffee SnD" else "Set", groups, key="rv_group")
        sub = rv[rv["group"] == group]
        item = c2.selectbox("Item", sorted(sub["item"].unique()), key="rv_item")
        sub = sub[sub["item"] == item]
        years = sorted(sub["year"].unique(), key=ystart)
        year = c3.selectbox("Crop year", years, index=len(years) - 1, key="rv_year")
        p = sub[sub["year"] == year].sort_values("when")
        card(f"{group} {item} {year}: path of the estimate", "each point is a saved revision")
        xs = [p["when"].iloc[0] - pd.Timedelta(seconds=1)] + list(p["when"])
        ys = [p["old"].iloc[0]] + list(p["new"])
        fig = go.Figure(go.Scatter(x=xs, y=ys, mode="lines+markers", line=dict(color=NAVY, width=2.2, shape="hv"), marker=dict(size=7)))
        _fig(fig, height=220, legend=False).update_layout(hovermode="closest", xaxis=dict(type="date", showgrid=False))
        st.plotly_chart(fig, width="stretch", key="rv_path")
    last = rv.sort_values("when", ascending=False).head(30)
    body = "".join(f"<tr><td class='lbl'>{r.when:%d %b %Y %H:%M}</td><td class='lbl'>{r.group} {r.item}</td><td>{r.year}</td>"
                   f"<td>{fnum(r.old)}</td><td>{fnum(r.new)}</td>"
                   f"<td class='{'neg' if pd.notna(r.effect) and r.effect < 0 else ''}'>{'' if pd.isna(r.effect) else format(r.effect, '+.1f')}</td></tr>"
                   for r in last.itertuples())
    st.markdown("<div class='snd-bar'>Latest revisions</div><div class='snd-wrap' style='border-radius:0 0 8px 8px;margin-top:0'><table class='snd'>"
                "<tr><th class='y first'>When</th><th class='y first'>Item</th><th class='y'>Year</th><th class='y'>Was</th><th class='y'>Now</th>"
                f"<th class='y'>Effect</th></tr>{body}</table></div>", unsafe_allow_html=True)
