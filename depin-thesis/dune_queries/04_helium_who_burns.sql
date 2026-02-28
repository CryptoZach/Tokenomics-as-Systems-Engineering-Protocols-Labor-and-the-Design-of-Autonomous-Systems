-- ============================================================
-- Query: Helium "Who Burns?" — DC Burn Concentration
-- Paper: Paper 2 ("GeoDePIN: Design Patterns")
-- Section: V.A (Pub2) — Burn Concentration Analysis
-- Chain: Solana
-- Time Range: May 2023 to February 2026
-- Author: Zach Zukowski
-- Dependencies: Dune Analytics account (free tier sufficient)
-- Known limitations:
--   - "signer" captures the transaction initiator; some burns
--     may be executed by relay/proxy contracts
--   - Top-5 concentration ~90% indicates single-buyer fragility
--   - Carrier identities (e.g., T-Mobile via Nova Labs) cannot
--     be confirmed on-chain without off-chain mapping
-- ============================================================

-- Part 1: Top 20 burn addresses by volume

WITH burn_events AS (
    SELECT
        signer AS burn_address,
        CAST(amount AS DOUBLE) / 1e8 AS hnt_burned,
        block_time
    FROM tokens_solana.transfers
    WHERE token_mint_address = 'hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux'
      AND action = 'burn'
      AND block_time >= TIMESTAMP '2023-05-01'
      AND block_time < TIMESTAMP '2026-03-01'
),

burn_by_address AS (
    SELECT
        burn_address,
        SUM(hnt_burned) AS total_burned,
        COUNT(*) AS burn_count,
        MIN(block_time) AS first_burn,
        MAX(block_time) AS last_burn
    FROM burn_events
    GROUP BY burn_address
),

ranked AS (
    SELECT
        burn_address,
        total_burned,
        burn_count,
        first_burn,
        last_burn,
        total_burned / SUM(total_burned) OVER () AS burn_share,
        ROW_NUMBER() OVER (ORDER BY total_burned DESC) AS rank
    FROM burn_by_address
)

SELECT
    rank,
    burn_address,
    total_burned,
    burn_count,
    ROUND(burn_share, 6) AS burn_share,
    ROUND(SUM(burn_share) OVER (ORDER BY rank), 6) AS cumulative_share,
    first_burn,
    last_burn
FROM ranked
WHERE rank <= 20
ORDER BY rank;


-- ============================================================
-- Part 2: Monthly burn concentration (Top-5 share over time)
-- Shows whether concentration is stable, increasing, or
-- decreasing as the network grows.
-- ============================================================

-- WITH monthly_burns AS (
--     SELECT
--         DATE_TRUNC('month', block_time) AS month,
--         signer AS burn_address,
--         SUM(CAST(amount AS DOUBLE) / 1e8) AS hnt_burned
--     FROM tokens_solana.transfers
--     WHERE token_mint_address = 'hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux'
--       AND action = 'burn'
--       AND block_time >= TIMESTAMP '2023-05-01'
--       AND block_time < TIMESTAMP '2026-03-01'
--     GROUP BY 1, 2
-- ),
-- monthly_ranked AS (
--     SELECT
--         month,
--         burn_address,
--         hnt_burned,
--         hnt_burned / SUM(hnt_burned) OVER (PARTITION BY month) AS share,
--         ROW_NUMBER() OVER (PARTITION BY month ORDER BY hnt_burned DESC) AS rank
--     FROM monthly_burns
-- )
-- SELECT
--     month,
--     COUNT(DISTINCT burn_address) AS n_burn_addresses,
--     SUM(CASE WHEN rank <= 5 THEN share ELSE 0 END) AS top5_share,
--     SUM(CASE WHEN rank = 1 THEN share ELSE 0 END) AS top1_share,
--     SUM(hnt_burned) AS total_monthly_burned
-- FROM monthly_ranked
-- GROUP BY month
-- ORDER BY month;
