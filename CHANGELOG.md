# Changelog

Versions follow [Semantic Versioning](https://semver.org). Dates are UTC.

## Unreleased

## 1.1.1 — 2026-10-31

### Changed
- Docstrings for every function and more inline comments in all seven scripts. Comments only:
  the code is unchanged and both final submissions rebuild identically.
- `reproduce.ipynb`: temporary copies go to the system temp folder (works on Windows too);
  department counts show as whole numbers.

## 1.1.0 — 2026-10-31

### Added
- `reproduce.ipynb`: reproduces the final submissions, analysis and discovery tables in Colab, saved with outputs.

### Changed
- `score.py` and `check_submission.py` fall back to the tract list in `submissions/submission_v34.csv`
  when Zindi's `SampleSubmission.csv` is absent.
- Results confirmed identical with pandas 2.2–3.0 and NumPy 2.0–2.5.

## 1.0.0 — 2026-10-31

Version submitted with the Zindi Bias Bounty Mapping Equity Challenge entry.

### Added
- Per-tract Overture features for five study regions (`features.py`, `strata_extra.py`).
- Every leaderboard submission as a named version, `v1` to `v39` (`score.py`).
- Score-to-correlation analysis (`analyse.py`).
- Best Bias Discovery: hidden fire departments, with OpenStreetMap validation
  (`discovery_fire.py`, `discovery_extra.py`).
- Submission checker (`check_submission.py`).
- Documentation in `docs/`.

### Fixed
- `discovery_extra.py` no longer rounds coordinates in `hidden_fire_departments_osm.csv`.
- Bootstrap intervals in `discovery_fire.py` are now identical on every run (fixed row order).

### Withdrawn
- Submission versions v21–v24, before upload: probes on top of a model clipped tracts at zero.
