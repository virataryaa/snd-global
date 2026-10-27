"""One-off seed: Archives/data.xlsx (one sheet per origin, rows = Oct-Sep crop years, columns Oct..Sep, bags)
-> Database/history_exports.csv (origin, year, month, bags).

Cells that are #N/A or empty are dropped (no data). From now on new months come from TDM (tdm_exports_ingest.py) or
the dashboard's Entry page (Database/manual_exports.csv); re-run this only to re-seed the history.
"""
import sys
from pathlib import Path

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "Dashboard"))
from origins import NAMES  # noqa: E402

SRC = ROOT / "Archives" / "data.xlsx"
OUT = ROOT / "Database" / "history_exports.csv"
MON = {"Oct": 10, "Nov": 11, "Dec": 12, "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9}


def main():
    wb = openpyxl.load_workbook(SRC, data_only=True)
    rows = []
    for name in NAMES:
        ws = wb[name]
        data = list(ws.iter_rows(values_only=True))
        header = data[0][1:]
        for r in data[1:]:
            if not r[0]:
                continue
            y0 = 2000 + int(str(r[0])[:2])                       # "14/15" -> Oct 2014 .. Sep 2015
            for mon, v in zip(header, r[1:]):
                if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
                    m = MON[mon]
                    rows.append((name, y0 if m >= 10 else y0 + 1, m, round(float(v))))
    out = pd.DataFrame(rows, columns=["origin", "year", "month", "bags"])
    out["_o"] = out["origin"].map({n: i for i, n in enumerate(NAMES)})
    out = out.sort_values(["_o", "year", "month"]).drop(columns="_o")
    out.to_csv(OUT, index=False, lineterminator="\n")
    last = out.assign(d=out.year * 100 + out.month).groupby("origin").agg(first=("d", "min"), last=("d", "max"), n=("bags", "size"))
    print(f"wrote {OUT}  rows={len(out)}")
    print(last.loc[NAMES].to_string())


if __name__ == "__main__":
    main()
