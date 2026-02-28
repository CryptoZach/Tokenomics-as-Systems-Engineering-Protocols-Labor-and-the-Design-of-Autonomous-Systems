#!/bin/bash
# run_all.sh — Full depin-thesis empirical pipeline
#
# Reproduces all empirical results: governance concentration metrics,
# Helium S2R/BME analysis, expansion protocols, and all exhibits.
#
# Prerequisites:
#   pip install -r scripts/requirements.txt
#
# Data source note:
#   Steps 1-2 require API access (Dune Analytics free tier, Solscan).
#   Pre-collected data is included in data/, so you can skip to Step 3
#   if you want to reproduce analysis from existing data.
set -e
cd "$(dirname "$0")"

echo "============================================================"
echo "DePIN Thesis — Full Replication Pipeline"
echo "============================================================"

# ── Phase 1: Data Collection (requires API access) ──────────
echo ""
echo "=== Phase 1: Data Collection ==="

echo "  Step 1: Collect DePIN governance token-holder data..."
python scripts/collect_depin_governance.py

echo "  Step 2a: Collect Helium on-chain data (Solscan)..."
python scripts/collect_hnt_solscan.py

echo "  Step 2b: Retry failed Helium queries..."
python scripts/collect_hnt_retry.py

# ── Phase 2: Governance Concentration Analysis ───────────────
echo ""
echo "=== Phase 2: Governance Concentration Analysis ==="

echo "  Step 3: Correct governance data..."
python scripts/task_1_corrected_governance.py

echo "  Step 4: Compute HHI/Gini governance metrics..."
python scripts/task_2_governance_hhi.py

echo "  Step 5: Snapshot governance analysis..."
python scripts/task_3a_snapshot_governance.py

echo "  Step 6: Compute HHI (standalone)..."
python scripts/compute_hhi.py

echo "  Step 7: Merge DePIN governance datasets..."
python scripts/merge_depin_governance.py

# ── Phase 3: Helium S2R & BME Analysis ───────────────────────
echo ""
echo "=== Phase 3: Helium S2R & BME Analysis ==="

echo "  Step 8: Compute Spend-to-Reward ratio..."
python scripts/compute_s2r.py

echo "  Step 9: BME decomposition (fee growth vs price decline)..."
python scripts/helium/bme_decomposition.py

echo "  Step 10: BME trailing 12-month analysis..."
python scripts/helium/bme_12month_analysis.py

echo "  Step 11: BME data quality audit..."
python scripts/helium/bme_data_quality.py

echo "  Step 12: Verify BME arithmetic..."
python scripts/helium/verify_bme_arithmetic.py

# ── Phase 4: Helium Validation ───────────────────────────────
echo ""
echo "=== Phase 4: Helium Validation ==="

echo "  Step 13: Validate burn events..."
python scripts/helium_validation/task_2a_validate_burns.py

echo "  Step 14: Clean S2R time series..."
python scripts/helium_validation/task_2c_clean_s2r.py

# ── Phase 5: Expansion Protocols (6 additional DePIN) ────────
echo ""
echo "=== Phase 5: Expansion Protocols ==="

echo "  Step 15: Governance expansion (6 protocols)..."
python scripts/expansion/01_governance_expansion.py

echo "  Step 15b: Governance retry (failed queries)..."
python scripts/expansion/01b_governance_retry.py

echo "  Step 16: CoinGecko market data pull..."
python scripts/expansion/02_coingecko_pull.py

echo "  Step 17: Unit economics computation..."
python scripts/expansion/03_unit_economics.py

echo "  Step 18: S2R computation (expansion protocols)..."
python scripts/expansion/04_s2r_computation.py

echo "  Step 19: Compile expansion results..."
python scripts/expansion/05_compile_results.py

echo "  Step 20: Thesis integration (update manuscript tables)..."
python scripts/expansion/06_thesis_integration.py

# ── Phase 6: Figure Generation ───────────────────────────────
echo ""
echo "=== Phase 6: Figure Generation ==="

echo "  Step 21: Build Figure 2 (S2R timeline)..."
python scripts/build_figure2_s2r.py

echo "  Step 22: Generate all publication figures..."
python scripts/generate_figures.py

echo ""
echo "============================================================"
echo "DONE — All phases complete."
echo "  Data outputs:  data/"
echo "  Exhibits:      exhibits/"
echo "============================================================"
