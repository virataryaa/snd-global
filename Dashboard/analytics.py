"""Analytics on the coffee SnD: balance bridge, stocks-to-use history, Arabica vs Robusta S/U spread against the arb, supply vs demand
growth, a what-if scenario, and the log of how our estimates were revised.

Everything is calculated from the same inputs as the SnD table (Database/coffee_snd.csv) plus the sheet's S/U history and arb block
(Database/coffee_su_history.csv).
"""
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ghstore as gh
import snd
from snd import (AMBER, AXIS, GREEN, GREY, INK, NAVY, ORIGINS, RED, TEAL, block, fnum, fpct, global_block, load, ystart)

SU_HIST = snd.ROOT / "Database" / "coffee_su_history.csv"
CSS = """
<style>
table.snd span.dl { font-size: 10.5px; margin-left: 6px; color: #94a3b8; }
table.snd span.dl.up { color: #1f9d6f; } table.snd span.dl.dn { color: #c0392b; }
.an-note { color: #64748b; font-size: 12.5px; margin: 2px 0 10px; }
</style>
"""
VIEWS = ["Balance bridge", "Stocks to use", "Growth", "Scenario", "Revisions"]


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
        st.markdown("<div class='an-note'>" + " · ".join(bits) + f" · median {med:.1%}, range {lo:.1%} to {hi:.1%}</div>", unsafe_allow_html=True)

    with right, st.container(border=True):
        spread = (su["Arabica"].reindex(xs) - su["Robusta"].reindex(xs)).dropna() * 100
        arb = hist.set_index("year")["arb_avg"].reindex(xs)
        fig = go.Figure()
        fcs = _forecast_start()
        cols = [("rgba(10,36,99,0.35)" if ystart(y) >= fcs else NAVY) for y in spread.index]
        fig.add_trace(go.Bar(x=list(spread.index), y=spread.values, name="Arabica S/U minus Robusta S/U (pp)", marker_color=cols, marker_line_width=0))
        fig.add_trace(go.Scatter(x=xs, y=arb.values, name="Arb, Jul-Jun average (right)", mode="lines+markers", yaxis="y2",
                                 line=dict(color=AMBER, width=2.2), marker=dict(size=5), connectgaps=False))
        _fig(fig, height=360, fmt=",.1f").update_layout(
            yaxis=dict(title="pp", gridcolor="rgba(15,23,42,0.06)", color=AXIS, zeroline=True, zerolinecolor="rgba(15,23,42,0.18)"),
            yaxis2=dict(overlaying="y", side="right", showgrid=False, color=AXIS, title="arb"),
            xaxis=dict(type="category", tickangle=-45, tickfont=dict(size=9.5)))
        card("Arabica minus Robusta S/U against the arb", "S/U gap in percentage points (bars) and the arb (line)")
        st.plotly_chart(fig, width="stretch", key="an_su_spread")
        both = pd.concat([spread.rename("sp"), arb.rename("arb")], axis=1).dropna()
        if len(both) >= 5:
            st.markdown(f"<div class='an-note'>Correlation of the gap with the arb: {both['sp'].corr(both['arb']):+.2f} over {len(both)} years.</div>",
                        unsafe_allow_html=True)


# ── 7. Growth ───────────────────────────────────────────────────────────────────────────────────────────────
def view_growth(frames, glob, years, meta):
    scope = st.radio("Scope", ["Global", "Arabica", "Robusta"], horizontal=True, key="an_gr_scope")
    if scope == "Global":
        prod, cons, fs = glob.loc["Production Global"], glob.loc["Consumption Global"], _forecast_start(meta, "Arabica")
    else:
        prod, cons, fs = frames[scope].loc["Production"], frames[scope].loc["Consumption"], _forecast_start(meta, scope)
    gp, gc = prod.pct_change(fill_method=None) * 100, cons.pct_change(fill_method=None) * 100
    ys = years[1:]
    op = [0.45 if ystart(y) >= fs else 1 for y in ys]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=ys, y=gp[ys], name="Production growth", marker=dict(color=NAVY, opacity=op, line_width=0)))
    fig.add_trace(go.Bar(x=ys, y=gc[ys], name="Consumption growth", marker=dict(color=AMBER, opacity=op, line_width=0)))
    fig.add_trace(go.Scatter(x=ys, y=(gp - gc)[ys], name="Gap (production - consumption)", mode="lines+markers",
                             line=dict(color=TEAL, width=2), marker=dict(size=5)))
    _fig(fig, height=380, fmt=".1f").update_layout(barmode="group", yaxis_ticksuffix="%")
    with st.container(border=True):
        card(f"{scope} supply growth vs demand growth", "year on year, % · lighter bars = estimates · a positive gap builds stocks")
        st.plotly_chart(fig, width="stretch", key="an_growth")
        st.markdown(f"<div class='an-note'>Average since {ys[0]}: production {gp[ys].mean():+.1f}% a year, consumption {gc[ys].mean():+.1f}%.</div>",
                    unsafe_allow_html=True)


# ── 5. Scenario ─────────────────────────────────────────────────────────────────────────────────────────────
def _reset_scenario():
    for k in [k for k in st.session_state if str(k).startswith("sc_")]:
        if k != "sc_years":
            st.session_state[k] = 0.0


def view_scenario(df, meta, years):
    opts = years[-6:]
    sel = st.multiselect("Apply to crop years", opts, default=opts[-2:], key="sc_years")
    if not sel:
        st.markdown("<div class='an-note'>Pick at least one crop year.</div>", unsafe_allow_html=True)
        return
    with st.container(border=True):
        card("Change vs base, % · applied to every year picked above", "production by origin and consumption · the stock roll carries it forward")
        pct = {}
        for comm in ORIGINS:
            st.markdown(f"<div class='sb-label' style='color:#64748b!important;margin:6px 0 2px'>{comm}</div>", unsafe_allow_html=True)
            cols = st.columns(len(ORIGINS[comm]) + 1, gap="small")
            for col, o in zip(cols, ORIGINS[comm]):
                st.session_state.setdefault(f"sc_p_{comm}_{o}", 0.0)
                pct[(comm, o)] = col.number_input(o, min_value=-50.0, max_value=50.0, step=1.0, format="%.0f", key=f"sc_p_{comm}_{o}")
            st.session_state.setdefault(f"sc_c_{comm}", 0.0)
            pct[(comm, "Consumption")] = cols[-1].number_input("Consumption", min_value=-10.0, max_value=10.0, step=0.5, format="%.1f",
                                                               key=f"sc_c_{comm}")
        st.button("Reset", on_click=_reset_scenario, key="sc_reset")

    scen = df.copy()
    mult = [1 + pct.get((c, it), 0.0) / 100 if y in sel else 1.0 for c, it, y in zip(scen["commodity"], scen["item"], scen["year"])]
    scen["value"] = scen["value"] * np.array(mult)
    b = {c: block(df, meta, c, years) for c in ORIGINS}
    s = {c: block(scen, meta, c, years) for c in ORIGINS}
    gb, gs = global_block(b["Arabica"], b["Robusta"], years), global_block(s["Arabica"], s["Robusta"], years)
    first = years.index(min(sel, key=ystart))
    ys = years[first:]

    def cell(new, old, fmt, pos_good=True):
        d = new - old
        cls = "" if abs(d) < 0.0005 else ("up" if (d > 0) == pos_good else "dn")
        dl = "" if abs(d) < 0.0005 else f"<span class='dl {cls}'>{('+' if d > 0 else '')}{fmt(d) if fmt is not fpct else format(d * 100, '.1f') + 'pp'}</span>"
        return f"<td>{fmt(new)}{dl}</td>"

    rows = []
    for comm in ORIGINS:
        for label, key, f, pg in (("Balance", "Balance", fnum, True), ("End season stock", "End Season Stock", fnum, True),
                                  ("S/U", "S/U", fpct, True)):
            cls = "bal" if key == "Balance" else ""
            rows.append(f"<tr class='{cls}'><td class='lbl'>{comm} {label.lower()}</td>"
                        + "".join(cell(s[comm].loc[key, y], b[comm].loc[key, y], f, pg) for y in ys) + "</tr>")
    rows.append("<tr class='bal'><td class='lbl'>Global balance</td>" + "".join(cell(gs.loc["Global Balance", y], gb.loc["Global Balance", y], fnum) for y in ys) + "</tr>")
    rows.append("<tr><td class='lbl'>Combined S/U</td>" + "".join(cell(gs.loc["Combined S/U", y], gb.loc["Combined S/U", y], fpct) for y in ys) + "</tr>")
    head = "<tr><th class='y first'></th>" + "".join(f"<th class='y{' fc' if y in sel else ''}'>{y}</th>" for y in ys) + "</tr>"
    left, right = st.columns([1.3, 1], gap="small")
    with left:
        st.markdown("<div class='snd-bar'>Scenario result (change vs base in small type)</div>"
                    f"<div class='snd-wrap' style='border-radius:0 0 8px 8px;margin-top:0'><table class='snd'>{head}{''.join(rows)}</table></div>",
                    unsafe_allow_html=True)
    with right, st.container(border=True):
        fig = go.Figure()
        for nm, ser_b, ser_s, col in (("Arabica", b["Arabica"].loc["S/U"], s["Arabica"].loc["S/U"], NAVY),
                                      ("Robusta", b["Robusta"].loc["S/U"], s["Robusta"].loc["S/U"], AMBER),
                                      ("Combined", gb.loc["Combined S/U"], gs.loc["Combined S/U"], TEAL)):
            fig.add_trace(go.Scatter(x=ys, y=ser_b[ys], name=f"{nm} base", mode="lines", line=dict(color=col, width=1.6, dash="dot")))
            fig.add_trace(go.Scatter(x=ys, y=ser_s[ys], name=f"{nm} scenario", mode="lines+markers", line=dict(color=col, width=2.4), marker=dict(size=5)))
        _fig(fig, height=330, fmt=".1%").update_layout(yaxis_tickformat=".0%", legend=dict(orientation="h", x=0, y=1.25, font=dict(size=10)))
        card("Stocks to use, base vs scenario")
        st.plotly_chart(fig, width="stretch", key="sc_chart")


# ── 8. Revisions ────────────────────────────────────────────────────────────────────────────────────────────
REV = re.compile(r"^(Arabica|Robusta) (.+) (\d{4}/\d{2}): (.*) -> (.*)$")


def _val(t):
    t = t.strip()
    return np.nan if t in ("", "-") else float(t)


@st.cache_data(ttl=300, show_spinner=False)
def _revisions(_token_ok: bool) -> pd.DataFrame:
    rows = []
    for ts, msg in gh.history(snd.CSV_PATH):
        first, _, body = msg.partition("\n")
        if not first.startswith("Coffee SnD |"):
            continue
        for ln in body.splitlines():
            m = REV.match(ln.strip())
            if m:
                rows.append((pd.Timestamp(ts), m.group(1), m.group(2), m.group(3), _val(m.group(4)), _val(m.group(5))))
    return pd.DataFrame(rows, columns=["when", "commodity", "item", "year", "old", "new"])


def view_revisions(years, meta):
    if not gh.enabled():
        st.markdown("<div class='an-note'>The revision log is read from the GitHub save history. Add github_token in Secrets to see it.</div>", unsafe_allow_html=True)
        return
    try:
        rv = _revisions(True)
    except Exception as ex:
        st.markdown(f"<div class='an-note'>Not available: {ex}</div>", unsafe_allow_html=True)
        return
    if rv.empty:
        st.markdown("<div class='an-note'>No revisions saved yet. Every change saved on the Entry page or in Edit mode is logged here.</div>", unsafe_allow_html=True)
        return
    rv = rv.assign(delta=(rv["new"].fillna(0) - rv["old"].fillna(0)), cons=rv["item"] == "Consumption")
    rv["balance_effect"] = np.where(rv["cons"], -rv["delta"], rv["delta"])
    left, right = st.columns([1, 1], gap="small")
    with left, st.container(border=True):
        g = rv.groupby("year", as_index=False)["balance_effect"].sum().sort_values("year", key=lambda s: s.map(ystart))
        fig = go.Figure(go.Bar(x=g["year"], y=g["balance_effect"], marker_color=[GREEN if v >= 0 else RED for v in g["balance_effect"]],
                               marker_line_width=0, text=[f"{v:+.1f}" for v in g["balance_effect"]], textposition="outside"))
        _fig(fig, height=320, legend=False).update_layout(hovermode="closest")
        card("Net effect of our revisions on the balance", "m bags · production up or consumption down raises the balance")
        st.plotly_chart(fig, width="stretch", key="rv_net")
    with right, st.container(border=True):
        c1, c2, c3 = st.columns(3)
        comm = c1.selectbox("Commodity", list(ORIGINS), key="rv_comm")
        items = ORIGINS[comm] + ["Consumption"]
        item = c2.selectbox("Item", items, key="rv_item")
        sub = rv[(rv["commodity"] == comm) & (rv["item"] == item)]
        yrs = sorted(sub["year"].unique(), key=ystart) or years[-1:]
        year = c3.selectbox("Crop year", yrs, index=len(yrs) - 1, key="rv_year")
        p = sub[sub["year"] == year].sort_values("when")
        card(f"{comm} {item} {year}: path of the estimate", "each point is a saved revision")
        if p.empty:
            st.markdown("<div class='an-note'>No revisions for this one yet.</div>", unsafe_allow_html=True)
        else:
            xs = [p["when"].iloc[0] - pd.Timedelta(seconds=1)] + list(p["when"])
            ys = [p["old"].iloc[0]] + list(p["new"])
            fig = go.Figure(go.Scatter(x=xs, y=ys, mode="lines+markers", line=dict(color=NAVY, width=2.2, shape="hv"), marker=dict(size=7)))
            _fig(fig, height=250, legend=False).update_layout(hovermode="closest", xaxis=dict(type="date", color=AXIS, showgrid=False))
            st.plotly_chart(fig, width="stretch", key="rv_path")
    last = rv.sort_values("when", ascending=False).head(25)
    body = "".join(f"<tr><td class='lbl'>{r.when:%d %b %Y %H:%M}</td><td class='lbl'>{r.commodity} {r.item}</td><td>{r.year}</td>"
                   f"<td>{fnum(r.old)}</td><td>{fnum(r.new)}</td><td class='{'neg' if r.balance_effect < 0 else ''}'>{r.balance_effect:+.1f}</td></tr>"
                   for r in last.itertuples())
    st.markdown("<div class='snd-bar'>Latest revisions</div><div class='snd-wrap' style='border-radius:0 0 8px 8px;margin-top:0'><table class='snd'>"
                "<tr><th class='y first'>When</th><th class='y first'>Item</th><th class='y'>Year</th><th class='y'>Was</th><th class='y'>Now</th>"
                f"<th class='y'>Balance effect</th></tr>{body}</table></div>", unsafe_allow_html=True)


# ── Page ──────────────────────────────────────────────────────────────────────
def render():
    st.markdown(snd.CSS + CSS, unsafe_allow_html=True)
    df, meta, _notes, years = load()
    st.markdown("<div class='snd-head'><span class='t'>Coffee analytics</span><span class='s'>from the SnD inputs · m bags</span></div>", unsafe_allow_html=True)
    view = st.radio("View", VIEWS, horizontal=True, key="an_view", label_visibility="collapsed")
    frames = {c: block(df, meta, c, years) for c in ORIGINS}
    glob = global_block(frames["Arabica"], frames["Robusta"], years)
    if view == "Balance bridge":
        view_bridge(frames, years, meta)
    elif view == "Stocks to use":
        view_su(frames, years, meta)
    elif view == "Growth":
        view_growth(frames, glob, years, meta)
    elif view == "Scenario":
        view_scenario(df, meta, years)
    else:
        view_revisions(years, meta)
