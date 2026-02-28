#!/usr/bin/env python3
"""
Phase 1A: Governance token concentration for new DePIN protocols.
Extends Table 6.G1 with: IOTX, DIMO, WXM, ANYONE (EVM chains) + HONEY, GRASS (Solana).
Uses same corrected methodology as governance_v2 (net balances, exchange exclusion).
"""
import os
import sys
import requests
import json
import time
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DUNE_API_KEY, EVM_TOKENS, SOLANA_TOKENS, EXCHANGE_ADDRESSES

HEADERS = {"X-Dune-API-Key": DUNE_API_KEY, "Content-Type": "application/json"}
BASE = "https://api.dune.com/api/v1"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "expansion")
os.makedirs(OUTPUT_DIR, exist_ok=True)


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
                    print(f"    Got {len(rows)} rows -> {fname}")
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
    hhi = sum(s ** 2 for s in shares)

    n = len(balances)
    sorted_b = sorted(balances)
    cum = 0
    for i, b in enumerate(sorted_b):
        cum += (2 * (i + 1) - n - 1) * b
    gini = cum / (n * total) if total > 0 and n > 1 else 0

    return round(hhi, 6), round(abs(gini), 4)


def build_evm_query(symbol, info):
    """Build net balance query for EVM tokens."""
    addr = info["address"].lower()
    chain = info["chain"]
    decimals = info["decimals"]
    chain_table = f"erc20_{chain}.evt_Transfer"

    return f"""
-- Net balance for {symbol} on {chain}
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


def build_solana_query(symbol, info):
    """Build net balance query for Solana SPL tokens."""
    mint = info["mint"]
    decimals = info["decimals"]

    return f"""
-- Net balance for {symbol} on Solana via token transfers
WITH inflows AS (
    SELECT to_owner AS address,
           SUM(amount / POWER(10, {decimals})) AS amount_in
    FROM tokens_solana.transfers
    WHERE token_mint_address = '{mint}'
    GROUP BY 1
),
outflows AS (
    SELECT from_owner AS address,
           SUM(amount / POWER(10, {decimals})) AS amount_out
    FROM tokens_solana.transfers
    WHERE token_mint_address = '{mint}'
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


def filter_and_validate(rows, total_supply, approach_label):
    """Filter exchange addresses, validate balances, return clean list."""
    if not rows:
        return [], "no_data"

    balances = []
    excluded_count = 0
    overflow_count = 0

    for row in rows:
        addr = str(row.get("address", "")).lower()
        bal = float(row.get("balance", 0))

        # Skip exchange addresses (EVM)
        if addr in EXCHANGE_ADDRESSES:
            excluded_count += 1
            continue

        # Skip null/dead addresses
        if addr.startswith("0x00000000") or addr == "11111111111111111111111111111111":
            excluded_count += 1
            continue

        # Sanity: balance cannot exceed 2x total supply
        if bal > total_supply * 2:
            overflow_count += 1
            continue

        if bal <= 0:
            continue

        balances.append(bal)

    print(
        f"    [{approach_label}] {len(balances)} valid holders, "
        f"{excluded_count} exchanges excluded, {overflow_count} overflows skipped"
    )

    if balances:
        coverage = sum(balances) / total_supply
        print(f"    Supply coverage: {coverage:.1%} of total supply")

    return balances, approach_label


def main():
    if not DUNE_API_KEY:
        print("ERROR: DUNE_API_KEY not set in config.py")
        return

    print("=" * 70)
    print("DePIN GOVERNANCE TOKEN CONCENTRATION EXPANSION")
    print("=" * 70)

    results = []

    # Process EVM tokens
    for symbol, info in EVM_TOKENS.items():
        print(f"\n{'=' * 50}")
        print(f"  {symbol} ({info['protocol']}) -- chain: {info['chain']}")
        print(f"{'=' * 50}")

        sql = build_evm_query(symbol, info)
        rows = execute_inline(sql, f"balance_{symbol.lower()}")

        if rows:
            balances, method = filter_and_validate(rows, info["total_supply"], "net_transfer")
        else:
            balances, method = [], "no_data"

        if len(balances) < 10:
            print(f"  FAILED: Only {len(balances)} valid holders for {symbol}")
            results.append({
                "protocol": info["protocol"],
                "token": symbol,
                "chain": info["chain"],
                "hhi": None,
                "gini": None,
                "top1_share": None,
                "top10_share": None,
                "top50_share": None,
                "n_holders": len(balances),
                "method": method,
                "note": f"Insufficient data ({len(balances)} holders)",
            })
            time.sleep(3)
            continue

        hhi, gini = compute_hhi_gini(balances)
        total = sum(balances)
        top1 = balances[0] / total if balances else 0
        top10 = sum(sorted(balances, reverse=True)[:10]) / total if len(balances) >= 10 else None
        top50 = sum(sorted(balances, reverse=True)[:50]) / total if len(balances) >= 50 else None
        coverage = total / info["total_supply"]

        print(f"\n  RESULTS for {symbol}:")
        print(f"    HHI:      {hhi}")
        print(f"    Gini:     {gini}")
        print(f"    Top 1:    {top1:.2%}")
        print(f"    Top 10:   {top10:.2%}" if top10 else "    Top 10:   N/A")
        print(f"    Coverage: {coverage:.1%}")
        print(f"    N:        {len(balances)}")

        results.append({
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
            "method": method,
        })
        time.sleep(3)

    # Process Solana tokens
    for symbol, info in SOLANA_TOKENS.items():
        print(f"\n{'=' * 50}")
        print(f"  {symbol} ({info['protocol']}) -- chain: solana")
        print(f"{'=' * 50}")

        sql = build_solana_query(symbol, info)
        rows = execute_inline(sql, f"balance_{symbol.lower()}")

        if rows:
            balances, method = filter_and_validate(rows, info["total_supply"], "net_transfer")
        else:
            balances, method = [], "no_data"

        if len(balances) < 10:
            print(f"  FAILED: Only {len(balances)} valid holders for {symbol}")
            results.append({
                "protocol": info["protocol"],
                "token": symbol,
                "chain": "solana",
                "hhi": None,
                "gini": None,
                "top1_share": None,
                "top10_share": None,
                "top50_share": None,
                "n_holders": len(balances),
                "method": method,
                "note": f"Insufficient data ({len(balances)} holders)",
            })
            time.sleep(3)
            continue

        hhi, gini = compute_hhi_gini(balances)
        total = sum(balances)
        top1 = balances[0] / total if balances else 0
        top10 = sum(sorted(balances, reverse=True)[:10]) / total if len(balances) >= 10 else None
        top50 = sum(sorted(balances, reverse=True)[:50]) / total if len(balances) >= 50 else None
        coverage = total / info["total_supply"]

        print(f"\n  RESULTS for {symbol}:")
        print(f"    HHI:      {hhi}")
        print(f"    Gini:     {gini}")
        print(f"    Top 1:    {top1:.2%}")
        print(f"    Top 10:   {top10:.2%}" if top10 else "    Top 10:   N/A")
        print(f"    Coverage: {coverage:.1%}")
        print(f"    N:        {len(balances)}")

        results.append({
            "protocol": info["protocol"],
            "token": symbol,
            "chain": "solana",
            "hhi": hhi,
            "gini": gini,
            "top1_share": round(top1, 4),
            "top10_share": round(top10, 4) if top10 else None,
            "top50_share": round(top50, 4) if top50 else None,
            "n_holders": len(balances),
            "supply_coverage": round(coverage, 4),
            "method": method,
        })
        time.sleep(3)

    # Save results
    df = pd.DataFrame(results)
    csv_path = os.path.join(OUTPUT_DIR, "depin_governance_expansion.csv")
    json_path = os.path.join(OUTPUT_DIR, "depin_governance_expansion.json")
    df.to_csv(csv_path, index=False)
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\n" + "=" * 70)
    print("DePIN GOVERNANCE EXPANSION RESULTS")
    print("=" * 70)
    print(f"  {'Protocol':<20} {'Token':<8} {'Chain':<10} {'HHI':>10} {'Gini':>8} {'Top1':>8} {'N':>6}")
    print(f"  {'─' * 74}")
    for r in results:
        hhi_s = f"{r['hhi']:.6f}" if r.get("hhi") else "N/A"
        gini_s = f"{r['gini']:.4f}" if r.get("gini") else "N/A"
        top1_s = f"{r.get('top1_share', 0):.2%}" if r.get("top1_share") else "N/A"
        print(f"  {r['protocol']:<20} {r['token']:<8} {r['chain']:<10} {hhi_s:>10} {gini_s:>8} {top1_s:>8} {r.get('n_holders', 0):>6}")

    print(f"\nSaved: {csv_path}")
    print(f"Saved: {json_path}")


if __name__ == "__main__":
    main()
