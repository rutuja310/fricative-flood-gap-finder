# Flood Gap Finder: change log

## Unreleased

### Demo is the working tool only; evidence lives in the deck (5 Nov 2026)

- **Removed from the demo:** the "Would these lists have worked?" backtest table, the headline-numbers strip, the "Does the gap repeat?" blind-test bars, and the backtest line inside each hover list.
- **Where that evidence now lives:**
  - Benchmark slide: the 2014 list backtest.
  - Methodology slide: the blind test, now including "9% picked by the model alone".
  - Architecture slide: 3,232 counties and 2.7M claims.
  - Risks slide: the 86% catastrophe finding.
  - The memo covers all of it in full.
- **Re-price subtitle** now reads "Review these with the pricing team", so the weak-backtest caveat stays without the numbers.
- **The demo keeps:** the plan bar, the map and county panel, the storm watch, downloads and reports, and the how-it-works footer.

### Shorter hover lists (5 Nov 2026)

- **One line per county.** Each county in the Grow / Re-price / Pause dropdowns shows only its rank, name and score (× model), under a small "County · Score (× model)" header. The reason and the recent-years check moved out of the list; they show in the county panel when the county is clicked, and the full reason appears as a tooltip on hover.

### Map and county panel, equal size (5 Nov 2026)

- **Layout.** The map and the county panel are two equal columns of the same height (the map is a little smaller). They stack on phones.
- **County panel, tightened:**
  - Header: county, call, and the score behind it.
  - The one-line reason, then "Still true recently?" on one line, in green when it agrees and red when it doesn't. The affordability flag shows when it applies.
  - A wider claims chart.
  - The evidence and The market side by side. Evidence: model expects / yr, actually paid / yr, gap all years, gap with the worst year left out, paid claims. Market: homes, share with NFIP cover, homes without NFIP cover, median income, median home value, modeled loss / yr.
  - FEMA's flood rating and the caveats in one footnote. "Worst year in normal years of loss" was dropped from the panel; it's still in the county download.
- **Map key.** Under the map, a key with how many counties have each call.

### Plan hover bar (5 Nov 2026)

- **Compact plan.** The three full top-5 lists at the top are now a bar of three tiles: Grow, Re-price, Pause. Each tile shows the decision, what to do, and the first three counties.
- **Dropdowns.** Hovering a tile opens its top 5 counties, with reasons, the recent-years check, "Show on map", the CSV link and the backtest line. Click or tap also opens it (phones), as does keyboard focus. Escape or a click outside closes it, and picking a county closes it and opens that county's panel. A short close delay lets the pointer move from the tile into the list.
- **Fix.** The "CSV" link no longer also toggles "Show on map".

### Public site and downloads (5 Nov 2026)

- **New repo.** The project moved to `rutuja310/fricative-flood-gap-finder`, with no Medicare files or history.
- **GitHub Pages site.** A root `index.html` redirects to `flood/demo/`, and `.nojekyll` makes GitHub serve the files as they are. `flood/demo/page.html` is the page source (also used for the Claude artifact); `publish.build_page()` wraps it into a full `flood/demo/index.html`.
- **Downloads**, rebuilt on every run by `publish.write_downloads()`:
  - `plan.xlsx`: About, Grow, Re-price and Pause sheets.
  - `plan-grow.csv`, `plan-re-price.csv`, `plan-pause.csv`.
  - `counties.xlsx` (All counties + About) and `counties.csv`: every county with its call, reason, evidence and market numbers.
- **Page buttons.** "Download the plan (Excel)", a CSV link on each list, "Download these counties (CSV)" for whatever filter or list is on the map, and a Downloads and reports panel. Inside the Claude viewer, where downloads are blocked, the links open the public site's copies.
- **`refresh.py --publish`** commits `flood/out` and `flood/demo` and pushes, so each scheduled run updates the site. The n8n workflow now uses it on all four schedules.
- **Storm watch keeps a rolling 90-day list** of declarations, so the panel isn't blanked on days with no new storms. Alerts fire only on new declarations.

### Target customers (added 5 Nov 2026)

These are the named targets for the model. They're young or growing private flood MGAs that are choosing which counties to enter, plus the insurers and reinsurers backing them. Facts come from trade-press reports and haven't been checked against each company's own disclosures. State counts come from different dates.

#### Primary users: private flood MGAs with a young book

| Company | Website | Why it fits | Source |
|---|---|---|---|
| Titan Flood | https://titanflood.com | Launched 2023 with K2 Insurance Services backing. Private residential flood through Nationwide E&S/Specialty in 15 states (FL, TX, CA, NJ and others), with expansion planned for 2026. Strongest example: new book, still entering states | [Coverager](https://coverager.com/titan-flood-partners-with-nationwide/), [Insurance Journal](https://www.insurancejournal.com/news/southeast/2023/09/28/742136.htm) |
| Flow Flood (Flow Insurance Services, Inc.) | https://flowinsurance.com (unconfirmed; inferred from its press release) | San Francisco MGA founded 2017. Runs a quoting marketplace across several private markets plus NFIP. Added capacity in FL, NJ, TX and CA during the October 2025 NFIP lapse | [Insurance Business](https://www.insurancebusinessmag.com/us/companies/flow-flood/563857/), [press release repost](https://rcnamericaflorida.blogspot.com/2025/10/flow-flood-adds-capacity-in-fl-nj-tx.html) |
| Wright Flood: FocusFlood | https://www.wrightflood.com | Large NFIP writer; FocusFlood is its newer private product backed by Lloyd's. Launched in FL, TX, NJ, SC and LA; reportedly in 19 states now | [PR Newswire](https://prnewswire.com/news-releases/wright-launches-focusflood-as-new-residential-private-flood-insurance-option-301906099.html), [The Insurer](https://www.theinsurer.com/interview/wright-floods-focusflood-enjoying-early-success-as-new-hires-eye-additional-offerings/) |
| reThought Flood | https://rethoughtflood.com | Small private flood MGA expanding distribution through Vertafore | [Beinsure](https://beinsure.com/news/rethought-flood-expands-private-flood-insurance-through-vertafore/) |
| SageSure | https://sagesure.com | Regional homeowners MGA; launched private flood in Texas in 2022 | [Insurance Journal](https://amp.insurancejournal.com/news/southcentral/2022/11/04/693581.htm) |

#### Secondary users: capacity behind the MGAs (own the concentration risk)

| Company | Website | Why it fits | Source |
|---|---|---|---|
| K2 Insurance Services | https://www.k2ins.com | Backed Titan Flood's 2023 launch | [Coverager](https://coverager.com/k2-insurance-invests-in-titan-flood/) |
| Nationwide E&S/Specialty | https://www.nationwide.com (no working E&S page found) | Carrier partner for Titan Flood | [Coverager](https://coverager.com/titan-flood-partners-with-nationwide/) |
| Palomar | https://palomarspecialty.com | Picked an MGA for its flood program | [Insurance Business](https://www.insurancebusinessmag.com/us/news/catastrophe/palomar-holdings-selects-mga-for-flood-insurance-needs-540913.aspx) |

#### Benchmark, not a target

| Company | Website | Note | Source |
|---|---|---|---|
| Neptune Flood | https://neptuneflood.com | Publicly traded market leader: 234,000+ policies (April 2025); says it holds more than a third of the private residential flood market. Has its own data and pricing tech, so less likely to buy. Its 10-K is worth reading for how a private flood writer describes underwriting and concentration | [10-K FY2025](https://www.sec.gov/Archives/edgar/data/2067129/000206712926000007/nyse-20251231.htm) |

Out of scope: large commercial flood writers (Zurich US, Berkshire Hathaway, Assurant, Liberty Mutual), which have in-house catastrophe teams and long claims histories ([Carrier Management](https://www.carriermanagement.com/news/2024/10/08/267359.htm)).

Website check, 5 Nov 2026:
- **Loaded:** Titan, Wright, reThought and K2.
- **Exists but sits behind a bot blocker:** SageSure, Neptune, Palomar and flowinsurance.com.
- **Not found:** flowflood.com doesn't resolve, and Nationwide has no working E&S page.

### Demo (5 Nov 2026)

- The selected county is now highlighted on the map, whether picked by click, search, a table row or a shared `#c<FIPS>` link. It gets a dark outline with a light halo, drawn above every other county and state line, plus a pulsing ring sized to the county so small counties are easy to spot. The pulse is off for viewers who turn off motion.

### Built (5 Nov 2026)

- **Calls.** "Avoid" is renamed "Pause".
- **County panel.** Opens with a one-line headline ("[Call] [County]: [reason]"). Below it: a "still true recently?" check on 2016–2025, median income and home value, an affordability flag on grow counties (22 of 224 flagged), and headroom labeled "homes without NFIP cover (upper bound)".
- **This quarter's plan.** Top 5 grow / re-price / pause lists sit at the top of the demo, with "Show on map".
  - Grow ranks by modeled loss on homes without NFIP cover, among affordable counties that agree over the last ten years, at most 2 per state.
  - Re-price and pause rank by strength of evidence (score), with 300+ paid claims and a recent decade that agrees.
- **Ranking choice.** Four ranking variants were tested on the 2014 backtest. Ranking by dollars at stake picked Katrina- and Sandy-hit counties that went quiet afterwards, so it was rejected.
- **Backtest of the lists.** Made with data to 2014, top 25, checked on 2015–2024:
  - Grow: 0.24× the model, 4% ran above it.
  - Pause: 2.06× the model, 72% ran above it.
  - Re-price: 0.41× the model. Weak, so it is presented as a review list.
  - Baseline (all counties): 1.02× the model, 26% ran above it.
- **Workflow.** `flood/src/refresh.py` has four modes: `--monthly` (re-run when FEMA republishes, report changed calls), `--quarterly` (the plan), `--storms` (FEMA disaster declarations; alert on list counties or 25+ counties declared) and `--followups` (30/60/90 days after a declaration). `flood/n8n/flood_refresh_workflow.json` schedules them and sends email and a Notion log; the Notion block ID and email are placeholders to fill in.
- **Live run, 5 Nov 2026.** The quarterly plan, a storm watch since 1 Aug 2026 (32 events, alert on Hurricane Isaias, Hurricane Lala, Tropical Storm Nolo and others) and a monthly check (no new FEMA data since the last run).
- **Deck.** Rebuilt as 12 slides with stick figures, icons and build-in animations. Order: problem and why now, the user and today's workflow, outcome, demo, workflow diagram, benchmark, architecture and data sources, methodology, disclaimer, risks, next steps.
- **Memo and Loom script.** Rewritten to match.

### Agreed changes (5 Nov 2026), now built

The user stays the underwriter or head of growth at a private flood insurer who wants to sell more policies. It is not the cat-model or reinsurance team.

Build:
- [x] **County panel headline.** One sentence at the top: "[Call] [County]: [reason with the key number]". For example: "Re-price Buncombe: insured homes here have lost 2.7× what the flood model predicts, even leaving out Helene." The evidence goes below it.
- [x] **"Still true recently?" line in the panel.** Show whether the county also ran above (or below) the model in 2015–2024, not just over the long run. This replaces the decade-by-decade idea. Research, 5 Nov 2026:
  - Flood pricing moved away from raw loss history: [Wharton interview with Milliman on Risk Rating 2.0](https://impact.wharton.upenn.edu/?p=7346), [Fathom](https://www.fathom.global/insight/flood-risk-and-the-modern-actuary/).
  - Ratemaking prices ordinary losses on a recent period and catastrophes on a longer-term or modeled load ([ASOP 39](http://www.actuarialstandardsboard.org/asops/treatment-catastrophe-losses-propertycasualty-insurance-ratemaking/), [ASOP 25](http://www.actuarialstandardsboard.org/wp-content/uploads/2015/03/asop025_143.pdf)).
  - Commercial models reproduce NFIP losses within about 4% nationally ([JCRR, Feb 2026](https://journalofcrr.com/research/04-01-dusseau-et-al/)). Our value is the county-level disagreement inside that total.
- [x] **Income and home value in the panel.** Census ACS 2019–2023 county tables B19013 (median household income) and B25077 (median home value), from the keyless summary files at www2.census.gov. They match 3,222 of 3,232 counties.
- [x] **Affordability flag on "grow".** When median income is under $50k, or modeled flood loss per home is over 2% of income, show "Grow, slowly: affordability will limit uptake". The four calls themselves don't change, so the blind test stays valid. Today this would flag 12 grow counties under $50k and 17 over 2% of income.
- [x] **Rename headroom to "homes without NFIP cover".** Add a caveat that private flood cover is not public by county, so headroom is an upper bound, especially in Florida and Texas. NFIP-only stays correct for the gap itself, since private policies don't create NFIP claims.
- [x] **Deck and memo.** Insured share moves from "edge" to "demand context". The edge is claims vs the model over 48 years.

Next steps (deck's last slide and memo):
- Bring your own model: the insurer loads its licensed model's county-level loss file and every gap is recomputed against it.
- Phase two: how much to re-price (a suggested rate change per county).
- Below-county (street-level) pricing. County level is the planning level for now.
- Optional: state-level private flood share from the NAIC data, if a usable table can be found.

### To do before the next push

- [x] Deck, "Who decides" slide: name Titan Flood, Flow Flood and Wright FocusFlood as example users, with the capacity partners as secondary users.
- [x] Memo, "Who decides" section: add the same names and links.
- [ ] Confirm Flow Flood's official domain and each company's current state footprint.
- [ ] Optional: skim Neptune's 10-K for how it describes underwriting and concentration limits.

## 2026-11-04

- Built the full pipeline. Claims now come through the OpenFEMA API, and the NRI v1.20 county table from FEMA's ArcGIS service.
- Changed the call to use the chronic gap: the county's worst year left out, then credibility-weighted.
- Added the 1978–2014 → 2015–2024 blind test, and "as of" calls for western NC (2023) and Tampa Bay (2014).
- Published the live demo, deck, memo and Loom script (links in `flood/README.md`).
