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
    """A chart title. The description argument is accepted but not shown: the charts speak for themselves."""
    st.markdown(f"<div class='chart-head'>{title}</div>", unsafe_allow_html=True)


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
        connector=dict(line=dict(color="rgba(15,23,42,.25)", width=1)), hovertemplate="%{x}: %{y:+.1f}<extra></extra>"))
    _fig(fig, height=400, legend=False).update_layout(hovermode="closest", yaxis_title="m bags")
    with st.container(border=True):
        card(f"{scope} balance bridge, {prev} to {y}",
             "m bags · green = adds to the balance (more supply or less demand), red = takes away")
        st.plotly_chart(fig, width="stretch", key="an_bridge")


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
    with st.container(border=True):
        comm = st.radio("Commodity", ["Arabica", "Robusta"], horizontal=True, key="an_su_comm", label_visibility="collapsed")
        s = su[comm].reindex(xs)
        fs = _forecast_start(meta, comm)
        actual = s[[y for y in s.index if ystart(y) < fs and pd.notna(s[y])]]
        lo, hi, q1, q3, med = actual.min(), actual.max(), actual.quantile(.25), actual.quantile(.75), actual.median()
        fig = go.Figure()
        for a_, b_, col, nm in [(hi, lo, "rgba(10,36,99,0.07)", "min-max"), (q3, q1, "rgba(10,36,99,0.14)", "25th-75th")]:
            fig.add_trace(go.Scatter(x=xs, y=[a_] * len(xs), mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=xs, y=[b_] * len(xs), mode="lines", line=dict(width=0), fill="tonexty", fillcolor=col, name=nm, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=xs, y=[med] * len(xs), mode="lines", line=dict(color=AXIS, width=1.2, dash="dot"), name="median", hoverinfo="skip"))
        a_idx = [y for y in xs if ystart(y) < fs]
        f_idx = [y for y in xs if ystart(y) >= fs]
        fig.add_trace(go.Scatter(x=a_idx, y=s.reindex(a_idx), mode="lines+markers", name="S/U", line=dict(color=NAVY, width=2.2),
                                 marker=dict(size=5), connectgaps=True))
        if f_idx:
            join = [a_idx[-1]] + f_idx if a_idx else f_idx
            fig.add_trace(go.Scatter(x=join, y=s.reindex(join), mode="lines+markers", name="estimate", line=dict(color=AMBER, width=2.2, dash="dot"),
                                     marker=dict(size=5)))
        _fig(fig, height=430, fmt=".1%").update_layout(yaxis_tickformat=".0%", xaxis=dict(type="category", tickangle=-45, tickfont=dict(size=9.5)))
        card(f"{comm} stocks to use vs history")
        st.plotly_chart(fig, width="stretch", key="an_su_band")


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
                             marker=dict(size=8, color=NAVY), hovertemplate="%{text}: %{x:.1f}, %{y:.1f}<extra></extra>"))
    xs = np.linspace(fit["x"].min(), fit["x"].max(), 20)
    fig.add_trace(go.Scatter(x=xs, y=fit["slope"] * xs + fit["icpt"], mode="lines", line=dict(color=AMBER, width=2, dash="dot"), hoverinfo="skip"))
    _fig(fig, height=height, legend=False).update_layout(hovermode="closest", xaxis=dict(title=xt, type="linear", showgrid=True, gridcolor="rgba(15,23,42,0.06)"),
                                                         yaxis=dict(title=yt, gridcolor="rgba(15,23,42,0.06)"))
    return fig


def view_cycle(frames, years, meta):
    """Brazil Arabica: the on/off cycle, the crop by year, the stock position and where the crop goes."""
    import brazil
    cur = ystart(snd.current_crop_year())
    inp, bmeta, _agri, byears = brazil.load()
    ea, er = brazil.etg_brazil(byears)
    A, _C, _O, eff = brazil.compute(inp, ea, er, byears, bmeta)
    prod = eff["Arabica production"]
    g = prod.pct_change(fill_method=None) * 100
    ys = [y for y in byears if ystart(y) < cur]
    fit = _fit(g.shift(1)[ys].values, g[ys].values)
    short = [y[2:] for y in byears]
    est = [snd.is_estimate(y) for y in byears]

    top_l, top_r = st.columns(2, gap="small")
    with top_l, st.container(border=True):
        card("On and off years: growth this year vs the year before")
        if fit is None:
            st.markdown("<div class='an-note'>Not enough history.</div>", unsafe_allow_html=True)
        else:
            lab = [y[2:] for y, a_, b_ in zip(ys, g.shift(1)[ys], g[ys]) if np.isfinite(a_) and np.isfinite(b_)]
            st.plotly_chart(_scatter(fit, lab, "growth the year before (%)", "growth this year (%)", height=330), width="stretch", key="an_cycle")
    with top_r, st.container(border=True):
        up = (g.fillna(0) >= 0).tolist()                              # the first year has nothing to compare with: navy
        colors = [NAVY if u else AMBER for u in up]
        fig = go.Figure(go.Bar(x=short, y=prod.values, marker=dict(color=colors, opacity=[0.55 if e else 1 for e in est], line_width=0),
                               text=[f"{v:.1f}" for v in prod.values], textposition="outside", textfont=dict(size=9.5),
                               hovertemplate="%{x}: %{y:.1f}m bags<extra></extra>", name="Production"))
        nxt = [y for y in byears if ystart(y) >= cur][:1]
        if fit is not None and nxt and np.isfinite(g[ys[-1]]):
            implied = float(prod[ys[-1]] * (1 + (fit["slope"] * g[ys[-1]] + fit["icpt"]) / 100))
            fig.add_trace(go.Scatter(x=[nxt[0][2:]], y=[implied], mode="markers", name="cycle-implied", marker=dict(symbol="diamond", size=12, color=RED,
                                                                                                                  line=dict(color="#ffffff", width=1.5)),
                                     hovertemplate="cycle-implied: %{y:.1f}m bags<extra></extra>"))
        _fig(fig, height=330, fmt=".1f").update_layout(hovermode="closest", bargap=0.3)
        card("Crop by year: navy = grew, amber = fell")
        st.plotly_chart(fig, width="stretch", key="an_cycle_prod")

    bot_l, bot_r = st.columns(2, gap="small")
    with bot_l, st.container(border=True):
        fig = go.Figure()
        fig.add_trace(go.Bar(x=short, y=A.loc["Closing Stock"].values, name="Closing stock", marker=dict(color="#c3cbe0", opacity=[0.6 if e else 1 for e in est], line_width=0),
                             hovertemplate="%{x}: %{y:.1f}m bags<extra></extra>"))
        fig.add_trace(go.Scatter(x=short, y=(A.loc["Stock/Use Arabica"] * 100).values, name="S/U (right)", yaxis="y2", mode="lines+markers",
                                 line=dict(color=NAVY, width=2.2), marker=dict(size=5), hovertemplate="%{x}: %{y:.1f}%<extra></extra>"))
        _fig(fig, height=300, fmt=".1f").update_layout(hovermode="x unified", yaxis2=dict(overlaying="y", side="right", showgrid=False, color=AXIS, ticksuffix="%"))
        card("Brazil Arabica closing stock and stocks to use")
        st.plotly_chart(fig, width="stretch", key="an_cycle_stock")
    with bot_r, st.container(border=True):
        fig = go.Figure()
        for nm, col, ser in (("Exports", NAVY, A.loc["Exports"]), ("Consumption", TEAL, A.loc["Consumption"]), ("Stock change", AMBER, A.loc["Stock Change"])):
            fig.add_trace(go.Bar(x=short, y=ser.values, name=nm, marker=dict(color=col, line_width=0), hovertemplate=nm + ": %{y:.1f}<extra></extra>"))
        _fig(fig, height=300, fmt=".1f").update_layout(barmode="relative", bargap=0.3, hovermode="x unified")
        card("Where the crop goes, m bags")
        st.plotly_chart(fig, width="stretch", key="an_cycle_use")


# ── Page ──────────────────────────────────────────────────────────────────────
def render():
    st.markdown(snd.CSS + CSS, unsafe_allow_html=True)
    df, meta, _notes, years = load()
    st.markdown("<div class='snd-head'><span class='t'>Analysis</span></div>", unsafe_allow_html=True)
    view = st.radio("View", VIEWS, horizontal=True, key="an_view", label_visibility="collapsed")
    frames = {c: block(df, meta, c, years) for c in ORIGINS}
    glob = global_block(frames["Arabica"], frames["Robusta"], years)
    if view == "Balance bridge":
        view_bridge(frames, years, meta)
    elif view == "Stocks to use":
        view_su(frames, years, meta)
    else:
        view_cycle(frames, years, meta)
