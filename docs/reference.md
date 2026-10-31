# Script reference

Every script runs from the repository folder and takes at most one argument.

| Script | Reads | Writes | Run |
| --- | --- | --- | --- |
| `features.py` | Challenge bucket: Overture, ACS, strata | `features/<region>-features.csv` | `python features.py all` or `<region>` |
| `strata_extra.py` | Challenge strata | `features/strata_extra.csv` | `python strata_extra.py` |
| `score.py` | `features/`, `SampleSubmission.csv` (or the committed tract list) | `submissions/submission_<v>.csv`, `submissions/components_<v>.csv` | `python score.py v34` |
| `analyse.py` | `submissions/`, scores logged in the script | prints a table | `python analyse.py` |
| `discovery_fire.py` | Challenge bucket: Overture places, tracts, strata | `discovery/*.csv` | `python discovery_fire.py` |
| `discovery_extra.py` | `discovery/`, `features/`, `external/` | `discovery/hidden_fire_extra.csv`, `discovery/hidden_fire_departments_osm.csv` | `python discovery_extra.py` |
| `check_submission.py` | a submission file, `SampleSubmission.csv` (or the committed tract list) | prints OK or FAIL | `python check_submission.py <file>` |
| `reproduce.ipynb` | the repository | notebook outputs | open in Jupyter or Colab |

## Key functions in `score.py`

| Function | What it does |
| --- | --- |
| `signals(df)` | Builds every tract-level signal, each oriented so that higher means a bigger hypothesised gap |
| `probe(df, name, lift)` | A probe: 0.0598 + 0.03 × one standardised signal; `lift` raises the base so no tract clips at zero |
| `combo(df, weights, add)` | A model: 0.0598 + 0.0890 × weighted sum of standardised signals |
| `building_gap`, `transport_gap`, `poi_gap` | The v1–v4 hand-built rules, one per component |
| `score(feats, version)` | Applies one entry of `VERSIONS` |

## Adding a submission version

1. Add an entry to `VERSIONS` in `score.py`, with a comment saying what it tests.
2. Run `python score.py <version>` and `python check_submission.py submissions/submission_<version>.csv`.
3. After uploading, add its public score to `PUBLIC_SCORES` in `analyse.py` and a row to `docs/rounds.md`.

## Key columns in `features/<region>-features.csv`

| Column | Meaning |
| --- | --- |
| `km_named` | Overture road km in classes motorway to secondary |
| `km_hwy_route` | Road km on interstate, US or state route relations |
| `km_fm_route`, `km_fm_route_minor` | Texas FM/RM route km; the part tagged below secondary |
| `km_local_pre2010` | Residential and unclassified km last edited before 2010 |
| `bldg_ms`, `bldg_osm`, `bldg_ms_old` | Buildings from Microsoft, from OSM, from pre-2020 Microsoft imagery |
| `poi_fire`, `poi_fire_miscat` | Places categorised `fire_department`; fire departments under another category |
