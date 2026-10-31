"""
Per-tract feature table for the Zindi Bias Bounty Mapping Equity Challenge.

Reads the challenge data straight from Source Cooperative (no download needed)
and writes one row per scored tract with what Overture has there:
  - road km by class (named highway classes + tertiary), clipped to the tract
  - OSM edit-history signals (version 1, last edit before 2010) for named
    highways and for local streets (residential + unclassified)
  - building counts by upstream source (Microsoft ML, OpenStreetMap, Esri, ...)
  - road km on interstate / US / state route relations (stand-in for TIGER's
    highway definition), and Texas FM/RM roads separately
  - POI counts for the categories the organisers score (fire, EMS, schools) + all POIs,
    plus fire departments filed under other categories (matched by name)
  - ACS housing units and a few strata columns

Usage:
    pip install "duckdb>=1.3" pandas
    python features.py northern-ca            # one region
    python features.py all                    # all five regions

Output: features/<region>-features.csv  (GEOID stored as text)

Uses only the provided challenge datasets. No reference layers.
"""
import sys
import time
from pathlib import Path

import duckdb

BASE = "https://data.source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge"
REGIONS = ["northern-ca", "eastern-ok", "maricopa-az", "south-central-tx", "eastern-wa"]

NAMED = ("motorway", "trunk", "primary", "secondary")
LOCAL = ("residential", "unclassified")
# Route networks that TIGER's S1100/S1200 (interstate, US, state highway) cover.
# Excludes historic, scenic, NHS, BIA, future and county networks.
HWY_NETWORK = r"^US:(I|US|[A-Z]{2})(:(Business|Loop|Spur|Alternate|Bypass|Truck))*$"
FM_NETWORK = r"^US:TX:(FM|RM)$"   # Texas farm/ranch-to-market roads, kept separate

# Fire departments filed under other categories: name says fire station,
# category doesn't. Business names (sprinklers, alarms...) excluded.
FIRE_NAME = r"(fire (station|dept|department|district|protection district|rescue)|volunteer fire|\bvfd\b|\bfpd\b)"
FIRE_NAME_EXCLUDE = (r"(system|sprinkler|extinguish|alarm|equipment|supply|plumbing|thrift|"
                     r"auxiliar|association|museum|training|academy|insurance|service co|inc\b|llc)")
SCHOOLS = ("elementary_school", "middle_school", "high_school",
           "school", "private_school", "public_school")

STRATA_COLS = [
    "GEOID", "ALAND", "pop_total", "pct_urban", "ur_class", "ruca_primary",
    "svi_overall", "cvi_overall", "tribal_any", "tribal_pct",
]

# Lon/lat -> metres. always_xy is required: without it DuckDB reads EPSG:4326
# as lat/lon and every length silently becomes inf (see the challenge README).
TO_M = "ST_Transform({g}, 'EPSG:4326', 'EPSG:5070', always_xy := true)"


def connect():
    con = duckdb.connect()
    for ext in ("httpfs", "spatial"):
        con.sql(f"INSTALL {ext}; LOAD {ext};")
    return con


def build(con, region):
    ref = f"{BASE}/reference/{region}/{region}"
    strata = f"{BASE}/strata/{region}/{region}"

    # Scored tracts + polygons
    con.sql(f"""
        CREATE OR REPLACE TABLE tracts AS
        SELECT GEOID, geometry,
               ST_Area({TO_M.format(g='geometry')}) / 1e6 AS area_km2
        FROM '{strata}-census-tracts.parquet'
    """)

    # ---- Roads: km per class, clipped to each tract -------------------------
    # First source = the feature's geometry source (OSM for roads).
    # record_id looks like 'w10298518@1' -> OSM way 10298518, version 1.
    # A segment can list several sources (e.g. route relations that only supply
    # /properties/routes). The geometry source is the one with an empty property.
    con.sql(f"""
        CREATE OR REPLACE TABLE roads AS
        WITH r AS (
            SELECT class, geometry,
                   list_filter(sources, lambda s: coalesce(s.property, '') = '')[1] AS g,
                   -- OSM route relations: interstate / US / state highway?
                   -- (TIGER S1100+S1200 = interstates + US/state highways)
                   list_bool_or(list_transform(routes, lambda x:
                       regexp_matches(coalesce(x.network, ''), '{HWY_NETWORK}'))) AS hwy_route,
                   list_bool_or(list_transform(routes, lambda x:
                       regexp_matches(coalesce(x.network, ''), '{FM_NETWORK}'))) AS fm_route
            FROM '{ref}-overture-roads.parquet'
            WHERE class IN {NAMED + LOCAL + ('tertiary',)}
        )
        SELECT class, geometry,
               coalesce(hwy_route, false) AS hwy_route,
               coalesce(fm_route, false) AS fm_route,
               g.dataset AS src,
               TRY_CAST(split_part(g.record_id, '@', 2) AS INTEGER) AS osm_version,
               TRY_CAST(left(g.update_time, 4) AS INTEGER) AS last_edit_year
        FROM r
    """)
    con.sql(f"""
        CREATE OR REPLACE TABLE road_parts AS
        SELECT t.GEOID, r.class, r.hwy_route, r.fm_route, r.src, r.osm_version, r.last_edit_year,
               ST_Length({TO_M.format(g='ST_Intersection(r.geometry, t.geometry)')}) / 1000 AS km
        FROM roads r JOIN tracts t ON ST_Intersects(r.geometry, t.geometry)
    """)
    con.sql(f"""
        CREATE OR REPLACE TABLE road_feats AS
        SELECT GEOID,
               sum(km) FILTER (class = 'motorway')  AS km_motorway,
               sum(km) FILTER (class = 'trunk')     AS km_trunk,
               sum(km) FILTER (class = 'primary')   AS km_primary,
               sum(km) FILTER (class = 'secondary') AS km_secondary,
               sum(km) FILTER (class = 'tertiary')  AS km_tertiary,
               sum(km) FILTER (class IN {NAMED})    AS km_named,
               -- route-based stand-in for TIGER's highway network
               sum(km) FILTER (hwy_route)                    AS km_hwy_route,
               sum(km) FILTER (hwy_route AND class IN {NAMED}) AS km_hwy_route_named,
               sum(km) FILTER (fm_route)                     AS km_fm_route,
               -- Texas FM/RM roads: OSM tags them secondary (town connectors) or
               -- tertiary (minor), per the Texas wiki. Only the named classes count
               -- on Overture's side of the organisers' road comparison.
               sum(km) FILTER (fm_route AND class IN {NAMED})     AS km_fm_route_named,
               sum(km) FILTER (fm_route AND class NOT IN {NAMED}) AS km_fm_route_minor,
               -- OSM history on the named network
               sum(km) FILTER (class IN {NAMED} AND osm_version = 1)       AS km_named_v1,
               sum(km) FILTER (class IN {NAMED} AND last_edit_year < 2010) AS km_named_pre2010,
               median(last_edit_year) FILTER (class IN {NAMED})            AS named_median_edit_year,
               -- OSM history on local streets: where untouched 2007-08 TIGER
               -- import geometry survives (named highways get re-edited)
               sum(km) FILTER (class IN {LOCAL})                           AS km_local,
               sum(km) FILTER (class IN {LOCAL} AND osm_version = 1)       AS km_local_v1,
               sum(km) FILTER (class IN {LOCAL} AND last_edit_year < 2010) AS km_local_pre2010,
               median(last_edit_year) FILTER (class IN {LOCAL})            AS local_median_edit_year
        FROM road_parts GROUP BY GEOID
    """)

    # ---- Buildings: count by upstream source (centroid in tract) -------------
    con.sql(f"""
        CREATE OR REPLACE TABLE bldg_feats AS
        SELECT t.GEOID,
               count(*) AS bldg_total,
               count(*) FILTER (b.src = 'Microsoft ML Buildings') AS bldg_ms,
               count(*) FILTER (b.src = 'OpenStreetMap')          AS bldg_osm,
               count(*) FILTER (b.src = 'Esri Community Maps')    AS bldg_esri,
               count(*) FILTER (b.src = 'Google Open Buildings')  AS bldg_google,
               -- Microsoft footprints by imagery year (update_time). Overture's copy is
               -- Microsoft's 2025-02-25 version (imagery to 2023-09); 2000 = placeholder.
               count(*) FILTER (b.src = 'Microsoft ML Buildings' AND b.yr = 2000)            AS bldg_ms_undated,
               count(*) FILTER (b.src = 'Microsoft ML Buildings' AND b.yr BETWEEN 2001 AND 2019) AS bldg_ms_old,
               count(*) FILTER (b.src = 'Microsoft ML Buildings' AND b.yr >= 2020)           AS bldg_ms_recent,
               median(b.yr) FILTER (b.src = 'Microsoft ML Buildings' AND b.yr > 2000)        AS ms_median_imagery_year
        FROM (SELECT g.dataset AS src,
                     TRY_CAST(left(g.update_time, 4) AS INTEGER) AS yr,
                     ST_Centroid(geometry) AS pt
              FROM (SELECT list_filter(sources, lambda s: coalesce(s.property, '') = '')[1] AS g, geometry
                    FROM '{ref}-overture-buildings.parquet')) b
        JOIN tracts t ON ST_Intersects(b.pt, t.geometry)
        GROUP BY t.GEOID
    """)

    # ---- POIs: the categories the organisers match on ------------------------
    con.sql(f"""
        CREATE OR REPLACE TABLE poi_feats AS
        SELECT t.GEOID,
               count(*) AS poi_total,
               count(*) FILTER (p.cat = 'fire_department')            AS poi_fire,
               count(*) FILTER (p.cat = 'ambulance_and_ems_services') AS poi_ems,
               count(*) FILTER (p.cat IN {SCHOOLS})                   AS poi_schools,
               count(*) FILTER (p.cat = 'hospital')                   AS poi_hospital,
               -- real-looking fire departments the organisers' category match misses
               count(*) FILTER (coalesce(p.cat, '') <> 'fire_department'
                                AND regexp_matches(p.nm, '{FIRE_NAME}')
                                AND NOT regexp_matches(p.nm, '{FIRE_NAME_EXCLUDE}'))
                                                                       AS poi_fire_miscat
        FROM (SELECT categories.primary AS cat, lower(coalesce(names.primary, '')) AS nm, geometry
              FROM '{ref}-overture-pois.parquet') p
        JOIN tracts t ON ST_Intersects(p.geometry, t.geometry)
        GROUP BY t.GEOID
    """)

    # ---- Assemble -------------------------------------------------------------
    df = con.sql(f"""
        SELECT '{region}' AS region, t.GEOID, t.area_km2,
               h.housing_units, s.* EXCLUDE (GEOID),
               r.* EXCLUDE (GEOID), b.* EXCLUDE (GEOID), p.* EXCLUDE (GEOID)
        FROM tracts t
        LEFT JOIN (SELECT GEOID, housing_units FROM '{ref}-census-acs-housing.parquet') h USING (GEOID)
        LEFT JOIN (SELECT {', '.join(STRATA_COLS)} FROM '{strata}-strata-tract-table.parquet') s USING (GEOID)
        LEFT JOIN road_feats r USING (GEOID)
        LEFT JOIN bldg_feats b USING (GEOID)
        LEFT JOIN poi_feats p USING (GEOID)
        ORDER BY GEOID
    """).df()

    # No feature in a tract means a count of zero, not missing.
    count_cols = [c for c in df.columns if c.startswith(("km_", "bldg_", "poi_"))]
    df[count_cols] = df[count_cols].fillna(0)
    return df


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "northern-ca"
    regions = REGIONS if arg == "all" else [arg]
    Path("features").mkdir(exist_ok=True)
    con = connect()
    for region in regions:
        t0 = time.time()
        df = build(con, region)
        out = Path("features") / f"{region}-features.csv"
        df.to_csv(out, index=False)
        print(f"{region}: {len(df)} tracts -> {out} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
