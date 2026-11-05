#!/bin/sh
# Downloads the public flood inputs into flood/raw/ (kept out of git).
#  - NRI v1.20 county table: FEMA's ArcGIS feature service (the hazards.fema.gov zip was retired in 2026)
#  - NFIP claims: OpenFEMA v3 parquet; if the CDN refuses it, fetch_claims_api.sh pages the API instead
#  - NFIP residential penetration rates: OpenFEMA API
#  - Median home value and household income: Census ACS 5-year API
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
R="$(cd "$HERE/.." && pwd)/raw"
mkdir -p "$R/nri" "$R/claims" "$R/pen" "$R/acs"

S='https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/National_Risk_Index_Counties/FeatureServer/0/query'
F='STCOFIPS,STATEABBRV,COUNTY,POPULATION,BUILDVALUE,IFLD_EALB,IFLD_EALT,IFLD_RISKR,CFLD_EALB,CFLD_EALT,CFLD_RISKR,NRI_VER'
for off in 0 2000; do
  curl -sS --fail -o "$R/nri/part$off.json" "$S?where=1%3D1&outFields=$F&returnGeometry=false&orderByFields=STCOFIPS&resultOffset=$off&resultRecordCount=2000&f=json"
done
python3 -I - "$R/nri" <<'EOF'
import json, sys, csv, pathlib
d = pathlib.Path(sys.argv[1]); rows = []
for p in sorted(d.glob("part*.json")):
    rows += [f["attributes"] for f in json.load(open(p))["features"]]
with open(d / "NRI_Table_Counties.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print("nri counties:", len(rows))
EOF

curl -sS --fail -o "$R/claims/NfipClaimsV3.parquet" "https://www.fema.gov/about/reports-and-data/openfema/v3/NfipClaimsV3.parquet" \
  || { rm -f "$R/claims/NfipClaimsV3.parquet"; sh "$HERE/fetch_claims_api.sh"; }

curl -sS --fail -o "$R/pen/penetration.csv" 'https://www.fema.gov/api/open/v1/NfipResidentialPenetrationRates?$top=5000&$format=csv'

# B19013 median household income; B25077 median owner-occupied home value
for t in b19013 b25077; do
  curl -sS --fail -o "$R/acs/acsdt5y2023-$t.dat" "https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/data/5YRData/acsdt5y2023-$t.dat"
done
