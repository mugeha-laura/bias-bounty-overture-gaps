# Reproduce the results

Every number in the writeup can be reproduced from this repository and the public challenge data.
No credentials or paid services are needed.

## Before you start

- Python 3.12 or later (tested with Python 3.13, DuckDB 2.0.0, pandas 3.0.5, NumPy 2.5.3).
- An internet connection: the scripts read the challenge data straight from its public bucket.
- `SampleSubmission.csv` from the challenge's Data page on Zindi, saved in the repository folder.

```bash
pip install -e .
```

## Quick path: from the committed features

The features in `features/` are committed, so the scoring steps run in seconds.

```bash
python score.py v34                     # final model
python score.py v15                     # second pick
python check_submission.py submissions/submission_v34.csv
python analyse.py                       # score -> correlation table
```

Any submission can be rebuilt by name (`python score.py v6`). To confirm a rebuilt file matches the
uploaded one exactly, copy it first and compare:

```bash
cp submissions/submission_v34.csv /tmp/uploaded_v34.csv
python score.py v34
python check_submission.py submissions/submission_v34.csv --same-as /tmp/uploaded_v34.csv
```

## Full path: from the raw challenge data

| Step | Command | Time | Writes |
| --- | --- | --- | --- |
| 1. Features per tract | `python features.py all` | ~20 min (Texas ~10) | `features/<region>-features.csv` |
| 2. Hazard columns | `python strata_extra.py` | ~1 min | `features/strata_extra.csv` |
| 3. Scores | `python score.py v34` | seconds | `submissions/submission_v34.csv` |
| 4. Analysis | `python analyse.py` | seconds | prints the table |
| 5. Discovery | `python discovery_fire.py` | ~5 min | `discovery/*.csv` |
| 6. Discovery checks | `python discovery_extra.py` | seconds | `discovery/hidden_fire_extra.csv` |

One region at a time: `python features.py northern-ca`.

## The OpenStreetMap file

`discovery_extra.py` reads `external/osm_fire_stations_2026-10-31.geojson`. To fetch a fresh copy, run
the query in [data.md](data.md) on [overpass-turbo.eu](https://overpass-turbo.eu) and export it as
GeoJSON. A fresh copy will differ slightly, because OSM changes daily.

## If something goes wrong

- **A join returns nothing for Maricopa.** GEOIDs must be read as text: Arizona's FIPS code starts with 0.
  Every script already does this; check any code you add.
- **Lengths come out as `inf` or `NaN` in DuckDB.** Pass `always_xy := true` to `ST_Transform`. See the
  challenge README for why.
- **A download is cut off.** Rerun the same command; nothing is written until a region finishes.
