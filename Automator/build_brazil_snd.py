"""One-off seed: the 'Brazil internal SnD' sheet of Archives/coffee.xlsx -> the Database/ files the Brazil page reads.

  Database/brazil_snd.csv     series, year, value   the INPUTS of the three blocks (hard-coded cells only; formula cells are recalculated)
  Database/brazil_agri.csv    table, year, carry_in, production, int_use, exports, stu   the AgriAcies-format tables at the bottom of the sheet
  Database/brazil_meta.json   the opening closing stocks (first year) of Arabica and Conillon

Rules the sheet follows, which the dashboard repeats:
  * Brazil production comes from the 'Coffee SnD ETG' sheet (Brazil rows) unless this sheet has its own number for the year.
  * Consumption is typed up to 2020/21; from 2021/22 it is (1 - Conillon demand %) or the Conillon demand % times the overall
    Brazil consumption, which is typed from 2020/21.
Usage:  python Automator/build_brazil_snd.py [path/to/coffee.xlsx]
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "Archives" / "coffee.xlsx"
DB = ROOT / "Database"
SHEET = "Brazil internal SnD"
FIRST_COL, LAST_COL = 2, 15                         # B..O = 14/15 .. 27/28
# series name -> row on the sheet (inputs only)
ROWS = {
    "Arabica production": 4, "Arabica exports": 5, "Arabica consumption": 6,
    "Conillon production": 20, "Green exports": 21, "Soluble exports": 22, "Conillon consumption": 23,
    "Conillon demand %": 24, "Overall consumption": 35,
}
ETG_FIRST_YEAR = "2016/17"                           # the ETG sheet starts here; earlier production has to be typed
OPENING = {"Arabica": 9, "Conillon": 26}            # row of the closing stock whose first column is an input


def clean(v) -> str:
    """'14/15*' -> '2014/15' (the long label the SnD ETG sheet and the dashboard use)."""
    t = str(v).replace("*", "").strip()
    return f"20{t}" if len(t) == 5 else t


def main():
    try:
        tmp = Path(tempfile.gettempdir()) / "brazil_snd_seed.xlsx"
        shutil.copy(SRC, tmp)
    except PermissionError:
        sys.exit(f"{SRC} is locked (open in Excel?). Close it, or pass a copy: python Automator/build_brazil_snd.py <copy.xlsx>")
    wf = openpyxl.load_workbook(tmp, data_only=False)[SHEET]
    wv = openpyxl.load_workbook(tmp, data_only=True)[SHEET]
    years = [clean(wv.cell(2, c).value) for c in range(FIRST_COL, LAST_COL + 1)]
    rows = []
    for name, r in ROWS.items():
        for c in range(FIRST_COL, LAST_COL + 1):
            f, v = wf.cell(r, c).value, wv.cell(r, c).value
            is_formula = isinstance(f, str) and f.startswith("=")
            if is_formula or not isinstance(v, (int, float)):
                continue
            y = years[c - FIRST_COL]
            # production rows that are typed in the years the ETG sheet also covers are the same numbers: use the link instead
            if name == "Arabica production" and int(y[:4]) >= 2016:
                continue
            rows.append((name, y, float(v)))
    inp = pd.DataFrame(rows, columns=["series", "year", "value"])
    inp.to_csv(DB / "brazil_snd.csv", index=False, lineterminator="\n")
    meta = {"opening": {k: float(wv.cell(r, FIRST_COL).value) for k, r in OPENING.items()}}
    (DB / "brazil_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    # AgriAcies-format tables: Arabica Jul-Jun (A..I), Robusta Apr-Mar (A..I, rows 80..96), Total Jul-Jun (K..S, rows 60..76)
    agri = []

    def val(r, c):
        v = wv.cell(r, c).value
        return float(v) if isinstance(v, (int, float)) else None

    def formula(r, c):
        f = wf.cell(r, c).value
        return isinstance(f, str) and f.startswith("=")

    for table, first, last, c0 in (("Arabica Jul-Jun", 60, 76, 1), ("Robusta Apr-Mar", 80, 96, 1), ("Total Jul-Jun", 60, 76, 11)):
        for r in range(first, last + 1):
            y = wv.cell(r, c0).value
            if not y:
                continue
            carry_in = val(r, c0 + 1) if not formula(r, c0 + 1) else None
            agri.append((table, clean(y), carry_in, val(r, c0 + 2), val(r, c0 + 4), val(r, c0 + 6),
                         val(r, c0 + 8) if not formula(r, c0 + 8) else None))
    for c in range(24, 33):                                          # the small side table: AgriAcies Brazil production and carry-in stocks
        y = wv.cell(74, c).value
        if y:
            agri.append(("AgriAcies Brazil", clean(y), val(76, c), val(75, c), None, None, None))
    pd.DataFrame(agri, columns=["table", "year", "carry_in", "production", "int_use", "exports", "stu"]).to_csv(
        DB / "brazil_agri.csv", index=False, lineterminator="\n")
    print(f"wrote {len(inp)} inputs ({inp.series.nunique()} series, {years[0]}..{years[-1]}), {len(agri)} AgriAcies rows, opening {meta['opening']}")


if __name__ == "__main__":
    main()
