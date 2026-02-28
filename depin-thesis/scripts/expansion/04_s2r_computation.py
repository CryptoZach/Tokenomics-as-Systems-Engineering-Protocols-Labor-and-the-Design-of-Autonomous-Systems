#!/usr/bin/env python3
"""
Phase 1B: S2R (Subsidy-to-Revenue ratio) computation for DePIN protocols.
S2R = token_burns_in_period / token_issuance_in_period

For protocols without on-chain burn data accessible via Dune, we document
the burn mechanism and classify S2R status.
"""
import json
import os
import sys
import requests
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DUNE_API_KEY

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
                    fname = os.path.join(OUTPUT_DIR, f"dune_s2r_{label}.json")
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


# Protocol S2R analysis - classified by data availability
S2R_PROFILES = {
    "Hivemapper": {
        "ticker": "HONEY",
        "chain": "solana",
        "sink_type": "Map credit burn (HONEY burned when clients consume map data via Map Credits)",
        "burn_mechanism": "Burn-and-mint: clients purchase Map Credits with HONEY (burned); contributors earn HONEY for dashcam imagery",
        "s2r_status": "active_burn",
        "mint_address": "4vMsoUT2BWatFweudnQM1xedRLfJgJ7hsWhs4xExf2Au",
        "notes": "MIP-7 introduced map credit pricing; burn data queryable on Solana",
    },
    "DIMO": {
        "ticker": "DIMO",
        "chain": "polygon",
        "sink_type": "Data marketplace burn (DIMO tokens burned for marketplace access)",
        "burn_mechanism": "License burn: developers burn DIMO to access vehicle data via DIMO Developer License; stake required for data consumers",
        "s2r_status": "early_burn",
        "contract": "0xE261D618a959aFfFd53168Cd07D12E37B26761db",
        "notes": "Marketplace launched 2024; burn volumes likely small",
    },
    "IoTeX": {
        "ticker": "IOTX",
        "chain": "iotex_l1",
        "sink_type": "Gas fee burn (similar to EIP-1559)",
        "burn_mechanism": "Transaction fees partially burned on IoTeX L1; staking locks reduce circulating supply",
        "s2r_status": "active_burn",
        "notes": "IoTeX L1 has native burn; not queryable via standard Dune tables",
    },
    "WeatherXM": {
        "ticker": "WXM",
        "chain": "arbitrum",
        "sink_type": "Data subscription burn (WXM burned for weather data access)",
        "burn_mechanism": "Data consumers burn WXM to access weather API/data marketplace; station operators earn WXM for verified weather data",
        "s2r_status": "early_burn",
        "contract": "0xB6093B61544572Ab42A0E43AF08aBaF6b3d2ad15",
        "notes": "Data marketplace active; burn volumes growing but small relative to emissions",
    },
    "Grass": {
        "ticker": "GRASS",
        "chain": "solana",
        "sink_type": "Token staking (no confirmed burn mechanism)",
        "burn_mechanism": "GRASS tokens staked for network access; no confirmed burn-and-mint; primarily emission-based rewards for bandwidth sharing",
        "s2r_status": "no_burn",
        "notes": "Revenue model is data sales (AI companies buy scraped data); token capture mechanism is indirect via staking",
    },
    "Anyone Protocol": {
        "ticker": "ANYONE",
        "chain": "ethereum",
        "sink_type": "Stake/lock for relay operation",
        "burn_mechanism": "Relay operators stake ANYONE tokens; bandwidth consumers may pay in ANYONE; no confirmed burn mechanism",
        "s2r_status": "no_burn",
        "notes": "Privacy/VPN relay; token economics still evolving",
    },
    "UpRock": {
        "ticker": "UPT",
        "chain": "solana",
        "sink_type": "Unclear/early-stage",
        "burn_mechanism": "Bandwidth contributors earn UPT; enterprise clients purchase proxy access; token burn/buyback details not public",
        "s2r_status": "unknown",
        "notes": "Early-stage protocol; tokenomics may not be fully deployed",
    },
    "Wayru": {
        "ticker": "WRU",
        "chain": "solana",
        "sink_type": "Service payment",
        "burn_mechanism": "WiFi users pay for connectivity; operators earn WRU; burn mechanism unclear from public docs",
        "s2r_status": "unknown",
        "notes": "Community WiFi focused on Latin America; limited tokenomics disclosure",
    },
    "WiFiDabba": {
        "ticker": "N/A",
        "chain": "polygon",
        "sink_type": "N/A",
        "burn_mechanism": "No public token; centralized service model with blockchain backend for payments",
        "s2r_status": "no_token",
        "notes": "India-focused community WiFi; may use Polygon for micropayments but no governance token",
    },
    "CUDIS": {
        "ticker": "CUDIS",
        "chain": "solana",
        "sink_type": "Data marketplace (planned)",
        "burn_mechanism": "Users earn CUDIS for health data from smart ring; data consumers may burn/stake CUDIS for access; mechanism details limited",
        "s2r_status": "unknown",
        "notes": "Early-stage wearable DePIN; tokenomics likely not mature",
    },
    "ROVR": {
        "ticker": "ROVR",
        "chain": "solana",
        "sink_type": "Unknown",
        "burn_mechanism": "Autonomous delivery network; token economics not well documented",
        "s2r_status": "unknown",
        "notes": "Very early stage; limited public information on burn mechanism",
    },
}


def try_hivemapper_burns():
    """Query Hivemapper HONEY burns from Solana."""
    sql = """
-- Monthly HONEY burns on Solana (last 6 months)
SELECT
    date_trunc('month', block_time) AS month,
    SUM(CASE WHEN action = 'burn' THEN ABS(amount) / POWER(10, 9) ELSE 0 END) AS honey_burned,
    SUM(CASE WHEN action = 'mint' THEN amount / POWER(10, 9) ELSE 0 END) AS honey_minted
FROM tokens_solana.transfers
WHERE token_mint_address = '4vMsoUT2BWatFweudnQM1xedRLfJgJ7hsWhs4xExf2Au'
    AND block_time >= NOW() - INTERVAL '6' MONTH
GROUP BY 1
ORDER BY 1
"""
    return execute_inline(sql, "hivemapper_burns")


def try_dimo_burns():
    """Query DIMO burns from Polygon."""
    sql = """
-- Monthly DIMO burns on Polygon
WITH burns AS (
    SELECT
        date_trunc('month', evt_block_time) AS month,
        SUM(CAST(value AS DOUBLE) / 1e18) AS amount
    FROM erc20_polygon.evt_Transfer
    WHERE contract_address = 0xE261D618a959aFfFd53168Cd07D12E37B26761db
        AND "to" = 0x0000000000000000000000000000000000000000
        AND evt_block_time >= NOW() - INTERVAL '6' MONTH
    GROUP BY 1
),
mints AS (
    SELECT
        date_trunc('month', evt_block_time) AS month,
        SUM(CAST(value AS DOUBLE) / 1e18) AS amount
    FROM erc20_polygon.evt_Transfer
    WHERE contract_address = 0xE261D618a959aFfFd53168Cd07D12E37B26761db
        AND "from" = 0x0000000000000000000000000000000000000000
        AND evt_block_time >= NOW() - INTERVAL '6' MONTH
    GROUP BY 1
)
SELECT
    COALESCE(b.month, m.month) AS month,
    COALESCE(b.amount, 0) AS dimo_burned,
    COALESCE(m.amount, 0) AS dimo_minted
FROM burns b
FULL OUTER JOIN mints m ON b.month = m.month
ORDER BY 1
"""
    return execute_inline(sql, "dimo_burns")


def main():
    print("=" * 70)
    print("DePIN S2R COMPUTATION AND CLASSIFICATION")
    print("=" * 70)

    results = []

    # Try on-chain queries for protocols with known burn mechanisms
    print("\n--- Querying on-chain burn data ---")

    # Hivemapper
    print("\n[Hivemapper HONEY burns]")
    hivemapper_data = try_hivemapper_burns()
    if hivemapper_data:
        for row in hivemapper_data:
            burned = float(row.get("honey_burned", 0))
            minted = float(row.get("honey_minted", 0))
            s2r = burned / minted if minted > 0 else 0
            print(f"  {row.get('month', 'N/A')}: burned={burned:,.0f}, minted={minted:,.0f}, S2R={s2r:.4f}")
        S2R_PROFILES["Hivemapper"]["on_chain_data"] = hivemapper_data
    else:
        print("  No data returned")

    time.sleep(3)

    # DIMO
    print("\n[DIMO burns]")
    dimo_data = try_dimo_burns()
    if dimo_data:
        for row in dimo_data:
            burned = float(row.get("dimo_burned", 0))
            minted = float(row.get("dimo_minted", 0))
            s2r = burned / minted if minted > 0 else 0
            print(f"  {row.get('month', 'N/A')}: burned={burned:,.0f}, minted={minted:,.0f}, S2R={s2r:.4f}")
        S2R_PROFILES["DIMO"]["on_chain_data"] = dimo_data
    else:
        print("  No data returned")

    # Build results table
    print("\n\n" + "=" * 70)
    print("S2R CLASSIFICATION SUMMARY")
    print("=" * 70)
    print(f"  {'Protocol':<20} {'Sink Type':<30} {'S2R Status':<15} {'S2R Value'}")
    print(f"  {'─' * 80}")

    for name, profile in S2R_PROFILES.items():
        s2r_val = "N/A"
        if profile.get("on_chain_data"):
            # Compute average S2R from on-chain data
            burns_total = sum(float(r.get(f"{profile['ticker'].lower()}_burned", r.get("honey_burned", r.get("dimo_burned", 0)))) for r in profile["on_chain_data"])
            mints_total = sum(float(r.get(f"{profile['ticker'].lower()}_minted", r.get("honey_minted", r.get("dimo_minted", 0)))) for r in profile["on_chain_data"])
            if mints_total > 0:
                s2r_val = f"{burns_total / mints_total:.4f}"
                profile["s2r_computed"] = round(burns_total / mints_total, 4)

        status = profile["s2r_status"]
        sink = profile["sink_type"][:28]
        print(f"  {name:<20} {sink:<30} {status:<15} {s2r_val}")

        results.append({
            "protocol": name,
            "ticker": profile["ticker"],
            "chain": profile["chain"],
            "sink_type": profile["sink_type"],
            "burn_mechanism": profile["burn_mechanism"],
            "s2r_status": profile["s2r_status"],
            "s2r_computed": profile.get("s2r_computed"),
            "notes": profile["notes"],
        })

    # Save
    json_path = os.path.join(OUTPUT_DIR, "s2r_classification.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved: {json_path}")

    # Summary for Table 6.D1 expansion
    print("\n--- Table 6.D1 Expansion Candidates ---")
    for r in results:
        if r["s2r_status"] in ("active_burn", "early_burn"):
            s2r_str = f"S2R={r['s2r_computed']:.4f}" if r.get("s2r_computed") else "S2R=TBD (on-chain query needed)"
            print(f"  {r['protocol']}: {r['sink_type']} | {s2r_str}")
        elif r["s2r_status"] == "no_burn":
            print(f"  {r['protocol']}: No native-token burn (analogous to Livepeer) | S2R ~ 0")
        else:
            print(f"  {r['protocol']}: {r['s2r_status']} | Insufficient data for S2R computation")


if __name__ == "__main__":
    main()
