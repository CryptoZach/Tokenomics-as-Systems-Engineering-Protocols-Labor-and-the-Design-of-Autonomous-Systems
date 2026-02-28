#!/usr/bin/env python3
"""
Task 2a (SEVERITY 2): Validate Helium burn classification.

PROBLEM: The action='burn' filter on Solana token transfers may capture
non-Data-Credit (DC) burns. We need to understand what the burn transactions
actually represent.

APPROACH: Run 5 targeted Dune queries to profile the burn data:
1. Distribution of HNT action types
2. Top burn signers (who is burning?)
3. Top mint signers (who is minting?)
4. Large individual burn events (>10,000 HNT)
5. October 2025 spike deep-dive
"""
import os
import requests
import json
import time

DUNE_API_KEY = os.environ.get("DUNE_API_KEY", "")
HEADERS = {"X-Dune-API-Key": DUNE_API_KEY, "Content-Type": "application/json"}
BASE = "https://api.dune.com/api/v1"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# HNT mint address on Solana
HNT_MINT = "hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux"


def execute_inline(sql, label):
    """Execute inline Dune query."""
    print(f"\n  Executing: {label}")
    try:
        resp = requests.post(
            f"{BASE}/sql/execute",
            headers=HEADERS,
            json={"sql": sql, "performance": "medium"},
            timeout=30,
        )
        if resp.status_code not in (200, 201):
            print(f"    Failed: {resp.status_code} {resp.text[:300]}")
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
                    f"{BASE}/execution/{eid}/results", headers=HEADERS, timeout=60
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
                return None
    except Exception as e:
        print(f"    Error: {e}")
    return None


# ============================================================
# QUERY 1: HNT transfer action types distribution
# ============================================================
QUERY_1_ACTION_TYPES = f"""
-- Q1: What action types exist for HNT transfers?
SELECT
    action,
    COUNT(*) AS n_txns,
    SUM(amount / 1e8) AS total_hnt,
    MIN(block_time) AS first_seen,
    MAX(block_time) AS last_seen
FROM tokens_solana.transfers
WHERE token_mint_address = '{HNT_MINT}'
    AND block_time >= DATE '2023-04-01'
GROUP BY 1
ORDER BY total_hnt DESC
"""

# ============================================================
# QUERY 2: Top burn signers (who is calling the burn?)
# ============================================================
QUERY_2_BURN_SIGNERS = f"""
-- Q2: Who are the top signers of burn transactions?
SELECT
    tx_signer,
    COUNT(*) AS n_burns,
    SUM(amount / 1e8) AS total_hnt_burned,
    MIN(block_time) AS first_burn,
    MAX(block_time) AS last_burn
FROM tokens_solana.transfers
WHERE token_mint_address = '{HNT_MINT}'
    AND action = 'burn'
    AND block_time >= DATE '2023-04-01'
GROUP BY 1
ORDER BY total_hnt_burned DESC
LIMIT 30
"""

# ============================================================
# QUERY 3: Top mint signers
# ============================================================
QUERY_3_MINT_SIGNERS = f"""
-- Q3: Who are the top signers of mint transactions?
SELECT
    tx_signer,
    COUNT(*) AS n_mints,
    SUM(amount / 1e8) AS total_hnt_minted,
    MIN(block_time) AS first_mint,
    MAX(block_time) AS last_mint
FROM tokens_solana.transfers
WHERE token_mint_address = '{HNT_MINT}'
    AND action = 'mint'
    AND block_time >= DATE '2023-04-01'
GROUP BY 1
ORDER BY total_hnt_minted DESC
LIMIT 30
"""

# ============================================================
# QUERY 4: Large individual burn events (>10,000 HNT)
# ============================================================
QUERY_4_LARGE_BURNS = f"""
-- Q4: Individual burn events > 10,000 HNT
SELECT
    block_time,
    tx_id,
    tx_signer,
    amount / 1e8 AS hnt_burned,
    from_owner
FROM tokens_solana.transfers
WHERE token_mint_address = '{HNT_MINT}'
    AND action = 'burn'
    AND amount / 1e8 > 10000
    AND block_time >= DATE '2023-04-01'
ORDER BY hnt_burned DESC
LIMIT 100
"""

# ============================================================
# QUERY 5: October 2025 spike deep-dive
# ============================================================
QUERY_5_OCT2025_SPIKE = f"""
-- Q5: October 2025 daily breakdown (S2R spike month)
SELECT
    DATE_TRUNC('day', block_time) AS day,
    action,
    COUNT(*) AS n_txns,
    SUM(amount / 1e8) AS total_hnt
FROM tokens_solana.transfers
WHERE token_mint_address = '{HNT_MINT}'
    AND block_time >= DATE '2025-10-01'
    AND block_time < DATE '2025-11-01'
GROUP BY 1, 2
ORDER BY 1, 2
"""


def main():
    if not DUNE_API_KEY:
        print("ERROR: Set DUNE_API_KEY environment variable")
        return

    print("=" * 60)
    print("HELIUM BURN CLASSIFICATION VALIDATION")
    print("=" * 60)

    queries = [
        (QUERY_1_ACTION_TYPES, "hnt_action_types"),
        (QUERY_2_BURN_SIGNERS, "hnt_burn_signers"),
        (QUERY_3_MINT_SIGNERS, "hnt_mint_signers"),
        (QUERY_4_LARGE_BURNS, "hnt_large_burns"),
        (QUERY_5_OCT2025_SPIKE, "hnt_oct2025_daily"),
    ]

    all_results = {}
    for sql, label in queries:
        rows = execute_inline(sql, label)
        all_results[label] = rows
        time.sleep(3)

    # Analyze results
    print("\n" + "=" * 60)
    print("ANALYSIS SUMMARY")
    print("=" * 60)

    # Action types
    if all_results.get("hnt_action_types"):
        print("\n1. HNT Action Types:")
        for r in all_results["hnt_action_types"]:
            print(
                f"   {r.get('action', '?'):>10}: {r.get('n_txns', 0):>10,} txns, "
                f"{r.get('total_hnt', 0):>15,.0f} HNT"
            )

    # Burn signers
    if all_results.get("hnt_burn_signers"):
        print("\n2. Top Burn Signers:")
        for r in all_results["hnt_burn_signers"][:10]:
            signer = str(r.get("tx_signer", ""))[:12]
            print(
                f"   {signer}...: {r.get('n_burns', 0):>8,} burns, "
                f"{r.get('total_hnt_burned', 0):>12,.0f} HNT"
            )

    # Large burns
    if all_results.get("hnt_large_burns"):
        print(f"\n3. Large Burns (>10K HNT): {len(all_results['hnt_large_burns'])} events")
        total_large = sum(r.get("hnt_burned", 0) for r in all_results["hnt_large_burns"])
        print(f"   Total in large burns: {total_large:,.0f} HNT")

    # Save combined analysis
    summary_path = os.path.join(OUTPUT_DIR, "burn_validation_summary.json")
    with open(summary_path, "w") as f:
        json.dump(
            {
                "queries_run": len([v for v in all_results.values() if v is not None]),
                "queries_total": len(queries),
                "results": {
                    k: len(v) if v else 0 for k, v in all_results.items()
                },
            },
            f,
            indent=2,
        )
    print(f"\nSaved summary: {summary_path}")


if __name__ == "__main__":
    main()
