#!/usr/bin/env python3
"""
Compute HHI, Gini, and Top-N concentration metrics from token holder data.

Input:  CSV with columns: protocol, holder_address, balance
Output: CSV with columns: protocol, hhi, gini, top_1_share, top_5_share,
        top_10_share, n_holders

Usage:
    python compute_hhi.py <input_csv> [output_csv]

If output_csv is not specified, writes to data/governance_concentration.csv
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path


def compute_gini(values: np.ndarray) -> float:
    """Compute Gini coefficient for an array of non-negative values."""
    if len(values) == 0:
        return 0.0
    sorted_vals = np.sort(values)
    n = len(sorted_vals)
    index = np.arange(1, n + 1)
    return float(
        (2 * np.sum(index * sorted_vals) - (n + 1) * np.sum(sorted_vals))
        / (n * np.sum(sorted_vals))
    )


def compute_hhi(shares: np.ndarray) -> float:
    """Compute Herfindahl-Hirschman Index (sum of squared shares)."""
    return float(np.sum(shares ** 2))


def compute_top_n(shares: np.ndarray, n: int) -> float:
    """Compute cumulative share of top-N holders."""
    sorted_desc = np.sort(shares)[::-1]
    return float(np.sum(sorted_desc[:n]))


def analyze_protocol(df: pd.DataFrame) -> dict:
    """Compute all concentration metrics for a single protocol."""
    balances = df["balance"].values.astype(float)
    balances = balances[balances > 0]

    if len(balances) == 0:
        return {
            "hhi": None, "gini": None,
            "top_1_share": None, "top_5_share": None, "top_10_share": None,
            "n_holders": 0,
        }

    total = balances.sum()
    shares = balances / total

    return {
        "hhi": round(compute_hhi(shares), 6),
        "gini": round(compute_gini(balances), 4),
        "top_1_share": round(compute_top_n(shares, 1), 4),
        "top_5_share": round(compute_top_n(shares, 5), 4),
        "top_10_share": round(compute_top_n(shares, 10), 4),
        "n_holders": len(balances),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python compute_hhi.py <input_csv> [output_csv]")
        print()
        print("Input CSV must have columns: protocol, holder_address, balance")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = (
        Path(sys.argv[2]) if len(sys.argv) > 2
        else Path("data") / "governance_concentration.csv"
    )

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    print(f"Reading: {input_path}")
    df = pd.read_csv(input_path)

    required_cols = {"protocol", "holder_address", "balance"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        print(f"ERROR: Missing columns: {missing}")
        print(f"Found columns: {list(df.columns)}")
        sys.exit(1)

    results = []
    for protocol, group in df.groupby("protocol"):
        metrics = analyze_protocol(group)
        metrics["protocol"] = protocol
        results.append(metrics)
        print(
            f"  {protocol}: HHI={metrics['hhi']}, Gini={metrics['gini']}, "
            f"Top-1={metrics['top_1_share']}, N={metrics['n_holders']}"
        )

    result_df = pd.DataFrame(results)
    col_order = [
        "protocol", "hhi", "gini",
        "top_1_share", "top_5_share", "top_10_share", "n_holders",
    ]
    result_df = result_df[col_order].sort_values("hhi")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output_path, index=False)
    print(f"\nSaved: {output_path} ({len(result_df)} protocols)")


if __name__ == "__main__":
    main()
