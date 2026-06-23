from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import pandas as pd


TABLE_S3 = Path("/Users/iyubin/Downloads/Table S3.xlsx")
RUN_DIR = Path("outputs/figure3/runs")
OUT_DIR = Path("outputs/figure3")
RATE_RE = re.compile(
    r"(?P<condition>self_(?:on|off))_n(?P<n_tf>\d+)_(?P<combo_id>combo\d+_.+)_seed(?P<seed>\d+)_rates\.txt$"
)


def load_measured() -> tuple[pd.DataFrame, float]:
    single = pd.read_excel(TABLE_S3, sheet_name="single-hit").rename(columns={"expression level": "measured"})
    wt = float(single.loc[single["name"] == "synCRE_Promega_0", "measured"].iloc[0])
    single["measured_delta"] = np.log2(single["measured"] / wt)
    return single, wt


def parse_rate_file(path: Path, measured: pd.DataFrame) -> dict[str, object] | None:
    match = RATE_RE.match(path.name)
    if not match:
        return None
    rates = pd.read_csv(path, sep=r"\s+").rename(columns={"id": "name", "HEK293_MPRA": "predicted"})
    wt_pred = float(rates.loc[rates["name"] == "synCRE_Promega_0", "predicted"].iloc[0])
    rates["predicted_delta"] = np.log2(rates["predicted"] / wt_pred)
    df = measured.merge(rates[["name", "predicted_delta"]], on="name")
    mutants = df[df["name"] != "synCRE_Promega_0"]
    x = mutants["measured_delta"].to_numpy(float)
    y = mutants["predicted_delta"].to_numpy(float)
    pearson_r = float(np.corrcoef(x, y)[0, 1])
    rmse = float(np.sqrt(np.mean((y - x) ** 2)))
    groups = match.groupdict()
    score_path = path.with_name(path.name.replace("_rates.txt", "_score.txt"))
    total_score = np.nan
    if score_path.exists():
        score = pd.read_csv(score_path, sep=r"\s+", skiprows=1, names=["name", "score", "count"])
        row = score.loc[score["name"] == "Total", "score"]
        if len(row):
            total_score = float(row.iloc[0])
    return {
        "condition": groups["condition"],
        "self_competition": groups["condition"] == "self_on",
        "n_tf": int(groups["n_tf"]),
        "combo_id": groups["combo_id"],
        "seed": int(groups["seed"]),
        "pearson_r": pearson_r,
        "r_squared": pearson_r * pearson_r,
        "rmse_delta_log2": rmse,
        "total_sse_score": total_score,
        "rates_file": str(path),
    }


def main() -> None:
    measured, _ = load_measured()
    rows = []
    for path in sorted(RUN_DIR.glob("*_rates.txt")):
        row = parse_rate_file(path, measured)
        if row is not None:
            rows.append(row)
    if not rows:
        raise SystemExit(f"No completed Figure 3 rate files found in {RUN_DIR}")
    out = pd.DataFrame(rows).sort_values(["condition", "n_tf", "combo_id", "seed"])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "figure3_completed_results.csv"
    out.to_csv(out_path, index=False)
    summary = (
        out.groupby(["condition", "n_tf"])
        .agg(
            n_runs=("pearson_r", "size"),
            mean_r=("pearson_r", "mean"),
            median_r=("pearson_r", "median"),
            max_r=("pearson_r", "max"),
            min_rmse=("rmse_delta_log2", "min"),
        )
        .reset_index()
    )
    summary_path = OUT_DIR / "figure3_completed_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(out.to_string(index=False))
    print(f"wrote {out_path}")
    print(f"wrote {summary_path}")


if __name__ == "__main__":
    main()
