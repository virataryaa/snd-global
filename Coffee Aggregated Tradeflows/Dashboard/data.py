"""Exports data layer (no Streamlit): history + manual entries + TDM -> one monthly table per origin.

  Database/history_exports.csv   origin, year, month, bags   seed from Archives/data.xlsx (fixed)
  Database/manual_exports.csv    origin, year, month, bags   typed on the dashboard's Entry page (wins over everything)
  Database/tdm_exports.parquet   REPORTER, COMMODITY, YEAR, MONTH, QTY1, GBE   from Automator/tdm_exports_ingest.py
  Database/settings.json         {"tdm_share": {origin: fraction}}

Priority per origin and month: manual > history > TDM. TDM only fills origins whose source is "tdm" (origins.py),
in months the other two do not have, as green-bean-equivalent tonnes (green + roasted, no soluble) / 0.06 x the origin's share.
"""
import io
import json
from pathlib import Path

import pandas as pd

from origins import BAGS_PER_TONNE, BY_NAME, ORIGINS

DB = Path(__file__).resolve().parent.parent / "Database"
HISTORY, MANUAL, TDM, SETTINGS = (DB / "history_exports.csv", DB / "manual_exports.csv", DB / "tdm_exports.parquet",
                                  DB / "settings.json")
COLS = ["origin", "year", "month", "bags"]
HS_USED = {90111, 90112, 90121, 90122}   # 0901 green (11/12) and roasted (21/22); the ingest also pulls soluble 2101 11/12


def read_settings() -> dict:
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def shares() -> dict:
    """TDM share per tdm origin: settings.json over the origins.py default."""
    over = read_settings().get("tdm_share", {})
    return {o["name"]: float(over.get(o["name"], o.get("share", 1.0))) for o in ORIGINS if o["source"] == "tdm"}


TEXT = None   # optional hook path -> text | None; the dashboard points it at the GitHub data branch for MANUAL


def _read(path) -> pd.DataFrame:
    try:
        text = TEXT(path) if TEXT else None
        d = pd.read_csv(io.StringIO(text)) if text is not None else pd.read_csv(path)
    except (OSError, ValueError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=COLS)
    d = d[COLS].dropna(subset=["bags"])
    d["year"], d["month"] = d["year"].astype(int), d["month"].astype(int)
    d["bags"] = d["bags"].astype(float)
    return d[d["bags"] > 0]


def tdm_bags() -> pd.DataFrame:
    """TDM months as bags for the tdm origins (origin, year, month, bags)."""
    if not TDM.exists():
        return pd.DataFrame(columns=COLS)
    t = pd.read_parquet(TDM, columns=["REPORTER", "COMMODITY", "YEAR", "MONTH", "GBE"])   # green-bean equivalent
    t = t[t["COMMODITY"].astype(int).isin(HS_USED)]               # green + roasted only, soluble (2101) left out
    t = t.groupby(["REPORTER", "YEAR", "MONTH"], as_index=False)["GBE"].sum()
    sh = shares()
    parts = []
    for o in ORIGINS:
        if o["source"] != "tdm":
            continue
        # TDM labels the reporter by country name; origins.py holds the code, so match on the name list below
        x = t[t["REPORTER"] == REPORTER_NAME[o["reporter"]]].copy()
        x["origin"] = o["name"]
        x["bags"] = x["GBE"] * BAGS_PER_TONNE * sh[o["name"]]
        parts.append(x.rename(columns={"YEAR": "year", "MONTH": "month"})[COLS])
    out = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=COLS)
    return out[out["bags"] > 0]


REPORTER_NAME = {"BR": "Brazil", "CO": "Colombia", "HN": "Honduras", "ET": "Ethiopia", "PE": "Peru", "VN": "Vietnam",
                 "ID": "Indonesia", "UG": "Uganda", "IN": "India"}


def combine() -> pd.DataFrame:
    """origin, year, month, bags, source ('manual' | 'history' | 'tdm'), one row per origin and month."""
    frames = [(_read(MANUAL), "manual"), (_read(HISTORY), "history"), (tdm_bags(), "tdm")]
    out = pd.concat([f.assign(source=s) for f, s in frames], ignore_index=True)
    out["_rank"] = out["source"].map({"manual": 0, "history": 1, "tdm": 2})
    out = out.sort_values("_rank").drop_duplicates(["origin", "year", "month"], keep="first").drop(columns="_rank")
    order = {n: i for i, n in enumerate(BY_NAME)}
    return out.assign(_o=out["origin"].map(order)).sort_values(["_o", "year", "month"]).drop(columns="_o").reset_index(drop=True)


def complete_months(df: pd.DataFrame, origins: list) -> pd.DataFrame:
    """Rows of the chosen origins, kept only for (type, month)s where EVERY chosen origin of that type has a value, so a
    month one origin has not reported yet never shows as a drop. Adds the coffee type."""
    d = df[df["origin"].isin(origins)].copy()
    d["type"] = d["origin"].map(lambda n: BY_NAME[n]["type"])
    want = pd.Series([BY_NAME[n]["type"] for n in origins]).value_counts()          # origins chosen per type
    have = d.groupby(["type", "year", "month"])["origin"].transform("nunique")
    return d[have == d["type"].map(want)].reset_index(drop=True)
