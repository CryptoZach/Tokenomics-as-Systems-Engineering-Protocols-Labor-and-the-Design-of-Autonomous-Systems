-- ============================================================
-- Query: DIMO Developer License Burn S2R
-- Paper: Paper 2 ("GeoDePIN: Design Patterns")
-- Section: V.B (Pub2) — Protocol Profile (DIMO)
-- Chain: Polygon
-- Time Range: January 2024 to February 2026
-- Author: Zach Zukowski
-- Dependencies: Dune Analytics account (free tier sufficient)
-- Known limitations:
--   - Burns detected via transfers to null address (0x000...000)
--   - Issuance detected via transfers from null address (mints)
--   - Developer License burns are the primary sink mechanism
--   - DIMO also has staking locks (not captured as burns here)
--   - S2R here is burns-only; burns+locks would be higher
-- ============================================================

-- DIMO token on Polygon:
-- 0xE261D618a959aFfFd53168Cd07D12E37B26761db
-- Decimals: 18

WITH monthly_burns AS (
    SELECT
        DATE_TRUNC('month', evt_block_time) AS month,
        SUM(CAST(value AS DOUBLE) / 1e18) AS dimo_burned
    FROM erc20_polygon.evt_Transfer
    WHERE contract_address = 0xE261D618a959aFfFd53168Cd07D12E37B26761db
      -- Burns: transfers to null address or known burn address
      AND "to" IN (
          0x0000000000000000000000000000000000000000,
          0x000000000000000000000000000000000000dEaD
      )
      AND evt_block_time >= TIMESTAMP '2024-01-01'
      AND evt_block_time < TIMESTAMP '2026-03-01'
    GROUP BY 1
),

monthly_issuance AS (
    SELECT
        DATE_TRUNC('month', evt_block_time) AS month,
        SUM(CAST(value AS DOUBLE) / 1e18) AS dimo_issued
    FROM erc20_polygon.evt_Transfer
    WHERE contract_address = 0xE261D618a959aFfFd53168Cd07D12E37B26761db
      -- Mints: transfers from null address
      AND "from" = 0x0000000000000000000000000000000000000000
      AND evt_block_time >= TIMESTAMP '2024-01-01'
      AND evt_block_time < TIMESTAMP '2026-03-01'
    GROUP BY 1
)

SELECT
    COALESCE(b.month, i.month) AS month,
    COALESCE(b.dimo_burned, 0) AS dimo_burned,
    COALESCE(i.dimo_issued, 0) AS dimo_issued,
    CASE
        WHEN i.dimo_issued > 0
        THEN b.dimo_burned / i.dimo_issued
        ELSE NULL
    END AS s2r,
    -- Fiscal regime
    CASE
        WHEN i.dimo_issued > 0 AND b.dimo_burned / i.dimo_issued >= 1.0
            THEN 'net_deflationary'
        WHEN i.dimo_issued > 0 AND b.dimo_burned / i.dimo_issued >= 0.35
            THEN 'approaching_parity'
        WHEN i.dimo_issued > 0 AND b.dimo_burned / i.dimo_issued >= 0.10
            THEN 'emerging_demand'
        ELSE 'subsidy_dependent'
    END AS fiscal_regime,
    -- Running totals
    SUM(COALESCE(b.dimo_burned, 0)) OVER (ORDER BY COALESCE(b.month, i.month))
        AS cumulative_burned,
    SUM(COALESCE(i.dimo_issued, 0)) OVER (ORDER BY COALESCE(b.month, i.month))
        AS cumulative_issued
FROM monthly_burns b
FULL OUTER JOIN monthly_issuance i ON b.month = i.month
ORDER BY 1;
