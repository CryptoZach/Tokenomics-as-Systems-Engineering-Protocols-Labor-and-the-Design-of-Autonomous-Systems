# Author Decisions — Data Report

Generated 2026-02-23 from repository data audit.

---

## DECISION F8: N=13 Protocol Governance Claim

### Protocols with quantitative HHI+Gini data: **10**

**DeFi protocols (source: `depin-gaps/governance_v2/governance_hhi_gini_CORRECTED.csv`):**

| # | Protocol | Token | Chain | HHI | Gini | n_holders | Quality |
|---|----------|-------|-------|-----|------|-----------|---------|
| 1 | Uniswap | UNI | ethereum | 0.1144 | 0.8737 | 990 | GOOD |
| 2 | Compound | COMP | ethereum | 0.0276 | 0.8584 | 992 | GOOD |
| 3 | MakerDAO | MKR | ethereum | 0.0454 | 0.8985 | 995 | GOOD |
| 4 | Aave | AAVE | ethereum | 0.0517 | 0.8810 | 992 | GOOD |
| 5 | Curve | CRV | ethereum | 0.1735 | 0.8973 | 993 | GOOD |
| 6 | Optimism | OP | optimism | 0.1312 | 0.8851 | 998 | GOOD |
| 7 | The Graph | GRT | ethereum | 0.1045 | 0.9181 | 993 | GOOD |

**DePIN protocols (source: `depin-gaps/expansion/data/depin_governance_expansion.csv`):**

| # | Protocol | Token | Chain | HHI | Gini | n_holders | Quality |
|---|----------|-------|-------|-----|------|-----------|---------|
| 8 | DIMO | DIMO | polygon | 0.3049 | 0.9378 | 1000 | GOOD |
| 9 | IoTeX | IOTX | ethereum | 0.3881 | 0.9831 | 989 | GOOD |
| 10 | Grass | GRASS | solana | 0.1193 | 0.9571 | 1000 | GOOD |

**Failed queries (0 holders / no data):**

- Livepeer (LPT, arbitrum) — 0 holders returned, insufficient on-chain data
- WeatherXM (WXM, arbitrum) — 0 holders returned, no data
- Anyone Protocol (ANYONE, ethereum) — 0 holders returned, no data
- Hivemapper (HONEY, solana) — 0 holders returned, no data

**Qualitative-only (governance_concentration.csv, no HHI/Gini):**

- Helium (HNT) — veHNT lock mechanism described, no quantitative concentration
- Filecoin — FIPs governance, no on-chain token vote data
- Livepeer — staking participation noted (~50%), no HHI/Gini

**Calibration file (`calibration_params.json`):** Contains only 7 DeFi protocols (Uniswap through The Graph). DePIN protocols not included.

### Ranges

| Metric | DePIN only (3) | DeFi only (7) | Full sample (10) |
|--------|---------------|---------------|-----------------|
| HHI | 0.119–0.388 | 0.028–0.174 | 0.028–0.388 |
| Gini | 0.937–0.983 | 0.858–0.918 | 0.858–0.983 |

**Paper's current claim:** "HHI 0.034-0.593" — does NOT match actual data. Actual DePIN HHI range is 0.119–0.388; DeFi range is 0.028–0.174. The 0.034 and 0.593 values do not appear in any data file.

### RECOMMENDATION

Revise claim from "13 DePIN and decentralized finance (DeFi) protocols" to **"10 protocols with quantitative concentration data (7 DeFi, 3 DePIN)"**. Update HHI range to "0.028–0.388". Add footnote: "Four DePIN protocols (WeatherXM, Anyone Protocol, Hivemapper, Livepeer) returned zero holders from Dune Analytics queries and are excluded from quantitative analysis. Snapshot date: February 2026. Methodology: top-1000 holders by net transfer balance." Update `calibration_params.json` to include the 3 DePIN protocols.

---

## DECISION F9: Helium Calibration Provenance

### Data

| Field | Value |
|-------|-------|
| Source file | `depin-gaps/helium_validation/helium_s2r_CLEANED.csv` |
| S2R date range | **2023-05-31 to 2026-02-28** |
| Months (raw) | 35 |
| Months (cleaned, usable) | 34 (cleaning summary reports 34 cleaned months) |
| Migration month excluded | **Yes** — `migration_excluded` column present; April 2023 migration month is not in the data (series starts May 2023, post-Solana migration) |
| Spike months flagged | 2024-11, 2025-02, 2025-03, 2025-06 (4 months) |
| S2R trend | INCREASING — first half mean 0.041, second half mean 0.587 |
| S2R range | 0.013 (May 2023) to 2.060 (Feb 2026), crossing parity ~late 2025 |

### Dune Query

| Field | Value |
|-------|-------|
| Source file | `depin-gaps/helium/dune_hnt_weekly_burns.json` |
| Execution ID | `01KHSVZE1CHY4HR6898V1V9VQG` |
| Execution date | 2026-02-19 |
| Rows | 149 weekly entries |
| Date range | 2023-04-17 to present |

**Note:** No Dune query ID (e.g., `dune.com/queries/NNNNN`) is embedded in the JSON metadata — only the execution ID is available. The JSON contains raw API response with `execution_id` but not the original query number.

### Calibration code

`meshnet_sim/src/calibration.py` contains **no hardcoded date references**. All date ranges are parameterized from `settings.py` (`EXTENDED_START`, `PRIMARY_END`).

### Exact text for paper

> "BME logistic parameters fitted to 34 months of cleaned Helium burn data (May 2023 through February 2026, Solana mainnet, April 2023 migration month excluded, 4 spike months flagged). Source: Dune Analytics execution 01KHSVZE1CHY4HR6898V1V9VQG (2026-02-19). HNT price calibration: Ornstein-Uhlenbeck parameters fitted to daily HNT returns over the same period."

---

## DECISION F14: Exhibit Units

### Finding

The exhibit captioned **"Emission Value vs. Fee Revenue in USD"** is **Exhibit 10** (new numbering; file `exhibit_10_emission_schedule.png`).

| Axis | Actual label on chart | Units |
|------|----------------------|-------|
| Left Y-axis | "PID Emission Rate" | **tokens/day** |
| Right Y-axis | "Fee Revenue" | **$/day** |
| X-axis | "Month" | months (0–60) |

**Caption claims:** "Emission Value vs. Fee Revenue **in USD**"

### Mismatch: **YES**

The caption says "in USD" but the left axis shows emission rate in **tokens/day**, not USD. The right axis (fee revenue) is correctly in $/day. The chart title on the image itself is "Emission-to-Fee Transition (Bull Scenario, PID Controller)" which is more accurate than the caption.

### RECOMMENDATION

**Option A (preferred):** Fix the caption to match the chart: "Exhibit 10. Emission-to-Fee Transition: Token Emission Rate vs. Fee Revenue (Bull Scenario, PID Controller)". This accurately describes what the chart shows — the convergence of emission rate and fee revenue on dual axes.

**Option B:** Regenerate the chart to show emission value in USD on the left axis (multiply tokens/day × price). This would make both axes in USD and match the current caption, but changes the exhibit's visual narrative.

---

## DECISION F11: Controller Ablation Feasibility

### Existing controller code

| Component | Location | Lines |
|-----------|----------|-------|
| PID controller | `src/meshnet_model.py` | 188–211 |
| PID gains (default) | `src/meshnet_model.py` | 53–57 (Kp=0.8, Ki=0.15, Kd=0.2) |
| PID bounds | `src/meshnet_model.py` | 48–49 (0.25×–3.0× base) |
| Static baseline | `src/meshnet_model.py` | 214–218 (`static_emission()`) |
| PID cadence | `src/meshnet_model.py` | 56 (PID_CADENCE=14) |

### Static baseline exists: **YES**

`static_emission(t)` is already implemented (line 214–218): linear taper at 5%/year from base emission. The multi-seed ensemble already runs both PID and static across all 4 scenarios (240 runs = 30 seeds × 4 scenarios × 2 models).

### P-only feasible by: **Setting Ki=0, Kd=0 — trivial**

The `pid_emission()` function accepts `kp`, `ki`, `kd` as optional keyword arguments (lines 188, 193–195). Setting `ki=0, kd=0` produces a pure proportional controller with no code changes. The `multi_seed.py` and `sensitivity_sweep.py` scripts already support passing custom gain values.

### Bang-bang feasible by: **Simple wrapper function**

A bang-bang controller would emit at PID_MAX (328,767) when N < N_TARGET and PID_MIN (27,397) when N >= N_TARGET. This requires writing a ~5-line function but no structural changes.

### Deadband feasible by: **Adding threshold check**

A deadband controller (no adjustment within ±X% of target) requires adding a threshold check before the PID calculation. ~10 lines of code.

### Estimated effort

| Ablation | Code effort | Run time (240 ensemble) |
|----------|------------|------------------------|
| P-only (Ki=0, Kd=0) | 0 lines — pass params | ~15 min |
| Bang-bang | 5 lines new function | ~15 min |
| Deadband PID | 10 lines modification | ~15 min |
| Full ablation report | Comparison script | ~1 hour total |

### RECOMMENDATION

The P-only ablation is zero-effort and high-value: it directly tests whether integral and derivative terms contribute meaningfully. Run `multi_seed.py` with `ki=0, kd=0` for all 4 scenarios × 30 seeds (120 runs, ~15 min). Compare CV and p5 against full PID. If P-only performs comparably, the paper's PID claim weakens. If P-only shows higher variance, it validates the full controller. This can be scoped as V&V (run now, add results as a paragraph in §8).

---

## DECISION F22: Parameter Interactions

### File: `results/interaction_sweep_results.csv`

| Field | Value |
|-------|-------|
| Rows | 100 |
| Parameters swept | Ki (5 values: 0.05, 0.10, 0.15, 0.25, 0.35), Kd (5 values: 0.05, 0.10, 0.20, 0.35, 0.50) |
| Kp | **Fixed at 0.8** (not swept) |
| Grid | 5 × 5 × 4 scenarios = 100 runs |
| Scenarios | bull, bear, competitor, regulatory |
| Outcomes measured | final_N, dev_from_target, total_emission, total_slashed, final_C, final_P, at_floor_steps, at_ceiling_steps |

### Covers Ki × Kd interaction: **YES (partial)**

This is a 2D grid sweep of Ki × Kd at fixed Kp=0.8, run across all 4 scenarios. It already constitutes a parameter interaction check for the two gain parameters most likely to interact (integral accumulation × derivative damping). However:

- Kp is held constant — no Kp × Ki or Kp × Kd interactions tested
- Slashing parameters not included — no gain × slashing interaction
- Cadence not included — no gain × cadence interaction
- Single seed per configuration — no seed variance captured

### RECOMMENDATION

**Already have partial data.** The Ki × Kd grid at Kp=0.8 is sufficient to check for non-monotonicity and interaction effects between integral and derivative terms. For V&V scope:

1. **Report what exists:** Add a paragraph noting the 5×5 Ki×Kd interaction sweep found [monotonic/non-monotonic] relationships, with deviation ranging from [min] to [max] across the grid.
2. **Flag remaining gaps:** Kp × Ki, gains × slashing, and gains × cadence interactions remain untested. These are scoped as future V&V work.
3. **Do not run new sweeps** unless the existing data shows surprising non-monotonicity that warrants deeper investigation.

To check: run `python3 -c "import pandas as pd; df=pd.read_csv('results/interaction_sweep_results.csv'); print(df.pivot_table(index='Ki', columns='Kd', values='dev_from_target', aggfunc='mean'))"` to visualize the interaction surface.
