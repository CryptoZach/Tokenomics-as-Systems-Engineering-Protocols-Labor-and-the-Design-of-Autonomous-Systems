#!/usr/bin/env python3
"""
Retry governance queries for WXM and ANYONE with corrected contract addresses.
"""
import os
import sys
import requests
import json
import time
import numpy as np

DUNE_API_KEY = "yGLinKdcZaQEr5b121QnW84jWDxzC8Ou"
HEADERS = {"X-Dune-API-Key": DUNE_API_KEY, "Content-Type": "application/json"}
BASE = "https://api.dune.com/api/v1"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "expansion")

EXCHANGE_ADDRESSES = {
    "0x28c6c06298d514db089934071355e5743bf21d60",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549",
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d",
    "0x56eddb7aa87536c09ccc2793473599fd21a8b17f",
    "0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43",
    "0x503828976d22510aad0201ac7ec88293211d23da",
    "0xf977814e90da44bfa03b6295a0616a897441acec",
    "0x47ac0fb4f2d84898e4d9e7b4dab3c24507a6d503",
    "0xbe0eb53f46cd790cd13851d5eff43d12404d33e8",
    "0x0000000000000000000000000000000000000000",
    "0x000000000000000000000000000000000000dead",
}

RETRY_TOKENS = {
    "WXM": {
        "address": "0xB6093B61544572Ab42A0E43AF08aBaFd41bF25a6",
        "chain": "arbitrum",
        "decimals": 18,
        "protocol": "WeatherXM",
        "total_supply": 100_000_000,
    },
    "ANYONE": {
        "address": "0xFEaC2eAE96899709a43e252b6b92971d32f9c0f9",
        "chain": "ethereum",
        "decimals": 18,
        "protocol": "Anyone Protocol",
        "total_supply": 100_000_000,
    },
}


def execute_inline(sql, label, retries=2):
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
                s = requests.get(f"{BASE}/execution/{eid}/status", headers=HEADERS, timeout=30)
                state = s.json().get("state", "?")
                if poll % 6 == 0:
                    print(f"    Poll {poll + 1}: {state}")
                if state == "QUERY_STATE_COMPLETED":
                    r = requests.get(f"{BASE}/execution/{eid}/results", headers=HEADERS, timeout=60)
                    data = r.json()
                    rows = data.get("result", {}).get("rows", [])
                    fname = os.path.join(OUTPUT_DIR, f"dune_retry_{label}.json")
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


def main():
    print("=" * 70)
    print("GOVERNANCE RETRY: WXM + ANYONE (corrected addresses)")
    print("=" * 70)

    results = []

    for symbol, info in RETRY_TOKENS.items():
        addr = info["address"].lower()
        chain = info["chain"]
        decimals = info["decimals"]
        chain_table = f"erc20_{chain}.evt_Transfer"

        sql = f"""
-- Net balance for {symbol} on {chain} (corrected address)
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

        print(f"\n{'=' * 50}")
        print(f"  {symbol} ({info['protocol']}) -- {chain}")
        print(f"  Address: {addr}")
        print(f"{'=' * 50}")

        rows = execute_inline(sql, f"retry_{symbol.lower()}")

        if not rows:
            print(f"  No data returned for {symbol}")
            results.append({
                "protocol": info["protocol"],
                "token": symbol,
                "chain": chain,
                "hhi": None,
                "gini": None,
                "n_holders": 0,
                "method": "no_data",
                "note": f"No rows returned with address {addr}",
            })
            time.sleep(3)
            continue

        # Filter
        balances = []
        excluded = 0
        for row in rows:
            a = str(row.get("address", "")).lower()
            bal = float(row.get("balance", 0))
            if a in EXCHANGE_ADDRESSES or a.startswith("0x00000000"):
                excluded += 1
                continue
            if bal > info["total_supply"] * 2 or bal <= 0:
                continue
            balances.append(bal)

        print(f"  {len(balances)} valid holders, {excluded} excluded")

        if len(balances) < 10:
            print(f"  FAILED: Only {len(balances)} valid holders")
            results.append({
                "protocol": info["protocol"],
                "token": symbol,
                "chain": chain,
                "hhi": None,
                "gini": None,
                "n_holders": len(balances),
                "method": "net_transfer",
                "note": f"Insufficient ({len(balances)} holders)",
            })
            time.sleep(3)
            continue

        hhi, gini = compute_hhi_gini(balances)
        total = sum(balances)
        top1 = balances[0] / total
        top10 = sum(sorted(balances, reverse=True)[:10]) / total
        coverage = total / info["total_supply"]

        print(f"  HHI: {hhi}, Gini: {gini}, Top1: {top1:.2%}, Coverage: {coverage:.1%}")

        results.append({
            "protocol": info["protocol"],
            "token": symbol,
            "chain": chain,
            "hhi": hhi,
            "gini": gini,
            "top1_share": round(top1, 4),
            "top10_share": round(top10, 4),
            "n_holders": len(balances),
            "supply_coverage": round(coverage, 4),
            "method": "net_transfer",
        })
        time.sleep(3)

    # Save
    json_path = os.path.join(OUTPUT_DIR, "governance_retry_wxm_anyone.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved: {json_path}")


if __name__ == "__main__":
    main()
