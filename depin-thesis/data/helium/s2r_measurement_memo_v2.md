# S2R Measurement Memo v2 (On-Chain Data)

## Upgrade from v1
- v1: 9 sparse monthly observations from secondary reports
- v2: 35 continuous monthly observations from Solana on-chain data
- Truth status upgraded: Estimate (Modeled) -> Finding (Empirical)

## Definition
S2R = (HNT burned via DC purchases) / (HNT issued as rewards)
Computed from Dune Analytics Solana tables.

## Method
- Burns: Negative HNT balance changes on Solana (DC mint program)
- Issuance: Positive HNT balance changes (reward distribution)
- Aggregation: Monthly sum of weekly data

## Exclusions (conservative baseline)
- veHNT locks excluded
- Nova Labs one-time buyback excluded
- Exchange deposits/withdrawals excluded (not sinks)

## Falsification
- S2R overstated if non-DC burns captured
- S2R understated if some DC burns happen off-chain or through proxies
- Cross-validate: compare monthly totals against Helium Foundation reports

## Replication
- Token mint: hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux
- Date range: April 2023 (Solana migration) to present
- Pre-Solana data (2020-2023): from v1 secondary sources
