#!/usr/bin/env python3
"""
Helium BME: Trailing 12-Month Analysis (Mar 2025 – Feb 2026).

Month-over-month decomposition, phase identification, rolling attribution,
and visualization of the critical year when BME crossed parity.
"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
HELIUM_DIR = SCRIPT_DIR.parent.parent / "data" / "helium"
OUTPUT_DIR = HELIUM_DIR


def load_dune_json(path):
    with open(path) as f:
        data = json.load(f)
    return pd.DataFrame(data.get("result", {}).get("rows", []))


def build_monthly():
    """Build monthly panel from weekly Dune data."""
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
    monthly["bme"] = monthly["hnt_burned"] / monthly["hnt_issued"]
    # Per-week rates remove calendar artifact (4-week vs 5-week months)
    monthly["dc_burn_pw"] = monthly["dc_burn_usd"] / monthly["n_weeks"]
    monthly["hnt_issued_pw"] = monthly["hnt_issued"] / monthly["n_weeks"]
    return monthly


def main():
    print("=" * 70)
    print("HELIUM BME: TRAILING 12-MONTH ANALYSIS (Mar 2025 – Feb 2026)")
    print("=" * 70)

    monthly = build_monthly()

    # ── Slice to trailing 12 months ──────────────────────────────
    t12 = monthly[
        (monthly["month"] >= "2025-03-01") & (monthly["month"] <= "2026-02-28")
    ].copy().reset_index(drop=True)

    # Also keep the month before (Feb 2025) as the baseline for MoM
    baseline_row = monthly[monthly["month"] == "2025-02-01"]
    if len(baseline_row) == 0:
        baseline_row = monthly[monthly["month"] < "2025-03-01"].iloc[[-1]]

    full = pd.concat([baseline_row, t12], ignore_index=True)
    print(f"  Window: {t12['month'].iloc[0].strftime('%Y-%m')} to "
          f"{t12['month'].iloc[-1].strftime('%Y-%m')} ({len(t12)} months)")

    # ── Month-over-month log decomposition ───────────────────────
    print(f"\n{'=' * 70}")
    print("MONTH-OVER-MONTH DECOMPOSITION")
    print(f"{'=' * 70}")

    mom_rows = []
    prev = full.iloc[0]
    for i in range(1, len(full)):
        curr = full.iloc[i]

        if prev["bme"] <= 0 or curr["bme"] <= 0:
            prev = curr
            continue
        if prev["dc_burn_usd"] <= 0 or curr["dc_burn_usd"] <= 0:
            prev = curr
            continue

        d_bme = np.log(curr["bme"] / prev["bme"])
        # Use per-week rates to remove calendar artifact (4 vs 5 week months)
        d_dc = np.log(curr["dc_burn_pw"] / prev["dc_burn_pw"])
        d_p = np.log(curr["hnt_price_avg"] / prev["hnt_price_avg"])
        d_e = np.log(curr["hnt_issued_pw"] / prev["hnt_issued_pw"])

        # USD-implied BME change (should be close to d_bme when price gap is small)
        d_bme_usd = d_dc - d_p - d_e

        # Shares (use USD-implied denominator so they sum to 100%)
        if abs(d_bme_usd) > 0.001:
            fee_pct = d_dc / d_bme_usd * 100
            price_pct = -d_p / d_bme_usd * 100
            emis_pct = -d_e / d_bme_usd * 100
        else:
            fee_pct = price_pct = emis_pct = np.nan

        mom_rows.append({
            "month": curr["month"],
            "bme": curr["bme"],
            "bme_prev": prev["bme"],
            "bme_chg_pct": (curr["bme"] / prev["bme"] - 1) * 100,
            "dc_burn_pw": curr["dc_burn_pw"],
            "hnt_price": curr["hnt_price_avg"],
            "hnt_issued_pw": curr["hnt_issued_pw"],
            "n_weeks": curr["n_weeks"],
            "dln_bme": d_bme,
            "dln_bme_usd": d_bme_usd,
            "dln_dc": d_dc,
            "dln_price": d_p,
            "dln_emission": d_e,
            "fee_contrib_pct": fee_pct,
            "price_contrib_pct": price_pct,
            "emission_contrib_pct": emis_pct,
        })
        prev = curr

    mom = pd.DataFrame(mom_rows)

    print(f"\n  {'Month':>8} {'BME':>7} {'Chg%':>7} "
          f"{'Fee%':>7} {'Price%':>7} {'Emis%':>7}  "
          f"{'DC/wk':>10} {'HNT_P':>7} {'E/wk':>9} {'wk':>3}")
    print(f"  {'─' * 82}")
    for _, r in mom.iterrows():
        fee_s = f"{r['fee_contrib_pct']:>6.0f}%" if not np.isnan(r['fee_contrib_pct']) else "   n/a"
        price_s = f"{r['price_contrib_pct']:>6.0f}%" if not np.isnan(r['price_contrib_pct']) else "   n/a"
        emis_s = f"{r['emission_contrib_pct']:>6.0f}%" if not np.isnan(r['emission_contrib_pct']) else "   n/a"
        print(f"  {r['month'].strftime('%Y-%m'):>8} "
              f"{r['bme']:>7.3f} {r['bme_chg_pct']:>+6.0f}% "
              f"{fee_s} {price_s} {emis_s}  "
              f"${r['dc_burn_pw']:>9,.0f} "
              f"${r['hnt_price']:>5.2f} "
              f"{r['hnt_issued_pw']:>9,.0f} "
              f"{int(r['n_weeks']):>2}")

    # ── Phase identification ─────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("PHASE IDENTIFICATION")
    print(f"{'=' * 70}")

    phases = []

    # Phase 1: pre-halving baseline (Mar–Jul 2025)
    p1 = t12[(t12["month"] >= "2025-03-01") & (t12["month"] <= "2025-07-31")]
    if len(p1) > 0:
        phases.append({
            "name": "Pre-halving baseline",
            "period": "Mar–Jul 2025",
            "months": len(p1),
            "bme_mean": p1["bme"].mean(),
            "bme_range": f"{p1['bme'].min():.3f}–{p1['bme'].max():.3f}",
            "dc_mean": p1["dc_burn_usd"].mean(),
            "price_mean": p1["hnt_price_avg"].mean(),
            "emission_mean": p1["hnt_issued"].mean(),
            "note": "Irregular: Jun spike ($2.16M DC) amid mostly low months",
        })

    # Phase 2: halving transition (Aug–Sep 2025)
    p2 = t12[(t12["month"] >= "2025-08-01") & (t12["month"] <= "2025-09-30")]
    if len(p2) > 0:
        phases.append({
            "name": "Halving transition",
            "period": "Aug–Sep 2025",
            "months": len(p2),
            "bme_mean": p2["bme"].mean(),
            "bme_range": f"{p2['bme'].min():.3f}–{p2['bme'].max():.3f}",
            "dc_mean": p2["dc_burn_usd"].mean(),
            "price_mean": p2["hnt_price_avg"].mean(),
            "emission_mean": p2["hnt_issued"].mean(),
            "note": "Emission halved (~1.5M→~700K/mo); DC burns >$1M/mo",
        })

    # Phase 3: post-halving maturity (Oct 2025 – Feb 2026)
    p3 = t12[(t12["month"] >= "2025-10-01") & (t12["month"] <= "2026-02-28")]
    if len(p3) > 0:
        phases.append({
            "name": "Post-halving maturity",
            "period": "Oct 2025 – Feb 2026",
            "months": len(p3),
            "bme_mean": p3["bme"].mean(),
            "bme_range": f"{p3['bme'].min():.3f}–{p3['bme'].max():.3f}",
            "dc_mean": p3["dc_burn_usd"].mean(),
            "price_mean": p3["hnt_price_avg"].mean(),
            "emission_mean": p3["hnt_issued"].mean(),
            "note": "Sustained BME >1.0; price decline accelerates",
        })

    for ph in phases:
        print(f"\n  {ph['name']} ({ph['period']}, {ph['months']} months):")
        print(f"    BME:       {ph['bme_mean']:.3f} (range {ph['bme_range']})")
        print(f"    DC/mo:     ${ph['dc_mean']:,.0f}")
        print(f"    Price:     ${ph['price_mean']:.2f}")
        print(f"    Emission:  {ph['emission_mean']:,.0f} HNT/mo")
        print(f"    Note:      {ph['note']}")

    # ── Year-over-year decomposition (Mar 2025 vs Feb 2026) ──────
    print(f"\n{'=' * 70}")
    print("12-MONTH DECOMPOSITION (start → end)")
    print(f"{'=' * 70}")

    start = t12.iloc[0]
    end = t12.iloc[-1]

    # Use per-week rates so calendar effects (4 vs 5 vs 3 week months) cancel
    d_dc_y = np.log(end["dc_burn_pw"] / start["dc_burn_pw"])
    d_p_y = np.log(end["hnt_price_avg"] / start["hnt_price_avg"])
    d_e_y = np.log(end["hnt_issued_pw"] / start["hnt_issued_pw"])
    d_bme_usd_y = d_dc_y - d_p_y - d_e_y

    fee_y = d_dc_y / d_bme_usd_y * 100
    price_y = -d_p_y / d_bme_usd_y * 100
    emis_y = -d_e_y / d_bme_usd_y * 100

    print(f"\n  {start['month'].strftime('%Y-%m')}: BME={start['bme']:.4f}, "
          f"DC/wk=${start['dc_burn_pw']:,.0f}, P=${start['hnt_price_avg']:.2f}, "
          f"E/wk={start['hnt_issued_pw']:,.0f} ({int(start['n_weeks'])}wk)")
    print(f"  {end['month'].strftime('%Y-%m')}: BME={end['bme']:.4f}, "
          f"DC/wk=${end['dc_burn_pw']:,.0f}, P=${end['hnt_price_avg']:.2f}, "
          f"E/wk={end['hnt_issued_pw']:,.0f} ({int(end['n_weeks'])}wk)")
    print(f"\n  BME change: {start['bme']:.4f} → {end['bme']:.4f} "
          f"({end['bme']/start['bme']:.1f}×)")

    print(f"\n  ┌─────────────────────────────────┬──────────┬──────────┐")
    print(f"  │ Component (per-week rates)       │ Δln      │ Share    │")
    print(f"  ├─────────────────────────────────┼──────────┼──────────┤")
    print(f"  │ Fee growth (DC burn/wk)          │ {d_dc_y:>+7.4f}  │ {fee_y:>6.1f}%  │")
    print(f"  │ Price decline (-Δln P)           │ {-d_p_y:>+7.4f}  │ {price_y:>6.1f}%  │")
    print(f"  │ Emission reduction (-Δln E/wk)   │ {-d_e_y:>+7.4f}  │ {emis_y:>6.1f}%  │")
    print(f"  ├─────────────────────────────────┼──────────┼──────────┤")
    print(f"  │ Total                            │ {d_bme_usd_y:>+7.4f}  │ {fee_y+price_y+emis_y:>6.1f}%  │")
    print(f"  └─────────────────────────────────┴──────────┴──────────┘")

    # ── Counterfactuals for 1-year window ────────────────────────
    # Use per-week rates so start/end week counts don't distort
    print(f"\n  COUNTERFACTUALS (1-year window, per-week rates):")
    cf_fee = (end["dc_burn_pw"] / start["hnt_price_avg"]) / end["hnt_issued_pw"]
    cf_price = (start["dc_burn_pw"] / end["hnt_price_avg"]) / end["hnt_issued_pw"]
    cf_emis = (end["dc_burn_pw"] / end["hnt_price_avg"]) / start["hnt_issued_pw"]
    cf_fee_alone = (end["dc_burn_pw"] / start["hnt_price_avg"]) / start["hnt_issued_pw"]

    print(f"    Fee only (hold price at ${start['hnt_price_avg']:.2f}):       "
          f"BME = {cf_fee:.3f} ({cf_fee/end['bme']:.0%} of actual)")
    print(f"    Price only (hold DC at ${start['dc_burn_pw']:,.0f}/wk): "
          f"BME = {cf_price:.3f} ({cf_price/end['bme']:.0%} of actual)")
    print(f"    Emission only (hold E at {start['hnt_issued_pw']:,.0f}/wk):  "
          f"BME = {cf_emis:.3f} ({cf_emis/end['bme']:.0%} of actual)")
    print(f"    Fee growth alone (all else @ start):    "
          f"BME = {cf_fee_alone:.3f}")

    # ── Rolling 3-month decomposition ────────────────────────────
    print(f"\n{'=' * 70}")
    print("ROLLING 3-MONTH ATTRIBUTION")
    print(f"{'=' * 70}")

    roll_rows = []
    for i in range(2, len(t12)):
        w = t12.iloc[i-2:i+1]
        curr_avg = w.tail(1)
        prev_3m = monthly[
            (monthly["month"] >= w["month"].iloc[0] - pd.DateOffset(months=3)) &
            (monthly["month"] < w["month"].iloc[0])
        ]
        if len(prev_3m) < 2:
            continue

        c_dc = w["dc_burn_pw"].mean()
        c_p = w["hnt_price_avg"].mean()
        c_e = w["hnt_issued_pw"].mean()
        c_bme = w["bme"].mean()
        p_dc = prev_3m["dc_burn_pw"].mean()
        p_p = prev_3m["hnt_price_avg"].mean()
        p_e = prev_3m["hnt_issued_pw"].mean()
        p_bme = prev_3m["bme"].mean()

        if p_bme <= 0 or c_bme <= 0 or p_dc <= 0 or c_dc <= 0:
            continue

        dl_bme = np.log(c_bme / p_bme)
        dl_dc = np.log(c_dc / p_dc)
        dl_p = np.log(c_p / p_p)
        dl_e = np.log(c_e / p_e)
        dl_bme_usd = dl_dc - dl_p - dl_e

        if abs(dl_bme_usd) > 0.01:
            roll_rows.append({
                "end_month": w["month"].iloc[-1],
                "bme_3m": c_bme,
                "fee_share": dl_dc / dl_bme_usd * 100,
                "price_share": -dl_p / dl_bme_usd * 100,
                "emission_share": -dl_e / dl_bme_usd * 100,
            })

    if roll_rows:
        roll = pd.DataFrame(roll_rows)
        print(f"\n  {'End Month':>10} {'BME_3m':>7} {'Fee%':>7} {'Price%':>8} {'Emis%':>7}")
        print(f"  {'─' * 44}")
        for _, r in roll.iterrows():
            print(f"  {r['end_month'].strftime('%Y-%m'):>10} "
                  f"{r['bme_3m']:>7.3f} "
                  f"{r['fee_share']:>6.0f}% "
                  f"{r['price_share']:>7.0f}% "
                  f"{r['emission_share']:>6.0f}%")

    # ── Chart: 3-panel (BME, components, attribution) ────────────
    # Include Feb 2025 as visible baseline so March's reference is explicit
    print(f"\n  Generating chart...")
    fig, axes = plt.subplots(3, 1, figsize=(10, 12),
                             gridspec_kw={"height_ratios": [2, 2, 1.5]})
    fig.suptitle("Helium BME: Trailing 12-Month Analysis (Feb 2025 – Feb 2026)",
                 fontsize=16, fontweight="bold", y=0.98)

    # full DataFrame: Feb 2025 (baseline) + 12 months Mar–Feb = 13 entries
    chart_df = full.copy().reset_index(drop=True)
    dates = chart_df["month"]
    x = range(len(dates))
    labels = [d.strftime("%b\n%y") for d in dates]

    # Panel A: BME trajectory (13 months, Feb baseline visible)
    ax = axes[0]
    bar_colors = []
    for i, b in enumerate(chart_df["bme"]):
        if i == 0:
            bar_colors.append("#999999")  # Feb baseline in grey
        elif b < 1:
            bar_colors.append("#003366")
        else:
            bar_colors.append("#339933")
    ax.bar(x, chart_df["bme"], color=bar_colors, alpha=0.8, width=0.7)
    ax.axhline(1.0, color="#CC3333", linestyle="--", linewidth=1.5, label="Parity (BME = 1.0)")
    ax.set_ylabel("BME (Burn / Emit)")
    ax.set_title("A. Monthly BME", fontsize=12, loc="left")
    ax.legend(loc="upper left", fontsize=10)
    # Identify halving index first so we can skip its value label
    halving_idx = None
    for i in range(len(chart_df)):
        if chart_df.iloc[i]["month"].month == 8 and chart_df.iloc[i]["month"].year == 2025:
            halving_idx = i
            break

    for i, b in enumerate(chart_df["bme"]):
        if i == 0:
            # Feb baseline: single label offset to the right to avoid overlap
            ax.annotate(f"{b:.3f}\n(baseline)", xy=(0, b),
                        xytext=(1.0, b + 0.15),
                        arrowprops=dict(arrowstyle="->", color="#999999", lw=0.8),
                        fontsize=7, color="#666666", ha="center", va="bottom")
        elif i == halving_idx:
            pass  # skip — halving annotation covers this bar
        elif b > 0.3:
            ax.text(i, b + 0.03, f"{b:.2f}", ha="center", va="bottom", fontsize=7.5)

    # Annotate halving (include BME value, place vertically above Aug bar)
    if halving_idx is not None:
        h_bme = chart_df.iloc[halving_idx]["bme"]
        ax.annotate(f"Emission halving\n(BME {h_bme:.2f})",
                     xy=(halving_idx, h_bme),
                     xytext=(halving_idx, h_bme + 0.45),
                     arrowprops=dict(arrowstyle="->", color="#CC3333"),
                     fontsize=8, color="#CC3333", ha="center")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)

    # Panel B: Three components (per-week rates, indexed to Feb 2025 = 100)
    ax = axes[1]
    base_dc = chart_df["dc_burn_pw"].iloc[0]
    base_p = chart_df["hnt_price_avg"].iloc[0]
    base_e = chart_df["hnt_issued_pw"].iloc[0]

    dc_idx = chart_df["dc_burn_pw"] / base_dc * 100
    p_idx = chart_df["hnt_price_avg"] / base_p * 100
    e_idx = chart_df["hnt_issued_pw"] / base_e * 100

    ax.plot(x, dc_idx, color="#339933", linewidth=2, marker="o", markersize=4,
            label=f"DC burn revenue (Feb: ${base_dc/1e3:.0f}K/wk)")
    ax.plot(x, p_idx, color="#CC3333", linewidth=2, marker="s", markersize=4,
            label=f"HNT price (Feb: ${base_p:.2f})")
    ax.plot(x, e_idx, color="#4682B4", linewidth=2, marker="^", markersize=4,
            label=f"HNT emission (Feb: {base_e/1e3:.0f}K/wk)")
    ax.axhline(100, color="gray", linestyle=":", linewidth=0.8)
    ax.set_ylabel("Index (Feb 2025 = 100)")
    ax.set_title("B. Component Trajectories — per-week rates (indexed to Feb 2025)",
                  fontsize=12, loc="left")
    ax.legend(loc="upper left", fontsize=10)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mticker.ScalarFormatter())
    ax.yaxis.set_minor_formatter(mticker.NullFormatter())
    ax.set_yticks([20, 50, 100, 200, 500, 1000])
    ax.set_ylim(10, 1500)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)

    # Panel C: MoM attribution bars (Feb baseline → Mar is the first bar)
    ax = axes[2]
    if len(mom) > 0:
        mom_12 = mom[mom["month"] >= "2025-03-01"].reset_index(drop=True)
        # Offset by 1 to align with Panel A/B (Feb is pos 0, Mar is pos 1)
        mx = [i + 1 for i in range(len(mom_12))]
        mlabels_c = [d.strftime("%b\n%y") for d in mom_12["month"]]

        # Clip extreme values for readability but keep all bars visible
        mom_plot = mom_12.copy()
        for col in ["fee_contrib_pct", "price_contrib_pct", "emission_contrib_pct"]:
            mom_plot[col] = mom_plot[col].clip(-200, 200)

        w = 0.25
        # Feb baseline at position 0: zero-height bars (no prior month to compare)
        ax.bar(0 - w, 0, width=w, color="#339933", alpha=0.3)
        ax.bar(0, 0, width=w, color="#CC3333", alpha=0.3)
        ax.bar(0 + w, 0, width=w, color="#4682B4", alpha=0.3)
        ax.annotate("Baseline", xy=(0, 0), xytext=(0, -15),
                    fontsize=7, color="#666666", ha="center")

        ax.bar([i - w for i in mx], mom_plot["fee_contrib_pct"], width=w,
               color="#339933", alpha=0.8, label="Fee growth")
        ax.bar([i for i in mx], mom_plot["price_contrib_pct"], width=w,
               color="#CC3333", alpha=0.8, label="Price decline")
        ax.bar([i + w for i in mx], mom_plot["emission_contrib_pct"], width=w,
               color="#4682B4", alpha=0.8, label="Emission reduction")
        ax.axhline(0, color="black", linewidth=0.5)
        ax.axvline(0.5, color="#CCCCCC", linestyle=":", linewidth=0.8)

        ax.set_ylabel("% of MoM BME change")
        ax.set_title("C. Month-over-Month Attribution (each bar vs. prior month)",
                      fontsize=12, loc="left")
        ax.legend(loc="upper center", fontsize=10, ncol=3)

        # Use full 13-position x axis matching panels A/B
        all_labels_c = [dates.iloc[0].strftime("Feb\n25")] + mlabels_c
        ax.set_xticks(range(len(all_labels_c)))
        ax.set_xticklabels(all_labels_c, fontsize=10)
    else:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=10)

    fig.text(0.02, 0.005,
             "Source: Dune Analytics (weekly HNT burns, issuance, volume). "
             "Decomposition uses per-week rates: Δln(BME) ≈ Δln(DC/wk) − Δln(P) − Δln(E/wk).",
             fontsize=8, fontstyle="italic", color="#666666")
    fig.tight_layout(rect=[0, 0.02, 1, 0.96])

    chart_path = OUTPUT_DIR / "exhibit_bme_12month_analysis.png"
    fig.savefig(chart_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved chart: {chart_path}")

    # ── Save JSON ────────────────────────────────────────────────
    results = {
        "analysis": "trailing_12_month",
        "window": f"{t12['month'].iloc[0].strftime('%Y-%m')} to {t12['month'].iloc[-1].strftime('%Y-%m')}",
        "start_bme": round(float(start["bme"]), 4),
        "end_bme": round(float(end["bme"]), 4),
        "bme_growth_x": round(float(end["bme"] / start["bme"]), 1),
        "decomposition_12m": {
            "method": "per-week rates, USD-consistent denominator",
            "fee_growth_pct": round(float(fee_y), 1),
            "price_decline_pct": round(float(price_y), 1),
            "emission_reduction_pct": round(float(emis_y), 1),
            "sum_check_pct": round(float(fee_y + price_y + emis_y), 1),
        },
        "phases": phases,
        "counterfactuals_12m": {
            "fee_only_bme": round(float(cf_fee), 3),
            "price_only_bme": round(float(cf_price), 3),
            "emission_only_bme": round(float(cf_emis), 3),
            "fee_alone_bme": round(float(cf_fee_alone), 3),
        },
        "monthly_detail": mom.assign(
            month=mom["month"].dt.strftime("%Y-%m")
        ).to_dict(orient="records"),
    }

    json_path = OUTPUT_DIR / "helium_bme_12month.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  Saved: {json_path}")

    # ── Narrative summary ────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("NARRATIVE SUMMARY")
    print(f"{'=' * 70}")
    print(f"""
  Over the trailing 12 months (Mar 2025 – Feb 2026), Helium's BME
  rose from {start['bme']:.3f} to {end['bme']:.2f} ({end['bme']/start['bme']:.0f}×).

  Three distinct phases:

  1. PRE-HALVING BASELINE (Mar–Jul 2025): BME averaged {phases[0]['bme_mean']:.3f}.
     DC burn revenue was volatile (${phases[0]['dc_mean']/1e3:.0f}K/mo avg) with a
     $2.16M spike in June. Price: ${phases[0]['price_mean']:.2f}. Emissions: ~{phases[0]['emission_mean']/1e6:.1f}M/mo.

  2. HALVING TRANSITION (Aug–Sep 2025): BME jumped to {phases[1]['bme_mean']:.3f}.
     Emissions dropped by ~{1 - phases[1]['emission_mean']/phases[0]['emission_mean']:.0%} to ~{phases[1]['emission_mean']/1e3:.0f}K/mo.
     DC burns held above $1M/mo. This is the structural break.

  3. POST-HALVING MATURITY (Oct 2025 – Feb 2026): BME averaged {phases[2]['bme_mean']:.2f},
     consistently above parity. DC revenue averaged ${phases[2]['dc_mean']/1e3:.0f}K/mo.
     Price fell from ${t12[t12['month']=='2025-10-01']['hnt_price_avg'].iloc[0]:.2f} to ${end['hnt_price_avg']:.2f}.

  12-MONTH DECOMPOSITION (per-week rates, sums to 100%):
    Fee growth:          {fee_y:.0f}% — DC burn/wk rose ${start['dc_burn_pw']:,.0f} → ${end['dc_burn_pw']:,.0f}
    Price decline:       {price_y:.0f}% — HNT fell ${start['hnt_price_avg']:.2f} → ${end['hnt_price_avg']:.2f}
    Emission reduction:  {emis_y:.0f}% — E/wk fell {start['hnt_issued_pw']:,.0f} → {end['hnt_issued_pw']:,.0f}

  The halving was the single most important structural event. Without it
  (holding weekly emission rate at Mar 2025 levels), BME would be {cf_emis:.2f}
  instead of {end['bme']:.2f}. Fee growth alone (all else at start) would
  have produced BME = {cf_fee_alone:.3f}.
""")

if __name__ == "__main__":
    main()
