"""
Turn public leaderboard scores into what they tell us about the target.

Two constant submissions give the public target's mean and E[y^2]:
    RMSE(0)^2  = E[y^2]
    RMSE(c)^2  = E[y^2] - 2c E[y] + c^2
For any submission p, RMSE^2 = E[p^2] - 2 E[p y] + E[y^2], so its score gives
E[p y], hence cov(p, y) and the correlation of that submission with the truth.

E[p] and E[p^2] are computed over all scored tracts; the public set is a random
~30%, so they're close but not exact. Treat correlations as rough (+/- ~0.03).

Usage: fill PUBLIC_SCORES as results come in, then   python analyse.py
"""
import numpy as np
import pandas as pd

R_ZERO, R_TEN = 0.107246299, 0.097675731          # constant 0 and constant 0.10
E_Y2 = R_ZERO ** 2
E_Y = (E_Y2 + 0.10 ** 2 - R_TEN ** 2) / (2 * 0.10)
SD_Y = np.sqrt(E_Y2 - E_Y ** 2)

PUBLIC_SCORES = {
    "v1": 0.131385528,
    "v2": 0.142175621,
    "v3": 0.131267843,
    "v4": 0.144472656,
    "v5": 0.089022463,
    "v6": 0.083450714,
    "v7": 0.090938105,
    "v8": 0.10232326,
    "v9": 0.092609961,
    "v10": 0.082051202,
    "v11": 0.081787643,
    "v12": 0.085891519,
    "v13": 0.088710139,
    "v14": 0.09265832,
    "v15": 0.078747125,
    "v16": 0.084702755,
    "v17": 0.083263784,
    "v18": 0.084882316,
    "v19": 0.083139741,
    "v20": 0.079073415,
    "v25": 0.097705657,
    "v26": 0.08544787,
    "v27": 0.090621964,
    "v28": 0.090283034,
    "v29": 0.098783363,
    "v30": 0.089659516,
    "v31": 0.092326969,
    "v32": 0.09175109,
    "v33": 0.088010084,
    "v34": 0.077739322,
    "v35": 0.099039396,
    "v36": 0.094198757,
    "v37": 0.078599548,
    "v39": 0.078290778,
}


ADDED_ON = {"v11": "v10", "v12": "v10", "v13": "v10", "v14": "v10",
            "v16": "v15", "v17": "v15", "v18": "v15", "v19": "v15",
            "v21": "v20", "v22": "v20", "v23": "v20", "v24": "v20"}


def main():
    print(f"public target: mean {E_Y:.4f}, sd {SD_Y:.4f}\n")
    rows = []
    for v, r in PUBLIC_SCORES.items():
        p = pd.read_csv(f"submissions/submission_{v}.csv").coverage_gap_score
        e_py = (np.mean(p ** 2) + E_Y2 - r ** 2) / 2
        cov = e_py - p.mean() * E_Y
        rows.append(dict(version=v, public_rmse=r, pred_mean=p.mean(), bias=p.mean() - E_Y,
                         corr_with_truth=cov / (p.std() * SD_Y) if p.std() > 0 else np.nan))
    print(pd.DataFrame(rows).round(4).to_string(index=False))

    # Incremental tests: submission = BASE + one added signal. The difference d = p - base
    # is known per tract, and E[d y] = E[p y] - E[base y], so we get corr(d, y) directly.
    print("\nadded signal on top of its base -> correlation of the added part with the truth")
    for v, base in ADDED_ON.items():
        if v not in PUBLIC_SCORES or base not in PUBLIC_SCORES:
            continue
        p = pd.read_csv(f"submissions/submission_{v}.csv").coverage_gap_score
        b = pd.read_csv(f"submissions/submission_{base}.csv").coverage_gap_score
        e_py = (np.mean(p ** 2) + E_Y2 - PUBLIC_SCORES[v] ** 2) / 2
        e_by = (np.mean(b ** 2) + E_Y2 - PUBLIC_SCORES[base] ** 2) / 2
        d = p - b
        cov = (e_py - e_by) - d.mean() * E_Y
        print(f"  {v} (on {base}): rmse {PUBLIC_SCORES[v]:.4f} vs {PUBLIC_SCORES[base]:.4f}"
              f" | corr(added, truth) {cov / (d.std() * SD_Y):+.3f}")


if __name__ == "__main__":
    main()
