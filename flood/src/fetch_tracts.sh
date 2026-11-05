#!/bin/sh
# Inputs for the tract-level blind test and the storm split (flood.py load_nri_tracts, load_storms), into
# flood/raw/. Claims and policies already carry a block-group code (fetch_claims_api.sh, fetch_policies_api.sh).
#  - NRI v1.20 census tract table (2020 tracts): FEMA's ArcGIS feature service, 2,000 rows per call
#  - Housing units by tract: Census ACS 2019-2023 table B25001
#  - 2010 -> 2020 tract relationship file, for claims and policies coded to 2010 tracts
#  - NOAA Storm Events details, 2015-2024, and NWS's zone-to-county file (tropical and surge events are coded by
#    forecast zone, not county)
set -e
R="$(cd "$(dirname "$0")/.." && pwd)/raw"
mkdir -p "$R/nri_tracts" "$R/acs" "$R/geo" "$R/storms"

S='https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/National_Risk_Index_Census_Tracts/FeatureServer/0/query'
F='TRACTFIPS,STCOFIPS,POPULATION,BUILDVALUE,IFLD_EALB,CFLD_EALB,NRI_VER'
off=0
while [ "$off" -lt 86000 ]; do
  f="$R/nri_tracts/part$(printf %05d "$off").json"
  [ -s "$f" ] || curl -sS --fail --retry 4 -o "$f" "$S?where=1%3D1&outFields=$F&returnGeometry=false&orderByFields=TRACTFIPS&resultOffset=$off&resultRecordCount=2000&f=json"
  off=$((off + 2000))
done
python3 -I - "$R/nri_tracts" <<'EOF'
import json, sys, csv, pathlib
d = pathlib.Path(sys.argv[1]); rows = []
for p in sorted(d.glob("part*.json")):
    rows += [f["attributes"] for f in json.load(open(p))["features"]]
with open(d / "NRI_Table_CensusTracts.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print("nri tracts:", len(rows))
EOF

[ -s "$R/acs/acsdt5y2023-b25001.dat" ] || curl -sS --fail -o "$R/acs/acsdt5y2023-b25001.dat" \
  "https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/data/5YRData/acsdt5y2023-b25001.dat"
[ -s "$R/geo/tab20_tract20_tract10_natl.txt" ] || curl -sS --fail -o "$R/geo/tab20_tract20_tract10_natl.txt" \
  "https://www2.census.gov/geo/docs/maps-data/data/rel2020/tract/tab20_tract20_tract10_natl.txt"

N='https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/'
curl -sS --fail "$N" | grep -o 'StormEvents_details-ftp_v1.0_d20[12][0-9]_c[0-9]*\.csv\.gz' | sort -u |
  while read -r g; do
    y=$(echo "$g" | sed 's/.*_d\([0-9]*\)_c.*/\1/')
    [ "$y" -ge 2015 ] && [ "$y" -le 2024 ] || continue
    [ -s "$R/storms/details_$y.csv.gz" ] || curl -sS --fail -o "$R/storms/details_$y.csv.gz" "$N$g"
  done
[ -s "$R/storms/zone_county.dbx" ] || curl -sS --fail -o "$R/storms/zone_county.dbx" \
  "https://www.weather.gov/source/gis/Shapefiles/County/bp18mr25.dbx"
ls "$R/storms"
