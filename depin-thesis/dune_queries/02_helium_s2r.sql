-- ============================================================
-- Query: Helium Monthly S2R (Burns vs. Issuance)
-- Paper: Paper 2 ("GeoDePIN: Design Patterns")
-- Table: Table 2 (Pub2) — Helium S2R Trajectory (34 months)
-- Figure: Figure 2 (Pub2) — S2R Timeline
-- Chain: Solana
-- Time Range: May 2023 (post-Solana migration) to February 2026
-- Author: Zach Zukowski
-- Dependencies: Dune Analytics account (free tier sufficient)
-- Known limitations:
--   - HNT mint address must be verified on Solana Explorer
--   - Solana table names may vary across Dune schema versions
--   - Pre-migration (L1 Helium) burns are excluded by design
--   - April 2023 excluded: anomalous migration-month issuance
-- ============================================================

-- HNT Mint Address on Solana:
-- hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux
-- (Verify at: https://explorer.solana.com/address/hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux)

-- APPROACH A: Using solana.transfers (if available)
-- Captures mint (issuance) and burn events for HNT token.

WITH monthly_burns AS (
    SELECT
        DATE_TRUNC('month', block_time) AS month,
        SUM(amount / 1e8) AS hnt_burned  -- HNT has 8 decimals
    FROM tokens_solana.transfers
    WHERE token_mint_address = 'hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux'
      AND action = 'burn'
      AND block_time >= TIMESTAMP '2023-05-01'
      AND block_time < TIMESTAMP '2026-03-01'
    GROUP BY 1
),

monthly_issuance AS (
    SELECT
        DATE_TRUNC('month', block_time) AS month,
        SUM(amount / 1e8) AS hnt_issued
    FROM tokens_solana.transfers
    WHERE token_mint_address = 'hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux'
      AND action = 'mint'
      AND block_time >= TIMESTAMP '2023-05-01'
      AND block_time < TIMESTAMP '2026-03-01'
    GROUP BY 1
),

combined AS (
    SELECT
        COALESCE(b.month, i.month) AS month,
        COALESCE(b.hnt_burned, 0) AS hnt_burned,
        COALESCE(i.hnt_issued, 0) AS hnt_issued
    FROM monthly_burns b
    FULL OUTER JOIN monthly_issuance i ON b.month = i.month
)

SELECT
    month,
    hnt_burned,
    hnt_issued,
    CASE
        WHEN hnt_issued > 0 THEN hnt_burned / hnt_issued
        ELSE NULL
    END AS s2r,
    -- Fiscal regime classification
    CASE
        WHEN hnt_issued > 0 AND hnt_burned / hnt_issued >= 1.0 THEN 'net_deflationary'
        WHEN hnt_issued > 0 AND hnt_burned / hnt_issued >= 0.35 THEN 'approaching_parity'
        WHEN hnt_issued > 0 AND hnt_burned / hnt_issued >= 0.10 THEN 'emerging_demand'
        ELSE 'subsidy_dependent'
    END AS fiscal_regime,
    -- Running cumulative
    SUM(hnt_burned) OVER (ORDER BY month) AS cumulative_burned,
    SUM(hnt_issued) OVER (ORDER BY month) AS cumulative_issued,
    SUM(hnt_burned) OVER (ORDER BY month)
        / NULLIF(SUM(hnt_issued) OVER (ORDER BY month), 0) AS cumulative_s2r
FROM combined
ORDER BY month;


-- ============================================================
-- APPROACH B: Using spl_token_solana event tables
-- If tokens_solana.transfers is unavailable, try this variant.
-- ============================================================

-- WITH burn_events AS (
--     SELECT
--         DATE_TRUNC('month', evt_block_time) AS month,
--         SUM(CAST(amount AS DOUBLE) / 1e8) AS hnt_burned
--     FROM spl_token_solana.spl_token_evt_burn
--     WHERE account_mint = 'hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux'
--       AND evt_block_time >= TIMESTAMP '2023-05-01'
--       AND evt_block_time < TIMESTAMP '2026-03-01'
--     GROUP BY 1
-- ),
-- mint_events AS (
--     SELECT
--         DATE_TRUNC('month', evt_block_time) AS month,
--         SUM(CAST(amount AS DOUBLE) / 1e8) AS hnt_issued
--     FROM spl_token_solana.spl_token_evt_mintTo
--     WHERE account = 'hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux'
--       AND evt_block_time >= TIMESTAMP '2023-05-01'
--       AND evt_block_time < TIMESTAMP '2026-03-01'
--     GROUP BY 1
-- )
-- SELECT
--     COALESCE(b.month, m.month) AS month,
--     COALESCE(b.hnt_burned, 0) AS hnt_burned,
--     COALESCE(m.hnt_issued, 0) AS hnt_issued,
--     CASE WHEN m.hnt_issued > 0
--          THEN b.hnt_burned / m.hnt_issued ELSE NULL END AS s2r
-- FROM burn_events b
-- FULL OUTER JOIN mint_events m ON b.month = m.month
-- ORDER BY 1;
