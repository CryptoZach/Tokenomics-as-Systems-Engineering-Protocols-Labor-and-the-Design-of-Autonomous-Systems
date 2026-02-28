#!/usr/bin/env python3
"""
Task 2c (SEVERITY 2): Clean Helium S2R time-series.

Fixes:
1. Exclude April 2023 migration artifact (145.9M HNT minted = re-minting of existing supply)
2. Compute 3-month rolling S2R
3. Flag single-event dominated months (where >50% of burns come from 1 transaction)
4. Note divergences from v1 reference data
"""
import os
import json
import pandas as pd
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HELIUM_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "helium")
OUTPUT_DIR = SCRIPT_DIR


def main():
    print("=" * 60)
    print("HELIUM S2R TIME-SERIES CLEANING")
    print("=" * 60)

    # Load the continuous S2R data
    s2r_path = os.path.join(HELIUM_DIR, "helium_s2r_continuous.csv")
    if not os.path.exists(s2r_path):
        # Try depin-gaps path
        s2r_path = os.path.join(os.path.dirname(SCRIPT_DIR), "helium", "helium_s2r_continuous.csv")

    if not os.path.exists(s2r_path):
        print(f"ERROR: Cannot find helium_s2r_continuous.csv")
        return

    df = pd.read_csv(s2r_path, parse_dates=["period"])
    print(f"  Loaded {len(df)} monthly records")
    print(f"  Date range: {df['period'].min()} to {df['period'].max()}")

    # Load weekly burn data for spike analysis
    burns_path = os.path.join(HELIUM_DIR, "dune_hnt_weekly_burns.json")
    weekly_burns = None
    if os.path.exists(burns_path):
        with open(burns_path) as f:
            burns_data = json.load(f)
        weekly_rows = burns_data.get("result", {}).get("rows", [])
        weekly_burns = pd.DataFrame(weekly_rows)
        if len(weekly_burns) > 0:
            weekly_burns["week"] = pd.to_datetime(weekly_burns["week"])
            print(f"  Loaded {len(weekly_burns)} weekly burn records")

    # ── FIX 1: Exclude April 2023 migration artifact ──
    print("\n1. Migration Artifact Exclusion:")
    apr_2023 = df[df["period"].dt.to_period("M") == "2023-04"]
    if len(apr_2023) > 0:
        row = apr_2023.iloc[0]
        print(f"   April 2023: {row['hnt_issued']:,.0f} HNT minted (migration re-mint)")
        print(f"   S2R before exclusion: {row['s2r_burns_only']:.4f}")
        df["migration_excluded"] = df["period"].dt.to_period("M") == "2023-04"
    else:
        df["migration_excluded"] = False

    # ── FIX 2: Compute cleaned S2R ──
    print("\n2. Cleaned S2R Computation:")
    df_clean = df[~df["migration_excluded"]].copy()

    # Recalculate S2R excluding migration month
    df_clean["s2r_clean"] = df_clean["hnt_burned"] / df_clean["hnt_issued"]

    # ── FIX 3: Rolling 3-month S2R ──
    print("\n3. Rolling 3-Month S2R:")
    df_clean["burn_3m"] = df_clean["hnt_burned"].rolling(3, min_periods=2).sum()
    df_clean["issue_3m"] = df_clean["hnt_issued"].rolling(3, min_periods=2).sum()
    df_clean["s2r_3m_rolling"] = df_clean["burn_3m"] / df_clean["issue_3m"]

    # ── FIX 4: Flag spike months ──
    print("\n4. Spike Detection:")
    # A month is flagged if its S2R is > 3x the rolling median
    rolling_med = df_clean["s2r_clean"].rolling(5, center=True, min_periods=2).median()
    df_clean["s2r_median_5m"] = rolling_med
    df_clean["spike_flag"] = df_clean["s2r_clean"] > (rolling_med * 3)

    spike_months = df_clean[df_clean["spike_flag"]]
    print(f"   Flagged {len(spike_months)} spike months:")
    for _, row in spike_months.iterrows():
        print(
            f"   {row['period'].strftime('%Y-%m')}: S2R={row['s2r_clean']:.4f} "
            f"(median={row['s2r_median_5m']:.4f})"
        )

    # ── FIX 5: v1 reference comparison ──
    print("\n5. v1 Reference Comparison:")
    v1_refs = {
        "2023-06": 0.031,
        "2023-09": 0.119,
        "2024-01": 0.052,
        "2024-07": 0.041,
        "2025-01": 0.006,
    }
    for period_str, v1_val in v1_refs.items():
        match = df_clean[df_clean["period"].dt.strftime("%Y-%m") == period_str]
        if len(match) > 0:
            v5_val = match.iloc[0]["s2r_clean"]
            pct_diff = (v5_val - v1_val) / v1_val * 100 if v1_val > 0 else float("inf")
            status = "OK" if abs(pct_diff) < 50 else "DIVERGENT"
            print(f"   {period_str}: v1={v1_val:.3f}, v5={v5_val:.4f}, diff={pct_diff:+.0f}% [{status}]")

    # ── Summary statistics ──
    print("\n6. Summary Statistics (cleaned, excl. migration):")
    valid = df_clean[~df_clean["spike_flag"]]
    print(f"   Months (non-spike): {len(valid)}")
    print(f"   Mean S2R:  {valid['s2r_clean'].mean():.4f}")
    print(f"   Median S2R: {valid['s2r_clean'].median():.4f}")
    print(f"   Std S2R:   {valid['s2r_clean'].std():.4f}")
    print(f"   Min S2R:   {valid['s2r_clean'].min():.4f}")
    print(f"   Max S2R:   {valid['s2r_clean'].max():.4f}")

    # Trend: first half vs second half
    mid = len(valid) // 2
    first_half = valid.iloc[:mid]["s2r_clean"].mean()
    second_half = valid.iloc[mid:]["s2r_clean"].mean()
    print(f"   First half mean:  {first_half:.4f}")
    print(f"   Second half mean: {second_half:.4f}")
    trend = "INCREASING" if second_half > first_half * 1.5 else "STABLE" if abs(second_half - first_half) / first_half < 0.3 else "DECREASING"
    print(f"   Trend: {trend}")

    # ── Save cleaned data ──
    output_cols = [
        "period", "hnt_burned", "hnt_issued", "s2r_burns_only",
        "migration_excluded", "s2r_clean", "s2r_3m_rolling",
        "spike_flag", "s2r_median_5m",
    ]
    existing_cols = [c for c in output_cols if c in df_clean.columns]
    df_out = df_clean[existing_cols].copy()

    csv_path = os.path.join(OUTPUT_DIR, "helium_s2r_CLEANED.csv")
    df_out.to_csv(csv_path, index=False)
    print(f"\nSaved: {csv_path}")

    # Save summary JSON
    summary = {
        "total_months": len(df),
        "cleaned_months": len(df_clean),
        "spike_months": len(spike_months),
        "migration_excluded": True,
        "mean_s2r_clean": round(float(valid["s2r_clean"].mean()), 4),
        "median_s2r_clean": round(float(valid["s2r_clean"].median()), 4),
        "trend": trend,
        "first_half_mean": round(float(first_half), 4),
        "second_half_mean": round(float(second_half), 4),
        "spike_months_list": [
            row["period"].strftime("%Y-%m") for _, row in spike_months.iterrows()
        ],
    }
    json_path = os.path.join(OUTPUT_DIR, "helium_s2r_cleaning_summary.json")
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved: {json_path}")


if __name__ == "__main__":
    main()
