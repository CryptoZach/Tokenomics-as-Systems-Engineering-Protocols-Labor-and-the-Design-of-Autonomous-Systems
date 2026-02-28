#!/usr/bin/env python3
"""
Merge DePIN governance data into governance_hhi_gini_CORRECTED.csv.
Combines:
- Existing 7 DeFi protocols (unchanged)
- 2 new DePIN protocols (RENDER, AKT from collect_depin_governance.py)
- 3 existing expansion protocols (DIMO, IoTeX, Grass from expansion/data/)
Adds category column (defi/depin).
"""
import os
import json
import pandas as pd
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
GOV_V2_DIR = os.path.join(DATA_DIR, "governance_v2")
EXPANSION_DIR = os.path.join(DATA_DIR, "expansion")

# ── Load existing DeFi data (7 protocols) ──────────────────────
corrected_path = os.path.join(GOV_V2_DIR, "governance_hhi_gini_CORRECTED.csv")
defi_df = pd.read_csv(corrected_path)

print("=" * 70)
print("MERGE DePIN INTO GOVERNANCE CSV")
print("=" * 70)

# Verify existing DeFi rows
defi_valid = defi_df.dropna(subset=["hhi"])
print(f"\nExisting DeFi protocols (unchanged): {len(defi_valid)}")
for _, r in defi_valid.iterrows():
    print(f"  {r['protocol']:<15} HHI={r['hhi']:.6f}  Gini={r['gini']:.4f}")

# Add category column
defi_valid = defi_valid.copy()
defi_valid["category"] = "defi"
defi_valid["snapshot_date"] = "2025-01-01"  # original collection date

# ── Load new DePIN data (RENDER, AKT) ──────────────────────────
new_path = os.path.join(GOV_V2_DIR, "depin_hnt_render_akt.json")
with open(new_path) as f:
    new_data = json.load(f)

# ── Load existing expansion data (DIMO, IoTeX, Grass) ──────────
expansion_path = os.path.join(EXPANSION_DIR, "depin_governance_expansion.json")
with open(expansion_path) as f:
    expansion_data = json.load(f)

# Combine all DePIN results
all_depin = new_data + expansion_data

# Filter to only successful protocols (HHI not null, n_holders >= 10)
depin_rows = []
for d in all_depin:
    if d.get("hhi") is not None and d.get("n_holders", 0) >= 10:
        depin_rows.append(d)
    else:
        print(f"  Skipping {d.get('protocol', '?')}: HHI={d.get('hhi')}, N={d.get('n_holders', 0)}")

# Deduplicate by protocol name
seen = set()
depin_unique = []
for d in depin_rows:
    name = d["protocol"]
    if name not in seen:
        seen.add(name)
        depin_unique.append(d)
    else:
        print(f"  Dedup: skipping duplicate {name}")

print(f"\nDePIN protocols to add: {len(depin_unique)}")
for d in depin_unique:
    notes = []
    if d.get("top1_share", 0) and d["top1_share"] > 0.50:
        notes.append("concentrated_by_design")
    note = d.get("note", "")
    if notes:
        note = "; ".join(notes) + (f"; {note}" if note else "")
    d["note"] = note
    print(f"  {d['protocol']:<15} HHI={d['hhi']:.6f}  Gini={d['gini']:.4f}  N={d['n_holders']}  chain={d['chain']}")

# ── Build DePIN DataFrame ──────────────────────────────────────
depin_df = pd.DataFrame(depin_unique)
depin_df["category"] = "depin"
depin_df["snapshot_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# ── Normalize columns ──────────────────────────────────────────
# The existing CSV has these columns:
# protocol,token,chain,hhi,gini,top1_share,top10_share,top50_share,n_holders,supply_coverage,total_queried,total_supply,method,note
# We want to keep all columns and add: category, snapshot_date

all_columns = [
    "protocol", "token", "chain", "hhi", "gini",
    "top1_share", "top10_share", "top50_share",
    "n_holders", "supply_coverage", "total_queried", "total_supply",
    "method", "note", "category", "snapshot_date",
]

for col in all_columns:
    if col not in defi_valid.columns:
        defi_valid[col] = None
    if col not in depin_df.columns:
        depin_df[col] = None

# ── Combine and save ────────────────────────────────────────────
combined = pd.concat([defi_valid[all_columns], depin_df[all_columns]], ignore_index=True)

# Save
output_path = os.path.join(GOV_V2_DIR, "governance_hhi_gini_CORRECTED.csv")
combined.to_csv(output_path, index=False)
print(f"\nSaved: {output_path}")
print(f"  Total rows: {len(combined)} ({len(defi_valid)} DeFi + {len(depin_df)} DePIN)")

# Also save as JSON for easier consumption
json_output = combined.to_dict(orient="records")
json_path = os.path.join(GOV_V2_DIR, "governance_hhi_gini_CORRECTED.json")
with open(json_path, "w") as f:
    json.dump(json_output, f, indent=2, default=str)
print(f"Saved: {json_path}")

# ── Comparison summary ──────────────────────────────────────────
print("\n" + "=" * 70)
print("DeFi vs DePIN COMPARISON")
print("=" * 70)
defi_hhi = defi_valid["hhi"].dropna()
depin_hhi = depin_df["hhi"].dropna()
defi_gini = defi_valid["gini"].dropna()
depin_gini = depin_df["gini"].dropna()

print(f"  DeFi  (N={len(defi_hhi)}):  HHI {defi_hhi.min():.4f}–{defi_hhi.max():.4f}  (mean {defi_hhi.mean():.4f})")
print(f"  DePIN (N={len(depin_hhi)}): HHI {depin_hhi.min():.4f}–{depin_hhi.max():.4f}  (mean {depin_hhi.mean():.4f})")
print(f"  DeFi  Gini: {defi_gini.min():.4f}–{defi_gini.max():.4f}  (mean {defi_gini.mean():.4f})")
print(f"  DePIN Gini: {depin_gini.min():.4f}–{depin_gini.max():.4f}  (mean {depin_gini.mean():.4f})")

if depin_hhi.mean() > defi_hhi.mean():
    print("\n  → DePIN HHI EXCEEDS DeFi on average: paper claim SUPPORTED")
else:
    print("\n  → DePIN HHI DOES NOT exceed DeFi on average: paper claim NEEDS REVISION")

if depin_gini.mean() > defi_gini.mean():
    print("  → DePIN Gini exceeds DeFi: more concentrated holder base")
else:
    print("  → DePIN Gini below DeFi: comparable or less concentrated")
