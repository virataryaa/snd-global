"""Brazil internal SnD: Arabica, Conillon (Robusta) and overall Brazil, plus the AgriAcies-format tables.

Inputs live in Database/brazil_snd.csv (hard-coded cells of the Excel sheet); everything else is calculated the way the sheet does it:
  * production = the 'Coffee SnD ETG' Brazil number, unless this sheet has its own for the year,
  * consumption is typed up to 2020/21; after that it is (1 - Conillon demand %) or the Conillon demand % times the overall Brazil
    consumption (typed from 2020/21),
  * stock change = production - exports - consumption, closing stock = last year's closing stock + stock change (the first year's is typed).
"""
import html
import io
import json
import re

MODE_SLOT = None   # sidebar container app.py reserves for Mode (above the section nav)

import numpy as np
import pandas as pd
import plotly.graph_objects as go
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
    inp = pd.read_csv(io.StringIO(gh.text_of(INP_PATH, INP)))
    meta = json.loads(gh.text_of(META_PATH, META))
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
    # Brazil production is linked to the Global SnD table's Brazil rows (one source; Brazil-page edits save there)
    pa, pc = etg_a.reindex(years).astype(float), etg_r.reindex(years).astype(float)
    ea, gx, sx = S["Arabica exports"], S["Green exports"], S["Soluble exports"]
    # rule: Arabica consumption + Conillon consumption = Overall consumption. Arabica and Overall are the inputs;
    # Conillon is what's left, and its demand share follows (older years without an Arabica input use the stored share)
    overall = S["Overall consumption"].fillna(S["Arabica consumption"] + S["Conillon consumption"])
    ca = S["Arabica consumption"].fillna((1 - S["Conillon demand %"]) * overall)
    cc = overall - ca
    share = cc / overall
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
    "Arabica": [("Production", "b", fnum), ("Exports", "", fnum), ("Consumption", "", fnum), ("Demand as % of total", "hl", p0),
                ("Stock Change", "bal", fnum), ("Closing Stock", "b", fnum), ("Exports % of Production", "soft", p0),
                ("Consumption % of Production", "soft", p0), ("Stock/Use Arabica", "soft", p0), ("All Coffee Stocks Brazil", "", fnum),
                ("Exports YoY", "soft", p0), ("Arabica Consumption %", "soft", p1)],
    "Conillon": [("Production", "b", fnum), ("Green Exports", "", fnum), ("Soluble Exports", "", fnum), ("Consumption", "", fnum),
                 ("Demand as % of total", "hl", p0), ("Stock Change", "bal", fnum), ("Closing Stock", "b", fnum),
                 ("Exports % of Production", "soft", p0), ("Consumption % of Production", "soft", p0), ("Stock/Use Conillon", "soft", p0),
                 ("Connie Consumption %", "soft", p1), ("All Coffee Production", "", fnum), ("Overall Consumption Brazil", "b", fnum),
                 ("Annual % change consumption", "soft", p1)],
    "Overall Brazil": [("Production", "b", fnum), ("Green Exports", "", fnum), ("Soluble Exports", "", fnum), ("Consumption", "", fnum),
                       ("Stock Change", "bal", fnum), ("Closing Stock", "b", fnum), ("Exports % of Production", "soft", p0),
                       ("Consumption % of Production", "soft", p0), ("Stock/Use", "soft", p0)],
}


# ratio rows shown only with the sidebar's "Detailed ratios" switch (stocks and stock/use always stay)
DETAIL = {"Exports % of Production", "Consumption % of Production", "Exports YoY",
          "Arabica Consumption %", "Connie Consumption %", "Annual % change consumption"}


# calculated rows still shown in Edit mode's "Editable" view, so the effect of a linked edit is visible
DISPLAY = {"Demand as % of total": "Share of domestic consumption"}   # row labels shown in the table


EDIT_ALWAYS = {("Conillon", "Consumption")}   # = Overall - Arabica


EDITABLE = {
    "Arabica": {"Production": "Arabica production", "Exports": "Arabica exports", "Consumption": "Arabica consumption"},
    "Conillon": {"Production": "Conillon production", "Green Exports": "Green exports", "Soluble Exports": "Soluble exports",
                 "Overall Consumption Brazil": "Overall consumption"},   # Conillon consumption = Overall - Arabica (calculated)
    "Overall Brazil": {},
}

_LINE_RX = re.compile(r"^(.+) (\d{4}/\d{2}): (.*) -> (.*)$")
_REASON_RX = re.compile(r"\| reason: (.*)$")


def _val(t):
    t = t.strip()
    return None if t in ("", "-") else float(t)


@st.cache_data(ttl=300)
def cell_history():
    """{(series, year): [(when, old, new, reason), ...]} newest first, from the GitHub save history — same convention as snd.cell_history."""
    out = {}
    if not gh.enabled():
        return out
    for ts, msg in gh.history(INP_PATH):
        first, _, body = msg.partition("\n")
        if not first.startswith("Brazil SnD |"):
            continue
        why = _REASON_RX.search(first)
        why = why.group(1).strip() if why else ""
        for ln in body.splitlines():
            m = _LINE_RX.match(ln.strip())
            if not m:
                continue
            series, year, old, new = m.groups()
            out.setdefault((series, year), []).append((ts, _val(old), _val(new), why))
    return out


def block_html(title, fr, shown, edit=None, hist=None) -> str:
    ncol = len(shown) + 2                                     # + the trailing Trend sparkline column
    out = [f"<tr class='comm'><th colspan='{ncol}'>{title}<span class='crop'>Jul–Jun</span></th></tr>",
           "<tr><th class='y first'></th>" + "".join(f"<th class='y{' fc' if snd.is_estimate(y) else ''}'>{short(y)}{'*' if snd.is_estimate(y) else ''}</th>"
                                                    for y in shown) + "<th class='y spark-h'>Trend</th></tr>"]
    for label, kind, fmt in LAYOUT[title]:
        if edit and not edit.get("all") and label not in EDITABLE[title] and (title, label) not in EDIT_ALWAYS:
            continue                                              # "Editable" view: input rows (+ EDIT_ALWAYS) only
        if label in DETAIL and not st.session_state.get("br_detail", False) and label not in EDITABLE[title]:
            continue
        neg = label == "Stock Change"
        series = EDITABLE[title].get(label) if edit else None
        hseries = EDITABLE[title].get(label)                  # revision history is keyed the same way, independent of edit mode

        def cell(y):
            cls = ("fc " if snd.is_estimate(y) else "") + ("neg" if neg and pd.notna(fr.loc[label, y]) and fr.loc[label, y] < -0.049 else "")
            attrs, pop = "", ""
            is_input = bool(series)
            if series:                                                   # an input cell: typed over in place
                k = f"{series}|{y}"
                b = edit["base"].get(k)
                cls += " ed" + (" chg" if k in edit["changed"] else "")
                attrs = (f" data-k='{k}' data-base='{'' if b is None or pd.isna(b) else b}'"
                         + (" data-pct='1'" if series in PCT_SERIES else ""))
            revs = hist.get((hseries, y)) if hist and hseries and not is_input else None
            if revs:
                cls += " rev"
                lo, ln = revs[0][1], revs[0][2]
                dc = "up" if lo is not None and ln is not None and ln > lo else "down" if lo is not None and ln is not None and ln < lo else ""
                rows = "".join(f"<div class='row'><span class='dt'>{ts[:10]}</span>{snd.fnum(o, 1) or '-'} &rarr; {snd.fnum(n, 1) or '-'}"
                               + (f"<span class='rs'>{html.escape(r, quote=True)}</span>" if r else "") + "</div>" for ts, o, n, r in revs[:8])
                pop = f"<span class='rev-dot {dc}'></span><div class='rev-pop'>{snd._rev_chart(revs, label)}{rows}</div>"
            return f"<td class='{cls.strip()}'{attrs}>{fmt(fr.loc[label, y])}{pop}</td>"
        cells = "".join(cell(y) for y in shown)
        skind = "bal" if kind == "bal" else ("plain" if fmt in (p0, p1) else "growth")
        spark = (snd.sparkline_balance if skind == "bal" else snd.sparkline)
        spark_html = spark([(y, fr.loc[label, y]) for y in shown], label) if skind == "bal" else spark([(y, fr.loc[label, y]) for y in shown], label, skind)
        out.append(f"<tr class='{kind}'><td class='lbl'>{DISPLAY.get(label, label)}</td>{cells}<td class='spark-td'>{spark_html}</td></tr>")
    if edit and title in ("Arabica", "Conillon"):              # the stock roll's starting point, typed like any other input
        k = f"Opening {title}|{shown[0]}"
        b = edit["base"].get(k)
        cls = "ed" + (" chg" if k in edit["changed"] else "")
        out.append(f"<tr><td class='lbl'>First-year closing stock</td><td class='{cls}' data-k='{k}' data-base='{b}'>{snd.fnum(b)}</td>"
                   + "<td></td>" * (len(shown) - 1) + "<td class='spark-td'></td></tr>")
    return "".join(out)


def full_table(A, C, O, shown, edit=None) -> str:
    hist = dict(cell_history())
    for (comm, item, y), revs in snd.cell_history().items():      # linked production: its saves live in the Global table
        if item == "Brazil":
            hist[("Arabica production" if comm == "Arabica" else "Conillon production", y)] = revs
    gap = f"<tr class='gap'><td colspan='{len(shown) + 2}'></td></tr>"
    overall = "" if edit and not edit.get("all") else f"{gap}{block_html('Overall Brazil', O, shown, edit, hist)}"   # no inputs there
    return (f"<div class='snd-wrap'><table class='snd'>{block_html('Arabica', A, shown, edit, hist)}{gap}{block_html('Conillon', C, shown, edit, hist)}"
            f"{overall}</table></div>")


# ── AgriAcies format ──────────────────────────────────────────────────────────
def agri_html(agri: pd.DataFrame) -> str:
    out = []
    for table in ["Arabica Jul-Jun", "Robusta Apr-Mar", "Total Jul-Jun"]:                  # the three main tables
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
    side = agri[agri["table"] == "AgriAcies Brazil"].copy()
    if not side.empty:
        side["_y"] = side["year"].map(ystart)
        side = side.sort_values("_y")
        head = "".join(f"<th class='y'>{short(y)}</th>" for y in side["year"])
        out.append("<div class='snd-bar'>AgriAcies Brazil</div><div class='snd-wrap' style='border-radius:0 0 8px 8px;margin-top:0'><table class='snd'>"
                   f"<tr><th class='y first'></th>{head}</tr>"
                   "<tr class='b'><td class='lbl'>Production</td>" + "".join(f"<td>{fnum(v)}</td>" for v in side["production"]) + "</tr>"
                   "<tr><td class='lbl'>Carry in stocks</td>" + "".join(f"<td>{fnum(v)}</td>" for v in side["carry_in"]) + "</tr></table></div>")
    return "".join(out)


# ── Editing helpers ───────────────────────────────────────────────────────────
def _show(series, v):
    if v is None or pd.isna(v):
        return ""
    return f"{v * 100:g}" if series in PCT_SERIES else f"{v:g}"


def _apply(inp, changes):
    d = inp.copy()
    for s, y, _o, n in changes:
        d = d[~((d["series"] == s) & (d["year"] == y))]
        if n is not None:
            d = pd.concat([d, pd.DataFrame([{"series": s, "year": y, "value": n}])], ignore_index=True)
    return d


# production series are stored in the Global SnD table (coffee_snd.csv, item "Brazil"), not in brazil_snd.csv
LINKED = {"Arabica production": "Arabica", "Conillon production": "Robusta"}


def _split(changes):
    return [c for c in changes if c[0] in LINKED], [c for c in changes if c[0] not in LINKED]


def _linked_etg(etg_a, etg_r, prod_changes):
    """Preview: the Global Brazil rows with this page's unsaved production edits applied."""
    a, r = etg_a.copy(), etg_r.copy()
    for s, y, _o, n in prod_changes:
        (a if LINKED[s] == "Arabica" else r)[y] = float("nan") if n is None else n
    return a, r


def _save_all(changes, reason=""):
    prod, rest = _split(changes)
    if prod:
        snd._save_inputs([(LINKED[s], "Brazil", y, o, n) for s, y, o, n in prod], reason)
    if rest:
        _save(rest, reason)


def _save(changes, reason=""):
    lines = [f"{s} {y}: {_show(s, o) or '-'} -> {_show(s, n) or '-'}" for s, y, o, n in changes]
    reason = snd.clean_reason(reason)
    msg = f"Brazil SnD | {len(changes)} change(s)" + (f" | reason: {reason}" if reason else "") + "\n\n" + "\n".join(lines)

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
    cell_history.clear()


# ── Page ──────────────────────────────────────────────────────────────────────
def _undo():
    st.session_state.pop("br_new_year", None)
    st.session_state["br_epoch"] = st.session_state.get("br_epoch", 0) + 1
    st.session_state["_br_edits"] = {}
    try:
        st.session_state["br_tbl"] = {}
    except Exception:
        pass


def edit_view(inp, meta, etg_a, etg_r, years, eff, editable):
    """Edit mode: the table itself, input cells typed over in place; the calculated rows follow the edits. One Save."""
    import tableedit
    epoch = st.session_state.setdefault("br_epoch", 0)
    edits = st.session_state.get("br_tbl")                       # see snd.render_edit: keep a copy across View / Edit switches
    if edits is None:
        edits = st.session_state.get("_br_edits", {})
    base = {f"{s}|{y}": float(eff[s][y]) for s in SERIES for y in years if pd.notna(eff[s][y])}
    base.update({f"Opening {k}|{years[0]}": float(meta["opening"][k]) for k in ("Arabica", "Conillon")})
    nxt = snd.next_year(years[-1])
    extra = st.session_state.get("br_new_year")                # "+ Crop year": a blank column to the right, saved once filled
    if extra:
        years = years + [extra]
        etg_a, etg_r = etg_a.reindex(years), etg_r.reindex(years)
    allc = [(k.split("|")[0], k.split("|")[1], base.get(k), (None if v is None else float(v))) for k, v in edits.items()]
    opens = [c for c in allc if c[0].startswith("Opening ")]    # first-year closing stock lives in the meta file
    changes = [c for c in allc if not c[0].startswith("Opening ")]
    live_meta = {**meta, "opening": {**meta["opening"], **{c[0][8:]: c[3] for c in opens if c[3] is not None}}}
    prod, rest = _split(changes)
    A, C, O, _eff = compute(_apply(inp, rest), *_linked_etg(etg_a, etg_r, prod), years, live_meta)
    table = full_table(A, C, O, years, edit=dict(base=base, changed=set(edits), all=st.session_state.get("edit_rows") != "Show only editable"))
    if allc:                                                     # tint every calculated cell the unsaved edits move
        A0, C0, O0, _ = compute(inp, etg_a, etg_r, years, meta)
        ref = full_table(A0, C0, O0, years, edit=dict(base=base, changed=set(edits), all=st.session_state.get("edit_rows") != "Show only editable"))
        table = tableedit.mark_moved(table, ref)
    ctrl = st.container()                                        # Save / Undo / Reason sit above the table
    bar = ctrl.container(horizontal=True, vertical_alignment="center", gap="small")   # one compact row, left-aligned
    bar.radio("Rows", ["Show all rows", "Show only editable"], horizontal=True, key="edit_rows", label_visibility="collapsed")
    tableedit.editable_table(table, tableedit.css_of(snd.CSS), "br_tbl", epoch, editable, edits)
    st.markdown("<div class='card-desc' style='margin:4px 0 0'>Rule: Arabica consumption + Conillon consumption = Overall consumption. "
                "Edit Arabica and Overall; Conillon is worked out as Overall minus Arabica.</div>", unsafe_allow_html=True)
    st.session_state["_br_edits"] = dict(edits)
    if not editable:
        ctrl.markdown("<div class='card-desc'>Read-only: add github_token in Secrets to edit.</div>", unsafe_allow_html=True)
        return
    n_all = len(allc)
    bad = any(c[3] is not None and c[3] < 0 for c in allc)
    if bad:
        ctrl.error("Values cannot be negative.")


    reason = bar.text_input("Reason", key=f"br_reason_{epoch}", placeholder="Reason for Change...", width=320,
                              label_visibility="collapsed", max_chars=140, disabled=not n_all)
    bar.button("Undo", disabled=not n_all, width="content", key="br_undo", on_click=_undo)
    save = bar.button("Save" + (f" · {n_all}" if n_all else ""), type="primary", disabled=(not n_all) or bad,
                      width="content", key="br_save")
    bar.button("+ Crop year", key="br_addyr", disabled=bool(extra), width="content",
               on_click=lambda: st.session_state.__setitem__("br_new_year", nxt))
    if save:
        try:
            with st.spinner("Saving..."):
                if changes:
                    _save_all(changes, reason)
                if opens:
                    old = dict(meta["opening"])
                    new = {**old, **{c[0][8:]: float(c[3]) for c in opens if c[3] is not None}}

                    def apply(text):
                        d = json.loads(text)
                        d["opening"] = {k: round(float(v), 4) for k, v in new.items()}
                        return json.dumps(d, indent=2) + "\n", None
                    text, _ = gh.commit(META_PATH, apply, f"Setting | Brazil opening stocks: {old} -> {new}")
                    with open(META, "w", encoding="utf-8", newline="") as f:
                        f.write(text)
                    load.clear()
        except (gh.GitHubError, Exception) as ex:
            ctrl.error(f"GitHub save failed: {ex}")
        else:
            _undo()
            st.session_state["en_flash"] = f"Saved {n_all} change(s)."
            st.rerun()

# ── Charts ────────────────────────────────────────────────────────────────────
def _bars(fig, x, y, name, color, est, **kw):
    fig.add_trace(go.Bar(x=x, y=y, name=name, marker=dict(color=color, opacity=[0.55 if e else 1 for e in est], line_width=0),
                         hovertemplate=name + ": %{y:.1f}<extra></extra>", **kw))


def _line(fig, x, y, name, color, right=False, pct=False):
    fig.add_trace(go.Scatter(x=x, y=y, name=name, mode="lines+markers", yaxis="y2" if right else "y", line=dict(color=color, width=2.2),
                             marker=dict(size=5), hovertemplate=name + (": %{y:.1f}%" if pct else ": %{y:.1f}") + "<extra></extra>"))


def _y2(fig, suffix="%"):
    return fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, color=snd.AXIS, ticksuffix=suffix, tickfont=dict(size=10)))


def consumption_share(A, C, shown):
    """Arabica vs Conillon share of Brazil's domestic consumption (stacked to 100%), volumes on hover."""
    import plotly.graph_objects as go
    from analytics import _fig, card
    x = [short(y) for y in shown]
    with st.container(border=True):
        card("Domestic consumption: Arabica vs Conillon share")
        fig = go.Figure()
        for fr, name, col in ((A, "Arabica", snd.NAVY), (C, "Conillon", snd.AMBER)):
            fig.add_trace(go.Bar(x=x, y=[fr.loc["Demand as % of total", y] * 100 for y in shown], name=name,
                                 customdata=[fr.loc["Consumption", y] for y in shown],
                                 marker=dict(color=col, line_width=0, opacity=[0.55 if snd.is_estimate(y) else 1 for y in shown]),
                                 text=[f"{fr.loc['Demand as % of total', y]:.0%}" for y in shown], textposition="inside",
                                 hovertemplate=name + ": %{y:.0f}% · %{customdata:.1f}m bags<extra></extra>"))
        st.plotly_chart(_fig(fig, height=280, fmt=",.0f").update_layout(barmode="stack", yaxis=dict(range=[0, 100], ticksuffix="%")),
                        width="stretch", key="br_cons_share")


def charts(A, C, O, shown):
    """Brazil internal SnD visuals: supply mix, stocks, exports, home demand, stock build/draw and stocks to use. Estimates are faded."""
    x = [y[2:] for y in shown]
    est = [snd.is_estimate(y) for y in shown]
    NAVY, TEAL, AMBER, GREEN, RED, GREY = snd.NAVY, snd.TEAL, snd.AMBER, snd.GREEN, snd.RED, snd.GREY
    total = A.loc["Production", shown] + C.loc["Production", shown]
    cells = [c for _ in range(2) for c in st.columns(3, gap="small")]   # 3 charts a row

    with cells[0], st.container(border=True):
        st.markdown("<div class='chart-head'>Production: Arabica and Conillon</div>", unsafe_allow_html=True)
        fig = go.Figure()
        _bars(fig, x, A.loc["Production", shown], "Arabica", NAVY, est)
        _bars(fig, x, C.loc["Production", shown], "Conillon", AMBER, est)
        _line(fig, x, (C.loc["Production", shown] / total * 100), "Conillon share (right)", RED, right=True, pct=True)
        st.plotly_chart(_y2(snd._style(fig, 230).update_layout(barmode="stack")), width="stretch", key="br_c_prod")
    with cells[1], st.container(border=True):
        st.markdown("<div class='chart-head'>Closing stocks</div>", unsafe_allow_html=True)
        fig = go.Figure()
        _bars(fig, x, A.loc["Closing Stock", shown], "Arabica", NAVY, est)
        _bars(fig, x, C.loc["Closing Stock", shown], "Conillon", AMBER, est)
        _line(fig, x, O.loc["Stock/Use", shown] * 100, "Brazil S/U (right)", RED, right=True, pct=True)
        st.plotly_chart(_y2(snd._style(fig, 230).update_layout(barmode="stack")), width="stretch", key="br_c_stock")

    with cells[2], st.container(border=True):
        st.markdown("<div class='chart-head'>Exports</div>", unsafe_allow_html=True)
        fig = go.Figure()
        _bars(fig, x, A.loc["Exports", shown], "Arabica", NAVY, est)
        _bars(fig, x, C.loc["Green Exports", shown], "Conillon green", AMBER, est)
        _bars(fig, x, C.loc["Soluble Exports", shown], "Soluble", TEAL, est)
        _line(fig, x, O.loc["Exports % of Production", shown] * 100, "% of crop (right)", RED, right=True, pct=True)
        st.plotly_chart(_y2(snd._style(fig, 230).update_layout(barmode="stack")), width="stretch", key="br_c_exp")
    with cells[3], st.container(border=True):
        st.markdown("<div class='chart-head'>Domestic consumption</div>", unsafe_allow_html=True)
        fig = go.Figure()
        _bars(fig, x, A.loc["Consumption", shown], "Arabica", NAVY, est)
        _bars(fig, x, C.loc["Consumption", shown], "Conillon", AMBER, est)
        _line(fig, x, C.loc["Consumption", shown] / O.loc["Consumption", shown] * 100, "Conillon share (right)", RED, right=True, pct=True)
        st.plotly_chart(_y2(snd._style(fig, 230).update_layout(barmode="stack")), width="stretch", key="br_c_cons")

    with cells[4], st.container(border=True):
        st.markdown("<div class='chart-head'>Stock build / draw</div>", unsafe_allow_html=True)
        fig = go.Figure()
        _bars(fig, x, A.loc["Stock Change", shown], "Arabica", NAVY, est)
        _bars(fig, x, C.loc["Stock Change", shown], "Conillon", AMBER, est)
        _line(fig, x, O.loc["Stock Change", shown], "Brazil", RED)
        st.plotly_chart(snd._style(fig, 230).update_layout(barmode="group"), width="stretch", key="br_c_chg")
    with cells[5], st.container(border=True):
        st.markdown("<div class='chart-head'>Stocks to use</div>", unsafe_allow_html=True)
        fig = go.Figure()
        _line(fig, x, A.loc["Stock/Use Arabica", shown] * 100, "Arabica", NAVY, pct=True)
        _line(fig, x, C.loc["Stock/Use Conillon", shown] * 100, "Conillon", AMBER, pct=True)
        _line(fig, x, O.loc["Stock/Use", shown] * 100, "Brazil", RED, pct=True)
        st.plotly_chart(snd._style(fig, 230).update_layout(yaxis_ticksuffix="%"), width="stretch", key="br_c_su")


def render(view="Brazil SnD"):
    st.markdown(snd.CSS, unsafe_allow_html=True)
    inp, meta, agri, years = load()
    etg_a, etg_r = etg_brazil(years)
    mode, span = "View", "All"
    if view == "Brazil SnD":
        with st.sidebar:
            st.markdown("<div class='sb-sep'></div>", unsafe_allow_html=True)
            st.toggle("Detailed ratios", value=False, key="br_detail")
        with (MODE_SLOT or st.sidebar), st.container(key="mode_nav"):
            mode = st.radio("Mode", ["View", "Edit"], horizontal=True, key="snd_mode", label_visibility="collapsed")   # shared with Global
    shown = years[-7:] if st.session_state.get("yrs_span", "All") == "Last 7" else years
    if st.session_state.get("en_flash"):
        st.toast(st.session_state.pop("en_flash"))
    title = "Brazil Internal SnD" if view == "Brazil SnD" else "AgriAcies format"
    editing = view == "Brazil SnD" and st.session_state.get("snd_mode") == "Edit"
    head = f"<span class='t edit'>Edit {title}</span>" if editing else f"<span class='t'>{title}</span>"
    st.markdown(f"<div class='snd-head'>{head}</div>", unsafe_allow_html=True)
    if view == "AgriAcies format":
        st.markdown(agri_html(agri), unsafe_allow_html=True)
        return
    A, C, O, eff = compute(inp, etg_a, etg_r, years, meta)
    if mode == "Edit":
        edit_view(inp, meta, etg_a, etg_r, years, eff, gh.enabled())
        return
    st.markdown(full_table(A, C, O, shown), unsafe_allow_html=True)
    consumption_share(A, C, shown)
    charts(A, C, O, shown)
