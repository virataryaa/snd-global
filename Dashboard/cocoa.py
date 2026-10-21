"""Cocoa SnD (Oct–Sep, k tonnes): Botanical and Statistical balances, plus the Ivory Coast / Ghana crop detail.

Inputs live in Database/cocoa_snd.csv (series, year, value). Ivory Coast (IC) and Ghana (GH) each have a Main and a Mid crop:
  Botanical crop = Tree.  Statistical crop = Tree + Carry-in + Smuggling GH + Smuggling Other + Held (to Mid / to Main).
Total = sum of origins x 0.99 · SnD = Total - Grind · Stock is typed up to 20/21 and from then on = previous stock + SnD.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import snd
from snd import fnum, fpct, ystart

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "Database" / "cocoa_snd.csv"
LOSS = 0.99                          # fixed haircut on the origin sum
ANCHOR = "2020/21"                   # last typed stock year; later years roll
ADJ = ["Carry-in", "Smuggling GH", "Smuggling Other", "Held"]
OTHERS = [("EC", "Ecuador"), ("NIG", "Nigeria"), ("CAM", "Cameroon"), ("INDO", "Indonesia"), ("BRAZ", "Brazil"),
          ("PERU", "Peru"), ("ROW", "Rest of world")]
COUNTRY = {"IC": "Ivory Coast", "GH": "Ghana"}


@st.cache_data(ttl=600)
def load():
    df = pd.read_csv(CSV)
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


def crop(S, years, cty, part, basis):
    tree = _row(S, f"{cty} {part} Tree", years)
    if basis == "Botanical":
        return tree
    return tree + sum(_row(S, f"{cty} {part} {k}", years).fillna(0) for k in ADJ)


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


def _head(title, years, sub="Oct–Sep · k tonnes"):
    ncol = len(years) + 2
    return (f"<tr class='comm'><th colspan='{ncol}'>{title}<span class='crop'>{sub}</span></th></tr>"
            "<tr><th class='y first'></th>" + "".join(f"<th class='y{' fc' if is_est(y) else ''}'>{y[2:]}{'*' if is_est(y) else ''}</th>"
                                                     for y in years) + "<th class='y spark-h'>Trend</th></tr>")


def table_html(title, T, years) -> str:
    out = [_head(title, years)]
    for name, kind, f in LAYOUT:
        if kind == "gap":
            out.append(f"<tr class='gap'><td colspan='{len(years) + 2}'></td></tr>")
            continue
        vals = T.loc[name]
        cells = "".join(f"<td class='{'fc ' if is_est(y) else ''}{'neg' if kind == 'bal' and pd.notna(vals[y]) and vals[y] < 0 else ''}'>"
                        f"{_fmt(vals[y], f)}</td>" for y in years)
        pairs = [(y, vals[y]) for y in years]
        spark = snd.sparkline_balance(pairs, LABEL[name]) if kind == "bal" else snd.sparkline(pairs, LABEL[name], "plain" if f in ("p0", "p1") else "growth")
        out.append(f"<tr class='{kind}'><td class='lbl'>{LABEL[name]}</td>{cells}<td class='spark-td'>{spark}</td></tr>")
    return "".join(out)


def detail_html(S, years) -> str:
    """Ivory Coast / Ghana: how each tree crop becomes the statistical crop."""
    out = []
    for cty, cname in COUNTRY.items():
        out.append(_head(cname, years, "Tree → statistical crop · k tonnes"))
        for part, held in (("Main", "Held to mid"), ("Mid", "Held to main")):
            rows = [("Tree", _row(S, f"{cty} {part} Tree", years), "b"),
                    ("Carry-in", _row(S, f"{cty} {part} Carry-in", years), ""),
                    ("Smuggling GH", _row(S, f"{cty} {part} Smuggling GH", years), ""),
                    ("Smuggling other", _row(S, f"{cty} {part} Smuggling Other", years), ""),
                    (held, _row(S, f"{cty} {part} Held", years), ""),
                    ("Stat crop", crop(S, years, cty, part, "Statistical"), "bal")]
            for lab, vals, kind in rows:
                label = f"{part} · {lab}" if lab == "Tree" else lab
                cells = "".join(f"<td class='{'fc ' if is_est(y) else ''}{'neg' if pd.notna(vals[y]) and vals[y] < 0 and kind != 'b' else ''}'>"
                                f"{fnum(vals[y], 0)}</td>" for y in years)
                out.append(f"<tr class='{'b' if kind else 'soft'}'><td class='lbl'>{label}</td>{cells}<td class='spark-td'></td></tr>")
        tree = crop(S, years, cty, "Main", "Botanical") + crop(S, years, cty, "Mid", "Botanical")
        stat = crop(S, years, cty, "Main", "Statistical") + crop(S, years, cty, "Mid", "Statistical")
        for lab, vals in (("Total tree", tree), ("Total stat", stat)):
            cells = "".join(f"<td class='{'fc' if is_est(y) else ''}'>{fnum(vals[y], 0)}</td>" for y in years)
            out.append(f"<tr class='bal'><td class='lbl'>{lab}</td>{cells}<td class='spark-td'></td></tr>")
        out.append(f"<tr class='gap'><td colspan='{len(years) + 2}'></td></tr>")
    return "".join(out)


def render():
    st.markdown(snd.CSS, unsafe_allow_html=True)
    S, years = load()
    # one table at a time: page switch on the left, crop basis on the right (SnD page only)
    left, right = st.columns([3, 1], vertical_alignment="center")
    page = left.radio("Page", ["Cocoa SnD", "IC & GH detail"], horizontal=True, key="co_page", label_visibility="collapsed")
    if page == "Cocoa SnD":
        with right.container(key="co_basis_nav"):
            basis = st.radio("Basis", ["Botanical", "Statistical"], horizontal=True, key="co_basis", label_visibility="collapsed")
        st.markdown(f"<div class='snd-head'><span class='t'>Cocoa SnD · {basis}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='snd-wrap'><table class='snd'>{table_html(basis, balance(S, years, basis), years)}</table></div>",
                    unsafe_allow_html=True)
        st.markdown("<div class='card-desc' style='margin-top:6px'>Total = sum of origins × 0.99 · SnD = Total − Grind · "
                    f"Stock typed up to {ANCHOR[2:]}, then previous stock + SnD"
                    + (" · Statistical crop = Tree + carry-in + smuggling + held" if basis == "Statistical" else "") + ".</div>",
                    unsafe_allow_html=True)
    else:
        st.markdown("<div class='snd-head'><span class='t'>Ivory Coast & Ghana crop detail</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='snd-wrap'><table class='snd'>{detail_html(S, years)}</table></div>", unsafe_allow_html=True)
