"""
Hardmine - TDM coffee exports by origin (monthly, tonnes -> green bean equivalent)
=================================================================================
Pulls monthly coffee EXPORTS for the origin reporters (Brazil, Colombia, Honduras, Ethiopia, Peru, Vietnam,
Indonesia, Uganda, India), summed over partners and kept per HS code, with the green-bean-equivalent tonnage.
The dashboard turns GBE tonnes into 60 kg bags (x 1000/60) for the origins whose source is "tdm" (Dashboard/origins.py).

Requires TDM_API_KEY (env var, or a .env file at the project root - see .env.example).

Usage:
    python tdm_exports_ingest.py            # incremental: re-pull from January of the latest year in the file
    python tdm_exports_ingest.py --full     # full history from 201401

Saves to Database/tdm_exports.parquet (REPORTER, COMMODITY, YEAR, MONTH, QTY1, GBE).
"""
import argparse
import io
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S",
                    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_DIR / "tdm_exports_ingest.log", encoding="utf-8")])
log = logging.getLogger(__name__)

API_KEY = os.environ.get("TDM_API_KEY")
if not API_KEY:
    sys.exit("TDM_API_KEY is not set. Put it in a .env file at the project root (TDM_API_KEY=...) or set it as an environment variable.")
BASE_URL = "https://www1.tdmlogin.com/tdm/api/api.asp"

REPORTERS = "BR,CO,HN,ET,PE,VN,ID,UG,IN"
HS_CODES = ["090111", "090112", "090121", "090122", "210111", "210112"]
PERIOD_FULL_BEGIN = "201401"
PERIOD_END = "203012"
OUT_FILE = ROOT / "Database" / "tdm_exports.parquet"
COLUMNS = ["REPORTER", "PARTNER", "COMMODITY", "YEAR", "MONTH", "QTY1", "UNIT1"]
KEYS = ["REPORTER", "COMMODITY", "YEAR", "MONTH"]

GBE_MULTIPLIER = {90111: 1.00, 90112: 1.05, 90121: 1.19, 90122: 1.25, 210111: 2.60, 210112: 2.60}


def fetch(period_begin: str) -> pd.DataFrame:
    url = (f"{BASE_URL}?key={API_KEY}&flow=E&reporter={REPORTERS}&partners=all&periodBegin={period_begin}"
           f"&periodEnd={PERIOD_END}&hsCode={','.join(HS_CODES)}&levelDetail=6&frequency=M&separator=T"
           f"&aggregatePartners=Y&conv=1")
    log.info("Fetching TDM exports from %s ...", period_begin)
    resp = requests.get(url, timeout=300)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.content.decode("utf-16")), sep="\t", low_memory=False)
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"API response missing expected columns: {missing}")
    df = df[COLUMNS].copy()
    df = df[df["UNIT1"].astype(str).str.strip() == "T"]                     # tonnes lines only (not litres / value-only)
    df["QTY1"] = pd.to_numeric(df["QTY1"], errors="coerce")
    out = df.groupby(KEYS, as_index=False)["QTY1"].sum()                    # sum over partners and customs regimes
    out["GBE"] = out["QTY1"] * out["COMMODITY"].map(GBE_MULTIPLIER)
    log.info("  -> %d rows (reporter x HS x month)", len(out))
    return out


def main():
    ap = argparse.ArgumentParser(description="TDM coffee exports by origin")
    ap.add_argument("--full", action="store_true", help=f"full pull from {PERIOD_FULL_BEGIN}")
    args = ap.parse_args()
    log.info("=" * 60)
    log.info("TDM exports ingest  |  %s  |  %s", datetime.now().strftime("%Y-%m-%d %H:%M"), "FULL" if args.full else "INCREMENTAL")
    if args.full or not OUT_FILE.exists():
        begin = PERIOD_FULL_BEGIN
    else:
        old = pd.read_parquet(OUT_FILE, columns=["YEAR"])
        begin = f"{int(old['YEAR'].max())}01"
    new = fetch(begin)
    if new.empty:
        sys.exit("TDM returned no rows - existing file left untouched.")
    if OUT_FILE.exists() and not args.full:
        old = pd.read_parquet(OUT_FILE)
        keep = old[~old.set_index(KEYS).index.isin(new.set_index(KEYS).index)]    # new pull replaces the months it covers
        new = pd.concat([keep, new], ignore_index=True)
    new = new.sort_values(KEYS).reset_index(drop=True)
    new.to_parquet(OUT_FILE, index=False)
    g = new.groupby("REPORTER").apply(lambda d: d.YEAR.mul(100).add(d.MONTH).max(), include_groups=False)
    log.info("Saved -> %s  (%d rows)", OUT_FILE, len(new))
    log.info("Latest month per reporter (YYYYMM): %s", g.to_dict())
    log.info("=" * 60)


if __name__ == "__main__":
    main()
