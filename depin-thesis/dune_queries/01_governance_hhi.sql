-- ============================================================
-- Query: Multi-Chain Governance Concentration (HHI, Gini, Top-N)
-- Paper: Paper 1 ("Tokenomics as Institutional Design")
-- Table: Table 2 (Pub1) / Table 6 (Pub2) — Governance Concentration Cross-Section
-- Chain: Multi (Ethereum, Polygon, Arbitrum, Solana)
-- Snapshot: February 2026 (adjust {{snapshot_date}} for replication)
-- Author: Zach Zukowski
-- Dependencies: Dune Analytics account (free tier sufficient)
-- Known limitations:
--   - Livepeer (LPT): Arbitrum schema prevented governance query
--   - Hivemapper (HONEY): Solana token not indexed for governance
--   - IoTeX (IOTX): Uses Ethereum ERC-20 representation, not L1
--   - Exchange exclusion is heuristic (labels + known addresses)
--   - Single-point snapshot; panel data would strengthen claims
-- ============================================================

-- This query computes HHI, Gini, and Top-N concentration for
-- governance tokens across multiple chains. Run each CTE block
-- separately if Dune times out, or use the parameterized
-- single-token version at the bottom.

-- ============================================================
-- PART A: Ethereum ERC-20 tokens (UNI, COMP, MKR, AAVE, CRV,
--         OP, GRT, IOTX-ERC20, ANYONE)
-- ============================================================

WITH token_list AS (
    SELECT * FROM (VALUES
        (0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984, 'UNI',  'Uniswap',   18),
        (0xc00e94Cb662C3520282E6f5717214004A7f26888, 'COMP', 'Compound',  18),
        (0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2, 'MKR',  'MakerDAO',  18),
        (0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9, 'AAVE', 'Aave',      18),
        (0xD533a949740bb3306d119CC777fa900bA034cd52, 'CRV',  'Curve',     18),
        (0xc944E90C64B2c07662A292be6244BDf05Cda44a7, 'GRT',  'The Graph', 18),
        (0x6fB3e0A217407EFFf7Ca062D46c26E5d60a14d69, 'IOTX', 'IoTeX',     18)
    ) AS t(token_address, symbol, protocol, decimals)
),

-- Compute net balances from transfer events
eth_balances AS (
    SELECT
        t.protocol,
        t.symbol,
        holder,
        SUM(amount) AS balance
    FROM (
        -- Inflows
        SELECT
            e.contract_address AS token_address,
            e."to" AS holder,
            CAST(e.value AS DOUBLE) / POWER(10, t.decimals) AS amount
        FROM erc20_ethereum.evt_Transfer e
        INNER JOIN token_list t ON e.contract_address = t.token_address
        WHERE e.evt_block_time <= CAST('{{snapshot_date}}' AS TIMESTAMP)
          AND e."to" != 0x0000000000000000000000000000000000000000

        UNION ALL

        -- Outflows (negative)
        SELECT
            e.contract_address AS token_address,
            e."from" AS holder,
            -1.0 * CAST(e.value AS DOUBLE) / POWER(10, t.decimals) AS amount
        FROM erc20_ethereum.evt_Transfer e
        INNER JOIN token_list t ON e.contract_address = t.token_address
        WHERE e.evt_block_time <= CAST('{{snapshot_date}}' AS TIMESTAMP)
          AND e."from" != 0x0000000000000000000000000000000000000000
    ) flows
    INNER JOIN token_list t ON flows.token_address = t.token_address
    GROUP BY t.protocol, t.symbol, holder
    HAVING SUM(amount) > 0
),

-- Exclude known exchange addresses using Dune labels
eth_filtered AS (
    SELECT
        eb.protocol,
        eb.symbol,
        eb.holder,
        eb.balance
    FROM eth_balances eb
    LEFT JOIN labels.addresses la
        ON eb.holder = la.address
        AND la.blockchain = 'ethereum'
    WHERE (
        la.name IS NULL
        OR la.name NOT LIKE '%Exchange%'
    )
    -- Also exclude null/burn addresses
    AND eb.holder != 0x0000000000000000000000000000000000000000
    AND eb.holder != 0x000000000000000000000000000000000000dEaD
),

-- Rank and compute shares per token
eth_ranked AS (
    SELECT
        protocol,
        symbol,
        holder,
        balance,
        balance / SUM(balance) OVER (PARTITION BY protocol) AS share,
        ROW_NUMBER() OVER (PARTITION BY protocol ORDER BY balance DESC) AS rank,
        COUNT(*) OVER (PARTITION BY protocol) AS n_holders
    FROM eth_filtered
),

-- Keep top 1000 holders per token for tractability
eth_top AS (
    SELECT * FROM eth_ranked WHERE rank <= 1000
),

-- Compute concentration metrics
eth_metrics AS (
    SELECT
        protocol,
        symbol,
        'Ethereum' AS chain,
        -- HHI = sum of squared shares
        SUM(share * share) AS hhi,
        -- Gini coefficient (Brown's formula)
        1.0 - 2.0 * SUM(share * (MAX(n_holders) + 1 - rank))
            / (MAX(n_holders) * SUM(share)) AS gini,
        -- Top-1 share
        MAX(CASE WHEN rank = 1 THEN share END) AS top_1_share,
        -- Top-5 share
        SUM(CASE WHEN rank <= 5 THEN share ELSE 0 END) AS top_5_share,
        -- Top-10 share
        SUM(CASE WHEN rank <= 10 THEN share ELSE 0 END) AS top_10_share,
        MAX(n_holders) AS n_holders,
        CAST('{{snapshot_date}}' AS DATE) AS snapshot_date
    FROM eth_top
    GROUP BY protocol, symbol
)

SELECT * FROM eth_metrics
ORDER BY hhi ASC;

-- ============================================================
-- PART B: Optimism (OP token)
-- Run separately on Dune with chain = Optimism
-- ============================================================

-- WITH op_balances AS (
--     SELECT
--         holder,
--         SUM(amount) AS balance
--     FROM (
--         SELECT "to" AS holder,
--                CAST(value AS DOUBLE) / 1e18 AS amount
--         FROM erc20_optimism.evt_Transfer
--         WHERE contract_address = 0x4200000000000000000000000000000000000042
--           AND evt_block_time <= CAST('{{snapshot_date}}' AS TIMESTAMP)
--           AND "to" != 0x0000000000000000000000000000000000000000
--         UNION ALL
--         SELECT "from" AS holder,
--                -1.0 * CAST(value AS DOUBLE) / 1e18 AS amount
--         FROM erc20_optimism.evt_Transfer
--         WHERE contract_address = 0x4200000000000000000000000000000000000042
--           AND evt_block_time <= CAST('{{snapshot_date}}' AS TIMESTAMP)
--           AND "from" != 0x0000000000000000000000000000000000000000
--     ) flows
--     GROUP BY holder
--     HAVING SUM(amount) > 0
-- ),
-- op_ranked AS (
--     SELECT holder, balance,
--            balance / SUM(balance) OVER () AS share,
--            ROW_NUMBER() OVER (ORDER BY balance DESC) AS rank,
--            COUNT(*) OVER () AS n_holders
--     FROM op_balances
-- ),
-- op_top AS (SELECT * FROM op_ranked WHERE rank <= 1000)
-- SELECT 'Optimism' AS protocol, 'OP' AS symbol, 'Optimism' AS chain,
--     SUM(share * share) AS hhi,
--     1.0 - 2.0 * SUM(share * (MAX(n_holders) + 1 - rank))
--         / (MAX(n_holders) * SUM(share)) AS gini,
--     MAX(CASE WHEN rank = 1 THEN share END) AS top_1_share,
--     SUM(CASE WHEN rank <= 5 THEN share ELSE 0 END) AS top_5_share,
--     SUM(CASE WHEN rank <= 10 THEN share ELSE 0 END) AS top_10_share,
--     MAX(n_holders) AS n_holders,
--     CAST('{{snapshot_date}}' AS DATE) AS snapshot_date
-- FROM op_top;


-- ============================================================
-- PART C: Polygon (DIMO token)
-- Run separately on Dune with chain = Polygon
-- ============================================================

-- WITH dimo_balances AS (
--     SELECT holder, SUM(amount) AS balance FROM (
--         SELECT "to" AS holder, CAST(value AS DOUBLE) / 1e18 AS amount
--         FROM erc20_polygon.evt_Transfer
--         WHERE contract_address = 0xE261D618a959aFfFd53168Cd07D12E37B26761db
--           AND evt_block_time <= CAST('{{snapshot_date}}' AS TIMESTAMP)
--           AND "to" != 0x0000000000000000000000000000000000000000
--         UNION ALL
--         SELECT "from" AS holder, -1.0 * CAST(value AS DOUBLE) / 1e18 AS amount
--         FROM erc20_polygon.evt_Transfer
--         WHERE contract_address = 0xE261D618a959aFfFd53168Cd07D12E37B26761db
--           AND evt_block_time <= CAST('{{snapshot_date}}' AS TIMESTAMP)
--           AND "from" != 0x0000000000000000000000000000000000000000
--     ) flows
--     GROUP BY holder HAVING SUM(amount) > 0
-- ),
-- dimo_ranked AS (
--     SELECT holder, balance,
--            balance / SUM(balance) OVER () AS share,
--            ROW_NUMBER() OVER (ORDER BY balance DESC) AS rank,
--            COUNT(*) OVER () AS n_holders
--     FROM dimo_balances
-- ),
-- dimo_top AS (SELECT * FROM dimo_ranked WHERE rank <= 1000)
-- SELECT 'DIMO' AS protocol, 'DIMO' AS symbol, 'Polygon' AS chain,
--     SUM(share * share) AS hhi,
--     1.0 - 2.0 * SUM(share * (MAX(n_holders) + 1 - rank))
--         / (MAX(n_holders) * SUM(share)) AS gini,
--     MAX(CASE WHEN rank = 1 THEN share END) AS top_1_share,
--     SUM(CASE WHEN rank <= 5 THEN share ELSE 0 END) AS top_5_share,
--     SUM(CASE WHEN rank <= 10 THEN share ELSE 0 END) AS top_10_share,
--     MAX(n_holders) AS n_holders,
--     CAST('{{snapshot_date}}' AS DATE) AS snapshot_date
-- FROM dimo_top;


-- ============================================================
-- PART D: Arbitrum (WeatherXM WXM token)
-- Run separately on Dune with chain = Arbitrum
-- Token address: look up WXM on Arbiscan and substitute below
-- ============================================================

-- WITH wxm_balances AS (
--     SELECT holder, SUM(amount) AS balance FROM (
--         SELECT "to" AS holder, CAST(value AS DOUBLE) / 1e18 AS amount
--         FROM erc20_arbitrum.evt_Transfer
--         WHERE contract_address = {{wxm_token_address}}
--           AND evt_block_time <= CAST('{{snapshot_date}}' AS TIMESTAMP)
--           AND "to" != 0x0000000000000000000000000000000000000000
--         UNION ALL
--         SELECT "from" AS holder, -1.0 * CAST(value AS DOUBLE) / 1e18 AS amount
--         FROM erc20_arbitrum.evt_Transfer
--         WHERE contract_address = {{wxm_token_address}}
--           AND evt_block_time <= CAST('{{snapshot_date}}' AS TIMESTAMP)
--           AND "from" != 0x0000000000000000000000000000000000000000
--     ) flows
--     GROUP BY holder HAVING SUM(amount) > 0
-- ),
-- wxm_ranked AS (
--     SELECT holder, balance,
--            balance / SUM(balance) OVER () AS share,
--            ROW_NUMBER() OVER (ORDER BY balance DESC) AS rank,
--            COUNT(*) OVER () AS n_holders
--     FROM wxm_balances
-- ),
-- wxm_top AS (SELECT * FROM wxm_ranked WHERE rank <= 1000)
-- SELECT 'WeatherXM' AS protocol, 'WXM' AS symbol, 'Arbitrum' AS chain,
--     SUM(share * share) AS hhi,
--     1.0 - 2.0 * SUM(share * (MAX(n_holders) + 1 - rank))
--         / (MAX(n_holders) * SUM(share)) AS gini,
--     MAX(CASE WHEN rank = 1 THEN share END) AS top_1_share,
--     SUM(CASE WHEN rank <= 5 THEN share ELSE 0 END) AS top_5_share,
--     SUM(CASE WHEN rank <= 10 THEN share ELSE 0 END) AS top_10_share,
--     MAX(n_holders) AS n_holders,
--     CAST('{{snapshot_date}}' AS DATE) AS snapshot_date
-- FROM wxm_top;


-- ============================================================
-- PART E: Solana (GRASS token)
-- Solana uses SPL token accounts; schema differs from EVM.
-- ============================================================

-- WITH grass_balances AS (
--     SELECT
--         account_address AS holder,
--         token_balance_owner AS owner,
--         balance / 1e9 AS balance  -- GRASS has 9 decimals
--     FROM solana.account_activity  -- or tokens_solana.fungible
--     WHERE token_mint_address = '{{grass_mint_address}}'
--       AND balance > 0
-- ),
-- grass_ranked AS (
--     SELECT owner AS holder, balance,
--            balance / SUM(balance) OVER () AS share,
--            ROW_NUMBER() OVER (ORDER BY balance DESC) AS rank,
--            COUNT(*) OVER () AS n_holders
--     FROM grass_balances
-- ),
-- grass_top AS (SELECT * FROM grass_ranked WHERE rank <= 1000)
-- SELECT 'Grass' AS protocol, 'GRASS' AS symbol, 'Solana' AS chain,
--     SUM(share * share) AS hhi,
--     1.0 - 2.0 * SUM(share * (MAX(n_holders) + 1 - rank))
--         / (MAX(n_holders) * SUM(share)) AS gini,
--     MAX(CASE WHEN rank = 1 THEN share END) AS top_1_share,
--     SUM(CASE WHEN rank <= 5 THEN share ELSE 0 END) AS top_5_share,
--     SUM(CASE WHEN rank <= 10 THEN share ELSE 0 END) AS top_10_share,
--     MAX(n_holders) AS n_holders,
--     CAST('{{snapshot_date}}' AS DATE) AS snapshot_date
-- FROM grass_top;


-- ============================================================
-- PARAMETERIZED SINGLE-TOKEN VERSION
-- Use Dune parameters: {{token_address}}, {{chain}}, {{protocol}},
-- {{symbol}}, {{decimals}}, {{snapshot_date}}
-- Uncomment and adapt for any individual token.
-- ============================================================

-- WITH balances AS (
--     SELECT holder, SUM(amount) AS balance FROM (
--         SELECT "to" AS holder, CAST(value AS DOUBLE) / POWER(10, {{decimals}}) AS amount
--         FROM erc20_{{chain}}.evt_Transfer
--         WHERE contract_address = {{token_address}}
--           AND evt_block_time <= CAST('{{snapshot_date}}' AS TIMESTAMP)
--           AND "to" != 0x0000000000000000000000000000000000000000
--         UNION ALL
--         SELECT "from" AS holder, -1.0 * CAST(value AS DOUBLE) / POWER(10, {{decimals}}) AS amount
--         FROM erc20_{{chain}}.evt_Transfer
--         WHERE contract_address = {{token_address}}
--           AND evt_block_time <= CAST('{{snapshot_date}}' AS TIMESTAMP)
--           AND "from" != 0x0000000000000000000000000000000000000000
--     ) flows
--     GROUP BY holder HAVING SUM(amount) > 0
-- ),
-- ranked AS (
--     SELECT holder, balance,
--            balance / SUM(balance) OVER () AS share,
--            ROW_NUMBER() OVER (ORDER BY balance DESC) AS rank,
--            COUNT(*) OVER () AS n_holders
--     FROM balances
-- ),
-- top_holders AS (SELECT * FROM ranked WHERE rank <= 1000)
-- SELECT
--     '{{protocol}}' AS protocol,
--     '{{symbol}}' AS symbol,
--     '{{chain}}' AS chain,
--     SUM(share * share) AS hhi,
--     1.0 - 2.0 * SUM(share * (MAX(n_holders) + 1 - rank))
--         / (MAX(n_holders) * SUM(share)) AS gini,
--     MAX(CASE WHEN rank = 1 THEN share END) AS top_1_share,
--     SUM(CASE WHEN rank <= 5 THEN share ELSE 0 END) AS top_5_share,
--     SUM(CASE WHEN rank <= 10 THEN share ELSE 0 END) AS top_10_share,
--     MAX(n_holders) AS n_holders,
--     CAST('{{snapshot_date}}' AS DATE) AS snapshot_date
-- FROM top_holders;
