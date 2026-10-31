"""
Check a submission file before uploading it to Zindi, and optionally confirm that
it matches a committed copy exactly.

Checks: same tracts as SampleSubmission.csv, GEOIDs read as 11-character text,
no blanks, no duplicates, every score between 0 and 1.

Usage:
    python check_submission.py submissions/submission_v34.csv
    python check_submission.py new.csv --same-as submissions/submission_v34.csv
"""
import sys

import pandas as pd

SAMPLE = "SampleSubmission.csv"   # the Zindi sample submission (authoritative tract list)
# Without the Zindi file, fall back to the tract list in our committed final submission
# (the same 9,794 census tract GEOIDs), so the code runs without a Zindi account.
FALLBACK_TRACTS = "submissions/submission_v34.csv"


def tract_list():
    """The scored tracts, as a one-column DataFrame of GEOIDs read as text."""
    from pathlib import Path as _P
    src = SAMPLE if _P(SAMPLE).exists() else FALLBACK_TRACTS
    if src != SAMPLE:
        print(f"note: {SAMPLE} not found; using the tract list from {FALLBACK_TRACTS}")
    return pd.read_csv(src, dtype={"GEOID": str})[["GEOID"]]


def check(path):
    """Read a submission and return (DataFrame, list of problems); an empty list means OK."""
    sub = pd.read_csv(path, dtype={"GEOID": str})
    sample = tract_list()
    problems = []
    if list(sub.columns[:2]) != ["GEOID", "coverage_gap_score"]:
        problems.append(f"columns should start GEOID, coverage_gap_score; got {list(sub.columns)}")
    if set(sub.GEOID) != set(sample.GEOID):
        problems.append(f"tracts differ from {SAMPLE}: "
                        f"{len(set(sample.GEOID) - set(sub.GEOID))} missing, "
                        f"{len(set(sub.GEOID) - set(sample.GEOID))} extra")
    if sub.GEOID.duplicated().any():
        problems.append(f"{sub.GEOID.duplicated().sum()} duplicate GEOIDs")
    if not (sub.GEOID.str.len() == 11).all():
        problems.append("some GEOIDs are not 11 characters (leading zero lost?)")
    if sub.isna().any().any():
        problems.append("blank cells")
    if not sub.coverage_gap_score.between(0, 1).all():
        problems.append("scores outside 0-1")
    return sub, problems


def main():
    """Run the checks, print OK or FAIL, and exit with status 1 on failure."""
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sub, problems = check(sys.argv[1])
    # Optional exact comparison with another copy (tolerance 1e-12: identical up to float noise)
    if "--same-as" in sys.argv:
        ref = pd.read_csv(sys.argv[sys.argv.index("--same-as") + 1], dtype={"GEOID": str})
        merged = sub.merge(ref, on="GEOID", suffixes=("", "_ref"))
        diff = (merged.coverage_gap_score - merged.coverage_gap_score_ref).abs().max()
        if len(merged) != len(ref) or diff > 1e-12:
            problems.append(f"differs from the committed copy (max difference {diff:.2e})")
    if problems:
        print("FAIL\n- " + "\n- ".join(problems))
        sys.exit(1)
    print(f"OK: {len(sub)} tracts, mean score {sub.coverage_gap_score.mean():.4f}")


if __name__ == "__main__":
    main()
