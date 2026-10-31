"""
Best Bias Discovery, extra checks on the hidden fire departments.

Inputs:
  discovery/fire_departments_all.csv    from discovery_fire.py (challenge data only)
  features/strata_extra.csv             from strata_extra.py (challenge strata)
  features/*-features.csv               from features.py (challenge data)
  external/osm_fire_stations_2026-10-31.geojson
      OUTSIDE PUBLIC DATA (discovery only, never used in a scored submission):
      OpenStreetMap amenity=fire_station, Overpass API via overpass-turbo.eu,
      retrieved 2026-10-31T16:00:06Z, ODbL. Query in docs/data.md.

Checks:
  OSM    is each hidden department mapped in OSM as a fire station (within 500 m)?
         control: the same rate for correctly categorised fire_department places
  hazard share hidden by wildfire-hazard and drought quartile (rural tracts)
  people population and housing units in tracts where every fire department is hidden
  fix    how many would be found by also matching fire_protection_service
  conf   does Overture's own confidence score flag hidden departments?
  es     Spanish-language fire-department names the English rule misses (South Texas)

Usage: python discovery_extra.py
"""
import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

BASE = "https://data.source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge"
OSM = "external/osm_fire_stations_2026-10-31.geojson"
MATCH_M = 500        # an OSM fire station this close counts as the same station
SPANISH = r"(bomberos|estaci[oó]n de bomberos|cuerpo de bomberos)"


def main():
    """Run the six checks and write discovery/hidden_fire_extra.csv (one row per result)."""
    out = []   # rows of (check, group, n, value, note)
    allp = pd.read_csv("discovery/fire_departments_all.csv", dtype={"GEOID": str})
    # Same denominator as discovery_fire.py: proper fire_department places + hidden ones
    base = allp[(allp.kind == "fire_department") | allp.hidden].copy()

    # ---- OSM validation ------------------------------------------------------------
    # Is each place an independently mapped fire station? A hidden department that OSM
    # also has is very likely a real station. The control row gives the same rate for
    # correctly categorised places, so the two can be compared.
    gj = json.load(open(OSM))
    # The export holds points (stations mapped as nodes, or centres of mapped areas)
    osm = pd.DataFrame([(f["geometry"]["coordinates"][0], f["geometry"]["coordinates"][1],
                         f["properties"].get("@id")) for f in gj["features"]], columns=["lon", "lat", "osm_id"])
    con = duckdb.connect()
    con.sql("INSTALL spatial; LOAD spatial;")
    con.register("osm", osm)
    con.register("b", base[["id", "lon", "lat"]])
    pt = "ST_Transform(ST_Point({x}, {y}), 'EPSG:4326', 'EPSG:5070', always_xy := true)"
    # Nearest OSM station within 5 km of each place (distance in metres, and its OSM id)
    near = con.sql(f"""
        WITH o AS (SELECT osm_id, {pt.format(x='lon', y='lat')} AS g FROM osm),
             q AS (SELECT id, {pt.format(x='lon', y='lat')} AS g FROM b)
        SELECT q.id, min(ST_Distance(q.g, o.g)) AS osm_m,
               arg_min(o.osm_id, ST_Distance(q.g, o.g)) AS osm_id
        FROM q, o WHERE ST_DWithin(q.g, o.g, 5000) GROUP BY q.id
    """).df()
    base = base.merge(near, on="id", how="left")   # no station within 5 km -> osm_m is NaN
    base["in_osm"] = base.osm_m <= MATCH_M
    for label, d in [("hidden, rural", base[base.hidden & (base.ur_class == "Rural")]),
                     ("hidden, urban", base[base.hidden & (base.ur_class != "Rural")]),
                     ("hidden, rural tribal Eastern OK", base[base.hidden & (base.group == "Rural tribal Eastern OK")]),
                     ("hidden, all", base[base.hidden]),
                     ("control: fire_department, all", base[base.kind == "fire_department"])]:
        out.append(dict(check="osm", group=label, n=len(d), value=d.in_osm.mean(),
                        note=f"share with an OSM amenity=fire_station within {MATCH_M} m"))
    # Per-department file for the map checks; round only the distance column
    base.loc[base.hidden, ["region", "GEOID", "name", "category", "lon", "lat", "in_osm", "osm_id", "osm_m"]] \
        .round({"osm_m": 1}).to_csv("discovery/hidden_fire_departments_osm.csv", index=False)

    # ---- hazard: share hidden by wildfire / drought quartile, rural tracts -----------
    # Rural only, so the rural/urban difference does not drive the result.
    ex = pd.read_csv("features/strata_extra.csv", dtype={"GEOID": str})
    rb = base[base.ur_class == "Rural"].merge(ex, on="GEOID", how="left")
    for col, name in [("usfs_WHP_mean", "wildfire hazard"), ("usdm_summer_dsci", "summer drought")]:
        # quartiles over fire departments (not tracts), lowest to highest hazard
        q = pd.qcut(rb[col], 4, labels=["Q1 lowest", "Q2", "Q3", "Q4 highest"])
        for lab, d in rb.groupby(q, observed=True):
            out.append(dict(check="hazard", group=f"rural, {name} {lab}", n=len(d), value=d.hidden.mean(),
                            note="share of fire departments hidden"))

    # ---- people in tracts where every fire department is hidden ------------------------
    # pop_total from the challenge strata, housing_units from the challenge ACS table
    feats = pd.concat([pd.read_csv(p, dtype={"GEOID": str}) for p in sorted(Path("features").glob("*-features.csv"))])
    allhid = base.groupby("GEOID").hidden.all()    # True if no department in the tract is findable
    tr = feats[feats.GEOID.isin(allhid[allhid].index)]
    out.append(dict(check="people", group="tracts where every fire department is hidden", n=len(tr),
                    value=tr.pop_total.sum(), note=f"population; housing units {int(tr.housing_units.sum())}; "
                    f"rural tracts {int((tr.ur_class == 'Rural').sum())}"))

    # ---- one-line fix -------------------------------------------------------------------
    # How many would a search find if it also matched the category most of them carry?
    h = base[base.hidden]
    out.append(dict(check="fix", group="hidden filed as fire_protection_service", n=len(h),
                    value=(h.category == "fire_protection_service").mean(),
                    note="share recovered by also matching fire_protection_service"))

    # ---- Overture confidence ------------------------------------------------------------
    # If hidden departments had low confidence, a quality filter would already flag them.
    for label, d in [("hidden", base[base.hidden]), ("fire_department", base[base.kind == "fire_department"])]:
        out.append(dict(check="confidence", group=label, n=int(d.confidence.notna().sum()),
                        value=d.confidence.median(), note="median Overture confidence"))

    # ---- Spanish names (South Texas) -----------------------------------------------------
    # The English name rule cannot see "bomberos"; count them directly from the challenge POIs.
    con.sql("INSTALL httpfs; LOAD httpfs;")
    es = con.sql(f"""
        SELECT count(*) AS n,
               count(*) FILTER (WHERE coalesce(categories.primary, '') <> 'fire_department') AS other_category
        FROM '{BASE}/reference/south-central-tx/south-central-tx-overture-pois.parquet'
        WHERE regexp_matches(lower(coalesce(names.primary, '')), '{SPANISH}')
    """).df().iloc[0]
    out.append(dict(check="spanish", group="South-Central TX names with bomberos", n=int(es.n),
                    value=int(es.other_category), note="of which filed under another category"))

    # ---- write and print -----------------------------------------------------------------
    res = pd.DataFrame(out)
    res.to_csv("discovery/hidden_fire_extra.csv", index=False)
    pd.set_option("display.width", 220); pd.set_option("display.max_colwidth", 80)
    print(res.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
