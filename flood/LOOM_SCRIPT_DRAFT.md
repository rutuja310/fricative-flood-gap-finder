# Loom script draft (5 min) and hand-off

Draft spoken text, about 845 words, roughly 5:15 at 155 words a minute. Lead with the recommendation; each part answers a question in the brief.

## Hand-off: still to do
1. Paste this script into the Loom script doc (https://claude.ai/artifact/HBS1jnxXFPzNZisXVJgH11), replacing the old 12-slide version. Demo link: https://rutuja310.github.io/fricative-flood-gap-finder/
2. Trim about 15 seconds if needed (for example the Buncombe line).
3. Optional: add a recommendation slide to the deck, and choose the slide 7 title.
4. Done already: the memo (387 words) and its Source list tab (28 claims, each labeled fact or inference) are in the memo doc.

## Part 1 · Slides 1–2 · 0:00–1:10 · The decision, the recommendation, why now

Hi, I'm Rutuja. This tool is for one person: the head of underwriting at a young private flood insurer, who decides each quarter which counties to grow in, which to re-price and where to stop writing. My recommendation, up front. Pause new business in five river counties where insured homes have lost 13 to 50 times what FEMA's flood model predicts. Send the re-price list to pricing as a review list, not a decision. And treat the grow list as a screen, capped at two counties per state.

Why this decision, and why now? Only 3 in 100 US homes have federal flood cover, against 64 billion dollars a year of modeled flood damage. That gap is the private market's opportunity, and it's opening now: the NFIP couldn't write new policies in the October 2025 shutdown, and the largest private writer quadrupled its book in four years. Growing that fast on a model nobody has checked against claims piles the book up where the next storm lands. So the real question isn't how to sell more. It's where.

## Part 2 · Slides 3–4 · 1:10–1:35 · Who decides and why it's hard today

Today that call runs on agent demand and a vendor model. Big carriers have analytics teams to check the model; a young MGA has neither the team nor the claims history.

So I aimed at a better decision, not a faster report: five counties per call each quarter, each with one sentence of evidence. The new information is 48 years of public claims, county by county, against the model.

## Part 3 · Slide 5, then the live demo · 1:35–2:30 · The tool making the call (clicks: Pause → Wilkinson, Re-price → Dixie, Grow → Los Angeles, Storm watch, Downloads)

Let me show you.

Start with the call that protects the book. These five pause counties sit on the Mississippi and Missouri rivers. Wilkinson, Mississippi: even leaving out its worst year, insured homes lose 50 times what the model predicts, across more than a thousand claims. That's a pattern, not one storm.

Re-price: Dixie, Florida, at three times the model. That list goes to pricing to review.

Grow: Los Angeles. Claims have run at 0.4 times the model, and only half a percent of homes have NFIP cover. That's headroom, though Maricopa and Pima are a warning I'll come back to.

The storm watch reads FEMA declarations daily. Replaying Hurricane Isaias, 10 of the 15 Florida counties declared were already on our lists. And the plan downloads as a spreadsheet for the team's meeting.

## Part 4 · Slides 6–8 · 2:30–3:25 · Why trust the call

Behind the site: a monthly refresh, the quarterly plan and the daily storm watch, each sending a report.

Why trust it? It joins six public sources on the county code: claims, insured share, FEMA's model, Census income, disaster declarations and prices. Then the test. I built the lists with data only through 2014 and checked the next ten years. Pause counties lost twice what the model predicted; 72 percent ran above it, against 26 percent of all counties. Grow counties lost a quarter of it. Re-price didn't beat the baseline, which is exactly why I recommend it as a review list.

The score: actual claims over what the model expects, worst year left out so one storm can't set a price, and pulled toward average when data is thin. Buncombe, North Carolina goes from 3.3 to 2.5 times: re-price, not pause.

## Part 5 · Slide 9 · 3:25–4:30 · Sources dropped, where the data didn't line up, where AI helped and was checked

How I got here matters as much as the tool. Sources I dropped: private flood data and vendor models, because they aren't public; NAIC's private flood data, because it's state level only. Where the data didn't line up: the original pitch said 45 of 52 billion dollars of loss sat in under-insured counties; on current FEMA data it's 32.5 of 66. Western North Carolina looked like 12 to 20 times the model; it's 1.8, and 0.6 without Helene. One storm. That's why the worst year comes out. And ranking by dollars just picked the Katrina and Sandy counties, so lists rank by evidence.

AI helped me pull and join 2.7 million claims and build the pipeline and site in days. But I had to check it. It repeated the pitch's numbers until I recomputed them. It wrote a baseline of 1.00 before computing it; the real number is 1.02. And it offered New Orleans as a pause example, which is a hold once Katrina is left out. My rule became: no number on a slide I haven't recomputed.

## Part 6 · Slide 10 · 4:30–5:15 · Where it breaks, another week, what would change the call

Where it breaks: it's FEMA's model, not the insurer's; a county is too coarse to price a home; and NFIP claims aren't their book. History can't see the next big storm: 86 percent of losses above the model hit counties we hadn't flagged. That's why growth is capped and there's a storm watch. And dry counties top the grow list, so it's a screen, not a plan.

With another week: validate with three to five underwriters, fix the grow list with disaster history and demand signals, and let insurers test their own model against our claims file.

What would change my call: if their vendor model already prices the pause counties above FEMA's, or underwriters wouldn't act on the grow list. Thanks for watching.

