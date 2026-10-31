# Changelog

Versions follow [Semantic Versioning](https://semver.org). Dates are UTC.

## Unreleased

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
