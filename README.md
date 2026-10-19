# Global SnD

Supply and demand balances, starting with coffee: the "SnD ETG" table (Arabica, Robusta, Global), the Brazil internal SnD, analytics and a revision log.
Crop year Jul-Jun, million 60 kg bags. Run from the project root: `streamlit run Dashboard/app.py`.

## Sections (sidebar)

- **SnD** - Coffee (Arabica, Robusta, Global), Brazil (internal SnD) and the AgriAcies-format tables. Mode **Edit** makes the input cells editable in
  place; the calculated rows follow as you type; Save writes to GitHub with an optional reason. The first-year stock is under the table.
- **Analysis** - Balance bridge (what moved the balance, origin by origin), Stocks to use (S/U against its history, and whether the Arabica-vs-Robusta
  S/U gap moves the arb), Brazil crop cycle (on/off years and what they imply for the next crop).
- **Scenarios** - what-if (change any origin or consumption by %, for the crop years you pick; KPI tiles, base-vs-scenario bars, result table) and
  sensitivity (flex one origin or consumption in one year by a step you choose; S/U, balance or end stock). Nothing here changes the data.
- **Revisions** - every saved change (Coffee or Brazil) as one line chart of all origins, with the reason given when saving.

Estimates follow today's date: the crop year that is running and every later one is starred and shaded.

## Structure

- `Dashboard/app.py` - shell, theme, optional password gate. `snd.py` (Coffee page), `brazil.py`, `analytics.py`, `scenario.py`, `revisions.py`.
  `tableedit.py` + `snd_table_component/` - the small Streamlit component that makes the styled table editable. `ghstore.py` - saves to GitHub.
- `Database/coffee_snd.csv` (inputs), `coffee_snd_meta.json` (first-year end stock), `coffee_snd_notes.csv` (analyst comments, purple corner),
  `coffee_su_history.csv` (S/U since 2006/07 and the arb), `brazil_snd.csv`, `brazil_agri.csv`, `brazil_meta.json`.
- `Automator/build_coffee_snd.py`, `build_brazil_snd.py` - one-off seeds from `Archives/coffee.xlsx` (stays local). If Excel has the workbook open it is locked:
  close it or pass a copy.

## How it is worked out

Only inputs are stored; everything else is calculated like the Excel sheets (checked against Excel's own numbers): production = sum of origins, balance =
production - consumption, end stock = last year's + balance, S/U = end stock / consumption, global = Arabica + Robusta. Brazil production comes from the
SnD sheet unless the Brazil sheet has its own; Brazil consumption after 2020/21 = (1 - Conillon demand %) or the Conillon demand % times overall consumption.
Differences from the Excel: Arabica 2027/28 production (sheet typed 98.4, origins add up to 95.2), the blank 2027/28 Conillon stock change, and two
buggy rows of the Overall Brazil block that are not reproduced.

## Deploying

Streamlit Cloud, main file `Dashboard/app.py`. Secrets (see `.streamlit/secrets.toml.example`): `github_token` (Contents read/write on this repo) lets Edit mode save,
and `[auth] password` asks for a password before anything is shown. Set the password: without it, anyone with the URL can edit the numbers.
A save commits to GitHub, which redeploys the app.

## Next

The "AgriAcies mimic" sheet has the Brazil layout with AgriAcies's inputs and the Conillon block on an Apr-Mar crop year; "Coffee Production per region" is another sheet.
