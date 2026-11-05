"""County flood model-gap analysis: NFIP paid claims vs FEMA NRI modeled loss.

Inputs (downloaded by fetch_raw.sh into flood/raw/):
  nri/NRI_Table_Counties.csv      FEMA National Risk Index, county table
  claims/FimaNfipClaims.parquet   OpenFEMA NFIP redacted claims, 1978-present
  pen/penetration.csv             OpenFEMA NfipResidentialPenetrationRates

Core measure, per county:
  insured_model = NRI modeled annual building loss (inland + coastal flood, EALB)
                  x share of homes insured with NFIP (resPenetrationRate)
  ratio         = average yearly NFIP building claims paid (real dollars) / insured_model
A ratio above 1 means insured homes there have lost more than the model implies.
"""
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"

# CPI-U, US city average, annual averages (BLS series CUUR0000SA0). 2025 = Jan-Sep 2025 average.
CPI = {
    1978: 65.2, 1979: 72.6, 1980: 82.4, 1981: 90.9, 1982: 96.5, 1983: 99.6, 1984: 103.9, 1985: 107.6,
    1986: 109.6, 1987: 113.6, 1988: 118.3, 1989: 124.0, 1990: 130.7, 1991: 136.2, 1992: 140.3,
    1993: 144.5, 1994: 148.2, 1995: 152.4, 1996: 156.9, 1997: 160.5, 1998: 163.0, 1999: 166.6,
    2000: 172.2, 2001: 177.1, 2002: 179.9, 2003: 184.0, 2004: 188.9, 2005: 195.3, 2006: 201.6,
    2007: 207.3, 2008: 215.3, 2009: 214.5, 2010: 218.1, 2011: 224.9, 2012: 229.6, 2013: 233.0,
    2014: 236.7, 2015: 237.0, 2016: 240.0, 2017: 245.1, 2018: 251.1, 2019: 255.7, 2020: 258.8,
    2021: 271.0, 2022: 292.7, 2023: 304.7, 2024: 313.7, 2025: 321.5,
}
BASE_YEAR = 2024          # all dollars restated to 2024
FIRST, LAST = 1978, 2025  # full calendar years of claims used
TRAIN = (1978, 2014)
TEST = (2015, 2024)

# Counties FEMA declared for Helene individual assistance in western NC (DR-4827), mountain region.
WNC = {
    "37005": "Alleghany", "37009": "Ashe", "37011": "Avery", "37021": "Buncombe", "37023": "Burke",
    "37027": "Caldwell", "37087": "Haywood", "37089": "Henderson", "37099": "Jackson",
    "37111": "McDowell", "37115": "Madison", "37121": "Mitchell", "37149": "Polk",
    "37161": "Rutherford", "37175": "Transylvania", "37189": "Watauga", "37193": "Wilkes",
    "37199": "Yancey",
}
HIGH = {"Very High", "Relatively High"}


def _num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def load_nri():
    f = next((RAW / "nri").glob("NRI_Table_Counties*.csv"))
    n = pd.read_csv(f, dtype={"STCOFIPS": str}, low_memory=False)
    n["fips"] = n.STCOFIPS.str.zfill(5)
    out = pd.DataFrame({
        "fips": n.fips, "county": n.COUNTY, "state": n.STATEABBRV,
        "population": _num(n.POPULATION), "build_value": _num(n.BUILDVALUE),
        "ealb": _num(n.IFLD_EALB) + _num(n.CFLD_EALB),
        "ealt": _num(n.IFLD_EALT) + _num(n.CFLD_EALT),
        "ealb_inland": _num(n.IFLD_EALB), "ealb_coastal": _num(n.CFLD_EALB),
        "ifld_rating": n.get("IFLD_RISKR"), "cfld_rating": n.get("CFLD_RISKR"),
    })
    out["high_flood"] = out.ifld_rating.isin(HIGH) | out.cfld_rating.isin(HIGH)
    return out.set_index("fips")


def load_pen():
    p = pd.read_csv(RAW / "pen" / "penetration.csv", dtype=str)
    fcol = next(c for c in p.columns if c.lower() in ("fipscode", "countycode", "countyfips", "fips"))
    rate = pd.to_numeric(p["resPenetrationRate"], errors="coerce")
    if rate.max() > 1.5:  # published as a percent
        rate = rate / 100
    out = pd.DataFrame({"fips": p[fcol].str.zfill(5), "pen": rate,
                        "pen_sfha": pd.to_numeric(p.get("resPenetrationRateSfha"), errors="coerce"),
                        "policies": pd.to_numeric(p.get("resContractsInForce"), errors="coerce"),
                        "homes": pd.to_numeric(p.get("totalResStructures"), errors="coerce")})
    return out.dropna(subset=["pen"]).drop_duplicates("fips").set_index("fips")


SNAP_THEN, SNAP_TEST = 2014, (2019,)   # 1 July snapshots of NFIP policies in force (2019: mid test decade)
RESIDENTIAL = (1, 2, 3, 11, 12, 13, 14, 15, 16)    # occupancyType codes for homes


def load_policies(digits=5):
    """Residential NFIP policies in force on 1 July of each snapshot year, by county (fips x year; digits=11:
    by census tract, as coded), from fetch_policies_api.sh. None when they haven't been fetched."""
    d = RAW / "policies"
    if not any(d.glob("*/*.csv")):
        return None
    day = lambda c: f"TRY_CAST(substr({c}, 1, 10) AS DATE)"  # noqa: E731
    q = f"""
      WITH p AS (SELECT CAST(regexp_extract(filename, '(\\d{{4}})/[^/]+$', 1) AS INT) AS snap, *
                 FROM read_csv('{d}/*/*.csv', filename=true, all_varchar=true))
      SELECT snap, substr(censusGeoid, 1, {digits}) AS fips, sum(coalesce(TRY_CAST(policyCount AS INT), 1)) AS n
      FROM p
      WHERE TRY_CAST(occupancyType AS INT) IN {RESIDENTIAL} AND length(censusGeoid) >= {digits}
        AND {day('policyTerminationDate')} > make_date(snap, 7, 1)
        AND coalesce({day('cancellationDateOfFloodPolicy')} > make_date(snap, 7, 1), true)
      GROUP BY 1, 2"""
    return duckdb.sql(q).df().pivot(index="fips", columns="snap", values="n").fillna(0)


def load_claims(tract=False):
    """County x year totals of paid NFIP claims, nominal dollars (tract=True: by census tract, as coded)."""
    pq = RAW / "claims" / "NfipClaimsV3.parquet"
    f = pq if pq.exists() else RAW / "claims" / "claims_api.csv"
    src = f"'{f}'" if f.suffix == ".parquet" else f"read_csv('{f}', all_varchar=true)"
    year = "yearOfLoss"
    num = lambda c: f"coalesce(TRY_CAST({c} AS DOUBLE), 0)"  # noqa: E731
    key = "substr(censusGeoid, 1, 11)" if tract else "lpad(CAST(countyCode AS VARCHAR), 5, '0')"
    col = "censusGeoid" if tract else "countyCode"
    q = f"""
      SELECT {key} AS fips, TRY_CAST({year} AS INT) AS year,
             count(*) AS claims,
             sum(CASE WHEN {num('amountPaidOnBuildingClaim')} > 0 THEN 1 ELSE 0 END) AS paid_claims,
             sum({num('amountPaidOnBuildingClaim')}) AS bldg,
             sum({num('amountPaidOnContentsClaim')}) AS cont
      FROM {src} WHERE {col} IS NOT NULL AND length({col}) >= {11 if tract else 1} GROUP BY 1, 2"""
    c = duckdb.sql(q).df()
    c = c[(c.year >= FIRST) & (c.year <= LAST)].copy()
    k = c.year.map(lambda y: CPI[BASE_YEAR] / CPI[y])
    c["bldg_real"], c["cont_real"] = c.bldg * k, c.cont * k
    return c


def window(c, lo, hi, drop=()):
    w = c[(c.year >= lo) & (c.year <= hi) & ~c.year.isin(drop)]
    years = hi - lo + 1 - len([y for y in drop if lo <= y <= hi])
    g = w.groupby("fips")[["bldg_real", "cont_real", "paid_claims"]].sum()
    return g.bldg_real / years, (g.bldg_real + g.cont_real) / years, g.paid_claims


def chronic(c, lo, hi):
    """Average yearly building paid with each county's single worst year left out (the 'chronic' run rate),
    and that worst year's amount and calendar year."""
    w = c[(c.year >= lo) & (c.year <= hi)]
    g = w.groupby("fips").bldg_real
    worst = g.max()
    worst_year = w.loc[g.idxmax(), ["fips", "year"]].set_index("fips").year
    return (g.sum() - worst) / (hi - lo), worst, worst_year


def credibility(n_claims, full=1082):
    """Limited-fluctuation credibility weight (1,082 claims = full credibility)."""
    return np.minimum(1.0, np.sqrt(n_claims / full))


def build():
    nri, pen, c = load_nri(), load_pen(), load_claims()
    df = nri.join(pen, how="left")
    df["insured_model"] = df.ealb * df.pen
    # Point-in-time insured share for the backtest: policies in force in 2014 (what was known then) and in
    # 2019, mid test decade, each over today's home count.
    pol = load_policies()
    if pol is not None and SNAP_THEN in pol and all(y in pol for y in SNAP_TEST):
        h = df.homes.where(df.homes > 0)
        df["pen_then"] = pol[SNAP_THEN].reindex(df.index).fillna(0) / h
        df["pen_test"] = pol[list(SNAP_TEST)].mean(axis=1).reindex(df.index).fillna(0) / h
        df["insured_then"], df["insured_test"] = df.ealb * df.pen_then, df.ealb * df.pen_test

    full_b, full_bc, full_n = window(c, FIRST, LAST)
    ex_b, _, _ = window(c, FIRST, LAST, drop=(2024,))
    tr_b, _, tr_n = window(c, *TRAIN)
    te_b, _, te_n = window(c, *TEST)
    for name, s in [("paid_bldg", full_b), ("paid_bc", full_bc), ("paid_bldg_ex2024", ex_b),
                    ("paid_train", tr_b), ("paid_test", te_b)]:
        df[name] = s.reindex(df.index).fillna(0.0)
    df["claims_n"] = full_n.reindex(df.index).fillna(0)
    df["claims_train"] = tr_n.reindex(df.index).fillna(0)
    df["claims_test"] = te_n.reindex(df.index).fillna(0)
    df["paid_2024"] = c[c.year == 2024].groupby("fips").bldg_real.sum().reindex(df.index).fillna(0)
    for tag, (lo, hi) in [("", (FIRST, LAST)), ("_train", TRAIN), ("_test", TEST)]:
        ch, worst, wy = chronic(c, lo, hi)
        df["paid_chronic" + tag] = ch.reindex(df.index).fillna(0.0)
        df["worst" + tag] = worst.reindex(df.index).fillna(0.0)
        df["worst_year" + tag] = wy.reindex(df.index)

    m = df.insured_model.where(df.insured_model > 0)
    df["ratio"] = df.paid_bldg / m
    df["ratio_ex2024"] = df.paid_bldg_ex2024 / m
    df["ratio_train"] = df.paid_train / m
    df["ratio_test"] = df.paid_test / m
    # Relative gap: county ratio / national ratio over the same years. This nets out what is common to every
    # county (insured homes sit mostly in the mapped high-risk zone; NFIP had more policies in earlier decades
    # than today's penetration implies) and leaves how far a county runs above or below the model's usual miss.
    ok = df.insured_model > 0
    for col, paid in [("rel", "paid_bldg"), ("rel_ex2024", "paid_bldg_ex2024"),
                      ("rel_train", "paid_train"), ("rel_test", "paid_test"),
                      ("chr", "paid_chronic"), ("chr_train", "paid_chronic_train"), ("chr_test", "paid_chronic_test")]:
        nat = df.loc[ok, paid].sum() / df.loc[ok, "insured_model"].sum()
        df[col] = df[paid] / m / nat
        df.attrs[f"nat_{col}"] = nat
    # Worst single year, in years of expected insured loss at the US norm ("one bad year = N normal years").
    df["shock"] = df.worst / (m * df.attrs["nat_rel"])
    z = credibility(df.claims_n)
    df["cred"] = z
    df["ratio_cred"] = z * df.rel.fillna(1.0) + (1 - z) * 1.0     # all years, for display
    df["chr_cred"] = z * df.chr.fillna(1.0) + (1 - z) * 1.0       # worst year left out: drives the call

    # "Still true recently?": the same relative gap over the last ten full years only.
    rb, _, rn = window(c, *RECENT)
    df["paid_recent"] = rb.reindex(df.index).fillna(0.0)
    df["claims_recent"] = rn.reindex(df.index).fillna(0)
    df.attrs["nat_recent"] = df.loc[ok, "paid_recent"].sum() / df.loc[ok, "insured_model"].sum()
    df["rel_recent"] = df.paid_recent / m / df.attrs["nat_recent"]

    # Demand context: household income and home value (Census ACS 2019-2023), and a rough affordability check.
    attrs = dict(df.attrs)
    df = df.join(load_acs(), how="left")
    df.attrs.update(attrs)
    df["loss_per_home"] = df.ealb / df.homes.where(df.homes > 0)
    df["loss_pct_income"] = df.loss_per_home / df.income
    df["afford_flag"] = (df.income < AFFORD_INCOME) | (df.loss_pct_income > AFFORD_SHARE)
    decide(df)
    return df, c


RECENT = (2016, 2025)        # last ten full years
AFFORD_INCOME = 50_000       # median household income below this: uptake will be slow
AFFORD_SHARE = 0.02          # modeled flood loss per home above 2% of median income: premiums will strain
LABEL = {"grow": "Grow", "re-price": "Re-price", "pause": "Pause", "hold": "Hold"}


def load_acs():
    """Median household income (B19013) and median home value (B25077), ACS 5-year 2019-2023, by county."""
    out = []
    for table, name in [("b19013", "income"), ("b25077", "homeval")]:
        a = pd.read_csv(RAW / "acs" / f"acsdt5y2023-{table}.dat", sep="|", dtype=str)
        a = a[a.GEO_ID.str.startswith("0500000US")]
        out.append(pd.Series(pd.to_numeric(a.iloc[:, 1], errors="coerce").values,
                             index=a.GEO_ID.str[-5:].values, name=name))
    return pd.concat(out, axis=1)


def action(r):
    """Per-county call for a private flood writer: four plain rules on the chronic gap (worst year left out,
    shrunk toward 1 when claims are few), plus headroom for growth. Returns (call, reason); the reason
    completes the sentence "<Call> <County>: <reason>." """
    if not (r.insured_model > 0) or pd.isna(r.pen):
        return "hold", "there is no modeled loss or NFIP insured-share figure for this county"
    g, pen = r.chr_cred, r.pen
    wy = "" if pd.isna(r.worst_year) else f" ({int(r.worst_year)})"
    if g >= 3:
        return "pause", (f"even leaving out its worst year{wy}, insured homes here lose {g:.1f}× what the flood "
                         f"model predicts, across {int(r.claims_n):,} paid claims")
    if g >= 1.5:
        return "re-price", (f"insured homes here have lost {g:.1f}× what the flood model predicts, even leaving "
                            f"out the worst year{wy}")
    if g <= 0.8 and pen < 0.10 and r.ealb > 1e6:
        return "grow", (f"claims have run at {g:.1f}× the flood model and only {pen:.1%} of homes have NFIP "
                        f"cover")
    return "hold", f"claims run close to the flood model ({g:.1f}×), or there are too few to tell"


def recency(r):
    """Does the last decade agree with the call? Returns (ok, sentence)."""
    if r.claims_recent < 30 or pd.isna(r.rel_recent):
        return None, f"Too few paid claims in {RECENT[0]}–{RECENT[1]} ({int(r.claims_recent)}) to check."
    v = r.rel_recent
    if r.action in ("re-price", "pause"):
        ok = v >= 1.0
        return ok, (f"{'Yes' if ok else 'No'}: {v:.1f}× the model in {RECENT[0]}–{RECENT[1]} "
                    f"({'still above' if ok else 'back below'} it).")
    if r.action == "grow":
        ok = v <= 1.0
        return ok, (f"{'Yes' if ok else 'No'}: {v:.1f}× the model in {RECENT[0]}–{RECENT[1]} "
                    f"({'still at or below' if ok else 'above'} it).")
    return None, f"{v:.1f}× the model in {RECENT[0]}–{RECENT[1]}."


def decide(df):
    """Calls, headline sentences and the recency check, in place."""
    df["action"], df["reason"] = zip(*[action(r) for r in df.itertuples()])
    df["headline"] = [f"{LABEL[a]} {n}: {why}." for a, n, why in zip(df.action, df.county, df.reason)]
    df["why"] = df.headline
    df["recent_ok"], df["recent_note"] = zip(*[recency(r) for r in df.itertuples()])
    nat = df.attrs.get("nat_rel", 1.0)
    # Yearly dollars above (or below) the model at the chronic gap: what mis-pricing costs, county by county.
    df["excess"] = df.insured_model * nat * (df.chr_cred - 1)
    # Size of the prize for growth: modeled loss on homes without NFIP cover (a premium-pool proxy).
    df["prize"] = df.ealb * (1 - df.pen)
    return df


def plan(df, n=5, grow_state_cap=2):
    """This quarter's lists. Grow: ranked by prize, affordable, recent decade agrees, at most
    grow_state_cap counties per state so the list never sits in one storm path. Re-price / Pause: ranked
    by strength of evidence (the credibility-weighted chronic gap), 300+ paid claims, recent decade agrees.
    Ranking by dollars above the model was tested and rejected: it picks catastrophe-hit counties (Katrina,
    Sandy) that went quiet in the next decade."""
    out = {}
    g = df[(df.action == "grow") & ~df.afford_flag.fillna(False) & (df.recent_ok != False)]  # noqa: E712
    picks, per_state = [], {}
    for f, r in g.sort_values("prize", ascending=False).iterrows():
        if per_state.get(r.state, 0) < grow_state_cap:
            picks.append(f)
            per_state[r.state] = per_state.get(r.state, 0) + 1
        if len(picks) == n:
            break
    out["grow"] = picks
    for a in ("re-price", "pause"):
        s = df[(df.action == a) & (df.claims_n >= 300) & (df.recent_ok == True)]  # noqa: E712
        out[a] = s.sort_values("chr_cred", ascending=False).head(n).index.tolist()
    return out


def scores_as_of(df, c, end_year):
    """Re-score every county with claims through end_year only: same model, same rules, same insured share
    (today's: the one figure not available historically). Recency = the last ten years before end_year."""
    sub = c[c.year <= end_year]
    a = df.copy()
    ch, worst, wy = chronic(sub, FIRST, end_year)
    n = sub.groupby("fips").paid_claims.sum().reindex(a.index).fillna(0)
    ok = a.insured_model > 0
    m = a.insured_model.where(ok)
    paid = ch.reindex(a.index).fillna(0)
    a["chr"] = paid / m / (paid[ok].sum() / a.loc[ok, "insured_model"].sum())
    full_b, _, _ = window(sub, FIRST, end_year)
    full_b = full_b.reindex(a.index).fillna(0)
    a.attrs["nat_rel"] = full_b[ok].sum() / a.loc[ok, "insured_model"].sum()
    a["claims_n"] = n
    a["worst_year"] = wy.reindex(a.index)
    a["chr_cred"] = credibility(n) * a.chr.fillna(1) + (1 - credibility(n))
    rb, _, rn = window(sub, end_year - 9, end_year)
    rb = rb.reindex(a.index).fillna(0)
    a["claims_recent"] = rn.reindex(a.index).fillna(0)
    a["rel_recent"] = rb / m / (rb[ok].sum() / a.loc[ok, "insured_model"].sum())
    return decide(a)


def point_in_time(df):
    """The county table with the insured share each backtest step could have known: 2014 policies in force
    to score, the test decade's to judge the outcome. Needs build() to have found the policy snapshots."""
    t = df.copy()
    for col, paid, m in [("chr_train", "paid_chronic_train", "insured_then"), ("rel_test", "paid_test", "insured_test"),
                         ("chr_test", "paid_chronic_test", "insured_test")]:
        ok = t[m] > 0
        t.attrs[f"nat_{col}"] = nat = t.loc[ok, paid].sum() / t.loc[ok, m].sum()
        t[col] = t[paid] / t[m].where(ok) / nat
    return t


def backtest_lists(df, c, end_year=2014, sizes=(5, 25), pit=False):
    """Make the lists as of end_year, then see how those counties ran in the next ten years (2015-2024),
    against the model at the US norm for that decade. Pricing at the model = 1.0x by construction.
    pit=True scores with the 2014 insured share and judges with the test decade's (point_in_time)."""
    if pit:
        df = point_in_time(df)
        a = scores_as_of(df.assign(insured_model=df.insured_then, pen=df.pen_then), c, end_year)
        m_test = df.insured_test
    else:
        a, m_test = scores_as_of(df, c, end_year), df.insured_model
    nat_test = df.attrs["nat_rel_test"]
    res = {"as_of": end_year, "outcome_years": list(TEST), "point_in_time": pit, "lists": {}}
    for k in sizes:
        lists = plan(a, n=k)
        for name, fips in lists.items():
            sub = df.loc[fips]
            exp = (m_test[fips] * nat_test).sum()
            res["lists"][f"{name}_top{k}"] = {
                "counties": [{"fips": f, "county": df.loc[f, "county"], "state": df.loc[f, "state"],
                              "score_then": round(float(a.loc[f, "chr_cred"]), 2),
                              "next_decade": None if pd.isna(df.loc[f, "rel_test"]) else
                              round(float(df.loc[f, "rel_test"]), 2)} for f in fips],
                "next_decade_dollars_vs_model": float(sub.paid_test.sum() / exp) if exp > 0 else None,
                "share_ran_above_model": float((sub.rel_test >= 1).mean()),
                "share_ran_high_1_5x": float((sub.rel_test >= 1.5).mean()),
            }
    base = df[(m_test > 0) & (df.claims_train >= 30)]
    res["baseline_all_counties"] = {
        "next_decade_dollars_vs_model": float(base.paid_test.sum() / (m_test[base.index] * nat_test).sum()),
        "share_ran_above_model": float((base.rel_test >= 1).mean()),
        "share_ran_high_1_5x": float((base.rel_test >= 1.5).mean()),
    }
    return res


def call_as_of(df, c, end_year, fips):
    """The call the tool would have made using only claims through end_year (same rules, same model)."""
    sub = c[c.year <= end_year]
    ch, _, _ = chronic(sub, FIRST, end_year)
    n = sub.groupby("fips").paid_claims.sum()
    ok = df.insured_model > 0
    paid = ch.reindex(df.index).fillna(0)
    nat = paid[ok].sum() / df.loc[ok, "insured_model"].sum()
    rel = paid / df.insured_model.where(ok) / nat
    z = credibility(n.reindex(df.index).fillna(0))
    g = z * rel.fillna(1) + (1 - z)
    out = []
    for f in fips:
        r = df.loc[f].copy()
        r["chr_cred"], r["claims_n"] = g[f], n.get(f, 0)
        a, why = action(r)
        out.append({"fips": f, "county": r.county, "state": r.state, "as_of": end_year,
                    "score": round(float(g[f]), 2), "call": a})
    return out


def headline_check(df):
    """The original claim: high-risk counties under 5% insured hold $45B of $52B expected loss."""
    nat_t, nat_b = df.ealt.sum(), df.ealb.sum()
    sel = df.high_flood & (df.pen < 0.05)
    return {
        "national_ealt": nat_t, "national_ealb": nat_b,
        "n_high_flood": int(df.high_flood.sum()), "n_selected": int(sel.sum()),
        "selected_ealt": df.loc[sel, "ealt"].sum(), "selected_ealb": df.loc[sel, "ealb"].sum(),
        "selected_share_ealt": df.loc[sel, "ealt"].sum() / nat_t,
        "selected_share_ealb": df.loc[sel, "ealb"].sum() / nat_b,
        "selected_insured_model": df.loc[sel, "insured_model"].sum(),
    }


def holdout(df, min_claims=30):
    """Blind test. Score counties on 1978-2014 claims only (chronic gap, worst year left out), then check
    2015-2024. 'Ran high' = 2015-2024 losses >= 1.5x the model, relative to the US norm for that decade."""
    d = df[(df.insured_model > 0) & (df.claims_train >= min_claims)].copy()
    d = d.dropna(subset=["chr_train", "rel_test"])
    zt = credibility(d.claims_train)
    d["train_cred"] = zt * d.chr_train + (1 - zt)
    flag, lo_flag = d.train_cred >= 1.5, d.train_cred <= 0.8
    hi = d.rel_test >= 1.5
    hi_chr = d.chr_test >= 1.5
    d["exp_test"] = d.insured_model * df.attrs["nat_rel_test"]
    # Model-only baseline: the same number of counties picked by modeled loss alone.
    top_model = d.ealb.rank(pct=True) >= 1 - flag.mean()
    dollars = lambda msk: float(d.loc[msk, "paid_test"].sum() / d.loc[msk, "exp_test"].sum())  # noqa: E731
    res = {
        "n": int(len(d)), "flagged": int(flag.sum()), "flagged_low": int(lo_flag.sum()),
        "base_rate_high": float(hi.mean()),
        "hit_rate_flagged": float(hi[flag].mean()),
        "hit_rate_low_flag": float(hi[lo_flag].mean()),
        "hit_rate_model_only": float(hi[top_model].mean()),
        "chronic_hit_flagged": float(hi_chr[flag].mean()), "chronic_hit_low": float(hi_chr[lo_flag].mean()),
        "chronic_base": float(hi_chr.mean()),
        "spearman": float(d.chr_train.rank().corr(d.rel_test.rank())),
        "dollars_flagged": dollars(flag), "dollars_low": dollars(lo_flag), "dollars_mid": dollars(~flag & ~lo_flag),
    }
    res["lift"] = res["hit_rate_flagged"] / res["base_rate_high"]
    res["lift_vs_low"] = res["hit_rate_flagged"] / res["hit_rate_low_flag"]
    # Quintiles of the 1978-2014 score
    d["quint"] = pd.qcut(d.train_cred.rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    q = d.groupby("quint", observed=True).apply(lambda g: pd.Series({
        "n": len(g), "score_median": g.train_cred.median(), "share_ran_high": (g.rel_test >= 1.5).mean(),
        "share_chronic_high": (g.chr_test >= 1.5).mean(),
        "dollars_vs_expected": g.paid_test.sum() / g.exp_test.sum()}))
    res["quintiles"] = q.reset_index().to_dict("records")
    # Where the 2015-2024 surprise dollars landed: losses above expectation, by 1978-2014 group
    excess = (d.paid_test - d.exp_test).clip(lower=0)
    res["excess_share_low_or_normal"] = float(excess[~flag].sum() / excess.sum())
    top20 = d.sort_values("paid_test", ascending=False).head(20)
    res["top20_test_flagged_before"] = int((top20.train_cred >= 1.5).sum())
    res["top20_test"] = top20[["county", "state", "train_cred", "rel_test", "paid_test", "worst_year_test"]] \
        .reset_index().to_dict("records")
    return res, d


# ---- Finer and fairer tests: census tracts, and storm years taken out (public data, fetch_tracts.sh) ----

TROPICAL = ("Hurricane", "Hurricane (Typhoon)", "Tropical Storm", "Tropical Depression", "Storm Surge/Tide")


def tract_xwalk(tracts):
    """Map tract codes as found in claims and policies (2010 or 2020 tracts) onto 2020 tracts. A 2020 code maps to
    itself; a 2010-only code is split across the 2020 tracts it overlaps, by share of its land area."""
    rel = pd.read_csv(RAW / "geo" / "tab20_tract20_tract10_natl.txt", sep="|", dtype=str,
                      usecols=["GEOID_TRACT_20", "GEOID_TRACT_10", "AREALAND_PART"])
    rel["w"] = rel.AREALAND_PART.astype(float)
    rel["w"] /= rel.groupby("GEOID_TRACT_10").w.transform("sum")
    rel = rel[~rel.GEOID_TRACT_10.isin(tracts) & (rel.w > 0)]
    same = pd.DataFrame({"t_in": list(tracts), "t20": list(tracts), "w": 1.0})
    return pd.concat([same, rel.rename(columns={"GEOID_TRACT_10": "t_in", "GEOID_TRACT_20": "t20"})[["t_in", "t20", "w"]]])


def _to_2020(frame, xw, by, cols):
    m = frame.merge(xw, left_on="fips", right_on="t_in")
    m[cols] = m[cols].mul(m.w, axis=0)
    return m.drop(columns=["fips"]).rename(columns={"t20": "fips"}).groupby(["fips"] + by, as_index=False)[cols].sum()


def build_tracts(df):
    """The county method run on 2020 census tracts, point in time: NRI tract building flood EAL x the tract's
    insured share (residential policies in force July 2014 to score, July 2019 to judge, over ACS 2019-2023
    housing units). Returns (tracts, tract x year claims) shaped like build()'s, or None if not fetched."""
    nri = RAW / "nri_tracts" / "NRI_Table_CensusTracts.csv"
    cl = RAW / "claims" / "claims_api.csv"
    if not nri.exists() or not cl.exists() or "censusGeoid" not in cl.open().readline():
        return None
    n = pd.read_csv(nri, dtype={"TRACTFIPS": str, "STCOFIPS": str})
    t = pd.DataFrame({"fips": n.TRACTFIPS, "county_fips": n.STCOFIPS.str.zfill(5),
                      "ealb": _num(n.IFLD_EALB) + _num(n.CFLD_EALB)}).set_index("fips")
    t = t.join(df[["county", "state"]], on="county_fips")
    acs = pd.read_csv(RAW / "acs" / "acsdt5y2023-b25001.dat", sep="|", dtype=str)
    acs = acs[acs.GEO_ID.str.startswith("1400000US")]
    t["homes"] = pd.to_numeric(acs.set_index(acs.GEO_ID.str[9:]).B25001_E001, errors="coerce").reindex(t.index)
    xw = tract_xwalk(set(t.index))

    pol = load_policies(11).reset_index().melt(id_vars="fips", var_name="snap", value_name="n")
    pol = _to_2020(pol, xw, ["snap"], ["n"]).pivot(index="fips", columns="snap", values="n")
    h = t.homes.where(t.homes > 0)
    t["pen_then"] = (pol[SNAP_THEN].reindex(t.index).fillna(0) / h).clip(upper=1)
    t["pen_test"] = (pol[list(SNAP_TEST)].mean(axis=1).reindex(t.index).fillna(0) / h).clip(upper=1)
    t["insured_then"], t["insured_test"] = t.ealb * t.pen_then, t.ealb * t.pen_test

    c = _to_2020(load_claims(tract=True), xw, ["year"], ["claims", "paid_claims", "bldg_real", "cont_real"])
    tr_b, _, tr_n = window(c, *TRAIN)
    te_b, _, te_n = window(c, *TEST)
    t["paid_test"], t["claims_train"] = te_b.reindex(t.index).fillna(0), tr_n.reindex(t.index).fillna(0)
    for tag, (lo, hi) in [("_train", TRAIN), ("_test", TEST)]:
        ch, worst, wy = chronic(c, lo, hi)
        t["paid_chronic" + tag] = ch.reindex(t.index).fillna(0.0)
        t["worst_year" + tag] = wy.reindex(t.index)
    t["insured_model"] = t.insured_test
    t = point_in_time(t)
    t.attrs["claims_coded"] = float(c.paid_claims.sum())
    return t, c


def load_storms():
    """County x year pairs with a NOAA tropical storm, hurricane or storm surge event, 2015-2024. NOAA codes
    these by forecast zone, so zones are mapped to the counties they cover. None if not fetched."""
    d = RAW / "storms"
    if not any(d.glob("details_*.csv.gz")):
        return None
    zc = pd.read_csv(d / "zone_county.dbx", sep="|", header=None, dtype=str,
                     names=["st", "zone", "cwa", "name", "sz", "county", "fips", "tz", "fe", "lat", "lon"])
    zc = zc.assign(state_fips=zc.fips.str[:2], zone=zc.zone.str.zfill(3))[["state_fips", "zone", "fips"]]
    e = pd.concat(pd.read_csv(f, dtype=str, usecols=["YEAR", "STATE_FIPS", "CZ_TYPE", "CZ_FIPS", "EVENT_TYPE"])
                  for f in sorted(d.glob("details_*.csv.gz")))
    e = e[e.EVENT_TYPE.isin(TROPICAL)].assign(state_fips=lambda x: x.STATE_FIPS.str.zfill(2),
                                              cz=lambda x: x.CZ_FIPS.str.zfill(3), year=lambda x: x.YEAR.astype(int))
    county = e[e.CZ_TYPE == "C"].assign(fips=lambda x: x.state_fips + x.cz)
    zone = e[e.CZ_TYPE == "Z"].merge(zc, left_on=["state_fips", "cz"], right_on=["state_fips", "zone"])
    return pd.concat([county[["fips", "year"]], zone[["fips", "year"]]]).drop_duplicates()


def storm_split(df, c, storms):
    """The county blind test (point in time) with each county's tropical-storm years taken out of 2015-2024,
    and how much of the surprise in unflagged counties came in those years."""
    t = point_in_time(df)
    w = c[(c.year >= TEST[0]) & (c.year <= TEST[1])].merge(storms.assign(storm=True), on=["fips", "year"], how="left")
    w["storm"] = w.storm.fillna(False).astype(bool)
    n_storm = storms.groupby("fips").year.nunique().reindex(t.index).fillna(0)
    calm = w[~w.storm].groupby("fips").bldg_real.sum().reindex(t.index).fillna(0) / (TEST[1] - TEST[0] + 1 - n_storm).where(n_storm < 10)
    storm_paid = w[w.storm].groupby("fips").bldg_real.sum().reindex(t.index).fillna(0) / (TEST[1] - TEST[0] + 1)
    ok = t.insured_test > 0
    nat = calm[ok].sum() / t.loc[ok, "insured_test"].sum()
    calm_t = t.assign(paid_test=calm, rel_test=calm / t.insured_test.where(ok) / nat, chr_test=calm / t.insured_test.where(ok) / nat,
                      insured_model=t.insured_test)
    calm_t.attrs["nat_rel_test"] = nat
    res, _ = holdout(calm_t)
    _, d = holdout(t.assign(insured_model=t.insured_test))
    flag = d.train_cred >= 1.5
    excess = (d.paid_test - d.exp_test).clip(lower=0)
    share = (storm_paid.reindex(d.index) / d.paid_test.where(d.paid_test > 0)).fillna(0)
    res["storm_county_years"] = int(len(storms))
    res["counties_with_storm"] = int((n_storm > 0).sum())
    res["unflagged_excess_in_storm_years"] = float((excess * share)[~flag].sum() / excess[~flag].sum())
    return res


def tract_holdout(df, c, tracts, tc):
    """The blind test on census tracts, plus the question the county test leaves open: inside counties the
    county score did not flag, does the tract score find where the 2015-2024 surprise landed?"""
    res, d = holdout(tracts)
    _, dc = holdout(point_in_time(df).assign(insured_model=lambda x: x.insured_test))
    in_flagged_county = d.county_fips.map(dc.train_cred >= 1.5).fillna(False).astype(bool)
    inside = d[~in_flagged_county]
    flag, hi = inside.train_cred >= 1.5, inside.rel_test >= 1.5
    excess = (inside.paid_test - inside.exp_test).clip(lower=0)
    res["in_unflagged_counties"] = {
        "tracts": int(len(inside)), "flagged": int(flag.sum()), "base_rate_high": float(hi.mean()),
        "hit_rate_flagged": float(hi[flag].mean()), "hit_rate_low_flag": float(hi[inside.train_cred <= 0.8].mean()),
        "excess_share_in_flagged_tracts": float(excess[flag].sum() / excess.sum())}
    res["tracts_total"] = int(len(tracts))
    res["claims_on_a_tract"] = float(tc.paid_claims.sum() / c.paid_claims.sum())
    return res
