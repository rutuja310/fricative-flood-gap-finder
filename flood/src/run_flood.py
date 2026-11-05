"""End-to-end flood run -> flood/out/: county table, headline check, holdout, western NC, summary.json.

Usage:  python flood/src/run_flood.py   (after sh flood/src/fetch_raw.sh)
"""
import json
import sys
import warnings
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
warnings.filterwarnings("ignore")
import flood as F  # noqa: E402
import publish  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "out"


def r(x, n=3):
    return None if pd.isna(x) else round(float(x), n)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df, claims = F.build()
    head = F.headline_check(df)
    ho, hod = F.holdout(df)
    plan = F.plan(df)
    list_bt = F.backtest_lists(df, claims)

    cols = ["county", "state", "population", "pen", "policies", "homes", "ealb", "ealb_inland", "ealb_coastal",
            "insured_model", "paid_bldg", "paid_bc", "paid_bldg_ex2024", "paid_2024", "claims_n",
            "ratio", "ratio_ex2024", "ratio_train", "ratio_test", "rel", "rel_ex2024", "rel_train", "rel_test",
            "chr", "chr_train", "chr_test", "shock", "worst", "worst_year", "cred", "ratio_cred", "chr_cred", "action", "why",
            "rel_recent", "claims_recent", "recent_ok", "recent_note", "income", "homeval", "loss_per_home",
            "loss_pct_income", "afford_flag", "excess", "prize", "ifld_rating", "cfld_rating"]
    df[cols].to_csv(OUT / "county_model_gap.csv")

    # National totals (building claims, real 2024 $) vs national insured model
    nat_paid = df.paid_bldg.sum()
    nat_paid_ex = df.paid_bldg_ex2024.sum()
    nat_model = df.insured_model.sum()
    yearly = claims.groupby("year").bldg_real.sum()

    wnc = df.loc[df.index.isin(F.WNC)].copy()
    wnc_tot = {
        "counties": int(len(wnc)), "policies": int(wnc.policies.sum()), "homes": int(wnc.homes.sum()),
        "pen": r(wnc.policies.sum() / wnc.homes.sum(), 4),
        "insured_model": r(wnc.insured_model.sum(), 0), "paid_bldg": r(wnc.paid_bldg.sum(), 0),
        "paid_bldg_ex2024": r(wnc.paid_bldg_ex2024.sum(), 0), "paid_2024": r(wnc.paid_2024.sum(), 0),
        "ratio": r(wnc.paid_bldg.sum() / wnc.insured_model.sum()),
        "ratio_ex2024": r(wnc.paid_bldg_ex2024.sum() / wnc.insured_model.sum()),
        "ratio_2024_alone": r(wnc.paid_2024.sum() / wnc.insured_model.sum()),
        "model_years_in_2024": r(wnc.paid_2024.sum() / (wnc.insured_model.sum() * df.attrs["nat_rel"]), 1),
        "rel": r(wnc.paid_bldg.sum() / wnc.insured_model.sum() / df.attrs["nat_rel"]),
        "rel_ex2024": r(wnc.paid_bldg_ex2024.sum() / wnc.insured_model.sum() / df.attrs["nat_rel_ex2024"]),
        "calls_as_of_2023": F.call_as_of(df, claims, 2023, list(wnc.index)),
        "calls_now": wnc[["county", "chr_cred", "ratio_cred", "action"]].reset_index().to_dict("records"),
    }
    wnc[cols].to_csv(OUT / "western_nc.csv")

    # Tampa Bay anchor (Flood Insurance Agency stopped new business here in Aug 2014)
    tb = {"12103": "Pinellas", "12057": "Hillsborough", "12101": "Pasco", "12115": "Sarasota", "12081": "Manatee"}
    tbd = df.loc[df.index.isin(tb)].copy()
    tbd[cols].to_csv(OUT / "tampa_bay.csv")
    tb_asof = F.call_as_of(df, claims, 2014, list(tb))

    act = df.groupby("action").agg(counties=("county", "size"), model_loss=("ealb", "sum"),
                                   insured_model=("insured_model", "sum"), homes=("homes", "sum"),
                                   policies=("policies", "sum"))
    top_reprice = df[df.action.isin(["avoid", "re-price"]) & (df.claims_n >= 300)] \
        .sort_values("insured_model", ascending=False).head(15)
    # The action counts above are on today's data; also record how many grow counties already had a shock year
    grow_shock = int(((df.action == "grow") & (df.shock >= 20)).sum())
    top_grow = df[df.action == "grow"].sort_values("ealb", ascending=False).head(15)

    summary = {
        "nri_version": "NRI v1.20 (December 2025)",
        "claims_years": [F.FIRST, F.LAST], "dollars": f"real {F.BASE_YEAR} dollars (CPI-U)",
        "counties": int(len(df)), "counties_with_pen": int(df.pen.notna().sum()),
        "claims_rows": int(claims.claims.sum()),
        "headline": {k: (r(v, 4) if isinstance(v, float) else v) for k, v in head.items()},
        "national": {"paid_bldg_per_year": r(nat_paid, 0), "paid_bldg_per_year_ex2024": r(nat_paid_ex, 0),
                     "insured_model": r(nat_model, 0), "ratio": r(nat_paid / nat_model),
                     "ratio_ex2024": r(nat_paid_ex / nat_model)},
        "yearly_paid_bldg": {int(k): r(v, 0) for k, v in yearly.items()},
        "holdout": {k: (r(v, 4) if isinstance(v, float) else v) for k, v in ho.items()},
        "western_nc": wnc_tot,
        "tampa_bay": tbd[["county", "pen", "ratio", "rel", "rel_train", "rel_test", "chr_train",
                          "ratio_cred", "chr_cred", "action", "claims_train"]].reset_index().to_dict("records"),
        "tampa_bay_calls_as_of_2014": tb_asof,
        "actions": act.reset_index().to_dict("records"),
        "grow_with_20yr_shock": grow_shock,
        "plan": {k: [plan_row(df, f) for f in v] for k, v in plan.items()},
        "list_backtest": list_bt,
        "afford_flagged_grow": int((df.action.eq("grow") & df.afford_flag.fillna(False)).sum()),
        "top_reprice": top_reprice[["county", "state", "pen", "chr_cred", "ratio_cred", "claims_n", "action"]]
        .reset_index().to_dict("records"),
        "top_grow": top_grow[["county", "state", "pen", "ealb", "homes", "policies", "chr_cred", "action"]]
        .reset_index().to_dict("records"),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    hod.to_csv(OUT / "holdout_counties.csv")
    df[["action", "chr_cred"]].to_csv(OUT / "calls_snapshot.csv")
    export_demo(df, claims, summary)
    publish.write_downloads(df, summary)
    publish.build_page()
    print(json.dumps({k: summary[k] for k in ("actions", "plan", "afford_flagged_grow")}, indent=1,
                     default=str))


def plan_row(df, f):
    x = df.loc[f]
    return {"fips": f, "county": x.county, "state": x.state, "call": x.action, "headline": x.headline,
            "score": r(x.chr_cred, 2), "recent": x.recent_note, "pen": r(x.pen, 4),
            "uninsured": None if pd.isna(x.homes) or pd.isna(x.policies) else int(x.homes - x.policies),
            "income": None if pd.isna(x.income) else int(x.income), "claims": int(x.claims_n),
            "model_loss": r(x.ealb, 0), "excess": r(x.excess, 0)}


def export_demo(df, claims, summary):
    """Compact per-county JSON for the live demo (flood/demo/data.json)."""
    yrs = list(range(F.FIRST, F.LAST + 1))
    piv = claims.pivot_table(index="fips", columns="year", values="bldg_real", aggfunc="sum").reindex(columns=yrs)
    piv = (piv.fillna(0) / 1000).round(0).astype(int)  # $ thousands
    counties = {}
    for fips, x in df.iterrows():
        rec = {
            "n": x.county, "s": x.state, "a": x.action, "w": x.why,
            "p": r(x.pen, 4), "h": None if pd.isna(x.homes) else int(x.homes),
            "pol": None if pd.isna(x.policies) else int(x.policies),
            "m": r(x.ealb, 0), "im": r(x.insured_model, 0), "pd": r(x.paid_bldg, 0),
            "g": r(x.chr_cred, 2), "gr": r(x.rel, 2), "gc": r(x.chr, 2), "sh": r(x.shock, 1),
            "wy": None if pd.isna(x.worst_year) else int(x.worst_year), "wv": r(x.worst, 0),
            "c": int(x.claims_n), "z": r(x.cred, 2), "y24": r(x.paid_2024, 0),
            "ir": x.ifld_rating, "cr": x.cfld_rating,
            "hl": x.headline, "rn": x.recent_note, "ro": None if x.recent_ok is None else bool(x.recent_ok),
            "inc": None if pd.isna(x.income) else int(x.income),
            "hv": None if pd.isna(x.homeval) else int(x.homeval),
            "lpi": r(x.loss_pct_income, 4), "af": bool(x.afford_flag) if not pd.isna(x.afford_flag) else False,
        }
        if fips in piv.index and piv.loc[fips].sum() > 0:
            rec["ys"] = piv.loc[fips].tolist()
        counties[fips] = rec
    demo = {"years": yrs, "nat_ratio": df.attrs["nat_rel"], "summary": summary, "counties": counties}
    rep = OUT / "reports" / "latest.json"   # written by refresh.py: last monthly/quarterly/storm run
    demo["reports"] = json.loads(rep.read_text()) if rep.exists() else None
    path = Path(__file__).resolve().parent.parent / "demo" / "data.json"
    path.write_text(json.dumps(demo, separators=(",", ":"), default=str))


if __name__ == "__main__":
    main()
