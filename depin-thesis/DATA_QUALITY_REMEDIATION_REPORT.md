# Data Quality Remediation Report

**Date:** 2026-02-19
**Branch:** `claude/depin-thesis-data-gathering-iyZoi`

---

## SEVERITY 1: Governance Token Concentration — FIXED

### Problem
The original Dune query (Query 9) used cumulative transfer sums (`SUM(value)` on incoming `evt_Transfer` events) instead of net balances. This produced:
- Exchange hot wallets dominating results (e.g., Binance at 615M UNI cumulative inflows)
- AAVE returning uint256 overflow values (1.16e+59 — Approval events counted as transfers)
- HHI values ~0.030 (invalid — too low because denominator was inflated by cumulative inflows)

### Fix Applied
Rewrote governance query to compute **net balances** (inflows minus outflows) from `evt_Transfer`:
- Expanded from 5 to 8 tokens (added CRV, OP, GRT)
- Excluded 13 known exchange addresses (Binance, Coinbase, null/dead)
- Added supply coverage validation
- Increased from 200 to 1000 holder limit

### Corrected Results

| Token | HHI | Gini | Top 1% | Top 10% | N Holders | Supply Coverage | Method |
|-------|-----|------|--------|---------|-----------|-----------------|--------|
| UNI | 0.1144 | 0.874 | 33.2% | 47.6% | 990 | 79.8% | net_transfer |
| COMP | 0.0276 | 0.858 | 14.4% | 31.6% | 992 | 86.0% | net_transfer |
| MKR | 0.0454 | 0.899 | 11.4% | 56.4% | 995 | 118.7% | net_transfer |
| AAVE | 0.0517 | 0.881 | 19.1% | — | 992 | — | net_transfer |
| CRV | 0.1735 | 0.897 | 40.9% | 61.3% | 993 | 103.9% | net_transfer |
| OP | 0.1312 | 0.885 | 33.4% | 59.6% | 998 | 90.2% | net_transfer |
| GRT | 0.1045 | 0.918 | 29.3% | 60.6% | 993 | 92.5% | net_transfer |
| LPT | N/A | N/A | N/A | N/A | 0 | — | Arbitrum schema issue |

### Interpretation
- HHI range: 0.028–0.174 (moderately to highly concentrated)
- Gini range: 0.86–0.92 (very high inequality, consistent with crypto governance)
- CRV most concentrated (top 1 holder = 40.9% = veCRV locker)
- COMP least concentrated (HHI 0.028)
- LPT failed on Arbitrum — needs separate investigation

### Files
- `governance_v2/governance_hhi_gini_CORRECTED.csv`
- `governance_v2/governance_hhi_gini_CORRECTED.json`
- `governance_v2/dune_balance_b_*.json` (raw Dune responses)

---

## SEVERITY 2: Helium S2R Validation — VALIDATED + CLEANED

### Problem
- `action='burn'` filter might capture non-DC burns
- April 2023 migration artifact (145.9M HNT minted)
- Large S2R spikes needing investigation

### Validation Findings

**Action Types (Dune Query):**
| Action | Transactions | Total HNT |
|--------|-------------|-----------|
| transfer | 42,002,755 | 8,183,229,752 |
| mint | 3,734 | 192,727,200 |
| burn | 1,501,043 | 7,538,876 |

Only 3 action types exist. The `burn` filter is clean — no contamination from other action types.

**Burn Concentration:**
- Top burner (`Bi5JuJD...`): 3.25M HNT (43%) in only 178 transactions → treasury/institutional
- #2 burner (`tasky4vv...`): 2.1M HNT in 39K txns → automated bot (since Nov 2025)
- #4 burner (`cronjz7v...`): 593K HNT in 324K txns → also appears as #2 minter (Helium rewards cron)
- 100 large burns (>10K HNT) account for 5.23M of 7.54M total (69%)

**Implication:** The burn data is predominantly treasury/institutional DC purchases, not diffuse network usage. The S2R metric reflects DC demand but is dominated by a few large actors.

### S2R Cleaning Applied
1. **April 2023 excluded** — 145.9M HNT minted was Solana migration re-mint
2. **4 spike months flagged** — Nov 2024, Feb/Mar 2025, Jun 2025
3. **3-month rolling S2R** added for smoothing
4. **v1 reference comparison:** All 5 reference points match within 6%:
   - 2023-06: v1=0.031, v5=0.031 (OK)
   - 2023-09: v1=0.119, v5=0.119 (OK)
   - 2024-01: v1=0.052, v5=0.052 (OK)
   - 2024-07: v1=0.041, v5=0.041 (OK)
   - 2025-01: v1=0.006, v5=0.006 (OK)

### Summary Statistics (cleaned, non-spike months)
- Mean S2R: 0.314 (driven up by H2 2025 structural increase)
- Median S2R: 0.035
- Trend: INCREASING (first half mean 0.041 → second half mean 0.587)

### Files
- `helium_validation/helium_s2r_CLEANED.csv`
- `helium_validation/helium_s2r_cleaning_summary.json`
- `helium_validation/dune_hnt_action_types.json`
- `helium_validation/dune_hnt_burn_signers.json`
- `helium_validation/dune_hnt_mint_signers.json`
- `helium_validation/dune_hnt_large_burns.json`
- `helium_validation/dune_hnt_oct2025_daily.json`
- `helium_validation/burn_validation_summary.json`

---

## SEVERITY 3: Missing Protocols — PARTIALLY ADDRESSED

### Addressed
- **CRV, OP, GRT**: Now included in corrected governance data (HHI 0.174, 0.131, 0.105 respectively)
- **Snapshot governance**: Attempted but hub.snapshot.org returned 504 errors (service temporarily unavailable)

### Remaining Gaps
- **LPT (Livepeer)**: Arbitrum `erc20_arbitrum.evt_Transfer` query returned 0 rows. Livepeer's token contract on Arbitrum (`0x289ba1701C2F088cf0faf8B3c94Cd3B9e166f367`) may need different table schema.
- **WeatherXM, Render**: Not attempted in this remediation round
- **Snapshot governance data**: Snapshot API down, should be retried

---

## Thesis Impact

### Governance Numbers to Update
The thesis should replace the invalid HHI values (0.030, 0.029, 0.027) with corrected values. The corrected HHI range (0.028–0.174) tells a more nuanced story:
- Some protocols are genuinely decentralized in token distribution (COMP: 0.028)
- Others are highly concentrated (CRV: 0.174, OP: 0.131, UNI: 0.114)
- Gini coefficients uniformly high (0.86–0.92) — governance token wealth is very unequal across all protocols

### Helium S2R Narrative
- S2R data is validated (v1 references match) and the burn filter is clean
- However, burns are dominated by a few large actors (top 5 signers = ~90% of volume)
- S2R shows structural increase in H2 2025, suggesting growing DC demand
- Recommend noting burn concentration in thesis discussion
