"""
Pull a few extra strata columns (hazard exposure) for every scored tract and write
features/strata_extra.csv, which score.py merges on GEOID.

Usage: python strata_extra.py
"""
from pathlib import Path

import duckdb

BASE = "https://data.source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge/strata"
REGIONS = ["northern-ca", "eastern-ok", "maricopa-az", "south-central-tx", "eastern-wa"]
COLS = [
    "usfs_WHP_mean",            # USFS wildfire hazard potential
    "epht_heat_days_summer",    # CDC EPHT extreme-heat days (summer)
    "usdm_summer_dsci",         # US Drought Monitor, summer drought severity
]


def main():
    con = duckdb.connect()
    con.sql("INSTALL httpfs; LOAD httpfs;")
    parts = " UNION ALL ".join(
        f"SELECT GEOID, {', '.join(COLS)} FROM '{BASE}/{r}/{r}-strata-tract-table.parquet'"
        for r in REGIONS
    )
    df = con.sql(parts).df()
    Path("features").mkdir(exist_ok=True)
    df.to_csv("features/strata_extra.csv", index=False)
    print(f"features/strata_extra.csv: {len(df)} tracts, columns {COLS}")
    print(df[COLS].describe().round(2))


if __name__ == "__main__":
    main()
