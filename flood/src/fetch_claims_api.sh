#!/bin/sh
# Fallback for when the claims parquet download is refused: page the OpenFEMA v3 NfipClaims API
# (10,000 rows per call, seven columns) into flood/raw/claims/claims_api.csv.
set -e
R="$(cd "$(dirname "$0")/.." && pwd)/raw/claims"
mkdir -p "$R/pages"
API='https://www.fema.gov/api/open/v3/NfipClaims'
SEL='countyCode,censusGeoid,floodEvent,yearOfLoss,amountPaidOnBuildingClaim,amountPaidOnContentsClaim,id'
N=$(curl -sS "$API?\$top=1&\$select=id&\$inlinecount=allpages" | sed -n 's/.*"count":\([0-9]*\).*/\1/p')
echo "rows: $N"
skip=0
while [ "$skip" -lt "$N" ]; do
  f="$R/pages/p$(printf %07d "$skip").csv"
  if [ ! -s "$f" ]; then
    for t in 1 2 3 4; do
      curl -sS --fail -o "$f" "$API?\$select=$SEL&\$orderby=id&\$top=10000&\$skip=$skip&\$format=csv" && break
      sleep $((t * 4))
    done
  fi
  skip=$((skip + 10000))
done
# Concatenate, keeping one header
first=1
for f in "$R"/pages/p*.csv; do
  if [ $first = 1 ]; then cat "$f"; first=0; else tail -n +2 "$f"; fi
done > "$R/claims_api.csv"
wc -l "$R/claims_api.csv"
