# Source list

The sources behind each key claim in the memo for the Private Flood Insurance Gap Finder. One line per claim. **Fact** = straight from the data or a calculation on it, or reported by a named source. **Inference** = my judgment, not yet checked with people in the industry.

| # | Claim | Source | Fact or inference |
|---|---|---|---|
| 1 | Only 3.2M of 108.8M homes (2.9%) have NFIP flood cover | OpenFEMA NFIP residential penetration rates (Aug 2026) | Fact (data) |
| 2 | FEMA's model expects $63.9B a year of flood loss to buildings ($66.3B all flood loss) | FEMA National Risk Index v1.20 (Dec 2025), inland + coastal flooding | Fact (model output) |
| 3 | The NFIP pays about $2.2B a year in building claims | OpenFEMA FimaNfipClaims v3, 1978–2025, in 2024 $ with BLS CPI-U | Fact (calculation) |
| 4 | The NFIP couldn't write new policies during the Oct 2025 shutdown | NPR, 16 Oct 2025 | Fact (reported) |
| 5 | Another NFIP lapse was threatened in Jan 2026 | Insurance Journal, 29 Jan 2026 | Fact (reported) |
| 6 | The largest private flood writer grew from ~50k to 205k+ policies in 2020–24 | Insurance Journal, 8 Oct 2024 | Fact (reported) |
| 7 | Titan Flood, Flow Flood and Wright FocusFlood write private flood | Company websites (titanflood.com, flowinsurance.com, wrightflood.com) | Fact (reported); Flow not fully confirmed |
| 8 | Young private insurers and MGAs are the right user | Secondary research | Inference |
| 9 | Today's underwriting workflow and its pain points | Secondary research | Inference |
| 10 | Big carriers have vendor models and analytics teams; young MGAs don't | Secondary research | Inference |
| 11 | 2.7M claims joined with the model for all 3,232 counties | OpenFEMA claims, NRI, penetration, ACS, joined on county FIPS | Fact (data) |
| 12 | The pitch's "$45B of $52B" is $32.5B of $66.3B on current data (189 high-risk counties under 5% insured) | NRI v1.20 + OpenFEMA penetration | Fact (calculation) |
| 13 | Western NC is 0.9% insured; Helene paid about 60 normal years of claims | OpenFEMA claims + penetration | Fact (calculation) |
| 14 | Western NC ran 1.8× the model, 0.6× with 2024 left out | OpenFEMA claims + NRI | Fact (calculation) |
| 15 | Buncombe, NC: $564K expected, $1.9M paid, 3.3× → 2.7× without 2024 → 2.5× weighted (re-price) | OpenFEMA claims + NRI + penetration | Fact (calculation) |
| 16 | Leave out the worst year; full weight at 1,082 claims | Classical credibility (Actuarial Standard of Practice 25) | Inference (method choice) |
| 17 | Lists made on 2014 data: grow counties ran 0.24× the model in 2015–24, pause 2.06× (72% above the model), re-price 0.41×, all counties 1.02× (26%) | Backtest on OpenFEMA claims + NRI | Fact (calculation); that it holds going forward is inference |
| 18 | Counties flagged high ran high 25% of the time vs 13% flagged low and 9% on the model alone | Blind test on OpenFEMA claims + NRI | Fact (calculation); forward use is inference |
| 19 | 86% of losses above the model hit counties that hadn't been flagged; 2 of the top 20 had been | Blind test | Fact (calculation) |
| 20 | Ranking by dollars picked the Katrina and Sandy counties, so lists rank by evidence | Backtest variants | Fact (calculation) |
| 21 | Pause counties run 13–50× the model (Wilkinson, MS 49.9×; Jersey, IL 39.1×; Warren 15.5×; Lincoln 15.2×; Holt 12.8×) | Tool output | Fact (calculation) |
| 22 | Dry counties like Maricopa and Pima top the grow list | Tool output | Fact (calculation); that they're low-demand is inference |
| 23 | Vendor flood models land within about 4% of NFIP losses nationally | Journal of Catastrophe Risk and Resilience, Feb 2026 | Fact (reported) |
| 24 | Isaias live run: 15 Florida counties declared, 10 on re-price or pause lists; Dixie on the re-price list | OpenFEMA Disaster Declarations Summaries v2 + tool output | Fact (calculation) |
| 25 | County median household income and home value | Census ACS 2019–2023 5-year, B19013 and B25077 | Fact (data) |
| 26 | Affordability flag: income under $50k, or modeled loss per home over 2% of income | Method choice | Inference |
| 27 | Private flood cover isn't public by county, so grow headroom is an upper bound | NAIC private flood data (state level only) | Fact (availability); headroom is inference |
| 28 | The recommendations (pause, re-price as review, grow as a screen) | All of the above | Inference |

## Data sets

- [OpenFEMA data sets](https://www.fema.gov/about/openfema/data-sets): NFIP claims (v3), NFIP policies (v3), NFIP residential penetration rates, disaster declarations summaries (v2)
- [FEMA National Risk Index](https://hazards.fema.gov/nri/): county and census-tract tables, v1.20
- [Census ACS summary files](https://www.census.gov/programs-surveys/acs/data/summary-file.html): 2019–2023 5-year tables B19013, B25077 and B25001
- [BLS Consumer Price Index](https://www.bls.gov/cpi/): CPI-U, US city average
- [NOAA Storm Events Database](https://www.ncdc.noaa.gov/stormevents/): 2015–2024 details

How each source is used and joined: [Methodology](https://rutuja310.github.io/fricative-flood-gap-finder/flood/demo/methodology.html).
