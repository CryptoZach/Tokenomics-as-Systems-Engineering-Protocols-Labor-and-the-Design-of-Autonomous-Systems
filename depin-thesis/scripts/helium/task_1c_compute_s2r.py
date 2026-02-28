#!/usr/bin/env python3
"""
Task 1c: Merge Dune burn + issuance data into continuous S2R series.
Run AFTER Task 1b produces dune_hnt_weekly_burns.json and dune_hnt_weekly_issuance.json.
"""
import json
import pandas as pd
import numpy as np
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_dune_rows(filename):
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        data = json.load(f)
    rows = data.get("result", {}).get("rows", data if isinstance(data, list) else [])
    if rows:
        return pd.DataFrame(rows)
    return None


def build_from_known_points():
    """Fallback: sparse S2R from secondary sources."""
    print("Building S2R series from known reference points (fallback)...")
    known = pd.DataFrame([
        {"month": "2022-06", "s2r_burns_only": 0.007, "source": "Evidence Pack", "note": "$6.5k/mo revenue"},
        {"month": "2022-12", "s2r_burns_only": 0.01,  "source": "Deep Research", "note": "Low IoT usage"},
        {"month": "2023-03", "s2r_burns_only": 0.10,  "source": "Deep Research", "note": "Post-Solana migration"},
        {"month": "2023-09", "s2r_burns_only": 0.30,  "source": "Deep Research", "note": "5G Mobile launch"},
        {"month": "2024-06", "s2r_burns_only": 0.35,  "source": "Interpolated", "note": "~$600k/mo revenue"},
        {"month": "2025-03", "s2r_burns_only": 0.40,  "source": "Interpolated", "note": "Pre full-burn"},
        {"month": "2025-08", "s2r_burns_only": 0.60,  "source": "Deep Research", "note": "Full carrier burn"},
        {"month": "2025-09", "s2r_burns_only": 0.99,  "source": "Messari Q3", "note": "615k issued, ~600k burned"},
        {"month": "2025-10", "s2r_burns_only": 0.52,  "source": "Deep Research", "note": "Burn stabilized ~$30k/day"},
    ])
    known.to_csv(os.path.join(OUTPUT_DIR, "helium_s2r_timeseries.csv"), index=False)
    print(f"  Saved {len(known)} known data points (sparse series)")
    return known


def main():
    burns = load_dune_rows("dune_hnt_weekly_burns.json")
    issuance = load_dune_rows("dune_hnt_weekly_issuance.json")

    if burns is None or issuance is None:
        print("Dune data not available. Using fallback.")
        if burns is None:
            print("  Missing: dune_hnt_weekly_burns.json")
        if issuance is None:
            print("  Missing: dune_hnt_weekly_issuance.json")
        return build_from_known_points()

    print("=== Merging Dune burn + issuance data ===")

    # Standardize column names
    burns.columns = [c.strip().lower() for c in burns.columns]
    issuance.columns = [c.strip().lower() for c in issuance.columns]

    # Parse dates
    for df, name in [(burns, "burns"), (issuance, "issuance")]:
        date_col = None
        for col in df.columns:
            if 'week' in col or 'month' in col or 'date' in col:
                date_col = col
                break
        if date_col:
            df['period'] = pd.to_datetime(df[date_col])
            print(f"  {name}: using '{date_col}' as date column, {len(df)} rows")
        else:
            print(f"  {name}: no date column found! Columns: {df.columns.tolist()}")
            return build_from_known_points()

    # Find burn and issuance value columns
    burn_col = [c for c in burns.columns if 'burn' in c and 'txn' not in c and c != 'period']
    issue_col = [c for c in issuance.columns if 'issue' in c and 'txn' not in c and c != 'period']

    if not burn_col:
        burn_col = [c for c in burns.columns if c not in ('period', 'week', 'burn_txns')]
    if not issue_col:
        issue_col = [c for c in issuance.columns if c not in ('period', 'week', 'reward_txns')]

    if not burn_col or not issue_col:
        print(f"  Cannot identify columns. Burns: {burns.columns.tolist()}, Issuance: {issuance.columns.tolist()}")
        return build_from_known_points()

    print(f"  Using burn column: {burn_col[0]}, issuance column: {issue_col[0]}")

    burns_series = burns[['period', burn_col[0]]].set_index('period').rename(columns={burn_col[0]: 'hnt_burned'})
    issue_series = issuance[['period', issue_col[0]]].set_index('period').rename(columns={issue_col[0]: 'hnt_issued'})

    merged = burns_series.join(issue_series, how='outer').fillna(0)

    # Monthly aggregation
    monthly = merged.resample('ME').sum()
    monthly['s2r_burns_only'] = np.where(
        monthly['hnt_issued'] > 0,
        (monthly['hnt_burned'] / monthly['hnt_issued']).round(4),
        0
    )
    monthly['s2r_burns_only'] = monthly['s2r_burns_only'].clip(0, 5)  # Cap outliers

    monthly.to_csv(os.path.join(OUTPUT_DIR, "helium_s2r_continuous.csv"))
    print(f"\nSaved continuous S2R: {len(monthly)} monthly observations")
    print(f"Period: {monthly.index[0].date()} to {monthly.index[-1].date()}")
    print(f"S2R range: {monthly['s2r_burns_only'].min():.4f} - {monthly['s2r_burns_only'].max():.4f}")
    print(f"\nLast 6 months:")
    print(monthly.tail(6).to_string())

    # Upgraded measurement memo
    with open(os.path.join(OUTPUT_DIR, "s2r_measurement_memo_v2.md"), "w") as f:
        f.write("# S2R Measurement Memo v2 (On-Chain Data)\n\n")
        f.write("## Upgrade from v1\n")
        f.write("- v1: 9 sparse monthly observations from secondary reports\n")
        f.write(f"- v2: {len(monthly)} continuous monthly observations from Solana on-chain data\n")
        f.write("- Truth status upgraded: Estimate (Modeled) -> Finding (Empirical)\n\n")
        f.write("## Definition\n")
        f.write("S2R = (HNT burned via DC purchases) / (HNT issued as rewards)\n")
        f.write("Computed from Dune Analytics Solana tables.\n\n")
        f.write("## Method\n")
        f.write("- Burns: Negative HNT balance changes on Solana (DC mint program)\n")
        f.write("- Issuance: Positive HNT balance changes (reward distribution)\n")
        f.write("- Aggregation: Monthly sum of weekly data\n\n")
        f.write("## Exclusions (conservative baseline)\n")
        f.write("- veHNT locks excluded\n")
        f.write("- Nova Labs one-time buyback excluded\n")
        f.write("- Exchange deposits/withdrawals excluded (not sinks)\n\n")
        f.write("## Falsification\n")
        f.write("- S2R overstated if non-DC burns captured\n")
        f.write("- S2R understated if some DC burns happen off-chain or through proxies\n")
        f.write("- Cross-validate: compare monthly totals against Helium Foundation reports\n\n")
        f.write("## Replication\n")
        f.write("- Token mint: hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux\n")
        f.write("- Date range: April 2023 (Solana migration) to present\n")
        f.write("- Pre-Solana data (2020-2023): from v1 secondary sources\n")
    print("\nMeasurement memo v2 saved")
    return monthly


if __name__ == "__main__":
    main()
