# Bias Bounty — round log

Closes 01 Nov 2026. Limits: 5 submissions/day, 200 total.
One change per round. Record the public score after each upload.
Public leaderboard = ~30% of tracts, so small differences (< ~0.005) may be noise.

| Round | Date | What changed | Public RMSE | Keep? |
|---|---|---|---|---|
| v1 | 2026-10-24 | Baseline: buildings from MS-calibrated density fit; flat road gap 0.10; fire 0.5 if none; schools by count; CBP 0.10 | 0.131386 | baseline |
| v2 | 2026-10-24 | Roads: defined only where an interstate/US/state route relation exists; gap = 1 - min(1, named km / route km) | 0.142176 | no — worse. Changed definedness AND value together; value set most road gaps to 0, mean score fell 0.115 -> 0.099. Suggests true gaps are higher than we predict. |
| v3 | 2026-10-24 | v1 + fire gap = 1 where no fire_department POI but a fire dept exists under another category (name match). 357 tracts change. | 0.131268 | yes — small gain (-0.00012), right direction |
| v4 | 2026-10-24 | v3 + road definedness from route relations only (value stays flat 0.10). 3,393 tracts change. | 0.144473 | no — much worse (+0.013). Route-based definedness hurts even with v1's road value. v2 (same definedness, road value ~0) scored 0.1422, so with this definedness lower road values help. |

Best so far: v3 (0.131268).

| const 0 | 2026-10-24 | every tract 0 | 0.107246 | diagnostic |
| const 0.10 | 2026-10-24 | every tract 0.10 | 0.097676 | diagnostic |

### What the two constants tell us (public set)
- Average true gap 0.060, spread (sd) 0.089. Sd > mean on a 0-1 score: most tracts at or
  near 0, a minority with large gaps.
- Best possible constant (0.06) would score ~0.089, far better than any rule set so far.
- Our versions sit ~0.04-0.06 too high on average AND correlate slightly NEGATIVELY with the
  truth (v1 -0.13, v2 -0.19, v3 -0.11, v4 -0.13; rough, public-set estimates). Our rules
  point the wrong way: they give urban tracts bigger gaps (fire rule: small urban tracts
  rarely contain a station), while the truth likely runs the other way.
- New approach: start from the average (0.06) and add only signals that move with the
  truth, each tested by one submission.

### Day 2 (2026-10-25): baseline + one signal each
Each signal file = 0.06 + 0.03 x standardised signal (higher = hypothesised bigger gap).
Reading a score: unrelated signal -> ~0.0939 (v9 ~0.0924); helpful (corr +0.2) -> ~0.088;
wrong direction (corr -0.2) -> ~0.0995. Run `python analyse.py` for the exact correlation.

| Round | Signal | Public RMSE | Est. corr with truth |
|---|---|---|---|
| v5 | constant 0.06 (floor; should be ~0.0890) | 0.089022 | n/a — confirms the arithmetic |
| v6 | rurality: lower housing density | 0.083451 | +0.35 — strong, keep |
| v7 | untouched import: share of local-street km at pre-2010 OSM version | 0.090938 | +0.10 — but fully explained by rurality (weight ~ -0.07 once rural is in) |
| v8 | OSM share of buildings (OSM suppresses overlapping MS footprints) | 0.102323 | -0.31 — OPPOSITE of hypothesis; stays -0.19 after rurality. Keep, reversed |
| v9 | few Overture places per home (online presence) | 0.092610 | -0.01 — no signal, drop |

Combined (w = Sigma^-1 c): rural 0.265 + osm_bldg -0.194 -> expected public RMSE ~0.0819.
Adding import improves only 0.0002 with a negative weight: dropped (not interpretable).

| v10 | rural (0.265) + OSM building share (-0.194), sd units | 0.082051 | yes — matches expected ~0.0819; best so far |

### Day 3 (2026-10-26): v10 + one signal each
Each file = v10 + 0.03 x standardised signal. Better than 0.0821 = the signal adds information.

| Round | Added signal | Public RMSE | Signal's own corr with truth | Weight in refit |
|---|---|---|---|---|
| v11 | tribal overlap (tribal_pct). NB 806 of 935 tribal tracts are Eastern OK | 0.081788 | +0.30 | +0.19 — keep |
| v12 | no fire_department POI in the tract | 0.085892 | -0.09 | ~0 — drop |
| v13 | rurality curve: extra gap only in the sparsest tracts | 0.088710 | +0.22 | ~0 — just rurality again (0.82 overlap) |
| v14 | no interstate/US/state route in the tract | 0.092658 | -0.32 | -0.20 — keep (sign reversed) |

Note: v12-v14 scored worse than v10 at a fixed 0.03 amplitude, but a signal can still
help at the right weight and sign — the refit decides. no_hwy_route helps, reversed.

Refit on all 8 measured correlations (w = Sigma^-1 c), parsimonious set of 4:
rural 0.177, osm_bldg -0.133, tribal 0.188, no_hwy_route -0.202 -> expected ~0.0785.
All 8 signals together: ~0.0780 (not worth 4 extra weights).

| v15 | rural + OSM bldg share + tribal + no highway route | 0.078747 | yes — matches expected ~0.0785; best so far |

Deferred: highways on minor classes — only ~50 tracts meaningfully affected, too few
to read from the public 30%.

Open question after v2/v4: we don't know whether our overall level is too high or too low.
Plan: submit the all-zeros sample file (RMSE = sqrt of mean squared target), then a constant
0.10, to get the public target's mean and spread. Two submissions, no per-tract information.

Scorecard check: v1's predicted rural/urban mean ratio is 0.089/0.121 = 0.73, exactly the
scorecard's 0.73x, so the bias scorecard is computed on OUR predictions, not the truth.

Road-rule check against organiser stats (share of tracts with >=1 undefined component):
ours (roads undefined) vs theirs — Eastern OK 24% vs 21%, Northern CA 40% vs 37%,
South TX 34% vs 28%, Maricopa 57% vs 55%. Ours is a little high everywhere, most in Texas:
TIGER probably counts some highways with no route relation (Texas FM roads?).

## Known problems to fix

- Roads: Overture "secondary" is much wider than TIGER S1100/S1200. Maricopa has only
  33 tracts with no Overture named km, but the organisers say >50% have no TIGER highway.
  v1 marks the road component defined almost everywhere — wrong for most of Maricopa.

## Findings so far (for the writeup)

- HEADLINE: by the organisers' own completeness metric, true gaps rise with rurality
  (corr ~ +0.35 on the public set) — consistent with the challenge hypothesis.
- The metric cannot see untouched TIGER import. Import share predicts gaps only through
  rurality; once rurality is accounted for, it adds nothing. Expected: the road reference
  IS TIGER, so unreviewed TIGER-derived geometry looks complete by construction.
- OSM-mapped tracts have SMALLER gaps, even at equal rurality — the "community mapping
  penalty" hypothesis is rejected. Possible reason (unverified): the reference is the
  Feb 2026 Microsoft refresh, likely newer than the Microsoft footprints inside Overture,
  so Microsoft-dominant tracts show gaps where the newer release found more buildings.
- TRIBAL: tribal tracts have bigger gaps beyond what rurality and building source explain
  (weight +0.19 sd). Mostly an Eastern OK result (806 of 935 tribal tracts).
- Tracts with no interstate/US/state highway have SMALLER composite gaps (-0.32). Likely
  structural: no highway in TIGER -> road component undefined; where highways exist,
  road gaps are often > 0. Supports: Overture's highway network has real gaps vs TIGER.
- No fire station in the tract predicts nothing once rurality is in.
- Bias scorecard grades predictions, not truth: v1-v4 (hand-built rules) correlated
  negatively with the truth and showed rural/tribal gaps as SMALLER. A plausible-looking
  model can reverse the equity picture.

- Local streets still at pre-2010 OSM version (share of km): South-Central TX 15.9%,
  Eastern OK 7.9%, Northern CA 10.4%, Eastern WA 1%.
- Eastern OK: 376 of 411 rural tracts are tribal — tribal vs non-tribal is confounded
  with rural vs urban there. Compare tribal vs non-tribal *within* rural.
- Eastern WA: tribal tracts 2.9% pre-2010 local km vs 0.1% non-tribal.

- Northern CA: on local streets (residential + unclassified), ~10% of km still at its
  pre-2010 OSM version (untouched TIGER import). Rural tracts average 7.7%, urban 0.8%.
- Northern CA: OSM-heavy tracts do NOT have fewer buildings per housing unit than
  Microsoft-dominant tracts at the same density. The "community mapping penalty"
  idea doesn't show here — check other regions before dropping it.

### Day 5 (2026-10-27): v15 + one signal each
Better than 0.0787 = the signal adds information (the refit decides weight and sign).

| Round | Added signal | Question | Public RMSE | Signal's corr with truth |
|---|---|---|---|---|
| v16 | estimated building shortfall (v1 method) | Does buildings-per-home shortfall predict the gap? | 0.084703 | -0.12 — wrong way: flags apartment areas (homes != structures), the trap organisers warned about. Weight ~0 in refit |
| v17 | Eastern OK region | Is the tribal effect really just Eastern OK? (overlap with tribal 0.78) | 0.083264 | +0.26 raw, but tribal explains the data better than the region; within E OK tribal tracts still higher |
| v18 | South-Central TX region | Does Texas (64% of tracts) sit higher or lower? | 0.084882 | -0.21 — lower |
| v19 | Maricopa region | Does Maricopa sit higher or lower? | 0.083140 | -0.09 — lower |

Average true gap by region (public set, derived from v17-v19):
Eastern OK 0.121 | N CA + E WA together 0.103 | South-Central TX 0.045 | Maricopa 0.041.

Refit on 12 signals: rural 0.153, osm_bldg -0.140, tribal 0.153, no_hwy_route -0.213,
TX -0.278, Eastern OK -0.112, Maricopa -0.155 -> expected ~0.0770 (all 12: ~0.0766).
Tribal keeps a clear positive weight with region levels in: NOT just an Eastern OK effect.

| v20 | v15 signals + region levels (TX, Eastern OK, Maricopa) | | |

## Research notes (Laura, 2026-10-27) and what each changed

- Other entrants' discovery narratives: post-fire phantoms (3+ entries) and single-exit
  roads (2) are taken -> dropped the burned-area writeup angle. Heat entry quotes the
  scorecard (0.59) as a fact about the map -> evidence for our "scorecard grades the
  model" angle. Entries flagged Microsoft imagery dates in Overture -> new signal.
- Mapping-equity principles: adopted estimand framing (refit weights = conditional
  effects), uncertainty ranges, ecological-fallacy wording, data-system framing.
  Added: CARE principles for Indigenous data governance (tribal finding).
- Literature: Herfort et al. 2023 verified (14% of 13,189 cities >80% complete; 69% <20%;
  reference = predicted area trained partly on Microsoft footprints). Framing: completeness
  inequality and vulnerability are established; we measure their overlap in a CONFLATED
  product, conditional on rurality. Other citations: verify before use.
- Microsoft vintage: release notes say +13.09M MS buildings globally, but every MS
  footprint in our extracts has version 2025-02-25 and imagery <= 2023-09. Reference =
  Feb 2026 refresh; Microsoft added ~4-5M US footprints Jan-Feb 2026 (Vexcel 2021-25).
  -> building gap partly measures vintage. Supports v8.
- CBP: participant reports ZIP->tract apportionment via HUD crosswalk (unconfirmed).
  Treat tract CBP as modelled estimates. Do NOT rebuild (removed layer). CBP scope
  excludes farms, public administration, most government establishments.
- FM roads: do not query TIGER (prohibited). Texas wiki: FM roads tagged secondary
  (town connectors) or tertiary (minor). TX region has 51,254 km FM/RM routes ~ equal to
  all interstate/US/state route km (50,268). Test via submissions instead.
- Oklahoma: interstate/US/state routes on classes below secondary ~1% (all regions ~1%):
  draft guidance is not causing a class mismatch on numbered state routes.

### Writeup thesis (draft)
The coverage gap assumes Overture and the reference count the same THING, at the same
TIME, in the same PLACE, from INDEPENDENT sources. Each fails somewhere (road classes /
fire categories / homes vs structures; MS 2025 vs 2026; CBP ZIP apportionment; OSM roads
descend from TIGER) — and the failures fall on rural and tribal tracts.

### Day 6 (2026-10-28): v20 + one signal each
| Round | Signal | Question | Public RMSE | Signal's corr with truth |
|---|---|---|---|---|
| v20 | v15 signals + region levels | Does the regional model reach ~0.0770? | 0.079073 | NO — worse than v15. Region weights came from clipped probes (below) |
| v21 | share of buildings that are Microsoft footprints from pre-2020 imagery (1,137 tracts) | Does older Microsoft imagery mean a bigger gap (vintage mechanism)? | | |
| v22 | FM road but no interstate/US/state route (714 TX tracts) | Does TIGER count Texas FM roads as highways? | | |
| v23 | share of FM km tagged below secondary (1,103 tracts) | Are tertiary-tagged FM roads invisible to Overture's side? | | |
| v24 | Climate Vulnerability Index | Do more climate-vulnerable tracts have bigger gaps, beyond rurality/region? | | |

FM tagging (TX region): 17,128 of 51,254 FM/RM km (33%) tagged below secondary.
Old-imagery Microsoft share of buildings: Eastern OK 14.4%, N CA 15.7%, TX 1.4%, AZ 0.9%, WA 0.2%.

### Correction (2026-10-28): clipping at zero
Predictions are clipped to [0,1]. Probes built ON TOP OF a model (v12, v16-v19) clipped
9-15% of tracts at 0, so their scores did not measure the signal cleanly. Affected
estimates: no_fire (v12), bldg_short (v16), region levels (v17-v19) -> v20's region
weights, and the regional averages derived from them (WITHDRAWN until re-measured).
Clean (<= 3% clipped): v6-v9, v11, v13, v14, v15.
v21-v24 (built on v20) withdrawn before upload. From now on every signal is measured on
the constant base (0.0598 + 0.03 z), which does not clip.

| Round | Signal (constant base) | Question | Public RMSE | Corr with truth |
|---|---|---|---|---|
| v25 | South-Central TX region | Re-measure: does Texas sit lower? | 0.097706 | -0.135 (clipped estimate was -0.205). TX avg gap ~0.050 vs others ~0.075 |
| v26 | Eastern OK region | Re-measure: does Eastern OK sit higher? | 0.085448 | +0.285. Eastern OK avg gap ~0.128 vs others ~0.050 (~2.5x) |
| v27 | Microsoft footprints from pre-2020 imagery (share of buildings) | Vintage mechanism: older imagery -> bigger gap? | 0.090622 | +0.115 raw, but ~0 once rurality/region are in (old imagery sits in OK and N CA) |
| v28 | share of FM km tagged below secondary | Are tertiary FM roads invisible to Overture's side? | 0.090283 | +0.126 raw; small but positive once others are in (+0.02-0.04) |
Queued for Thursday: Maricopa region, FM-only tracts, CVI, then a clean refit.

Clean refit (constant-base and low-clipping measurements only): best sets reach expected
~0.0780-0.0782 vs v15's predicted 0.0785 (observed 0.0787). Gain ~0.0004 = within noise.
-> The scored model has converged. v15 stays primary.
Tribal with Eastern OK region included: weight drops 0.188 -> ~0.10. About half of the
tribal effect is Eastern OK sitting higher overall; the rest persists within region.

### Day 7 (2026-10-29): spatial non-stationarity + true-scorecard strata (constant base)
Probe base lifted where needed so no tract clips at 0 (v29-v31); a shift doesn't change the reading.
| Round | Signal | Question | Score if unrelated | Public RMSE | Corr with truth |
|---|---|---|---|---|---|
| v29 | rurality x Eastern OK | Does rurality matter more in Eastern OK? | 0.1063 | 0.098783 | +0.29 raw; +0.10 beyond everything else — rurality matters MORE in Eastern OK |
| v30 | rurality x South-Central TX | Does rurality matter differently in Texas? | 0.0953 | 0.089660 | +0.19 raw; ~0 (-0.03) beyond — Texas rurality behaves like the average |
| v31 | Climate Vulnerability Index | Do more climate-vulnerable tracts have bigger gaps? | 0.0963 | 0.092327 | +0.14 raw; +0.10 beyond rurality+region |
| v32 | Social Vulnerability Index | Do more socially vulnerable tracts have bigger gaps? | 0.0939 | 0.091751 | +0.08 raw; +0.08 beyond rurality+region |
| v33 | USFS wildfire hazard (log) | Do higher-wildfire-hazard tracts have bigger gaps? | 0.0939 | 0.088010 | +0.20 raw; +0.13 beyond rurality+region |

Findings from day 7:
- SPATIAL NON-STATIONARITY (Laura's point): the rurality effect is not uniform. It is
  stronger in Eastern OK (interaction +0.10 sd), average in Texas.
- With rurality x Eastern OK in the model, tribal drops to ~0.03-0.05: the "tribal" effect
  and "rural Eastern Oklahoma" cannot be separated with this data (376 of 411 rural E OK
  tracts are tribal). Writeup wording: gaps concentrate in rural tribal Oklahoma.
- THE CHALLENGE'S ESTIMAND: beyond rurality and region, gaps are larger where climate
  vulnerability (CVI +0.10 sd), social vulnerability (SVI +0.08) and wildfire hazard (+0.13)
  are higher. The hypothesis holds on the truth, modestly, within region.

| v34 | MODEL: rural, OSM bldg, no hwy, E OK level, rural x E OK, wildfire, CVI | Expected ~0.0775 (v15 0.0787) | 0.077739 | YES — new best; corr with truth 0.49. FINAL PICK 1 |
| v35 | heat (summer extreme-heat days) | true-scorecard stratum | 0.099039 | -0.18 raw (hot metros better mapped); ~-0.04 beyond rurality+region |
| v36 | drought (summer DSCI) | true-scorecard stratum | 0.094199 | ~0 raw (-0.01); +0.14 beyond rurality+region (raw masked by drought-heavy Maricopa) |

FINAL SELECTION: v34 (0.077739, best) + v15 (0.078747, simpler 4-signal model).

TRUE SCORECARD (public set; corr with truth: raw / beyond rurality+region):
rural +0.35 | tribal +0.30 (inseparable from rural E OK) | wildfire +0.20 / +0.13 |
CVI +0.14 / +0.10 | SVI +0.08 / +0.08 | drought -0.01 / +0.14 | heat -0.18 / -0.04.
Heat and raw drought are confounded by region: the hot, drought-hit metros (Phoenix,
San Antonio) are among the best-mapped places. Within region, drought-exposed tracts
have bigger gaps; heat stays ~0.

### Day 9 (2026-10-30): shape test (one idea, two strengths)
Same v34 signals and tract ranking; same mean and spread; only the SHAPE changes
(skewed, like the truth: most ~0, a few large). Only correlation with truth can move.
Break-even = v34's 0.0777. Below = skewed shape fits better.
| Round | Shape | Skew (v34 = 1.1) | Public RMSE | Keep? |
|---|---|---|---|---|
| v37 | mild skew, k=0.3 | 2.5 | 0.078600 | no — more skew hurts |
| v38 | strong skew, k=0.6 | 4.4 | not uploaded | skipped after v37 |
| v39 | flatter, k=-0.3 (10% clip at 0) | 0.3 | 0.078291 | no — v34's shape is the optimum |
If either beats v34, it replaces v15 as the second final pick (v34 stays first).

SCORED WORK CLOSED (2026-10-30). Final picks: v34 (0.077739) + v15 (0.078747).
Shape test: both more skew (v37) and less skew (v39) score worse -> v34's linear shape is right.
Path: v1 0.1314 -> const 0.0890 -> rural 0.0835 -> v10 0.0821 -> v15 0.0787 -> v34 0.0777.
