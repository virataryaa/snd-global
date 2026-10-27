"""Sanity-checks the Database files before they get pushed.

Run standalone: python Automator/validate_data.py
Exit code 0 = safe to push. Exit code 1 = problems found, do not push.
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "Dashboard"))
from origins import NAMES  # noqa: E402

DB = ROOT / "Database"
COLS = ["origin", "year", "month", "bags"]
JUMP = 1.8            # a month this many times the usual level for that origin gets a warning


def check_bags(name: str, errors: list, warnings: list):
    path = DB / name
    try:
        df = pd.read_csv(path)
    except Exception as e:
        errors.append(f"{name}: cannot read - {e}")
        return
    if list(df.columns) != COLS:
        errors.append(f"{name}: columns must be {','.join(COLS)} - found {list(df.columns)}")
        return
    for i, r in df.iterrows():
        if r.origin not in NAMES:
            errors.append(f"{name} row {i + 2}: unknown origin {r.origin!r}")
        if not (pd.notna(r.year) and float(r.year).is_integer() and 2000 <= r.year <= 2035):
            errors.append(f"{name} row {i + 2}: bad year {r.year!r}")
        if not (pd.notna(r.month) and float(r.month).is_integer() and 1 <= r.month <= 12):
            errors.append(f"{name} row {i + 2}: bad month {r.month!r} (1-12)")
    bags = pd.to_numeric(df["bags"], errors="coerce")
    for i in df.index[bags.isna() | (bags <= 0)]:
        errors.append(f"{name} row {i + 2}: bags must be a positive number ({df.loc[i, 'bags']!r})")
    for k in df[df.duplicated(["origin", "year", "month"])][["origin", "year", "month"]].itertuples(index=False):
        errors.append(f"{name}: duplicate {k.origin} {int(k.year)}-{int(k.month):02d}")
    if errors:
        return
    for o, g in df.groupby("origin"):                                  # last 3 months vs the same month a year earlier
        g = g.assign(k=g.year * 12 + g.month).set_index("k")["bags"]
        for k in g.index[-3:]:
            prev = g.get(k - 12)
            if prev and (g[k] > JUMP * prev or g[k] < prev / JUMP):
                warnings.append(f"{name}: {o} {int((k - 1) // 12)}-{int((k - 1) % 12 + 1):02d} is {g[k] / prev:.1f}x the same month a year before")


def main():
    errors, warnings = [], []
    for name in ("history_exports.csv", "manual_exports.csv"):
        check_bags(name, errors, warnings)
    try:
        s = json.loads((DB / "settings.json").read_text(encoding="utf-8"))
        for o, v in s.get("tdm_share", {}).items():
            if o not in NAMES or not (0 < float(v) <= 1.5):
                errors.append(f"settings.json: tdm_share {o!r} = {v!r} is not valid")
    except Exception as e:
        errors.append(f"settings.json: {e}")
    try:
        t = pd.read_parquet(DB / "tdm_exports.parquet")
        if t.empty:
            errors.append("tdm_exports.parquet is empty")
    except Exception as e:
        errors.append(f"tdm_exports.parquet: {e}")
    if warnings:
        print("Warnings (won't block the push):")
        for w in warnings:
            print(f"  - {w}")
    if errors:
        print("FAIL - fix these before pushing:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("PASS - history, manual entries, settings and the TDM file look good.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
