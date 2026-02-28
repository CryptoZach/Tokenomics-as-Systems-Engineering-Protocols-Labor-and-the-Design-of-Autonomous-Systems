#!/usr/bin/env python3
"""
Task 3a: Snapshot governance voting power concentration.

Uses the Snapshot GraphQL API to get:
1. Total proposals and voter counts per protocol
2. Top voter participation rates
3. Voting power concentration (if available via strategies)
"""
import requests
import json
import time
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_API = "https://hub.snapshot.org/graphql"

# Snapshot space IDs for DePIN-relevant governance protocols
SPACES = {
    "uniswapgovernance.eth": "Uniswap",
    "comp-vote.eth": "Compound",
    "aave.eth": "Aave",
    "hnt.xyz": "Helium",
    "livepeer-community.eth": "Livepeer",
    "opcollective.eth": "Optimism",
    "graphprotocol.eth": "The Graph",
}

# Alternate IDs to try if primary fails
SPACE_ALTERNATES = {
    "hnt.xyz": ["heliumdao.eth", "heliumfoundation.eth", "helium-vote.eth"],
    "livepeer-community.eth": ["livepeer.eth"],
    "graphprotocol.eth": ["thegraphcouncil.eth", "graph-protocol.eth"],
}


def query_snapshot(query, variables=None):
    """Execute Snapshot GraphQL query."""
    try:
        resp = requests.post(
            SNAPSHOT_API,
            json={"query": query, "variables": variables or {}},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json().get("data")
        print(f"    HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"    Error: {e}")
    return None


def get_space_info(space_id):
    """Get basic space information."""
    query = """
    query Space($id: String!) {
        space(id: $id) {
            id
            name
            about
            members
            proposalsCount
            followersCount
            voting {
                delay
                period
                quorum
            }
        }
    }
    """
    return query_snapshot(query, {"id": space_id})


def get_recent_proposals(space_id, limit=20):
    """Get recent proposals with vote counts."""
    query = """
    query Proposals($space: String!, $limit: Int!) {
        proposals(
            where: { space: $space, state: "closed" },
            orderBy: "created",
            orderDirection: desc,
            first: $limit
        ) {
            id
            title
            state
            votes
            scores_total
            quorum
            created
            end
        }
    }
    """
    return query_snapshot(query, {"space": space_id, "limit": limit})


def get_top_voters(proposal_id, limit=50):
    """Get top voters for a specific proposal."""
    query = """
    query Votes($proposal: String!, $limit: Int!) {
        votes(
            where: { proposal: $proposal },
            orderBy: "vp",
            orderDirection: desc,
            first: $limit
        ) {
            voter
            vp
            choice
        }
    }
    """
    return query_snapshot(query, {"proposal": proposal_id, "limit": limit})


def compute_voting_concentration(votes):
    """Compute HHI and Gini of voting power."""
    if not votes or len(votes) < 2:
        return None, None, None, None

    vps = sorted([v.get("vp", 0) for v in votes if v.get("vp", 0) > 0], reverse=True)
    if not vps:
        return None, None, None, None

    total = sum(vps)
    shares = [v / total for v in vps]

    hhi = sum(s**2 for s in shares)

    n = len(vps)
    sorted_vps = sorted(vps)
    cum = 0
    for i, v in enumerate(sorted_vps):
        cum += (2 * (i + 1) - n - 1) * v
    gini = abs(cum / (n * total)) if total > 0 and n > 1 else 0

    top1 = vps[0] / total if vps else 0
    top10 = sum(vps[:10]) / total if len(vps) >= 10 else None

    return round(hhi, 6), round(gini, 4), round(top1, 4), round(top10, 4) if top10 else None


def main():
    print("=" * 60)
    print("SNAPSHOT GOVERNANCE DATA COLLECTION")
    print("=" * 60)

    results = []

    for space_id, protocol in SPACES.items():
        print(f"\n--- {protocol} ({space_id}) ---")

        # Get space info
        space_data = get_space_info(space_id)
        space = space_data.get("space") if space_data else None

        if not space:
            # Try alternates
            alts = SPACE_ALTERNATES.get(space_id, [])
            for alt in alts:
                print(f"    Trying alternate: {alt}")
                space_data = get_space_info(alt)
                space = space_data.get("space") if space_data else None
                if space:
                    space_id = alt
                    break

        if not space:
            print(f"    Space not found")
            results.append({
                "protocol": protocol,
                "space_id": space_id,
                "found": False,
            })
            time.sleep(1)
            continue

        print(f"    Name: {space.get('name')}")
        print(f"    Members: {space.get('members', 'N/A')}")
        print(f"    Proposals: {space.get('proposalsCount', 'N/A')}")
        print(f"    Followers: {space.get('followersCount', 'N/A')}")

        # Get recent proposals
        proposals_data = get_recent_proposals(space_id)
        proposals = proposals_data.get("proposals", []) if proposals_data else []
        print(f"    Recent closed proposals: {len(proposals)}")

        # Analyze voting concentration on most recent high-turnout proposal
        voting_analysis = None
        if proposals:
            # Pick the proposal with most votes
            best = max(proposals, key=lambda p: p.get("votes", 0))
            print(f"    Best proposal: '{best.get('title', '?')[:50]}...' ({best.get('votes', 0)} votes)")

            votes_data = get_top_voters(best["id"])
            votes = votes_data.get("votes", []) if votes_data else []

            if votes:
                hhi, gini, top1, top10 = compute_voting_concentration(votes)
                voting_analysis = {
                    "proposal_id": best["id"],
                    "proposal_votes": best.get("votes", 0),
                    "sampled_voters": len(votes),
                    "voting_power_hhi": hhi,
                    "voting_power_gini": gini,
                    "top1_vp_share": top1,
                    "top10_vp_share": top10,
                }
                print(f"    Voting HHI: {hhi}, Gini: {gini}")
                print(f"    Top 1 VP share: {top1:.2%}" if top1 else "    Top 1 VP share: N/A")

        # Compute average voter turnout
        avg_votes = 0
        if proposals:
            avg_votes = sum(p.get("votes", 0) for p in proposals) / len(proposals)

        result = {
            "protocol": protocol,
            "space_id": space_id,
            "found": True,
            "members": space.get("members"),
            "proposals_count": space.get("proposalsCount"),
            "followers": space.get("followersCount"),
            "recent_proposals_sampled": len(proposals),
            "avg_voter_turnout": round(avg_votes, 1),
            "voting_concentration": voting_analysis,
        }
        results.append(result)
        time.sleep(2)

    # Save results
    json_path = os.path.join(OUTPUT_DIR, "snapshot_governance_data.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\n" + "=" * 60)
    print("SNAPSHOT GOVERNANCE SUMMARY")
    print("=" * 60)
    for r in results:
        if r.get("found"):
            vc = r.get("voting_concentration", {}) or {}
            hhi_s = f"{vc.get('voting_power_hhi', 'N/A')}"
            print(
                f"  {r['protocol']:<15} proposals={r.get('proposals_count', 'N/A'):>5} "
                f"avg_voters={r.get('avg_voter_turnout', 0):>6.0f} "
                f"vp_hhi={hhi_s}"
            )
        else:
            print(f"  {r['protocol']:<15} NOT FOUND on Snapshot")

    print(f"\nSaved: {json_path}")


if __name__ == "__main__":
    main()
