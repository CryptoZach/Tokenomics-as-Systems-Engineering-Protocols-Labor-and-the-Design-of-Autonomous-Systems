#!/usr/bin/env python3
"""
Collect HNT holder data from Solscan API and Filecoin validator data.
"""
import requests
import json
import os
import time
import sys

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

HNT_MINT = "hntyVP6YFm1Hg25TN9WGLqM12b8TQv4smRNhB3XMv1b"

SOLANA_EXCHANGE_ADDRESSES = {
    "5tzFkiKscjHsFKSoztMttaT2nJJRHNtMma1KUpBBkP8K",
    "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
    "2ojv9BAiHUrvsm9gxDe7fJSzbNZSJcxZvf8dqmWGHG8S",
    "H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS",
    "3yFwqXBfZY12N8VWMEmz4A7xFJrPEFoayPnmbXkAGn58",
    "AobVSwdW9BbpMdJvTqeCN4hPAmh4rHm7vwLnQ5ATbo3s",
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "11111111111111111111111111111111",
}


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


def try_solscan_v1():
    """Try Solscan v1 API for HNT holders."""
    print("=== Solscan v1 API ===")
    all_holders = []
    for offset in range(0, 1000, 50):
        url = f"https://api.solscan.io/token/holders?token={HNT_MINT}&offset={offset}&size=50"
        try:
            resp = requests.get(url, timeout=15, headers={"Accept": "application/json"})
            if resp.status_code == 200:
                data = resp.json()
                holders = data.get("data", {}).get("result", [])
                if not holders:
                    break
                all_holders.extend(holders)
                print(f"  Offset {offset}: {len(holders)} holders (total: {len(all_holders)})")
            elif resp.status_code == 429:
                print(f"  Rate limited at offset {offset}, waiting...")
                time.sleep(10)
                continue
            else:
                print(f"  Status {resp.status_code} at offset {offset}")
                break
        except Exception as e:
            print(f"  Error: {e}")
            break
        time.sleep(2)
    return all_holders


def try_solscan_v2():
    """Try Solscan v2 public API for HNT holders."""
    print("\n=== Solscan v2 API ===")
    all_holders = []
    page = 1
    while len(all_holders) < 1000:
        url = f"https://api-v2.solscan.io/v2/token/holders?token={HNT_MINT}&page={page}&page_size=40"
        try:
            resp = requests.get(url, timeout=15, headers={
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0"
            })
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", {}).get("items", [])
                if not items:
                    # Try alternative response format
                    items = data.get("data", [])
                    if not items:
                        print(f"  Page {page}: no items, stopping")
                        break
                all_holders.extend(items)
                print(f"  Page {page}: {len(items)} holders (total: {len(all_holders)})")
                page += 1
            elif resp.status_code == 429:
                print(f"  Rate limited, waiting 10s...")
                time.sleep(10)
                continue
            else:
                print(f"  Status {resp.status_code}: {resp.text[:200]}")
                break
        except Exception as e:
            print(f"  Error: {e}")
            break
        time.sleep(2)
    return all_holders


def try_birdeye_api():
    """Try Birdeye public API for top holders."""
    print("\n=== Birdeye API ===")
    url = f"https://public-api.birdeye.so/defi/v3/token/top-holders?address={HNT_MINT}&limit=100"
    try:
        resp = requests.get(url, timeout=15, headers={"Accept": "application/json"})
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", {}).get("items", [])
            print(f"  Got {len(items)} holders")
            return items
    except Exception as e:
        print(f"  Error: {e}")
    return []


def try_helius_das():
    """Try Helius DAS API for token accounts (requires API key, check env)."""
    print("\n=== Helius DAS API ===")
    api_key = os.environ.get("HELIUS_API_KEY", "")
    if not api_key:
        print("  No HELIUS_API_KEY set, skipping")
        return []
    url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenLargestAccounts",
        "params": [HNT_MINT]
    }
    try:
        resp = requests.post(url, json=payload, timeout=30)
        data = resp.json()
        accounts = data.get("result", {}).get("value", [])
        print(f"  Got {len(accounts)} accounts")
        return accounts
    except Exception as e:
        print(f"  Error: {e}")
    return []


def try_solana_rpc():
    """Try public Solana RPC for getTokenLargestAccounts."""
    print("\n=== Solana Public RPC: getTokenLargestAccounts ===")
    rpcs = [
        "https://api.mainnet-beta.solana.com",
    ]
    for rpc_url in rpcs:
        print(f"  Trying {rpc_url}...")
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenLargestAccounts",
            "params": [HNT_MINT]
        }
        try:
            resp = requests.post(rpc_url, json=payload, timeout=30)
            data = resp.json()
            if "error" in data:
                print(f"    Error: {data['error']}")
                continue
            accounts = data.get("result", {}).get("value", [])
            if accounts:
                print(f"    Got {len(accounts)} largest accounts")
                # Save raw
                fname = os.path.join(OUTPUT_DIR, "hnt_largest_accounts_rpc.json")
                with open(fname, "w") as f:
                    json.dump(accounts, f, indent=2)
                print(f"    Saved: {fname}")
                return accounts
        except Exception as e:
            print(f"    Error: {e}")
        time.sleep(1)
    return []


def collect_filecoin_miners():
    """Collect Filecoin miner/provider power distribution from Filecoin APIs."""
    print("\n=== Filecoin Miner Power Distribution ===")

    # Try Filfox API (popular Filecoin explorer)
    print("  Trying Filfox API...")
    try:
        resp = requests.get(
            "https://filfox.info/api/v1/miner/top-miners/power?count=200",
            timeout=30,
            headers={"Accept": "application/json"}
        )
        if resp.status_code == 200:
            data = resp.json()
            miners = data.get("miners", [])
            if miners:
                print(f"  Got {len(miners)} top miners by power")
                balances = []
                for m in miners:
                    power = float(m.get("rawBytePower", 0))
                    if power > 0:
                        balances.append(power)
                balances.sort(reverse=True)
                # Save raw
                fname = os.path.join(OUTPUT_DIR, "filecoin_miners_raw.json")
                with open(fname, "w") as f:
                    json.dump(miners[:200], f, indent=2, default=str)
                print(f"    Saved: {fname}")
                return balances
        else:
            print(f"  Filfox status: {resp.status_code}")
    except Exception as e:
        print(f"  Filfox error: {e}")

    # Try Spacescope API
    print("  Trying Spacescope API...")
    try:
        resp = requests.get(
            "https://api.spacescope.io/v2/power/storage_provider_power?limit=200",
            timeout=30,
        )
        print(f"  Spacescope status: {resp.status_code}")
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"  Spacescope error: {e}")

    return []


def main():
    print("=" * 70)
    print("HNT + FILECOIN COLLECTION (ALTERNATIVE APPROACHES)")
    print("=" * 70)

    # --- HNT ---
    print("\n--- HNT (Helium) ---")

    # Try Solana RPC first (most reliable, returns top 20)
    rpc_accounts = try_solana_rpc()

    # Try Solscan APIs
    holders_v1 = try_solscan_v1()
    if not holders_v1:
        holders_v2 = try_solscan_v2()
    else:
        holders_v2 = []

    # Try Birdeye
    birdeye = try_birdeye_api()

    # Process best HNT result
    hnt_balances = []
    hnt_source = None

    if holders_v1:
        hnt_source = "Solscan v1"
        for h in holders_v1:
            amt = float(h.get("amount", 0)) / 1e8  # HNT has 8 decimals
            owner = h.get("owner", "")
            if owner not in SOLANA_EXCHANGE_ADDRESSES and amt > 0:
                hnt_balances.append(amt)
    elif holders_v2:
        hnt_source = "Solscan v2"
        for h in holders_v2:
            amt = float(h.get("amount", h.get("balance", 0))) / 1e8
            owner = h.get("owner", h.get("address", ""))
            if owner not in SOLANA_EXCHANGE_ADDRESSES and amt > 0:
                hnt_balances.append(amt)
    elif rpc_accounts:
        hnt_source = "Solana RPC getTokenLargestAccounts"
        for a in rpc_accounts:
            amt_str = a.get("uiAmountString", a.get("amount", "0"))
            try:
                amt = float(amt_str) if "." in str(amt_str) else float(amt_str) / 1e8
            except:
                continue
            addr = a.get("address", "")
            if addr not in SOLANA_EXCHANGE_ADDRESSES and amt > 0:
                hnt_balances.append(amt)
    elif birdeye:
        hnt_source = "Birdeye"
        for h in birdeye:
            amt = float(h.get("uiAmount", h.get("amount", 0)))
            if amt > 0:
                hnt_balances.append(amt)

    hnt_balances.sort(reverse=True)
    print(f"\n  HNT: {len(hnt_balances)} holders from {hnt_source or 'none'}")

    if hnt_balances:
        hhi, gini = compute_hhi_gini(hnt_balances)
        total = sum(hnt_balances)
        top1 = hnt_balances[0] / total
        top10 = sum(hnt_balances[:10]) / total if len(hnt_balances) >= 10 else None
        print(f"  HHI:  {hhi}")
        print(f"  Gini: {gini}")
        print(f"  Top1: {top1:.2%}")
        print(f"  Total: {total:,.0f} HNT")
        print(f"  N:    {len(hnt_balances)}")

        hnt_result = {
            "protocol": "Helium",
            "token": "HNT",
            "chain": "solana",
            "hhi": hhi,
            "gini": gini,
            "top1_share": round(top1, 4),
            "top10_share": round(top10, 4) if top10 else None,
            "n_holders": len(hnt_balances),
            "supply_coverage": round(total / 223_000_000, 4),
            "method": hnt_source,
            "note": f"Top {len(hnt_balances)} accounts only" if len(hnt_balances) < 100 else "",
        }
    else:
        hnt_result = {
            "protocol": "Helium",
            "token": "HNT",
            "chain": "solana",
            "hhi": None,
            "gini": None,
            "n_holders": 0,
            "method": "no_data",
            "note": "All API approaches returned 0 holders",
        }

    # --- Filecoin ---
    print("\n--- Filecoin (FIL) ---")
    fil_balances = collect_filecoin_miners()

    if fil_balances and len(fil_balances) >= 10:
        hhi, gini = compute_hhi_gini(fil_balances)
        total = sum(fil_balances)
        top1 = fil_balances[0] / total
        top10 = sum(fil_balances[:10]) / total if len(fil_balances) >= 10 else None
        print(f"\n  FIL miners: {len(fil_balances)}")
        print(f"  HHI:  {hhi}")
        print(f"  Gini: {gini}")
        print(f"  Top1: {top1:.2%}")

        fil_result = {
            "protocol": "Filecoin",
            "token": "FIL",
            "chain": "filecoin",
            "hhi": hhi,
            "gini": gini,
            "top1_share": round(top1, 4),
            "top10_share": round(top10, 4) if top10 else None,
            "n_holders": len(fil_balances),
            "method": "miner_power",
            "note": "HHI computed on raw byte storage power (miner/provider distribution)",
        }
    else:
        fil_result = {
            "protocol": "Filecoin",
            "token": "FIL",
            "chain": "filecoin",
            "hhi": None,
            "gini": None,
            "n_holders": 0,
            "method": "no_data",
            "note": "API unavailable",
        }

    # Save combined results
    results = [hnt_result, fil_result]
    fname = os.path.join(OUTPUT_DIR, "hnt_fil_results.json")
    with open(fname, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved: {fname}")

    return results


if __name__ == "__main__":
    main()
