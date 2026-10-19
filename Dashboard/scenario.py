"""Scenario manager: change production by origin or consumption, see the balance and stocks move, save named scenarios, compare them, and read
how sensitive stocks-to-use is to each origin.

A scenario is {"years": [...], "pct": {"Arabica|Brazil": -10.0, "Robusta|Consumption": 2.0}}: percent changes on the inputs of those crop years
(the stock roll carries them forward). Saved scenarios live in Database/scenarios.json (committed to GitHub when a token is set, otherwise kept
for the session only).
"""
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analytics
import ghstore as gh
import snd
from analytics import _fig, _fit, card
from snd import AMBER, AXIS, GREEN, NAVY, ORIGINS, RED, TEAL, block, fnum, fpct, global_block, ystart

SC_PATH = "Database/scenarios.json"
SC_FILE = snd.ROOT / "Database" / "scenarios.json"
PROD_KEYS = [f"{c}|{o}" for c in ORIGINS for o in ORIGINS[c]]
CONS_KEYS = [f"{c}|Consumption" for c in ORIGINS]
ALL_KEYS = PROD_KEYS + CONS_KEYS
COLORS = [NAVY, AMBER, TEAL, "#8a5fb0", "#94a3b8"]


def _skey(k: str) -> str:
    comm, item = k.split("|")
    return f"sc_c_{comm}" if item == "Consumption" else f"sc_p_{comm}_{item}"


# ── the maths ──────────────────────────────────────────────────────────────────────────────────────────────
def apply_params(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    pct, yrs = params.get("pct", {}), set(params.get("years", []))
    f = [1 + pct.get(f"{c}|{it}", 0.0) / 100 if y in yrs else 1.0 for c, it, y in zip(df["commodity"], df["item"], df["year"])]
    out = df.copy()
    out["value"] = out["value"].to_numpy() * np.array(f)
    return out


def run(df, meta, years, params):
    scen = apply_params(df, params)
    a, r = block(scen, meta, "Arabica", years), block(scen, meta, "Robusta", years)
    return a, r, global_block(a, r, years)


def metrics(df, meta, years, params, y) -> dict:
    a, r, g = run(df, meta, years, params)
    return {"Arabica S/U": a.loc["S/U", y], "Robusta S/U": r.loc["S/U", y], "Combined S/U": g.loc["Combined S/U", y],
            "Arabica balance": a.loc["Balance", y], "Robusta balance": r.loc["Balance", y], "Global balance": g.loc["Global Balance", y]}


# ── saved scenarios ───────────────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def _file_scenarios() -> dict:
    try:
        return json.loads(SC_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def scenarios() -> dict:
    d = dict(_file_scenarios())
    d.update(st.session_state.get("_sc_local", {}))
    return d


def _commit(mutate, msg):
    def apply(text):
        d = json.loads(text) if text.strip() else {}
        mutate(d)
        return json.dumps(d, indent=2) + "\n", None
    text, _ = gh.commit(SC_PATH, apply, msg)
    SC_FILE.write_text(text, encoding="utf-8", newline="")
    _file_scenarios.clear()


def save_scenario(name: str, params: dict):
    name = " ".join(name.split())[:60]
    entry = dict(params, saved=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"))
    if gh.enabled():
        _commit(lambda d: d.__setitem__(name, entry), f"Scenario | saved: {name}")
    else:
        st.session_state.setdefault("_sc_local", {})[name] = entry
    return name


def delete_scenario(name: str):
    st.session_state.get("_sc_local", {}).pop(name, None)
    if gh.enabled() and name in _file_scenarios():
        _commit(lambda d: d.pop(name, None), f"Scenario | deleted: {name}")


# ── presets and loading ─────────────────────────────────────────────────────────────────────────────────
def _zero():
    for k in ALL_KEYS:
        st.session_state[_skey(k)] = 0.0


def load_params(params: dict):
    _zero()
    for k, v in params.get("pct", {}).items():
        if k in ALL_KEYS:
            st.session_state[_skey(k)] = float(v)
    st.session_state["sc_years"] = list(params.get("years", []))


def current_params() -> dict:
    pct = {k: float(st.session_state.get(_skey(k), 0.0)) for k in ALL_KEYS}
    return {"years": list(st.session_state.get("sc_years", [])), "pct": {k: v for k, v in pct.items() if abs(v) > 1e-9}}


def cycle_pct(df, meta, years):
    """Brazil Arabica on/off-year cycle: the production this year implied by last year's growth (fit on the actual years), as a percent change
    against our own estimate. None when there is no estimate year or too little history."""
    import brazil
    cur = ystart(snd.current_crop_year())
    inp, bmeta, _agri, byears = brazil.load()
    ea, er = brazil.etg_brazil(byears)
    prod = brazil.compute(inp, ea, er, byears, bmeta)[3]["Arabica production"]
    g = prod.pct_change(fill_method=None) * 100
    ys = [y for y in byears if ystart(y) < cur]
    fit = _fit(g.shift(1)[ys].values, g[ys].values)
    nxt = [y for y in byears if ystart(y) >= cur][:1]
    if fit is None or not nxt or not np.isfinite(g[ys[-1]]):
        return None
    implied_growth = fit["slope"] * g[ys[-1]] + fit["icpt"]
    implied = prod[ys[-1]] * (1 + implied_growth / 100)
    return dict(year=nxt[0], implied=float(implied), ours=float(prod[nxt[0]]), pct=float((implied / prod[nxt[0]] - 1) * 100), r=fit["r"])


# ── page ──────────────────────────────────────────────────────────────────────────────────────────────────
def render(df, meta, years):
    est = [y for y in years if snd.is_estimate(y)] or years[-1:]
    opts = years[-6:]
    cyc = cycle_pct(df, meta, years)
    st.session_state.setdefault("sc_years", est[:2])

    # 1. presets, saved scenarios
    with st.container(border=True):
        card("Start from", "a preset or a saved scenario, then adjust below")
        presets = {"Base (reset)": dict(years=est[:2], pct={}),
                   "Brazil Arabica -10%": dict(years=est[:2], pct={"Arabica|Brazil": -10}),
                   "Brazil Arabica +10%": dict(years=est[:2], pct={"Arabica|Brazil": 10}),
                   "Demand +2%": dict(years=est[:2], pct={"Arabica|Consumption": 2, "Robusta|Consumption": 2}),
                   "Demand -2%": dict(years=est[:2], pct={"Arabica|Consumption": -2, "Robusta|Consumption": -2}),
                   "Vietnam -10%": dict(years=est[:2], pct={"Robusta|Vietnam": -10})}
        if cyc:
            presets = {f"Brazil at cycle crop ({cyc['implied']:.1f}m)":
                       dict(years=[cyc["year"]], pct={"Arabica|Brazil": round(cyc["pct"], 1)}), **presets}
        cols = st.columns(len(presets))
        for i, (label, spec) in enumerate(presets.items()):
            cols[i].button(label, key=f"sc_pre_{i}", on_click=load_params, args=(spec,), width="stretch")
        saved = scenarios()
        if saved:
            lc = st.columns([3, 1, 1, 5], vertical_alignment="bottom")
            pick = lc[0].selectbox("Saved scenarios", list(saved), key="sc_load_pick")
            lc[1].button("Load", key="sc_load", on_click=load_params, args=(saved[pick],), width="stretch")
            if lc[2].button("Delete", key="sc_del", width="stretch"):
                try:
                    delete_scenario(pick)
                except (gh.GitHubError, Exception) as ex:
                    st.error(f"Delete failed: {ex}")
                else:
                    st.rerun()

    # 2. the inputs
    sel = st.multiselect("Apply to crop years", opts, key="sc_years")
    if not sel:
        st.markdown("<div class='an-note'>Pick at least one crop year.</div>", unsafe_allow_html=True)
        return
    with st.container(border=True):
        card("Change vs base, %", "production by origin and consumption · applied to every year picked above · the stock roll carries it forward")
        for comm in ORIGINS:
            st.markdown(f"<div class='sb-label' style='color:#64748b!important;margin:6px 0 2px'>{comm}</div>", unsafe_allow_html=True)
            cols = st.columns(len(ORIGINS[comm]) + 1, gap="small")
            for col, o in zip(cols, ORIGINS[comm]):
                st.session_state.setdefault(_skey(f"{comm}|{o}"), 0.0)
                col.number_input(o, min_value=-50.0, max_value=50.0, step=1.0, format="%.0f", key=_skey(f"{comm}|{o}"))
            st.session_state.setdefault(_skey(f"{comm}|Consumption"), 0.0)
            cols[-1].number_input("Consumption", min_value=-10.0, max_value=10.0, step=0.5, format="%.1f", key=_skey(f"{comm}|Consumption"))
        sc = st.columns([3, 1, 6], vertical_alignment="bottom")
        name = sc[0].text_input("Name", key="sc_name", placeholder="Name this scenario to save it (e.g. Brazil 45m)", label_visibility="collapsed")
        if sc[1].button("Save", key="sc_save", disabled=not name.strip(), width="stretch"):
            try:
                saved_name = save_scenario(name, current_params())
            except (gh.GitHubError, Exception) as ex:
                st.error(f"Save failed: {ex}")
            else:
                st.session_state["en_flash"] = f"Saved scenario '{saved_name}'" + ("" if gh.enabled() else " for this session (add github_token to keep it)")
                st.rerun()

    params = current_params()
    base_a, base_r, base_g = run(df, meta, years, {})
    sc_a, sc_r, sc_g = run(df, meta, years, params)
    first = years.index(min(sel, key=ystart))
    ys = years[first:]

    # 3. result: the table and two bar charts
    def cell(new, old, fmt, pos_good=True):
        d = new - old
        cls = "" if abs(d) < 0.0005 else ("up" if (d > 0) == pos_good else "dn")
        dl = "" if abs(d) < 0.0005 else f"<span class='dl {cls}'>{('+' if d > 0 else '')}{fmt(d) if fmt is not fpct else format(d * 100, '.1f') + 'pp'}</span>"
        return f"<td>{fmt(new)}{dl}</td>"

    rows = []
    for comm, b, s in (("Arabica", base_a, sc_a), ("Robusta", base_r, sc_r)):
        for label, key, f in (("balance", "Balance", fnum), ("end season stock", "End Season Stock", fnum), ("S/U", "S/U", fpct)):
            rows.append(f"<tr class='{'bal' if key == 'Balance' else ''}'><td class='lbl'>{comm} {label}</td>"
                        + "".join(cell(s.loc[key, y], b.loc[key, y], f) for y in ys) + "</tr>")
    rows.append("<tr class='bal'><td class='lbl'>Global balance</td>" + "".join(cell(sc_g.loc["Global Balance", y], base_g.loc["Global Balance", y], fnum) for y in ys) + "</tr>")
    rows.append("<tr><td class='lbl'>Combined S/U</td>" + "".join(cell(sc_g.loc["Combined S/U", y], base_g.loc["Combined S/U", y], fpct) for y in ys) + "</tr>")
    head = "<tr><th class='y first'></th>" + "".join(f"<th class='y{' fc' if y in sel else ''}'>{y}</th>" for y in ys) + "</tr>"
    left, right = st.columns([0.85, 1.3], gap="small")
    with left:
        st.markdown("<div class='snd-bar'>Scenario result (change vs base in small type)</div>"
                    f"<div class='snd-wrap' style='border-radius:0 0 8px 8px;margin-top:0'><table class='snd'>{head}{''.join(rows)}</table></div>",
                    unsafe_allow_html=True)
    with right, st.container(border=True):
        short = [y[2:] for y in ys]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=short, y=(base_g.loc["Combined S/U", ys] * 100).values, name="Base", marker_color="#c3cbe0", marker_line_width=0))
        fig.add_trace(go.Bar(x=short, y=(sc_g.loc["Combined S/U", ys] * 100).values, name="Scenario", marker_color=NAVY, marker_line_width=0))
        _fig(fig, height=165, fmt=".1f").update_layout(barmode="group", margin=dict(t=2, b=22, l=8, r=8), yaxis_ticksuffix="%")
        card("Combined stocks to use", "% · base vs scenario")
        st.plotly_chart(fig, width="stretch", key="sc_bar_su")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=short, y=base_g.loc["Global Balance", ys].values, name="Base", marker_color="#c3cbe0", marker_line_width=0))
        fig.add_trace(go.Bar(x=short, y=sc_g.loc["Global Balance", ys].values, name="Scenario", marker_color=AMBER, marker_line_width=0))
        _fig(fig, height=165, fmt=",.1f").update_layout(barmode="group", margin=dict(t=2, b=22, l=8, r=8))
        card("Global balance", "m bags · base vs scenario")
        st.plotly_chart(fig, width="stretch", key="sc_bar_bal")

    # 4. compare saved scenarios
    compare_section(df, meta, years, saved, params, sel)

    # 5. sensitivity and tornado
    sensitivity_section(df, meta, years, sel, params)


def compare_section(df, meta, years, saved, params, sel):
    if not saved and not params["pct"]:
        return
    with st.container(border=True):
        card("Compare scenarios", "pick up to three saved scenarios · the current inputs can be included")
        c = st.columns([3, 1.4, 1.4, 4], vertical_alignment="bottom")
        picks = c[0].multiselect("Saved scenarios", list(saved), max_selections=3, key="sc_cmp", label_visibility="collapsed",
                                 placeholder="Choose saved scenarios to compare")
        cmp_years = years[-6:]
        default = snd.current_crop_year() if snd.current_crop_year() in cmp_years else cmp_years[-1]
        y = c[1].selectbox("Compare in", cmp_years, index=cmp_years.index(default), key="sc_cmp_year")
        incl = c[2].checkbox("Current inputs", value=bool(params["pct"]), key="sc_cmp_cur")
        sets = [("Base", {})] + ([("Current inputs", params)] if incl and params["pct"] else []) + [(p, saved[p]) for p in picks]
        if len(sets) < 2:
            st.markdown("<div class='an-note'>Pick a saved scenario (or include the current inputs) to compare with the base.</div>", unsafe_allow_html=True)
            return
        M = pd.DataFrame({name: metrics(df, meta, years, p, y) for name, p in sets})
        l, r = st.columns(2, gap="small")
        with l:
            fig = go.Figure()
            for i, name in enumerate(M.columns):
                v = M.loc[["Arabica S/U", "Robusta S/U", "Combined S/U"], name] * 100
                fig.add_trace(go.Bar(x=list(v.index), y=v.values, name=name, marker_color=COLORS[i % len(COLORS)], marker_line_width=0,
                                     text=[f"{x:.1f}%" for x in v.values], textposition="outside", textfont=dict(size=10)))
            _fig(fig, height=300, fmt=".1f").update_layout(barmode="group", yaxis_ticksuffix="%")
            st.markdown(f"<div class='chart-head'>Stocks to use in {y}</div>", unsafe_allow_html=True)
            st.plotly_chart(fig, width="stretch", key="sc_cmp_su")
        with r:
            fig = go.Figure()
            for i, name in enumerate(M.columns):
                v = M.loc[["Arabica balance", "Robusta balance", "Global balance"], name]
                fig.add_trace(go.Bar(x=["Arabica", "Robusta", "Global"], y=v.values, name=name, marker_color=COLORS[i % len(COLORS)], marker_line_width=0,
                                     text=[f"{x:+.1f}" for x in v.values], textposition="outside", textfont=dict(size=10)))
            _fig(fig, height=300, fmt=",.1f").update_layout(barmode="group")
            st.markdown(f"<div class='chart-head'>Balance in {y}, m bags</div>", unsafe_allow_html=True)
            st.plotly_chart(fig, width="stretch", key="sc_cmp_bal")
        for name, p in sets[1:]:
            ch = ", ".join(f"{k.replace('|', ' ')} {v:+g}%" for k, v in p.get("pct", {}).items()) or "no change"
            st.markdown(f"<div class='an-note'><b>{name}</b>: {ch} · years {', '.join(p.get('years', []))}</div>", unsafe_allow_html=True)


def sensitivity_section(df, meta, years, sel, params):
    last = max(sel, key=ystart)
    first = min(sel, key=ystart)
    left, right = st.columns(2, gap="small")
    with left, st.container(border=True):
        y = first
        base_v = float(df[(df["commodity"] == "Arabica") & (df["item"] == "Brazil") & (df["year"] == y)]["value"].iloc[0])
        grid = [round(base_v + d, 1) for d in (-10, -5, 0, 5, 10) if base_v + d > 0]
        rows = []
        for v in grid:
            scen = df.copy()
            scen.loc[(scen["commodity"] == "Arabica") & (scen["item"] == "Brazil") & (scen["year"] == y), "value"] = v
            a, r, g = run(scen, meta, years, {})
            rows.append((v, a.loc["S/U", y], g.loc["Combined S/U", y], g.loc["Global Balance", y]))
        S = pd.DataFrame(rows, columns=["crop", "asu", "csu", "bal"])
        fig = go.Figure(go.Bar(x=[f"{v:g}m" for v in S["crop"]], y=S["csu"] * 100, marker_color=[NAVY if abs(v - base_v) < 1e-9 else "#c3cbe0" for v in S["crop"]],
                               marker_line_width=0, text=[f"{x:.1f}%" for x in S["csu"] * 100], textposition="outside", textfont=dict(size=10)))
        _fig(fig, height=250, legend=False, fmt=".1f").update_layout(hovermode="closest", yaxis_ticksuffix="%")
        card(f"If the Brazil Arabica crop in {y} were different", f"combined stocks to use in {y} · dark bar = our estimate ({base_v:g}m) · everything else unchanged")
        st.plotly_chart(fig, width="stretch", key="sc_sens")
        body = "".join(f"<tr><td class='lbl'>{v:g}m{' (ours)' if abs(v - base_v) < 1e-9 else ''}</td><td>{fpct(a, 1)}</td><td>{fpct(c, 1)}</td><td>{fnum(b)}</td></tr>"
                       for v, a, c, b in S.itertuples(index=False))
        st.markdown("<div class='snd-wrap' style='margin-top:4px'><table class='snd'><tr><th class='y first'>Brazil Arabica</th><th class='y'>Arabica S/U</th>"
                    f"<th class='y'>Combined S/U</th><th class='y'>Global balance</th></tr>{body}</table></div>", unsafe_allow_html=True)
    with right, st.container(border=True):
        yrs = list(params.get("years") or sel)
        base_su = run(df, meta, years, {})[2].loc["Combined S/U", last] * 100
        bars = []
        for k in ALL_KEYS:
            shock = 2.0 if k.endswith("Consumption") else 10.0
            lo = run(df, meta, years, {"years": yrs, "pct": {k: -shock}})[2].loc["Combined S/U", last] * 100 - base_su
            hi = run(df, meta, years, {"years": yrs, "pct": {k: shock}})[2].loc["Combined S/U", last] * 100 - base_su
            bars.append((k.replace("|", " "), lo, hi, shock))
        bars.sort(key=lambda b: max(abs(b[1]), abs(b[2])))
        bars = bars[-10:]
        fig = go.Figure()
        fig.add_trace(go.Bar(y=[b[0] for b in bars], x=[b[1] for b in bars], orientation="h", name="production -10% (consumption -2%)",
                             marker_color=RED, marker_line_width=0))
        fig.add_trace(go.Bar(y=[b[0] for b in bars], x=[b[2] for b in bars], orientation="h", name="production +10% (consumption +2%)",
                             marker_color=NAVY, marker_line_width=0))
        _fig(fig, height=330, fmt="+.2f").update_layout(barmode="relative", hovermode="closest", xaxis=dict(title=f"change in combined S/U in {last}, pp", showgrid=True,
                                                                                                           gridcolor="rgba(15,23,42,0.06)", type="linear"),
                                                        yaxis=dict(type="category", showgrid=False), legend=dict(orientation="h", x=0, y=1.18, font=dict(size=10)))
        card("What moves stocks to use the most", f"each input shocked on its own, in {', '.join(y[2:] for y in yrs)} · the ten biggest")
        st.plotly_chart(fig, width="stretch", key="sc_tornado")


def page():
    """The Scenarios section."""
    st.markdown(snd.CSS + analytics.CSS, unsafe_allow_html=True)
    df, meta, _notes, years = snd.load()
    st.markdown("<div class='snd-head'><span class='t'>Scenarios</span><span class='s'>change an input, see the balance and stocks move · save, compare, stress-test</span></div>",
                unsafe_allow_html=True)
    if st.session_state.get("en_flash"):
        st.toast(st.session_state.pop("en_flash"))
    render(df, meta, years)
