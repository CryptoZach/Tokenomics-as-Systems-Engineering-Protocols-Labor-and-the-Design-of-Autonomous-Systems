"""
Figure 2 / Exhibit 9: Helium BME ratio trajectory, May 2023 – Feb 2026.
Burns-only monthly snapshots from Dune Analytics on-chain data.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from pathlib import Path

plt.rcParams['font.family'] = 'sans-serif'

# ── Load actual on-chain data ────────────────────────────────
csv_path = Path(__file__).resolve().parent.parent / "data" / "helium" / "helium_bme_monthly.csv"
df = pd.read_csv(csv_path)
df["date"] = pd.to_datetime(df["month"])
df = df.rename(columns={"bme": "s2r"})

# Filter to May 2023 onward (post-Solana migration; Apr 2023 is anomalous)
df = df[df["date"] >= "2023-05-01"].copy()
df = df.sort_values("date").reset_index(drop=True)

# ── Color palette (matches Figure 1 GeoDePIN color) ─────────
COLOR_MAIN = "#D94A4A"
COLOR_FILL = "#D94A4A"
COLOR_THRESHOLD = "#333333"
COLOR_REGIME_1 = "#4A90D9"   # Subsidy-dependent (blue tint)
COLOR_REGIME_2 = "#F5A623"   # Transitional (amber tint)
COLOR_REGIME_3 = "#7ED321"   # Net-deflationary (green tint)
COLOR_EVENT = "#555555"

# ── Build figure ─────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5.5))

# Regime background shading
regime_alpha = 0.06
ax.axvspan(pd.Timestamp("2023-05-01"), pd.Timestamp("2025-05-31"),
           color=COLOR_REGIME_1, alpha=regime_alpha, zorder=0)
ax.axvspan(pd.Timestamp("2025-06-01"), pd.Timestamp("2025-09-30"),
           color=COLOR_REGIME_2, alpha=regime_alpha, zorder=0)
ax.axvspan(pd.Timestamp("2025-10-01"), pd.Timestamp("2026-05-01"),
           color=COLOR_REGIME_3, alpha=regime_alpha, zorder=0)

# Regime labels (positioned inside each zone, near top)
label_y = 2.30
ax.text(pd.Timestamp("2024-05-01"), label_y, "Subsidy-dependent",
        fontsize=8, color=COLOR_REGIME_1, alpha=0.7, ha="center", va="top",
        fontstyle="italic", clip_on=False)
ax.text(pd.Timestamp("2025-08-01"), label_y, "Transitional",
        fontsize=8, color=COLOR_REGIME_2, alpha=0.8, ha="center", va="top",
        fontstyle="italic", clip_on=False)
ax.text(pd.Timestamp("2026-01-15"), 2.30, "Net-deflationary",
        fontsize=8, color=COLOR_REGIME_3, alpha=0.8, ha="center", va="top",
        fontstyle="italic", clip_on=False)

# S2R = 1.0 fiscal parity line
ax.axhline(y=1.0, color=COLOR_THRESHOLD, linewidth=1.0, linestyle="--",
           alpha=0.6, zorder=2)
ax.text(df["date"].iloc[0] + pd.Timedelta(days=15), 1.05,
        "Fiscal parity (BME = 1.0)", fontsize=8.5, color=COLOR_THRESHOLD,
        alpha=0.7, va="bottom")

# Main S2R line + area fill
ax.plot(df["date"], df["s2r"], color=COLOR_MAIN, linewidth=2.2,
        zorder=4, solid_capstyle="round")
ax.fill_between(df["date"], 0, df["s2r"], color=COLOR_FILL, alpha=0.15,
                zorder=3)

# Data point markers
ax.scatter(df["date"], df["s2r"], color=COLOR_MAIN, s=24, zorder=5,
           edgecolors="white", linewidths=0.6)

# ── Event annotations (3 key events) ────────────────────────
events = [
    (pd.Timestamp("2023-06-15"), "Solana\nmigration", 30, 30),
    (pd.Timestamp("2025-09-30"), "HIP-147\npasses", -50, 88),
    (pd.Timestamp("2025-10-31"), "BME > 1.0\n(first time)", 30, -29),
]

for edate, elabel, x_off, y_off in events:
    # Vertical marker line
    ax.axvline(x=edate, color=COLOR_EVENT, linewidth=0.7, linestyle=":",
               alpha=0.4, zorder=1)
    # Find y value at this date
    match = df.loc[df["date"] == edate, "s2r"]
    if len(match) > 0:
        yval = match.iloc[0]
    else:
        yval = 0.5
    ax.annotate(
        elabel,
        xy=(edate, yval),
        xytext=(x_off, y_off),
        textcoords="offset points",
        fontsize=8, color=COLOR_EVENT,
        ha="center", va="bottom",
        arrowprops=dict(arrowstyle="-", color=COLOR_EVENT, alpha=0.5,
                        linewidth=0.8),
    )

# ── Axes formatting ──────────────────────────────────────────
ax.set_ylabel("BME Ratio (burns ÷ emissions)", fontsize=12)
ax.set_ylim(-0.05, 2.25)
ax.set_xlim(pd.Timestamp("2023-04-15"), pd.Timestamp("2026-06-01"))

# X-axis: monthly locator, show every 3 months
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
plt.setp(ax.xaxis.get_majorticklabels(), rotation=35, ha="right", fontsize=10)

# Y-axis
ax.yaxis.set_major_locator(mticker.MultipleLocator(0.5))
ax.yaxis.set_minor_locator(mticker.MultipleLocator(0.25))
ax.tick_params(axis="y", labelsize=10)

# Grid: light horizontal only
ax.grid(axis="y", color="#E0E0E0", linewidth=0.5, alpha=0.7)
ax.grid(axis="x", visible=False)

# Spines: hide top and right (match Figure 1)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_color("#AAAAAA")
ax.spines["bottom"].set_color("#AAAAAA")

fig.suptitle(
    "Helium BME: From Subsidy-Dependence to Net Deflation (May 2023 \u2013 Feb 2026)",
    fontsize=16, fontweight="bold", y=0.98
)
fig.tight_layout(rect=[0, 0, 1, 0.95])

# ── Save ─────────────────────────────────────────────────────
base = Path(__file__).resolve().parent.parent
out_primary = base / "exhibits" / "figure2_s2r_timeline.png"
fig.savefig(out_primary, dpi=300, bbox_inches="tight", pad_inches=0.15, facecolor="white")

out_exhibit = base / "exhibits" / "exhibit_08_s2r_timeline.png"
fig.savefig(out_exhibit, dpi=300, bbox_inches="tight", pad_inches=0.15, facecolor="white")

from PIL import Image
img = Image.open(out_primary)
print(f"Saved: {out_primary}  ({out_primary.stat().st_size / 1024:.0f} KB, {img.size[0]}×{img.size[1]} px)")
print(f"Saved: {out_exhibit}  ({out_exhibit.stat().st_size / 1024:.0f} KB)")

plt.close(fig)
