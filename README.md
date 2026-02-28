# DePIN Thesis -- Replication Package

Data, code, exhibits, and simulation for the DePIN research papers.

## Papers

### 1. DePIN Thesis

Replication materials for "Tokenomics as Institutional Design" (governance concentration analysis) and "GeoDePIN: Design Patterns for Decentralized Physical Infrastructure Networks" (Helium S2R timeline). Includes governance HHI/Gini for 12 protocols (7 DeFi + 5 DePIN), Helium Burn-Mint Equilibrium decomposition (34 months), and S2R timeline exhibits.

Directory: [`depin-thesis/`](depin-thesis/)

### 2. MeshNet Tokenomics Simulation

Simulation model for decentralized physical infrastructure networks (DePIN), analyzing governance concentration, Spend-to-Reward dynamics, and network sustainability. Appendix A of the DePIN thesis.

Directory: [`meshnet-simulation/`](meshnet-simulation/)

## System Requirements

| Requirement | Details |
|-------------|---------|
| **Python** | 3.10 or later |
| **OS** | Tested on Ubuntu 22.04 and macOS 14; any POSIX system should work |
| **RAM** | 4 GB minimum (8 GB recommended for Monte Carlo sweeps) |
| **Runtime** | depin-thesis: ~5 min (analysis only, excludes API collection); meshnet-simulation: ~30 min (15,000+ simulation runs) |
| **API keys** | Dune Analytics (free tier), CoinGecko (free tier) — only needed if re-collecting raw data; pre-collected data is included |

## Quick Start

Each subdirectory has its own README with specific replication instructions. In general:

```bash
# Install Python dependencies
pip install -r meshnet-simulation/requirements.txt
pip install -r depin-thesis/scripts/requirements.txt
```

### Reproduce from included data (no API keys needed)

```bash
# Empirical analysis
cd depin-thesis && bash run_all.sh

# Simulation (Appendix A)
cd meshnet-simulation && bash run_all.sh
```

### Re-collect raw data from APIs

Steps 1-2 in `depin-thesis/run_all.sh` query Dune Analytics and Solscan. These require free-tier API access. All collected data is already included in `depin-thesis/data/`, so you can skip collection and start from Phase 2 if preferred.

## Data Sources

| Source | Access | Cost | Used In |
|--------|--------|------|---------|
| [Dune Analytics](https://dune.com) | Free account | $0 (Pro optional) | depin-thesis |
| [Solscan API](https://solscan.io) | Public | $0 | depin-thesis |
| [CoinGecko](https://www.coingecko.com/en/api) | Free tier | $0 | depin-thesis |
| [DefiLlama](https://defillama.com/docs/api) | Public, no key | $0 | depin-thesis |

## Data Availability Note

All data derived from public APIs (Dune Analytics, Solscan, CoinGecko, DefiLlama) is included in this repository.

## License

CC-BY 4.0. See [LICENSE](LICENSE).

Data derived from public blockchain records.

## Citation

If you use this code or data, please cite:

```bibtex
@unpublished{zukowski2026tokenomics,
  title={Tokenomics as Institutional Design: A Normative Framework and Governance Concentration Analysis},
  author={Zukowski, Zach},
  year={2026},
  note={Journal of Institutional Economics, submitted}
}

@dataset{zukowski2026tokenomics_replication,
  author={Zukowski, Zach},
  title={Replication Package for Tokenomics as Institutional Design: A Normative Framework and Governance Concentration Analysis},
  year={2026},
  publisher={Zenodo},
  version={v1.0},
  doi={10.5281/zenodo.18809561},
  url={https://doi.org/10.5281/zenodo.18809561}
}
```

## Archival & DOI

To generate a persistent DOI for this replication package:

1. Link this GitHub repository to [Zenodo](https://zenodo.org) (free)
2. Create a GitHub release (e.g., `v1.0`)
3. Zenodo will automatically archive the release and assign a DOI
4. Add the DOI to the `CITATION.cff` file and the BibTeX block above

## Contact

Zach Zukowski --- see paper correspondence addresses.
