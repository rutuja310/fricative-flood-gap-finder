"""Scheduled refresh for Flood Gap Finder, called by the n8n workflow (flood/n8n/flood_refresh_workflow.json).

Modes (one per run; each prints a JSON summary on stdout for n8n):
  --monthly     If FEMA has republished NFIP claims or insured-share data since the last run, re-fetch, re-run
                the pipeline and write a "what changed" report. Prints {"updated": false} when nothing is new.
  --quarterly   Re-run and write this quarter's plan: top 5 grow / re-price / pause, with what changed since
                the last quarterly report.
  --storms      Check FEMA disaster declarations (floods, hurricanes, tropical and coastal storms) since the
                last check. Alert when a declared county is on a plan list, or when many counties are declared.
                Schedules follow-up re-runs 30, 60 and 90 days out, because NFIP claims arrive with a lag.
  --followups   Run any follow-ups that are due and report which declared counties changed call.
Options:
  --force       Re-run even if FEMA has not republished.
  --no-fetch    Re-use flood/raw/ instead of downloading again (for demos and tests).
  --since DATE  For --storms: look back to DATE (YYYY-MM-DD) instead of the last check.
  --publish     Afterwards, commit flood/out and flood/demo and push, so the public site (GitHub Pages) updates.

Every run writes a Markdown report to flood/out/reports/ and updates flood/out/reports/latest.json, which the
live demo reads.
"""
import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "src", ROOT / "out"
REPORTS = OUT / "reports"
VINTAGE = OUT / "fema_vintage.json"
STORM_STATE = REPORTS / "storm_state.json"
API = "https://www.fema.gov/api/open"
LABEL = {"grow": "Grow", "re-price": "Re-price", "pause": "Pause", "hold": "Hold"}

STORM_TYPES = {"Flood", "Hurricane", "Tropical Storm", "Coastal Storm", "Typhoon"}
MANY_COUNTIES = 25        # a declaration this wide is an alert on its own
MANY_CHANGES = 10         # this many changed calls in one run is an alert
FOLLOWUP_DAYS = (30, 60, 90)
RECENT_DAYS = 90         # the demo's storm panel shows declarations from this many days back


def today():
    return dt.date.today()


def get_json(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def fema_vintage():
    """Last refresh dates of the two FEMA datasets the scores depend on."""
    out = {}
    for name, ver in [("NfipClaims", 3), ("NfipResidentialPenetrationRates", 1)]:
        q = urllib.parse.quote(f"name eq '{name}' and version eq {ver}")
        d = get_json(f"{API}/v1/DataSets?$filter={q}&$select=name,version,lastRefresh,lastDataSetRefresh")
        rows = d.get("DataSets", [])
        out[name] = (rows[0].get("lastDataSetRefresh") or rows[0].get("lastRefresh")) if rows else None
    return out


def load_calls(path):
    if not path.exists():
        return None
    return pd.read_csv(path, dtype={"fips": str}).set_index("fips")


def summary():
    return json.loads((OUT / "summary.json").read_text())


def run_pipeline(fetch):
    if fetch:
        subprocess.run(["sh", str(SRC / "fetch_raw.sh")], check=True)
    subprocess.run([sys.executable, str(SRC / "run_flood.py")], check=True, stdout=subprocess.DEVNULL)


def plan_ids(s):
    return {k: [x["fips"] for x in v] for k, v in s["plan"].items()}


def diff_calls(before, after, names):
    """Counties whose call changed, largest score move first."""
    if before is None:
        return []
    j = before.join(after, lsuffix="_old", rsuffix="_new", how="inner")
    ch = j[j.action_old != j.action_new].copy()
    ch["move"] = (ch.chr_cred_new - ch.chr_cred_old).abs()
    return [{"fips": f, "county": names.get(f, f), "from": r.action_old, "to": r.action_new,
             "score_from": round(float(r.chr_cred_old), 2), "score_to": round(float(r.chr_cred_new), 2)}
            for f, r in ch.sort_values("move", ascending=False).iterrows()]


def county_names():
    d = pd.read_csv(OUT / "county_model_gap.csv", dtype={"fips": str}).set_index("fips")
    return {f: f"{r.county}, {r.state}" for f, r in d.iterrows()}, d


def plan_md(s):
    lines = []
    for key, title in [("grow", "Grow: put agents and marketing here"), ("re-price", "Re-price: take to pricing"),
                       ("pause", "Pause: stop new business or tighten terms")]:
        lines.append(f"\n### {title}\n")
        for i, x in enumerate(s["plan"][key], 1):
            lines.append(f"{i}. **{x['county']}, {x['state']}.** {x['headline']} Still true recently? {x['recent']}")
    return "\n".join(lines)


def changes_md(changes, limit=25):
    if not changes:
        return "No county changed call."
    rows = ["| County | From | To | Score then → now |", "| --- | --- | --- | --- |"]
    rows += [f"| {c['county']} | {LABEL[c['from']]} | {LABEL[c['to']]} | {c['score_from']}× → {c['score_to']}× |"
             for c in changes[:limit]]
    more = f"\n\n…and {len(changes) - limit} more." if len(changes) > limit else ""
    return "\n".join(rows) + more


def list_moves(old_plan, new_plan, names):
    moves = []
    for k in new_plan:
        added = [names.get(f, f) for f in new_plan[k] if f not in old_plan.get(k, [])]
        dropped = [names.get(f, f) for f in old_plan.get(k, []) if f not in new_plan[k]]
        if added or dropped:
            moves.append({"list": k, "added": added, "dropped": dropped})
    return moves


def save_report(kind, md, payload):
    REPORTS.mkdir(parents=True, exist_ok=True)
    stamp = today().isoformat()
    path = REPORTS / f"{kind}-{stamp}.md"
    path.write_text(md)
    latest_path = REPORTS / "latest.json"
    latest = json.loads(latest_path.read_text()) if latest_path.exists() else {}
    latest[kind] = {**payload, "date": stamp, "report": str(path.relative_to(ROOT.parent))}
    latest_path.write_text(json.dumps(latest, indent=1, default=str))
    # The live demo reads these too
    demo = ROOT / "demo" / "data.json"
    if demo.exists():
        d = json.loads(demo.read_text())
        d["reports"] = latest
        demo.write_text(json.dumps(d, separators=(",", ":"), default=str))
    return str(path)


def refresh(kind, force, fetch):
    """Shared by --monthly and --quarterly: re-run if needed, then diff against the last snapshot."""
    vint_now = fema_vintage()
    vint_old = json.loads(VINTAGE.read_text()) if VINTAGE.exists() else {}
    new_data = vint_now != vint_old
    if kind == "monthly" and not (new_data or force):
        return None, {"mode": kind, "updated": False, "fema": vint_now}
    snap = OUT / f"calls_snapshot_{kind}.csv"
    before = load_calls(snap)
    old_plan = plan_ids(summary()) if (OUT / "summary.json").exists() else {}
    prev_plan_path = OUT / f"plan_{kind}.json"
    if prev_plan_path.exists():
        old_plan = json.loads(prev_plan_path.read_text())
    run_pipeline(fetch and new_data)
    VINTAGE.write_text(json.dumps(vint_now, indent=1))
    s = summary()
    names, _ = county_names()
    after = load_calls(OUT / "calls_snapshot.csv")
    changes = diff_calls(before, after, names)
    moves = list_moves(old_plan, plan_ids(s), names)
    shutil.copy(OUT / "calls_snapshot.csv", snap)
    prev_plan_path.write_text(json.dumps(plan_ids(s)))
    alert = len(changes) >= MANY_CHANGES or any(
        c["fips"] in sum(plan_ids(s).values(), []) for c in changes)
    payload = {"mode": kind, "updated": True, "new_fema_data": new_data, "fema": vint_now,
               "changed_calls": len(changes), "changes": changes[:50], "list_moves": moves, "alert": alert,
               "plan": s["plan"]}
    return s, payload


def cmd_monthly(a):
    s, p = refresh("monthly", a.force, not a.no_fetch)
    if s is None:
        return p
    first = not p["changes"] and p["changed_calls"] == 0
    md = (f"# Flood Gap Finder: monthly refresh, {today():%B %Y}\n\n"
          f"FEMA data: claims refreshed {p['fema'].get('NfipClaims')}, insured share refreshed "
          f"{p['fema'].get('NfipResidentialPenetrationRates')}.\n\n"
          f"**{p['changed_calls']} counties changed call since the last monthly run.**"
          + (" (First run: nothing to compare yet.)" if first else "") + "\n\n"
          + changes_md(p["changes"]) + "\n\n## Changes to this quarter's lists\n\n"
          + ("\n".join(f"- {LABEL[m['list']]}: added {', '.join(m['added']) or 'none'}; dropped "
                       f"{', '.join(m['dropped']) or 'none'}" for m in p["list_moves"]) or "None.")
          + "\n\n## Current lists\n" + plan_md(s))
    p["report"] = save_report("monthly", md, {k: v for k, v in p.items() if k != "plan"})
    return {k: v for k, v in p.items() if k not in ("plan", "changes")}


def cmd_quarterly(a):
    s, p = refresh("quarterly", True, not a.no_fetch)
    q = (today().month - 1) // 3 + 1
    bt = s["list_backtest"]
    lb = bt["lists"]
    base = bt["baseline_all_counties"]
    md = (f"# Flood Gap Finder: plan for Q{q} {today().year}\n\n"
          "Three lists for this quarter. Each county comes with the reason and whether the last ten years agree.\n"
          + plan_md(s)
          + "\n\n## What changed since the last quarterly plan\n\n" + changes_md(p["changes"])
          + "\n\n## How lists like these did before (made with data to 2014, checked on 2015–2024)\n\n"
          "| List (top 25) | Next decade, losses vs model | Ran above the model |\n| --- | --- | --- |\n"
          + "\n".join(f"| {LABEL[k.split('_')[0]]} | {v['next_decade_dollars_vs_model']:.2f}× | "
                      f"{v['share_ran_above_model']:.0%} |" for k, v in lb.items() if k.endswith("top25"))
          + f"\n| All counties (baseline) | {base['next_decade_dollars_vs_model']:.2f}× | "
            f"{base['share_ran_above_model']:.0%} |\n\n"
          "Grow and Pause lists held up; the Re-price list did not beat the baseline, so treat it as a list to "
          "review with pricing, not a decision.\n")
    p["report"] = save_report("quarterly", md, {k: v for k, v in p.items() if k != "plan"})
    return {k: v for k, v in p.items() if k not in ("plan", "changes")}


def declarations(since):
    q = urllib.parse.quote(f"declarationDate ge '{since}T00:00:00.000Z'")
    url = (f"{API}/v2/DisasterDeclarationsSummaries?$filter={q}&$top=5000&$orderby=declarationDate%20desc"
           "&$select=disasterNumber,declarationDate,incidentType,declarationTitle,state,fipsStateCode,"
           "fipsCountyCode,designatedArea,declarationType")
    rows = get_json(url).get("DisasterDeclarationsSummaries", [])
    keep = [r for r in rows if r["incidentType"] in STORM_TYPES or "FLOOD" in (r["declarationTitle"] or "").upper()]
    events = {}
    for r in keep:
        e = events.setdefault(r["disasterNumber"], {"disaster": r["disasterNumber"], "title": r["declarationTitle"],
                                                    "type": r["incidentType"], "state": r["state"],
                                                    "declared": r["declarationDate"][:10],
                                                    "kind": r["declarationType"], "fips": set()})
        if r["fipsCountyCode"] and r["fipsCountyCode"] != "000":
            e["fips"].add(r["fipsStateCode"] + r["fipsCountyCode"])
    return sorted(events.values(), key=lambda e: e["declared"], reverse=True)


def cmd_storms(a):
    state = json.loads(STORM_STATE.read_text()) if STORM_STATE.exists() else {"seen": [], "followups": []}
    since = a.since or state.get("last_check") or (today() - dt.timedelta(days=30)).isoformat()
    events = [e for e in declarations(since) if e["disaster"] not in state["seen"]]
    names, d = county_names()
    s = summary()
    on_list = {f: k for k, v in plan_ids(s).items() for f in v}
    out_events, alert = [], False
    for e in events:
        rows = []
        for f in sorted(e["fips"]):
            if f in d.index:
                x = d.loc[f]
                rows.append({"fips": f, "county": names[f], "call": x.action, "on_list": on_list.get(f),
                             "insured_model": None if pd.isna(x.insured_model) else round(float(x.insured_model)),
                             "pen": None if pd.isna(x.pen) else round(float(x.pen), 4)})
        hits = [r for r in rows if r["on_list"]]
        wide = len(rows) >= MANY_COUNTIES
        alert = alert or bool(hits) or wide
        out_events.append({**{k: v for k, v in e.items() if k != "fips"}, "counties": len(rows),
                           "on_list": hits, "calls": {c: sum(r["call"] == c for r in rows) for c in LABEL},
                           "alert": bool(hits) or wide, "top_exposure": sorted(
                               rows, key=lambda r: r["insured_model"] or 0, reverse=True)[:5]})
        decl = dt.date.fromisoformat(e["declared"])
        for days in FOLLOWUP_DAYS:
            state["followups"].append({"disaster": e["disaster"], "title": e["title"],
                                       "due": (decl + dt.timedelta(days=days)).isoformat(), "done": False,
                                       "counties": sorted(e["fips"]),
                                       "calls_at_declaration": {r["fips"]: r["call"] for r in rows}})
        state["seen"].append(e["disaster"])
    # Keep a rolling 90-day list so the demo always shows recent storms; alerts fire only on new ones.
    for e in out_events:
        e["new"] = True
    keep = (today() - dt.timedelta(days=RECENT_DAYS)).isoformat()
    store = {str(k): {**v, "new": False} for k, v in state.get("events", {}).items() if v["declared"] >= keep}
    store.update({str(e["disaster"]): e for e in out_events})
    state["events"] = store
    recent = sorted(store.values(), key=lambda e: e["declared"], reverse=True)
    state["last_check"] = today().isoformat()
    REPORTS.mkdir(parents=True, exist_ok=True)
    STORM_STATE.write_text(json.dumps(state, indent=1))
    md = [f"# Flood Gap Finder: storm watch, {today():%d %B %Y}\n",
          f"New FEMA declarations for floods, hurricanes and tropical or coastal storms since {since}: "
          f"**{len(out_events)}**" + (", **alert**." if alert else ", no alert.")
          + f" {len(recent)} declarations in the last {RECENT_DAYS} days in total.\n",
          "Claims from a storm reach FEMA's data over the following months, so calls are re-checked "
          f"{', '.join(map(str, FOLLOWUP_DAYS))} days after each declaration.\n"]
    for e in out_events:
        md.append(f"\n## {e['title'].title()} ({e['state']}, {e['type']}, declared {e['declared']})"
                  + (" · ALERT" if e["alert"] else "") + "\n")
        md.append(f"{e['counties']} counties declared: " + ", ".join(
            f"{n} {LABEL[c].lower()}" for c, n in e["calls"].items() if n) + ".\n")
        if e["on_list"]:
            md.append("**On this quarter's lists:** " + "; ".join(
                f"{r['county']} ({LABEL[r['on_list']]} list)" for r in e["on_list"]) + ".\n")
        if e["top_exposure"]:
            md.append("Largest insured exposure in the area: " + "; ".join(
                f"{r['county']} ({LABEL[r['call']]})" for r in e["top_exposure"]) + ".\n")
    payload = {"mode": "storms", "since": since, "events": recent, "new_events": len(out_events), "alert": alert}
    payload["report"] = save_report("storms", "\n".join(md), payload)
    return {"mode": "storms", "since": since, "events": len(out_events), "alert": alert,
            "alert_events": [e["title"] for e in out_events if e["alert"]], "report": payload["report"]}


def cmd_followups(a):
    if not STORM_STATE.exists():
        return {"mode": "followups", "due": 0}
    state = json.loads(STORM_STATE.read_text())
    due = [f for f in state["followups"] if not f["done"] and f["due"] <= today().isoformat()]
    if not due:
        return {"mode": "followups", "due": 0}
    run_pipeline(not a.no_fetch)
    names, d = county_names()
    results, alert = [], False
    for f in due:
        changed = [{"county": names.get(x, x), "from": f["calls_at_declaration"][x], "to": d.loc[x, "action"]}
                   for x in f["counties"] if x in d.index and x in f["calls_at_declaration"]
                   and d.loc[x, "action"] != f["calls_at_declaration"][x]]
        alert = alert or bool(changed)
        results.append({"disaster": f["disaster"], "title": f["title"], "due": f["due"], "changed": changed})
        f["done"] = True
    STORM_STATE.write_text(json.dumps(state, indent=1))
    md = [f"# Flood Gap Finder: storm follow-up, {today():%d %B %Y}\n"]
    for r in results:
        md.append(f"\n## {r['title'].title()} (follow-up due {r['due']})\n")
        md.append(("Calls changed: " + "; ".join(f"{c['county']} {LABEL[c['from']]} → {LABEL[c['to']]}"
                                                for c in r["changed"])) if r["changed"]
                  else "No declared county has changed call yet; claims may still be arriving.")
    payload = {"mode": "followups", "results": results, "alert": alert}
    payload["report"] = save_report("followups", "\n".join(md), payload)
    return {"mode": "followups", "due": len(due), "alert": alert, "report": payload["report"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    for m in ("monthly", "quarterly", "storms", "followups"):
        g.add_argument(f"--{m}", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--since")
    ap.add_argument("--publish", action="store_true")
    a = ap.parse_args()
    fn = {"monthly": cmd_monthly, "quarterly": cmd_quarterly, "storms": cmd_storms, "followups": cmd_followups}
    mode = next(m for m in fn if getattr(a, m))
    result = fn[mode](a)
    if a.publish:
        result["published"] = publish_site(mode)
    print(json.dumps(result, default=str))


def publish_site(mode):
    """Commit the refreshed outputs and push; GitHub Pages republishes within a minute or two."""
    repo = ROOT.parent
    git = lambda *args: subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)  # noqa: E731
    git("add", "flood/out", "flood/demo")
    if git("diff", "--cached", "--quiet").returncode == 0:
        return False
    git("commit", "-m", f"Flood Gap Finder: {mode} refresh {today().isoformat()}")
    return git("push").returncode == 0


if __name__ == "__main__":
    main()
