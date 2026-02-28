#!/usr/bin/env python3
"""
Task 1b: Execute Dune queries for Helium HNT data on Solana.
Uses tokens_solana.transfers table (verified working).
"""
import os
import requests
import json
import time
import pandas as pd

DUNE_API_KEY = os.environ.get("DUNE_API_KEY", "")
HEADERS = {"X-Dune-API-Key": DUNE_API_KEY, "Content-Type": "application/json"}
BASE = "https://api.dune.com/api/v1"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def execute_sql(sql, label):
    """Execute SQL via Dune /sql/execute endpoint."""
    print(f"\nExecuting: {label}")
    resp = requests.post(
        f"{BASE}/sql/execute",
        headers=HEADERS,
        json={"sql": sql, "performance": "medium"},
        timeout=30
    )
    if resp.status_code not in (200, 201):
        print(f"  Execute failed: {resp.status_code} {resp.text[:300]}")
        return None

    execution_id = resp.json().get("execution_id")
    print(f"  Execution ID: {execution_id}")

    # Poll for results (max 10 minutes)
    for attempt in range(60):
        time.sleep(10)
        status = requests.get(
            f"{BASE}/execution/{execution_id}/status",
            headers=HEADERS, timeout=30
        )
        sdata = status.json()
        state = sdata.get("state", "UNKNOWN")
        if attempt % 3 == 0:
            print(f"  Poll {attempt+1}: {state}")

        if state == "QUERY_STATE_COMPLETED":
            results = requests.get(
                f"{BASE}/execution/{execution_id}/results",
                headers=HEADERS, timeout=60
            )
            data = results.json()
            rows = data.get("result", {}).get("rows", [])
            with open(os.path.join(OUTPUT_DIR, f"dune_{label}.json"), "w") as f:
                json.dump(data, f, indent=2)
            print(f"  Got {len(rows)} rows")
            return rows
        elif "FAILED" in state or "CANCELLED" in state:
            error = sdata.get("error", "unknown")
            print(f"  Failed: {state} — {error}")
            return None

    print("  Timed out")
    return None


# ============================================================
# HELIUM QUERIES using tokens_solana.transfers
# The HNT mint address is: hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux
# ============================================================

# Query 1: Weekly HNT transfer volume and activity
HNT_WEEKLY_VOLUME_SQL = """
-- HNT weekly transfer volume and activity on Solana
SELECT
    date_trunc('week', block_time) as week,
    COUNT(*) as n_transfers,
    COUNT(DISTINCT tx_signer) as unique_signers,
    SUM(amount_display) as hnt_volume,
    SUM(amount_usd) as volume_usd,
    AVG(amount_usd / NULLIF(amount_display, 0)) as avg_price_usd
FROM tokens_solana.transfers
WHERE token_mint_address = 'hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux'
    AND block_time >= DATE '2023-04-01'
    AND amount_display > 0
GROUP BY 1
ORDER BY 1
"""

# Query 2: HNT transfers TO burn/null addresses (burns)
# The burn address on Solana for HNT is typically the system program or
# specific known addresses. We approximate by looking for large
# concentrating flows to known sink addresses.
HNT_BURN_PROXY_SQL = """
-- HNT transfers to top receiving addresses (identify sinks/burns)
-- Run this first to identify which addresses are burn/treasury sinks
SELECT
    to_owner,
    COUNT(*) as n_received,
    SUM(amount_display) as total_hnt_received,
    SUM(amount_usd) as total_usd_received,
    MIN(block_time) as first_received,
    MAX(block_time) as last_received
FROM tokens_solana.transfers
WHERE token_mint_address = 'hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux'
    AND block_time >= DATE '2023-04-01'
    AND amount_display > 0
GROUP BY 1
ORDER BY total_hnt_received DESC
LIMIT 50
"""

# Query 3: Weekly HNT burns (transfers to known burn addresses)
# Helium DC burn: HNT is sent to the DC mint program which burns it
# The Helium DC mint program on Solana: credMBJhYFzfn7NxBMdU4B8vWpZsMm2bqfWzc2TSfTQ
# The Helium sub-dao treasury: multi-sig or program-controlled
HNT_WEEKLY_BURNS_SQL = """
-- HNT weekly outflows to known Helium program addresses (burn proxy)
-- These addresses are the DC mint program and subDAO treasuries
SELECT
    date_trunc('week', block_time) as week,
    COUNT(*) as burn_txns,
    SUM(amount_display) as hnt_burned,
    SUM(amount_usd) as usd_burned
FROM tokens_solana.transfers
WHERE token_mint_address = 'hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux'
    AND block_time >= DATE '2023-04-01'
    AND amount_display > 0
    AND action = 'burn'
GROUP BY 1
ORDER BY 1
"""

# Query 4: HNT mint (issuance) events
HNT_WEEKLY_ISSUANCE_SQL = """
-- HNT weekly mint events (token issuance)
SELECT
    date_trunc('week', block_time) as week,
    COUNT(*) as mint_txns,
    SUM(amount_display) as hnt_issued,
    SUM(amount_usd) as usd_issued
FROM tokens_solana.transfers
WHERE token_mint_address = 'hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux'
    AND block_time >= DATE '2023-04-01'
    AND amount_display > 0
    AND action = 'mint'
GROUP BY 1
ORDER BY 1
"""

# Query 5: Helium MOBILE token weekly volume
MOBILE_WEEKLY_SQL = """
-- Helium MOBILE token weekly transfer volume
SELECT
    date_trunc('week', block_time) as week,
    COUNT(*) as n_transfers,
    SUM(amount_display) as mobile_volume,
    SUM(amount_usd) as volume_usd,
    COUNT(DISTINCT tx_signer) as unique_signers
FROM tokens_solana.transfers
WHERE token_mint_address = 'mb1eu7TzEc71KxDpsmsKoucSSuuo5mV69gSCQVFkiRG'
    AND block_time >= DATE '2023-04-01'
    AND amount_display > 0
GROUP BY 1
ORDER BY 1
"""

# Query 6: Helium IOT token weekly volume
IOT_WEEKLY_SQL = """
-- Helium IOT token weekly transfer volume
SELECT
    date_trunc('week', block_time) as week,
    COUNT(*) as n_transfers,
    SUM(amount_display) as iot_volume,
    SUM(amount_usd) as volume_usd,
    COUNT(DISTINCT tx_signer) as unique_signers
FROM tokens_solana.transfers
WHERE token_mint_address = 'iotEVVZLEywoTn1QdwNPddxPWszn3zFhEot3MfL9fns'
    AND block_time >= DATE '2023-04-01'
    AND amount_display > 0
GROUP BY 1
ORDER BY 1
"""


if __name__ == "__main__":
    print("=" * 60)
    print("HELIUM DUNE DATA GATHERING")
    print("=" * 60)

    queries = [
        ("hnt_weekly_volume", HNT_WEEKLY_VOLUME_SQL),
        ("hnt_top_receivers", HNT_BURN_PROXY_SQL),
        ("hnt_weekly_burns", HNT_WEEKLY_BURNS_SQL),
        ("hnt_weekly_issuance", HNT_WEEKLY_ISSUANCE_SQL),
        ("mobile_weekly_volume", MOBILE_WEEKLY_SQL),
        ("iot_weekly_volume", IOT_WEEKLY_SQL),
    ]

    results = {}
    for label, sql in queries:
        rows = execute_sql(sql, label)
        results[label] = rows
        time.sleep(3)

    print("\n" + "=" * 60)
    print("HELIUM DUNE SUMMARY")
    print("=" * 60)
    for label, rows in results.items():
        if rows:
            print(f"  {label}: {len(rows)} rows")
        else:
            print(f"  {label}: FAILED")

    # Quick sanity check on volume data
    if results.get("hnt_weekly_volume"):
        df = pd.DataFrame(results["hnt_weekly_volume"])
        if 'week' in df.columns:
            df['week'] = pd.to_datetime(df['week'])
            print(f"\n  HNT Volume: {df['week'].min().date()} to {df['week'].max().date()}")
            if 'hnt_volume' in df.columns:
                print(f"  Total HNT transferred: {df['hnt_volume'].sum():,.0f}")
            if 'volume_usd' in df.columns:
                print(f"  Total USD volume: ${df['volume_usd'].sum():,.0f}")
