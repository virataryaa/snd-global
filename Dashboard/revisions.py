"""Revisions: every change saved on the dashboard (Coffee SnD inputs and Brazil inputs), with its effect, read from the GitHub save history.

Each save is one commit whose message lists the cells changed ("Arabica Brazil 2026/27: 50 -> 55"), so the log needs no database of its own.
"""
import html
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
from snd import fnum, ystart

COFFEE_LINE = re.compile(r"^(Arabica|Robusta) (.+) (\d{4}/\d{2}): (.*) -> (.*)$")
BRAZIL_LINE = re.compile(r"^(.+) (\d{4}/\d{2}): (.*) -> (.*)$")
# effect of a Brazil input on Brazil's closing stock (+ builds stock, - draws it); the rest has no direct sign
BRAZIL_SIGN = {"Arabica production": 1, "Conillon production": 1, "Arabica exports": -1, "Green exports": -1, "Soluble exports": -1,
               "Arabica consumption": -1, "Conillon consumption": -1}


def _val(t):
    t = t.strip()
    return np.nan if t in ("", "-") else float(t)


REASON = re.compile(r"\| reason: (.*)$")


def _rows(dataset):
    """[(when, group, item, year, old, new, effect, reason)] for one dataset, newest first."""
    out = []
    if dataset == "Coffee SnD":
        path, head, rx = snd.CSV_PATH, "Coffee SnD |", COFFEE_LINE
    else:
        path, head, rx = brazil.INP_PATH, "Brazil SnD |", BRAZIL_LINE
    for ts, msg in gh.history(path):
        first, _, body = msg.partition("\n")
        if not first.startswith(head):
            continue
        why = REASON.search(first)
        why = why.group(1).strip() if why else ""
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
            out.append((pd.Timestamp(ts), comm, item, year, o, n, sign * (np.nan_to_num(n) - np.nan_to_num(o)), why))
    return pd.DataFrame(out, columns=["when", "group", "item", "year", "old", "new", "effect", "reason"])


PALETTE = ["#0a2463", "#3e5fa8", "#1f8a9c", "#b7791f", "#1f9d6f", "#c0392b", "#8a5fb0", "#7f9bd1", "#e2b768", "#94a3b8", "#0f172a", "#8fc7d0", "#c9a227", "#d9534f"]


def _revert(dataset, grp: pd.DataFrame):
    """Set every cell in one saved commit back to what it was before that save — as a new save, so the log keeps the full history."""
    when = grp["when"].iloc[0]
    reason = f"revert of {when:%d %b %Y %H:%M}"               # never embed the old reason: reverting a revert would chain forever
    if dataset == "Coffee SnD":
        changes = [(r.group, r.item, r.year, r.new, None if pd.isna(r.old) else float(r.old)) for r in grp.itertuples()]
        snd._save_inputs(changes, reason)
    else:
        changes = [(r.item, r.year, r.new, None if pd.isna(r.old) else float(r.old)) for r in grp.itertuples()]
        brazil._save(changes, reason)


def revision_lines(sub: pd.DataFrame, level: bool, with_commodity: bool):
    """One step line per origin / item: its estimate over time, from the first number to every saved revision.
    level=False plots the change against the first estimate, so origins of very different size sit on one axis."""
    fig = go.Figure()
    for i, ((group, item), p) in enumerate(sub.sort_values("when").groupby(["group", "item"], sort=True)):
        xs = [p["when"].iloc[0] - pd.Timedelta(seconds=1)] + list(p["when"])
        ys = [p["old"].iloc[0]] + list(p["new"])
        why = [""] + [r if r else "no reason given" for r in p["reason"]]
        xs, ys, why = xs + [sub["when"].max()], ys + [ys[-1]], why + [""]      # carry the line on to the latest revision of any origin
        if not level:
            ys = [v - ys[0] if pd.notna(v) and pd.notna(ys[0]) else np.nan for v in ys]
        name = f"{group[:1]}. {item}" if with_commodity else item
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", name=name, line=dict(color=PALETTE[i % len(PALETTE)], width=2, shape="hv"),
                                 marker=dict(size=6), connectgaps=True, customdata=why,
                                 hovertemplate=(f"{name}: %{{y:+.1f}}" if not level else f"{name}: %{{y:.1f}}") + "  %{customdata}<extra></extra>"))
    _fig(fig, height=420, fmt="+.1f" if not level else ",.1f").update_layout(
        hovermode="x unified", xaxis=dict(type="date", showgrid=False),
        legend=dict(orientation="h", x=0, y=1.12, font=dict(size=10)),
        yaxis=dict(title="m bags" if level else "m bags vs first estimate", zeroline=True, zerolinecolor="rgba(15,23,42,0.25)",
                   gridcolor="rgba(15,23,42,0.06)"))
    return fig


def render():
    st.markdown(snd.CSS + analytics.CSS + "<style>"
                ".undo-row { display: flex; align-items: center; gap: 10px; padding: 7px 2px; border-bottom: 1px solid rgba(0,0,0,.06); "
                "font-size: 12px; } .undo-dt { color: #94a3b8; font-size: 10.5px; white-space: nowrap; min-width: 110px; } "
                ".undo-items { color: #1d1d1f; } .undo-why { color: #94a3b8; font-style: italic; }</style>", unsafe_allow_html=True)
    st.markdown("<div class='snd-head'><span class='t'>Revisions</span><span class='s'></span></div>",
                unsafe_allow_html=True)
    dataset = st.radio("Dataset", ["Coffee SnD", "Brazil SnD"], horizontal=True, key="rv_set", label_visibility="collapsed")
    if not gh.enabled():
        st.markdown("<div class='an-note'>Add github_token in Secrets to see the revision log.</div>", unsafe_allow_html=True)
        return
    try:
        rv = _rows(dataset)
    except Exception as ex:
        st.markdown(f"<div class='an-note'>Not available: {ex}</div>", unsafe_allow_html=True)
        return
    if rv.empty:
        st.markdown("<div class='an-note'>No revisions saved yet.</div>", unsafe_allow_html=True)
        return
    with st.container(border=True):
        c1, c2, c3, _ = st.columns([1.2, 1.4, 2, 4], vertical_alignment="bottom")
        years = sorted(rv["year"].unique(), key=ystart)
        year = c1.selectbox("Crop year", years, index=len(years) - 1, key="rv_year")
        groups = ["All"] + sorted(rv["group"].unique()) if dataset == "Coffee SnD" else ["All"]
        group = c2.selectbox("Commodity", groups, key="rv_group") if len(groups) > 1 else "All"
        mode = c3.radio("Show", ["Change vs first estimate", "Level"], horizontal=True, key="rv_mode")
        sub = rv[rv["year"] == year]
        if group != "All":
            sub = sub[sub["group"] == group]
        card(f"How every estimate for {year} was revised", "each line is one origin or item · each point is a saved revision")
        st.plotly_chart(revision_lines(sub, mode == "Level", dataset == "Coffee SnD" and group == "All"), width="stretch", key="rv_lines")
    last = rv.sort_values("when", ascending=False).head(30)
    is_revert = last["reason"].str.startswith("revert of", na=False)
    real = last[~is_revert]                                    # the top table: actual edits only, no "revert of revert of ..." noise
    body = "".join(f"<tr><td class='lbl'>{r.when:%d %b %Y %H:%M}</td><td class='lbl'>{r.group} {r.item}</td><td>{r.year}</td>"
                   f"<td>{fnum(r.old)}</td><td>{fnum(r.new)}</td>"
                   f"<td class='{'neg' if pd.notna(r.effect) and r.effect < 0 else ''}'>{'' if pd.isna(r.effect) else format(r.effect, '+.1f')}</td>"
                   f"<td class='lbl' style='min-width:220px'>{html.escape(r.reason)}</td></tr>"
                   for r in real.itertuples())
    st.markdown("<div class='snd-bar'>Latest revisions</div><div class='snd-wrap' style='border-radius:0 0 8px 8px;margin-top:0'><table class='snd'>"
                "<tr><th class='y first'>When</th><th class='y first'>Item</th><th class='y'>Year</th><th class='y'>Was</th><th class='y'>Now</th>"
                f"<th class='y'>Effect</th><th class='y first'>Reason</th></tr>{body}</table></div>", unsafe_allow_html=True)

    groups = list(real.groupby("when", sort=False))              # actionable: undo one of the real edits above
    revert_groups = list(last[is_revert].groupby("when", sort=False))
    if revert_groups and gh.enabled():
        with st.expander(f"Revert log ({len(revert_groups)})", expanded=False):
            st.markdown("<div class='card-desc'>Every revert that's been saved, on its own, separate from the real edits above.</div>",
                        unsafe_allow_html=True)
            for ts, grp in revert_groups:
                items = ", ".join(f"{r.group + ' ' if r.group != 'Brazil' else ''}{r.item} {r.year}" for r in grp.itertuples())
                st.markdown(f"<div class='undo-row'><span class='undo-dt'>{ts:%d %b %Y, %H:%M}</span>"
                           f"<span class='undo-items'>{html.escape(items)}</span>"
                           f"<span class='undo-why'>{html.escape(grp['reason'].iloc[0])}</span></div>", unsafe_allow_html=True)
    if groups and gh.enabled():
        with st.expander(f"Undo a save ({len(groups)})", expanded=False):
            st.markdown("<div class='card-desc'>Sets that save's cells back to what they were before it — recorded as a new revision, "
                        "nothing above is erased.</div>", unsafe_allow_html=True)
            for ts, grp in groups:
                items = ", ".join(f"{r.group + ' ' if r.group != 'Brazil' else ''}{r.item} {r.year}" for r in grp.itertuples())
                why = grp["reason"].iloc[0]
                c1, c2 = st.columns([7, 1], vertical_alignment="center")
                c1.markdown(f"<div class='undo-row'><span class='undo-dt'>{ts:%d %b %Y, %H:%M}</span>"
                            f"<span class='undo-items'>{html.escape(items)}</span>"
                            + (f"<span class='undo-why'>{html.escape(why)}</span>" if why else "") + "</div>", unsafe_allow_html=True)
                if c2.button("Revert", key=f"rv_undo_{dataset}_{ts.value}", width="stretch"):
                    try:
                        with st.spinner("Reverting..."):
                            _revert(dataset, grp)
                    except Exception as ex:
                        st.error(f"Revert failed: {ex}")
                    else:
                        st.toast("Reverted.")
                        st.rerun()
