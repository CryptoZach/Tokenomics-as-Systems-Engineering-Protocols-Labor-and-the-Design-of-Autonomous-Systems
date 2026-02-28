#!/usr/bin/env python3
"""
House style and shared utilities for all exhibits.
"""
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from pathlib import Path

EXHIBITS_DIR = Path(__file__).resolve().parent.parent / "exhibits"
EXHIBITS_DIR.mkdir(parents=True, exist_ok=True)

COLORS = {
    'primary': '#1a1a2e',
    'secondary': '#16213e',
    'accent1': '#0f3460',
    'accent2': '#e94560',
    'accent3': '#533483',
    'accent4': '#2b9348',
    'accent5': '#f77f00',
    'accent6': '#4895ef',
    'grid': '#e0e0e0',
    'text': '#1a1a2e',
    'bg': '#ffffff',
    'light_gray': '#f5f5f5',
    'mid_gray': '#999999',
}

SCENARIO_COLORS = {
    'bull': '#2b9348',
    'bear': '#e94560',
    'competitor': '#f77f00',
    'regulatory': '#533483',
}

def setup_style():
    plt.rcParams.update({
        'figure.facecolor': COLORS['bg'],
        'axes.facecolor': COLORS['bg'],
        'axes.edgecolor': COLORS['grid'],
        'axes.grid': True,
        'grid.alpha': 0.3,
        'grid.color': COLORS['grid'],
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': 11,
        'axes.titlesize': 16,
        'axes.titleweight': 'bold',
        'axes.labelsize': 12,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'legend.fontsize': 10,
        'figure.titlesize': 16,
        'figure.titleweight': 'bold',
        'figure.dpi': 150,
        'savefig.dpi': 300,
        'legend.framealpha': 0.9,
        'legend.edgecolor': COLORS['grid'],
    })

def hide_spines(ax, keep_left=True, keep_bottom=True):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    if not keep_left:
        ax.spines['left'].set_visible(False)
    if not keep_bottom:
        ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_color(COLORS['grid'])
    ax.spines['bottom'].set_color(COLORS['grid'])

def save_exhibit(fig, name):
    path = EXHIBITS_DIR / name
    fig.savefig(path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"  Saved: {path.name}")

def add_source(fig, text="Source: MeshNet simulation (seed=42)."):
    fig.text(0.02, 0.01, text, fontsize=8, color=COLORS['mid_gray'],
             fontstyle='italic', transform=fig.transFigure)
