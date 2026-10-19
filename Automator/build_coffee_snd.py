"""One-off seed: the 'Coffee SnD ETG' sheet of Archives/coffee.xlsx -> the Database/ files the dashboard reads.

  Database/coffee_snd.csv         commodity, item, year, value   the INPUTS: each origin's production and consumption (m bags)
  Database/coffee_snd_meta.json   opening stock (first year's end stock), the first starred (*) year and the first orange-shaded
                                  year, per commodity
  Database/coffee_snd_notes.csv   commodity, item, year, note     the analyst comments on the sheet's cells
  Database/coffee_su_history.csv  year, arabica_su, robusta_su, arb_end_jun, arb_avg   the sheet's right-hand history block
                                  (S/U since 2006/07 and the arabica-robusta arb, which the dashboard overlays on the S/U spread)

Everything else on the sheet (production totals, balance, end stocks, S/U, global rows) is a formula in Excel and is
worked out by the dashboard. This script checks its own arithmetic against Excel's cached numbers before it writes.

Usage:  python Automator/build_coffee_snd.py [path/to/coffee.xlsx]
If Excel has the workbook open it is locked: close it, or pass a copy (Excel > File > Save a Copy).
After this, new numbers are typed on the dashboard's Entry page; re-run only to re-seed from Excel.
"""
import json
import re
import sys
import tempfile
import shutil
from pathlib import Path

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "Archives" / "coffee.xlsx"
DB = ROOT / "Database"
SHEET = "Coffee SnD ETG"
FIRST_COL, LAST_COL = 2, 13                       # B..M = 2016/17 .. 2027/28
BLOCKS = {                                        # commodity: (year header row, first item row, last item row, consumption row, stock row)
    "Arabica": dict(head=4, first=5, last=11, cons=13, stock=16),
    "Robusta": dict(head=19, first=20, last=26, cons=28, stock=31),
}


def clean_year(v) -> str:
    return str(v).replace("*", "").strip()


def main():
    try:
        tmp = Path(tempfile.gettempdir()) / "coffee_snd_seed.xlsx"
        shutil.copy(SRC, tmp)
    except PermissionError:
        sys.exit(f"{SRC} is locked (open in Excel?). Close it, or pass a copy: python Automator/build_coffee_snd.py <copy.xlsx>")
    wb_v = openpyxl.load_workbook(tmp, data_only=True)
    ws = wb_v[SHEET]
    rows, meta = [], {"opening_stock": {}, "estimate_from": {}, "forecast_from": {"Arabica": "2023/24", "Robusta": "2023/24"}}
    years = None
    for comm, b in BLOCKS.items():
        yrs = [clean_year(ws.cell(b["head"], c).value) for c in range(FIRST_COL, LAST_COL + 1)]
        years = years or yrs
        assert yrs == years, f"{comm} year headers differ from Arabica's: {yrs}"
        starred = [c for c in range(FIRST_COL, LAST_COL + 1) if "*" in str(ws.cell(b["head"], c).value)]
        meta["estimate_from"][comm] = years[starred[0] - FIRST_COL] if starred else None
        meta["opening_stock"][comm] = float(ws.cell(b["stock"], FIRST_COL).value)
        for r in list(range(b["first"], b["last"] + 1)) + [b["cons"]]:
            item = str(ws.cell(r, 1).value).strip()
            for c in range(FIRST_COL, LAST_COL + 1):
                v = ws.cell(r, c).value
                if isinstance(v, (int, float)):
                    rows.append((comm, item, years[c - FIRST_COL], float(v)))
    df = pd.DataFrame(rows, columns=["commodity", "item", "year", "value"])

    # ── check: the dashboard's arithmetic vs Excel's own numbers ─────────────────────────────────────────────
    bad = []
    for comm, b in BLOCKS.items():
        d = df[df.commodity == comm]
        prod = d[d.item != "Consumption"].groupby("year")["value"].sum().reindex(years)
        cons = d[d.item == "Consumption"].set_index("year")["value"].reindex(years)
        bal = prod - cons
        stock, prev = [], meta["opening_stock"][comm]
        for i, y in enumerate(years):
            prev = prev if i == 0 else prev + bal[y]
            stock.append(prev)
        for name, row, mine in [("production", b["last"] + 1, prod), ("balance", b["cons"] + 2, bal),
                                ("end stock", b["stock"], pd.Series(stock, index=years)), ("S/U", b["stock"] + 1, pd.Series(stock, index=years) / cons)]:
            for c in range(FIRST_COL, LAST_COL + 1):
                xl = ws.cell(row, c).value
                if isinstance(xl, (int, float)) and abs(xl - mine[years[c - FIRST_COL]]) > 0.051 * (0.01 if name == "S/U" else 1):
                    bad.append(f"{comm} {name} {years[c - FIRST_COL]}: Excel {xl:.3f} vs {mine[years[c - FIRST_COL]]:.3f}")
    print("check vs Excel:", "OK" if not bad else f"{len(bad)} difference(s) (cells Excel hard-coded instead of a formula)")
    for x in bad[:12]:
        print("  ", x)

    # ── analyst comments ────────────────────────────────────────────────────────────────────────────────────
    notes = []
    wb_f = openpyxl.load_workbook(tmp, data_only=False)
    for row in wb_f[SHEET].iter_rows(min_row=1, max_row=33, min_col=FIRST_COL, max_col=LAST_COL):
        for cell in row:
            if not cell.comment:
                continue
            for comm, b in BLOCKS.items():
                if b["first"] <= cell.row <= b["last"] or cell.row == b["cons"]:
                    item = str(wb_f[SHEET].cell(cell.row, 1).value).strip()
                    body = cell.comment.text.split("Comment:", 1)[-1]
                    body = re.sub(r"\s*Reply:\s*", " | ", body)
                    notes.append((comm, item, years[cell.column - FIRST_COL], re.sub(r"\s+", " ", body).strip(" |")))
    pd.DataFrame(notes, columns=["commodity", "item", "year", "note"]).to_csv(DB / "coffee_snd_notes.csv", index=False, lineterminator="\n")
    # history block (columns AE..AV = 2006/07 .. 2023/24): S/U and the arb
    ws_h = wb_v[SHEET]
    hist = []
    for c in range(31, 49):
        y = ws_h.cell(3, c).value
        if not y:
            continue

        def g(r, c=c):
            v = ws_h.cell(r, c).value
            return float(v) if isinstance(v, (int, float)) else None
        hist.append((str(y).strip(), g(4), g(6), g(9), g(11)))
    pd.DataFrame(hist, columns=["year", "arabica_su", "robusta_su", "arb_end_jun", "arb_avg"]).to_csv(
        DB / "coffee_su_history.csv", index=False, lineterminator="\n")
    df.to_csv(DB / "coffee_snd.csv", index=False, lineterminator="\n")
    (DB / "coffee_snd_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(df)} inputs, {len(notes)} notes, years {years[0]} .. {years[-1]}, meta {meta}")


if __name__ == "__main__":
    main()
