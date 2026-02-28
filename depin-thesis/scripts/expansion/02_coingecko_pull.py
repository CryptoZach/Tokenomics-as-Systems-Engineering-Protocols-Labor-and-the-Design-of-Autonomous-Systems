#!/usr/bin/env python3
"""
Phase 1A-alt: Pull CoinGecko market data for all 11 DePIN protocols.
Captures: price, market cap, circulating supply, total supply, volume, FDV.
"""
import requests
import json
import time
import os
import sys

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "expansion")
os.makedirs(OUTPUT_DIR, exist_ok=True)

COINGECKO_API_KEY = "CG-xdnQo3sz9rMcWarQuTKnCa5W"

# CoinGecko IDs for all target protocols
PROTOCOLS = {
    "iotex": {"name": "IoTeX", "ticker": "IOTX", "chain": "IoTeX L1 + Ethereum"},
    "dimo": {"name": "DIMO", "ticker": "DIMO", "chain": "Polygon"},
    "hivemapper": {"name": "Hivemapper", "ticker": "HONEY", "chain": "Solana"},
    "weatherxm": {"name": "WeatherXM", "ticker": "WXM", "chain": "Arbitrum"},
    "grass": {"name": "Grass", "ticker": "GRASS", "chain": "Solana"},
    "anyone-protocol": {"name": "Anyone Protocol", "ticker": "ANYONE", "chain": "Ethereum"},
    "uprock": {"name": "UpRock", "ticker": "UPT", "chain": "Solana"},
    "wayru": {"name": "Wayru", "ticker": "WRU", "chain": "Solana"},
    "cudis": {"name": "CUDIS", "ticker": "CUDIS", "chain": "Solana"},
}

# Some IDs may need correction - try alternatives
ALTERNATIVE_IDS = {
    "anyone-protocol": ["anyone", "anyone-protocol"],
    "uprock": ["uprock", "uprock-com"],
    "wayru": ["wayru"],
    "cudis": ["cudis", "cudis-token"],
}


def fetch_coin_data(coin_id):
    """Fetch detailed coin data from CoinGecko."""
    base = "https://pro-api.coingecko.com" if COINGECKO_API_KEY else "https://api.coingecko.com"
    url = f"{base}/api/v3/coins/{coin_id}"
    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "true",
        "community_data": "false",
        "developer_data": "false",
    }
    headers = {}
    if COINGECKO_API_KEY:
        headers["x-cg-pro-api-key"] = COINGECKO_API_KEY
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code == 429:
            print(f"    Rate limited. Waiting 60s...")
            time.sleep(60)
            resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"    HTTP {resp.status_code}: {resp.text[:200]}")
            # Try free API as fallback
            if "pro-api" in url:
                free_url = url.replace("pro-api.coingecko.com", "api.coingecko.com")
                print(f"    Trying free API fallback...")
                resp = requests.get(free_url, params=params, timeout=30)
                if resp.status_code == 200:
                    return resp.json()
                print(f"    Free API also failed: {resp.status_code}")
            return None
        return resp.json()
    except Exception as e:
        print(f"    Error: {e}")
        return None


def main():
    print("=" * 70)
    print("CoinGecko DATA PULL FOR DePIN PROTOCOLS")
    print("=" * 70)

    results = []

    for cg_id, meta in PROTOCOLS.items():
        print(f"\n  {meta['name']} ({meta['ticker']}) -- CoinGecko ID: {cg_id}")

        # Try primary ID first, then alternatives
        ids_to_try = [cg_id] + ALTERNATIVE_IDS.get(cg_id, [])
        data = None
        used_id = None

        for try_id in ids_to_try:
            data = fetch_coin_data(try_id)
            if data and "market_data" in data:
                used_id = try_id
                break
            time.sleep(2)

        if not data or "market_data" not in data:
            print(f"    FAILED: No data for {cg_id}")
            results.append({
                "protocol": meta["name"],
                "ticker": meta["ticker"],
                "chain": meta["chain"],
                "coingecko_id": cg_id,
                "status": "NOT_FOUND",
            })
            time.sleep(3)
            continue

        md = data["market_data"]
        platforms = data.get("platforms", {})

        entry = {
            "protocol": meta["name"],
            "ticker": meta["ticker"],
            "chain": meta["chain"],
            "coingecko_id": used_id,
            "price_usd": md.get("current_price", {}).get("usd"),
            "market_cap_usd": md.get("market_cap", {}).get("usd"),
            "fully_diluted_valuation": md.get("fully_diluted_valuation", {}).get("usd"),
            "total_volume_24h": md.get("total_volume", {}).get("usd"),
            "circulating_supply": md.get("circulating_supply"),
            "total_supply": md.get("total_supply"),
            "max_supply": md.get("max_supply"),
            "price_change_24h_pct": md.get("price_change_percentage_24h"),
            "price_change_7d_pct": md.get("price_change_percentage_7d"),
            "price_change_30d_pct": md.get("price_change_percentage_30d"),
            "ath_usd": md.get("ath", {}).get("usd"),
            "ath_date": md.get("ath_date", {}).get("usd"),
            "atl_usd": md.get("atl", {}).get("usd"),
            "atl_date": md.get("atl_date", {}).get("usd"),
            "contract_addresses": platforms,
            "categories": data.get("categories", []),
            "description": data.get("description", {}).get("en", "")[:500],
            "links_homepage": data.get("links", {}).get("homepage", []),
            "genesis_date": data.get("genesis_date"),
            "status": "OK",
        }

        results.append(entry)

        # Print summary
        price = entry["price_usd"]
        mcap = entry["market_cap_usd"]
        circ = entry["circulating_supply"]
        total = entry["total_supply"]
        print(f"    Price: ${price:.6f}" if price and price < 1 else f"    Price: ${price:.2f}" if price else "    Price: N/A")
        print(f"    Market Cap: ${mcap:,.0f}" if mcap else "    Market Cap: N/A")
        print(f"    Circulating: {circ:,.0f}" if circ else "    Circulating: N/A")
        print(f"    Total Supply: {total:,.0f}" if total else "    Total Supply: N/A")
        print(f"    Categories: {', '.join(entry.get('categories', [])[:3])}")

        # Save individual file
        with open(os.path.join(OUTPUT_DIR, f"coingecko_{used_id}.json"), "w") as f:
            json.dump(data, f, indent=2)

        time.sleep(4)  # Respect rate limits

    # Save combined results
    json_path = os.path.join(OUTPUT_DIR, "coingecko_all_depin.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\n" + "=" * 70)
    print("CoinGecko RESULTS SUMMARY")
    print("=" * 70)
    print(f"  {'Protocol':<20} {'Ticker':<8} {'Price':>12} {'MCap':>14} {'Status'}")
    print(f"  {'─' * 65}")
    for r in results:
        price_s = f"${r['price_usd']:.4f}" if r.get("price_usd") else "N/A"
        mcap_s = f"${r['market_cap_usd']/1e6:.1f}M" if r.get("market_cap_usd") else "N/A"
        print(f"  {r['protocol']:<20} {r['ticker']:<8} {price_s:>12} {mcap_s:>14} {r['status']}")

    print(f"\nSaved: {json_path}")


if __name__ == "__main__":
    main()
