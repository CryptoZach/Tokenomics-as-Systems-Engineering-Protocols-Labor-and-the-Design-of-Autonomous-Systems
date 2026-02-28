# DePIN Thesis -- Replication Package

Data, code, exhibits, and simulation for the DePIN research papers.

## Papers

### 1. DePIN Thesis

Replication materials for "Tokenomics as Institutional Design" (governance concentration analysis) and "GeoDePIN: Design Patterns for Decentralized Physical Infrastructure Networks" (Helium S2R timeline). Includes governance HHI/Gini for 12 protocols (7 DeFi + 5 DePIN), Helium Burn-Mint Equilibrium decomposition (34 months), and S2R timeline exhibits.

Directory: [`depin-thesis/`](depin-thesis/)

### 2. MeshNet Tokenomics Simulation

Simulation model for decentralized physical infrastructure networks (DePIN), analyzing governance concentration, Spend-to-Reward dynamics, and network sustainability. Appendix A of the DePIN thesis.

Directory: [`meshnet-simulation/`](meshnet-simulation/)

## Quick Start

Each subdirectory has its own README with specific replication instructions. In general:

```bash
# Install Python dependencies
pip install -r meshnet-simulation/requirements.txt
pip install -r depin-thesis/scripts/requirements.txt
```

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
```

## Contact

Zach Zukowski --- see paper correspondence addresses.
