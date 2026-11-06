# Methodology

How the Private Flood Insurance Gap Finder scores every US county, makes each call, builds the quarterly lists, and how we tested it. Numbers are from the run of 5 November 2026 (`flood/out/summary.json`). The code is `flood/src/flood.py`, and `flood/src/run_flood.py` runs everything end to end.

What this is, and isn't: a public-data screen that shows where insured flood losses have run well above or below FEMA's flood model, refreshed as often as FEMA publishes claims. It is not a pricing model and doesn't replace a licensed catastrophe model; it works best next to one.

## 1. Data

| Input | Source | Used for |
|---|---|---|
| NFIP claims, 1978–2025 | OpenFEMA v3 `NfipClaims` (2.7M rows; county code, census block group, named flood event, year, building and contents paid) | What insured homes actually lost |
| Modeled flood loss | FEMA National Risk Index v1.20 (December 2025), county and census-tract tables: inland (`IFLD_EALB`) plus coastal (`CFLD_EALB`) expected annual building loss | What the model says they should lose |
| Insured share today | OpenFEMA v1 `NfipResidentialPenetrationRates` (residential policies in force ÷ residential structures) | Scaling the model to insured homes |
| Insured share in the past | OpenFEMA v3 `NfipPolicies`: residential policies in force on 1 July 2014 and 1 July 2019 | Point-in-time backtest |
| Prices | BLS CPI-U, US city average (`CUUR0000SA0`), annual | Restating every claim in 2024 dollars |
| Income and home value | Census ACS 2019–2023 5-year, tables B19013 (median household income) and B25077 (median home value) | Affordability check on the grow list; context |
| Housing units by tract | Census ACS 2019–2023 5-year, table B25001 | Tract-level insured share |
| Tract crosswalk | Census 2010→2020 tract relationship file | Moving 2010-coded claims and policies onto 2020 tracts |
| Disaster declarations | OpenFEMA v2 `DisasterDeclarationsSummaries` | The daily storm watch |
| Storm records | NOAA Storm Events details, 2015–2024, and the NWS zone-to-county file | The storm-years-out test |

Everything is public. Fetch scripts: `fetch_raw.sh`, `fetch_claims_api.sh`, `fetch_policies_api.sh`, `fetch_tracts.sh`.

## 2. The score

For each of 3,232 counties:

1. **Expected loss on insured homes** = NRI building flood loss (inland + coastal) × the county's NFIP insured share. NRI models all buildings; the insured share scales it to the homes that actually file NFIP claims.
2. **Actual loss** = average yearly NFIP building claims paid, in 2024 dollars.
3. **Worst year left out.** The county's single worst year is dropped and the rest averaged (the "chronic" rate), so one storm can't set a county's price.
4. **Relative to the US norm.** The county's ratio (actual ÷ expected) is divided by the national ratio for the same years (1.25 overall). This nets out whatever is common to every county, such as insured homes sitting mostly in mapped flood zones, or more policies in earlier decades than today's share implies.
5. **Pulled toward average when data is thin.** Limited-fluctuation credibility: weight z = √(paid claims ÷ 1,082), capped at 1. Score = z × relative ratio + (1 − z) × 1.0. A county with 1,082+ paid claims keeps its own ratio; one with 100 claims keeps about 30% of it.

The result is one number per county: 1.0× means losses ran at the model; 3× means three times what the model predicts, even with the worst year out.

Worked example: Wilkinson County, MS. Claims since 1978, worst year dropped, divided by the model's expected loss on insured homes and by the US norm: about 50×. With over a thousand paid claims, credibility keeps nearly all of it, so the call is pause.

## 3. The calls

| Call | Rule | Counties |
|---|---|---|
| Pause | score ≥ 3 | 183 |
| Re-price | 1.5 ≤ score < 3 | 380 |
| Grow | score ≤ 0.8, under 10% of homes insured, and modeled loss over $1M a year | 224 |
| Hold | everything else, or no modeled loss or insured-share figure | 2,445 |

**Does the last decade agree?** Each call is checked against 2016–2025 alone (same score, same norm, those years only). Re-price and pause need the recent ratio at or above 1.0; grow needs it at or below 1.0. With fewer than 30 paid claims in the decade, the check is skipped.

## 4. This quarter's lists

The live site shows the top 5 for each call:

- **Pause and re-price:** ranked by score (strength of evidence), with at least 300 paid claims and a recent decade that agrees. Ranking by dollars above the model was tried and rejected: it picked counties hit once by a catastrophe (Katrina, Sandy) that then went quiet.
- **Grow:** ranked by the size of the prize, modeled loss on homes without NFIP cover (NRI loss × (1 − insured share)), a proxy for the premium pool. A county must:
  - **pass the affordability check:** median household income of at least $50,000, and modeled flood loss per home no more than 2% of that income. Below either, uptake is likely slow or premiums would strain;
  - **not be contradicted by the last decade** (recent ratio not above 1.0);
  - **respect the state cap:** at most 2 counties per state, so the list never sits in one storm path.

Known weakness: dry counties (Maricopa and Pima, AZ) reach the grow list because big modeled loss and few insured homes make a large prize. The fix is to add disaster history, demand signals and storm forecasts (next steps).

## 5. The storm watch

`refresh.py --storms` reads FEMA's disaster declarations every day. It keeps flood, hurricane, tropical storm, coastal storm and typhoon declarations (or any titled "flood"), matches the declared counties against the current pause, re-price and grow lists, and sends an alert. It then schedules re-checks 30, 60 and 90 days later, because NFIP claims reach OpenFEMA with a lag of weeks to months. FEMA's flood model doesn't change after a storm; it's updated on a release schedule (roughly yearly). So the claims are what move.

The storm watch uses FEMA declarations, not NOAA. NOAA storm records are used only in the storm-years-out test (section 6.4).

## 6. How we tested it

All tests use the same idea: score with claims through 2014 only, then see what happened in 2015–2024, which the score never saw.

### 6.1 List backtest

Build the three lists as of 2014 with the same rules (top 25 each), then compare each list's 2015–2024 losses with the model at the US norm for that decade. Pricing at the model scores 1.0× by construction.

| List (top 25) | 2015–24 losses ÷ model | Share that ran above the model |
|---|---|---|
| Grow | 0.16× | 4% |
| Re-price | 0.91× | 28% |
| All counties (30+ claims) | 1.01× | 27% |
| Pause | 2.24× | 76% |

Pause counties lost more than twice the model; grow counties a sixth of it. Re-price didn't beat the baseline, so it's a review list, not a decision.

### 6.2 Point in time

The first version used today's insured share for every year, which leaks later information into the 2014 lists. The point-in-time version scores with NFIP policies in force on 1 July 2014 and judges outcomes with those in force on 1 July 2019 (mid test decade), each divided by today's home count. Policies were pulled from `NfipPolicies` one day of effective dates at a time; a policy counts if it took effect in the 12 months before the snapshot and ends (or was cancelled) after it.

| | Today's share for every year | Point in time |
|---|---|---|
| Grow (top 25) | 0.24× | 0.16× |
| Re-price (top 25) | 0.41× | 0.91× |
| Pause (top 25) | 2.06× | 2.24× |
| All counties | 1.02× | 1.01× |

Grow and pause hold or strengthen. Still not point in time: FEMA's model (NRI didn't exist in 2014) and the home counts.

### 6.3 County blind test

1,521 counties with 30+ paid claims through 2014. "Flagged high" = 2014 score ≥ 1.5; "flagged low" = ≤ 0.8; "ran high" = 2015–2024 losses ≥ 1.5× the model at the US norm.

| | Today's share | Point in time |
|---|---|---|
| Flagged high that ran high | 24.6% | 29.2% |
| Any county | 17.9% | 20.5% |
| Flagged low | 12.5% | 11.8% |
| Same number picked by modeled loss alone | 9.5% | 10.6% |
| Rank correlation, 2014 score vs 2015–24 | 0.25 | 0.32 |
| Losses above the model that hit unflagged counties | 86% | 82% |

The gap repeats: counties flagged high run high again 2.5 times as often as counties flagged low. But most surprise dollars land in counties nobody flagged.

### 6.4 Storm years out (NOAA)

Why do unflagged counties take most of the surprise? NOAA Storm Events records hurricanes, tropical storms, tropical depressions and storm surge by forecast zone; the NWS zone-to-county file maps them to counties. That gives 2,244 county-years with a tropical or surge event in 2015–2024, across 790 counties.

- **80%** of the losses above the model in unflagged counties came in those storm years.
- With each county's storm years taken out of 2015–2024 (the rest averaged), the point-in-time blind test gives: flagged high ran high **45%**, any county 33%, flagged low **12%** (3.8 times as often, up from 2.5). Rank correlation 0.34. The base rate rises because storm dollars also leave the national norm.

So the score reads lasting gaps well; what it misses is mostly where the next hurricane lands. That's what the state cap and the storm watch are for. This split explains the miss; it doesn't remove it, since insurers still pay storm-year claims.

### 6.5 Census tracts

The same point-in-time method on 2020 census tracts: NRI tract building loss × the tract's insured share (2014 and 2019 residential policies over ACS housing units). Claims and policies coded to 2010 tracts are split across the 2020 tracts they overlap by share of land area; 97% of paid claims land on a tract.

| | Tracts (6,750 with 30+ claims) | Counties |
|---|---|---|
| Flagged high that ran high | 35% | 29% |
| Any area | 25% | 21% |
| Flagged low | 14% | 12% |
| Rank correlation | 0.24 | 0.32 |
| Losses above the model in unflagged areas | 69% | 82% |

Inside counties the county score didn't flag, flagged tracts ran high 44% of the time (base 26%, flagged low 17%) and held 24% of those counties' surprise losses. Finer areas find part of what the county view misses, with a noisier ranking because many tracts have few claims. The tract test is in `summary.json` and here only; the live tool scores counties.

## 7. Limits

- **FEMA's model, not the insurer's.** The checks run on NRI; a vendor model can be swapped in (next step: bring your own model).
- **County is too coarse to price a home.** It's a screen for where to look, not a rate.
- **NFIP claims aren't the insurer's book.** Private flood claims aren't public.
- **Insured homes aren't a random sample.** Most NFIP policies sit in mapped flood zones; the US-norm step cancels the uniform part of that bias, not all of it.
- **Thin counties.** Credibility pulls them toward 1.0, so a county with few policies is held, not judged.
- **History can't see the next big storm.** See 6.4.

## 8. Reproduce

```bash
sh flood/src/fetch_raw.sh
sh flood/src/fetch_policies_api.sh   # optional, hours: point-in-time tests
sh flood/src/fetch_tracts.sh         # optional, about a minute: tract and storm tests
python3 flood/src/run_flood.py
```

Results land in `flood/out/summary.json`: `list_backtest` and `holdout` (today's share), `list_backtest_pit` and `holdout_pit` (point in time), `holdout_storm_years_out`, `holdout_tracts`.
