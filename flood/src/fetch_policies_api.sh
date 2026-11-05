#!/bin/sh
# NFIP policies in force by county at mid-year snapshots, for a point-in-time backtest (flood.py
# load_policies). OpenFEMA v3 NfipPolicies has 75M rows from 2009 on; the parquet is refused by FEMA's CDN
# and deep paging times out, so this pulls one day of policy effective dates per call (about 10,000 rows)
# for the 12 months before each 1 July snapshot, four calls at a time, into flood/raw/policies/<year>/.
# A policy is in force at the snapshot if it took effect in those 12 months and ends after it.
set -e
API='https://www.fema.gov/api/open/v3/NfipPolicies'
SEL='id,censusGeoid,policyCount,occupancyType,policyTerminationDate,cancellationDateOfFloodPolicy'

if [ "$1" = "--day" ]; then  # --day <dir> <day> <next day>: every page of one day's policies
  skip=0
  while :; do
    f="$2/$3_$(printf %06d "$skip").csv"
    if [ ! -s "$f" ]; then
      flt="policyEffectiveDate%20ge%20%27$3%27%20and%20policyEffectiveDate%20lt%20%27$4%27"
      for t in 1 2 3 4; do
        curl -sS --fail --max-time 120 -o "$f.part" "$API?\$select=$SEL&\$orderby=id&\$top=10000&\$skip=$skip&\$format=csv&\$filter=$flt" \
          && mv "$f.part" "$f" && break
        rm -f "$f.part"; sleep $((t * 5))
      done
      [ -s "$f" ] || { echo "failed: $3 skip $skip" >&2; exit 1; }
    fi
    [ "$(wc -l < "$f")" -gt 10000 ] || break
    skip=$((skip + 10000))
  done
  exit 0
fi

R="$(cd "$(dirname "$0")/.." && pwd)/raw/policies"
for y in ${SNAPSHOTS:-2014 2019}; do
  mkdir -p "$R/$y"
  python3 -I -c "
import datetime as d, sys
y = int(sys.argv[1]); a = d.date(y - 1, 7, 2)
while a <= d.date(y, 7, 1):
    b = a + d.timedelta(days=1); print(a, b); a = b" "$y" |
    xargs -P 4 -n 2 sh "$0" --day "$R/$y" || echo "snapshot $y: some days failed; run again to fill them in" >&2
  echo "snapshot $y: $(ls "$R/$y"/*.csv | wc -l | tr -d ' ') files"
done
