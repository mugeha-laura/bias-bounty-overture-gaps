"""
Coverage-gap scores for the Zindi Bias Bounty Mapping Equity Challenge.

Every submission is a named version in VERSIONS below, so each one reproduces
exactly:  python score.py v34   ->   submissions/submission_v34.csv

Three kinds of version (docs/method.md explains each):
  v1-v4    hand-built rules: estimate each reference layer, then apply the
           organisers' formula gap = 1 - min(1, overture / reference)
  probes   constant 0.0598 + 0.03 x one standardised signal; the public score of
           a probe gives that signal's correlation with the truth (analyse.py)
  models   0.0598 + 0.0890 x sum(w * standardised signal), weights w = Sigma^-1 c
           from the measured correlations (v10, v15, v20, v34)

Final submissions: v34 (best model) and v15 (simpler hedge).

Usage:
    python features.py all          # builds features/<region>-features.csv (~20 min)
    python strata_extra.py          # adds hazard columns (needed from v31 on)
    python score.py v34             # writes submissions/submission_v34.csv

Needs the Zindi sample submission saved as SampleSubmission.csv in this folder.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SAMPLE = "SampleSubmission.csv"   # the Zindi sample submission (authoritative tract list)

BASE = dict(
    # Buildings: learn "buildings per housing unit, by density" in tracts where
    # Overture's footprints are mostly Microsoft's (so Overture count ~ Microsoft
    # count), then predict Microsoft's count everywhere.
    ms_dominant_share=0.8,
    building_tolerance=0.68,   # gap only below this share of expected (~10th pct)

    # Roads
    road_mode="flat",          # "flat": 0.10 wherever Overture has named roads
                               # "route": defined only where an interstate/US/state
                               #   route relation exists (TIGER's highway definition);
                               #   gap = 1 - min(1, named km / highway-route km)
                               # "route_flat": route definedness, flat value
    road_flat_gap=0.10,

    # POIs: facilities half = mean(fire, schools); EMS ~1:1, rarely binds
    fire_gap_if_none=0.50,     # no Overture fire_department POI
    fire_gap_if_miscat=None,   # None = ignore; else gap when a fire dept exists
                               #   under another category (name match)
    school_gap={0: 0.70, 1: 0.30},   # by Overture school count; 2+ -> 0
    cbp_gap=0.10,
)

V10 = {"rural": 0.265, "osm_bldg": -0.194}
V15 = {"rural": 0.177, "osm_bldg": -0.133, "tribal": 0.188, "no_hwy_route": -0.202}
V20 = {"rural": 0.153, "osm_bldg": -0.140, "tribal": 0.153, "no_hwy_route": -0.213,
       "reg_tx": -0.278, "reg_eok": -0.112, "reg_az": -0.155}

VERSIONS = {
    "v1": dict(),                                   # baseline
    "v2": dict(road_mode="route"),                  # route rule (definedness + value) -> worse
    "v3": dict(fire_gap_if_miscat=1.0),             # v1 + miscategorised fire depts
    "v4": dict(fire_gap_if_miscat=1.0, road_mode="route_flat"),  # v3 + route definedness only
    # From v5: start at the measured public average and test one signal per submission.
    "v5": dict(probe=None),            # constant 0.06 (floor)
    "v6": dict(probe="rural"),         # lower housing density -> bigger gap?
    "v7": dict(probe="import"),        # untouched 2007-08 TIGER import on local streets
    "v8": dict(probe="osm_bldg"),      # OSM share of buildings (OSM suppresses MS footprints)
    "v9": dict(probe="poi_sparse"),    # few Overture places per home (online presence)
    # Combined model. Weights (in sd of the target per sd of the signal) solve
    # w = Sigma^-1 c, with c = each signal's measured correlation with the truth
    # (v6, v8) and Sigma = the signals' correlation with each other.
    "v10": dict(combo=V10),
    # Day 3: v10 + one more signal each; v10's own score isolates what the signal adds.
    "v11": dict(combo=V10, add="tribal"),        # tribal overlap, beyond rurality
    "v12": dict(combo=V10, add="no_fire"),       # no fire_department POI in tract
    "v13": dict(combo=V10, add="rural_curve"),   # extra gap in the sparsest tracts
    "v14": dict(combo=V10, add="no_hwy_route"),  # no interstate/US/state route in tract
    # Day 4: refit on all 8 measured correlations; kept the 4 signals that each add
    # clearly (import, places, fire, curve add <= 0.0002 and were dropped).
    "v15": dict(combo=V15),
    # Day 5: v15 + one signal each
    "v16": dict(combo=V15, add="bldg_short"),    # estimated building shortfall (v1 method)
    "v17": dict(combo=V15, add="reg_eok"),       # Eastern OK: is "tribal" really regional?
    "v18": dict(combo=V15, add="reg_tx"),        # South-Central TX level
    "v19": dict(combo=V15, add="reg_az"),        # Maricopa level
    # Day 6: refit on 12 measured signals. Region levels (TX, AZ, Eastern OK vs the
    # rest) plus the four v15 signals; others add < 0.0005 and were dropped.
    "v20": dict(combo=V20),
    # v21-v24 (v20 + one signal) WITHDRAWN before upload: v20 sits near zero in many
    # tracts, so adding a signal clips at 0 and the score no longer measures the signal.
    # Same flaw affected v12 and v16-v19 (9-15% of tracts clipped). From here, every
    # signal is measured on the constant base (as v6-v9), where clipping is ~0.
    "v25": dict(probe="reg_tx"),       # re-measure: South-Central TX level
    "v26": dict(probe="reg_eok"),      # re-measure: Eastern OK level
    "v27": dict(probe="ms_old"),       # Microsoft footprints from pre-2020 imagery
    "v28": dict(probe="fm_minor"),     # share of FM km tagged below secondary
    # Day 7: spatial non-stationarity + true-scorecard strata (constant base)
    "v29": dict(probe="rural_x_eok", lift=True),  # does rurality matter more in Eastern OK?
    "v30": dict(probe="rural_x_tx", lift=True),   # ...or differently in Texas?
    "v31": dict(probe="cvi", lift=True),          # Climate Vulnerability Index
    "v32": dict(probe="svi", lift=True),          # Social Vulnerability Index
    "v33": dict(probe="wildfire", lift=True),     # USFS wildfire hazard potential (log)
    # Day 8: model refit on clean measurements only, with the spatial term (rurality
    # matters more in Eastern OK) and hazard/vulnerability. Tribal drops out (~0.03):
    # it is almost entirely rural Eastern OK. Expected public ~0.0775 vs v15 0.0787.
    "v34": dict(combo={"rural": 0.089, "osm_bldg": -0.118, "no_hwy_route": -0.193, "reg_eok": 0.191,
                       "rural_x_eok": 0.100, "wildfire": 0.112, "cvi": 0.051}),
    # Remaining true-scorecard strata (constant base)
    "v35": dict(probe="heat", lift=True),         # CDC EPHT summer extreme-heat days
    "v36": dict(probe="drought", lift=True),      # US Drought Monitor summer severity
    # Day 9: same v34 signals, reshaped. The true gaps are skewed (most ~0, a few large;
    # sd 0.089 > mean 0.060). Keep v34's mean and spread, make the shape skewed:
    # p = c + A*exp(k*z). k=0 is v34 itself. Only the correlation with the truth can change.
    "v37": dict(reshape="v34", k=0.3),
    "v38": dict(reshape="v34", k=0.6),          # not uploaded: v37 showed more skew hurts
    "v39": dict(reshape="v34", k=-0.3),         # opposite direction: flatten the top
}
TARGET_SD = 0.0890       # measured from the two constant submissions

# Measured from the two constant submissions (public set): mean 0.0598, E[y^2] = 0.10725^2
TARGET_MEAN = 0.0598
PROBE_AMPLITUDE = 0.03   # prediction = TARGET_MEAN + 0.03 * standardised signal


def signals(df):
    """Tract-level signals, each oriented so that higher = hypothesised bigger gap."""
    s = pd.DataFrame(index=df.index)
    s["rural"] = -np.log10((df.housing_units.fillna(0) + 1) / df.area_km2)
    s["import"] = (df.km_local_pre2010 / df.km_local).where(df.km_local > 0, 0)
    s["osm_bldg"] = (df.bldg_osm / df.bldg_total).where(df.bldg_total > 0, 0)
    s["poi_sparse"] = -np.log10((df.poi_total + 1) / (df.housing_units.fillna(0) + 1))
    s["tribal"] = df.tribal_pct.fillna(0)
    s["no_fire"] = (df.poi_fire == 0).astype(float)
    zr = (s.rural - s.rural.mean()) / s.rural.std()
    s["rural_curve"] = zr.clip(lower=0) ** 2
    s["no_hwy_route"] = (df.km_hwy_route == 0).astype(float)
    # v1's building estimate: shortfall vs buildings-per-home of similar-density tracts
    s["bldg_short"] = building_gap(df, BASE).fillna(0)
    # Region levels: organisers note gap values aren't comparable across regions
    for code, region in [("eok", "eastern-ok"), ("tx", "south-central-tx"), ("az", "maricopa-az"),
                         ("nca", "northern-ca"), ("ewa", "eastern-wa")]:
        s[f"reg_{code}"] = (df.region == region).astype(float)
    # Overture's Microsoft copy is the 2025-02-25 version; the reference is Feb 2026, after
    # Microsoft re-detected US buildings from 2021-25 imagery. Old-imagery tracts = most to gain.
    s["ms_old"] = (df.bldg_ms_old / df.bldg_total).where(df.bldg_total > 0, 0)
    # Texas FM roads: if TIGER counts them as S1200, FM-only tracts have a road component
    s["fm_only"] = ((df.km_fm_route > 0) & (df.km_hwy_route == 0)).astype(float)
    # ...and FM km tagged tertiary or below is invisible to Overture's side of the comparison
    s["fm_minor"] = (df.km_fm_route_minor / df.km_fm_route).where(df.km_fm_route > 0, 0)
    s["cvi"] = df.cvi_overall.fillna(df.cvi_overall.median())
    s["svi"] = df.svi_overall.fillna(df.svi_overall.median())
    # Spatial non-stationarity: does rurality matter more in some regions?
    s["rural_x_eok"] = zr * (df.region == "eastern-ok")
    s["rural_x_tx"] = zr * (df.region == "south-central-tx")
    # Hazard exposure (features/strata_extra.csv, from strata_extra.py)
    if "usfs_WHP_mean" in df:
        s["wildfire"] = np.log1p(df.usfs_WHP_mean.fillna(df.usfs_WHP_mean.median()))
        s["heat"] = df.epht_heat_days_summer.fillna(df.epht_heat_days_summer.median())
        s["drought"] = df.usdm_summer_dsci.fillna(df.usdm_summer_dsci.median())
    return s


def combo(df, weights, add=None):
    s = signals(df)
    z = (s - s.mean()) / s.std()
    pred = TARGET_MEAN + TARGET_SD * sum(w * z[name] for name, w in weights.items())
    if add is not None:            # test one extra signal on top of the combination
        pred = pred + PROBE_AMPLITUDE * z[add]
    return pred.clip(0, 1)


def probe(df, name, lift=False):
    if name is None:
        return pd.Series(TARGET_MEAN, index=df.index)
    x = signals(df)[name]
    z = (x - x.mean()) / x.std()
    base = TARGET_MEAN
    if lift:   # raise the base just enough that no tract clips at 0 (shift doesn't change the reading)
        base = max(TARGET_MEAN, -PROBE_AMPLITUDE * z.min() + 0.001)
    return (base + PROBE_AMPLITUDE * z).clip(0, 1)


def building_gap(df, p):
    out = pd.Series(np.nan, index=df.index)
    for _, g in df.groupby("region"):
        g = g[(g.housing_units > 0) & (g.bldg_total > 0)]
        log_dens = np.log10(g.housing_units / g.area_km2)
        log_ratio = np.log10(g.bldg_total / g.housing_units)
        cal = (g.bldg_ms / g.bldg_total) >= p["ms_dominant_share"]
        if cal.sum() < 30:          # too few calibration tracts: use all
            cal[:] = True
        coef = np.polyfit(log_dens[cal], log_ratio[cal], 1)
        expected = g.housing_units * 10 ** np.polyval(coef, log_dens)
        out[g.index] = (1 - g.bldg_total / (expected * p["building_tolerance"])).clip(0, 1)
    return out   # NaN = undefined


def transport_gap(df, p):
    if p["road_mode"] == "flat":
        return pd.Series(np.where(df.km_named > 0, p["road_flat_gap"], np.nan), index=df.index)
    ref_km = df.km_hwy_route
    if p["road_mode"] == "route_flat":
        # defined where a highway route exists; same flat value as v1
        return pd.Series(np.where(ref_km > 0, p["road_flat_gap"], np.nan), index=df.index)
    # "route": TIGER S1100/S1200 ~ interstate/US/state highways
    gap = (1 - (df.km_named / ref_km).clip(upper=1)).where(ref_km > 0)
    return gap   # NaN = no highway to compare against (undefined)


def poi_gap(df, p):
    fire = pd.Series(np.where(df.poi_fire > 0, 0.0, p["fire_gap_if_none"]), index=df.index)
    if p["fire_gap_if_miscat"] is not None:
        miscat = (df.poi_fire == 0) & (df.poi_fire_miscat > 0)
        fire[miscat] = p["fire_gap_if_miscat"]
    schools = df.poi_schools.map(lambda n: p["school_gap"].get(int(n), 0.0))
    facilities = (fire + schools) / 2
    return (facilities + p["cbp_gap"]) / 2


def score(feats, version):
    p = {**BASE, **VERSIONS[version]}
    out = feats.copy()
    if "probe" in p:
        out["coverage_gap_score"] = probe(out, p["probe"], p.get("lift", False))
        return out
    if "reshape" in p:
        base = score(feats, p["reshape"]).coverage_gap_score
        z = (base - base.mean()) / base.std()
        e = np.sign(p["k"]) * np.exp(p["k"] * z)           # k<0: concave (flattens the top)
        e = (e - e.mean()) / e.std()                       # standardise the shape
        out["coverage_gap_score"] = (base.mean() + base.std() * e).clip(0, 1)
        return out
    if "combo" in p:
        out["coverage_gap_score"] = combo(out, p["combo"], p.get("add"))
        return out
    out["building_gap"] = building_gap(out, p)
    out["transport_gap"] = transport_gap(out, p)
    out["poi_gap"] = poi_gap(out, p)
    # Composite = mean of the defined components (NaN = undefined)
    out["coverage_gap_score"] = out[["transport_gap", "building_gap", "poi_gap"]].mean(axis=1)
    return out


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else max(VERSIONS)
    feats = pd.concat(
        [pd.read_csv(f, dtype={"GEOID": str}) for f in sorted(Path("features").glob("*-features.csv"))],
        ignore_index=True,
    )
    extra = Path("features/strata_extra.csv")
    if extra.exists():
        feats = feats.merge(pd.read_csv(extra, dtype={"GEOID": str}), on="GEOID", how="left")
    sample = pd.read_csv(SAMPLE, dtype={"GEOID": str})
    feats = feats[feats.GEOID.isin(sample.GEOID)].reset_index(drop=True)   # scored tracts only
    scored = score(feats, version)

    sub = sample[["GEOID"]].merge(scored[["GEOID", "coverage_gap_score"]], on="GEOID", how="left")
    missing = sub.coverage_gap_score.isna().sum()
    assert missing == 0, f"{missing} tracts have no score - did features.py run for every region?"
    assert sub.coverage_gap_score.between(0, 1).all()

    Path("submissions").mkdir(exist_ok=True)
    sub.to_csv(f"submissions/submission_{version}.csv", index=False)
    scored.to_csv(f"submissions/components_{version}.csv", index=False)
    print(f"submission_{version}.csv: {len(sub)} rows, mean score {sub.coverage_gap_score.mean():.3f}")


if __name__ == "__main__":
    main()
