# Flood Gap Finder

County-by-county grow / re-price / hold / avoid calls for a private flood insurer. Each call compares NFIP paid claims (1978–2025) with FEMA's modeled flood loss. Public data only.

| Piece | Where |
|---|---|
| Live demo | https://claude.ai/artifact/N1f6ca4x6WbYGTtx8iL96H (page source: `flood/demo/index.html`) |
| Deck | https://claude.ai/artifact/Ru7kDpujGzwgQkVd2jLqVN |
| Memo | https://claude.ai/artifact/RPDn32fitiTPVDedgiZcNS |
| Loom script | https://claude.ai/artifact/HBS1jnxXFPzNZisXVJgH11 |
| Fetch raw data | `sh flood/src/fetch_raw.sh` → `flood/raw/` (not in git) |
| Analysis | `flood/src/flood.py` (scores, calls, blind test) |
| Run everything | `python3 flood/src/run_flood.py` → `flood/out/` and `flood/demo/data.json` |
| Scheduled refresh | `python3 flood/src/refresh.py --monthly | --quarterly | --storms | --followups` → `flood/out/reports/` |
| n8n workflow | `flood/n8n/flood_refresh_workflow.json` (runs from `~/workspace/fricative-flood-gap-finder`; set the Notion block ID and alert email first) |
| Code | https://github.com/rutuja310/fricative-flood-gap-finder |

## Inputs

- **NFIP claims:** OpenFEMA v3 `NfipClaims`. The parquet file is refused by FEMA's CDN from cloud machines, so `fetch_claims_api.sh` pages the API instead (273 calls of 10,000 rows).
- **NFIP residential penetration rates:** OpenFEMA v1 API, August 2026.
- **FEMA National Risk Index v1.20 (Dec 2025), county table:** FEMA's ArcGIS feature service. The old hazards.fema.gov zip was retired.
- **CPI-U annual averages:** hard-coded in `flood.py`.
- **Census ACS 2019–2023 (B19013 income, B25077 home value):** keyless summary files from www2.census.gov.
- **FEMA disaster declarations (v2):** OpenFEMA API, read by `refresh.py --storms`.

## This quarter's lists

- **Grow:** top 5 by modeled loss on homes without NFIP cover. Counties must be affordable and agree over the last ten years, with at most 2 per state.
- **Re-price and Pause:** top 5 by score. Counties need 300+ paid claims and must agree over the last ten years.

Backtest (lists made with data to 2014, top 25, losses vs model in 2015–2024):
- Grow: 0.24×.
- Pause: 2.06×.
- Re-price: 0.41×. Weak, so treat it as a review list.
- All counties: 1.02×.

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
- **By county count:** flagged-high counties ran high 24.6% of the time, vs 12.5% for flagged-low and a 17.9% base rate.
- **By dollars:** 86% of the losses above the model landed in unflagged counties.

So the tool is a pricing signal and needs a concentration cap.
