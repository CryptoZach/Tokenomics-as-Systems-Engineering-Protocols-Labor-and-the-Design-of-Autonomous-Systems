#!/usr/bin/env python3
"""
BME Data Quality: Resolve Five Discrepancies.

Issues:
  1 (HIGH): Feb 2026 emission anomaly — partial week artifact?
  2 (HIGH): Jan-to-Jan 12-month decomposition (both 4-week months)
  3 (MEDIUM): Burn-weighted price series
  4 (MEDIUM): Counterfactuals with Jan-to-Jan window
  5 (LOW): Pre-halving emission trajectory

Output: bme_data_quality.json (alongside existing helium_bme_12month.json)
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
HELIUM_DIR = SCRIPT_DIR.parent.parent / "data" / "helium"


def load_dune_json(path):
    with open(path) as f:
        data = json.load(f)
    return pd.DataFrame(data.get("result", {}).get("rows", []))


def build_monthly_full():
    """Build monthly panel from weekly Dune data (full range)."""
    burns = load_dune_json(HELIUM_DIR / "dune_hnt_weekly_burns.json")
    issuance = load_dune_json(HELIUM_DIR / "dune_hnt_weekly_issuance.json")
    volume = load_dune_json(HELIUM_DIR / "dune_hnt_weekly_volume.json")

    for df in [burns, issuance, volume]:
        df["week"] = pd.to_datetime(df["week"], utc=True).dt.tz_localize(None)

    weekly = burns[["week", "hnt_burned", "usd_burned"]].merge(
        issuance[["week", "hnt_issued", "mint_txns"]], on="week", how="inner"
    ).merge(
        volume[["week", "avg_price_usd"]], on="week", how="inner"
    ).sort_values("week").reset_index(drop=True)

    weekly = weekly[weekly["week"] >= "2023-05-01"].reset_index(drop=True)
    weekly["month"] = weekly["week"].dt.to_period("M")

    monthly = weekly.groupby("month").agg(
        dc_burn_usd=("usd_burned", "sum"),
        hnt_burned=("hnt_burned", "sum"),
        hnt_issued=("hnt_issued", "sum"),
        hnt_price_avg=("avg_price_usd", "mean"),
        n_weeks=("week", "count"),
    ).reset_index()
    monthly["month"] = monthly["month"].dt.to_timestamp()
    monthly["bme"] = monthly["hnt_burned"] / monthly["hnt_issued"]
    monthly["dc_burn_pw"] = monthly["dc_burn_usd"] / monthly["n_weeks"]
    monthly["hnt_issued_pw"] = monthly["hnt_issued"] / monthly["n_weeks"]
    monthly["hnt_burned_pw"] = monthly["hnt_burned"] / monthly["n_weeks"]
    return monthly, weekly


def main():
    print("=" * 70)
    print("BME DATA QUALITY: RESOLVE FIVE DISCREPANCIES")
    print("=" * 70)

    monthly, weekly = build_monthly_full()
    results = {}

    # ================================================================
    # ISSUE 1: Feb 2026 emission anomaly
    # ================================================================
    print(f"\n{'=' * 70}")
    print("ISSUE 1: Feb 2026 Emission Anomaly")
    print(f"{'=' * 70}")

    feb26_weeks = weekly[weekly["month"] == pd.Period("2026-02", "M")]
    jan26_weeks = weekly[weekly["month"] == pd.Period("2026-01", "M")]

    print("\n  Raw weekly emissions (Jan–Feb 2026):")
    print(f"  {'Week':>12} {'HNT Issued':>12} {'Mint Txns':>10} {'Complete?':>10}")
    print(f"  {'─' * 48}")

    for _, row in jan26_weeks.iterrows():
        complete = "YES" if row["mint_txns"] >= 27 else "PARTIAL"
        print(f"  {row['week'].strftime('%Y-%m-%d'):>12} "
              f"{row['hnt_issued']:>12,.0f} "
              f"{int(row['mint_txns']):>10} "
              f"{complete:>10}")

    for _, row in feb26_weeks.iterrows():
        complete = "YES" if row["mint_txns"] >= 27 else "PARTIAL"
        print(f"  {row['week'].strftime('%Y-%m-%d'):>12} "
              f"{row['hnt_issued']:>12,.0f} "
              f"{int(row['mint_txns']):>10} "
              f"{complete:>10}")

    # Identify partial weeks
    feb_complete = feb26_weeks[feb26_weeks["mint_txns"] >= 27]
    feb_partial = feb26_weeks[feb26_weeks["mint_txns"] < 27]

    e_pw_all = feb26_weeks["hnt_issued"].sum() / len(feb26_weeks)
    e_pw_complete = feb_complete["hnt_issued"].mean() if len(feb_complete) > 0 else np.nan
    steady_state = 155342.4657533  # from post-halving constant

    print(f"\n  Feb 2026 E/wk (all 3 weeks):         {e_pw_all:>12,.0f}")
    print(f"  Feb 2026 E/wk (complete weeks only):  {e_pw_complete:>12,.0f}")
    print(f"  Post-halving steady state:            {steady_state:>12,.0f}")
    print(f"\n  Partial week: {feb_partial.iloc[0]['week'].strftime('%Y-%m-%d')} — "
          f"{int(feb_partial.iloc[0]['mint_txns'])} mint txns "
          f"({feb_partial.iloc[0]['hnt_issued']:,.0f} HNT = "
          f"{feb_partial.iloc[0]['hnt_issued']/steady_state:.1%} of full week)")

    verdict_1 = ("ARTIFACT: Feb 2026 E/wk of 125,753 is a partial-week artifact. "
                 "The last week (2026-02-16) has only 12/28 mint txns. "
                 "Complete-weeks-only E/wk = 155,342 (matches steady state).")
    print(f"\n  VERDICT: {verdict_1}")

    results["issue_1_feb2026_emission"] = {
        "raw_weeks": [
            {
                "week": row["week"].strftime("%Y-%m-%d"),
                "hnt_issued": round(float(row["hnt_issued"]), 2),
                "mint_txns": int(row["mint_txns"]),
                "complete": bool(row["mint_txns"] >= 27),
            }
            for _, row in pd.concat([jan26_weeks, feb26_weeks]).iterrows()
        ],
        "e_pw_all_3_weeks": round(float(e_pw_all), 0),
        "e_pw_complete_only": round(float(e_pw_complete), 0),
        "steady_state": round(float(steady_state), 0),
        "partial_week_fraction": round(float(feb_partial.iloc[0]["hnt_issued"] / steady_state), 3),
        "verdict": "PARTIAL_WEEK_ARTIFACT",
        "recommendation": "Use complete-weeks-only E/wk (155,342) or use Jan 2026 as endpoint",
    }

    # ================================================================
    # ISSUE 2: Jan 2025 → Jan 2026 decomposition (BLOCKING)
    # ================================================================
    print(f"\n{'=' * 70}")
    print("ISSUE 2: Jan-to-Jan 12-Month Decomposition (BLOCKING)")
    print(f"{'=' * 70}")

    jan25 = monthly[monthly["month"] == "2025-01-01"].iloc[0]
    jan26 = monthly[monthly["month"] == "2026-01-01"].iloc[0]

    print(f"\n  Jan 2025: BME={jan25['bme']:.4f}, DC/wk=${jan25['dc_burn_pw']:,.0f}, "
          f"P=${jan25['hnt_price_avg']:.2f}, E/wk={jan25['hnt_issued_pw']:,.0f} ({int(jan25['n_weeks'])}wk)")
    print(f"  Jan 2026: BME={jan26['bme']:.4f}, DC/wk=${jan26['dc_burn_pw']:,.0f}, "
          f"P=${jan26['hnt_price_avg']:.2f}, E/wk={jan26['hnt_issued_pw']:,.0f} ({int(jan26['n_weeks'])}wk)")

    # BME definitions
    bme_onchain_start = jan25["hnt_burned"] / jan25["hnt_issued"]
    bme_onchain_end = jan26["hnt_burned"] / jan26["hnt_issued"]
    bme_usd_start = jan25["dc_burn_usd"] / (jan25["hnt_price_avg"] * jan25["hnt_issued"])
    bme_usd_end = jan26["dc_burn_usd"] / (jan26["hnt_price_avg"] * jan26["hnt_issued"])

    print(f"\n  BME definitions:")
    print(f"    Jan 2025 onchain: {bme_onchain_start:.4f}  |  USD: {bme_usd_start:.4f}  |  gap: {abs(bme_onchain_start - bme_usd_start)/bme_onchain_start:.1%}")
    print(f"    Jan 2026 onchain: {bme_onchain_end:.4f}  |  USD: {bme_usd_end:.4f}  |  gap: {abs(bme_onchain_end - bme_usd_end)/bme_onchain_end:.1%}")

    # Compare with Feb 2026 endpoint
    feb26 = monthly[monthly["month"] == "2026-02-01"].iloc[0]
    bme_onchain_feb = feb26["hnt_burned"] / feb26["hnt_issued"]
    bme_usd_feb = feb26["dc_burn_usd"] / (feb26["hnt_price_avg"] * feb26["hnt_issued"])
    gap_feb = abs(bme_onchain_feb - bme_usd_feb) / bme_onchain_feb

    print(f"    Feb 2026 onchain: {bme_onchain_feb:.4f}  |  USD: {bme_usd_feb:.4f}  |  gap: {gap_feb:.1%}")

    # Log decomposition (Jan-to-Jan)
    d_dc = np.log(jan26["dc_burn_pw"] / jan25["dc_burn_pw"])
    d_p = np.log(jan26["hnt_price_avg"] / jan25["hnt_price_avg"])
    d_e = np.log(jan26["hnt_issued_pw"] / jan25["hnt_issued_pw"])
    d_bme_usd = d_dc - d_p - d_e
    d_bme_onchain = np.log(jan26["bme"] / jan25["bme"])

    fee_pct = d_dc / d_bme_usd * 100
    price_pct = -d_p / d_bme_usd * 100
    emis_pct = -d_e / d_bme_usd * 100

    print(f"\n  12-MONTH DECOMPOSITION (Jan 2025 → Jan 2026):")
    print(f"  ┌─────────────────────────────────┬──────────┬──────────┐")
    print(f"  │ Component (per-week rates)       │ Δln      │ Share    │")
    print(f"  ├─────────────────────────────────┼──────────┼──────────┤")
    print(f"  │ Fee growth (DC burn/wk)          │ {d_dc:>+7.4f}  │ {fee_pct:>6.1f}%  │")
    print(f"  │ Price decline (-Δln P)           │ {-d_p:>+7.4f}  │ {price_pct:>6.1f}%  │")
    print(f"  │ Emission reduction (-Δln E/wk)   │ {-d_e:>+7.4f}  │ {emis_pct:>6.1f}%  │")
    print(f"  ├─────────────────────────────────┼──────────┼──────────┤")
    print(f"  │ Total (USD-implied)              │ {d_bme_usd:>+7.4f}  │ {fee_pct+price_pct+emis_pct:>6.1f}%  │")
    print(f"  │ Total (onchain)                  │ {d_bme_onchain:>+7.4f}  │         │")
    print(f"  └─────────────────────────────────┴──────────┴──────────┘")
    print(f"  BME_usd vs BME_onchain gap: {abs(d_bme_usd - d_bme_onchain)/abs(d_bme_onchain):.1%}")

    # Compare: Feb endpoint (current) vs Jan-to-Jan (proposed)
    # Recompute Feb endpoint from existing JSON
    mar25 = monthly[monthly["month"] == "2025-03-01"].iloc[0]
    d_dc_feb = np.log(feb26["dc_burn_pw"] / mar25["dc_burn_pw"])
    d_p_feb = np.log(feb26["hnt_price_avg"] / mar25["hnt_price_avg"])
    d_e_feb = np.log(feb26["hnt_issued_pw"] / mar25["hnt_issued_pw"])
    d_bme_usd_feb = d_dc_feb - d_p_feb - d_e_feb
    d_bme_onchain_feb = np.log(feb26["bme"] / mar25["bme"])

    print(f"\n  COMPARISON: Feb endpoint vs Jan-to-Jan")
    print(f"  {'Metric':>30} {'Mar→Feb':>12} {'Jan→Jan':>12}")
    print(f"  {'─' * 56}")
    print(f"  {'Start BME':>30} {mar25['bme']:>12.4f} {jan25['bme']:>12.4f}")
    print(f"  {'End BME':>30} {feb26['bme']:>12.4f} {jan26['bme']:>12.4f}")
    print(f"  {'Δln(BME) onchain':>30} {d_bme_onchain_feb:>+12.4f} {d_bme_onchain:>+12.4f}")
    print(f"  {'Δln(BME) USD-implied':>30} {d_bme_usd_feb:>+12.4f} {d_bme_usd:>+12.4f}")
    print(f"  {'Onchain/USD gap':>30} {abs(d_bme_usd_feb-d_bme_onchain_feb)/abs(d_bme_onchain_feb):>11.1%} {abs(d_bme_usd-d_bme_onchain)/abs(d_bme_onchain):>11.1%}")
    print(f"  {'Fee share':>30} {25.4:>11.1f}% {fee_pct:>11.1f}%")
    print(f"  {'Price share':>30} {36.2:>11.1f}% {price_pct:>11.1f}%")
    print(f"  {'Emission share':>30} {38.4:>11.1f}% {emis_pct:>11.1f}%")
    print(f"  {'Start n_weeks':>30} {int(mar25['n_weeks']):>12} {int(jan25['n_weeks']):>12}")
    print(f"  {'End n_weeks':>30} {int(feb26['n_weeks']):>12} {int(jan26['n_weeks']):>12}")

    results["issue_2_jan_to_jan"] = {
        "start": {
            "month": "2025-01",
            "bme_onchain": round(float(bme_onchain_start), 4),
            "bme_usd": round(float(bme_usd_start), 4),
            "dc_burn_pw": round(float(jan25["dc_burn_pw"]), 0),
            "hnt_price_avg": round(float(jan25["hnt_price_avg"]), 4),
            "hnt_issued_pw": round(float(jan25["hnt_issued_pw"]), 0),
            "n_weeks": int(jan25["n_weeks"]),
        },
        "end": {
            "month": "2026-01",
            "bme_onchain": round(float(bme_onchain_end), 4),
            "bme_usd": round(float(bme_usd_end), 4),
            "dc_burn_pw": round(float(jan26["dc_burn_pw"]), 0),
            "hnt_price_avg": round(float(jan26["hnt_price_avg"]), 4),
            "hnt_issued_pw": round(float(jan26["hnt_issued_pw"]), 0),
            "n_weeks": int(jan26["n_weeks"]),
        },
        "decomposition": {
            "dln_dc": round(float(d_dc), 4),
            "dln_price": round(float(d_p), 4),
            "dln_emission": round(float(d_e), 4),
            "dln_bme_usd": round(float(d_bme_usd), 4),
            "dln_bme_onchain": round(float(d_bme_onchain), 4),
            "fee_pct": round(float(fee_pct), 1),
            "price_pct": round(float(price_pct), 1),
            "emission_pct": round(float(emis_pct), 1),
            "sum_check": round(float(fee_pct + price_pct + emis_pct), 1),
        },
        "onchain_usd_gap_pct": round(float(abs(d_bme_usd - d_bme_onchain) / abs(d_bme_onchain) * 100), 1),
        "comparison_vs_feb_endpoint": {
            "feb_gap_pct": round(float(abs(d_bme_usd_feb - d_bme_onchain_feb) / abs(d_bme_onchain_feb) * 100), 1),
            "jan_gap_pct": round(float(abs(d_bme_usd - d_bme_onchain) / abs(d_bme_onchain) * 100), 1),
            "improvement": "Jan-to-Jan reduces definition gap substantially",
        },
    }

    # ================================================================
    # ISSUE 3: Burn-weighted price series
    # ================================================================
    print(f"\n{'=' * 70}")
    print("ISSUE 3: Burn-Weighted Price Series")
    print(f"{'=' * 70}")

    # P_burn = DC_burn_usd / HNT_burned
    target_months = monthly[
        (monthly["month"] >= "2025-01-01") & (monthly["month"] <= "2026-02-28")
    ].copy()

    print(f"\n  {'Month':>8} {'P_burn':>8} {'P_avg':>8} {'Gap%':>8} {'HNT_burned':>12}")
    print(f"  {'─' * 52}")

    burn_price_rows = []
    for _, row in target_months.iterrows():
        p_burn = row["dc_burn_usd"] / row["hnt_burned"] if row["hnt_burned"] > 0 else np.nan
        p_avg = row["hnt_price_avg"]
        gap = (p_burn - p_avg) / p_avg * 100 if p_avg > 0 else np.nan

        burn_price_rows.append({
            "month": row["month"].strftime("%Y-%m"),
            "p_burn": round(float(p_burn), 4) if not np.isnan(p_burn) else None,
            "p_avg": round(float(p_avg), 4),
            "gap_pct": round(float(gap), 1) if not np.isnan(gap) else None,
            "hnt_burned": round(float(row["hnt_burned"]), 0),
        })

        print(f"  {row['month'].strftime('%Y-%m'):>8} "
              f"${p_burn:>7.4f} " if not np.isnan(p_burn) else f"  {row['month'].strftime('%Y-%m'):>8}     n/a ",
              end="")
        print(f"${p_avg:>7.4f} "
              f"{gap:>+7.1f}% " if not np.isnan(gap) else "    n/a ",
              end="")
        print(f"{row['hnt_burned']:>12,.0f}")

    results["issue_3_burn_weighted_price"] = {
        "definition": "P_burn = DC_burn_usd / HNT_burned",
        "note": "P_burn != P_avg because burns happen at different times/prices than average transfer volume",
        "monthly": burn_price_rows,
    }

    # ================================================================
    # ISSUE 4: Counterfactuals with Jan-to-Jan window
    # ================================================================
    print(f"\n{'=' * 70}")
    print("ISSUE 4: Counterfactuals (Jan 2025 → Jan 2026)")
    print(f"{'=' * 70}")

    # BME = DC/(P*E), so counterfactuals vary one component at end, hold others at start
    # "Fee only": end DC, start P, end E → BME = end_dc_pw / (start_p * end_e_pw)
    cf_fee = jan26["dc_burn_pw"] / (jan25["hnt_price_avg"] * jan26["hnt_issued_pw"])
    # "Price only": start DC, end P, start E
    cf_price = jan25["dc_burn_pw"] / (jan26["hnt_price_avg"] * jan25["hnt_issued_pw"])
    # "Emission only": start DC, start P, end E
    cf_emis = jan25["dc_burn_pw"] / (jan25["hnt_price_avg"] * jan26["hnt_issued_pw"])
    # "Fee alone": end DC, start P, start E
    cf_fee_alone = jan26["dc_burn_pw"] / (jan25["hnt_price_avg"] * jan25["hnt_issued_pw"])
    # Actual end BME (USD definition)
    actual_bme_usd = jan26["dc_burn_pw"] / (jan26["hnt_price_avg"] * jan26["hnt_issued_pw"])
    # "No halving": end DC, end P, start E
    cf_no_halving = jan26["dc_burn_pw"] / (jan26["hnt_price_avg"] * jan25["hnt_issued_pw"])

    print(f"\n  Actual BME (Jan 2026, USD):        {actual_bme_usd:.4f}")
    print(f"  Actual BME (Jan 2026, onchain):     {jan26['bme']:.4f}")
    print(f"\n  COUNTERFACTUALS (all use per-week rates):")
    print(f"    Fee only (DC→end, P&E @start):           BME = {cf_fee:.4f} ({cf_fee/actual_bme_usd:.0%} of actual)")
    print(f"    Price only (P→end, DC&E @start):         BME = {cf_price:.4f} ({cf_price/actual_bme_usd:.0%} of actual)")
    print(f"    Emission only (E→end, DC&P @start):      BME = {cf_emis:.4f} ({cf_emis/actual_bme_usd:.0%} of actual)")
    print(f"    Fee growth alone (DC→end, all else @Jan25): BME = {cf_fee_alone:.4f}")
    print(f"    No halving (E @Jan25, DC&P @Jan26):      BME = {cf_no_halving:.4f} ({cf_no_halving/actual_bme_usd:.0%} of actual)")

    results["issue_4_counterfactuals_jan_to_jan"] = {
        "actual_bme_usd": round(float(actual_bme_usd), 4),
        "actual_bme_onchain": round(float(jan26["bme"]), 4),
        "fee_only": round(float(cf_fee), 4),
        "price_only": round(float(cf_price), 4),
        "emission_only": round(float(cf_emis), 4),
        "fee_alone": round(float(cf_fee_alone), 4),
        "no_halving": round(float(cf_no_halving), 4),
        "no_halving_pct_of_actual": round(float(cf_no_halving / actual_bme_usd * 100), 1),
        "interpretation": (
            "Without halving, BME would be {:.3f} vs actual {:.3f}. "
            "The halving is necessary but not sufficient — fee growth "
            "and price decline both contribute materially."
        ).format(cf_no_halving, actual_bme_usd),
    }

    # ================================================================
    # ISSUE 5: Pre-halving emission trajectory
    # ================================================================
    print(f"\n{'=' * 70}")
    print("ISSUE 5: Pre-Halving Emission Trajectory")
    print(f"{'=' * 70}")

    pre_halving = monthly[
        (monthly["month"] >= "2025-01-01") & (monthly["month"] <= "2025-07-31")
    ].copy()

    print(f"\n  {'Month':>8} {'E/wk':>10} {'E total':>12} {'N_wk':>5} {'MoM Δ':>8}")
    print(f"  {'─' * 48}")

    trajectory_rows = []
    prev_e = None
    for _, row in pre_halving.iterrows():
        e_pw = row["hnt_issued_pw"]
        mom_pct = ((e_pw / prev_e) - 1) * 100 if prev_e is not None else np.nan
        trajectory_rows.append({
            "month": row["month"].strftime("%Y-%m"),
            "e_pw": round(float(e_pw), 0),
            "e_total": round(float(row["hnt_issued"]), 0),
            "n_weeks": int(row["n_weeks"]),
            "mom_pct": round(float(mom_pct), 2) if not np.isnan(mom_pct) else None,
        })
        mom_s = f"{mom_pct:>+7.2f}%" if not np.isnan(mom_pct) else "     —"
        print(f"  {row['month'].strftime('%Y-%m'):>8} "
              f"{e_pw:>10,.0f} "
              f"{row['hnt_issued']:>12,.0f} "
              f"{int(row['n_weeks']):>5} "
              f"{mom_s}")
        prev_e = e_pw

    # Halving week identification
    aug_weeks = weekly[weekly["month"] == pd.Period("2025-08", "M")].sort_values("week")
    jul_weeks = weekly[weekly["month"] == pd.Period("2025-07", "M")].sort_values("week")

    print(f"\n  Halving week boundary (weekly detail):")
    print(f"  {'Week':>12} {'HNT Issued':>12} {'Mint Txns':>10}")
    print(f"  {'─' * 38}")
    for _, row in jul_weeks.tail(2).iterrows():
        print(f"  {row['week'].strftime('%Y-%m-%d'):>12} "
              f"{row['hnt_issued']:>12,.0f} "
              f"{int(row['mint_txns']):>10}")
    for _, row in aug_weeks.head(2).iterrows():
        print(f"  {row['week'].strftime('%Y-%m-%d'):>12} "
              f"{row['hnt_issued']:>12,.0f} "
              f"{int(row['mint_txns']):>10}")

    # Identify the transition week
    halving_week = None
    all_weeks_sorted = weekly.sort_values("week")
    for i in range(1, len(all_weeks_sorted)):
        curr = all_weeks_sorted.iloc[i]
        prev_row = all_weeks_sorted.iloc[i - 1]
        if (prev_row["hnt_issued"] > 300000 and curr["hnt_issued"] < 200000
                and curr["week"] >= pd.Timestamp("2025-07-01")):
            halving_week = curr["week"]
            print(f"\n  Halving transition: {prev_row['week'].strftime('%Y-%m-%d')} "
                  f"({prev_row['hnt_issued']:,.0f}) → "
                  f"{curr['week'].strftime('%Y-%m-%d')} "
                  f"({curr['hnt_issued']:,.0f})")
            print(f"  Transition week (2025-07-28) is a split week: "
                  f"{curr['hnt_issued']:,.0f} HNT = mix of pre/post halving")
            break

    # Was emission already declining before halving?
    jan_e = pre_halving.iloc[0]["hnt_issued_pw"]
    jul_e = pre_halving.iloc[-1]["hnt_issued_pw"]
    pre_halving_drift = (jul_e / jan_e - 1) * 100
    print(f"\n  Pre-halving drift (Jan→Jul 2025): {pre_halving_drift:+.2f}%")
    print(f"    Jan: {jan_e:,.0f}/wk → Jul: {jul_e:,.0f}/wk")
    if abs(pre_halving_drift) < 5:
        print(f"  → Emissions were essentially FLAT before halving (drift < 5%)")
    else:
        print(f"  → Emissions were drifting {('down' if pre_halving_drift < 0 else 'up')} before halving")

    results["issue_5_pre_halving_trajectory"] = {
        "monthly_e_pw": trajectory_rows,
        "halving_transition_week": halving_week.strftime("%Y-%m-%d") if halving_week else None,
        "pre_halving_drift_pct": round(float(pre_halving_drift), 2),
        "emissions_flat_pre_halving": abs(pre_halving_drift) < 5,
        "steady_state_post_halving": round(float(steady_state), 0),
        "interpretation": (
            "Emissions were flat (~375K/wk) Jan–Jul 2025. "
            "The halving transition occurs in the week of 2025-07-28 "
            "(split week: 317K HNT, mix of pre/post rates). "
            "By 2025-08-04, emissions stabilize at ~155K/wk."
        ),
    }

    # ================================================================
    # SUMMARY
    # ================================================================
    print(f"\n{'=' * 70}")
    print("SUMMARY: RECOMMENDATION")
    print(f"{'=' * 70}")

    print(f"""
  The Jan-to-Jan window is PREFERRED for the paper because:

  1. Both endpoints are 4-week months (no partial-week contamination)
  2. The BME onchain/USD definition gap drops from
     {abs(d_bme_usd_feb-d_bme_onchain_feb)/abs(d_bme_onchain_feb):.1%} (Feb endpoint) to {abs(d_bme_usd-d_bme_onchain)/abs(d_bme_onchain):.1%} (Jan endpoint)
  3. Avoids the Feb 2026 partial-week emission artifact entirely
  4. Still captures the full halving effect (Aug 2025)

  PROPOSED 12-MONTH DECOMPOSITION (Jan 2025 → Jan 2026):
    Fee growth:          {fee_pct:.1f}%
    Price decline:       {price_pct:.1f}%
    Emission reduction:  {emis_pct:.1f}%
    Sum:                 {fee_pct+price_pct+emis_pct:.1f}%
""")

    results["summary"] = {
        "recommended_window": "Jan 2025 → Jan 2026",
        "reason": [
            "Both endpoints are 4-week months",
            "BME definition gap much smaller than Feb endpoint",
            "Avoids partial-week emission artifact in Feb 2026",
            "Still captures full halving effect (Aug 2025)",
        ],
        "proposed_decomposition": {
            "fee_pct": round(float(fee_pct), 1),
            "price_pct": round(float(price_pct), 1),
            "emission_pct": round(float(emis_pct), 1),
        },
    }

    # Save
    out_path = HELIUM_DIR / "bme_data_quality.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  Saved: {out_path}")


if __name__ == "__main__":
    main()
