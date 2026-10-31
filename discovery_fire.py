"""
Best Bias Discovery: fire departments that a category search cannot find.

For every Overture place whose NAME says fire department but whose CATEGORY is not
`fire_department` (the category the organisers match on):
  - distance to the nearest place categorised `fire_department` (EPSG:5070, metres)
  - "hidden" = no `fire_department` place within DUP_M (else it is a duplicate record
    of a station that IS findable)
  - its tract, rural/urban class, tribal overlap, county, upstream source

Outputs (discovery/):
  hidden_fire_departments.csv   one row per hidden department
  hidden_fire_summary.csv       shares by group, with county-block bootstrap 95% CIs

Uses only the challenge datasets. Usage: python discovery_fire.py
"""
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

BASE = "https://data.source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge"
REGIONS = ["northern-ca", "eastern-ok", "maricopa-az", "south-central-tx", "eastern-wa"]
# Names that say "fire department" (matched on the lower-cased primary name).
# The same rule as FIRE_NAME in features.py.
NAME = r"(fire (station|dept|department|district|protection district|rescue)|volunteer fire|\bvfd\b|\bfpd\b)"
# Names to drop: businesses and organisations that are not stations
# (sprinkler fitters, alarm companies, auxiliaries, museums, training centres...).
EXCLUDE = (r"(system|sprinkler|extinguish|alarm|equipment|supply|plumbing|thrift|"
           r"auxiliar|association|museum|training|academy|insurance|service co|inc\b|llc)")
DUP_M = 500          # a fire_department place this close = same station, already findable
BOOT = 2000          # bootstrap draws for the confidence intervals
RNG = np.random.default_rng(20261030)   # fixed seed: the CIs reproduce exactly
# Lon/lat -> metres (CONUS Albers). always_xy is required, see features.py.
TO_M = "ST_Transform({g}, 'EPSG:4326', 'EPSG:5070', always_xy := true)"


def main():
    """Find the hidden fire departments, summarise them by group and write discovery/."""
    con = duckdb.connect()
    for ext in ("httpfs", "spatial"):
        con.sql(f"INSTALL {ext}; LOAD {ext};")
    rows = []
    for r in REGIONS:
        ref, strata = f"{BASE}/reference/{r}/{r}", f"{BASE}/strata/{r}/{r}"
        # Candidate places: everything categorised fire_department, plus everything
        # whose name says fire department (after the business exclusions).
        con.sql(f"""
            CREATE OR REPLACE TABLE p AS
            SELECT id, names.primary AS name, coalesce(categories.primary, '') AS category,
                   list_transform(sources, lambda s: s.dataset) AS datasets, confidence,
                   ST_X(geometry) AS lon, ST_Y(geometry) AS lat,
                   {TO_M.format(g='geometry')} AS g, geometry
            FROM '{ref}-overture-pois.parquet'
            WHERE categories.primary = 'fire_department'
               OR (regexp_matches(lower(coalesce(names.primary, '')), '{NAME}')
                   AND NOT regexp_matches(lower(coalesce(names.primary, '')), '{EXCLUDE}'))
        """)
        # Named but filed under another category: distance to the nearest proper
        # fire_department place, plus the tract it falls in and that tract's strata.
        df = con.sql(f"""
            WITH named AS (SELECT * FROM p WHERE category <> 'fire_department'),
                 proper AS (SELECT * FROM p WHERE category = 'fire_department')
            SELECT '{r}' AS region, n.id, n.name, n.category, n.datasets, n.confidence, n.lon, n.lat,
                   (SELECT min(ST_Distance(n.g, q.g)) FROM proper q) / 1000 AS nearest_fire_dept_km,
                   t.GEOID, s.ur_class, s.tribal_pct, s.aiannh_name
            FROM named n
            LEFT JOIN '{strata}-census-tracts.parquet' t ON ST_Intersects(n.geometry, t.geometry)
            LEFT JOIN '{strata}-strata-tract-table.parquet' s ON s.GEOID = t.GEOID
        """).df()
        df["kind"] = "named, other category"
        # The correctly categorised fire_department places: the denominator for "share hidden"
        prop = con.sql(f"""
            SELECT '{r}' AS region, q.id, q.name, q.confidence, q.lon, q.lat, t.GEOID, s.ur_class, s.tribal_pct
            FROM p q
            LEFT JOIN '{strata}-census-tracts.parquet' t ON ST_Intersects(q.geometry, t.geometry)
            LEFT JOIN '{strata}-strata-tract-table.parquet' s ON s.GEOID = t.GEOID
            WHERE q.category = 'fire_department'
        """).df()
        prop["kind"] = "fire_department"
        rows += [df, prop]
    allp = pd.concat(rows, ignore_index=True)
    # Keep places inside a scored tract only.
    allp = allp[allp.GEOID.notna()].sort_values(["region", "id"]).reset_index(drop=True)   # fixed order -> reproducible bootstrap
    # Hidden = named as a fire department, filed under another category, and with no
    # fire_department place within DUP_M (otherwise it duplicates a findable station).
    allp["hidden"] = (allp.kind == "named, other category") & (allp.nearest_fire_dept_km * 1000 > DUP_M)
    allp["county"] = allp.GEOID.str[:5]        # state + county FIPS: the bootstrap's blocks
    # Three groups: rural tracts at least half inside a tribal area in Eastern OK,
    # other rural tracts, and urban tracts (ur_class from the challenge strata).
    allp["group"] = np.where((allp.region == "eastern-ok") & (allp.ur_class == "Rural") & (allp.tribal_pct >= 0.5),
                             "Rural tribal Eastern OK",
                             np.where(allp.ur_class == "Rural", "Other rural", "Urban"))
    # Did the place come (at least partly) from Meta? sources.dataset lists the upstream datasets.
    allp["via_meta"] = allp.datasets.apply(lambda d: isinstance(d, (list, np.ndarray)) and "meta" in list(d))

    out = Path("discovery"); out.mkdir(exist_ok=True)
    allp.drop(columns=["datasets"]).to_csv(out / "fire_departments_all.csv", index=False)   # input to discovery_extra.py
    hid = allp[allp.hidden].sort_values(["region", "nearest_fire_dept_km"], ascending=[True, False])
    hid[["region", "GEOID", "name", "category", "via_meta", "lon", "lat", "nearest_fire_dept_km",
         "ur_class", "tribal_pct", "aiannh_name"]].round(4).to_csv(out / "hidden_fire_departments.csv", index=False)

    # Share of fire departments that are hidden, by group, with 95% CIs from a
    # county-block bootstrap: resample whole counties, because places in one county
    # share a source and a mapping history, so they are not independent.
    # Denominator: proper fire_department places + hidden ones (duplicates excluded).
    base = allp[(allp.kind == "fire_department") | allp.hidden]
    def share(d):
        return d.hidden.mean()
    summ = []
    for grp, d in base.groupby("group"):
        counties = np.sort(d.county.unique())          # sorted: same draws on every run
        by = {c: g for c, g in d.groupby("county")}
        # each draw: pick len(counties) counties with replacement, pool their places
        boots =[share(pd.concat([by[c] for c in RNG.choice(counties, len(counties))])) for _ in range(BOOT)]
        summ.append(dict(group=grp, departments=len(d), hidden=int(d.hidden.sum()), share=share(d),
                         ci_low=np.percentile(boots, 2.5), ci_high=np.percentile(boots, 97.5),
                         counties=len(counties),
                         median_km_to_findable=hid[hid.group == grp].nearest_fire_dept_km.median(),
                         via_meta=hid[hid.group == grp].via_meta.mean()))
    # Rural minus urban difference: rural and urban counties resampled separately in each
    # draw, so the CI on the difference carries both groups' uncertainty.
    rur, urb = base[base.ur_class == "Rural"], base[base.ur_class != "Rural"]
    rc, uc = {c: g for c, g in rur.groupby("county", sort=True)}, {c: g for c, g in urb.groupby("county", sort=True)}
    diffs = [share(pd.concat([rc[c] for c in RNG.choice(list(rc), len(rc))])) -
             share(pd.concat([uc[c] for c in RNG.choice(list(uc), len(uc))])) for _ in range(BOOT)]
    summ.append(dict(group="Rural minus urban", share=share(rur) - share(urb),
                     ci_low=np.percentile(diffs, 2.5), ci_high=np.percentile(diffs, 97.5)))
    s = pd.DataFrame(summ)
    s.round(4).to_csv(out / "hidden_fire_summary.csv", index=False)
    print(s.round(3).to_string(index=False))
    print(f"\nnamed under other category: {(allp.kind == 'named, other category').sum()} | "
          f"hidden (no fire_department within {DUP_M} m): {allp.hidden.sum()}")
    # Tracts where a category search finds no fire department although named ones exist
    print("tracts whose only fire departments are hidden:",
          base.groupby("GEOID").hidden.all().sum(), "of", base.GEOID.nunique())


if __name__ == "__main__":
    main()
