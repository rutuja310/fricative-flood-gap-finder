"""Files for the public site (GitHub Pages): spreadsheet downloads and the standalone page.

  write_downloads(df, summary)  -> flood/demo/downloads/
      plan.xlsx                 this quarter's lists: About, Grow, Re-price, Pause sheets
      plan-grow.csv, plan-re-price.csv, plan-pause.csv
      counties.xlsx, counties.csv   every county with its call, reason and numbers
  build_page()                  -> flood/demo/index.html (page.html wrapped in a full HTML document)

Called by run_flood.py on every run; refresh.py --publish commits and pushes the result.
"""
import datetime as dt
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "demo"
DL = DEMO / "downloads"
LABEL = {"grow": "Grow", "re-price": "Re-price", "pause": "Pause", "hold": "Hold"}
SITE = "https://rutuja310.github.io/fricative-flood-gap-finder/"

# (column title, source column, kind) — kind sets the Excel number format
COUNTY_COLS = [
    ("FIPS", "fips", "text"), ("County", "county", "text"), ("State", "state", "text"),
    ("Call", "call", "text"), ("Reason", "headline", "wide"),
    ("On this quarter's list", "on_list", "text"),
    ("Score used for the call (× model)", "chr_cred", "x"),
    ("Gap, all years (× model)", "rel", "x"), ("Gap without worst year (× model)", "chr", "x"),
    ("Worst year", "worst_year", "int"), ("Worst year, in normal years of loss", "shock", "x"),
    ("Still true recently?", "recent_note", "wide"), ("Gap 2016–2025 (× model)", "rel_recent", "x"),
    ("Paid NFIP claims, 1978–2025", "claims_n", "int"),
    ("Expected NFIP paid per year, model at US norm ($)", "expected", "usd"),
    ("Actual NFIP paid per year, 1978–2025 ($)", "paid_bldg", "usd"),
    ("Modeled flood loss, all buildings, per year ($)", "ealb", "usd"),
    ("Homes", "homes", "int"), ("Homes with NFIP cover", "policies", "int"),
    ("Share of homes with NFIP cover", "pen", "pct"),
    ("Homes without NFIP cover (upper bound)", "uninsured", "int"),
    ("Median household income ($)", "income", "usd"), ("Median home value ($)", "homeval", "usd"),
    ("Affordability flag (grow, slowly)", "afford", "text"),
    ("FEMA inland flood rating", "ifld_rating", "text"), ("FEMA coastal flood rating", "cfld_rating", "text"),
]
PLAN_COLS = [("Rank", "rank", "int")] + [c for c in COUNTY_COLS if c[1] in (
    "county", "state", "fips", "headline", "recent_note", "chr_cred", "claims_n", "uninsured", "income",
    "ealb", "pen")]
FORMATS = {"x": '0.00"×"', "usd": '"$"#,##0', "int": "#,##0", "pct": "0.0%"}


def quarter(d=None):
    d = d or dt.date.today()
    return f"Q{(d.month - 1) // 3 + 1} {d.year}"


def county_table(df, plan):
    t = df.copy()
    on = {f: LABEL[k] for k, v in plan.items() for f in v}
    t["fips"] = t.index
    t["call"] = t.action.map(LABEL)
    t["on_list"] = t.index.map(lambda f: on.get(f, ""))
    t["expected"] = t.insured_model * df.attrs["nat_rel"]
    t["uninsured"] = t.homes - t.policies
    t["afford"] = ["Yes" if (a == "grow" and bool(f)) else "" for a, f in zip(t.action, t.afford_flag.fillna(False))]
    return t


def frame(t, cols):
    out = pd.DataFrame({title: t[src].values for title, src, _ in cols})
    return out


def style(ws, cols, wide=60):
    ws.freeze_panes = "B2"
    for i, (title, _, kind) in enumerate(cols, 1):
        c = ws.cell(row=1, column=i)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="13222F")
        c.alignment = Alignment(wrap_text=True, vertical="top")
        width = wide if kind == "wide" else max(12, min(28, len(title) * 0.9))
        ws.column_dimensions[get_column_letter(i)].width = width
        if kind in FORMATS:
            for row in ws.iter_rows(min_row=2, min_col=i, max_col=i):
                row[0].number_format = FORMATS[kind]
        if kind == "wide":
            for row in ws.iter_rows(min_row=2, min_col=i, max_col=i):
                row[0].alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[1].height = 48


def about_rows(summary, q):
    bt = summary["list_backtest"]
    lb, base = bt["lists"], bt["baseline_all_counties"]
    rows = [
        ("Private Flood Insurance Gap Finder", f"This quarter's plan, {q}"),
        ("Generated", dt.date.today().isoformat()),
        ("Live site", SITE),
        ("", ""),
        ("What a call means", ""),
        ("Grow", "Claims have run at or below the flood model (score ≤ 0.8×) and under 10% of homes have NFIP cover. "
                 "List: ranked by modeled loss on homes without NFIP cover; affordable counties whose last ten years "
                 "agree; at most 2 per state."),
        ("Re-price", "Claims run 1.5× the model or more, even leaving out the worst year. List: ranked by strength of "
                     "evidence; 300+ paid claims; last ten years agree. Weak in the backtest: review with pricing."),
        ("Pause", "Claims run 3× the model or more, even leaving out the worst year. List: ranked by strength of "
                  "evidence; 300+ paid claims; last ten years agree."),
        ("", ""),
        ("Backtest (lists made with data to 2014, top 25)", "Losses vs model in 2015–2024 · share that ran above it"),
    ]
    for k in ("grow", "re-price", "pause"):
        v = lb.get(f"{k}_top25")
        if v:
            rows.append((LABEL[k], f"{v['next_decade_dollars_vs_model']:.2f}× · {v['share_ran_above_model']:.0%}"))
    rows.append(("All counties (baseline)", f"{base['next_decade_dollars_vs_model']:.2f}× · "
                                            f"{base['share_ran_above_model']:.0%}"))
    rows += [
        ("", ""),
        ("Method", "Expected = FEMA National Risk Index modeled flood loss to buildings × share of homes with NFIP "
                   "cover. Actual = NFIP building claims paid per year, 1978–2025, 2024 dollars. Gap = actual ÷ "
                   "expected, vs the US ratio for the same years, worst year left out, shrunk toward 1 for thin "
                   "data (full weight at 1,082 paid claims)."),
        ("Limits", "FEMA's public model, not the insurer's own. Private flood cover is not public by county, so "
                   "homes without NFIP cover is an upper bound. Today's insured share stands in for past years. "
                   "A hypothesis from secondary research; not validated with industry practitioners."),
        ("Sources", "OpenFEMA (NFIP claims v3, residential penetration rates, disaster declarations); FEMA National "
                    "Risk Index v1.20; Census ACS 2019–2023 (B19013, B25077); BLS CPI-U."),
    ]
    return pd.DataFrame(rows, columns=["Item", "Detail"])


def write_downloads(df, summary):
    DL.mkdir(parents=True, exist_ok=True)
    plan = {k: [x["fips"] for x in v] for k, v in summary["plan"].items()}
    t = county_table(df, plan)
    q = quarter()

    allc = frame(t.sort_values(["state", "county"]), COUNTY_COLS)
    allc.to_csv(DL / "counties.csv", index=False)
    with pd.ExcelWriter(DL / "counties.xlsx", engine="openpyxl") as xw:
        allc.to_excel(xw, sheet_name="All counties", index=False)
        style(xw.sheets["All counties"], COUNTY_COLS)
        a = about_rows(summary, q)
        a.to_excel(xw, sheet_name="About", index=False)
        ws = xw.sheets["About"]
        ws.column_dimensions["A"].width = 34
        ws.column_dimensions["B"].width = 110
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.cell(row=1, column=1).font = ws.cell(row=1, column=2).font = Font(bold=True)

    with pd.ExcelWriter(DL / "plan.xlsx", engine="openpyxl") as xw:
        a = about_rows(summary, q)
        a.to_excel(xw, sheet_name="About", index=False)
        ws = xw.sheets["About"]
        ws.column_dimensions["A"].width = 34
        ws.column_dimensions["B"].width = 110
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
        for k in ("grow", "re-price", "pause"):
            sub = t.loc[plan[k]].copy()
            sub["rank"] = range(1, len(sub) + 1)
            p = frame(sub, PLAN_COLS)
            p.to_csv(DL / f"plan-{k}.csv", index=False)
            p.to_excel(xw, sheet_name=LABEL[k], index=False)
            style(xw.sheets[LABEL[k]], PLAN_COLS)
    return {"quarter": q, "files": sorted(f.name for f in DL.iterdir())}


HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="This quarter's grow / re-price / pause counties for a private flood writer, from 48 years of NFIP claims vs FEMA's flood model.">
<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>
"""


def build_page():
    """flood/demo/index.html for GitHub Pages: page.html (the Claude artifact source) in a full document."""
    body = (DEMO / "page.html").read_text()
    (DEMO / "index.html").write_text(HEAD + "</head>\n<body>\n" + body + "\n</body>\n</html>\n")
    build_methodology()


METHOD_CSS = """
:root { --bg: #f4f5f1; --panel: #fbfcf9; --ink: #15202b; --muted: #56616c; --line: #d8ddd5; --soft: #e9ece6; --accent: #a9541a;
  --display: "Source Serif 4", Georgia, serif; --body: "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace; color-scheme: light }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #11171d; --panel: #182029; --ink: #e8ece8; --muted: #a3adb5; --line: #2c3742; --soft: #212b35; --accent: #f0a75a; color-scheme: dark } }
:root[data-theme="dark"] { --bg: #11171d; --panel: #182029; --ink: #e8ece8; --muted: #a3adb5; --line: #2c3742; --soft: #212b35;
  --accent: #f0a75a; color-scheme: dark }
body { margin: 0; background: var(--bg); color: var(--ink); font: 16px/1.6 var(--body); }
main { max-width: 52rem; margin-inline: auto; padding: 32px max(16px, env(safe-area-inset-left, 0px)) 64px; }
h1, h2, h3 { font-family: var(--display); font-weight: 400; line-height: 1.2; text-wrap: balance; }
h1 { font-size: clamp(1.9rem, 4vw, 2.6rem); margin: 8px 0 16px; }
h2 { font-size: 1.5rem; margin: 40px 0 12px; padding-top: 16px; border-top: 1px solid var(--line); }
h3 { font-size: 1.15rem; margin: 28px 0 8px; }
p, ul, ol { margin: 0 0 14px; }
li { margin-bottom: 6px; }
a { color: var(--accent); }
.eyebrow { font-size: .75rem; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); font-weight: 500; }
.eyebrow a { color: inherit; }
code { font-family: var(--mono); font-size: .88em; background: var(--soft); padding: 1px 5px; border-radius: 4px; }
pre { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; overflow-x: auto; }
pre code { background: none; padding: 0; }
.table { overflow-x: auto; margin: 0 0 18px; }
table { border-collapse: collapse; width: 100%; font-size: .92rem; background: var(--panel); }
th, td { border: 1px solid var(--line); padding: 8px 10px; text-align: left; vertical-align: top; }
th { background: var(--soft); font-weight: 600; }
"""


def _inline(s):
    """Escape, then the inline markdown METHODOLOGY.md uses: `code`, **bold**, [text](link)."""
    import html
    import re
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)


def md_to_html(md):
    """Just enough markdown for METHODOLOGY.md: headings, paragraphs, bullet and numbered lists (one nested
    level), pipe tables and fenced code."""
    out, para, i = [], [], 0
    lines = md.splitlines()

    def flush():
        if para:
            out.append(f"<p>{_inline(' '.join(para))}</p>")
            para.clear()

    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            flush()
            j = i + 1
            while not lines[j].startswith("```"):
                j += 1
            import html
            out.append("<pre><code>" + html.escape("\n".join(lines[i + 1:j])) + "</code></pre>")
            i = j + 1
            continue
        if ln.startswith("#"):
            flush()
            n = len(ln) - len(ln.lstrip("#"))
            out.append(f"<h{n}>{_inline(ln[n:].strip())}</h{n}>")
        elif ln.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], rows[2:]
            out.append('<div class="table"><table><thead><tr>' + "".join(f"<th>{_inline(c)}</th>" for c in head)
                       + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r)
                                                         + "</tr>" for r in body) + "</tbody></table></div>")
            continue
        elif ln.startswith(("- ", "1. ")) or (ln[:1].isdigit() and ". " in ln[:4]):
            flush()
            tag = "ul" if ln.startswith("- ") else "ol"
            items = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith("#"):
                cur = lines[i]
                if cur.startswith("  "):
                    items[-1][1].append(cur.strip()[2:])
                else:
                    items.append([cur.split(" ", 1)[1], []])
                i += 1
            lis = []
            for text, sub in items:
                inner = "".join(f"<li>{_inline(t)}</li>" for t in sub)
                lis.append(f"<li>{_inline(text)}" + (f"<ul>{inner}</ul>" if sub else "") + "</li>")
            out.append(f"<{tag}>" + "".join(lis) + f"</{tag}>")
            continue
        elif not ln.strip():
            flush()
        else:
            para.append(ln.strip())
        i += 1
    flush()
    return "\n".join(out)


def build_methodology():
    """flood/demo/methodology.html for GitHub Pages, from flood/METHODOLOGY.md."""
    body = md_to_html((ROOT / "METHODOLOGY.md").read_text())
    fonts = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600"
             "&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap")
    page = (f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f"<title>Methodology · Private Flood Insurance Gap Finder</title>\n"
            f'<meta name="description" content="How the Private Flood Insurance Gap Finder scores counties and how it was tested.">\n'
            f'<link rel="stylesheet" href="{fonts}">\n<style>{METHOD_CSS}</style>\n</head>\n<body>\n<main>\n'
            f'<p class="eyebrow"><a href="./">Private Flood Insurance Gap Finder</a> · Methodology</p>\n'
            f"{body}\n</main>\n</body>\n</html>\n")
    (DEMO / "methodology.html").write_text(page)
