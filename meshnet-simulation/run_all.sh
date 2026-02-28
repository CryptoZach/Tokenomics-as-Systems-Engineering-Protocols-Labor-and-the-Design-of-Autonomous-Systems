#!/bin/bash
# run_all.sh — Full MeshNet simulation pipeline
set -e
cd "$(dirname "$0")"

echo "=== Step 1: Core simulation (8 configs) ==="
python src/meshnet_model.py

echo "=== Step 2: PID gain sensitivity (60 runs) ==="
python src/sensitivity_sweep.py

echo "=== Step 3: Slashing sensitivity (40 runs) ==="
python src/slashing_sweep.py

echo "=== Step 4: Ki × Kd interaction grid (100 runs) ==="
python src/interaction_sweep.py

echo "=== Step 5: Cadence sensitivity (16 runs) ==="
python src/cadence_sweep.py

echo "=== Step 6: Governance exponent sweep (analytical) ==="
python src/exponent_sweep.py

echo "=== Step 7: Wash trading Monte Carlo (100 runs) ==="
python src/wash_trading_mc.py

echo "=== Step 8: Multi-seed ensemble (240+ runs) ==="
python src/multi_seed.py

echo "=== Step 9: Generate all 21 exhibits ==="
python src/generate_exhibits.py

echo "=== Step 10: Run validation ==="
python src/validate.py

echo "=== DONE ==="
echo "Results in results/"
echo "Exhibits in exhibits/"
