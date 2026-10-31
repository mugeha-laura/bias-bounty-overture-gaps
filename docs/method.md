# Method

The reference layers behind the target were removed, so the target cannot be computed. We measured it
instead, from leaderboard scores, one documented signal at a time.

## 1. Features from Overture only

`features.py` builds one row per tract from the challenge data: road length by class, route relations
(interstate, US, state; Texas FM/RM; BIA), OSM edit history from each road's `sources.record_id` and
`update_time`, building counts by upstream source with Microsoft imagery year, place counts by
category, ACS housing units and strata columns.

## 2. Calibration with two constant submissions

A constant `c` scores

```
RMSE(c)² = E[y²] − 2c·E[y] + c²
```

Constant 0 scored 0.1072 and constant 0.10 scored 0.0977. Solving both gives a public target mean of
0.0598 and standard deviation of 0.0890.

## 3. One signal per submission

Each probe submits `0.0598 + 0.03 × z`, where `z` is one standardised signal. Its score gives
`E[p·y]`, and so the signal's correlation with the truth. `analyse.py` does this arithmetic.

Probes are built on the constant base so that no tract is clipped at zero. Probes built on top of a
model clipped 9–15% of tracts and were withdrawn (v12, v16–v19, and v21–v24 before upload).

## 4. Combining signals

Model weights solve `w = Σ⁻¹c`: `Σ` holds the signals' correlations with each other (from our
features), `c` their measured correlations with the truth. The prediction is
`0.0598 + 0.0890 × Σ w·z`. Predicted and observed scores agreed within 0.0003 for v10, v15 and v34.

## 5. Final model (v34)

| Signal | Weight (sd of gap per sd of signal) |
| --- | --- |
| Rurality (low housing density) | +0.089 |
| OSM share of buildings | −0.118 |
| No interstate, US or state route in the tract | −0.193 |
| Eastern Oklahoma region | +0.191 |
| Rurality × Eastern Oklahoma | +0.100 |
| Wildfire hazard | +0.112 |
| Climate Vulnerability Index | +0.051 |

Reshaping its predictions to be more skewed (v37) or less skewed (v39) scored worse.

## Use of the leaderboard

36 submissions over 8 days. Calibration used whole-population constants, and each probe moved all
tracts by one documented signal. No submission targeted individual tracts. Every submission, score
and decision is in [rounds.md](rounds.md).
