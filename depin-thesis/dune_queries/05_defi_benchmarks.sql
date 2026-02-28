-- ============================================================
-- Query: DeFi Governance Concentration Benchmarks
-- Paper: Paper 1 ("Tokenomics as Institutional Design")
-- Table: Table 2 subset (Pub1) — DeFi benchmark subset (6 protocols on Ethereum)
-- Chain: Ethereum (all 7 DeFi governance tokens are ERC-20)
-- Snapshot: February 2026 (adjust {{snapshot_date}})
-- Author: Zach Zukowski
-- Dependencies: Dune Analytics account (free tier sufficient)
-- Known limitations:
--   - Uses raw token balances, not delegated voting power
--   - Curve: veCRV locking distorts circulating supply picture
--   - Exchange addresses excluded heuristically via labels
--   - Top-1000 holder cutoff may miss long-tail dynamics
-- ============================================================

-- This is a focused version of 01_governance_hhi.sql for the
-- 7 DeFi protocols used as benchmarks against DePIN.

WITH defi_tokens AS (
    SELECT * FROM (VALUES
        (0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984, 'UNI',  'Uniswap',   18),
        (0xc00e94Cb662C3520282E6f5717214004A7f26888, 'COMP', 'Compound',  18),
        (0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2, 'MKR',  'MakerDAO',  18),
        (0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9, 'AAVE', 'Aave',      18),
        (0xD533a949740bb3306d119CC777fa900bA034cd52, 'CRV',  'Curve',     18),
        (0xc944E90C64B2c07662A292be6244BDf05Cda44a7, 'GRT',  'The Graph', 18)
        -- WARNING: OP (0x4200...0042) is an Optimism L2 token.
        -- Querying erc20_ethereum.evt_Transfer for this address returns
        -- zero results. Run 01_governance_hhi.sql Part B on Optimism chain
        -- instead. The row is commented out here to prevent silent failures.
        -- (0x4200000000000000000000000000000000000042, 'OP', 'Optimism', 18)
    ) AS t(token_address, symbol, protocol, decimals)
),

balances AS (
    SELECT
        t.protocol, t.symbol,
        holder, SUM(amount) AS balance
    FROM (
        SELECT e.contract_address AS token_address,
               e."to" AS holder,
               CAST(e.value AS DOUBLE) / POWER(10, t.decimals) AS amount
        FROM erc20_ethereum.evt_Transfer e
        INNER JOIN defi_tokens t ON e.contract_address = t.token_address
        WHERE e.evt_block_time <= CAST('{{snapshot_date}}' AS TIMESTAMP)
          AND e."to" != 0x0000000000000000000000000000000000000000

        UNION ALL

        SELECT e.contract_address AS token_address,
               e."from" AS holder,
               -1.0 * CAST(e.value AS DOUBLE) / POWER(10, t.decimals) AS amount
        FROM erc20_ethereum.evt_Transfer e
        INNER JOIN defi_tokens t ON e.contract_address = t.token_address
        WHERE e.evt_block_time <= CAST('{{snapshot_date}}' AS TIMESTAMP)
          AND e."from" != 0x0000000000000000000000000000000000000000
    ) flows
    INNER JOIN defi_tokens t ON flows.token_address = t.token_address
    GROUP BY t.protocol, t.symbol, holder
    HAVING SUM(amount) > 0
),

-- Exclude exchange addresses
filtered AS (
    SELECT b.protocol, b.symbol, b.holder, b.balance
    FROM balances b
    LEFT JOIN labels.addresses la
        ON b.holder = la.address AND la.blockchain = 'ethereum'
    WHERE (la.name IS NULL OR la.name NOT LIKE '%Exchange%')
      AND b.holder NOT IN (
          0x0000000000000000000000000000000000000000,
          0x000000000000000000000000000000000000dEaD
      )
),

ranked AS (
    SELECT
        protocol, symbol, holder, balance,
        balance / SUM(balance) OVER (PARTITION BY protocol) AS share,
        ROW_NUMBER() OVER (PARTITION BY protocol ORDER BY balance DESC) AS rank,
        COUNT(*) OVER (PARTITION BY protocol) AS n_holders
    FROM filtered
),

top_holders AS (
    SELECT * FROM ranked WHERE rank <= 1000
)

SELECT
    protocol,
    symbol,
    'DeFi' AS category,
    'Ethereum' AS chain,
    ROUND(SUM(share * share), 6) AS hhi,
    ROUND(1.0 - 2.0 * SUM(share * (MAX(n_holders) + 1 - rank))
        / (MAX(n_holders) * SUM(share)), 4) AS gini,
    ROUND(MAX(CASE WHEN rank = 1 THEN share END), 4) AS top_1_share,
    ROUND(SUM(CASE WHEN rank <= 5 THEN share ELSE 0 END), 4) AS top_5_share,
    ROUND(SUM(CASE WHEN rank <= 10 THEN share ELSE 0 END), 4) AS top_10_share,
    MAX(n_holders) AS n_holders,
    CAST('{{snapshot_date}}' AS DATE) AS snapshot_date
FROM top_holders
GROUP BY protocol, symbol
ORDER BY hhi ASC;
