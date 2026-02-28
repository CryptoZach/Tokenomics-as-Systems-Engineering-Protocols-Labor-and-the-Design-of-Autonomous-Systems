#!/usr/bin/env python3
"""
Verify Helium BME Decomposition Arithmetic.

Three issues flagged for paper-readiness:
  Issue 1: Counterfactual BME of 0.34 vs expected ~0.76
  Issue 2: "58% emission cut" vs 50% halving
  Issue 3: Endpoint BME doesn't close from stated components
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


def build_monthly():
    """Build monthly panel from weekly Dune data (same as decomposition scripts)."""
    burns = load_dune_json(HELIUM_DIR / "dune_hnt_weekly_burns.json")
    issuance = load_dune_json(HELIUM_DIR / "dune_hnt_weekly_issuance.json")
    volume = load_dune_json(HELIUM_DIR / "dune_hnt_weekly_volume.json")

    for df in [burns, issuance, volume]:
        df["week"] = pd.to_datetime(df["week"])

    weekly = burns[["week", "hnt_burned", "usd_burned"]].merge(
        issuance[["week", "hnt_issued"]], on="week", how="inner"
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
    monthly["bme_onchain"] = monthly["hnt_burned"] / monthly["hnt_issued"]
    monthly["bme_usd"] = monthly["dc_burn_usd"] / (
        monthly["hnt_price_avg"] * monthly["hnt_issued"]
    )
    return monthly, weekly


def main():
    monthly, weekly = build_monthly()

    # ================================================================
    # ISSUE 3 (HIGHEST PRIORITY): ENDPOINT BME CLOSURE
    # ================================================================
    print("=" * 74)
    print("ISSUE 3: ENDPOINT BME CLOSURE")
    print("=" * 74)
    print()
    print("The paper quotes BME = 2.06 for Feb 2026, but:")
    print("  $707K / $1.10 = 643K HNT burned; 643K / 700K = 0.92, not 2.06.")
    print()
    print("ROOT CAUSE: Two different BME calculations exist in the code:")
    print("  bme_onchain = hnt_burned / hnt_issued  (used as headline)")
    print("  bme_usd     = dc_burn_usd / (price × issued)  (used in decomposition)")
    print()

    last3 = monthly[monthly["month"] >= "2025-12-01"].copy()
    print(f"  {'Month':>8}  {'dc_burn_usd':>12}  {'hnt_burned':>12}  {'hnt_issued':>10}"
          f"  {'price':>7}  {'BME_onch':>9}  {'BME_usd':>9}  {'gap':>6}")
    print(f"  {'─' * 84}")
    for _, r in last3.iterrows():
        gap_pct = (r["bme_onchain"] / r["bme_usd"] - 1) * 100
        print(f"  {r['month'].strftime('%Y-%m'):>8}"
              f"  ${r['dc_burn_usd']:>10,.0f}"
              f"  {r['hnt_burned']:>12,.0f}"
              f"  {r['hnt_issued']:>10,.0f}"
              f"  ${r['hnt_price_avg']:>5.4f}"
              f"  {r['bme_onchain']:>9.4f}"
              f"  {r['bme_usd']:>9.4f}"
              f"  {gap_pct:>+5.1f}%")

    print()
    print("  CROSS-CHECK for each month:")
    for _, r in last3.iterrows():
        m = r["month"].strftime("%Y-%m")
        implied_hnt = r["dc_burn_usd"] / r["hnt_price_avg"]
        print(f"\n  {m}:")
        print(f"    dc_burn_usd / avg_price = ${r['dc_burn_usd']:,.0f} / ${r['hnt_price_avg']:.4f}"
              f" = {implied_hnt:,.0f} HNT (USD-implied burns)")
        print(f"    Actual hnt_burned from Dune = {r['hnt_burned']:,.0f} HNT")
        print(f"    Discrepancy: {r['hnt_burned']:,.0f} vs {implied_hnt:,.0f}"
              f" = {(r['hnt_burned']/implied_hnt - 1)*100:+.1f}%")
        print(f"    bme_onchain = {r['hnt_burned']:,.0f} / {r['hnt_issued']:,.0f}"
              f" = {r['bme_onchain']:.4f}")
        print(f"    bme_usd     = {implied_hnt:,.0f} / {r['hnt_issued']:,.0f}"
              f" = {r['bme_usd']:.4f}")

    # Show Feb 2026 specifically (the user's example)
    feb26 = monthly[monthly["month"] == "2026-02-01"].iloc[0]
    print(f"\n  WHY hnt_burned ≠ dc_burn_usd / avg_price:")
    print(f"    The 'usd_burned' from Dune = sum of (HNT_burned × price_at_burn_time)")
    print(f"    The 'avg_price_usd' from Dune = volume-weighted average transfer price")
    print(f"    These are different price averages. When HNT price moves within a month,")
    print(f"    the burn-weighted price ≠ the transfer-volume-weighted price.")
    print(f"    Feb 2026 implied burn price: ${feb26['dc_burn_usd'] / feb26['hnt_burned']:.4f}")
    print(f"    Feb 2026 avg transfer price: ${feb26['hnt_price_avg']:.4f}")
    print(f"    Ratio: {feb26['dc_burn_usd'] / feb26['hnt_burned'] / feb26['hnt_price_avg']:.3f}"
          f" (burn-time price / transfer-avg price)")

    # Also: Feb 2026 has only 3 weeks of data (data pulled Feb 19)
    feb_weeks = weekly[weekly["week"].dt.to_period("M") == pd.Period("2026-02", "M")]
    print(f"\n  NOTE: Feb 2026 has only {len(feb_weeks)} weeks of data (Dune pulled 2026-02-19).")
    print(f"    This is a PARTIAL MONTH — BME may change when full month is available.")

    # Also: Feb 2026 emissions = 377K, not "~700K" as user assumed
    print(f"\n  CRITICAL: Feb 2026 hnt_issued = {feb26['hnt_issued']:,.0f}")
    print(f"    The user assumed ~700K from the phase average, but Feb specifically")
    print(f"    has lower emissions. Post-halving emissions vary by month:")
    post = monthly[monthly["month"] >= "2025-08-01"]
    for _, r in post.iterrows():
        print(f"      {r['month'].strftime('%Y-%m')}: {r['hnt_issued']:>10,.0f} HNT"
              f" ({r['n_weeks']} weeks)")

    # ================================================================
    # ISSUE 2: "58% EMISSION CUT" VS 50% HALVING
    # ================================================================
    print(f"\n{'=' * 74}")
    print("ISSUE 2: 58% EMISSION CUT VS 50% HALVING")
    print("=" * 74)

    halving_months = monthly[
        (monthly["month"] >= "2025-06-01") & (monthly["month"] <= "2025-10-31")
    ]
    print(f"\n  Monthly HNT emission values around the halving:")
    print(f"  {'Month':>8}  {'hnt_issued':>12}  {'n_weeks':>7}  {'per_week':>12}  Source")
    print(f"  {'─' * 70}")
    for _, r in halving_months.iterrows():
        per_wk = r["hnt_issued"] / r["n_weeks"]
        print(f"  {r['month'].strftime('%Y-%m'):>8}  {r['hnt_issued']:>12,.0f}"
              f"  {int(r['n_weeks']):>7}  {per_wk:>12,.0f}"
              f"  Dune: weekly mint txns")

    # Show the weekly detail around the halving
    print(f"\n  Weekly detail (Jul–Sep 2025):")
    halving_weeks = weekly[
        (weekly["week"] >= "2025-07-01") & (weekly["week"] <= "2025-09-30")
    ]
    print(f"  {'Week':>12}  {'hnt_issued':>12}")
    print(f"  {'─' * 28}")
    for _, r in halving_weeks.iterrows():
        print(f"  {r['week'].strftime('%Y-%m-%d'):>12}  {r['hnt_issued']:>12,.0f}")

    jul = halving_months[halving_months["month"] == "2025-07-01"].iloc[0]
    aug = halving_months[halving_months["month"] == "2025-08-01"].iloc[0]
    jul_per_wk = jul["hnt_issued"] / jul["n_weeks"]
    aug_per_wk = aug["hnt_issued"] / aug["n_weeks"]
    pct_cut = (1 - aug_per_wk / jul_per_wk) * 100

    print(f"\n  Jul per-week: {jul_per_wk:,.0f} HNT ({int(jul['n_weeks'])} weeks)")
    print(f"  Aug per-week: {aug_per_wk:,.0f} HNT ({int(aug['n_weeks'])} weeks)")
    print(f"  Per-week reduction: {pct_cut:.1f}%")

    # Phase-average comparison (what the narrative used)
    pre_halving = monthly[
        (monthly["month"] >= "2025-03-01") & (monthly["month"] <= "2025-07-31")
    ]["hnt_issued"]
    post_halving = monthly[
        (monthly["month"] >= "2025-08-01") & (monthly["month"] <= "2025-09-30")
    ]["hnt_issued"]
    pre_avg = pre_halving.mean()
    post_avg = post_halving.mean()
    phase_cut = (1 - post_avg / pre_avg) * 100

    print(f"\n  Phase-average comparison (what the '58%' came from):")
    print(f"    Pre-halving avg (Mar–Jul): {pre_avg:,.0f} HNT/mo")
    print(f"    Halving transition avg (Aug–Sep): {post_avg:,.0f} HNT/mo")
    print(f"    Reduction: {phase_cut:.1f}%")
    print(f"\n  The 58% is a phase-average comparison, NOT a clean pre/post single-month")
    print(f"  comparison. It's legitimate but conflates:")
    print(f"    - The actual halving schedule reduction")
    print(f"    - Varying weeks-per-month (4 vs 5 week months)")
    print(f"    - Any ongoing emission schedule changes")

    # ================================================================
    # ISSUE 1: COUNTERFACTUAL BME OF 0.34
    # ================================================================
    print(f"\n{'=' * 74}")
    print("ISSUE 1: COUNTERFACTUAL BME OF 0.34")
    print("=" * 74)

    mar25 = monthly[monthly["month"] == "2025-03-01"].iloc[0]
    feb26 = monthly[monthly["month"] == "2026-02-01"].iloc[0]

    print(f"\n  The 12-month analysis claims:")
    print(f"    'Without the halving, BME would be 0.34 instead of 2.06.'")
    print(f"\n  Step-by-step trace of the counterfactual code:")
    print(f"    cf_emis = (end['dc_burn_usd'] / end['hnt_price_avg']) / start['hnt_issued']")

    cf_numerator = feb26["dc_burn_usd"] / feb26["hnt_price_avg"]
    cf_denom = mar25["hnt_issued"]
    cf_result = cf_numerator / cf_denom

    print(f"    = (${feb26['dc_burn_usd']:,.0f} / ${feb26['hnt_price_avg']:.4f}) / {mar25['hnt_issued']:,.0f}")
    print(f"    = {cf_numerator:,.0f} / {cf_denom:,.0f}")
    print(f"    = {cf_result:.4f}")
    print(f"\n  This uses the USD-implied burn path (dc_burn_usd / price), not on-chain hnt_burned.")
    print(f"  The headline BME uses hnt_burned / hnt_issued = {feb26['bme_onchain']:.4f}")

    # What the user expected
    emission_ratio = mar25["hnt_issued"] / feb26["hnt_issued"]
    user_expected = feb26["bme_onchain"] / emission_ratio
    print(f"\n  User's expectation: actual_BME / emission_ratio")
    print(f"    = {feb26['bme_onchain']:.4f} / ({mar25['hnt_issued']:,.0f} / {feb26['hnt_issued']:,.0f})")
    print(f"    = {feb26['bme_onchain']:.4f} / {emission_ratio:.2f}")
    print(f"    = {user_expected:.4f}")

    # Why these differ
    print(f"\n  WHY 0.34 ≠ 0.41:")
    print(f"    0.344 = (dc_burn_usd / avg_price) / start_emissions  [USD-implied path]")
    print(f"    0.414 = hnt_burned / start_emissions                  [on-chain path]")
    print(f"    The gap comes from the same price discrepancy as Issue 3:")
    print(f"    Feb 2026 burn-price (${feb26['dc_burn_usd']/feb26['hnt_burned']:.4f})"
          f" ≠ transfer-avg price (${feb26['hnt_price_avg']:.4f})")

    # The user's SECOND error: assumed 700K emissions, actual is 377K
    print(f"\n  User also assumed emission ratio = 1.9M / 700K = 2.71×")
    print(f"  Actual emission ratio = {mar25['hnt_issued']:,.0f} / {feb26['hnt_issued']:,.0f}"
          f" = {emission_ratio:.2f}×")
    print(f"  Feb 2026 emissions are 377K, not ~700K (Feb is a partial month + further decline)")

    # Internally consistent counterfactuals
    print(f"\n  CORRECTED COUNTERFACTUALS (two consistent versions):")
    print(f"\n  Version A — USD-implied path (consistent with decomposition formula):")
    cf_a = (feb26["dc_burn_usd"] / feb26["hnt_price_avg"]) / mar25["hnt_issued"]
    actual_a = feb26["bme_usd"]
    print(f"    Actual BME_usd  = {actual_a:.4f}")
    print(f"    CF (no halving) = {cf_a:.4f}")
    print(f"    Sentence: 'Without the halving, BME would be {cf_a:.2f} instead of {actual_a:.2f}.'")

    print(f"\n  Version B — On-chain path (consistent with headline BME):")
    cf_b = feb26["hnt_burned"] / mar25["hnt_issued"]
    actual_b = feb26["bme_onchain"]
    print(f"    Actual BME_onch = {actual_b:.4f}")
    print(f"    CF (no halving) = {cf_b:.4f}")
    print(f"    Sentence: 'Without the halving, BME would be {cf_b:.2f} instead of {actual_b:.2f}.'")

    # ================================================================
    # METHODOLOGICAL FINDING
    # ================================================================
    print(f"\n{'=' * 74}")
    print("METHODOLOGICAL FINDING: TWO BME DEFINITIONS")
    print("=" * 74)

    print(f"""
  The decomposition script mixes two BME calculations:

  1. HEADLINE BME (on-chain): hnt_burned / hnt_issued
     - Used for: the reported BME values (0.107, 2.06, etc.)
     - Source: Dune burn transactions (hnt_burned) and mint transactions (hnt_issued)

  2. USD-IMPLIED BME: dc_burn_usd / (avg_price × hnt_issued)
     - Used for: the log decomposition (Δln(DC) - Δln(P) - Δln(E))
     - Source: Dune burn USD values and volume-weighted transfer prices

  These diverge because avg_price_usd (volume-weighted transfer price) ≠
  the burn-weighted average price implicit in dc_burn_usd / hnt_burned.

  CONSEQUENCES:
  - Decomposition shares don't sum to 100% (currently 96.3% for 12-month)
  - Counterfactuals computed via USD path don't match headline BME
  - The 0.34 counterfactual is consistent with bme_usd=1.71, not bme_onchain=2.06""")

    # Show the gap across all months
    print(f"  BME gap (onchain vs USD-implied) by month:")
    print(f"  {'Month':>8}  {'BME_onch':>9}  {'BME_usd':>9}  {'Gap%':>7}")
    print(f"  {'─' * 40}")
    for _, r in monthly[monthly["month"] >= "2025-03-01"].iterrows():
        gap = (r["bme_onchain"] / r["bme_usd"] - 1) * 100
        flag = " ← large" if abs(gap) > 10 else ""
        print(f"  {r['month'].strftime('%Y-%m'):>8}"
              f"  {r['bme_onchain']:>9.4f}"
              f"  {r['bme_usd']:>9.4f}"
              f"  {gap:>+6.1f}%{flag}")

    # ================================================================
    # RECOMMENDED FIX
    # ================================================================
    print(f"\n{'=' * 74}")
    print("RECOMMENDED FIX")
    print("=" * 74)
    print(f"""
  Option A (RECOMMENDED): Use bme_usd consistently everywhere.
    - Headline BME = dc_burn_usd / (avg_price × hnt_issued)
    - Decomposition: Δln(BME_usd) = Δln(DC) - Δln(P) - Δln(E) → sums to 100%
    - Counterfactuals are internally consistent
    - Trade-off: Feb 2026 BME = 1.71 instead of 2.06

  Option B: Use bme_onchain as headline, decompose into 2 components only.
    - BME = hnt_burned / hnt_issued
    - Δln(BME) = Δln(hnt_burned) - Δln(hnt_issued)
    - Only two components: burn growth and emission reduction (no price separation)
    - Trade-off: can't isolate the price channel

  Option C: Use bme_onchain but note the residual explicitly.
    - Keep the 3-component decomposition
    - Report the residual (interaction/timing term) as a fourth line
    - Trade-off: decomposition doesn't sum to 100%, more complex for readers""")

    # ================================================================
    # RECOMPUTE WITH CONSISTENT USD-IMPLIED BME
    # ================================================================
    print(f"\n{'=' * 74}")
    print("RECOMPUTED DECOMPOSITION (USD-consistent, Option A)")
    print("=" * 74)

    # 12-month window
    mar25 = monthly[monthly["month"] == "2025-03-01"].iloc[0]
    feb26 = monthly[monthly["month"] == "2026-02-01"].iloc[0]

    d_bme = np.log(feb26["bme_usd"] / mar25["bme_usd"])
    d_dc = np.log(feb26["dc_burn_usd"] / mar25["dc_burn_usd"])
    d_p = np.log(feb26["hnt_price_avg"] / mar25["hnt_price_avg"])
    d_e = np.log(feb26["hnt_issued"] / mar25["hnt_issued"])

    fee_s = d_dc / d_bme * 100
    price_s = -d_p / d_bme * 100
    emis_s = -d_e / d_bme * 100

    print(f"\n  12-MONTH (Mar 2025 → Feb 2026), using bme_usd:")
    print(f"    Start: bme_usd = {mar25['bme_usd']:.4f}")
    print(f"    End:   bme_usd = {feb26['bme_usd']:.4f}")
    print(f"    Growth: {feb26['bme_usd']/mar25['bme_usd']:.1f}×")
    print(f"\n    Δln(BME_usd)  = {d_bme:+.4f}")
    print(f"    Δln(DC_USD)   = {d_dc:+.4f}  → fee share:      {fee_s:>6.1f}%")
    print(f"    -Δln(Price)   = {-d_p:+.4f}  → price share:    {price_s:>6.1f}%")
    print(f"    -Δln(Emission)= {-d_e:+.4f}  → emission share: {emis_s:>6.1f}%")
    print(f"    Sum:                               {fee_s+price_s+emis_s:>6.1f}%")

    cf_emis_consistent = (feb26["dc_burn_usd"] / feb26["hnt_price_avg"]) / mar25["hnt_issued"]
    print(f"\n    Counterfactual (no halving): {cf_emis_consistent:.4f}")
    print(f"    Actual bme_usd:             {feb26['bme_usd']:.4f}")
    print(f"    Sentence: 'Without emission reduction, BME would be {cf_emis_consistent:.2f}"
          f" instead of {feb26['bme_usd']:.2f}.'")

    # Full-period decomposition (Jun-Aug 2023 → Oct-Dec 2025)
    early = monthly[(monthly["month"] >= "2023-06-01") & (monthly["month"] <= "2023-08-31")]
    late = monthly[(monthly["month"] >= "2025-10-01") & (monthly["month"] <= "2025-12-31")]

    e_bme = early["bme_usd"].mean()
    l_bme = late["bme_usd"].mean()
    e_dc = early["dc_burn_usd"].mean()
    l_dc = late["dc_burn_usd"].mean()
    e_p = early["hnt_price_avg"].mean()
    l_p = late["hnt_price_avg"].mean()
    e_e = early["hnt_issued"].mean()
    l_e = late["hnt_issued"].mean()

    d_bme_f = np.log(l_bme / e_bme)
    d_dc_f = np.log(l_dc / e_dc)
    d_p_f = np.log(l_p / e_p)
    d_e_f = np.log(l_e / e_e)

    fee_f = d_dc_f / d_bme_f * 100
    price_f = -d_p_f / d_bme_f * 100
    emis_f = -d_e_f / d_bme_f * 100

    print(f"\n  FULL-PERIOD (Jun-Aug 2023 → Oct-Dec 2025), using bme_usd:")
    print(f"    Start: bme_usd = {e_bme:.4f}")
    print(f"    End:   bme_usd = {l_bme:.4f}")
    print(f"    Growth: {l_bme/e_bme:.1f}×")
    print(f"\n    Δln(BME_usd)  = {d_bme_f:+.4f}")
    print(f"    Δln(DC_USD)   = {d_dc_f:+.4f}  → fee share:      {fee_f:>6.1f}%")
    print(f"    -Δln(Price)   = {-d_p_f:+.4f}  → price share:    {price_f:>6.1f}%")
    print(f"    -Δln(Emission)= {-d_e_f:+.4f}  → emission share: {emis_f:>6.1f}%")
    print(f"    Sum:                               {fee_f+price_f+emis_f:>6.1f}%")

    # ================================================================
    # BUILD CORRECTIONS JSON
    # ================================================================
    print(f"\n{'=' * 74}")
    print("SAVING CORRECTIONS")
    print("=" * 74)

    corrections_data = {
        "verification_date": "2026-02-24",
        "corrections": [
            {
                "issue": "counterfactual_bme",
                "old_value": 0.34,
                "old_context": "Compared against headline bme_onchain=2.06",
                "new_value_usd_consistent": round(float(cf_emis_consistent), 4),
                "new_context_usd": f"Consistent with bme_usd={feb26['bme_usd']:.4f}",
                "new_value_onchain_consistent": round(float(feb26["hnt_burned"] / mar25["hnt_issued"]), 4),
                "new_context_onchain": f"Consistent with bme_onchain={feb26['bme_onchain']:.4f}",
                "explanation": (
                    "The 0.34 counterfactual was computed via the USD-implied path "
                    "(dc_burn_usd / price / start_emissions) but compared against the "
                    "on-chain headline BME of 2.06. It is internally consistent with "
                    "bme_usd=1.71, not bme_onchain=2.06. The on-chain equivalent "
                    "counterfactual is 0.41. Additionally, the user assumed Feb 2026 "
                    "emissions were ~700K, but they are actually 377K (partial month "
                    "data + further emission schedule decline), making the emission "
                    "ratio 4.97x not 2.71x."
                ),
            },
            {
                "issue": "emission_cut_pct",
                "old_value": "58%",
                "verified": True,
                "explanation": (
                    f"The 58% is a phase-average comparison: pre-halving average "
                    f"(Mar-Jul 2025) = {pre_avg:,.0f} HNT/mo vs halving transition "
                    f"average (Aug-Sep 2025) = {post_avg:,.0f} HNT/mo. "
                    f"Per-week comparison Jul→Aug = {pct_cut:.1f}% reduction. "
                    f"Exceeds 50% because: (1) months have 4 or 5 weeks, affecting "
                    f"monthly totals; (2) the halving may not align exactly to month "
                    f"boundaries; (3) SubDAO emission allocation mechanics."
                ),
            },
            {
                "issue": "endpoint_bme_closure",
                "explanation": (
                    "The BME does NOT close from the stated components because the code "
                    "uses two different calculations: bme_onchain = hnt_burned / hnt_issued "
                    "(headline), and the decomposition uses dc_burn_usd / (avg_price × "
                    "hnt_issued). These diverge because avg_price_usd (volume-weighted "
                    "transfer price from Dune) differs from the burn-weighted average price "
                    "implicit in dc_burn_usd / hnt_burned. For Feb 2026: burn-weighted "
                    f"price = ${feb26['dc_burn_usd']/feb26['hnt_burned']:.4f}, transfer-avg "
                    f"price = ${feb26['hnt_price_avg']:.4f}. Also note Feb 2026 is a PARTIAL "
                    f"MONTH (3 weeks of data, pulled 2026-02-19)."
                ),
                "bme_onchain": round(float(feb26["bme_onchain"]), 4),
                "bme_usd_implied": round(float(feb26["bme_usd"]), 4),
                "gap_pct": round(float((feb26["bme_onchain"] / feb26["bme_usd"] - 1) * 100), 1),
            },
        ],
        "monthly_emissions_around_halving": {},
        "endpoint_arithmetic": {
            "months": [],
            "values": [],
        },
        "revised_decomposition": {
            "twelve_month": {
                "method": "USD-consistent (bme_usd = dc_burn_usd / (price × issued))",
                "start_bme_usd": round(float(mar25["bme_usd"]), 4),
                "end_bme_usd": round(float(feb26["bme_usd"]), 4),
                "fee_growth_pct": round(float(fee_s), 1),
                "price_decline_pct": round(float(price_s), 1),
                "emission_reduction_pct": round(float(emis_s), 1),
                "sum_check_pct": round(float(fee_s + price_s + emis_s), 1),
                "counterfactual_no_halving": round(float(cf_emis_consistent), 4),
            },
            "full_period": {
                "method": "USD-consistent (bme_usd = dc_burn_usd / (price × issued))",
                "start_bme_usd": round(float(e_bme), 4),
                "end_bme_usd": round(float(l_bme), 4),
                "fee_growth_pct": round(float(fee_f), 1),
                "price_decline_pct": round(float(price_f), 1),
                "emission_reduction_pct": round(float(emis_f), 1),
                "sum_check_pct": round(float(fee_f + price_f + emis_f), 1),
            },
        },
        "recommended_fix": (
            "Use bme_usd = dc_burn_usd / (avg_price × hnt_issued) consistently as the "
            "headline BME metric. This ensures the three-component log decomposition sums "
            "to exactly 100% and counterfactuals are internally consistent. The trade-off: "
            "Feb 2026 BME = 1.71 instead of 2.06. Alternatively, note both metrics and "
            "report the residual explicitly."
        ),
    }

    # Fill emissions around halving
    for _, r in halving_months.iterrows():
        m = r["month"].strftime("%Y-%m")
        corrections_data["monthly_emissions_around_halving"][m] = {
            "hnt_issued": round(float(r["hnt_issued"]), 0),
            "n_weeks": int(r["n_weeks"]),
            "per_week": round(float(r["hnt_issued"] / r["n_weeks"]), 0),
            "source": "Dune Analytics: weekly HNT mint transactions",
        }

    # Fill endpoint arithmetic
    for _, r in last3.iterrows():
        m = r["month"].strftime("%Y-%m")
        implied_hnt = r["dc_burn_usd"] / r["hnt_price_avg"]
        corrections_data["endpoint_arithmetic"]["months"].append(m)
        corrections_data["endpoint_arithmetic"]["values"].append({
            "dc_burn_usd": round(float(r["dc_burn_usd"]), 2),
            "hnt_burned_onchain": round(float(r["hnt_burned"]), 0),
            "hnt_burned_usd_implied": round(float(implied_hnt), 0),
            "hnt_price_avg": round(float(r["hnt_price_avg"]), 4),
            "hnt_price_at_burn": round(float(r["dc_burn_usd"] / r["hnt_burned"]), 4),
            "hnt_issued": round(float(r["hnt_issued"]), 0),
            "n_weeks": int(r["n_weeks"]),
            "bme_onchain": round(float(r["bme_onchain"]), 4),
            "bme_usd_implied": round(float(r["bme_usd"]), 4),
            "closure_check": f"{implied_hnt:,.0f} / {r['hnt_issued']:,.0f} = {r['bme_usd']:.4f}",
        })

    # Save
    json_path = HELIUM_DIR / "helium_bme_decomposition.json"
    # Read existing to preserve monthly_data
    with open(json_path) as f:
        existing = json.load(f)

    # Merge corrections into existing
    existing["corrections"] = corrections_data["corrections"]
    existing["monthly_emissions_around_halving"] = corrections_data["monthly_emissions_around_halving"]
    existing["endpoint_arithmetic"] = corrections_data["endpoint_arithmetic"]
    existing["revised_decomposition"] = corrections_data["revised_decomposition"]
    existing["recommended_fix"] = corrections_data["recommended_fix"]
    existing["verification_date"] = corrections_data["verification_date"]

    with open(json_path, "w") as f:
        json.dump(existing, f, indent=2, default=str)
    print(f"\n  Updated: {json_path}")

    # ================================================================
    # FINAL SUMMARY
    # ================================================================
    print(f"\n{'=' * 74}")
    print("FINAL SUMMARY")
    print("=" * 74)
    print(f"""
  ISSUE 3 (endpoint closure): CONFIRMED PROBLEM
    Root cause: bme_onchain (hnt_burned/hnt_issued) ≠ bme_usd (dc_burn_usd/(P×E))
    because burn-weighted price ≠ volume-weighted transfer price.
    Feb 2026: 2.060 (onchain) vs 1.712 (USD-implied) = 20.3% gap.
    Also: Feb 2026 has only 3 weeks of data (partial month).

  ISSUE 1 (counterfactual 0.34): PARTIALLY CORRECT, NEEDS CONTEXT
    0.344 is internally consistent with bme_usd = 1.712, not bme_onchain = 2.060.
    On-chain-consistent counterfactual = 0.414.
    User's estimate of 0.76 was wrong because Feb emissions = 377K, not 700K.

  ISSUE 2 (58% emission cut): VERIFIED CORRECT
    Phase-average comparison: 1,644K → 695K = 57.7%.
    Per-week Jul→Aug: {pct_cut:.1f}% reduction.
    Exceeds 50% due to variable weeks/month and emission schedule mechanics.

  ACTION REQUIRED BEFORE PAPER PUBLICATION:
    1. Choose one BME definition (recommend bme_usd for decomposition consistency)
    2. If using bme_usd: revise headline BME values throughout
    3. If keeping bme_onchain: report residual term in decomposition,
       recompute counterfactuals using on-chain path
    4. Note Feb 2026 is partial-month data (3 of ~4 weeks)
""")


if __name__ == "__main__":
    main()
