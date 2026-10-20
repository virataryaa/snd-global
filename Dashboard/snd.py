"""Coffee SnD: the 'SnD ETG' table (Arabica, Robusta, Global) from the inputs in Database/coffee_snd.csv.

Inputs are each origin's production and the consumption, per crop year (Jul-Jun), in million 60 kg bags. Everything else is
worked out here the way the Excel sheet does: production = sum of the origins, balance = production - consumption,
end stock = last year's end stock + balance (the first year's end stock is an input), S/U = end stock / consumption.
"""
import html
import io
import json
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ghstore as gh

ROOT = Path(__file__).resolve().parent.parent
CSV, META, NOTES = ROOT / "Database" / "coffee_snd.csv", ROOT / "Database" / "coffee_snd_meta.json", ROOT / "Database" / "coffee_snd_notes.csv"
CSV_PATH, META_PATH = "Database/coffee_snd.csv", "Database/coffee_snd_meta.json"            # paths in the repo
ORIGINS = {
    "Arabica": ["Brazil", "Colombia", "Honduras", "Super 5", "Ethiopia", "Peru", "Others"],
    "Robusta": ["Vietnam", "Brazil", "Indonesia", "India", "Uganda", "Cote d'Ivoire", "Others"],
}
TZ = "Europe/Amsterdam"
NAVY, TEAL, GREEN, RED, AMBER, GREY = "#0a2463", "#1f8a9c", "#1f9d6f", "#c0392b", "#b7791f", "#94a3b8"
INK, AXIS, GRID = "#1d1d1f", "#86868b", "rgba(0,0,0,0.05)"

CSS = """
<style>
.snd-wrap { background: #ffffff; border: 1px solid #e6e9f0; border-radius: 12px; padding: 3px 5px 6px; margin-bottom: 12px;
            box-shadow: 0 1px 2px rgba(15,23,42,.04); overflow-x: auto; width: fit-content; max-width: 100%; }
table.snd { border-collapse: separate; border-spacing: 0; width: auto; font-size: 12px; color: #0f172a;
            font-variant-numeric: tabular-nums; letter-spacing: .005em; }
table.snd td, table.snd th { padding: 2px 9px; text-align: right; white-space: nowrap; line-height: 1.3; }
table.snd td { min-width: 46px; }
table.snd td.lbl { text-align: left; color: #475569; padding-left: 12px; min-width: 150px; }
table.snd td { border: 0; border-bottom: 1px solid #f1f3f7; }
table.snd th { border: 0; }
/* title strip + context line */
table.snd tr.meta td { color: #64748b; font-size: 11.5px; border-bottom: 0; padding: 6px 12px 10px; }
table.snd tr.meta td.lbl { color: #94a3b8; }
/* commodity header: label left, a thin accent rule under it */
table.snd tr.comm th { text-align: left; font-size: 12px; font-weight: 700; color: #ffffff; letter-spacing: .12em; text-transform: uppercase;
                       padding: 5px 12px; background: linear-gradient(90deg, #0a1d4d 0%, #0a2463 100%); }
table.snd tr.gap td { border: 0; height: 8px; padding: 0; }
/* year header */
table.snd th.y { font-size: 11px; font-weight: 600; color: #0a2463; padding: 4px 9px; background: #eef2fb; border-bottom: 1px solid #dbe4f7; }
table.snd th.y.fc { background: #dbe4f7; }
table.snd th.y.first { text-align: left; }
table.snd td.fc { background: #f6f8fd; }
table.snd tr.b td { font-weight: 650; color: #0f172a; }
table.snd tr.b td.lbl { color: #0f172a; }
table.snd tr.bal td { background: #e8eefb; font-weight: 700; border-bottom: 1px solid #dbe4f7; }
table.snd tr.bal td.fc { background: #dfe8f9; }
table.snd tr.bal td.lbl { color: #0a2463; }
table.snd tr.soft td { color: #64748b; }
table.snd tr.soft td.lbl { color: #94a3b8; }
table.snd tr.sep td { border: 0; height: 6px; padding: 0; }
table.snd td.neg { color: #c0392b; }
table.snd td.ed { cursor: text; }
table.snd td.ed:hover { box-shadow: inset 0 0 0 1px #9db3e6; background: #f3f6fd; }
table.snd td.ed:focus { outline: none; box-shadow: inset 0 0 0 2px #0a2463; background: #ffffff; }
table.snd td.chg { background: #fff4d6 !important; color: #7a4b00; font-weight: 700; }
table.snd td.note { position: relative; cursor: help; }
table.snd td.note::after { content: ""; position: absolute; top: 0; right: 0; border-style: solid; border-width: 0 6px 6px 0;
                           border-color: transparent #a855f7 transparent transparent; }
.snd-bar { background: linear-gradient(90deg, #0a1d4d 0%, #0a2463 100%); color: #ffffff; font-size: 12px; font-weight: 700;
           letter-spacing: .12em; text-transform: uppercase; padding: 7px 14px; border-radius: 8px 8px 0 0; margin-top: 6px; }
.snd-head { display: flex; align-items: baseline; gap: 12px; margin: 2px 0 12px; }
.snd-head .t { font-size: 20px; font-weight: 700; color: #0a2463; letter-spacing: -.01em; }
.snd-head .s { font-size: 12px; color: #94a3b8; letter-spacing: .02em; }
</style>
"""


# ── Data ──────────────────────────────────────────────────────────────────────
def ystart(label: str) -> int:
    return int(label[:4])


def current_crop_year(today=None) -> str:
    """The Jul-Jun crop year today falls in: Oct 2026 -> '2026/27', Mar 2027 -> '2026/27'."""
    t = today or date.today()
    y = t.year if t.month >= 7 else t.year - 1
    return f"{y}/{(y + 1) % 100:02d}"


def is_estimate(year: str) -> bool:
    """A crop year that has not finished yet (the running one and later) is an estimate: starred and shaded."""
    return ystart(year) >= ystart(current_crop_year())


@st.cache_data(ttl=600)
def load():
    df = pd.read_csv(CSV)
    meta = json.loads(META.read_text(encoding="utf-8"))
    notes = pd.read_csv(NOTES) if NOTES.exists() else pd.DataFrame(columns=["commodity", "item", "year", "note"])
    years = sorted(df["year"].unique(), key=ystart)
    return df, meta, {(r.commodity, r.item, r.year): r.note for r in notes.itertuples()}, years


def block(df, meta, comm, years) -> pd.DataFrame:
    """One commodity's SnD: rows = origins, Production, Consumption, Consumption %, Balance, End Season Stock, S/U."""
    d = df[df["commodity"] == comm]
    piv = d.pivot_table(index="item", columns="year", values="value", aggfunc="sum").reindex(columns=years)
    out = piv.reindex(ORIGINS[comm] + ["Consumption"]).copy()
    prod = out.loc[ORIGINS[comm]].sum(axis=0, min_count=1)
    cons = out.loc["Consumption"]
    bal = prod - cons
    stock, run = [], float(meta["opening_stock"][comm])
    for i, y in enumerate(years):
        run = run if i == 0 else run + (bal[y] if pd.notna(bal[y]) else 0.0)
        stock.append(run)
    out.loc["Production"] = prod
    out.loc["Consumption %"] = cons.pct_change(fill_method=None)
    out.loc["Balance"] = bal
    out.loc["End Season Stock"] = stock
    out.loc["S/U"] = out.loc["End Season Stock"] / cons
    return out


def global_block(a: pd.DataFrame, r: pd.DataFrame, years) -> pd.DataFrame:
    g = pd.DataFrame(columns=years, dtype=float)
    g.loc["Production Global"] = a.loc["Production"] + r.loc["Production"]
    g.loc["Consumption Global"] = a.loc["Consumption"] + r.loc["Consumption"]
    g.loc["Global Balance"] = g.loc["Production Global"] - g.loc["Consumption Global"]
    g.loc["Global demand chg"] = g.loc["Consumption Global"].pct_change(fill_method=None)
    g.loc["Combined End Season Stock"] = a.loc["End Season Stock"] + r.loc["End Season Stock"]
    g.loc["Combined S/U"] = g.loc["Combined End Season Stock"] / g.loc["Consumption Global"]
    g.loc["Robusta demand share"] = r.loc["Consumption"] / g.loc["Consumption Global"]
    return g


# ── Table ─────────────────────────────────────────────────────────────────────
def fnum(v, dec=1):
    if pd.isna(v):
        return ""
    r = round(float(v), dec)
    return f"({abs(r):.{dec}f})" if r < 0 else f"{r:.{dec}f}"


def fpct(v, dec=1):
    return "" if pd.isna(v) else f"{v * 100:.{dec}f}%"


def snd_table(df, meta, notes, years, shown, comm_frames, glob, combo, edit=None) -> str:
    """The sheet's layout, quietly: Brazil Combo line, then Arabica / Robusta / Global blocks."""
    ncol = len(shown) + 1

    def shaded(comm, y):
        return bool(comm) and is_estimate(y)

    def starred(comm, y):
        return bool(comm) and is_estimate(y)

    def head(comm=None):
        cells = "".join(f"<th class='y{' fc' if shaded(comm, y) else ''}'>{y}{'*' if starred(comm, y) else ''}</th>" for y in shown)
        return f"<tr><th class='y first'></th>{cells}</tr>"

    def tr(label, vals, kind="", fmt=fnum, comm=None, item=None, neg_red=False):
        cells = ""
        for y in shown:
            v = vals[y]
            cls = []
            if shaded(comm, y):
                cls.append("fc")
            if neg_red and pd.notna(v) and v < -0.049:
                cls.append("neg")
            title = ""
            nt = notes.get((comm, item, y)) if comm else None
            if nt:
                cls.append("note")
                title = f" title='{html.escape(nt, quote=True)}'"
            if edit and comm and item:                                   # an input cell: typed over in place
                k = f"{comm}|{item}|{y}"
                b = edit["base"].get(k)
                cls.append("ed")
                if k in edit["changed"]:
                    cls.append("chg")
                title += f" data-k='{html.escape(k, quote=True)}' data-base='{'' if b is None or pd.isna(b) else b}'"
            cells += f"<td class='{' '.join(cls)}'{title}>{fmt(v)}</td>"
        return f"<tr class='{kind}'><td class='lbl'>{label}</td>{cells}</tr>"

    out = [f"<tr class='meta'><td class='lbl'>Brazil combo</td>{''.join(f'<td>{combo[y]:.1f}</td>' for y in shown)}</tr>"]
    for comm, fr in comm_frames.items():
        if comm != "Arabica":
            out.append(f"<tr class='gap'><td colspan='{ncol}'></td></tr>")
        out.append(f"<tr class='comm'><th colspan='{ncol}'>{comm}</th></tr>")
        out.append(head(comm))
        for o in ORIGINS[comm]:
            out.append(tr(o, fr.loc[o], comm=comm, item=o))
        out.append(tr("Production", fr.loc["Production"], "b"))
        out.append(tr("Consumption", fr.loc["Consumption"], "b", comm=comm, item="Consumption"))
        out.append(tr("Consumption %", fr.loc["Consumption %"], "soft", fpct))
        out.append(tr("Balance", fr.loc["Balance"], "bal", neg_red=True))
        out.append(tr("End season stock", fr.loc["End Season Stock"], ""))
        out.append(tr("S/U", fr.loc["S/U"], "soft", (lambda v: fpct(v, 1 if comm == "Arabica" else 0))))
        if comm == "Robusta":
            out.append(tr("Robusta demand share", glob.loc["Robusta demand share"], "soft", lambda v: fpct(v, 0)))
    out.append(f"<tr class='gap'><td colspan='{ncol}'></td></tr>")
    out.append(f"<tr class='comm'><th colspan='{ncol}'>Global</th></tr>")
    out.append(head(None))
    out.append(tr("Production", glob.loc["Production Global"], "b"))
    out.append(tr("Consumption", glob.loc["Consumption Global"], "b"))
    out.append(tr("Balance", glob.loc["Global Balance"], "bal", neg_red=True))
    start = years.index(shown[0]) % 2                                 # the sheet pairs 2016/17 + 2017/18, 2018/19 + 2019/20, ...
    lab, val = {}, {}
    for i, y in enumerate(shown):
        if (i + start) % 2 == 0 and i + 1 < len(shown):
            lab[y] = f"{y[:4]}/{shown[i + 1][5:7]}"                  # 2016/17 + 2017/18 -> 2016/18
            val[y] = glob.loc["Global Balance", y] + glob.loc["Global Balance", shown[i + 1]]
    out.append("<tr class='soft'><td class='lbl'>2 year cycle</td>" + "".join(f"<td>{lab.get(y, '')}</td>" for y in shown) + "</tr>")
    out.append("<tr class='b'><td class='lbl'>2 year balance</td>"
               + "".join(f"<td class='{'neg' if val.get(y, 0) < -0.049 else ''}'>{fnum(val[y]) if y in val else ''}</td>" for y in shown) + "</tr>")
    out.append(tr("Demand change", glob.loc["Global demand chg"], "soft", fpct))
    out.append(tr("Combined end season stock", glob.loc["Combined End Season Stock"], ""))
    out.append(tr("Combined S/U", glob.loc["Combined S/U"], "soft", fpct))
    return f"<div class='snd-wrap'><table class='snd'>{''.join(out)}</table></div>"


# ── Charts ────────────────────────────────────────────────────────────────────
def _style(fig, height=230, fmt=",.1f", legend=True):
    fig.update_layout(template="plotly_white", height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#1d1d1f", size=11, family="-apple-system, BlinkMacSystemFont, Inter, Segoe UI, sans-serif"), margin=dict(t=4, b=24, l=8, r=8), hovermode="x unified",
                      legend=dict(orientation="h", x=0, y=1.14, bgcolor="rgba(0,0,0,0)", font=dict(size=10.5)) if legend else None,
                      showlegend=legend, bargap=0.35,
                      xaxis=dict(color=AXIS, showgrid=False, type="category", tickfont=dict(size=10),
                                 tickangle=0, tickvals=None),
                      yaxis=dict(gridcolor=GRID, color=AXIS, hoverformat=fmt, zeroline=True, zerolinecolor="rgba(15,23,42,0.18)",
                                 tickfont=dict(size=10)))
    return fig


def _bars(fig, x, y, name, color, est, **kw):
    fig.add_trace(go.Bar(x=x, y=y, name=name, marker=dict(color=color, opacity=[0.55 if e else 1 for e in est], line_width=0),
                         hovertemplate=name + ": %{y:.1f}<extra></extra>", **kw))


def _line(fig, x, y, name, color, right=False, pct=False, dash=None):
    fig.add_trace(go.Scatter(x=x, y=y, name=name, mode="lines+markers", yaxis="y2" if right else "y", line=dict(color=color, width=2.2, dash=dash),
                             marker=dict(size=5), hovertemplate=name + (": %{y:.1f}%" if pct else ": %{y:.1f}") + "<extra></extra>"))


def _y2(fig, suffix="%"):
    return fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, color=AXIS, ticksuffix=suffix, tickfont=dict(size=10)))


def charts(a, r, glob, shown):
    """Global SnD visuals: supply mix, stocks, balance, demand, origins and stocks to use. Estimates are faded."""
    x = [y[2:] for y in shown]                                        # 2024/25 -> 24/25 on the axes
    est = [is_estimate(y) for y in shown]
    rows = [st.columns(2, gap="small") for _ in range(3)]

    with rows[0][0], st.container(border=True):
        st.markdown("<div class='chart-head'>Production: Arabica and Robusta</div>", unsafe_allow_html=True)
        fig = go.Figure()
        _bars(fig, x, a.loc["Production", shown], "Arabica", NAVY, est)
        _bars(fig, x, r.loc["Production", shown], "Robusta", AMBER, est)
        _line(fig, x, r.loc["Production", shown] / glob.loc["Production Global", shown] * 100, "Robusta share (right)", RED, right=True, pct=True)
        st.plotly_chart(_y2(_style(fig, 280).update_layout(barmode="stack")), width="stretch", key="c_prod")
    with rows[0][1], st.container(border=True):
        st.markdown("<div class='chart-head'>End season stocks</div>", unsafe_allow_html=True)
        fig = go.Figure()
        _bars(fig, x, a.loc["End Season Stock", shown], "Arabica", NAVY, est)
        _bars(fig, x, r.loc["End Season Stock", shown], "Robusta", AMBER, est)
        _line(fig, x, glob.loc["Combined S/U", shown] * 100, "Global S/U (right)", RED, right=True, pct=True)
        st.plotly_chart(_y2(_style(fig, 280).update_layout(barmode="stack")), width="stretch", key="c_stock")

    with rows[1][0], st.container(border=True):
        st.markdown("<div class='chart-head'>Balance</div>", unsafe_allow_html=True)
        fig = go.Figure()
        _bars(fig, x, a.loc["Balance", shown], "Arabica", NAVY, est)
        _bars(fig, x, r.loc["Balance", shown], "Robusta", AMBER, est)
        _line(fig, x, glob.loc["Global Balance", shown], "Global", RED)
        st.plotly_chart(_style(fig, 280).update_layout(barmode="group"), width="stretch", key="c_bal")
    with rows[1][1], st.container(border=True):
        st.markdown("<div class='chart-head'>Consumption</div>", unsafe_allow_html=True)
        fig = go.Figure()
        _bars(fig, x, a.loc["Consumption", shown], "Arabica", NAVY, est)
        _bars(fig, x, r.loc["Consumption", shown], "Robusta", AMBER, est)
        _line(fig, x, glob.loc["Global demand chg", shown] * 100, "Growth (right)", RED, right=True, pct=True)
        st.plotly_chart(_y2(_style(fig, 280).update_layout(barmode="stack")), width="stretch", key="c_cons")

    with rows[2][0], st.container(border=True):
        st.markdown("<div class='chart-head'>Production by origin</div>", unsafe_allow_html=True)
        orig = {}
        for comm, fr in (("Arabica", a), ("Robusta", r)):
            for o in ORIGINS[comm]:
                nm = o if o != "Others" else "Others"
                orig[nm] = orig.get(nm, 0) + fr.loc[o, shown].fillna(0)
        order = sorted([o for o in orig if o != "Others"], key=lambda o: -float(orig[o].sum())) + ["Others"]
        pal = [NAVY, AMBER, TEAL, "#3e5c9a", "#d9a441", "#6fb7c4", "#8796c2", "#c9b38a", "#a8b3c7", "#cfd6e4", "#e3e7ef"]
        fig = go.Figure()
        for o, col in zip(order, pal + [GREY] * len(order)):
            _bars(fig, x, orig[o], o, col, est)
        st.plotly_chart(_style(fig, 300).update_layout(barmode="stack", legend=dict(font=dict(size=9.5), y=1.2)), width="stretch", key="c_orig")
    with rows[2][1], st.container(border=True):
        st.markdown("<div class='chart-head'>Stocks to use</div>", unsafe_allow_html=True)
        fig = go.Figure()
        _line(fig, x, a.loc["S/U", shown] * 100, "Arabica", NAVY, pct=True)
        _line(fig, x, r.loc["S/U", shown] * 100, "Robusta", AMBER, pct=True)
        _line(fig, x, glob.loc["Combined S/U", shown] * 100, "Global", RED, pct=True)
        st.plotly_chart(_style(fig, 300).update_layout(yaxis_ticksuffix="%"), width="stretch", key="c_su")


# ── Edit view: the styled table itself, typed over in place ────────────────────────────────────────────────
def _opening_controls(meta, years, editable):
    """The first year's end stock (where the stock roll starts), per commodity."""
    with st.expander("First-year end stock", expanded=False):
        c = st.columns([1.2, 1.2, 1, 4], vertical_alignment="bottom")
        old = {k: float(v) for k, v in meta["opening_stock"].items()}
        new = {k: c[i].number_input(f"{k} {years[0]} (m bags)", min_value=0.0, value=old[k], step=0.1, format="%.1f",
                                    key=f"os_{k}", disabled=not editable) for i, k in enumerate(["Arabica", "Robusta"])}
        if c[2].button("Save", disabled=(not editable) or all(abs(new[k] - old[k]) < 1e-9 for k in new), width="stretch", key="os_save"):
            try:
                with st.spinner("Saving..."):
                    def mut(m):
                        for k, v in new.items():
                            m["opening_stock"][k] = round(float(v), 4)
                    _save_meta("opening stock", old, new, mut)
            except (gh.GitHubError, Exception) as ex:
                st.error(f"GitHub save failed: {ex}")
            else:
                st.session_state["en_flash"] = "Opening stock saved."
                st.rerun()


def _undo():
    st.session_state["snd_epoch"] = st.session_state.get("snd_epoch", 0) + 1
    st.session_state["_snd_edits"] = {}
    try:
        st.session_state["snd_tbl"] = {}
    except Exception:
        pass


def render_edit(df, meta, notes, years, shown, editable):
    """Edit mode: the same table, with the input cells (origins, consumption) editable in place. The calculated rows are rebuilt from the
    edits and sent back to the table, so they move as you type. One Save for everything."""
    import tableedit
    epoch = st.session_state.setdefault("snd_epoch", 0)
    edits = st.session_state.get("snd_tbl")                      # the table's own state is dropped when Edit mode is left:
    if edits is None:                                            # fall back to the copy kept below, so pending edits survive a View / Edit switch
        edits = st.session_state.get("_snd_edits", {})
    base = {f"{c}|{it}|{y}": float(v) for c, it, y, v in zip(df["commodity"], df["item"], df["year"], df["value"])}
    changes = [(k.split("|")[0], k.split("|")[1], k.split("|")[2], base.get(k), (None if v is None else float(v))) for k, v in edits.items()]
    live = _apply_changes(df, changes)
    a, r = block(live, meta, "Arabica", years), block(live, meta, "Robusta", years)
    glob = global_block(a, r, years)
    table = snd_table(live, meta, notes, years, shown, {"Arabica": a, "Robusta": r}, glob, a.loc["Brazil"] + r.loc["Brazil"],
                      edit=dict(base=base, changed=set(edits)))
    tableedit.editable_table(table, tableedit.css_of(CSS), "snd_tbl", epoch, editable, edits)
    st.session_state["_snd_edits"] = dict(edits)
    if not editable:
        st.markdown("<div class='card-desc'>Read-only: add github_token in Secrets to edit.</div>", unsafe_allow_html=True)
        return
    bad = any(c[4] is not None and c[4] < 0 for c in changes)
    if bad:
        st.error("Values cannot be negative.")
    bc = st.columns([1, 1, 5, 3], vertical_alignment="center")
    save = bc[0].button("Save", type="primary", disabled=(not changes) or bad, width="stretch", key="snd_save")
    bc[1].button("Undo", disabled=not changes, width="stretch", key="snd_undo", on_click=_undo)
    reason = bc[2].text_input("Reason", key=f"snd_reason_{epoch}", placeholder="Reason for the change, shown in Revisions (e.g. CCS adjustment, weather shock)",
                              label_visibility="collapsed", max_chars=140, disabled=not changes)
    if changes:
        bc[3].markdown(f"<div class='card-desc' style='margin:0'>{len(changes)} unsaved change(s)</div>", unsafe_allow_html=True)
    if save:
        try:
            with st.spinner("Saving..."):
                _save_inputs(changes, reason)
        except (gh.GitHubError, Exception) as ex:
            st.error(f"GitHub save failed: {ex}")
        else:
            _undo()
            st.session_state["en_flash"] = f"Saved {len(changes)} change(s)."
            st.rerun()
    _opening_controls(meta, years, True)


# ── Page ──────────────────────────────────────────────────────────────────────
def render():
    st.markdown(CSS, unsafe_allow_html=True)
    df, meta, notes, years = load()
    with st.sidebar:
        st.markdown("<div class='sb-sep'></div>", unsafe_allow_html=True)
        span = st.radio("Years", ["Last 10", "All"], horizontal=True, key="snd_span")
        mode = st.radio("Mode", ["View", "Edit"], horizontal=True, key="snd_mode")
    shown = years[-10:] if span == "Last 10" else years
    if st.session_state.get("en_flash"):
        st.toast(st.session_state.pop("en_flash"))
    a, r = block(df, meta, "Arabica", years), block(df, meta, "Robusta", years)
    glob = global_block(a, r, years)
    combo = a.loc["Brazil"] + r.loc["Brazil"]
    st.markdown("<div class='snd-head'><span class='t'>Global SnD</span><span class='s'>Jul–Jun · m bags · * estimate</span></div>", unsafe_allow_html=True)
    if mode == "Edit":
        render_edit(df, meta, notes, years, shown, gh.enabled())
        return
    st.markdown(snd_table(df, meta, notes, years, shown, {"Arabica": a, "Robusta": r}, glob, combo), unsafe_allow_html=True)
    charts(a, r, glob, shown)


# ── Saving ────────────────────────────────────────────────────────────────────
def _num(txt):
    if txt is None or (isinstance(txt, float) and pd.isna(txt)):
        return None
    if isinstance(txt, (int, float)):
        return float(txt)
    txt = str(txt).replace(",", "").strip()
    return float(txt) if txt else None


def _fmt(v):
    return "" if v is None or pd.isna(v) else f"{v:g}"


def _apply_changes(d: pd.DataFrame, changes) -> pd.DataFrame:
    """The inputs frame with (commodity, item, year, old, new) changes applied; new = None removes the value."""
    d = d.copy()
    for c, it, y, _o, n in changes:
        d = d[~((d["commodity"] == c) & (d["item"] == it) & (d["year"] == y))]
        if n is not None:
            d = pd.concat([d, pd.DataFrame([{"commodity": c, "item": it, "year": y, "value": n}])], ignore_index=True)
    return d


def clean_reason(txt) -> str:
    """The reason typed with a save, as one short line that the revision log can read back (no ' | ' inside)."""
    return " ".join(str(txt or "").split()).replace(" | ", " / ")[:140]


def _save_inputs(changes, reason=""):
    lines = [f"{c} {it} {y}: {_fmt(o) or '-'} -> {_fmt(n) or '-'}" for c, it, y, o, n in changes]
    reason = clean_reason(reason)
    msg = f"Coffee SnD | {len(changes)} change(s)" + (f" | reason: {reason}" if reason else "") + "\n\n" + "\n".join(lines)

    def apply(text):
        d = _apply_changes(pd.read_csv(io.StringIO(text)), changes)
        order = {(c, it): i for c, its in ORIGINS.items() for i, it in enumerate(its + ["Consumption"])}
        d["_o"] = [order.get((c, it), 99) for c, it in zip(d["commodity"], d["item"])]
        d["_c"] = d["commodity"].map({"Arabica": 0, "Robusta": 1})
        d["_y"] = d["year"].map(ystart)
        d = d.sort_values(["_c", "_o", "_y"]).drop(columns=["_o", "_c", "_y"])
        return d.to_csv(index=False, lineterminator="\n"), None
    new_text, _ = gh.commit(CSV_PATH, apply, msg)
    with open(CSV, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)
    load.clear()


def _save_meta(label, old, new, mutate):
    msg = f"Setting | {label}: {old} -> {new}"

    def apply(text):
        d = json.loads(text)
        mutate(d)
        return json.dumps(d, indent=2) + "\n", None
    text, _ = gh.commit(META_PATH, apply, msg)
    with open(META, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    load.clear()
