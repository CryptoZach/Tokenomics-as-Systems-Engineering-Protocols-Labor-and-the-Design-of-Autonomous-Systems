#!/usr/bin/env python3
"""
Task 1a: Search Dune for existing Helium community queries.
"""
import os
import requests
import json
import time

DUNE_API_KEY = os.environ.get("DUNE_API_KEY", "")
HEADERS = {"X-Dune-API-Key": DUNE_API_KEY}
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

def search_dune_queries(keyword, limit=10):
    """Search for existing Dune queries by keyword."""
    url = "https://api.dune.com/api/v1/query/search"
    params = {"q": keyword, "limit": limit}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            queries = data.get("queries", data if isinstance(data, list) else [])
            return queries
        else:
            print(f"  Search returned {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"  Search error: {e}")
    return []

search_terms = [
    "helium data credits burn",
    "helium HNT burn solana",
    "helium DC burn daily",
    "helium network stats solana",
    "helium mobile subscribers",
    "HNT token supply",
]

all_found = []
for term in search_terms:
    print(f"\nSearching: '{term}'")
    results = search_dune_queries(term)
    for q in results[:3]:
        qid = q.get("query_id", q.get("id", "?"))
        name = q.get("name", q.get("title", "untitled"))
        owner = q.get("owner", q.get("user", {}).get("name", "?"))
        print(f"  [{qid}] {name} (by {owner})")
        all_found.append({"id": qid, "name": name, "owner": owner, "search": term})
    time.sleep(2)

with open(f"{OUTPUT_DIR}/dune_helium_queries_found.json", "w") as f:
    json.dump(all_found, f, indent=2)
print(f"\nSaved {len(all_found)} discovered queries")
