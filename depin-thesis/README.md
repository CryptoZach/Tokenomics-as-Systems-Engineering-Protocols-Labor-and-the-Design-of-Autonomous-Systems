# DePIN Thesis -- Replication Package

Canonical repository for all materials supporting:

> **Paper:** "Tokenomics as Systems Engineering: Mechanism Design, Governance, and Control in Decentralized Physical Infrastructure Networks"
>
> Published as **Pub3** on SSRN. Covers institutional design (Part I), DePIN design patterns (Part II), and MeshNet simulation (Part III / Appendix A).

## Directory Structure

```
depin-thesis/
├── Pub3_SSRN_final.docx                 # Final Word manuscript
├── Pub3_SSRN_restructured (5).md        # Latest markdown (26 exhibits, renumbered)
├── Pub3_SSRN_restructured_Code.md       # Markdown with code appendix (24 exhibits)
├── AUTHOR_DECISIONS.md                   # Design decision log
├── DATA_QUALITY_REMEDIATION_REPORT.md    # Data quality audit
│
├── codebook/                             # Taxonomy and scoring instruments
│   ├── protocol_codebook.csv             #   14-protocol coding template (48+ fields)
│   ├── scoring_rubric.csv                #   8 philosophical lenses x 4 levels
│   └── scoring_sheet.csv                 #   Per-protocol per-lens scores
│
├── data/
│   ├── expected_results.csv              # Verifiable claims for automated checking
│   ├── governance/                       # Governance concentration (12 protocols)
│   │   ├── governance_hhi_gini_CORRECTED.csv
│   │   └── governance_hhi_gini_CORRECTED.json
│   ├── governance_v2/                    # Updated collection (Dune + Cosmos LCD)
│   │   ├── governance_hhi_gini_CORRECTED.csv
│   │   ├── governance_hhi_gini_CORRECTED.json
│   │   ├── depin_hnt_render_akt.json     #   HNT/RENDER/AKT holder data
│   │   └── collection_log.json           #   API call log
│   ├── helium/                           # Helium Burn-Mint Equilibrium
│   │   ├── helium_bme_monthly.csv        #   34 months (May 2023 -- Feb 2026)
│   │   ├── helium_bme_decomposition.json #   BME factor decomposition
│   │   ├── helium_bme_12month.json       #   12-month rolling analysis
│   │   ├── bme_data_quality.json         #   Data quality audit
│   │   ├── helium_s2r_continuous.csv     #   Continuous S2R time series
│   │   └── s2r_measurement_memo_v2.md    #   Measurement methodology
│   ├── helium_validation/                # Burn/mint validation
│   │   ├── helium_s2r_CLEANED.csv        #   Cleaned S2R after outlier removal
│   │   ├── burn_validation_summary.json  #   Burn event validation
│   │   └── helium_s2r_cleaning_summary.json
│   └── expansion/                        # Protocol expansion (6 additional DePINs)
│       ├── consolidated_expansion_results.json
│       ├── depin_governance_expansion.csv
│       ├── depin_governance_expansion.json
│       ├── s2r_classification.json       #   S2R tier classification
│       ├── table_6u1_expansion.csv       #   Table 6 expansion data
│       └── unit_economics_expanded.json  #   Per-protocol unit economics
│
├── dune_queries/                         # Dune Analytics SQL
│   ├── 01_governance_hhi.sql             #   HHI/Gini for 12 governance tokens
│   ├── 02_helium_s2r.sql                 #   Helium monthly S2R (Solana)
│   ├── 03_dimo_s2r.sql                   #   DIMO license burn S2R (Polygon)
│   ├── 04_helium_who_burns.sql           #   DC burn concentration (top-20 signers)
│   ├── 05_defi_benchmarks.sql            #   DeFi governance benchmarks
│   └── README.md
│
├── exhibits/                             # All publication exhibits (24 + 26 numbering)
│   ├── exhibit_01_coordination_timeline.png  # _Code.md numbering
│   ├── exhibit_02_discipline_map.png
│   ├── exhibit_03_value_flow_comparison.png
│   ├── exhibit_04_private_currencies.png
│   ├── exhibit_05_meshnet_system_map.png
│   ├── exhibit_06_whale_governance.png      # Governance HHI cross-section
│   ├── exhibit_07_voting_power.png          # V(i) = tau(i) x (1+R(i))^2
│   ├── exhibit_08_burn_mint_equilibrium.png # BME 3-scenario simulation
│   ├── exhibit_09_helium_burns_mints_price.png  # Helium BME timeline
│   ├── exhibit_10_dynamic_fee_curves.png
│   ├── exhibit_11_token_allocation.png
│   ├── exhibit_12_emission_schedule.png     # PID fee/emission crossover
│   ├── exhibit_13_airdrop_sensitivity.png
│   ├── exhibit_14_conviction_curves.png
│   ├── exhibit_15_governance_flowchart.png
│   ├── exhibit_16_pid_block_diagram.png
│   ├── exhibit_17_emission_pid_vs_static.png
│   ├── exhibit_18_node_count_stability.png
│   ├── exhibit_19_ensemble_node_distributions.png
│   ├── exhibit_20_price_trajectories.png        # Appendix A
│   ├── exhibit_21_ensemble_price_distributions.png
│   ├── exhibit_22_pid_sensitivity.png
│   ├── exhibit_23_slashing_sensitivity.png
│   ├── exhibit_24_wash_trading_impact.png
│   ├── exhibit_bme_12month_analysis.png     # Supplemental: BME decomposition
│   └── figure2_s2r_timeline.png             # Alias of exhibit_09
│
├── scripts/
│   ├── build_figure2_s2r.py               # Helium S2R / BME timeline chart
│   ├── collect_depin_governance.py        # Multi-source governance data
│   ├── compute_hhi.py                     # HHI/Gini from Dune exports
│   ├── compute_s2r.py                     # S2R time-series computation
│   ├── generate_figures.py                # All paper figures
│   ├── merge_depin_governance.py          # Merge DeFi + DePIN governance
│   ├── requirements.txt
│   ├── helium/                            # Helium BME analysis
│   │   ├── bme_decomposition.py           #   Factor decomposition
│   │   ├── bme_12month_analysis.py        #   12-month rolling
│   │   ├── bme_data_quality.py            #   Quality checks
│   │   └── verify_bme_arithmetic.py       #   Arithmetic verification
│   └── expansion/                         # Protocol expansion pipeline
│       ├── 01_governance_expansion.py     #   Dune governance for 6 protocols
│       ├── 01b_governance_retry.py        #   Retry failed queries
│       ├── 02_coingecko_pull.py           #   CoinGecko market data
│       ├── 03_unit_economics.py           #   Unit economics computation
│       ├── 04_s2r_computation.py          #   S2R classification
│       ├── 05_compile_results.py          #   Consolidate results
│       └── 06_thesis_integration.py       #   Thesis integration
│
└── (simulation code lives in ../meshnet-simulation/)
```

## Exhibit Map

Exhibits 1--19 appear in the body text; Exhibits 20--24 in Appendix A.

| # | Name | Source | Section |
|---|------|--------|---------|
| 1 | Coordination Technology Timeline | Conceptual | Section 2 |
| 2 | Interdisciplinary Foundations of Token Design | Conceptual | Section 2 |
| 3 | Value Flow: Traditional Firm vs. Protocol | Conceptual | Section 3 |
| 4 | Historical Private Currency Issuance, 1790--1870 | Historical | Section 3 |
| 5 | MeshNet System Architecture | Design | Section 4 |
| 6 | Governance Concentration Cross-Section | Empirical (Dune) | Section 5 |
| 7 | Voting Power Function V(i) | Simulation | Section 5 |
| 8 | Burn-Mint Equilibrium: 3 Scenarios | Simulation | Section 5 |
| 9 | Helium Weekly Burns, Mints, Price | Empirical (on-chain) | Section 5 |
| 10 | Dynamic Fee Curves by Coverage Zone | Design | Section 5 |
| 11 | MeshNet Token Allocation | Design | Section 6 |
| 12 | Emission Rate vs. Fee Revenue (PID) | Simulation | Section 6 |
| 13 | Airdrop Sizing Sensitivity | Simulation | Section 6 |
| 14 | Conviction Voting Curves | Design | Section 7 |
| 15 | Governance Decision Tree | Design | Section 7 |
| 16 | PID Controller Decomposition | Simulation | Section 8 |
| 17 | PID vs. Static Emission | Simulation | Section 8 |
| 18 | Node Count Stability | Simulation | Section 8 |
| 19 | Ensemble Node Distributions (30 seeds) | Simulation | Section 8 |
| 20 | Price Trajectories | Simulation | Appendix A |
| 21 | Ensemble Price Distributions | Simulation | Appendix A |
| 22 | PID Gain Sensitivity | Simulation | Appendix A |
| 23 | Slashing Parameter Sensitivity | Simulation | Appendix A |
| 24 | Wash Trading Defense (PoC) | Simulation | Appendix A |

## Key Results

### Governance Concentration (Section 5.2)

12 protocols (7 DeFi benchmarks + 5 DePIN):

| Protocol | Category | HHI | Gini | Method |
|----------|----------|-----|------|--------|
| Compound | DeFi | 0.028 | 0.86 | net_transfer |
| Akash | DePIN | 0.037 | 0.67 | validator_staking |
| MakerDAO | DeFi | 0.045 | 0.90 | net_transfer |
| Aave | DeFi | 0.052 | 0.88 | net_transfer |
| Render | DePIN | 0.093 | 0.93 | net_transfer |
| The Graph | DeFi | 0.105 | 0.92 | net_transfer |
| Uniswap | DeFi | 0.114 | 0.87 | net_transfer |
| Grass | DePIN | 0.119 | 0.96 | net_transfer |
| Optimism | DeFi | 0.131 | 0.89 | net_transfer |
| Curve | DeFi | 0.174 | 0.90 | net_transfer |
| DIMO | DePIN | 0.305 | 0.94 | net_transfer |
| IoTeX | DePIN | 0.388 | 0.98 | net_transfer |

DePIN mean HHI: 0.19 (range 0.037--0.388) vs. DeFi mean HHI: 0.09 (range 0.028--0.174).

### Helium S2R / BME Timeline (Section 5.1)

- **Start:** BME = 0.013 (May 2023, post-Solana migration)
- **Parity:** BME > 1.0 (October 2025)
- **Peak:** BME = 2.06 (mid-February 2026, complete weeks only)
- **12-month attribution** (Jan 2025 -- Jan 2026): fee growth 58%, price decline 25%, emission reduction 17%
- **34 monthly observations** (May 2023 -- February 2026)

### MeshNet Simulation (Appendix A)

15,412 simulation runs. See `../meshnet-simulation/` for full code and results.

- PID emission vs. static across 4 scenarios (bull, bear, competitor, regulatory)
- 30-seed ensemble confidence intervals per configuration
- PoC wash-trading defense reduces fraud leakage by 96.9%
- All 10 validation assertions PASS

## Setup

```bash
pip install -r scripts/requirements.txt

# Governance data collection (requires Dune API key)
python scripts/collect_depin_governance.py

# Helium BME analysis
python scripts/helium/bme_decomposition.py
python scripts/helium/bme_12month_analysis.py

# Protocol expansion (requires Dune + CoinGecko API keys)
python scripts/expansion/01_governance_expansion.py
python scripts/expansion/05_compile_results.py

# Generate Exhibit 9 (Helium BME timeline)
python scripts/build_figure2_s2r.py
```

## Data Sources

- **Dune Analytics**: On-chain governance token balances, Helium DC burns, DeFi benchmarks
- **Solscan / Cosmos LCD**: Solana and Cosmos token holder snapshots
- **CoinGecko**: Token supply and market data
- **Helium Explorer**: Network statistics
- **MeshNet simulation**: Agent-based model in `../meshnet-simulation/src/`

## Related Directories

| Directory | Contents |
|-----------|----------|
| `../meshnet-simulation/` | Full MeshNet simulation code, 24 exhibits, all results |
