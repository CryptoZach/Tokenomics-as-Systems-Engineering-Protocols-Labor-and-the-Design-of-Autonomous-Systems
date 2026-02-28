# Dune Analytics Queries

## Overview

These queries reproduce all on-chain empirical results in both papers. They are
written in DuneSQL (Trino-based) and designed to run on [Dune Analytics](https://dune.com)
(free tier sufficient for most queries).

## Query Inventory

| File | Paper | Output | Chain(s) | Description |
|------|-------|--------|----------|-------------|
| `01_governance_hhi.sql` | Paper 1 | Table 2 (Pub1) / Table 6 (Pub2) | Multi | HHI, Gini, Top-N for 12 governance tokens |
| `02_helium_s2r.sql` | Paper 2 | Table 2 (Pub2), Figure 2 | Solana | Helium monthly S2R (34 months) |
| `03_dimo_s2r.sql` | Paper 2 | Section V.B (Pub2) | Polygon | DIMO license burn S2R |
| `04_helium_who_burns.sql` | Paper 2 | Section V.A (Pub2) | Solana | DC burn concentration (top-20 signers) |
| `05_defi_benchmarks.sql` | Paper 1 | Table 2 subset (Pub1) | Ethereum | DeFi governance concentration benchmarks |

## How to Run

1. Create a free account at [dune.com](https://dune.com)
2. Open a new query and paste the SQL
3. Set the `{{snapshot_date}}` parameter to `2026-02-20` (or your replication date)
4. Click "Run" — most queries complete in 30–120 seconds
5. Export results as CSV to the `data/` directory

### Parameter Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `{{snapshot_date}}` | `2026-02-20` | Point-in-time snapshot for holder balances |
| `{{token_address}}` | varies | Contract address (parameterized version of Q01) |
| `{{chain}}` | varies | Blockchain name for table prefix |

## Expected Output Columns

### 01_governance_hhi.sql
```
protocol, symbol, chain, hhi, gini, top_1_share, top_5_share, top_10_share, n_holders, snapshot_date
```

### 02_helium_s2r.sql
```
month, hnt_burned, hnt_issued, s2r, fiscal_regime, cumulative_burned, cumulative_issued, cumulative_s2r
```

### 03_dimo_s2r.sql
```
month, dimo_burned, dimo_issued, s2r, fiscal_regime, cumulative_burned, cumulative_issued
```

### 04_helium_who_burns.sql
```
rank, burn_address, total_burned, burn_count, burn_share, cumulative_share, first_burn, last_burn
```

### 05_defi_benchmarks.sql
```
protocol, symbol, category, chain, hhi, gini, top_1_share, top_5_share, top_10_share, n_holders, snapshot_date
```

## Chain-Specific Notes

### Ethereum (UNI, COMP, MKR, AAVE, CRV, GRT, IOTX, ANYONE)
- Table: `erc20_ethereum.evt_Transfer`
- Standard ERC-20 transfer event pattern
- Exchange exclusion via `labels.addresses`

### Solana (HNT, GRASS)
- Table: `tokens_solana.transfers` or `spl_token_solana.spl_token_evt_burn`
- HNT mint: `hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux`
- GRASS mint: look up on Solana Explorer
- Token decimals vary (HNT = 8, GRASS = 9)

### Polygon (DIMO)
- Table: `erc20_polygon.evt_Transfer`
- DIMO: `0xE261D618a959aFfFd53168Cd07D12E37B26761db` (18 decimals)
- Burns = transfers to `0x000...000`

### Arbitrum (WXM)
- Table: `erc20_arbitrum.evt_Transfer`
- WXM address: look up on Arbiscan (launched May 2024)

### Optimism (OP)
- Table: `erc20_optimism.evt_Transfer`
- OP: `0x4200000000000000000000000000000000000042` (18 decimals)

## Known Limitations

1. **Livepeer (LPT)** excluded: Arbitrum schema prevented governance query from returning results. Document as "N/A — schema limitation."
2. **Hivemapper (HONEY)** excluded: Solana token not indexed for governance concentration in current Dune schema.
3. **IoTeX (IOTX)**: Computed on Ethereum ERC-20 representation, not IoTeX L1. May reflect bridge dynamics rather than true governance distribution.
4. **Exchange exclusion** is heuristic: uses `labels.addresses` table plus known burn addresses. Some custodial addresses may be misclassified.
5. **Curve (CRV)**: Raw CRV balances differ from veCRV voting power. The HHI captures token concentration, not effective governance weight.
6. **Snapshot methodology**: Single point-in-time. Panel data (monthly snapshots) would strengthen causal claims but requires Dune Pro for historical balance queries.
7. **Dune schema changes**: Table names (`erc20_ethereum.evt_Transfer`, `tokens_solana.transfers`) may change. Check [docs.dune.com](https://docs.dune.com) for current schema.

## Replication Timing

- Queries 01 and 05: ~60–180 seconds each (large transfer tables)
- Queries 02 and 03: ~30–60 seconds each
- Query 04: ~30 seconds
- Total: ~10 minutes including export
