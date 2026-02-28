#!/usr/bin/env python3
"""
Generate merged ensemble exhibit: Competitor Entry, nodes + price.
Paper Exhibit 20 (new numbering).
"""
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from exhibit_style import (
    COLORS, SCENARIO_COLORS, setup_style, hide_spines,
    save_exhibit, add_source, EXHIBITS_DIR
)

ROOT = Path(__file__).resolve().parent.parent
setup_style()

ms = pd.read_csv(ROOT / "results" / "multi_seed_results.csv")
comp = ms[ms['scenario'] == 'competitor']
pid = comp[comp['emission_model'] == 'pid']
static = comp[comp['emission_model'] == 'static']

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))
fig.suptitle("Ensemble Distributions Under Competitor Entry (30 Seeds per Model)",
             fontsize=14, fontweight='bold', y=0.98)

# Verification targets
TARGETS = {
    'final_N': {'pid_cv': 0.087, 'pid_p5': 8880, 'static_cv': 0.544, 'static_p5': 1049},
    'final_P': {'pid_cv': 0.532, 'pid_p5': 1.09, 'static_cv': 0.921, 'static_p5': 0.04},
}

for ax, col, label, fmt_p5, yscale, target in [
    (ax1, 'final_N', 'Panel A. Node Count', '{:,.0f}', 'linear', 10000),
    (ax2, 'final_P', 'Panel B. Token Price', '${:.2f}', 'log', None),
]:
    pid_data = pid[col].values
    static_data = static[col].values

    bp = ax.boxplot(
        [pid_data, static_data], positions=[0, 1], widths=0.5,
        patch_artist=True, showfliers=True,
        flierprops=dict(marker='o', markersize=4, alpha=0.4),
        whiskerprops=dict(linewidth=1.5),
        capprops=dict(linewidth=1.5),
    )
    for i, box in enumerate(bp['boxes']):
        box.set_facecolor(COLORS['accent6'] if i == 0 else COLORS['mid_gray'])
        box.set_alpha(0.7 if i == 0 else 0.5)
        box.set_linewidth(1)
        box.set_zorder(2)
    for whisker in bp['whiskers']:
        whisker.set_color('black')
        whisker.set_linewidth(1.5)
        whisker.set_zorder(3)
    for median in bp['medians']:
        median.set_color('white')
        median.set_linewidth(4)
        median.set_zorder(5)
    for cap in bp['caps']:
        cap.set_color('black')
        cap.set_linewidth(1.5)
        cap.set_zorder(6)

    # When median==Q3 the white median hides the box top border.
    # Redraw box top edge + stub whisker + cap on top of everything.
    box_width = 0.5
    for i, data in enumerate([pid_data, static_data]):
        q3 = np.percentile(data, 75)
        med = np.median(data)
        dmax = data.max()
        pos = [0, 1][i]
        half_bw = box_width / 2
        # If median sits at Q3, redraw the box top border above the white line
        if med == q3:
            ax.plot([pos - half_bw, pos + half_bw], [q3, q3],
                    color='black', linewidth=1, zorder=7, solid_capstyle='butt')

    if target:
        ax.axhline(target, color=COLORS['accent2'], ls='--', lw=1, alpha=0.5)
        ax.text(-0.32, target + 1100, f'{target:,}\ntarget', fontsize=7,
                color=COLORS['accent2'], va='center', ha='right')

    if yscale == 'log':
        ax.set_yscale('log')

    # Ensure box caps are clearly visible — set ylim with headroom
    all_data = np.concatenate([pid_data, static_data])
    if yscale == 'linear':
        lo, hi = all_data.min(), all_data.max()
        pad = (hi - lo) * 0.10
        ax.set_ylim(max(0, lo - pad), hi + pad)
    else:
        ax.set_ylim(auto=True)

    pid_cv = np.std(pid_data, ddof=1) / pid_data.mean() if pid_data.mean() > 0 else 0
    static_cv = np.std(static_data, ddof=1) / static_data.mean() if static_data.mean() > 0 else 0
    pid_p5 = np.percentile(pid_data, 5)
    static_p5 = np.percentile(static_data, 5)

    ax.set_xticks([0, 1])
    ax.set_xticklabels([
        f"PID\nCV={pid_cv:.3f}, p5={fmt_p5.format(pid_p5)}",
        f"Static\nCV={static_cv:.3f}, p5={fmt_p5.format(static_p5)}",
    ], fontsize=9)

    ylabel = "Final Node Count" if col == 'final_N' else "$MESH Price ($)"
    ax.set_ylabel(ylabel)
    ax.set_title(label, loc='left', fontsize=11, fontweight='bold',
                 color=SCENARIO_COLORS['competitor'])
    hide_spines(ax)

    # Print verification
    print(f"{label}: PID CV={pid_cv:.3f}, p5={fmt_p5.format(pid_p5)}; "
          f"Static CV={static_cv:.3f}, p5={fmt_p5.format(static_p5)}")

    # Check against targets
    t = TARGETS[col]
    for name, computed, expected in [
        ('PID CV', pid_cv, t['pid_cv']),
        ('PID p5', pid_p5, t['pid_p5']),
        ('Static CV', static_cv, t['static_cv']),
        ('Static p5', static_p5, t['static_p5']),
    ]:
        if expected != 0 and abs(computed - expected) / abs(expected) > 0.05:
            print(f"  WARNING: {label} {name} = {computed:.4f}, expected ~{expected}")

fig.tight_layout(rect=[0, 0.04, 1, 0.93])
add_source(fig, "Source: MeshNet 240-run ensemble (30 seeds \u00d7 8 configurations). "
           "Competitor entry: 25% operator poach at month 18, 30% cost increase.")
save_exhibit(fig, "exhibit_20_ensemble_competitor.png")

print("\nDone. Output: exhibits/exhibit_20_ensemble_competitor.png")
