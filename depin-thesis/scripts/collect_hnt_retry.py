#!/usr/bin/env python3
"""
Retry HNT holder collection using alternative Dune queries and Helium APIs.
"""
import os
import sys
import requests
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "expansion"))
from config import DUNE_API_KEY

HEADERS = {"X-Dune-API-Key": DUNE_API_KEY, "Content-Type": "application/json"}
BASE = "https://api.dune.com/api/v1"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

HNT_MINT = "hntyVP6YFm1Hg25TN9WGLqM12b8TQv4smRNhB3XMv1b"


def execute_inline(sql, label, retries=1):
    """Execute inline Dune query."""
    for attempt in range(retries + 1):
        try:
            print(f"\n  Executing: {label} (attempt {attempt + 1})")
            resp = requests.post(
                f"{BASE}/sql/execute",
                headers=HEADERS,
                json={"sql": sql, "performance": "medium"},
                timeout=30,
            )
            if resp.status_code not in (200, 201):
                print(f"    Submit failed: {resp.status_code} {resp.text[:300]}")
                if attempt < retries:
                    time.sleep(5)
                    continue
                return None

            eid = resp.json().get("execution_id")
            print(f"    Execution ID: {eid}")

            for poll in range(90):
                time.sleep(10)
                s = requests.get(
                    f"{BASE}/execution/{eid}/status", headers=HEADERS, timeout=30
                )
                state = s.json().get("state", "?")
                if poll % 6 == 0:
                    print(f"    Poll {poll + 1}: {state}")
                if state == "QUERY_STATE_COMPLETED":
                    r = requests.get(
                        f"{BASE}/execution/{eid}/results",
                        headers=HEADERS,
                        timeout=60,
                    )
                    data = r.json()
                    rows = data.get("result", {}).get("rows", [])
                    fname = os.path.join(OUTPUT_DIR, f"dune_{label}.json")
                    with open(fname, "w") as f:
                        json.dump(data, f, indent=2)
                    print(f"    Got {len(rows)} rows -> {fname}")
                    return rows
                elif "FAILED" in state or "CANCELLED" in state:
                    err = s.json().get("error", "unknown")
                    print(f"    {state}: {err}")
                    break
        except Exception as e:
            print(f"    Error: {e}")
            if attempt < retries:
                time.sleep(5)
    return None


def try_approach_1():
    """Approach 1: Use tokens_solana.fungible_token_balances (newer table)."""
    print("\n=== APPROACH 1: tokens_solana.fungible_token_balances ===")
    sql = f"""
SELECT
    account_owner AS address,
    balance / POWER(10, 8) AS balance
FROM tokens_solana.fungible_token_balances
WHERE token_mint_address = '{HNT_MINT}'
AND balance > 0
ORDER BY balance DESC
LIMIT 1000
"""
    return execute_inline(sql, "hnt_approach1_fungible_balances")


def try_approach_2():
    """Approach 2: Use solana.account_activity to derive balances."""
    print("\n=== APPROACH 2: spl_token_solana table ===")
    sql = f"""
SELECT
    token_balance_owner AS address,
    token_balance / POWER(10, 8) AS balance
FROM solana.account_activity
WHERE token_mint_address = '{HNT_MINT}'
AND token_balance > 0
AND block_time >= NOW() - INTERVAL '7' DAY
ORDER BY token_balance DESC
LIMIT 1000
"""
    return execute_inline(sql, "hnt_approach2_account_activity")


def try_approach_3():
    """Approach 3: Try the raw Solana token accounts."""
    print("\n=== APPROACH 3: Raw query for known Helium addresses ===")
    # Check if the mint is actually indexed - query any transfers at all
    sql = f"""
SELECT COUNT(*) AS cnt
FROM tokens_solana.transfers
WHERE token_mint_address = '{HNT_MINT}'
AND block_time >= NOW() - INTERVAL '30' DAY
"""
    return execute_inline(sql, "hnt_approach3_count_check")


def try_helium_api():
    """Try Helium's own APIs for token holder data."""
    print("\n=== HELIUM API: Checking for HNT holder endpoints ===")

    # Try Solana FM API
    endpoints = [
        ("SolanaFM token holders", f"https://api.solana.fm/v0/tokens/{HNT_MINT}/holders?limit=100"),
        ("Helius token holders", f"https://api.helius.xyz/v0/token-metadata?api-key=no-key"),
    ]

    for name, url in endpoints:
        try:
            print(f"  Trying {name}...")
            resp = requests.get(url, timeout=15)
            print(f"    Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"    Response keys: {list(data.keys()) if isinstance(data, dict) else f'{len(data)} items'}")
                return data
        except Exception as e:
            print(f"    Failed: {e}")

    return None


def main():
    print("=" * 70)
    print("HNT HOLDER COLLECTION RETRY")
    print("=" * 70)

    # Approach 1: Materialized balance table
    rows = try_approach_1()
    if rows and len(rows) > 0:
        print(f"\n  SUCCESS with approach 1: {len(rows)} holders")
        return rows

    # Approach 2: Account activity
    rows = try_approach_2()
    if rows and len(rows) > 0:
        print(f"\n  SUCCESS with approach 2: {len(rows)} holders")
        return rows

    # Approach 3: Check if HNT is even indexed
    rows = try_approach_3()
    if rows:
        print(f"  HNT transfers in last 30 days: {rows[0].get('cnt', 0) if rows else 0}")

    # Approach 4: External API
    try_helium_api()

    print("\n  All approaches exhausted for HNT.")
    print("  HNT may not be indexed in Dune's Solana token tables.")
    print("  This is common for native protocol tokens that migrated from L1.")


if __name__ == "__main__":
    main()
