"""Cocoa SnD (Oct–Sep, k tonnes): Botanical and Statistical balances, plus the Ivory Coast / Ghana crop detail.

Inputs live in Database/cocoa_snd.csv (series, year, value). Ivory Coast (IC) and Ghana (GH) each have a Main and a Mid crop:
  Botanical crop = Tree.  Statistical crop = Tree + Carry-in + Smuggling GH + Smuggling Other + Held (to Mid / to Main).
  Rule: Ghana's IC<->GH smuggling = minus Ivory Coast's (typed on the IC side only).
Total = sum of origins x 0.99 · SnD = Total - Grind · Stock is typed up to 20/21 and from then on = previous stock + SnD.
"""
import html
import io
import re
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import theme

import ghstore as gh
import snd
from snd import fnum, fpct, ystart

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "Database" / "cocoa_snd.csv"
CSV_PATH = "Database/cocoa_snd.csv"                # path in the repo (data branch)
LOSS = 0.99                          # fixed haircut on the origin sum
ANCHOR = "2020/21"                   # last typed stock year; later years roll
ADJ = ["Carry-in", "Smuggling GH", "Smuggling Other", "Held"]
OTHERS = [("EC", "Ecuador"), ("NIG", "Nigeria"), ("CAM", "Cameroon"), ("INDO", "Indonesia"), ("BRAZ", "Brazil"),
          ("PERU", "Peru"), ("ROW", "Rest of world")]
COUNTRY = {"IC": "Ivory Coast", "GH": "Ghana"}


@st.cache_data(ttl=600)
def load():
    df = pd.read_csv(io.StringIO(gh.text_of(CSV_PATH, CSV)))
    years = sorted(df["year"].unique(), key=ystart)
    S = df.pivot_table(index="series", columns="year", values="value", aggfunc="sum").reindex(columns=years)
    return S, years


def current_year(today=None) -> str:
    t = pd.Timestamp(today or pd.Timestamp.today())
    y0 = t.year if t.month >= 10 else t.year - 1      # cocoa crop year starts in October
    return f"{y0}/{str(y0 + 1)[-2:]}"


def is_est(y: str) -> bool:
    return ystart(y) >= ystart(current_year())


def _row(S, name, years):
    return S.loc[name].reindex(years).astype(float) if name in S.index else pd.Series(np.nan, index=years)


def adj(S, years, cty, part, k):
    """One statistical adjustment. Rule: Ghana's IC<->GH smuggling is the mirror of Ivory Coast's (typed on the IC side only)."""
    if cty == "GH" and k == "Smuggling GH":
        return 0.0 - _row(S, f"IC {part} Smuggling GH", years)     # 0.0 - x, not -x: keeps zeros as 0 (not "-0")
    return _row(S, f"{cty} {part} {k}", years)


def crop(S, years, cty, part, basis):
    tree = _row(S, f"{cty} {part} Tree", years)
    if basis == "Botanical":
        return tree
    return tree + sum(adj(S, years, cty, part, k).fillna(0) for k in ADJ)


def balance(S, years, basis) -> pd.DataFrame:
    """The SnD table (rows x crop years) for one basis."""
    T = pd.DataFrame(columns=years, dtype=float)
    for cty in ("IC", "GH"):
        T.loc[f"{cty} Main"] = crop(S, years, cty, "Main", basis)
        T.loc[f"{cty} Mid"] = crop(S, years, cty, "Mid", basis)
        T.loc[f"{cty} Total"] = T.loc[f"{cty} Main"] + T.loc[f"{cty} Mid"]
    for code, _name in OTHERS:
        T.loc[code] = _row(S, code, years)
    origins = ["IC Total", "GH Total"] + [c for c, _ in OTHERS]
    T.loc["Total"] = T.loc[origins].sum(min_count=1) * LOSS
    T.loc["Grind"] = _row(S, "Grind", years)
    T.loc["SnD"] = T.loc["Total"] - T.loc["Grind"]
    stock, typed = [], _row(S, "Stock", years)
    for y in years:
        if ystart(y) <= ystart(ANCHOR):
            stock.append(typed[y])
        else:
            prev = stock[-1]
            stock.append(prev + T.loc["SnD", y] if pd.notna(prev) and pd.notna(T.loc["SnD", y]) else np.nan)
    T.loc["Stock proxy"] = stock
    T.loc["STU"] = T.loc["Stock proxy"] / T.loc["Grind"]
    T.loc["Grind %"] = T.loc["Grind"].pct_change(fill_method=None)
    ivgh = T.loc["IC Total"] + T.loc["GH Total"]
    T.loc["IVC/GH share"] = ivgh / T.loc["Grind"]
    T.loc["Main %"] = (T.loc["IC Main"] + T.loc["GH Main"]) / T.loc["Grind"]
    T.loc["IVC + GH"] = ivgh
    T.loc["IVC + GH +/-"] = ivgh.diff()
    return T


# label, kind, format  (kind: "b" bold, "bal" balance, "soft" muted ratio, "gap" spacer)
LAYOUT = ([("IC Main", "", 0), ("IC Mid", "", 0), ("IC Total", "b", 0), ("GH Main", "", 0), ("GH Mid", "", 0), ("GH Total", "b", 0)]
          + [(c, "", 0) for c, _ in OTHERS]
          + [("Total", "b", 0), ("Grind", "b", 0), ("SnD", "bal", 0), ("Stock proxy", "b", 0), ("STU", "soft", "p1"), (None, "gap", None),
             ("Grind %", "soft", "p1"), ("IVC/GH share", "soft", "p0"), ("Main %", "soft", "p0"), ("IVC + GH", "", 0), ("IVC + GH +/-", "bal", 0)])
LABEL = {"IC Main": "Ivory Coast main", "IC Mid": "Ivory Coast mid", "IC Total": "Ivory Coast total", "GH Main": "Ghana main",
         "GH Mid": "Ghana mid", "GH Total": "Ghana total", **dict(OTHERS), "Total": "Total × 0.99", "Grind": "Grind", "SnD": "SnD",
         "Stock proxy": "Stock proxy", "STU": "Stock / grind", "Grind %": "Grind change", "IVC/GH share": "IVC + GH share of grind",
         "Main %": "Main crops share of grind", "IVC + GH": "IVC + GH", "IVC + GH +/-": "IVC + GH change"}


def _fmt(v, f):
    return fpct(v, 1) if f == "p1" else fpct(v, 0) if f == "p0" else fnum(v, f)


# short row labels for the compact side-by-side tables
SHORT = {"Total": "Total ×0.99", "Stock proxy": "Stock", "STU": "STU", "Grind %": "Grind %", "IVC/GH share": "IVC+GH / grind",
         "Main %": "Main / grind", "IVC + GH": "IVC + GH", "IVC + GH +/-": "IVC + GH +/-"}


def _head(title, years, sub="Oct–Sep · k tonnes", spark=True):
    ncol = len(years) + (2 if spark else 1)
    return (f"<tr class='comm'><th colspan='{ncol}'>{title}<span class='crop'>{sub}</span></th></tr>"
            "<tr><th class='y first'></th>" + "".join(f"<th class='y{' fc' if is_est(y) else ''}'>{y[2:]}{'*' if is_est(y) else ''}</th>"
                                                     for y in years) + ("<th class='y spark-h'>Trend</th>" if spark else "") + "</tr>")


@st.cache_data(ttl=300)
def cell_history():
    """{(series, year): [(when, old, new, reason), ...]} newest first, from the save history (same as the coffee pages)."""
    out = {}
    if not gh.enabled():
        return out
    for ts, msg in gh.history(CSV_PATH):
        first, _, body = msg.partition("\n")
        if not first.startswith("Cocoa SnD |"):
            continue
        why = _WHY.search(first)
        why = why.group(1).strip() if why else ""
        for ln in body.splitlines():
            m = _LINE.match(ln.strip())
            if m:
                s_, y, o, n = m.groups()
                out.setdefault((s_, y), []).append((ts, _v(o), _v(n), why))
    return out


def _cell(v, y, txt, cls, label, revs):
    """A table cell; with a revision dot + hover history when that input has been changed."""
    pop = ""
    if revs:
        cls += " rev"
        lo, ln = revs[0][1], revs[0][2]
        dc = "up" if pd.notna(lo) and pd.notna(ln) and ln > lo else "down" if pd.notna(lo) and pd.notna(ln) and ln < lo else ""
        rows = "".join(f"<div class='row'><span class='dt'>{str(ts)[:10]}</span>{fnum(o, 0) or '-'} &rarr; {fnum(n, 0) or '-'}"
                       + (f"<span class='rs'>{html.escape(r, quote=True)}</span>" if r else "") + "</div>" for ts, o, n, r in revs[:8])
        pop = f"<span class='rev-dot {dc}'></span><div class='rev-pop'>{snd._rev_chart(revs, label)}{rows}</div>"
    return f"<td class='{cls.strip()}'>{txt}{pop}</td>"


def _series_of(name, basis):
    """Which saved input a balance-table row shows (for its revision dots)."""
    if name in ("IC Main", "IC Mid", "GH Main", "GH Mid"):
        return f"{name} Tree" if basis == "Botanical" else None
    if name in dict(OTHERS) or name == "Grind":
        return name
    return "Stock" if name == "Stock proxy" else None


def _spark(name, vals, years, kind, f, label):
    pairs = [(y, vals[y]) for y in years]
    return snd.sparkline_balance(pairs, label) if kind == "bal" else snd.sparkline(pairs, label, "plain" if f in ("p0", "p1") else "growth")


def table_html(title, T, years, compact=False) -> str:
    """compact: short labels (for the side-by-side view). Every row has a Trend sparkline; changed inputs carry a revision dot."""
    hist = cell_history()
    out = [_head(title, years)]
    for name, kind, f in LAYOUT:
        if kind == "gap":
            out.append(f"<tr class='gap'><td colspan='{len(years) + 2}'></td></tr>")
            continue
        vals, series = T.loc[name], _series_of(name, title)
        label = SHORT.get(name, name) if compact else LABEL[name]
        cells = "".join(_cell(vals[y], y, _fmt(vals[y], f),
                              ("fc " if is_est(y) else "") + ("neg" if kind == "bal" and pd.notna(vals[y]) and vals[y] < 0 else ""),
                              LABEL[name], hist.get((series, y)) if series and (series != "Stock" or ystart(y) <= ystart(ANCHOR)) else None)
                        for y in years)
        out.append(f"<tr class='{kind}'><td class='lbl'>{label}</td>{cells}<td class='spark-td'>{_spark(name, vals, years, kind, f, LABEL[name])}</td></tr>")
    return "".join(out)


def detail_html(S, years, ctys=("IC", "GH")) -> str:
    """Ivory Coast / Ghana: how each tree crop becomes the statistical crop (Trend + revision dots like the balance)."""
    hist = cell_history()
    out = []
    for cty, cname in COUNTRY.items():
        if cty not in ctys:
            continue
        out.append(_head(cname, years, "Tree → statistical crop · k tonnes"))
        for part, held in (("Main", "Held to mid"), ("Mid", "Held to main")):
            rows = [("Tree", _row(S, f"{cty} {part} Tree", years), "b", f"{cty} {part} Tree"),
                    ("Carry-in", _row(S, f"{cty} {part} Carry-in", years), "", f"{cty} {part} Carry-in"),
                    ("Smuggling GH" if cty == "IC" else "Smuggling IC (= − IC)", adj(S, years, cty, part, "Smuggling GH"), "",
                     f"{cty} {part} Smuggling GH" if cty == "IC" else None),
                    ("Smuggling other", _row(S, f"{cty} {part} Smuggling Other", years), "", f"{cty} {part} Smuggling Other"),
                    (held, _row(S, f"{cty} {part} Held", years), "", f"{cty} {part} Held"),
                    ("Stat crop", crop(S, years, cty, part, "Statistical"), "bal", None)]
            for lab, vals, kind, series in rows:
                label = f"{part} · {lab}" if lab == "Tree" else lab
                cells = "".join(_cell(vals[y], y, fnum(vals[y], 0),
                                      ("fc " if is_est(y) else "") + ("neg" if pd.notna(vals[y]) and vals[y] < 0 and kind != "b" else ""),
                                      f"{cname} {label}", hist.get((series, y)) if series else None) for y in years)
                pairs = [(y, vals[y]) for y in years]
                spark = (snd.sparkline(pairs, f"{cname} {label}", "growth") if kind in ("b", "bal")
                         else snd.sparkline_balance(pairs, f"{cname} {label}"))         # adjustments: red / green bars
                out.append(f"<tr class='{'b' if kind else 'soft'}'><td class='lbl'>{label}</td>{cells}<td class='spark-td'>{spark}</td></tr>")
        tree = crop(S, years, cty, "Main", "Botanical") + crop(S, years, cty, "Mid", "Botanical")
        stat = crop(S, years, cty, "Main", "Statistical") + crop(S, years, cty, "Mid", "Statistical")
        for lab, vals in (("Total tree", tree), ("Total stat", stat)):
            cells = "".join(f"<td class='{'fc' if is_est(y) else ''}'>{fnum(vals[y], 0)}</td>" for y in years)
            out.append(f"<tr class='bal'><td class='lbl'>{lab}</td>{cells}<td class='spark-td'>"
                       f"{snd.sparkline([(y, vals[y]) for y in years], f'{cname} {lab}', 'growth')}</td></tr>")
        out.append(f"<tr class='gap'><td colspan='{len(years) + 2}'></td></tr>")
    return "".join(out)


def render():
    st.markdown(snd.CSS, unsafe_allow_html=True)
    S, years = load()
    shown = years[-7:] if st.session_state.get("yrs_span", "Last 7") == "Last 7" else years   # stock still rolls over all years
    # one table at a time: page switch on the left, crop basis on the right (SnD page only)
    left, right = st.columns([3, 1], vertical_alignment="center")
    page = left.radio("Page", ["Cocoa SnD", "IC & GH detail"], horizontal=True, key="co_page", label_visibility="collapsed")
    with right.container(key="mode_nav"):
        mode = theme.mode_switch("co_mode")
    if mode == "Edit":
        part = "snd" if page == "Cocoa SnD" else "detail"
        title = "Edit Cocoa SnD" if part == "snd" else "Edit IC & GH detail"
        edit_view(S, years, part, title)
        return
    if page == "Cocoa SnD":
        # Botanical and Statistical side by side, compact
        st.markdown("<style>table.snd.cmp td, table.snd.cmp th.y { padding: 3px 6px !important; font-size: 11px !important; }"
                    "table.snd.cmp td.lbl { white-space: nowrap; } .snd-wrap.cmp { padding: 6px 8px 8px; }</style>"
                    "<div class='snd-head'><span class='t'>Cocoa SnD</span></div>", unsafe_allow_html=True)
        for col, basis in zip(st.columns(2, gap="small"), ("Botanical", "Statistical")):
            col.markdown(f"<div class='snd-wrap cmp'><table class='snd cmp'>{table_html(basis, balance(S, years, basis), shown, compact=True)}"
                         "</table></div>", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:4px;font-size:10.5px;font-style:italic;color:#64748b'>"
                    f"Tot = Σorig×0.99 · SnD = Tot−Grind · Stk typed ≤{ANCHOR[2:]}, then prev+SnD · Stat = Tree+CI+Smug+Held</div>",
                    unsafe_allow_html=True)
    else:
        st.markdown("<div class='snd-head'><span class='t'>Ivory Coast & Ghana crop detail</span></div>", unsafe_allow_html=True)
        pair = "".join(f"<div class='snd-wrap cmp'><table class='snd cmp'>{detail_html(S, shown, (c,))}</table></div>" for c in ("IC", "GH"))
        import tableedit
        tableedit.editable_table(f"<div class='co-pair'>{pair}</div>", tableedit.css_of(snd.CSS), "co_tbl", st.session_state.get("co_epoch", 0), editable=False, red=False,
                                 edits=st.session_state.get("co_tbl"))   # same frame as Edit (detail page)   # same frame as Edit


# ── Edit mode ─────────────────────────────────────────────────────────────────
# Every input is one series in cocoa_snd.csv, so the IC & GH detail and the main table share them: the Tree you type
# here is the IC/GH Main/Mid row of the balance. Saves are GitHub commits on the data branch (one per Save), which is
# also the revision log.
INPUTS = ([f"{c} {p} {k}" for c in ("IC", "GH") for p in ("Main", "Mid") for k in ["Tree"] + ADJ]
          + [c for c, _ in OTHERS] + ["Grind", "Stock"])


def _apply(S, changes):
    S2 = S.copy()
    for s, y, _o, n in changes:
        if s not in S2.index:
            S2.loc[s] = np.nan
        S2.loc[s, y] = np.nan if n is None else n
    return S2


def _editable(series, y) -> bool:
    return series != "Stock" or ystart(y) <= ystart(ANCHOR)          # stock is typed only up to the anchor year


def edit_html(S, years, edit, part="snd") -> str:
    """part: "snd" = tree crops, other origins, grind, stock; "detail" = IC / GH tree, adjustments and stat crop."""
    """One table holding every input (editable cells) and the numbers they drive (calculated cells)."""
    allrows = edit.get("all")
    ncol = len(years) + 2                                         # + Trend

    def head(title, sub="Oct–Sep · k tonnes"):
        return (f"<tr class='comm'><th colspan='{ncol}'>{title}<span class='crop'>{sub}</span></th></tr>"
                "<tr><th class='y first'></th>" + "".join(f"<th class='y{' fc' if is_est(y) else ''}'>{y[2:]}{'*' if is_est(y) else ''}</th>"
                                                         for y in years) + "<th class='y spark-h'>Trend</th></tr>")

    def row(label, vals, kind="", series=None, f=0, always=False, bars=False):
        if not allrows and series is None and not always:
            return ""
        cells = ""
        for y in years:
            v = vals[y]
            cls = ("fc " if is_est(y) else "") + ("neg " if kind == "bal" and pd.notna(v) and v < 0 else "")
            attrs = ""
            if series and _editable(series, y):
                k = f"{series}|{y}"
                b = edit["base"].get(k)
                cls += "ed" + (" chg" if k in edit["changed"] else "")
                attrs = f" data-k='{k}' data-base='{'' if b is None or pd.isna(b) else b}'"
            cells += f"<td class='{cls.strip()}'{attrs}>{_fmt(v, f)}</td>"
        pairs = [(y, vals[y]) for y in years]
        spark = (snd.sparkline_balance(pairs, label) if bars or kind == "bal"           # adjustments / balances: red-green bars
                 else snd.sparkline(pairs, label, "plain" if f in ("p0", "p1") else "growth"))
        return f"<tr class='{kind}'><td class='lbl'>{label}</td>{cells}<td class='spark-td'>{spark}</td></tr>"

    out, pair = [], ""
    if part == "detail":
        for cty, cname in COUNTRY.items():
            out = [head(cname, "Tree → statistical crop · k tonnes")]
            for crp, held in (("Main", "Held to mid"), ("Mid", "Held to main")):
                out.append(row(f"{crp} · Tree", _row(S, f"{cty} {crp} Tree", years), "b", f"{cty} {crp} Tree"))
                for k, lab in (("Carry-in", "Carry-in"), ("Smuggling GH", "Smuggling GH"), ("Smuggling Other", "Smuggling other"), ("Held", held)):
                    if cty == "GH" and k == "Smuggling GH":           # mirror of Ivory Coast: shown, not typed
                        out.append(row("Smuggling IC (= − IC)", adj(S, years, cty, crp, k), "soft", always=True, bars=True))
                    else:
                        out.append(row(lab, _row(S, f"{cty} {crp} {k}", years), "", f"{cty} {crp} {k}", bars=True))
                out.append(row(f"{crp} · Stat crop", crop(S, years, cty, crp, "Statistical"), "bal", always=True))
            pair += f"<div class='snd-wrap cmp'><table class='snd cmp'>{''.join(out)}</table></div>"
        out = []                                                  # the Balance (all rows) goes full width below the pair
    else:
        out.append(head("Origins, grind & stock"))
        for cty, cname in COUNTRY.items():
            for crp in ("Main", "Mid"):
                out.append(row(f"{cname} {crp.lower()} (tree)", _row(S, f"{cty} {crp} Tree", years), "", f"{cty} {crp} Tree"))
        for code, name in OTHERS:
            out.append(row(name, _row(S, code, years), "", code))
        out.append(row("Grind", _row(S, "Grind", years), "b", "Grind"))
        out.append(row(f"Stock (typed to {ANCHOR[2:]})", _row(S, "Stock", years), "", "Stock"))
    if allrows:
        if out:
            out.append(f"<tr class='gap'><td colspan='{ncol}'></td></tr>")
        out.append(head("Balance"))
        for basis in ("Botanical", "Statistical"):
            T = balance(S, years, basis)
            b = basis[:3] + "."
            out += [row(f"Total ×0.99 ({b})", T.loc["Total"], "b"), row(f"SnD ({b})", T.loc["SnD"], "bal"),
                    row(f"Stock ({b})", T.loc["Stock proxy"], ""), row(f"STU ({b})", T.loc["STU"], "soft", f="p1")]
    full = f"<div class='snd-wrap'><table class='snd'>{''.join(out)}</table></div>" if out else ""
    return (f"<div class='co-pair'>{pair}</div>" if pair else "") + full


def _show(v):
    return "" if v is None or pd.isna(v) else f"{v:g}"


def _save(changes, reason=""):
    lines = [f"{s} {y}: {_show(o) or '-'} -> {_show(n) or '-'}" for s, y, o, n in changes]
    reason = snd.clean_reason(reason)
    msg = f"Cocoa SnD | {len(changes)} change(s)" + (f" | reason: {reason}" if reason else "") + "\n\n" + "\n".join(lines)
    order = {s: i for i, s in enumerate(INPUTS)}

    def apply(text):
        d = pd.read_csv(io.StringIO(text))
        for s, y, _o, n in changes:
            d = d[~((d["series"] == s) & (d["year"] == y))]
            if n is not None:
                d = pd.concat([d, pd.DataFrame([{"series": s, "year": y, "value": n}])], ignore_index=True)
        d["_o"], d["_y"] = d["series"].map(order).fillna(99), d["year"].map(ystart)
        d = d.sort_values(["_o", "_y"]).drop(columns=["_o", "_y"])
        return d.to_csv(index=False, lineterminator="\n"), None
    new_text, _ = gh.commit(CSV_PATH, apply, msg)
    with open(CSV, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)
    load.clear()
    cell_history.clear()


def _undo():
    st.session_state.pop("co_new_year", None)
    st.session_state["co_epoch"] = st.session_state.get("co_epoch", 0) + 1
    st.session_state["_co_edits"] = {}
    try:
        st.session_state["co_tbl"] = {}
    except Exception:
        pass


def edit_view(S, years, part="snd", title="Edit Cocoa SnD"):
    import tableedit
    editable = gh.enabled()
    epoch = st.session_state.setdefault("co_epoch", 0)
    edits = st.session_state.get("co_tbl")
    if edits is None:
        edits = st.session_state.get("_co_edits", {})
    base = {f"{s}|{y}": float(S.loc[s, y]) for s in S.index for y in years if pd.notna(S.loc[s, y])}
    nxt = snd.next_year(years[-1])
    extra = st.session_state.get("co_new_year")                # "+ Crop year": a blank column to the right, saved once filled
    if extra:
        years = years + [extra]
        S = S.reindex(columns=years)
    changes = [(k.split("|")[0], k.split("|")[1], base.get(k), (None if v is None else float(v))) for k, v in edits.items()]
    allrows = not st.session_state.get("rows_only", False)
    E = dict(base=base, changed=set(edits), all=allrows)
    table = edit_html(_apply(S, changes), years, E, part)
    if changes:                                                  # tint every calculated cell the unsaved edits move
        table = tableedit.mark_limits(tableedit.mark_moved(table, edit_html(S, years, E, part)))
    ctrl = st.container()
    ctrl.markdown(f"<div class='snd-head'><span class='t edit'>{title}</span></div>", unsafe_allow_html=True)   # same title row as View
    tableedit.editable_table(table, tableedit.css_of(snd.CSS), "co_tbl", epoch, editable, edits)
    st.session_state["_co_edits"] = dict(edits)
    st.markdown("<div class='card-desc' style='margin:4px 0 0'>Stat crop = Tree + carry-in + smuggling + held · Total = origins × 0.99 · "
                f"SnD = Total − Grind · Stock typed to {ANCHOR[2:]}, then previous stock + SnD.</div>", unsafe_allow_html=True)
    if not editable:
        ctrl.markdown("<div class='card-desc'>Read-only: add github_token in Secrets to edit.</div>", unsafe_allow_html=True)
        return
    n = len(changes)
    bad = any(c[3] is not None and c[3] < 0 and not any(a in c[0] for a in ADJ) for c in changes)   # adjustments may be negative
    if bad:
        ctrl.error("Crops, grind and stock cannot be negative.")
    # pending edits -> a slim bar floats at the bottom of the screen; nothing pending -> it is hidden
    bar = st.container(horizontal=True, vertical_alignment="center", gap="small", key="edit_bar" if n else "edit_bar_idle")
    bar.markdown(f"<span class='eb-n'>{n} unsaved change{'s' if n != 1 else ''}</span>", unsafe_allow_html=True)
    reason = bar.text_input("Reason", key=f"co_reason_{epoch}", placeholder="Reason for Change...", width=320,
                            label_visibility="collapsed", max_chars=140, disabled=not n)
    bar.button("Undo", disabled=not n, width="content", key="co_undo", on_click=_undo)
    save = bar.button("Save" + (f" · {n}" if n else ""), type="primary", disabled=(not n) or bad, width="content", key="co_save")
    st.sidebar.button("Add a Crop Year", key="co_addyr", disabled=bool(extra), width="content",
               on_click=lambda: st.session_state.__setitem__("co_new_year", nxt))
    if save:
        try:
            with st.spinner("Saving..."):
                _save(changes, reason)
        except Exception as ex:
            ctrl.error(f"GitHub save failed: {ex}")
        else:
            _undo()
            st.toast(f"Saved {n} change(s).")
            st.rerun()


# ── Revisions ─────────────────────────────────────────────────────────────────
_LINE = re.compile(r"^(.+) (\d{4}/\d{2}): (.*) -> (.*)$")
_WHY = re.compile(r"\| reason: (.*)$")
HIDDEN = ("revert of ", "deleted ")


def _v(t):
    t = t.strip()
    return np.nan if t in ("", "-") else float(t)


def _revision_rows() -> pd.DataFrame:
    out = []
    for ts, msg in gh.history(CSV_PATH):
        first, _, body = msg.partition("\n")
        if not first.startswith("Cocoa SnD |"):
            continue
        why = _WHY.search(first)
        why = why.group(1).strip() if why else ""
        for ln in body.splitlines():
            m = _LINE.match(ln.strip())
            if m:
                s, y, o, nv = m.groups()
                grp = COUNTRY.get(s.split(" ")[0], "Other")
                out.append((pd.Timestamp(ts), grp, s, y, _v(o), _v(nv), np.nan, why))
    return pd.DataFrame(out, columns=["when", "group", "item", "year", "old", "new", "effect", "reason"])


def revisions_page():
    import revisions as rvmod
    st.markdown(snd.CSS + "<style>.rv-row { font-size: 12.5px; color: #1a1a2e; padding-top: 7px; } .rv-row.m { color: #8a94a8; } "
                ".rv-row.g { color: #0a2463; font-weight: 600; }</style>", unsafe_allow_html=True)
    st.markdown("<div class='snd-head'><span class='t'>Cocoa revisions</span></div>", unsafe_allow_html=True)
    if not gh.enabled():
        st.markdown("<div class='card-desc'>Add github_token in Secrets to see the revision log.</div>", unsafe_allow_html=True)
        return
    try:
        rv = _revision_rows()
    except Exception as ex:
        st.markdown(f"<div class='card-desc'>Not available: {ex}</div>", unsafe_allow_html=True)
        return
    rv = rvmod.visible(rv)
    if rv.empty:
        st.markdown("<div class='card-desc'>No revisions saved yet.</div>", unsafe_allow_html=True)
        return
    with st.container(border=True):
        c1, c2, _ = st.columns([1.2, 2, 5], vertical_alignment="bottom")
        ys = sorted(rv["year"].unique(), key=ystart)
        year = c1.selectbox("Crop year", ys, index=len(ys) - 1, key="co_rv_year")
        mode = c2.radio("Show", ["Change vs first estimate", "Level"], horizontal=True, key="co_rv_mode")
        st.plotly_chart(rvmod.revision_lines(rv[rv["year"] == year], mode == "Level", False), width="stretch", key="co_rv_lines")
    real = rv.sort_values("when", ascending=False).head(30)
    st.markdown("<div class='snd-bar' style='margin-top:14px'>Saved revisions</div>"
                "<div class='card-desc'>Delete puts that save's numbers back and removes it from the log.</div>", unsafe_allow_html=True)
    for ts, grp in real.groupby("when", sort=False):
        why = grp["reason"].iloc[0]
        c = st.columns([1.3, 4.2, 2.6, 0.8], vertical_alignment="center")
        c[0].markdown(f"<div class='rv-row'><b>{ts:%a %d %b %Y}</b><br><span style='color:#8a94a8;font-size:11px'>{ts:%H:%M}</span></div>",
                      unsafe_allow_html=True)
        items = ", ".join(f"{r.item} {r.year}: {fnum(r.old, 0) or '-'} &rarr; {fnum(r.new, 0) or '-'}" for r in grp.itertuples())
        c[1].markdown(f"<div class='rv-row g'>{items}</div>", unsafe_allow_html=True)
        c[2].markdown(f"<div class='rv-row m'>{html.escape(why) if why else 'no reason given'}</div>", unsafe_allow_html=True)
        if c[3].button("Delete", key=f"co_del_{ts.value}", width="stretch"):
            try:
                with st.spinner("Deleting..."):
                    _save([(r.item, r.year, r.new, None if pd.isna(r.old) else float(r.old)) for r in grp.itertuples()],
                          f"deleted {ts:%d %b %Y %H:%M:%S}")
            except Exception as ex:
                st.error(f"Delete failed: {ex}")
            else:
                st.toast("Deleted.")
                st.rerun()
