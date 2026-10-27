# Coffee Aggregated Exports

Aggregated coffee exports of the major origins, by crop year (Oct-Sep, Jul-Jun or calendar), in bags.

- **Arabica**: Brazil Arabica, Colombia, Honduras, Ethiopia, Peru
- **Robusta**: Vietnam, Brazil Robusta, Indonesia, Uganda, India

## Structure

- `Dashboard/app.py` - Streamlit app (run from the project root: `streamlit run Dashboard/app.py`). Sidebar: Entry, Exports.
  - `exports_view.py` - the Exports page: Monthly, Cumulative, Rolling, table, Full-year totals, YTD, with an optional projection.
    Filters: Type (Arabica / Robusta / Arabica + Robusta), Crop year, Years, Unit, Origin.
  - `data.py` - merges the data files into one monthly table per origin. `origins.py` - the ten origins and their source.
  - `ghstore.py` - saves Entry changes to GitHub (needs `github_token` in Secrets, see `.streamlit/secrets.toml.example`).
- `Database/history_exports.csv` - the starting history (from `Archives/data.xlsx`), origin / year / month / bags.
- `Database/manual_exports.csv` - numbers typed on the Entry page. They win over everything else.
- `Database/tdm_exports.parquet` - TDM monthly exports (tonnes) for the origin reporters.
- `Database/settings.json` - `tdm_share`: the fraction of TDM tonnage counted for Indonesia and India.
- `Automator/` - `tdm_exports_ingest.py` (TDM pull), `build_history.py` (one-off seed), `validate_data.py`, `refresh_tdm.bat`.
- `refresh_and_publish.bat` - pull entries, refresh TDM, validate, commit, push. `Archives/` is local only.

## Where each number comes from

Per origin and month: **manual entry > history > TDM**. TDM only fills Honduras, Ethiopia, Peru, Indonesia and India (see
`Dashboard/origins.py`), in months the history does not have, as tonnes / 0.06 x share. Honduras, Ethiopia and Peru are pure Arabica
(share 1.0). Indonesia and India export both types, so only a share of the tonnage counts as Robusta; the defaults
(0.76 and 0.92) come from the last 12 months of history against TDM and can be changed on the Entry page.
Brazil (both types), Colombia, Vietnam and Uganda are manual: TDM has no Arabica/Robusta split for Brazil,
Vietnam is not reliable in TDM and Uganda has no TDM data.

An aggregate only counts a month when every chosen origin has a number for it, so an origin that has not reported
yet never shows up as a drop. The full Arabica aggregate starts in Oct 2015 (Peru history starts then; Honduras comes from TDM before Oct 2017).

## Updating data

1. Type the latest months of the manual origins on the Entry page (saves itself to GitHub).
2. Run `refresh_and_publish.bat` to pull TDM and push (add `--full` for a full TDM re-pull).
