# Data sources

## Challenge data (scored submission and discovery)

Read directly from the public bucket, never copied into this repository.

| Data | File pattern | Version | Licence |
| --- | --- | --- | --- |
| Overture buildings, roads, places | `reference/<region>/<region>-overture-*.parquet` | Overture release 2026-08-19.0 | ODbL (buildings, transportation); CDLA Permissive 2.0 (places) |
| ACS housing units | `reference/<region>/<region>-census-acs-housing.parquet` | ACS 2020–2024 5-year | Public domain |
| Tract boundaries and strata | `strata/<region>/<region>-*.parquet` | 2020 tracts; per-source vintages in the challenge README | Per source |

Bucket: `https://data.source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge`,
read 23–31 October 2026. Documentation:
[challenge README](https://data.source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge/README.md).

Not used, by the challenge rules: TIGER/Line roads, Microsoft building footprints, HIFLD facilities,
County Business Patterns, or any copy of them.

## Outside data (Best Bias Discovery only)

| Data | File | Retrieved | Licence |
| --- | --- | --- | --- |
| OpenStreetMap `amenity=fire_station`, five study-region bounding boxes (3,798 stations) | `external/osm_fire_stations_2026-10-31.geojson` | 2026-10-31 16:00 UTC, Overpass API via overpass-turbo.eu | ODbL, © OpenStreetMap contributors |

Query:

```
[out:json][timeout:300];
(
  nwr["amenity"="fire_station"](38.313,-124.230,42.010,-119.996);  // northern-ca
  nwr["amenity"="fire_station"](33.616,-100.004,37.002,-94.431);  // eastern-ok
  nwr["amenity"="fire_station"](31.332,-114.564,36.410,-108.208);  // maricopa-az
  nwr["amenity"="fire_station"](25.837,-103.253,34.242,-94.646);  // south-central-tx
  nwr["amenity"="fire_station"](45.606,-122.284,49.001,-116.916);  // eastern-wa
);
out center tags;
```

## Documentation cited

- Microsoft Global ML Building Footprints changelog (dataset versions and US updates, 2025–2026)
- OSM wiki: Texas map features; US 2021 highway classification guidance
- US Census: County Business Patterns coverage
- Overture: buildings guide and release notes

Links are in the writeup's Sources section.
