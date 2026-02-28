#!/usr/bin/env python3
"""
Data loader for MeshNet simulation calibration.
Parses Helium on-chain data, governance metrics, and price data
from the DePIN dataset.
"""
import json
import pandas as pd
import numpy as np
from pathlib import Path

# ── Data paths ────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
DEPIN_THESIS = BASE.parent / "depin-thesis"
DEPIN_DATA = DEPIN_THESIS / "data"

PATHS = {
    "weekly_burns": DEPIN_DATA / "helium" / "dune_hnt_weekly_burns.json",
    "weekly_issuance": DEPIN_DATA / "helium" / "dune_hnt_weekly_issuance.json",
    "s2r_cleaned": DEPIN_DATA / "helium_validation" / "helium_s2r_CLEANED.csv",
    "hnt_price": DEPIN_DATA / "helium" / "hnt_daily_price.csv",
    "hnt_current": DEPIN_DATA / "helium" / "hnt_current_data.json",
    "governance": DEPIN_DATA / "governance_v2" / "governance_hhi_gini_CORRECTED.csv",
    "gov_qualitative": DEPIN_DATA / "governance" / "governance_hhi_gini_CORRECTED.csv",
    "protocol_profiles": DEPIN_DATA / "expansion" / "consolidated_expansion_results.json",
}


def _parse_dune_json(path: Path) -> pd.DataFrame:
    """Parse Dune Analytics JSON response format."""
    with open(path) as f:
        data = json.load(f)
    rows = data.get("result", {}).get("rows", [])
    if not rows:
        raise ValueError(f"No rows found in {path}")
    df = pd.DataFrame(rows)
    if "week" in df.columns:
        df["week"] = pd.to_datetime(df["week"])
        df = df.sort_values("week").reset_index(drop=True)
    return df


def load_weekly_burns() -> pd.DataFrame:
    """Load weekly HNT burn data (149 weeks)."""
    df = _parse_dune_json(PATHS["weekly_burns"])
    return df[["week", "hnt_burned", "usd_burned", "burn_txns"]]


def load_weekly_issuance() -> pd.DataFrame:
    """Load weekly HNT issuance data (149 weeks)."""
    df = _parse_dune_json(PATHS["weekly_issuance"])
    cols = [c for c in ["week", "hnt_issued", "usd_issued"] if c in df.columns]
    return df[cols]


def load_s2r_cleaned() -> pd.DataFrame:
    """Load cleaned monthly S2R data (35 months)."""
    df = pd.read_csv(PATHS["s2r_cleaned"])
    df["period"] = pd.to_datetime(df["period"])
    # Filter out migration month (April 2023)
    df = df[df["period"] >= "2023-05-01"].reset_index(drop=True)
    return df


def load_hnt_price() -> pd.DataFrame:
    """Load daily HNT price data."""
    df = pd.read_csv(PATHS["hnt_price"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def load_hnt_current() -> dict:
    """Load current HNT supply/market snapshot."""
    with open(PATHS["hnt_current"]) as f:
        return json.load(f)


def load_governance() -> pd.DataFrame:
    """Load corrected governance concentration metrics (DeFi + DePIN protocols)."""
    df = pd.read_csv(PATHS["governance"])
    # Drop rows with no HHI data
    df = df.dropna(subset=["hhi"]).reset_index(drop=True)
    # Ensure category column exists (backward compat)
    if "category" not in df.columns:
        df["category"] = "defi"
    return df


def load_all() -> dict:
    """Load all data sources. Returns dict of DataFrames/dicts."""
    data = {}
    loaders = {
        "weekly_burns": load_weekly_burns,
        "weekly_issuance": load_weekly_issuance,
        "s2r_cleaned": load_s2r_cleaned,
        "hnt_price": load_hnt_price,
        "hnt_current": load_hnt_current,
        "governance": load_governance,
    }
    for name, loader in loaders.items():
        try:
            data[name] = loader()
            if isinstance(data[name], pd.DataFrame):
                print(f"  {name}: {len(data[name])} rows")
            else:
                print(f"  {name}: loaded (dict)")
        except Exception as e:
            print(f"  {name}: FAILED — {e}")
            data[name] = None
    return data


if __name__ == "__main__":
    print("Loading all data sources...\n")
    data = load_all()
    print(f"\nLoaded {sum(1 for v in data.values() if v is not None)}/{len(data)} sources")
