#!/usr/bin/env python3
"""
Task 1 (SEVERITY 1): Corrected governance token concentration.

PROBLEM: Original query used cumulative transfer sums (total_received) instead
of net balances. Exchange hot wallets dominated results, and AAVE had uint256
overflow values (1.16e59).

FIX: Use Dune's pre-materialized balance tables for actual current holdings.
Fallback to net balance computation (inflows - outflows) from evt_Transfer.
Exclude known exchange addresses from governance concentration analysis.
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

# Known exchange hot wallets to EXCLUDE from governance concentration
EXCHANGE_ADDRESSES = {
    "0x28c6c06298d514db089934071355e5743bf21d60",  # Binance 14
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549",  # Binance 15
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d",  # Binance 16
    "0x56eddb7aa87536c09ccc2793473599fd21a8b17f",  # Binance 17
    "0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43",  # Coinbase 2
    "0x503828976d22510aad0201ac7ec88293211d23da",  # Coinbase 3
    "0xf977814e90da44bfa03b6295a0616a897441acec",  # Binance 8
    "0x47ac0fb4f2d84898e4d9e7b4dab3c24507a6d503",  # Binance cold
    "0xbe0eb53f46cd790cd13851d5eff43d12404d33e8",  # Binance cold 2
    "0x1d42064fc4beb5f8aaf85f4617ae8b3b5b8bd801",  # Uniswap: UNI Token Distributor
    "0x51c72848c68a965f66fa7a88855f9f7784502a7f",  # Coinbase 10
    "0x0000000000000000000000000000000000000000",  # Null address
    "0x000000000000000000000000000000000000dead",  # Dead address
}

# Tokens to query — expanded to include CRV, OP, GRT
TOKENS = {
    "UNI": {
        "address": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
        "chain": "ethereum",
        "decimals": 18,
        "protocol": "Uniswap",
        "total_supply": 1_000_000_000,
    },
    "COMP": {
        "address": "0xc00e94Cb662C3520282E6f5717214004A7f26888",
        "chain": "ethereum",
        "decimals": 18,
        "protocol": "Compound",
        "total_supply": 10_000_000,
    },
    "MKR": {
        "address": "0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2",
        "chain": "ethereum",
        "decimals": 18,
        "protocol": "MakerDAO",
        "total_supply": 977_631,
    },
    "AAVE": {
        "address": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
        "chain": "ethereum",
        "decimals": 18,
        "protocol": "Aave",
        "total_supply": 16_000_000,
    },
    "CRV": {
        "address": "0xD533a949740bb3306d119CC777fa900bA034cd52",
        "chain": "ethereum",
        "decimals": 18,
        "protocol": "Curve",
        "total_supply": 2_020_000_000,
    },
    "OP": {
        "address": "0x4200000000000000000000000000000000000042",
        "chain": "optimism",
        "decimals": 18,
        "protocol": "Optimism",
        "total_supply": 4_294_967_296,
    },
    "GRT": {
        "address": "0xc944E90C64B2c07662A292be6244BDf05Cda44a7",
        "chain": "ethereum",
        "decimals": 18,
        "protocol": "The Graph",
        "total_supply": 10_799_706_720,
    },
    "LPT": {
        "address": "0x289ba1701C2F088cf0faf8B3c94Cd3B9e166f367",
        "chain": "arbitrum",
        "decimals": 18,
        "protocol": "Livepeer",
        "total_supply": 30_527_383,
    },
}


def execute_inline(sql, label, retries=2):
    """Execute inline Dune query with retry logic."""
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

            for poll in range(90):  # Up to 15 minutes
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
                    print(f"    Got {len(rows)} rows → {fname}")
                    return rows
                elif "FAILED" in state or "CANCELLED" in state:
                    print(f"    {state}")
                    break
        except Exception as e:
            print(f"    Error: {e}")
            if attempt < retries:
                time.sleep(5)
    return None


def compute_hhi_gini(balances):
    """Compute HHI and Gini from a list of token balances."""
    if not balances or len(balances) < 2:
        return None, None
    total = sum(balances)
    if total == 0:
        return None, None

    shares = [b / total for b in balances]
    hhi = sum(s**2 for s in shares)

    n = len(balances)
    sorted_b = sorted(balances)
    cum = 0
    for i, b in enumerate(sorted_b):
        cum += (2 * (i + 1) - n - 1) * b
    gini = cum / (n * total) if total > 0 and n > 1 else 0

    return round(hhi, 6), round(abs(gini), 4)


def build_balance_query_approach_a(symbol, info):
    """Approach A: Use Dune's materialized balance tables (daily snapshot)."""
    addr = info["address"].lower()  # Dune v2 needs lowercase hex
    chain = info["chain"]
    decimals = info["decimals"]

    # Dune v2: use tokens_<chain>.balances_daily for most recent snapshot
    if chain == "ethereum":
        return f"""
-- Approach A: Materialized daily balance for {symbol}
SELECT
    wallet_address AS address,
    token_balance_raw / POWER(10, {decimals}) AS balance
FROM tokens_ethereum.balances_daily
WHERE token_address = {addr}
    AND day = (SELECT MAX(day) FROM tokens_ethereum.balances_daily WHERE token_address = {addr})
    AND token_balance_raw > 0
ORDER BY token_balance_raw DESC
LIMIT 1000
"""
    elif chain == "arbitrum":
        return f"""
SELECT
    wallet_address AS address,
    token_balance_raw / POWER(10, {decimals}) AS balance
FROM tokens_arbitrum.balances_daily
WHERE token_address = {addr}
    AND day = (SELECT MAX(day) FROM tokens_arbitrum.balances_daily WHERE token_address = {addr})
    AND token_balance_raw > 0
ORDER BY token_balance_raw DESC
LIMIT 1000
"""
    elif chain == "optimism":
        return f"""
SELECT
    wallet_address AS address,
    token_balance_raw / POWER(10, {decimals}) AS balance
FROM tokens_optimism.balances_daily
WHERE token_address = {addr}
    AND day = (SELECT MAX(day) FROM tokens_optimism.balances_daily WHERE token_address = {addr})
    AND token_balance_raw > 0
ORDER BY token_balance_raw DESC
LIMIT 1000
"""
    return None


def build_balance_query_approach_b(symbol, info):
    """Approach B: Net balance from evt_Transfer (inflows - outflows)."""
    addr = info["address"].lower()
    chain = info["chain"]
    decimals = info["decimals"]

    chain_table = f"erc20_{chain}.evt_Transfer"

    return f"""
-- Approach B: Net balance for {symbol} from transfer events
WITH inflows AS (
    SELECT "to" AS address,
           SUM(CAST(value AS DOUBLE) / POWER(10, {decimals})) AS amount_in
    FROM {chain_table}
    WHERE contract_address = {addr}
    GROUP BY 1
),
outflows AS (
    SELECT "from" AS address,
           SUM(CAST(value AS DOUBLE) / POWER(10, {decimals})) AS amount_out
    FROM {chain_table}
    WHERE contract_address = {addr}
    GROUP BY 1
)
SELECT
    COALESCE(i.address, o.address) AS address,
    COALESCE(i.amount_in, 0) - COALESCE(o.amount_out, 0) AS balance
FROM inflows i
FULL OUTER JOIN outflows o ON i.address = o.address
WHERE COALESCE(i.amount_in, 0) - COALESCE(o.amount_out, 0) > 0
ORDER BY balance DESC
LIMIT 1000
"""


def filter_and_validate(rows, token_info, approach_label):
    """Filter exchange addresses, validate balances, return clean list."""
    if not rows:
        return [], "no_data"

    balances = []
    excluded_count = 0
    overflow_count = 0
    total_supply = token_info["total_supply"]

    for row in rows:
        addr = str(row.get("address", "")).lower()
        bal = float(row.get("balance", 0))

        # Skip exchange addresses
        if addr in EXCHANGE_ADDRESSES:
            excluded_count += 1
            continue

        # Skip null/dead addresses
        if addr.startswith("0x00000000"):
            excluded_count += 1
            continue

        # Sanity: balance cannot exceed 2x total supply
        if bal > total_supply * 2:
            overflow_count += 1
            print(f"    OVERFLOW: {addr[:10]}... has {bal:.2e} (supply={total_supply:.2e})")
            continue

        # Skip negative or zero balances
        if bal <= 0:
            continue

        balances.append(bal)

    print(
        f"    [{approach_label}] {len(balances)} valid holders, "
        f"{excluded_count} exchanges excluded, {overflow_count} overflows skipped"
    )

    # Supply coverage check
    if balances:
        coverage = sum(balances) / total_supply
        print(f"    Supply coverage: {coverage:.1%} of total supply")
        if coverage < 0.10:
            print(f"    WARNING: Very low coverage (<10%) — results may be unreliable")

    return balances, approach_label


def main():
    if not DUNE_API_KEY:
        print("ERROR: Set DUNE_API_KEY environment variable")
        return

    print("=" * 70)
    print("CORRECTED GOVERNANCE TOKEN CONCENTRATION ANALYSIS")
    print("=" * 70)
    print(f"Tokens: {', '.join(TOKENS.keys())}")
    print(f"Exchange addresses excluded: {len(EXCHANGE_ADDRESSES)}")

    results = []

    for symbol, info in TOKENS.items():
        print(f"\n{'─' * 50}")
        print(f"  {symbol} ({info['protocol']}) — chain: {info['chain']}")
        print(f"{'─' * 50}")

        balances = []
        method = "none"

        # Try Approach A: Materialized balance tables
        sql_a = build_balance_query_approach_a(symbol, info)
        if sql_a:
            rows_a = execute_inline(sql_a, f"balance_a_{symbol.lower()}")
            if rows_a:
                balances, method = filter_and_validate(rows_a, info, "materialized")

        # Fallback: Approach B — net balance from transfers
        if len(balances) < 50:
            print(f"    Approach A returned only {len(balances)} holders. Trying Approach B...")
            sql_b = build_balance_query_approach_b(symbol, info)
            rows_b = execute_inline(sql_b, f"balance_b_{symbol.lower()}")
            if rows_b:
                balances_b, method_b = filter_and_validate(rows_b, info, "net_transfer")
                if len(balances_b) > len(balances):
                    balances = balances_b
                    method = method_b

        if len(balances) < 10:
            print(f"  FAILED: Only {len(balances)} valid holders for {symbol}")
            results.append(
                {
                    "protocol": info["protocol"],
                    "token": symbol,
                    "chain": info["chain"],
                    "hhi": None,
                    "gini": None,
                    "n_holders": 0,
                    "method": method,
                    "note": f"Insufficient data ({len(balances)} holders)",
                }
            )
            continue

        # Compute metrics
        hhi, gini = compute_hhi_gini(balances)
        total = sum(balances)
        top1 = balances[0] / total if balances else 0
        top10 = sum(sorted(balances, reverse=True)[:10]) / total if len(balances) >= 10 else None
        top50 = sum(sorted(balances, reverse=True)[:50]) / total if len(balances) >= 50 else None
        coverage = total / info["total_supply"]

        print(f"\n  RESULTS for {symbol}:")
        print(f"    Method: {method}")
        print(f"    HHI:        {hhi:.6f}" if hhi else "    HHI:        N/A")
        print(f"    Gini:       {gini:.4f}" if gini else "    Gini:       N/A")
        print(f"    Top 1:      {top1:.2%}")
        print(f"    Top 10:     {top10:.2%}" if top10 else "    Top 10:     N/A")
        print(f"    Top 50:     {top50:.2%}" if top50 else "    Top 50:     N/A")
        print(f"    Coverage:   {coverage:.1%} of supply")
        print(f"    N holders:  {len(balances)}")

        results.append(
            {
                "protocol": info["protocol"],
                "token": symbol,
                "chain": info["chain"],
                "hhi": hhi,
                "gini": gini,
                "top1_share": round(top1, 4),
                "top10_share": round(top10, 4) if top10 else None,
                "top50_share": round(top50, 4) if top50 else None,
                "n_holders": len(balances),
                "supply_coverage": round(coverage, 4),
                "total_queried": round(total, 2),
                "total_supply": info["total_supply"],
                "method": method,
            }
        )

        time.sleep(3)

    # Save results
    df = pd.DataFrame(results)
    csv_path = os.path.join(OUTPUT_DIR, "governance_hhi_gini_CORRECTED.csv")
    json_path = os.path.join(OUTPUT_DIR, "governance_hhi_gini_CORRECTED.json")
    df.to_csv(csv_path, index=False)
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\n" + "=" * 70)
    print("CORRECTED GOVERNANCE CONCENTRATION SUMMARY")
    print("=" * 70)
    print(f"  {'Protocol':<15} {'Token':<6} {'HHI':>10} {'Gini':>8} {'Top1':>8} {'N':>6} {'Method':<15}")
    print(f"  {'─' * 70}")
    for r in results:
        hhi_s = f"{r['hhi']:.6f}" if r["hhi"] else "N/A"
        gini_s = f"{r['gini']:.4f}" if r["gini"] else "N/A"
        top1_s = f"{r.get('top1_share', 0):.2%}" if r.get("top1_share") else "N/A"
        method_s = r.get("method", "?")
        n = r.get("n_holders", 0)
        print(f"  {r['protocol']:<15} {r['token']:<6} {hhi_s:>10} {gini_s:>8} {top1_s:>8} {n:>6} {method_s:<15}")

    # Validation flags
    print("\nVALIDATION:")
    for r in results:
        issues = []
        if r["hhi"] is None:
            issues.append("NO DATA")
        elif r["hhi"] < 0.001:
            issues.append("HHI suspiciously low")
        if r.get("supply_coverage", 0) < 0.30:
            issues.append(f"low coverage ({r.get('supply_coverage', 0):.0%})")
        if r.get("n_holders", 0) < 50:
            issues.append(f"few holders ({r.get('n_holders', 0)})")
        flag = " | ".join(issues) if issues else "OK"
        print(f"  {r['token']}: {flag}")

    print(f"\nSaved: {csv_path}")
    print(f"Saved: {json_path}")


if __name__ == "__main__":
    main()
