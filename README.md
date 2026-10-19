# Global SnD

Supply and demand balances, starting with coffee: the "SnD ETG" table (Arabica, Robusta, Global), crop year Jul-Jun, million 60 kg bags.

## Structure

- `Dashboard/app.py` - Streamlit app (run from the project root: `streamlit run Dashboard/app.py`). Sidebar: Entry, Coffee.
  - `snd.py` - the Coffee page (the SnD table and three charts) and the Entry page. `ghstore.py` - saves Entry changes to GitHub
    (needs `github_token` in Secrets, see `.streamlit/secrets.toml.example`).
- `Database/coffee_snd.csv` - the inputs: each origin's production and the consumption, per crop year (commodity, item, year, value).
- `Database/coffee_snd_meta.json` - end stock of the first year (the starting point of the stock roll), per commodity.
- `Database/coffee_snd_notes.csv` - the analyst comments from the sheet's cells (shown as a purple corner, text on hover).
- `Database/coffee_su_history.csv` - the sheet's right-hand block: Arabica and Robusta S/U since 2006/07 and the arb (end June and Jul-Jun average).
- `Dashboard/analytics.py` - the Analytics section (see below).
- `Dashboard/brazil.py` + `Database/brazil_snd.csv`, `brazil_agri.csv`, `brazil_meta.json` - the Brazil internal SnD page (Arabica, Conillon, overall Brazil, and the AgriAcies-format tables), seeded by `Automator/build_brazil_snd.py` from the sheet "Brazil internal SnD".
- `Automator/build_coffee_snd.py` - one-off seed from `Archives/coffee.xlsx` (sheet "Coffee SnD ETG"). `Archives/` stays local.

## How it is worked out

Same as the Excel sheet: production = sum of the origins, balance = production - consumption, end stock = last year's end stock + balance,
S/U = end stock / consumption, global = Arabica + Robusta, 2 year cycle = balance of the two years in a pair (2016/18, 2018/20, ...).
Only the inputs are stored; everything else is calculated, so a changed origin number flows through the whole table.

## Updating

Type changes on the Entry page (each commodity: origins, consumption, plus the first-year end stock).
It saves to GitHub and the app reloads. Old Excel hard-codes are not copied: for example the sheet's 2027/28 Arabica production was typed as
98.4 while its origins add up to 95.2, so the dashboard shows 95.2.

## Analytics

Balance bridge (what moved the balance, origin by origin), Stocks to use (today's S/U against its history with bands, and the Arabica
minus Robusta S/U gap against the arb), Growth (production vs consumption growth), Scenario (change production by origin or consumption and
see balance, stocks and S/U move; nothing is saved) and Revisions (a log of every saved change and its effect on the balance, read from the
GitHub save history, so it needs `github_token`).

The Coffee page has an Edit mode (sidebar) that makes the inputs editable in place, with the calculated rows updating as you type.

## Next

Other sheets of the workbook (Brazil internal SnD, Coffee production per region, AgriAcies mimic) can become further pages.

Estimates follow today's date: the crop year (Jul-Jun) that is running and every later one is starred and shaded, years that have finished are not.

## Brazil internal SnD

Same rules as the sheet: Brazil production comes from the SnD ETG sheet unless the Brazil sheet has its own number for the year; consumption is typed up to 2020/21 and from 2021/22 is (1 - Conillon demand %) or the Conillon demand % times the overall Brazil consumption; stock change = production - exports - consumption; closing stock rolls forward from the first year. Every calculated row was checked against Excel's own numbers. One difference: the sheet leaves the 2027/28 Conillon stock change blank, so its closing stock stays at 3.9; the dashboard calculates it (+2.8, closing 6.7). The sheet's rows "All Coffee Production" and "Overall Consumption Brazil" at the bottom of the Overall block add the wrong cells and are not reproduced (the same figures are in the Conillon block).

Edit mode (sidebar, Coffee and Brazil pages) edits the table itself: the input cells are typed over in place (Enter to commit, Escape to cancel), the calculated rows are rebuilt from the edits as you go, and one Save writes to GitHub. The editable table is a small Streamlit component in `Dashboard/snd_table_component`.
