# Contributing

Corrections, questions and reuse of this work are welcome.

## Report a problem

Open an issue and include:

- what you ran (the command and the version name, such as `v34`);
- what you expected and what happened;
- your Python, DuckDB and pandas versions.

## Propose a change

1. Fork the repository and create a branch named for the change, such as `fix/geoid-text` or `docs/method-typo`.
2. Make the change. Keep each pull request to one idea.
3. Check that the final submission still reproduces:

   ```bash
   cp submissions/submission_v34.csv /tmp/v34.csv
   python score.py v34
   python check_submission.py submissions/submission_v34.csv --same-as /tmp/v34.csv
   ```

4. Add a line to `CHANGELOG.md` under "Unreleased".
5. Open a pull request saying what changed and why. The maintainer reviews within a week.

## Code style

- Plain Python with DuckDB and pandas; no new dependency without a reason in the pull request.
- A docstring at the top of every script: what it does, what it reads and writes, how to run it.
- Constants and thresholds named at the top of the file, with a comment saying where the value comes from.
- GEOIDs always read as text.
- Never add the challenge's removed reference layers (TIGER roads, Microsoft footprints, HIFLD,
  County Business Patterns) or copies of them.

## Data

Outside data belongs in `external/` with a row in `docs/data.md`: source URL, retrieval date,
licence and the exact query or download step.
