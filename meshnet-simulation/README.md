# MeshNet Tokenomics Simulation

Simulation model and exhibits for the MeshNet tokenomics whitepaper, analyzing decentralized physical infrastructure network (DePIN) governance, token dynamics, and network sustainability.

## Directory Structure

```
meshnet-simulation/
├── src/                         # 14 Python modules
│   ├── meshnet_model.py         # Core simulation model
│   ├── generate_exhibits.py     # All 24 exhibit generators
│   ├── exhibit_style.py         # Chart formatting
│   ├── data_loader.py           # Data ingestion
│   ├── calibration.py           # Parameter calibration
│   ├── validate.py              # Result validation
│   ├── multi_seed.py            # Multi-seed robustness
│   ├── sensitivity_sweep.py     # Sensitivity analysis
│   ├── slashing_sweep.py        # Slashing parameter sweep
│   ├── wash_trading_mc.py       # Wash trading Monte Carlo
│   ├── cadence_sweep.py         # Cadence parameter sweep
│   ├── exponent_sweep.py        # Exponent parameter sweep
│   └── interaction_sweep.py     # Interaction effects
├── results/                     # Simulation output CSVs
├── exhibits/                    # 24 exhibit PNGs
├── calibration_params.json      # Model calibration parameters
├── requirements.txt             # Python dependencies
└── run_all.sh                   # Run full pipeline
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run full pipeline (simulation + exhibits + validation)
bash run_all.sh

# Or run individual components:
python src/generate_exhibits.py      # Generate all 24 exhibits
python src/validate.py               # Validate results against expected values
python src/multi_seed.py             # Multi-seed robustness check
python src/sensitivity_sweep.py      # Sensitivity analysis
```

## Exhibits

24 exhibits covering:
- Coordination timelines and value flow comparisons
- Governance concentration (whale governance, voting power)
- Token economics (burn-mint equilibrium, emission schedules)
- Dynamic fee curves and protocol revenue
- Network growth scenarios and sustainability metrics
- Sensitivity analysis and robustness checks

All exhibits are pre-generated in `exhibits/` and can be reproduced by running `src/generate_exhibits.py`.

## Calibration

Model parameters are stored in `calibration_params.json` and derived from on-chain data for Helium, DIMO, Hivemapper, and other DePIN protocols. See the paper for calibration methodology.
