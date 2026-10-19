"""Brazil internal SnD: Arabica, Conillon (Robusta) and overall Brazil, plus the AgriAcies-format tables.

Inputs live in Database/brazil_snd.csv (hard-coded cells of the Excel sheet); everything else is calculated the way the sheet does it:
  * production = the 'Coffee SnD ETG' Brazil number, unless this sheet has its own for the year,
  * consumption is typed up to 2020/21; after that it is (1 - Conillon demand %) or the Conillon demand % times the overall Brazil
    consumption (typed from 2020/21),
  * stock change = production - exports - consumption, closing stock = last year's closing stock + stock change (the first year's is typed).
"""
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import ghstore as gh
import snd
from snd import ROOT, fnum, fpct, ystart

INP, META, AGRI = ROOT / "Database" / "brazil_snd.csv", ROOT / "Database" / "brazil_meta.json", ROOT / "Database" / "brazil_agri.csv"
INP_PATH, META_PATH = "Database/brazil_snd.csv", "Database/brazil_meta.json"
SERIES = ["Arabica production", "Arabica exports", "Arabica consumption", "Conillon production", "Green exports",
          "Soluble exports", "Conillon consumption", "Conillon demand %", "Overall consumption"]
PCT_SERIES = {"Conillon demand %"}                                   # typed as a fraction, shown and edited as a percent
TZ = "Europe/Amsterdam"


# ── Data ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def load():
    inp = pd.read_csv(INP)
    meta = json.loads(META.read_text(encoding="utf-8"))
    agri = pd.read_csv(AGRI)
    years = sorted(inp["year"].unique(), key=ystart)
    return inp, meta, agri, years


def etg_brazil(years):
    """Brazil production per the SnD ETG sheet (Arabica and Robusta), by crop year."""
    df, smeta, _n, yrs = snd.load()
    a, r = snd.block(df, smeta, "Arabica", yrs), snd.block(df, smeta, "Robusta", yrs)
    return a.loc["Brazil"], r.loc["Brazil"]


def compute(inp, etg_a, etg_r, years, meta):
    """The three blocks as DataFrames (rows x crop years) plus the effective value of every input series."""
    S = {s: inp[inp["series"] == s].set_index("year")["value"].reindex(years).astype(float) for s in SERIES}
    pa = S["Arabica production"].fillna(etg_a.reindex(years))
    pc = S["Conillon production"].fillna(etg_r.reindex(years))
    ea, gx, sx, share = S["Arabica exports"], S["Green exports"], S["Soluble exports"], S["Conillon demand %"]
    overall = S["Overall consumption"].fillna(S["Arabica consumption"] + S["Conillon consumption"])
    ca = S["Arabica consumption"].fillna((1 - share) * overall)
    cc = S["Conillon consumption"].fillna(share * overall)
    eff = {"Arabica production": pa, "Arabica exports": ea, "Arabica consumption": ca, "Conillon production": pc, "Green exports": gx,
           "Soluble exports": sx, "Conillon consumption": cc, "Conillon demand %": share, "Overall consumption": overall}

    def roll(change, opening):
        out, run = [], float(opening)
        for i, v in enumerate(change):
            run = run if i == 0 else run + (v if pd.notna(v) else 0.0)
            out.append(run)
        return pd.Series(out, index=years)

    A = pd.DataFrame(index=years, dtype=float)
    chg_a = pa - ea - ca
    A["Production"], A["Exports"], A["Consumption"], A["Demand as % of total"] = pa, ea, ca, 1 - share
    A["Stock Change"] = chg_a
    A["Closing Stock"] = roll(chg_a, meta["opening"]["Arabica"])
    A["Exports % of Production"], A["Consumption % of Production"] = ea / pa, ca / pa
    A["Stock/Use Arabica"] = A["Closing Stock"] / ca

    C = pd.DataFrame(index=years, dtype=float)
    chg_c = pc - gx - sx - cc
    C["Production"], C["Green Exports"], C["Soluble Exports"], C["Consumption"], C["Demand as % of total"] = pc, gx, sx, cc, share
    C["Stock Change"] = chg_c
    C["Closing Stock"] = roll(chg_c, meta["opening"]["Conillon"])
    C["Exports % of Production"] = (gx + sx) / pc
    cop = (cc / pc).tolist()
    for i in range(10, len(cop)):                                     # the sheet projects it as the average of the 10 years before
        cop[i] = float(np.nanmean(cop[i - 10:i]))
    C["Consumption % of Production"] = cop
    C["Stock/Use Conillon"] = C["Closing Stock"] / cc

    A["All Coffee Stocks Brazil"] = A["Closing Stock"] + C["Closing Stock"]
    A["Exports YoY"] = ea.pct_change(fill_method=None)
    A["Arabica Consumption %"] = ca.pct_change(fill_method=None)
    C["Connie Consumption %"] = cc.pct_change(fill_method=None)
    C["All Coffee Production"] = pa + pc
    C["Overall Consumption Brazil"] = overall
    C["Annual % change consumption"] = overall.pct_change(fill_method=None)

    O = pd.DataFrame(index=years, dtype=float)
    prod, cons = pa + pc, ca + cc
    O["Production"], O["Green Exports"], O["Soluble Exports"], O["Consumption"] = prod, ea + gx, sx, cons
    O["Stock Change"] = prod - O["Green Exports"] - sx - cons
    O["Closing Stock"] = A["Closing Stock"] + C["Closing Stock"]
    O["Exports % of Production"] = (O["Green Exports"] + sx) / prod
    O["Consumption % of Production"] = cons / prod
    O["Stock/Use"] = O["Closing Stock"] / cons
    return A.T, C.T, O.T, eff


# ── Table ─────────────────────────────────────────────────────────────────────
def short(y: str) -> str:
    """2014/15 -> 14/15, as the sheet shows it."""
    return y[2:]


def p0(v):
    return fpct(v, 0)


def p1(v):
    return fpct(v, 1)


LAYOUT = {
    "Arabica": [("Production", "b", fnum), ("Exports", "", fnum), ("Consumption", "", fnum), ("Demand as % of total", "soft", p0),
                ("Stock Change", "bal", fnum), ("Closing Stock", "b", fnum), ("Exports % of Production", "soft", p0),
                ("Consumption % of Production", "soft", p0), ("Stock/Use Arabica", "soft", p0), ("All Coffee Stocks Brazil", "", fnum),
                ("Exports YoY", "soft", p0), ("Arabica Consumption %", "soft", p1)],
    "Conillon": [("Production", "b", fnum), ("Green Exports", "", fnum), ("Soluble Exports", "", fnum), ("Consumption", "", fnum),
                 ("Demand as % of total", "soft", p0), ("Stock Change", "bal", fnum), ("Closing Stock", "b", fnum),
                 ("Exports % of Production", "soft", p0), ("Consumption % of Production", "soft", p0), ("Stock/Use Conillon", "soft", p0),
                 ("Connie Consumption %", "soft", p1), ("All Coffee Production", "", fnum), ("Overall Consumption Brazil", "b", fnum),
                 ("Annual % change consumption", "soft", p1)],
    "Overall Brazil": [("Production", "b", fnum), ("Green Exports", "", fnum), ("Soluble Exports", "", fnum), ("Consumption", "", fnum),
                       ("Stock Change", "bal", fnum), ("Closing Stock", "b", fnum), ("Exports % of Production", "soft", p0),
                       ("Consumption % of Production", "soft", p0), ("Stock/Use", "soft", p0)],
}


def block_html(title, fr, shown, notes_for=None) -> str:
    ncol = len(shown) + 1
    out = [f"<tr class='comm'><th colspan='{ncol}'>{title}</th></tr>",
           "<tr><th class='y first'></th>" + "".join(f"<th class='y{' fc' if snd.is_estimate(y) else ''}'>{short(y)}{'*' if snd.is_estimate(y) else ''}</th>"
                                                    for y in shown) + "</tr>"]
    for label, kind, fmt in LAYOUT[title]:
        neg = label == "Stock Change"
        cells = "".join(f"<td class='{'fc ' if snd.is_estimate(y) else ''}{'neg' if neg and pd.notna(fr.loc[label, y]) and fr.loc[label, y] < -0.049 else ''}'>"
                        f"{fmt(fr.loc[label, y])}</td>" for y in shown)
        out.append(f"<tr class='{kind}'><td class='lbl'>{label}</td>{cells}</tr>")
    return "".join(out)


def full_table(A, C, O, shown) -> str:
    gap = f"<tr class='gap'><td colspan='{len(shown) + 1}'></td></tr>"
    return (f"<div class='snd-wrap'><table class='snd'>{block_html('Arabica', A, shown)}{gap}{block_html('Conillon', C, shown)}{gap}"
            f"{block_html('Overall Brazil', O, shown)}</table></div>")


# ── AgriAcies format ──────────────────────────────────────────────────────────
def agri_html(agri: pd.DataFrame) -> str:
    out = []
    for table in ["Arabica Jul-Jun", "Robusta Apr-Mar", "Total Jul-Jun"]:
        d = agri[agri["table"] == table].copy()
        d = d[d["production"].notna() | d["stu"].notna()]                # no empty history rows
        d["_y"] = d["year"].map(ystart)
        d = d.sort_values("_y")
        rows, prev_out = [], None
        for r in d.itertuples():
            has = pd.notna(r.production)
            if has:
                carry = r.carry_in if pd.notna(r.carry_in) else prev_out
                supply = r.production + (carry if carry is not None else 0.0)
                carry_out = supply - r.int_use - r.exports
                stu = carry_out / (r.exports + r.int_use)
                prev_out = carry_out
                rows.append(f"<tr><td class='lbl'>{short(r.year)}</td><td>{fnum(carry)}</td><td>{fnum(r.production)}</td><td>{fnum(supply)}</td>"
                            f"<td>{fnum(r.int_use)}</td><td>{fnum(r.exports)}</td><td>{fnum(carry_out)}</td><td class='b'>{fpct(stu, 1)}</td></tr>")
            else:
                stu = fpct(r.stu, 1) if pd.notna(r.stu) else ""
                rows.append(f"<tr class='soft'><td class='lbl'>{short(r.year)}</td><td></td><td></td><td></td><td></td><td></td><td></td><td>{stu}</td></tr>")
        out.append(f"<div class='snd-bar'>{table}</div><div class='snd-wrap' style='border-radius:0 0 8px 8px;margin-top:0'><table class='snd'>"
                   "<tr><th class='y first'>Crop year</th><th class='y'>Carry in</th><th class='y'>Production</th><th class='y'>Supply</th>"
                   "<th class='y'>Int use</th><th class='y'>Exports</th><th class='y'>Carry out</th><th class='y'>STU</th></tr>"
                   + "".join(rows) + "</table></div>")
    return "".join(out)


# ── Editing helpers ───────────────────────────────────────────────────────────
def _num(t):
    return snd._num(t)


def _show(series, v):
    if v is None or pd.isna(v):
        return ""
    return f"{v * 100:g}" if series in PCT_SERIES else f"{v:g}"


def _parse(series, txt):
    v = _num(txt)
    return None if v is None else (v / 100 if series in PCT_SERIES else v)


def _apply(inp, changes):
    d = inp.copy()
    for s, y, _o, n in changes:
        d = d[~((d["series"] == s) & (d["year"] == y))]
        if n is not None:
            d = pd.concat([d, pd.DataFrame([{"series": s, "year": y, "value": n}])], ignore_index=True)
    return d


def _save(changes):
    lines = [f"{s} {y}: {_show(s, o) or '-'} -> {_show(s, n) or '-'}" for s, y, o, n in changes]
    msg = f"Brazil SnD | {len(changes)} change(s)\n\n" + "\n".join(lines)

    def apply(text):
        d = _apply(pd.read_csv(io.StringIO(text)), changes)
        order = {s: i for i, s in enumerate(SERIES)}
        d["_o"], d["_y"] = d["series"].map(order), d["year"].map(ystart)
        d = d.sort_values(["_o", "_y"]).drop(columns=["_o", "_y"])
        return d.to_csv(index=False, lineterminator="\n"), None
    new_text, _ = gh.commit(INP_PATH, apply, msg)
    with open(INP, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)
    load.clear()


def _grid(eff, years):
    return pd.DataFrame({y: [_show(s, eff[s][y]) for s in SERIES] for y in years}, index=SERIES)


def _changes(g, after, years):
    out = []
    for s in SERIES:
        for y in years:
            o, n = _parse(s, g.loc[s, y]), _parse(s, after.loc[s, y])
            if o != n:
                out.append((s, y, o, n))
    return out


def _editor(eff, years, editable, key):
    g = _grid(eff, years)
    cols = {y: st.column_config.TextColumn(f"{short(y)}{'*' if snd.is_estimate(y) else ''}", alignment="right", width=72) for y in years}
    cols["_index"] = st.column_config.TextColumn("", width=170)
    after = st.data_editor(g, column_config=cols, disabled=not editable, width="stretch", row_height=28, height=len(g) * 28 + 40, key=key)
    try:
        return g, after, _changes(g, after, years)
    except ValueError:
        st.error("Numbers only.")
        return g, after, None


def _save_controls(changes, keys, prefix):
    bc = st.columns([1, 1, 6], vertical_alignment="center")
    save = bc[0].button("Save", type="primary", disabled=not changes, width="stretch", key=f"{prefix}_save")
    if bc[1].button("Undo", disabled=not changes, width="stretch", key=f"{prefix}_undo"):
        for k in keys:
            st.session_state.pop(k, None)
        st.rerun()
    if changes:
        bc[2].markdown(f"<div class='card-desc' style='margin:0'>{len(changes)} unsaved cell(s).</div>", unsafe_allow_html=True)
    if save:
        try:
            with st.spinner("Saving..."):
                _save(changes)
        except (gh.GitHubError, Exception) as ex:
            st.error(f"GitHub save failed: {ex}")
        else:
            for k in keys:
                st.session_state.pop(k, None)
            st.session_state["en_flash"] = f"Saved {len(changes)} change(s)."
            st.rerun()


# ── Page ──────────────────────────────────────────────────────────────────────
def render():
    st.markdown(snd.CSS, unsafe_allow_html=True)
    inp, meta, agri, years = load()
    etg_a, etg_r = etg_brazil(years)
    with st.sidebar:
        st.markdown("<div class='sb-sep'></div>", unsafe_allow_html=True)
        span = st.radio("Years", ["All", "Last 10"], horizontal=True, key="br_span")
        mode = st.radio("Mode", ["View", "Edit"], horizontal=True, key="br_mode")
    shown = years if span == "All" else years[-10:]
    if st.session_state.get("en_flash"):
        st.toast(st.session_state.pop("en_flash"))
    st.markdown("<div class='snd-head'><span class='t'>Brazil internal SnD</span><span class='s'>Jul–Jun · million 60 kg bags · * estimate"
                + (" · editing inputs" if mode == "Edit" else "") + "</span></div>", unsafe_allow_html=True)
    view = st.radio("View", ["Brazil SnD", "AgriAcies format"], horizontal=True, key="br_view", label_visibility="collapsed")
    if view == "AgriAcies format":
        st.markdown(agri_html(agri), unsafe_allow_html=True)
        return
    A, C, O, eff = compute(inp, etg_a, etg_r, years, meta)
    if mode == "Edit":
        editable = gh.enabled()
        st.markdown("<div class='snd-bar'>Inputs</div>", unsafe_allow_html=True)
        key = f"br_edit_{len(years)}"
        g, after, changes = _editor({s: eff[s] for s in SERIES}, years, editable, key)
        if changes is None:
            return
        if changes:                                                   # the tables below follow the edits
            A, C, O, eff = compute(_apply(inp, changes), etg_a, etg_r, years, meta)
        st.markdown(full_table(A, C, O, years), unsafe_allow_html=True)
        if not editable:
            st.markdown("<div class='card-desc'>Read-only: add github_token in Secrets to edit.</div>", unsafe_allow_html=True)
        else:
            _save_controls(changes, [key], "br")
        return
    st.markdown(full_table(A, C, O, shown), unsafe_allow_html=True)


def render_entry():
    st.markdown(snd.CSS, unsafe_allow_html=True)
    inp, meta, _agri, years = load()
    etg_a, etg_r = etg_brazil(years)
    _A, _C, _O, eff = compute(inp, etg_a, etg_r, years, meta)
    editable = gh.enabled()
    with st.container(border=True):
        st.markdown("<div class='card-title'>Brazil inputs <span class='pill'>m bags · demand % as percent</span></div>", unsafe_allow_html=True)
        key = f"br_entry_{len(years)}"
        g, after, changes = _editor({s: eff[s] for s in SERIES}, years, editable, key)
        if changes is not None:
            if not editable:
                st.markdown("<div class='card-desc'>Read-only: add github_token in Secrets to edit.</div>", unsafe_allow_html=True)
            else:
                _save_controls(changes, [key], "brn")
    with st.container(border=True):
        st.markdown("<div class='card-title'>Closing stock of the first year</div>", unsafe_allow_html=True)
        c = st.columns([1.2, 1.2, 1, 4], vertical_alignment="bottom")
        old = dict(meta["opening"])
        new = {k: c[i].number_input(f"{k} {years[0]} (m bags)", min_value=0.0, value=float(old[k]), step=0.1, format="%.1f",
                                    key=f"br_open_{k}", disabled=not editable) for i, k in enumerate(["Arabica", "Conillon"])}
        if c[2].button("Save", disabled=(not editable) or all(abs(new[k] - old[k]) < 1e-9 for k in new), width="stretch", key="br_open_save"):
            try:
                with st.spinner("Saving..."):
                    def apply(text):
                        d = json.loads(text)
                        d["opening"] = {k: round(float(v), 4) for k, v in new.items()}
                        return json.dumps(d, indent=2) + "\n", None
                    text, _ = gh.commit(META_PATH, apply, f"Setting | Brazil opening stocks: {old} -> {new}")
                    with open(META, "w", encoding="utf-8", newline="") as f:
                        f.write(text)
                    load.clear()
            except (gh.GitHubError, Exception) as ex:
                st.error(f"GitHub save failed: {ex}")
            else:
                st.session_state["en_flash"] = "Opening stocks saved."
                st.rerun()
