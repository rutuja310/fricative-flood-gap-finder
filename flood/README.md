# Private Flood Insurance Gap Finder

County-by-county grow / re-price / hold / avoid calls for a private flood insurer. Each call compares NFIP paid claims (1978–2025) with FEMA's modeled flood loss. Public data only.

| Piece | Where |
|---|---|
| Public site (GitHub Pages) | https://rutuja310.github.io/fricative-flood-gap-finder/ (built from `flood/demo/page.html` into `flood/demo/index.html`) |
| Downloads | `flood/demo/downloads/`: `plan.xlsx`, `plan-{grow,re-price,pause}.csv`, `counties.xlsx`, `counties.csv` |
| Live demo in Claude | https://claude.ai/artifact/N1f6ca4x6WbYGTtx8iL96H (same page; its download links open the public site) |
| Deck | https://claude.ai/artifact/Ru7kDpujGzwgQkVd2jLqVN |
| Memo | https://claude.ai/artifact/RPDn32fitiTPVDedgiZcNS |
| Deck (PowerPoint, public) | https://github.com/rutuja310/fricative-flood-gap-finder/blob/main/flood/deck/Private-Flood-Insurance-Gap-Finder.pptx |
| Sources (public) | https://rutuja310.github.io/fricative-flood-gap-finder/flood/demo/sources.html ([`flood/SOURCES.md`](SOURCES.md)) |
| Loom script | https://claude.ai/artifact/HBS1jnxXFPzNZisXVJgH11 |
| Fetch raw data | `sh flood/src/fetch_raw.sh` → `flood/raw/` (not in git) |
| Point-in-time policies (optional) | `sh flood/src/fetch_policies_api.sh` → `flood/raw/policies/` (hours when the API is slow; adds the point-in-time backtest) |
| Tracts and storms (optional) | `sh flood/src/fetch_tracts.sh` → NRI tracts, ACS homes, tract crosswalk, NOAA storms (about a minute; adds the tract and storm-years-out tests) |
| Methodology | [`flood/METHODOLOGY.md`](METHODOLOGY.md), also as a web page: https://rutuja310.github.io/fricative-flood-gap-finder/flood/demo/methodology.html |
| Analysis | `flood/src/flood.py` (scores, calls, blind test) |
| Run everything | `python3 flood/src/run_flood.py` → `flood/out/` and `flood/demo/data.json` |
| Scheduled refresh | `python3 flood/src/refresh.py --monthly | --quarterly | --storms | --followups [--publish]` → `flood/out/reports/`; `--publish` commits and pushes so the site updates |
| n8n workflow | `flood/n8n/flood_refresh_workflow.json` (runs from `~/workspace/fricative-flood-gap-finder`; set the Notion block ID and alert email first) |
| Code | https://github.com/rutuja310/fricative-flood-gap-finder |

## Inputs

- **NFIP claims:** OpenFEMA v3 `NfipClaims`. The parquet file is refused by FEMA's CDN from cloud machines, so `fetch_claims_api.sh` pages the API instead (273 calls of 10,000 rows).
- **NFIP residential penetration rates:** OpenFEMA v1 API, August 2026.
- **FEMA National Risk Index v1.20 (Dec 2025), county table:** FEMA's ArcGIS feature service. The old hazards.fema.gov zip was retired.
- **CPI-U annual averages:** hard-coded in `flood.py`.
- **Census ACS 2019–2023 (B19013 income, B25077 home value):** keyless summary files from www2.census.gov.
- **FEMA disaster declarations (v2):** OpenFEMA API, read by `refresh.py --storms`.
- **NFIP policies in force (v3 `NfipPolicies`), 1 July 2014 and 2019:** OpenFEMA API, one day of effective dates per call (the parquet is refused and deep paging times out). Used only by the point-in-time backtest.

## This quarter's lists

- **Grow:** top 5 by modeled loss on homes without NFIP cover. Counties must be affordable and agree over the last ten years, with at most 2 per state.
- **Re-price and Pause:** top 5 by score. Counties need 300+ paid claims and must agree over the last ten years.

Backtest (lists made with data to 2014, top 25, losses vs model in 2015–2024). The insured share is the one known at each step (policies in force July 2014 to score, July 2019 to judge); today's share for every year is in brackets:
- Grow: 0.16× (0.24×).
- Pause: 2.24× (2.06×).
- Re-price: 0.91× (0.41×). No better than all counties, so treat it as a review list.
- All counties: 1.01× (1.02×).

## The score

expected = NRI building flood loss (inland + coastal) × NFIP insured share.
ratio = NFIP building claims paid per year (2024 $) ÷ expected.
The ratio is divided by the US ratio for the same years, with the county's worst year left out. It is then credibility-weighted toward 1, with full weight at 1,082 paid claims.

Calls:
- **Pause:** score ≥ 3.
- **Re-price:** score ≥ 1.5.
- **Grow:** score ≤ 0.8, with under 10% of homes insured and modeled loss over $1M.
- **Hold:** everything else.

## Blind test

Scores use 1978–2014 only and are checked against 2015–2024.
- **By county count:** flagged-high counties ran high 29.2% of the time, vs 11.8% for flagged-low and a 20.5% base rate (today's share: 24.6%, 12.5%, 17.9%).
- **By dollars:** 82% of the losses above the model landed in unflagged counties (86% with today's share).
- **Storm years out (NOAA Storm Events):** 80% of that unflagged excess came in years a hurricane, tropical storm or storm surge hit the county. With those years taken out of 2015–2024, flagged-high counties ran high 45%, vs 12% flagged-low and a 33% base rate (the base rate rises because storm dollars also leave the national norm). The score reads lasting gaps; it can't place the next hurricane.
- **Census tracts (2020 tracts; 97% of claims carry a tract code):** the same point-in-time test on 6,750 tracts with 30+ claims to 2014. Flagged-high tracts ran high 35%, vs 14% flagged-low and a 25% base rate (Spearman 0.24). Losses above the model in unflagged areas fall to 69% (82% by county). Inside counties the county score did not flag, flagged tracts ran high 44% (base 26%, flagged-low 17%) and held 24% of those counties' excess: the tract score finds part of what the county score misses.

So the tool is a pricing signal and needs a concentration cap.
