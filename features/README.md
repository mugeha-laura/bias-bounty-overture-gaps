# features/

One CSV per study region, one row per scored tract, built by `features.py`; plus
`strata_extra.csv` (wildfire, heat, drought) from `strata_extra.py`.

Committed so that `score.py` runs in seconds. Rebuild with `python features.py all` (~20 minutes).
Column meanings: [docs/reference.md](../docs/reference.md).

Derived from Overture Maps release 2026-08-19.0 and the challenge strata. Licences: see the README.
