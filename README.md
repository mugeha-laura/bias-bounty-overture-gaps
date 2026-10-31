# Who the map misses

Code and data for an entry to the Zindi **Bias Bounty Mapping Equity Challenge**: estimating
how much Overture Maps under-covers each US census tract, and finding where those gaps fall.

- **Scored submission:** coverage-gap scores for 9,794 tracts in five study regions, built only
  from the challenge datasets. Final picks: `v34` (public RMSE 0.0777) and `v15` (0.0787).
- **Best Bias Discovery:** 697 fire departments in Overture's places are named as fire departments
  but filed under another category, so a category search cannot find them. Rural tracts hide 25%
  of theirs, urban tracts 9%.

The full writeup explains the method and findings. This repository lets anyone reproduce them.

## Reproduce the results

You need Python 3.12 or later and the Zindi sample submission.

1. Install the dependencies:

   ```bash
   pip install -e .
   ```

2. Download `SampleSubmission.csv` from the challenge's Data page on Zindi and save it in this folder.

3. Rebuild the final submission from the committed features (takes seconds):

   ```bash
   python score.py v34
   python check_submission.py submissions/submission_v34.csv
   ```

4. Turn the logged leaderboard scores into each signal's correlation with the truth:

   ```bash
   python analyse.py
   ```

5. Reproduce the Best Bias Discovery tables:

   ```bash
   python discovery_fire.py      # ~5 min, reads the challenge bucket
   python discovery_extra.py
   ```

To rebuild every feature from the raw challenge data (~20 minutes), see
[docs/reproduce.md](docs/reproduce.md).

## What is in this repository

| Path | What it holds |
| --- | --- |
| `features.py` | Builds one row of Overture features per tract, read straight from the challenge bucket |
| `strata_extra.py` | Adds wildfire, heat and drought columns from the challenge strata |
| `score.py` | Every submission as a named version (`v1` … `v39`) |
| `analyse.py` | Converts public leaderboard scores into correlations with the truth |
| `discovery_fire.py`, `discovery_extra.py` | The Best Bias Discovery analysis |
| `check_submission.py` | Checks a submission file before upload |
| `features/` | Per-tract features (generated, committed for speed) |
| `submissions/` | Every file uploaded to the leaderboard |
| `discovery/` | Discovery outputs, including all 697 hidden departments |
| `external/` | The one outside dataset: OpenStreetMap fire stations (discovery only) |
| `figures/` | Screenshots and map layers used in the writeup |
| `docs/` | Method, data sources, reproduction steps and the round-by-round log |

Start with the [documentation index](docs/index.md).

## Data and licences

- **Code:** MIT licence, see [LICENSE](LICENSE).
- **Challenge data** is read from the public bucket on
  [Source Cooperative](https://source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge);
  it is not copied here.
- **Derived data** in `features/`, `discovery/`, `submissions/` and `figures/` comes from Overture Maps
  release 2026-08-19.0 and keeps its licences: ODbL for buildings and transportation, CDLA Permissive
  2.0 for places. © Overture Maps Foundation and its sources, including OpenStreetMap contributors.
- **`external/`** holds OpenStreetMap data under the ODbL. © OpenStreetMap contributors.

Full sources, versions and retrieval dates: [docs/data.md](docs/data.md).

## Challenge rules

Scored submissions use only the challenge datasets. The removed reference layers (TIGER roads,
Microsoft footprints, HIFLD, County Business Patterns) are never downloaded or approximated.
The one outside dataset, OpenStreetMap fire stations, is used in the discovery only.

## Maintainer and contributing

Maintained by Laura Mugeha. Questions and corrections are welcome as issues; see
[CONTRIBUTING.md](CONTRIBUTING.md). Changes are listed in [CHANGELOG.md](CHANGELOG.md).

To cite this work, use [CITATION.cff](CITATION.cff).
