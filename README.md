# Private Flood Insurance Gap Finder

A quarterly decision tool for the underwriter at a private flood insurer. For each of 3,232 US counties it gives one of four calls: grow, re-price, pause or hold. Each call compares 48 years of NFIP claims (1978–2025) with FEMA's modeled flood loss. Public data only.

**Live site:** https://rutuja310.github.io/fricative-flood-gap-finder/: this quarter's plan, every county on a map, storm watch, and Excel/CSV downloads.

This repo holds only the flood project.

Everything is in [`flood/`](flood/README.md): the pipeline, the scheduled refresh, the n8n workflow, the live demo, the outputs, the change log and the [methodology](flood/METHODOLOGY.md).

## Quick start

```sh
pip install -r requirements.txt
sh flood/src/fetch_raw.sh          # downloads FEMA, Census and BLS inputs into flood/raw/ (not in git)
sh flood/src/fetch_policies_api.sh # optional, can take hours: NFIP policies in force for the point-in-time backtest
sh flood/src/fetch_tracts.sh       # optional: NRI tracts, ACS homes, NOAA storms for the tract and storm tests
python3 flood/src/run_flood.py     # scores every county → flood/out/ and flood/demo/data.json
python3 flood/src/refresh.py --quarterly --no-fetch   # writes this quarter's plan report
```
