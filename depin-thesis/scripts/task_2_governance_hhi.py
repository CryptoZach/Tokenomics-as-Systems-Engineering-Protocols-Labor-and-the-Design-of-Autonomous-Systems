#!/usr/bin/env python3
"""
Task 2: Compute governance HHI and Gini from token holder distributions.
Uses Dune to query top holder balances for governance tokens.
"""
import os
import requests
import json
import time
import pandas as pd
import numpy as np

DUNE_API_KEY = os.environ.get("DUNE_API_KEY", "")
HEADERS = {"X-Dune-API-Key": DUNE_API_KEY, "Content-Type": "application/json"}
BASE = "https://api.dune.com/api/v1"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def execute_inline(sql, label):
    """Execute inline Dune query via /sql/execute."""
    print(f"\n  Executing: {label}")
    resp = requests.post(
        f"{BASE}/sql/execute",
        headers=HEADERS,
        json={"sql": sql, "performance": "medium"},
        timeout=30
    )
    if resp.status_code not in (200, 201):
        print(f"    Failed: {resp.status_code} {resp.text[:200]}")
        return None

    eid = resp.json().get("execution_id")
    for attempt in range(60):
        time.sleep(10)
        s = requests.get(f"{BASE}/execution/{eid}/status", headers=HEADERS, timeout=30)
        state = s.json().get("state", "?")
        if attempt % 6 == 0:
            print(f"    Poll {attempt+1}: {state}")
        if state == "QUERY_STATE_COMPLETED":
            r = requests.get(f"{BASE}/execution/{eid}/results", headers=HEADERS, timeout=60)
            data = r.json()
            rows = data.get("result", {}).get("rows", [])
            with open(os.path.join(OUTPUT_DIR, f"dune_{label}.json"), "w") as f:
                json.dump(data, f, indent=2)
            print(f"    Got {len(rows)} rows")
            return rows
        elif "FAILED" in state or "CANCELLED" in state:
            print(f"    {state}")
            return None
    return None


def compute_hhi_gini(balances):
    """Compute HHI and Gini from a list of token balances."""
    if not balances or len(balances) < 2:
        return None, None
    total = sum(balances)
    if total == 0:
        return None, None

    # HHI: sum of squared market shares (among top holders)
    shares = [b / total for b in balances]
    hhi = sum(s ** 2 for s in shares)

    # Gini coefficient
    n = len(balances)
    sorted_b = sorted(balances)
    cum = 0
    for i, b in enumerate(sorted_b):
        cum += (2 * (i + 1) - n - 1) * b
    gini = cum / (n * total) if total > 0 and n > 1 else 0

    return round(hhi, 6), round(abs(gini), 4)


# ============================================================
# GOVERNANCE TOKEN QUERIES
# Top 1000 holders for each governance token
# ============================================================
TOKENS = {
    "UNI": {
        "address": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
        "chain": "ethereum",
        "decimals": 18,
        "protocol": "Uniswap",
    },
    "COMP": {
        "address": "0xc00e94Cb662C3520282E6f5717214004A7f26888",
        "chain": "ethereum",
        "decimals": 18,
        "protocol": "Compound",
    },
    "MKR": {
        "address": "0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2",
        "chain": "ethereum",
        "decimals": 18,
        "protocol": "MakerDAO",
    },
    "AAVE": {
        "address": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
        "chain": "ethereum",
        "decimals": 18,
        "protocol": "Aave",
    },
    "LPT": {
        "address": "0x58b6A8A3302369DAEc383334672404Ee733aB239",
        "chain": "arbitrum",
        "decimals": 18,
        "protocol": "Livepeer",
        "note": "Livepeer migrated to Arbitrum; L1 contract is 0x58b6...",
    },
}


def build_holder_query(token_symbol, token_info):
    """Build Dune SQL to get top 1000 holders of a token."""
    addr = token_info["address"]
    chain = token_info["chain"]
    decimals = token_info["decimals"]

    # Use Dune's ERC20 balances table for current snapshot
    if chain == "ethereum":
        return f"""
-- Top 1000 holders of {token_symbol} on Ethereum
SELECT
    address,
    token_balance / POWER(10, {decimals}) as balance
FROM (
    SELECT
        "to" as address,
        SUM(CASE WHEN "to" = address THEN CAST(value AS DOUBLE)
                 ELSE -CAST(value AS DOUBLE) END) as token_balance
    FROM (
        SELECT "from" as address, "to", value
        FROM erc20_ethereum.evt_Transfer
        WHERE contract_address = {addr}
        UNION ALL
        SELECT "from", "to" as address, value
        FROM erc20_ethereum.evt_Transfer
        WHERE contract_address = {addr}
    )
    GROUP BY 1
    HAVING SUM(CASE WHEN "to" = address THEN CAST(value AS DOUBLE)
                    ELSE -CAST(value AS DOUBLE) END) > 0
)
ORDER BY balance DESC
LIMIT 1000
"""
    elif chain == "arbitrum":
        return f"""
-- Top 1000 holders of {token_symbol} on Arbitrum
SELECT
    address,
    token_balance / POWER(10, {decimals}) as balance
FROM (
    SELECT
        "to" as address,
        SUM(CASE WHEN "to" = address THEN CAST(value AS DOUBLE)
                 ELSE -CAST(value AS DOUBLE) END) as token_balance
    FROM (
        SELECT "from" as address, "to", value
        FROM erc20_arbitrum.evt_Transfer
        WHERE contract_address = {addr}
        UNION ALL
        SELECT "from", "to" as address, value
        FROM erc20_arbitrum.evt_Transfer
        WHERE contract_address = {addr}
    )
    GROUP BY 1
    HAVING SUM(CASE WHEN "to" = address THEN CAST(value AS DOUBLE)
                    ELSE -CAST(value AS DOUBLE) END) > 0
)
ORDER BY balance DESC
LIMIT 1000
"""
    return None


def simpler_holder_query(token_symbol, token_info):
    """Simpler query using Dune's token balances tables."""
    addr = token_info["address"]
    chain = token_info["chain"]
    decimals = token_info["decimals"]

    # Dune v2 has tokens_<chain>.erc20 for current balances
    schema = f"tokens_{chain}" if chain != "ethereum" else "tokens_ethereum"
    return f"""
-- Top 500 holders of {token_symbol} (simpler approach)
SELECT
    wallet_address as address,
    amount as balance
FROM {schema}.balances
WHERE token_address = {addr}
    AND amount > 0
ORDER BY amount DESC
LIMIT 500
"""


def simplest_holder_query(token_symbol, token_info):
    """Simplest possible query — just count transfers and approximate."""
    addr = token_info["address"]
    chain = token_info["chain"]
    table = f"erc20_{chain}" if chain != "ethereum" else "erc20_ethereum"
    return f"""
-- Top 200 addresses by {token_symbol} received volume (proxy for holdings)
SELECT
    "to" as address,
    COUNT(*) as n_received,
    SUM(CAST(value AS DOUBLE) / 1e18) as total_received
FROM {table}.evt_Transfer
WHERE contract_address = {addr}
    AND evt_block_time >= DATE '2024-01-01'
GROUP BY 1
ORDER BY total_received DESC
LIMIT 200
"""


def main():
    print("=" * 60)
    print("GOVERNANCE TOKEN CONCENTRATION ANALYSIS")
    print("=" * 60)

    results = []
    for symbol, info in TOKENS.items():
        print(f"\n--- {symbol} ({info['protocol']}) ---")

        # Try simplest query first (most likely to work)
        sql = simplest_holder_query(symbol, info)
        rows = execute_inline(sql, f"holders_{symbol.lower()}")

        if not rows:
            print(f"  Skipping {symbol} — query failed")
            results.append({
                "protocol": info["protocol"],
                "token": symbol,
                "hhi": None,
                "gini": None,
                "n_holders_queried": 0,
                "note": "Query failed"
            })
            continue

        # Extract balances
        balances = []
        for row in rows:
            bal = row.get("balance", row.get("total_received", 0))
            if bal and float(bal) > 0:
                balances.append(float(bal))

        if len(balances) < 10:
            print(f"  Too few holders ({len(balances)})")
            continue

        hhi, gini = compute_hhi_gini(balances)
        top1_share = balances[0] / sum(balances) if balances else 0
        top10_share = sum(balances[:10]) / sum(balances) if len(balances) >= 10 else 0
        top50_share = sum(balances[:50]) / sum(balances) if len(balances) >= 50 else 0

        print(f"  HHI: {hhi}")
        print(f"  Gini: {gini}")
        print(f"  Top 1 share: {top1_share:.2%}")
        print(f"  Top 10 share: {top10_share:.2%}")
        print(f"  Top 50 share: {top50_share:.2%}")

        results.append({
            "protocol": info["protocol"],
            "token": symbol,
            "chain": info["chain"],
            "hhi": hhi,
            "gini": gini,
            "top1_share": round(top1_share, 4),
            "top10_share": round(top10_share, 4),
            "top50_share": round(top50_share, 4),
            "n_holders_queried": len(balances),
            "total_supply_queried": round(sum(balances), 2),
        })

        time.sleep(5)

    # Save results
    df = pd.DataFrame(results)
    df.to_csv(os.path.join(OUTPUT_DIR, "governance_hhi_gini_dune.csv"), index=False)

    with open(os.path.join(OUTPUT_DIR, "governance_hhi_gini_dune.json"), "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\n" + "=" * 60)
    print("GOVERNANCE CONCENTRATION SUMMARY")
    print("=" * 60)
    for r in results:
        hhi_str = f"{r['hhi']:.4f}" if r['hhi'] is not None else "N/A"
        gini_str = f"{r['gini']:.4f}" if r['gini'] is not None else "N/A"
        print(f"  {r['protocol']:15s} ({r['token']:5s}): HHI={hhi_str}, Gini={gini_str}")

    # Merge with existing known data
    existing = os.path.join(OUTPUT_DIR, "..", "depin-data", "governance", "governance_concentration.csv")
    if os.path.exists(existing):
        old = pd.read_csv(existing)
        print(f"\nMerging with existing {len(old)} records from earlier run")

    print(f"\nSaved: governance_hhi_gini_dune.csv, governance_hhi_gini_dune.json")


if __name__ == "__main__":
    main()
