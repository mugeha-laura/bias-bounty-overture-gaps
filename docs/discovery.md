# Best Bias Discovery: fire departments a category search cannot find

## Finding

697 fire departments in Overture's places are named as fire departments but filed under another
category. The organisers' facility term, and any tool that looks stations up by category, cannot
see them.

| Group | Fire departments | Hidden | Share hidden (95% CI) |
| --- | --- | --- | --- |
| Rural tribal Eastern Oklahoma | 466 | 123 | 26.4% (21.6–31.4%) |
| Other rural tracts | 1,470 | 367 | 25.0% (22.6–27.5%) |
| Urban tracts | 2,402 | 207 | 8.6% (7.5–10.2%) |

Intervals come from 2,000 bootstrap draws that resample whole counties (seed 20261030).

## The rule

A place counts as a **hidden fire department** when all four hold:

1. Its name matches `(fire (station|dept|department|district|protection district|rescue)|volunteer fire|\bvfd\b|\bfpd\b)`, case-insensitive.
2. Its name does not match `(system|sprinkler|extinguish|alarm|equipment|supply|plumbing|thrift|auxiliar|association|museum|training|academy|insurance|service co|inc\b|llc)`.
3. Its category is not `fire_department`.
4. No place categorised `fire_department` lies within 500 m (otherwise it is a findable duplicate).

Distances are measured in EPSG:5070, to the nearest `fire_department` place in the same study region.

## Outputs

| File | One row per | Key columns |
| --- | --- | --- |
| `discovery/fire_departments_all.csv` | fire department, findable or hidden | `kind`, `hidden`, `category`, `GEOID`, `ur_class`, `tribal_pct`, `group`, `confidence` |
| `discovery/hidden_fire_departments.csv` | hidden department | `name`, `category`, `via_meta`, `lon`, `lat`, `nearest_fire_dept_km` |
| `discovery/hidden_fire_summary.csv` | group | `share`, `ci_low`, `ci_high`, `median_km_to_findable`, `via_meta` |
| `discovery/hidden_fire_departments_osm.csv` | hidden department | `in_osm`, `osm_id`, `osm_m` (distance to nearest OSM fire station) |
| `discovery/hidden_fire_extra.csv` | check | `check`, `group`, `n`, `value`, `note` |

## Known limits

- The rule is not hand-audited. A read of all 697 finds 16 clear non-stations (2%); removing them
  changes each share by under half a point.
- Distances only count stations inside the same study region, which overstates them near region edges.
- Overture's point is often a town or contact location, not the station building.
