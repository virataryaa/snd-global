"""Analytics on the coffee SnD: balance bridge, stocks-to-use history, Arabica vs Robusta S/U spread against the arb, supply vs demand
growth, a what-if scenario, and the log of how our estimates were revised.

Everything is calculated from the same inputs as the SnD table (Database/coffee_snd.csv) plus the sheet's S/U history and arb block
(Database/coffee_su_history.csv).
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import snd
from snd import AMBER, AXIS, GREEN, NAVY, ORIGINS, RED, TEAL, block, fnum, fpct, global_block, load, ystart

SU_HIST = snd.ROOT / "Database" / "coffee_su_history.csv"
CSS = """
<style>
table.snd span.dl { font-size: 10.5px; margin-left: 6px; color: #94a3b8; }
table.snd span.dl.up { color: #1f9d6f; } table.snd span.dl.dn { color: #c0392b; }
.an-note { color: #64748b; font-size: 12.5px; margin: 2px 0 10px; }
</style>
"""
VIEWS = ["Balance bridge", "Stocks to use", "Brazil crop cycle"]


@st.cache_data(ttl=600)
def load_su() -> pd.DataFrame:
    return pd.read_csv(SU_HIST)


def _fig(fig, height=360, fmt=",.1f", legend=True):
    snd._style(fig, height=height, fmt=fmt, legend=legend)
    fig.update_layout(margin=dict(t=8, b=30, l=10, r=10))
    return fig


def card(title, desc=""):
    st.markdown(f"<div class='chart-head'>{title}</div>" + (f"<div class='card-desc'>{desc}</div>" if desc else ""), unsafe_allow_html=True)


def _forecast_start(meta=None, comm=None):
    """First crop year that has not finished yet (set by today's date): estimates from here on."""
    return ystart(snd.current_crop_year())


# ── 1. Balance bridge ───────────────────────────────────────────────────────────────────────────────────────
def view_bridge(frames, years, meta):
    c1, c2, _ = st.columns([1.2, 1.4, 5], vertical_alignment="bottom")
    opts = years[1:]
    y = c1.selectbox("Crop year", opts, index=opts.index("2026/27") if "2026/27" in opts else len(opts) - 1, key="an_br_year")
    scope = c2.radio("Scope", ["Global", "Arabica", "Robusta"], horizontal=True, key="an_br_scope")
    prev = years[years.index(y) - 1]
    comms = ["Arabica", "Robusta"] if scope == "Global" else [scope]
    prod_steps, dem_steps = [], []
    for comm in comms:
        fr = frames[comm]
        for o in ORIGINS[comm]:
            d = float(fr.loc[o, y] - fr.loc[o, prev])
            prod_steps.append((f"{o} ({comm[0]})" if scope == "Global" else o, d))
        dem_steps.append((f"{comm} demand" if scope == "Global" else "Demand", -float(fr.loc["Consumption", y] - fr.loc["Consumption", prev])))
    start = sum(float(frames[c].loc["Balance", prev]) for c in comms)
    end = sum(float(frames[c].loc["Balance", y]) for c in comms)
    big = sorted([s for s in prod_steps if abs(s[1]) >= 0.05], key=lambda s: -abs(s[1]))
    small = sum(s[1] for s in prod_steps if abs(s[1]) < 0.05)
    steps = big + ([("Other (small)", small)] if abs(small) >= 0.005 else []) + dem_steps
    x = [f"Balance {prev}"] + [s[0] for s in steps] + [f"Balance {y}"]
    fig = go.Figure(go.Waterfall(
        x=x, y=[start] + [s[1] for s in steps] + [end], measure=["absolute"] + ["relative"] * len(steps) + ["total"],
        text=[f"{start:.1f}"] + [f"{s[1]:+.1f}" for s in steps] + [f"{end:.1f}"], textposition="outside", textfont=dict(size=11),
        increasing=dict(marker=dict(color=GREEN)), decreasing=dict(marker=dict(color=RED)), totals=dict(marker=dict(color=NAVY)),
        connector=dict(line=dict(color="rgba(15,23,42,.25)", width=1)), hovertemplate="%{x}: %{y:+.2f}<extra></extra>"))
    _fig(fig, height=400, legend=False).update_layout(hovermode="closest", yaxis_title="m bags")
    with st.container(border=True):
        card(f"{scope} balance bridge, {prev} to {y}",
             "m bags · green = adds to the balance (more supply or less demand), red = takes away")
        st.plotly_chart(fig, width="stretch", key="an_bridge")
        st.markdown(f"<div class='an-note'>Balance moves from {start:+.1f} to {end:+.1f} ({end - start:+.1f}): "
                    f"production {sum(s[1] for s in prod_steps):+.1f}, demand {sum(s[1] for s in dem_steps):+.1f}.</div>", unsafe_allow_html=True)


# ── 3 + 4. Stocks to use ────────────────────────────────────────────────────────────────────────────────────
def _su_series(comm, frames, years, hist):
    """S/U per crop year: the sheet's history before the first modelled year, the calculated S/U from then on."""
    col = "arabica_su" if comm == "Arabica" else "robusta_su"
    h = hist.set_index("year")[col].dropna()
    h = h[[y for y in h.index if ystart(y) < ystart(years[0])]]
    return pd.concat([h, frames[comm].loc["S/U", years]]).astype(float)


def view_su(frames, years, meta):
    hist = load_su()
    su = {c: _su_series(c, frames, years, hist) for c in ORIGINS}
    xs = sorted(set(su["Arabica"].index) | set(su["Robusta"].index), key=ystart)
    left, right = st.columns(2, gap="small")
    with left, st.container(border=True):
        comm = st.radio("Commodity", ["Arabica", "Robusta"], horizontal=True, key="an_su_comm", label_visibility="collapsed")
        s = su[comm].reindex(xs)
        fs = _forecast_start(meta, comm)
        actual = s[[y for y in s.index if ystart(y) < fs and pd.notna(s[y])]]
        lo, hi, q1, q3, med = actual.min(), actual.max(), actual.quantile(.25), actual.quantile(.75), actual.median()
        fig = go.Figure()
        for a, b, col, nm in [(hi, lo, "rgba(10,36,99,0.07)", "min-max"), (q3, q1, "rgba(10,36,99,0.14)", "25th-75th")]:
            fig.add_trace(go.Scatter(x=xs, y=[a] * len(xs), mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=xs, y=[b] * len(xs), mode="lines", line=dict(width=0), fill="tonexty", fillcolor=col, name=nm, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=xs, y=[med] * len(xs), mode="lines", line=dict(color=AXIS, width=1.2, dash="dot"), name="median", hoverinfo="skip"))
        a_idx = [y for y in xs if ystart(y) < fs]
        f_idx = [y for y in xs if ystart(y) >= fs]
        fig.add_trace(go.Scatter(x=a_idx, y=s.reindex(a_idx), mode="lines+markers", name="S/U", line=dict(color=NAVY, width=2.2),
                                 marker=dict(size=5), connectgaps=True))
        if f_idx:
            join = [a_idx[-1]] + f_idx if a_idx else f_idx
            fig.add_trace(go.Scatter(x=join, y=s.reindex(join), mode="lines+markers", name="estimate", line=dict(color=AMBER, width=2.2, dash="dot"),
                                     marker=dict(size=5)))
        _fig(fig, height=360, fmt=".1%").update_layout(yaxis_tickformat=".0%", xaxis=dict(type="category", tickangle=-45, tickfont=dict(size=9.5)))
        card(f"{comm} stocks to use vs history", f"{xs[0]} to {xs[-1]} · bands from {len(actual)} actual years")
        st.plotly_chart(fig, width="stretch", key="an_su_band")
        last = [y for y in f_idx if pd.notna(s[y])][:3] or [y for y in a_idx if pd.notna(s[y])][-1:]
        bits = [f"{y}: {s[y]:.1%} = {(actual < s[y]).mean():.0%} percentile" for y in last]
        st.markdown("<div class='an-note'>" + " · ".join(bits) + f" · median {med:.1%}, range {lo:.1%} to {hi:.1%}. "
                    f"Up to {hist['year'].iloc[hist['year'].map(ystart).lt(ystart(years[0])).sum() - 1]} the S/U comes from the sheet's history block, "
                    f"from {years[0]} on it is calculated from the inputs.</div>", unsafe_allow_html=True)

    with right, st.container(border=True):
        D = pd.DataFrame(index=xs)
        D["gap"] = (su["Arabica"].reindex(xs) - su["Robusta"].reindex(xs)) * 100
        D["arb"] = hist.set_index("year")["arb_avg"].reindex(xs)
        cur = ystart(snd.current_crop_year())
        actual_d = D[[ystart(y) < cur for y in D.index]]
        dx, dy = actual_d["gap"].diff(), actual_d["arb"].diff()
        fit = _fit(dx, dy)
        card("Does a widening Arabica-vs-Robusta S/U gap move the arb?", "each dot is a crop year with an arb number (the sheet has them to 2021/22)")
        if fit is None:
            st.markdown("<div class='an-note'>Not enough years with both numbers.</div>", unsafe_allow_html=True)
        else:
            lab = [y[2:] for y, a_, b_ in zip(actual_d.index, dx, dy) if np.isfinite(a_) and np.isfinite(b_)]
            st.plotly_chart(_scatter(fit, lab, "change in S/U gap, Arabica minus Robusta (pp)", "change in arb"), width="stretch", key="an_su_scatter")
            note = f"r = {fit['r']:+.2f} ({_strength(fit['r'])}), {fit['n']} years."
            nxt = D["gap"].diff()[[y for y in D.index if ystart(y) >= cur][:1]]
            if len(nxt) and np.isfinite(nxt.iloc[0]):
                note += f" {nxt.index[0]}: the gap moves {nxt.iloc[0]:+.1f}pp, which the fit maps to an arb move of {fit['slope'] * nxt.iloc[0]:+.0f} (indicative only)."
            st.markdown(f"<div class='an-note'>{note}</div>", unsafe_allow_html=True)


# ── Correlations ────────────────────────────────────────────────────────────────────────────────────────────
def _fit(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 4 or np.std(x) == 0:
        return None
    slope, icpt = np.polyfit(x, y, 1)
    r = float(np.corrcoef(x, y)[0, 1])
    return dict(slope=float(slope), icpt=float(icpt), r=r, n=len(x), x=x, y=y)


def _strength(r):
    a = abs(r)
    return "weak" if a < 0.3 else "moderate" if a < 0.6 else "strong"


def _scatter(fit, labels, xt, yt, height=360):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=fit["x"], y=fit["y"], mode="markers+text", text=labels, textposition="top center", textfont=dict(size=9, color=AXIS),
                             marker=dict(size=8, color=NAVY), hovertemplate="%{text}: %{x:.2f}, %{y:.2f}<extra></extra>"))
    xs = np.linspace(fit["x"].min(), fit["x"].max(), 20)
    fig.add_trace(go.Scatter(x=xs, y=fit["slope"] * xs + fit["icpt"], mode="lines", line=dict(color=AMBER, width=2, dash="dot"), hoverinfo="skip"))
    _fig(fig, height=height, legend=False).update_layout(hovermode="closest", xaxis=dict(title=xt, type="linear", showgrid=True, gridcolor="rgba(15,23,42,0.06)"),
                                                         yaxis=dict(title=yt, gridcolor="rgba(15,23,42,0.06)"))
    return fig


def view_cycle(frames, years, meta):
    """Brazil Arabica on/off years: growth this year against growth the year before."""
    import brazil
    cur = ystart(snd.current_crop_year())
    inp, bmeta, _agri, byears = brazil.load()
    ea, er = brazil.etg_brazil(byears)
    prod = brazil.compute(inp, ea, er, byears, bmeta)[3]["Arabica production"]
    g = prod.pct_change(fill_method=None) * 100
    ys = [y for y in byears if ystart(y) < cur]
    fit = _fit(g.shift(1)[ys].values, g[ys].values)
    left, right = st.columns([1.4, 1], gap="small")
    with left, st.container(border=True):
        card("Brazil Arabica on and off years", "growth this year against growth the year before · a negative slope is the biennial cycle")
        if fit is None:
            st.markdown("<div class='an-note'>Not enough history.</div>", unsafe_allow_html=True)
            return
        lab = [y[2:] for y, a_, b_ in zip(ys, g.shift(1)[ys], g[ys]) if np.isfinite(a_) and np.isfinite(b_)]
        st.plotly_chart(_scatter(fit, lab, "growth the year before (%)", "growth this year (%)", height=380), width="stretch", key="an_cycle")
    with right, st.container(border=True):
        last = ys[-1]
        nxt = [y for y in byears if ystart(y) >= cur][:1]
        card("What the cycle says now", f"slope {fit['slope']:+.2f}, r = {fit['r']:+.2f} ({_strength(fit['r'])}), {fit['n']} years")
        if nxt and np.isfinite(g[last]):
            implied_g = fit["slope"] * g[last] + fit["icpt"]
            implied = prod[last] * (1 + implied_g / 100)
            rows = [(f"{last} actual", prod[last], g[last]), (f"{nxt[0]}: cycle-implied", implied, implied_g), (f"{nxt[0]}: our estimate", prod[nxt[0]], g[nxt[0]])]
            body = "".join(f"<tr class='{'b' if 'our' in lab_ else ''}'><td class='lbl'>{lab_}</td><td>{p:.1f}</td><td>{gr:+.0f}%</td></tr>" for lab_, p, gr in rows)
            st.markdown("<div class='snd-wrap'><table class='snd'><tr><th class='y first'></th><th class='y'>m bags</th><th class='y'>growth</th></tr>"
                        f"{body}</table></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='an-note'>After a {g[last]:+.0f}% year the pattern points to about {implied:.1f}m bags for {nxt[0]}; we have {prod[nxt[0]]:.1f}m "
                        f"({prod[nxt[0]] - implied:+.1f}m above the cycle). Frost and drought can override it; treat it as a check on the number, not a forecast.</div>", unsafe_allow_html=True)


# ── Page ──────────────────────────────────────────────────────────────────────
def render():
    st.markdown(snd.CSS + CSS, unsafe_allow_html=True)
    df, meta, _notes, years = load()
    st.markdown("<div class='snd-head'><span class='t'>Analysis</span><span class='s'>from the SnD inputs · m bags</span></div>", unsafe_allow_html=True)
    view = st.radio("View", VIEWS, horizontal=True, key="an_view", label_visibility="collapsed")
    frames = {c: block(df, meta, c, years) for c in ORIGINS}
    glob = global_block(frames["Arabica"], frames["Robusta"], years)
    if view == "Balance bridge":
        view_bridge(frames, years, meta)
    elif view == "Stocks to use":
        view_su(frames, years, meta)
    else:
        view_cycle(frames, years, meta)
