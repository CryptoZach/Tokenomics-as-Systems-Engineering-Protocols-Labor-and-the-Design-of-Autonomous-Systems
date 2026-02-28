#!/usr/bin/env python3
"""
Helium BME Decomposition: Fee Growth vs Price Decline vs Emission Reduction.

Decomposes the BME improvement (0.013 → 2.06) into three components using
log-difference attribution:
  ln(BME) = ln(DC_USD) - ln(P) - ln(E)
  Δln(BME) = Δln(DC_USD) - Δln(P) - Δln(E)

Data: Dune Analytics weekly burns, issuance, and volume (149 weeks).
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
HELIUM_DIR = SCRIPT_DIR.parent.parent / "data" / "helium"
OUTPUT_DIR = HELIUM_DIR


def load_dune_json(path):
    """Parse Dune Analytics JSON response."""
    with open(path) as f:
        data = json.load(f)
    rows = data.get("result", {}).get("rows", [])
    return pd.DataFrame(rows)


def main():
    print("=" * 70)
    print("HELIUM BME DECOMPOSITION: Fee Growth vs Price Decline")
    print("=" * 70)

    # ── Load weekly data ─────────────────────────────────────────
    burns = load_dune_json(HELIUM_DIR / "dune_hnt_weekly_burns.json")
    issuance = load_dune_json(HELIUM_DIR / "dune_hnt_weekly_issuance.json")
    volume = load_dune_json(HELIUM_DIR / "dune_hnt_weekly_volume.json")

    for df, name in [(burns, "burns"), (issuance, "issuance"), (volume, "volume")]:
        df["week"] = pd.to_datetime(df["week"])
        print(f"  {name}: {len(df)} weeks, {df['week'].min().date()} to {df['week'].max().date()}")

    # ── Merge into weekly panel ──────────────────────────────────
    weekly = burns[["week", "hnt_burned", "usd_burned"]].merge(
        issuance[["week", "hnt_issued"]], on="week", how="inner"
    ).merge(
        volume[["week", "avg_price_usd"]], on="week", how="inner"
    ).sort_values("week").reset_index(drop=True)

    # Exclude the April 2023 migration week (massive one-time issuance)
    weekly = weekly[weekly["week"] >= "2023-05-01"].reset_index(drop=True)
    print(f"\n  Weekly panel: {len(weekly)} weeks (excl migration)")

    # ── Aggregate to monthly ─────────────────────────────────────
    weekly["month"] = weekly["week"].dt.to_period("M")
    monthly = weekly.groupby("month").agg(
        dc_burn_usd=("usd_burned", "sum"),
        hnt_burned=("hnt_burned", "sum"),
        hnt_issued=("hnt_issued", "sum"),
        hnt_price_avg=("avg_price_usd", "mean"),
        n_weeks=("week", "count"),
    ).reset_index()
    monthly["month"] = monthly["month"].dt.to_timestamp()

    # Compute BME = hnt_burned / hnt_issued
    monthly["bme"] = monthly["hnt_burned"] / monthly["hnt_issued"]

    # Cross-check: BME should also equal dc_burn_usd / (price * emission)
    monthly["bme_check"] = monthly["dc_burn_usd"] / (
        monthly["hnt_price_avg"] * monthly["hnt_issued"]
    )

    print(f"  Monthly panel: {len(monthly)} months")
    print(f"  Date range: {monthly['month'].iloc[0].strftime('%Y-%m')} to "
          f"{monthly['month'].iloc[-1].strftime('%Y-%m')}")

    # ── Print monthly summary ────────────────────────────────────
    print(f"\n  {'Month':>8} {'DC_USD':>12} {'Price':>8} {'Emission':>12} "
          f"{'BME':>8} {'BME_chk':>8}")
    print(f"  {'─' * 60}")
    for _, r in monthly.iterrows():
        print(f"  {r['month'].strftime('%Y-%m'):>8} "
              f"${r['dc_burn_usd']:>10,.0f} "
              f"${r['hnt_price_avg']:>6.2f} "
              f"{r['hnt_issued']:>11,.0f} "
              f"{r['bme']:>8.4f} "
              f"{r['bme_check']:>8.4f}")

    # ── Define anchor periods ────────────────────────────────────
    # Early: June-August 2023 (post-migration settling)
    early_mask = (monthly["month"] >= "2023-06-01") & (monthly["month"] <= "2023-08-31")
    # Late: October-December 2025 (recent stable period)
    late_mask = (monthly["month"] >= "2025-10-01") & (monthly["month"] <= "2025-12-31")

    early = monthly[early_mask]
    late = monthly[late_mask]

    print(f"\n  Early period ({early['month'].iloc[0].strftime('%Y-%m')} to "
          f"{early['month'].iloc[-1].strftime('%Y-%m')}): {len(early)} months")
    print(f"  Late period ({late['month'].iloc[0].strftime('%Y-%m')} to "
          f"{late['month'].iloc[-1].strftime('%Y-%m')}): {len(late)} months")

    # Period averages
    early_dc = early["dc_burn_usd"].mean()
    late_dc = late["dc_burn_usd"].mean()
    early_p = early["hnt_price_avg"].mean()
    late_p = late["hnt_price_avg"].mean()
    early_e = early["hnt_issued"].mean()
    late_e = late["hnt_issued"].mean()
    early_bme = early["bme"].mean()
    late_bme = late["bme"].mean()

    print(f"\n  Early averages:")
    print(f"    DC burn USD/mo:  ${early_dc:,.0f}")
    print(f"    HNT price:       ${early_p:.4f}")
    print(f"    HNT emission/mo: {early_e:,.0f}")
    print(f"    BME:             {early_bme:.4f}")
    print(f"\n  Late averages:")
    print(f"    DC burn USD/mo:  ${late_dc:,.0f}")
    print(f"    HNT price:       ${late_p:.4f}")
    print(f"    HNT emission/mo: {late_e:,.0f}")
    print(f"    BME:             {late_bme:.4f}")

    # ── Log-difference decomposition ─────────────────────────────
    print(f"\n{'=' * 70}")
    print("LOG-DIFFERENCE DECOMPOSITION")
    print(f"{'=' * 70}")

    delta_ln_bme = np.log(late_bme / early_bme)
    delta_ln_dc = np.log(late_dc / early_dc)
    delta_ln_p = np.log(late_p / early_p)
    delta_ln_e = np.log(late_e / early_e)

    # Δln(BME) = Δln(DC) - Δln(P) - Δln(E)
    # So: fee_contrib = Δln(DC), price_contrib = -Δln(P), emission_contrib = -Δln(E)
    fee_contrib = delta_ln_dc
    price_contrib = -delta_ln_p
    emission_contrib = -delta_ln_e

    # Shares (% of total Δln(BME))
    fee_share = fee_contrib / delta_ln_bme
    price_share = price_contrib / delta_ln_bme
    emission_share = emission_contrib / delta_ln_bme

    # Residual (interaction term)
    residual = delta_ln_bme - (fee_contrib + price_contrib + emission_contrib)

    print(f"\n  Δln(BME)      = {delta_ln_bme:+.4f}  (BME: {early_bme:.4f} → {late_bme:.4f})")
    print(f"  Δln(DC_USD)   = {delta_ln_dc:+.4f}  (${early_dc:,.0f} → ${late_dc:,.0f})")
    print(f"  Δln(Price)    = {delta_ln_p:+.4f}  (${early_p:.2f} → ${late_p:.2f})")
    print(f"  Δln(Emission) = {delta_ln_e:+.4f}  ({early_e:,.0f} → {late_e:,.0f})")
    print(f"  Residual      = {residual:+.6f}")

    print(f"\n  DECOMPOSITION:")
    print(f"  ┌─────────────────────────────────┬──────────┬──────────┐")
    print(f"  │ Component                        │ Δln      │ Share    │")
    print(f"  ├─────────────────────────────────┼──────────┼──────────┤")
    print(f"  │ Fee growth (DC burn USD)         │ {fee_contrib:>+7.4f}  │ {fee_share:>7.1%}  │")
    print(f"  │ Price decline (-Δln P)           │ {price_contrib:>+7.4f}  │ {price_share:>7.1%}  │")
    print(f"  │ Emission reduction (-Δln E)      │ {emission_contrib:>+7.4f}  │ {emission_share:>7.1%}  │")
    print(f"  ├─────────────────────────────────┼──────────┼──────────┤")
    print(f"  │ Total                            │ {delta_ln_bme:>+7.4f}  │ {fee_share + price_share + emission_share:>7.1%}  │")
    print(f"  └─────────────────────────────────┴──────────┴──────────┘")

    # ── Counterfactual BMEs ──────────────────────────────────────
    print(f"\n  COUNTERFACTUALS:")

    # Late fees, early price, late emissions
    cf_fee_only = (late_dc / early_p) / late_e
    print(f"  If price stayed at ${early_p:.2f} (late fees + late emissions):")
    print(f"    BME would be {cf_fee_only:.4f} vs actual {late_bme:.4f} "
          f"({cf_fee_only / late_bme:.0%} of actual)")

    # Early fees, late price, late emissions (price decline only)
    cf_price_only = (early_dc / late_p) / late_e
    print(f"  If fees stayed at ${early_dc:,.0f}/mo (late price + late emissions):")
    print(f"    BME would be {cf_price_only:.4f} vs actual {late_bme:.4f} "
          f"({cf_price_only / late_bme:.0%} of actual)")

    # Late fees, late price, early emissions (emission reduction only)
    cf_emission_only = (late_dc / late_p) / early_e
    print(f"  If emissions stayed at {early_e:,.0f}/mo (late fees + late price):")
    print(f"    BME would be {cf_emission_only:.4f} vs actual {late_bme:.4f} "
          f"({cf_emission_only / late_bme:.0%} of actual)")

    # Fee growth only (everything else held at early levels)
    cf_fee_growth_alone = (late_dc / early_p) / early_e
    print(f"  Fee growth alone (all else at early levels):")
    print(f"    BME would be {cf_fee_growth_alone:.4f} (from {early_bme:.4f})")

    # ── Alternative anchor: paper's stated endpoints ─────────────
    print(f"\n{'=' * 70}")
    print("PAPER ENDPOINT CROSS-CHECK (May 2023 and Feb 2026)")
    print(f"{'=' * 70}")

    may23 = monthly[monthly["month"] == "2023-05-01"]
    feb26 = monthly[monthly["month"] == "2026-02-01"]

    if len(may23) > 0 and len(feb26) > 0:
        m_dc = may23["dc_burn_usd"].iloc[0]
        m_p = may23["hnt_price_avg"].iloc[0]
        m_e = may23["hnt_issued"].iloc[0]
        m_bme = may23["bme"].iloc[0]

        f_dc = feb26["dc_burn_usd"].iloc[0]
        f_p = feb26["hnt_price_avg"].iloc[0]
        f_e = feb26["hnt_issued"].iloc[0]
        f_bme = feb26["bme"].iloc[0]

        d_bme2 = np.log(f_bme / m_bme)
        d_dc2 = np.log(f_dc / m_dc)
        d_p2 = np.log(f_p / m_p)
        d_e2 = np.log(f_e / m_e)

        print(f"  May 2023: BME={m_bme:.4f}, DC=${m_dc:,.0f}, P=${m_p:.2f}, E={m_e:,.0f}")
        print(f"  Feb 2026: BME={f_bme:.4f}, DC=${f_dc:,.0f}, P=${f_p:.2f}, E={f_e:,.0f}")
        print(f"\n  Fee growth:        {d_dc2 / d_bme2:>7.1%}")
        print(f"  Price decline:     {-d_p2 / d_bme2:>7.1%}")
        print(f"  Emission reduction:{-d_e2 / d_bme2:>7.1%}")

    # ── Save monthly CSV ─────────────────────────────────────────
    csv_path = OUTPUT_DIR / "helium_bme_monthly.csv"
    monthly_out = monthly.copy()
    monthly_out["month"] = monthly_out["month"].dt.strftime("%Y-%m")
    monthly_out.to_csv(csv_path, index=False)
    print(f"\n  Saved: {csv_path}")

    # ── Save JSON results ────────────────────────────────────────
    results = {
        "early_period": f"{early['month'].iloc[0].strftime('%Y-%m')} to {early['month'].iloc[-1].strftime('%Y-%m')}",
        "late_period": f"{late['month'].iloc[0].strftime('%Y-%m')} to {late['month'].iloc[-1].strftime('%Y-%m')}",
        "early_bme": round(float(early_bme), 4),
        "late_bme": round(float(late_bme), 4),
        "early_dc_usd_monthly": round(float(early_dc), 0),
        "late_dc_usd_monthly": round(float(late_dc), 0),
        "early_hnt_price": round(float(early_p), 4),
        "late_hnt_price": round(float(late_p), 4),
        "early_hnt_emission_monthly": round(float(early_e), 0),
        "late_hnt_emission_monthly": round(float(late_e), 0),
        "decomposition": {
            "fee_growth_pct": round(float(fee_share) * 100, 1),
            "price_decline_pct": round(float(price_share) * 100, 1),
            "emission_reduction_pct": round(float(emission_share) * 100, 1),
            "sum_check_pct": round(float(fee_share + price_share + emission_share) * 100, 1),
        },
        "log_differences": {
            "delta_ln_bme": round(float(delta_ln_bme), 4),
            "delta_ln_dc_usd": round(float(delta_ln_dc), 4),
            "delta_ln_price": round(float(delta_ln_p), 4),
            "delta_ln_emission": round(float(delta_ln_e), 4),
        },
        "counterfactuals": {
            "late_fees_early_price": round(float(cf_fee_only), 4),
            "early_fees_late_price": round(float(cf_price_only), 4),
            "late_fees_early_emissions": round(float(cf_emission_only), 4),
            "fee_growth_alone": round(float(cf_fee_growth_alone), 4),
        },
        "multipliers": {
            "dc_usd_growth_x": round(float(late_dc / early_dc), 1),
            "price_decline_x": round(float(late_p / early_p), 2),
            "emission_decline_x": round(float(late_e / early_e), 2),
            "bme_growth_x": round(float(late_bme / early_bme), 1),
        },
        "data_sources": {
            "price": "Dune Analytics avg_price_usd from weekly HNT volume (149 weeks)",
            "burns": "Dune Analytics usd_burned from weekly HNT burn transactions (149 weeks)",
            "emissions": "Dune Analytics hnt_issued from weekly mint transactions (149 weeks)",
        },
        "methodology": (
            "Log-difference attribution: ln(BME) = ln(DC_USD) - ln(P) - ln(E). "
            "Early anchor = 3-month average (Jun–Aug 2023, post-migration settling). "
            "Late anchor = 3-month average (Oct–Dec 2025, recent stable period). "
            "Shares computed as component Δln / total Δln(BME)."
        ),
        "monthly_data": monthly_out.to_dict(orient="records"),
        "notes": (
            "April 2023 excluded (one-time Solana migration issuance of 145M HNT). "
            "BME and S2R are used interchangeably in this analysis (same formula). "
            "The usd_burned field from Dune represents DC burn revenue at "
            "$0.00001/DC × HNT price at burn time."
        ),
    }

    json_path = OUTPUT_DIR / "helium_bme_decomposition.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Saved: {json_path}")

    # ── Summary for paper ────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("SUMMARY FOR PAPER (§5 paragraph)")
    print(f"{'=' * 70}")
    print(f"""
  Helium's BME improved from {early_bme:.3f} (Jun–Aug 2023) to {late_bme:.2f}
  (Oct–Dec 2025), a {late_bme/early_bme:.0f}× increase. Log-difference
  attribution decomposes this into three channels:

  - Fee growth:          {fee_share:.1%} — DC burn revenue rose from
    ${early_dc:,.0f}/mo to ${late_dc:,.0f}/mo ({late_dc/early_dc:.0f}×)
  - Price decline:       {price_share:.1%} — HNT price fell from
    ${early_p:.2f} to ${late_p:.2f}, mechanically increasing HNT burned
    per dollar of DC demand
  - Emission reduction:  {emission_share:.1%} — Monthly HNT issuance
    fell from {early_e:,.0f} to {late_e:,.0f} (halving schedule)

  Counterfactual: holding price and emissions at early-period levels,
  fee growth alone would have raised BME from {early_bme:.4f} to
  {cf_fee_growth_alone:.4f} — a {cf_fee_growth_alone/early_bme:.0f}× improvement
  versus the observed {late_bme/early_bme:.0f}×.
""")

if __name__ == "__main__":
    main()
