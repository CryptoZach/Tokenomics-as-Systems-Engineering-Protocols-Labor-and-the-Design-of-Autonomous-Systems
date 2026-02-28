#!/usr/bin/env python3
"""
Compute monthly Spend-to-Reward (S2R) ratio from burn and issuance data.

Input:  CSV with columns: month, burns, issuance
Output: CSV with columns: month, burns, issuance, s2r, fiscal_regime,
        cumulative_burns, cumulative_issuance, cumulative_s2r

Usage:
    python compute_s2r.py <input_csv> [output_csv]

If output_csv is not specified, writes to data/s2r_computed.csv
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path


# Fiscal regime thresholds (Section V.A of Paper 2)
REGIME_THRESHOLDS = [
    (1.0, "net_deflationary"),       # S2R >= 1.0: burns exceed issuance
    (0.35, "approaching_parity"),    # 0.35 <= S2R < 1.0
    (0.10, "emerging_demand"),       # 0.10 <= S2R < 0.35
    (0.0, "subsidy_dependent"),      # S2R < 0.10
]


def classify_regime(s2r: float) -> str:
    """Classify fiscal regime based on S2R value."""
    if pd.isna(s2r):
        return "no_data"
    for threshold, label in REGIME_THRESHOLDS:
        if s2r >= threshold:
            return label
    return "subsidy_dependent"


def compute_s2r(df: pd.DataFrame) -> pd.DataFrame:
    """Compute S2R and cumulative metrics from burn/issuance data."""
    result = df.copy()

    # Monthly S2R
    result["s2r"] = np.where(
        result["issuance"] > 0,
        result["burns"] / result["issuance"],
        np.nan,
    )

    # Fiscal regime classification
    result["fiscal_regime"] = result["s2r"].apply(classify_regime)

    # Cumulative totals
    result["cumulative_burns"] = result["burns"].cumsum()
    result["cumulative_issuance"] = result["issuance"].cumsum()
    result["cumulative_s2r"] = np.where(
        result["cumulative_issuance"] > 0,
        result["cumulative_burns"] / result["cumulative_issuance"],
        np.nan,
    )

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python compute_s2r.py <input_csv> [output_csv]")
        print()
        print("Input CSV must have columns: month, burns, issuance")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = (
        Path(sys.argv[2]) if len(sys.argv) > 2
        else Path("data") / "s2r_computed.csv"
    )

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    print(f"Reading: {input_path}")
    df = pd.read_csv(input_path)

    # Accept flexible column names
    col_map = {}
    burns_mapped = False
    issuance_mapped = False
    for col in df.columns:
        cl = col.lower().strip()
        if cl in ("month", "period", "date"):
            col_map[col] = "month"
        elif "burn" in cl and not burns_mapped:
            # Take first burn-like column only (avoid duplicates)
            col_map[col] = "burns"
            burns_mapped = True
        elif ("issu" in cl or "mint" in cl) and not issuance_mapped:
            col_map[col] = "issuance"
            issuance_mapped = True
    df = df.rename(columns=col_map)

    required = {"month", "burns", "issuance"}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        print(f"ERROR: Missing columns: {missing}")
        print(f"Found columns: {list(df.columns)}")
        sys.exit(1)

    df["month"] = pd.to_datetime(df["month"])
    df = df.sort_values("month").reset_index(drop=True)

    result = compute_s2r(df)

    # Summary statistics
    print(f"\n{'='*60}")
    print(f"S2R ANALYSIS: {len(result)} months")
    print(f"{'='*60}")
    print(f"  Period: {result['month'].iloc[0].strftime('%b %Y')} to "
          f"{result['month'].iloc[-1].strftime('%b %Y')}")
    print(f"  S2R range: {result['s2r'].min():.4f} to {result['s2r'].max():.4f}")
    print(f"  Mean S2R:  {result['s2r'].mean():.4f}")
    print(f"  Cumulative S2R: {result['cumulative_s2r'].iloc[-1]:.4f}")
    print()

    # Regime breakdown
    regime_counts = result["fiscal_regime"].value_counts()
    print("  Fiscal regime distribution:")
    for regime, count in regime_counts.items():
        pct = count / len(result) * 100
        print(f"    {regime}: {count} months ({pct:.0f}%)")

    # Key milestones
    parity_months = result[result["s2r"] >= 1.0]
    if len(parity_months) > 0:
        first = parity_months.iloc[0]
        print(f"\n  First fiscal parity (S2R >= 1.0): "
              f"{first['month'].strftime('%b %Y')} (S2R = {first['s2r']:.3f})")
    else:
        print("\n  Fiscal parity NOT reached in sample period.")

    print(f"{'='*60}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    main()
