#!/usr/bin/env python3
"""
Collect DePIN governance token holder distributions for HNT, RENDER, AKT.
Uses Dune Analytics for Solana tokens and Cosmos LCD API for AKT.
Merges with existing expansion data (DIMO, IoTeX, Grass).
"""
import os
import sys
import requests
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "expansion"))
from config import DUNE_API_KEY, EXCHANGE_ADDRESSES

HEADERS = {"X-Dune-API-Key": DUNE_API_KEY, "Content-Type": "application/json"}
BASE = "https://api.dune.com/api/v1"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Target DePIN protocols for Solana (Dune)
SOLANA_TARGETS = {
    "HNT": {
        "mint": "hntyVP6YFm1Hg25TN9WGLqM12b8TQv4smRNhB3XMv1b",
        "protocol": "Helium",
        "decimals": 8,
        "total_supply": 223_000_000,
        "chain": "solana",
    },
    "RENDER": {
        "mint": "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof",
        "protocol": "Render",
        "decimals": 8,
        "total_supply": 532_000_000,
        "chain": "solana",
    },
}

# Known Solana exchange/program addresses to exclude
SOLANA_EXCHANGE_ADDRESSES = {
    "5tzFkiKscjHsFKSoztMttaT2nJJRHNtMma1KUpBBkP8K",   # Binance Solana hot
    "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",   # Binance Solana 2
    "2ojv9BAiHUrvsm9gxDe7fJSzbNZSJcxZvf8dqmWGHG8S",   # Coinbase Solana
    "H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS",   # Coinbase Solana 2
    "3yFwqXBfZY12N8VWMEmz4A7xFJrPEFoayPnmbXkAGn58",   # Kraken Solana
    "AobVSwdW9BbpMdJvTqeCN4hPAmh4rHm7vwLnQ5ATbo3s",   # OKX Solana
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",     # Token program
    "11111111111111111111111111111111",                   # System program
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


def filter_solana(rows, total_supply):
    """Filter exchange/program addresses from Solana results."""
    if not rows:
        return []
    balances = []
    excluded = 0
    for row in rows:
        addr = str(row.get("address", ""))
        bal = float(row.get("balance", 0))
        if addr in SOLANA_EXCHANGE_ADDRESSES:
            excluded += 1
            continue
        if addr == "11111111111111111111111111111111":
            excluded += 1
            continue
        if bal > total_supply * 2 or bal <= 0:
            continue
        balances.append(bal)
    print(f"    {len(balances)} valid holders, {excluded} exchanges/programs excluded")
    if balances:
        coverage = sum(balances) / total_supply
        print(f"    Supply coverage: {coverage:.1%}")
    return balances


def collect_akash_validators():
    """Collect AKT staking distribution from Cosmos LCD API."""
    print("\n  Collecting Akash (AKT) validator staking distribution...")
    all_validators = []
    next_key = None
    page = 0

    while True:
        page += 1
        params = {"pagination.limit": "200"}
        if next_key:
            params["pagination.key"] = next_key
        try:
            resp = requests.get(
                "https://rest.cosmos.directory/akash/cosmos/staking/v1beta1/validators",
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            validators = data.get("validators", [])
            all_validators.extend(validators)
            print(f"    Page {page}: {len(validators)} validators (total: {len(all_validators)})")

            pagination = data.get("pagination", {})
            next_key = pagination.get("next_key")
            if not next_key or not validators:
                break
            time.sleep(1)
        except Exception as e:
            print(f"    Error on page {page}: {e}")
            break

    if not all_validators:
        print("    FAILED: No validators returned")
        return []

    # Extract staking amounts (in uAKT, convert to AKT)
    balances = []
    excluded = 0
    for v in all_validators:
        tokens = float(v.get("tokens", 0)) / 1e6  # uAKT -> AKT
        status = v.get("status", "")
        moniker = v.get("description", {}).get("moniker", "unknown")
        # Only include bonded validators for governance power
        if status == "BOND_STATUS_BONDED" and tokens > 0:
            balances.append(tokens)
        elif tokens > 0:
            excluded += 1

    balances.sort(reverse=True)
    print(f"    {len(balances)} bonded validators, {excluded} unbonded/jailed excluded")
    if balances:
        total = sum(balances)
        print(f"    Total staked: {total:,.0f} AKT")
        print(f"    Top validator: {balances[0]:,.0f} AKT ({balances[0]/total:.1%})")

    # Save raw data
    raw_path = os.path.join(OUTPUT_DIR, "akash_validators_raw.json")
    with open(raw_path, "w") as f:
        json.dump(
            [{"moniker": v.get("description", {}).get("moniker", ""),
              "tokens_akt": float(v.get("tokens", 0)) / 1e6,
              "status": v.get("status", ""),
              "operator": v.get("operator_address", "")}
             for v in all_validators],
            f, indent=2
        )
    print(f"    Saved raw: {raw_path}")

    return balances


def process_results(symbol, info, balances):
    """Compute metrics from holder balances."""
    if len(balances) < 10:
        return {
            "protocol": info["protocol"],
            "token": symbol,
            "chain": info["chain"],
            "hhi": None, "gini": None,
            "top1_share": None, "top10_share": None, "top50_share": None,
            "n_holders": len(balances),
            "supply_coverage": None,
            "method": "no_data",
            "note": f"Insufficient data ({len(balances)} holders)",
        }

    hhi, gini = compute_hhi_gini(balances)
    total = sum(balances)
    top1 = balances[0] / total
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

    return {
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
        "method": "net_transfer",
    }


def main():
    print("=" * 70)
    print("DePIN GOVERNANCE COLLECTION: HNT, RENDER, AKT")
    print("=" * 70)

    collection_log = {
        "collection_date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "protocols_attempted": [],
        "protocols_succeeded": [],
        "protocols_failed": {},
        "data_source": {},
        "exclusions": {
            "solana_exchange_addresses": list(SOLANA_EXCHANGE_ADDRESSES),
        },
        "snapshot_dates": {},
        "methodology": "Top-1000 holders via Dune net_transfer (Solana) / Cosmos LCD staking (AKT), exchange-excluded, HHI/Gini on token balances/delegations",
    }

    results = []

    # 1. Solana tokens via Dune
    if not DUNE_API_KEY:
        print("WARNING: No Dune API key. Skipping Solana tokens.")
    else:
        for symbol, info in SOLANA_TARGETS.items():
            collection_log["protocols_attempted"].append(symbol)
            print(f"\n{'=' * 50}")
            print(f"  {symbol} ({info['protocol']}) -- chain: solana")
            print(f"{'=' * 50}")

            sql = build_solana_query(symbol, info)
            rows = execute_inline(sql, f"balance_{symbol.lower()}")

            if rows:
                balances = filter_solana(rows, info["total_supply"])
                result = process_results(symbol, info, balances)
                results.append(result)
                if result["hhi"] is not None:
                    collection_log["protocols_succeeded"].append(symbol)
                    collection_log["data_source"][symbol] = "Dune Analytics (tokens_solana.transfers)"
                    collection_log["snapshot_dates"][symbol] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                else:
                    collection_log["protocols_failed"][symbol] = f"Only {len(balances)} valid holders"
            else:
                results.append({
                    "protocol": info["protocol"], "token": symbol, "chain": "solana",
                    "hhi": None, "gini": None, "n_holders": 0, "method": "no_data",
                    "note": "Dune query returned no results",
                })
                collection_log["protocols_failed"][symbol] = "Dune query returned no results"

            time.sleep(3)

    # 2. Akash (AKT) via Cosmos LCD
    collection_log["protocols_attempted"].append("AKT")
    print(f"\n{'=' * 50}")
    print(f"  AKT (Akash) -- chain: cosmos")
    print(f"{'=' * 50}")

    akt_info = {
        "protocol": "Akash",
        "chain": "cosmos",
        "total_supply": 248_000_000,  # ~248M AKT total
    }
    akt_balances = collect_akash_validators()
    if akt_balances:
        akt_result = process_results("AKT", akt_info, akt_balances)
        # For Cosmos, method is validator staking
        akt_result["method"] = "validator_staking"
        akt_result["note"] = "HHI computed on bonded validator voting power (delegated PoS)"
        results.append(akt_result)
        if akt_result["hhi"] is not None:
            collection_log["protocols_succeeded"].append("AKT")
            collection_log["data_source"]["AKT"] = "Cosmos LCD API (rest.cosmos.directory/akash)"
            collection_log["snapshot_dates"]["AKT"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        else:
            collection_log["protocols_failed"]["AKT"] = f"Only {len(akt_balances)} validators"
    else:
        results.append({
            "protocol": "Akash", "token": "AKT", "chain": "cosmos",
            "hhi": None, "gini": None, "n_holders": 0, "method": "no_data",
            "note": "Cosmos LCD API returned no validators",
        })
        collection_log["protocols_failed"]["AKT"] = "No validators returned"

    # Save new results
    new_json_path = os.path.join(OUTPUT_DIR, "depin_hnt_render_akt.json")
    with open(new_json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved new results: {new_json_path}")

    # Save collection log
    log_path = os.path.join(OUTPUT_DIR, "collection_log.json")
    with open(log_path, "w") as f:
        json.dump(collection_log, f, indent=2, default=str)
    print(f"Saved collection log: {log_path}")

    # Print summary
    print("\n" + "=" * 70)
    print("COLLECTION SUMMARY")
    print("=" * 70)
    print(f"  {'Protocol':<15} {'Token':<8} {'Chain':<8} {'HHI':>10} {'Gini':>8} {'Top1':>8} {'N':>6}")
    print(f"  {'─' * 64}")
    for r in results:
        hhi_s = f"{r['hhi']:.6f}" if r.get("hhi") else "N/A"
        gini_s = f"{r['gini']:.4f}" if r.get("gini") else "N/A"
        top1_s = f"{r.get('top1_share', 0):.2%}" if r.get("top1_share") else "N/A"
        print(f"  {r['protocol']:<15} {r['token']:<8} {r['chain']:<8} {hhi_s:>10} {gini_s:>8} {top1_s:>8} {r.get('n_holders', 0):>6}")

    print(f"\nSucceeded: {collection_log['protocols_succeeded']}")
    print(f"Failed: {collection_log['protocols_failed']}")


if __name__ == "__main__":
    main()
