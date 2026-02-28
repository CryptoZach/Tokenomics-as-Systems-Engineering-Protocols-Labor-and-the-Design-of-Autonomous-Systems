# Codebook: Protocol Taxonomy and Normative Scoring

## Overview

This directory contains the structured data instruments for the thesis's empirical
taxonomy of 13 DePIN/DeVIN protocols and the normative scoring framework based on
8 philosophical lenses.

## Files

| File | Description | Rows |
|------|-------------|------|
| `protocol_codebook.csv` | 14-protocol coding template (48+ fields) | 14 rows (13 taxonomy + Render reference) |
| `scoring_rubric.csv` | Philosophy lens scoring rubric (8 lenses x 4 levels) | 8 rows |
| `scoring_sheet.csv` | Per-protocol per-lens scores with evidence | 104+ rows (13 x 8) |

---

## Field Definitions: protocol_codebook.csv

### Metadata Block
| Field | Type | Description |
|-------|------|-------------|
| `protocol_id` | string | Unique identifier (lowercase, no spaces) |
| `name` | string | Display name |
| `chain` | string | Primary blockchain (e.g., "Solana", "Ethereum", "Polygon") |
| `category` | enum | `GeoDePIN` \| `GeoDePIN*` (data-only) \| `DeVIN` (compute/storage) |
| `subcategory` | string | Functional domain (wireless, storage, mapping, etc.) |
| `launch_date` | date | Mainnet or token launch date (YYYY-MM-DD) |
| `token_ticker` | string | Token symbol (e.g., "HNT", "FIL") |
| `market_cap_usd` | float | Market capitalization at snapshot date |
| `circulating_supply` | float | Circulating token supply |
| `total_supply` | float | Maximum or total token supply |
| `website` | url | Official project website |
| `whitepaper_url` | url | Technical whitepaper or documentation |
| `governance_forum_url` | url | Governance discussion forum |

### Supply/Issuance Block
| Field | Type | Description |
|-------|------|-------------|
| `emission_model` | enum | `fixed` \| `decaying` \| `algorithmic` \| `none` |
| `max_supply` | float | Hard cap on total supply (if any) |
| `inflation_rate_annual_pct` | float | Current annual inflation rate (%) |
| `decay_rule` | string | Description of emission decay (e.g., "halving every 2 years") |
| `halving_schedule` | string | Halving dates/intervals if applicable |
| `vesting_months` | int | Total vesting period for team/investor tokens |
| `unlock_schedule_description` | string | Free-text description of unlock schedule |

### Distribution Block
| Field | Type | Description |
|-------|------|-------------|
| `team_allocation_pct` | float | Percentage allocated to team/founders |
| `investor_allocation_pct` | float | Percentage allocated to investors |
| `community_allocation_pct` | float | Percentage for community rewards/mining |
| `treasury_allocation_pct` | float | Percentage held in protocol treasury |
| `airdrop_method` | enum | `none` \| `merkle` \| `linear` \| `retroactive` |
| `sybil_defense_method` | string | Anti-sybil mechanism for distribution |

### Value Routing Block
| Field | Type | Description |
|-------|------|-------------|
| `fee_switch` | enum | `on` \| `off` \| `partial` — whether protocol captures fees |
| `burn_mechanism` | enum | `none` \| `fee_burn` \| `DC_burn` \| `license_burn` \| `gas_burn` |
| `buyback_mechanism` | enum | `none` \| `treasury_buyback` |
| `treasury_routing_description` | string | How revenue flows through the protocol |
| `sink_type_primary` | string | Primary token sink (burn, stake, lock, etc.) |

### Staking/Locks Block
| Field | Type | Description |
|-------|------|-------------|
| `staking_enabled` | boolean | Whether staking is available |
| `lockup_mechanism` | enum | `none` \| `time_lock` \| `ve_lock` |
| `unbonding_period_days` | int | Days to unbond staked tokens |
| `slashing_enabled` | boolean | Whether slashing is implemented |
| `slashing_conditions` | string | Conditions that trigger slashing |

### Governance Block
| Field | Type | Description |
|-------|------|-------------|
| `governance_type` | enum | `token_vote` \| `multisig` \| `hybrid` \| `foundation` |
| `on_chain_voting` | boolean | Whether votes are recorded on-chain |
| `delegation_enabled` | boolean | Whether token delegation is supported |
| `proposal_threshold` | string | Minimum tokens to submit a proposal |
| `quorum_pct` | float | Quorum requirement (% of supply) |
| `timelock_hours` | int | Hours between vote passage and execution |
| `veto_mechanism` | enum | `none` \| `guardian` \| `security_council` |
| `bicameral` | boolean | Whether governance has two chambers/houses |

### Concentration Metrics Block (Computed)
| Field | Type | Description |
|-------|------|-------------|
| `holding_hhi` | float | Herfindahl-Hirschman Index (top-1000 holders) |
| `holding_gini` | float | Gini coefficient (0–1) |
| `top_1_share` | float | Share held by largest single holder |
| `top_5_share` | float | Cumulative share of top 5 holders |
| `top_10_share` | float | Cumulative share of top 10 holders |
| `n_holders_sampled` | int | Number of holders in concentration sample |
| `snapshot_date` | date | Date of concentration snapshot (YYYY-MM) |
| `dune_query_id` | string | Reference to Dune query used |

### S2R Metrics Block (Computed)
| Field | Type | Description |
|-------|------|-------------|
| `s2r_burns_only` | float/range | Spend-to-Reward ratio (burns / issuance) |
| `s2r_burns_plus_locks` | float | S2R including staking locks as "spend" |
| `s2r_period` | string | Time period for S2R measurement |
| `s2r_data_source` | string | Data source (e.g., "Dune Analytics") |

### DePIN-Specific Block
| Field | Type | Description |
|-------|------|-------------|
| `operator_type` | enum | `individual` \| `institutional` \| `mixed` |
| `deployment_unit` | string | What operators deploy (hotspot, server, dashcam, etc.) |
| `hardware_cost_usd` | string | Typical hardware cost range |
| `coverage_verification_method` | string | How coverage/work is verified |
| `reward_basis` | enum | `coverage` \| `service` \| `hybrid` |
| `geodata_required` | boolean | Whether geolocation is required for rewards |
| `location_verification_method` | string | How location claims are verified |

---

## Scoring Procedure (Section 4.5.1)

The normative scoring framework applies 8 philosophical lenses to each protocol.
Each lens is scored on a 0–3 scale per `scoring_rubric.csv`.

### 5-Step Scoring Process

1. **Documentation Review**: Read the protocol's whitepaper, governance docs,
   token economics documentation, and community forum.

2. **On-Chain Verification**: Cross-reference documentation claims against
   on-chain data (governance votes, token flows, smart contract parameters).

3. **Independent Scoring**: Each scorer assigns 0–3 for each lens based on
   the rubric, recording evidence links and brief justification notes.

4. **Reconciliation**: Where scores diverge by >1 point between raters,
   discuss and reconcile with explicit rationale recorded in notes field.

5. **Aggregation**: Compute the Synergy Index (arithmetic mean of 5 core
   lenses) and record all individual lens scores.

### Synergy Index Formula

The Synergy Index is the arithmetic mean of 5 core philosophical lens scores:

```
Synergy Index = (kantian + rawlsian + pettit + ostrom + hayek) / 5
```

**Included lenses** (5):
- `kantian_publicity` — Transparency and public justification
- `rawlsian_fairness` — Equity and floor-raising mechanisms
- `pettit_contestation` — Checks, balances, and appeal mechanisms
- `ostrom_polycentricity` — Distributed and nested governance
- `hayek_knowledge` — Price signals and demand-coupling

**Excluded lenses** (3) and rationale:
- `nussbaum_capability` — Insufficient measurement infrastructure across protocols;
  capability gains are aspirational rather than measurable in most DePIN projects
- `floridi_integrity` — Information-flow governance is nascent; most protocols
  lack systematic privacy/data-flow frameworks to meaningfully differentiate
- `appiah_cosmopolitan` — Cross-cultural participation data is unreliable;
  geographic distribution ≠ meaningful cosmopolitan engagement

---

## Inter-Rater Reliability Protocol (Section 4.5.2)

### Requirements
- **Minimum overlap**: 5 protocols scored independently by both raters
- **Target**: Cohen's κ ≥ 0.70 (substantial agreement)
- **Scoring**: Blind (raters do not see each other's scores during initial pass)

### Reconciliation Rules
1. Scores within 0 or 1 point: Accept higher score with notation
2. Scores diverging by 2+ points: Mandatory discussion and evidence review
3. Final score must be justified with explicit evidence link
4. All reconciliation decisions recorded in `notes` column

### Reporting
- Report Cohen's κ for each lens and overall
- Report percentage exact agreement and within-1 agreement
- Discuss any lenses with κ < 0.60 (moderate agreement threshold)

---

## Data Completeness Notes

- **Helium** is the most completely scored protocol (worked example)
- **CUDIS, UpRock, Wayru**: Minimal data available; scored conservatively
- **Hivemapper, GEODNET**: Some fields are `data_insufficient`
- Protocols without on-chain governance tokens receive 0 for governance lenses
- Empty `evidence_link` cells indicate scores are based on general documentation
  review rather than a specific source
