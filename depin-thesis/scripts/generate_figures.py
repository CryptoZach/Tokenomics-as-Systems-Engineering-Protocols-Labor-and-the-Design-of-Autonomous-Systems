#!/usr/bin/env python3
"""
Generate publication figures for both papers.

Figure 1 (Paper 1): Horizontal bar chart of HHI across 12 protocols.
Figure 2 (Paper 2): Helium S2R timeline (34 months) with fiscal regimes.

Usage:
    python generate_figures.py [--data-dir DATA_DIR] [--output-dir OUTPUT_DIR]

If no arguments, reads from data/ and writes to data/.
Pass --use-expected to generate from expected_results.csv (no Dune export needed).
"""
import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd


# ── Style constants (shared across both figures) ─────────────
COLOR_DEPIN = "#D94A4A"
COLOR_DEFI = "#4A90D9"
COLOR_THRESHOLD = "#333333"
SPINE_COLOR = "#AAAAAA"
DPI = 300
FIG_WIDTH = 10


def setup_style():
    """Configure matplotlib for clean academic charts."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "figure.dpi": DPI,
        "savefig.dpi": DPI,
    })


def hide_spines(ax):
    """Hide top and right spines, lighten remaining."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(SPINE_COLOR)
    ax.spines["bottom"].set_color(SPINE_COLOR)


# ═════════════════════════════════════════════════════════════
# FIGURE 1: HHI Horizontal Bar Chart
# ═════════════════════════════════════════════════════════════

# Expected values from February 2026 snapshot (Table 2, Pub1)
EXPECTED_HHI = {
    "Compound":  {"hhi": 0.028, "category": "DeFi"},
    "Anyone":    {"hhi": 0.034, "category": "GeoDePIN"},
    "MakerDAO":  {"hhi": 0.045, "category": "DeFi"},
    "Aave":      {"hhi": 0.052, "category": "DeFi"},
    "The Graph": {"hhi": 0.105, "category": "DeFi"},
    "Uniswap":   {"hhi": 0.114, "category": "DeFi"},
    "Grass":     {"hhi": 0.119, "category": "GeoDePIN"},
    "Optimism":  {"hhi": 0.131, "category": "DeFi"},
    "Curve":     {"hhi": 0.174, "category": "DeFi"},
    "DIMO":      {"hhi": 0.305, "category": "GeoDePIN"},
    "IoTeX":     {"hhi": 0.388, "category": "GeoDePIN"},
    "WeatherXM": {"hhi": 0.593, "category": "GeoDePIN"},
}


def generate_figure1(data_dir: Path, output_dir: Path, use_expected: bool = False):
    """Generate Figure 1: HHI bar chart."""
    print("Generating Figure 1: HHI bar chart...")

    if use_expected or not (data_dir / "governance_concentration.csv").exists():
        # Use built-in expected values
        protocols = list(EXPECTED_HHI.keys())
        hhi_vals = [EXPECTED_HHI[p]["hhi"] for p in protocols]
        categories = [EXPECTED_HHI[p]["category"] for p in protocols]
    else:
        df = pd.read_csv(data_dir / "governance_concentration.csv")
        df = df.sort_values("hhi")
        protocols = df["protocol"].tolist()
        hhi_vals = df["hhi"].tolist()
        # Map to categories (customize as needed)
        defi_set = {"Compound", "MakerDAO", "Aave", "Curve", "Uniswap",
                     "The Graph", "Optimism"}
        categories = [
            "DeFi" if p in defi_set else "GeoDePIN" for p in protocols
        ]

    colors = [COLOR_DEFI if c == "DeFi" else COLOR_DEPIN for c in categories]

    fig, ax = plt.subplots(figsize=(FIG_WIDTH, 6))

    y_pos = np.arange(len(protocols))
    bars = ax.barh(y_pos, hhi_vals, color=colors, height=0.65, zorder=3)

    # Value labels
    for bar, val in zip(bars, hhi_vals):
        ax.text(
            bar.get_width() + 0.008, bar.get_y() + bar.get_height() / 2,
            f"{val:.3f}", va="center", ha="left", fontsize=8.5, color="#333333",
        )

    # HHI = 0.25 threshold
    ax.axvline(x=0.25, color=COLOR_THRESHOLD, linewidth=1.0, linestyle="--",
               alpha=0.6, zorder=2)
    ax.text(0.255, len(protocols) - 0.5,
            "Highly concentrated\n(HHI = 0.25)",
            fontsize=8.5, color=COLOR_THRESHOLD, alpha=0.7, va="top")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(protocols, fontsize=10)
    ax.set_xlabel("Herfindahl-Hirschman Index (HHI)", fontsize=11)
    ax.set_xlim(0, max(hhi_vals) * 1.25)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=COLOR_DEFI, label="DeFi"),
        Patch(facecolor=COLOR_DEPIN, label="GeoDePIN"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=9,
              frameon=True, fancybox=False, edgecolor="#CCCCCC")

    ax.grid(axis="x", color="#E0E0E0", linewidth=0.5, alpha=0.7, zorder=0)
    ax.grid(axis="y", visible=False)
    hide_spines(ax)

    fig.tight_layout()
    out_path = output_dir / "figure1_hhi_bar_chart.png"
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {out_path}")


# ═════════════════════════════════════════════════════════════
# FIGURE 2: Helium S2R Timeline
# ═════════════════════════════════════════════════════════════

# Expected S2R values (Table 2, 34 months)
EXPECTED_S2R = [
    ("2023-05-31", 0.0129), ("2023-06-30", 0.0311), ("2023-07-31", 0.0266),
    ("2023-08-31", 0.0469), ("2023-09-30", 0.1185), ("2023-10-31", 0.0625),
    ("2023-11-30", 0.0242), ("2023-12-31", 0.0336), ("2024-01-31", 0.0518),
    ("2024-02-29", 0.0339), ("2024-03-31", 0.0332), ("2024-04-30", 0.0318),
    ("2024-05-31", 0.0374), ("2024-06-30", 0.0242), ("2024-07-31", 0.0412),
    ("2024-08-31", 0.0067), ("2024-09-30", 0.0362), ("2024-10-31", 0.0223),
    ("2024-11-30", 0.1371), ("2024-12-31", 0.0040), ("2025-01-31", 0.0064),
    ("2025-02-28", 0.0991), ("2025-03-31", 0.1068), ("2025-04-30", 0.0098),
    ("2025-05-31", 0.0245), ("2025-06-30", 0.3764), ("2025-07-31", 0.0737),
    ("2025-08-31", 0.8686), ("2025-09-30", 0.5873), ("2025-10-31", 1.5696),
    ("2025-11-30", 0.8773), ("2025-12-31", 1.5517), ("2026-01-31", 1.1027),
    ("2026-02-28", 2.0597),
]


def generate_figure2(data_dir: Path, output_dir: Path, use_expected: bool = False):
    """Generate Figure 2: Helium S2R timeline."""
    print("Generating Figure 2: S2R timeline...")

    if use_expected or not (data_dir / "s2r_computed.csv").exists():
        dates = [pd.Timestamp(d) for d, _ in EXPECTED_S2R]
        s2r_vals = [v for _, v in EXPECTED_S2R]
    else:
        df = pd.read_csv(data_dir / "s2r_computed.csv", parse_dates=["month"])
        dates = df["month"].tolist()
        s2r_vals = df["s2r"].tolist()

    # Regime zone colors
    COLOR_REGIME_1 = "#4A90D9"  # Subsidy-dependent
    COLOR_REGIME_2 = "#F5A623"  # Transitional
    COLOR_REGIME_3 = "#7ED321"  # Net-deflationary

    fig, ax = plt.subplots(figsize=(FIG_WIDTH, 5.5))

    # Background regime shading
    regime_alpha = 0.06
    ax.axvspan(pd.Timestamp("2023-05-01"), pd.Timestamp("2025-05-31"),
               color=COLOR_REGIME_1, alpha=regime_alpha, zorder=0)
    ax.axvspan(pd.Timestamp("2025-06-01"), pd.Timestamp("2025-09-30"),
               color=COLOR_REGIME_2, alpha=regime_alpha, zorder=0)
    ax.axvspan(pd.Timestamp("2025-10-01"), pd.Timestamp("2026-03-31"),
               color=COLOR_REGIME_3, alpha=regime_alpha, zorder=0)

    # Regime labels
    label_y = 2.10
    ax.text(pd.Timestamp("2024-05-01"), label_y, "Subsidy-dependent",
            fontsize=8, color=COLOR_REGIME_1, alpha=0.7, ha="center",
            va="top", fontstyle="italic")
    ax.text(pd.Timestamp("2025-08-01"), label_y, "Transitional",
            fontsize=8, color=COLOR_REGIME_2, alpha=0.8, ha="center",
            va="top", fontstyle="italic")
    ax.text(pd.Timestamp("2025-12-15"), label_y, "Net-deflationary",
            fontsize=8, color=COLOR_REGIME_3, alpha=0.8, ha="center",
            va="top", fontstyle="italic")

    # Fiscal parity line
    ax.axhline(y=1.0, color=COLOR_THRESHOLD, linewidth=1.0, linestyle="--",
               alpha=0.6, zorder=2)
    ax.text(dates[0] + pd.Timedelta(days=15), 1.05,
            "Fiscal parity (S2R = 1.0)", fontsize=8.5,
            color=COLOR_THRESHOLD, alpha=0.7, va="bottom")

    # S2R line + area fill
    ax.plot(dates, s2r_vals, color=COLOR_DEPIN, linewidth=2.2,
            zorder=4, solid_capstyle="round")
    ax.fill_between(dates, 0, s2r_vals, color=COLOR_DEPIN, alpha=0.15,
                    zorder=3)
    ax.scatter(dates, s2r_vals, color=COLOR_DEPIN, s=24, zorder=5,
               edgecolors="white", linewidths=0.6)

    # Event annotations
    events = [
        (pd.Timestamp("2023-05-31"), "Solana\nmigration", -40, 30),
        (pd.Timestamp("2025-09-30"), "HIP-147\npasses", -40, 30),
        (pd.Timestamp("2025-10-31"), "S2R > 1.0\n(first time)", 20, 30),
    ]
    for edate, elabel, x_off, y_off in events:
        idx = min(range(len(dates)), key=lambda i: abs(dates[i] - edate))
        yval = s2r_vals[idx]
        ax.axvline(x=edate, color="#555555", linewidth=0.7, linestyle=":",
                   alpha=0.4, zorder=1)
        ax.annotate(
            elabel, xy=(edate, yval), xytext=(x_off, y_off),
            textcoords="offset points", fontsize=8, color="#555555",
            ha="center", va="bottom",
            arrowprops=dict(arrowstyle="-", color="#555555", alpha=0.5,
                            linewidth=0.8),
        )

    # Axes
    ax.set_ylabel("Spend-to-Reward Ratio (burns only)", fontsize=11)
    ax.set_ylim(-0.05, 2.25)
    ax.set_xlim(pd.Timestamp("2023-04-15"), pd.Timestamp("2026-03-15"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=35, ha="right",
             fontsize=9)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(0.5))
    ax.yaxis.set_minor_locator(mticker.MultipleLocator(0.25))
    ax.tick_params(axis="y", labelsize=9.5)

    ax.grid(axis="y", color="#E0E0E0", linewidth=0.5, alpha=0.7)
    ax.grid(axis="x", visible=False)
    hide_spines(ax)

    fig.tight_layout()
    out_path = output_dir / "figure2_s2r_timeline.png"
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {out_path}")


# ═════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Generate publication figures for both papers."
    )
    parser.add_argument(
        "--data-dir", type=Path, default=Path("data"),
        help="Directory containing input CSVs (default: data/)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data"),
        help="Directory for output PNGs (default: data/)",
    )
    parser.add_argument(
        "--use-expected", action="store_true",
        help="Use built-in expected values instead of CSV data",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    setup_style()

    generate_figure1(args.data_dir, args.output_dir, args.use_expected)
    generate_figure2(args.data_dir, args.output_dir, args.use_expected)

    print("\nAll figures generated successfully.")


if __name__ == "__main__":
    main()
