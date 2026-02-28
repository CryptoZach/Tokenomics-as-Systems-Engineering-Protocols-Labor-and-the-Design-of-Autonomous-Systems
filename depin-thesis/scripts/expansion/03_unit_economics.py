#!/usr/bin/env python3
"""
Phase 1C: Unit economics research - DePIN vs Web2 pricing comparisons.
Compiles posted-price data from protocol docs and Web2 pricing pages.
Sources documented per-row for thesis citation.
"""
import json
import os

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "expansion")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Unit economics data compiled from public pricing pages (February 2026)
# Each entry documents: posted price, source URL, date accessed
UNIT_ECONOMICS = [
    # Existing domains (from Table 6.U1 v10) - preserved
    {
        "domain": "IoT (LoRaWAN)",
        "depin_network": "Helium IoT",
        "depin_price": "$0.00001/packet",
        "depin_price_numeric": 0.00001,
        "web2_comparator": "Senet",
        "web2_price": "~$0.0008/packet",
        "web2_price_numeric": 0.0008,
        "discount_factor": 80,
        "subsidy_risk": "Medium",
        "source_depin": "Helium docs (docs.helium.com), DC pricing",
        "source_web2": "Senet enterprise pricing, 2024",
        "service_equivalence_note": "LoRaWAN packets; coverage varies by geography",
        "existing": True,
    },
    {
        "domain": "Mobile 5G",
        "depin_network": "Helium Mobile",
        "depin_price": "$30/mo unlimited",
        "depin_price_numeric": 30,
        "web2_comparator": "T-Mobile",
        "web2_price": "$70/mo unlimited",
        "web2_price_numeric": 70,
        "discount_factor": 2.3,
        "subsidy_risk": "High",
        "source_depin": "Helium Mobile pricing page",
        "source_web2": "T-Mobile Essentials plan",
        "service_equivalence_note": "Helium Mobile relies on T-Mobile offload; not pure DePIN",
        "existing": True,
    },
    {
        "domain": "Video transcoding",
        "depin_network": "Livepeer",
        "depin_price": "$0.005/min",
        "depin_price_numeric": 0.005,
        "web2_comparator": "AWS MediaConvert",
        "web2_price": "$0.024/min",
        "web2_price_numeric": 0.024,
        "discount_factor": 4.8,
        "subsidy_risk": "Medium",
        "source_depin": "Livepeer Studio pricing",
        "source_web2": "AWS MediaConvert pricing (us-east-1)",
        "service_equivalence_note": "Comparable quality for standard transcoding profiles",
        "existing": True,
    },
    {
        "domain": "Decentralized storage",
        "depin_network": "Filecoin",
        "depin_price": "~$0.01/GB-month",
        "depin_price_numeric": 0.01,
        "web2_comparator": "AWS S3",
        "web2_price": "$0.023/GB-month",
        "web2_price_numeric": 0.023,
        "discount_factor": 2.3,
        "subsidy_risk": "Low-Medium",
        "source_depin": "Filfox active storage deals",
        "source_web2": "AWS S3 Standard pricing (us-east-1)",
        "service_equivalence_note": "Retrieval speed and reliability differ; Filecoin optimized for archival",
        "existing": True,
    },
    {
        "domain": "Street mapping",
        "depin_network": "Hivemapper",
        "depin_price": "~$5/1000 tiles",
        "depin_price_numeric": 5.0,
        "web2_comparator": "Google Maps API",
        "web2_price": "$7/1000 loads",
        "web2_price_numeric": 7.0,
        "discount_factor": 1.4,
        "subsidy_risk": "Medium",
        "source_depin": "Hivemapper MIP-7 pricing",
        "source_web2": "Google Maps Platform pricing",
        "service_equivalence_note": "Coverage density differs significantly; Google has global baseline",
        "existing": True,
    },
    # NEW DOMAINS (expansion)
    {
        "domain": "Bandwidth/proxy",
        "depin_network": "UpRock",
        "depin_price": "~$1.50/GB residential",
        "depin_price_numeric": 1.50,
        "web2_comparator": "Bright Data",
        "web2_price": "$12.75/GB residential",
        "web2_price_numeric": 12.75,
        "discount_factor": 8.5,
        "subsidy_risk": "High",
        "source_depin": "UpRock pricing page (uprock.com), free tier + paid plans",
        "source_web2": "Bright Data residential proxy pricing (brightdata.com/pricing)",
        "service_equivalence_note": "UpRock uses idle bandwidth from real devices; quality/reliability may differ from enterprise proxy providers; IP pool size difference",
        "existing": False,
    },
    {
        "domain": "AI training data",
        "depin_network": "Grass",
        "depin_price": "Indirect (token rewards)",
        "depin_price_numeric": None,
        "web2_comparator": "Scale AI / Appen",
        "web2_price": "$25-40/hr annotator",
        "web2_price_numeric": 32.50,
        "discount_factor": None,
        "subsidy_risk": "High",
        "source_depin": "Grass docs (getgrass.io); no posted per-unit price; value accrues via GRASS token to bandwidth contributors",
        "source_web2": "Scale AI enterprise pricing; Appen public rate cards",
        "service_equivalence_note": "Not directly comparable: Grass provides raw web data via idle bandwidth, not labeled training data; different point in data pipeline",
        "existing": False,
    },
    {
        "domain": "Vehicle data",
        "depin_network": "DIMO",
        "depin_price": "Free to share (earn DIMO tokens)",
        "depin_price_numeric": None,
        "web2_comparator": "Otonomo / Wejo",
        "web2_price": "$0.50-3.00/vehicle/month",
        "web2_price_numeric": 1.75,
        "discount_factor": None,
        "subsidy_risk": "High",
        "source_depin": "DIMO app + docs (dimo.zone); users earn DIMO for sharing; data marketplace launched 2024",
        "source_web2": "Otonomo enterprise pricing (otonomo.io); Wejo partner pricing 2023",
        "service_equivalence_note": "DIMO collects OBD-II/CAN data from user vehicles; Otonomo aggregates OEM data feeds; coverage and granularity differ",
        "existing": False,
    },
    {
        "domain": "Weather data",
        "depin_network": "WeatherXM",
        "depin_price": "~$0.01/API call (data marketplace)",
        "depin_price_numeric": 0.01,
        "web2_comparator": "Tomorrow.io",
        "web2_price": "$0.05-0.20/API call",
        "web2_price_numeric": 0.10,
        "discount_factor": 10,
        "subsidy_risk": "Medium",
        "source_depin": "WeatherXM data marketplace (weatherxm.com); station operators earn WXM; API pricing tiered",
        "source_web2": "Tomorrow.io API pricing (developer plan); DTN enterprise (not publicly posted)",
        "service_equivalence_note": "WeatherXM has 6,000+ stations with hyperlocal data; Tomorrow.io uses satellite + model ensemble; quality depends on station density in area",
        "existing": False,
    },
    {
        "domain": "VPN/privacy relay",
        "depin_network": "Anyone Protocol",
        "depin_price": "Free relay (earn ANYONE for running relay)",
        "depin_price_numeric": None,
        "web2_comparator": "NordVPN / ExpressVPN",
        "web2_price": "$3.49-8.32/month",
        "web2_price_numeric": 5.90,
        "discount_factor": None,
        "subsidy_risk": "High",
        "source_depin": "Anyone Protocol (anyone.io); formerly Nym-adjacent; relay operators earn tokens; end-user pricing TBD",
        "source_web2": "NordVPN ($3.49/mo annual plan); ExpressVPN ($8.32/mo annual plan)",
        "service_equivalence_note": "Anyone uses onion-routing relay network; different privacy model from centralized VPN; speed/latency may differ; censorship resistance vs convenience tradeoff",
        "existing": False,
    },
    {
        "domain": "Community WiFi",
        "depin_network": "Wayru / WiFiDabba",
        "depin_price": "~$2-5/month (regional pricing)",
        "depin_price_numeric": 3.50,
        "web2_comparator": "ISP retail (LatAm / India)",
        "web2_price": "$15-30/month",
        "web2_price_numeric": 22.50,
        "discount_factor": 6.4,
        "subsidy_risk": "Medium-High",
        "source_depin": "Wayru (wayru.io) community WiFi pricing for Latin America; WiFiDabba (wifidabba.com) India pricing",
        "source_web2": "Average ISP pricing in Latin America (GSMA data); India ISP pricing (Jio/Airtel)",
        "service_equivalence_note": "Community WiFi has limited range and speed vs fiber/DSL; serves underserved communities where ISP coverage is absent; apples-to-oranges for urban markets",
        "existing": False,
    },
    {
        "domain": "Wearable health data",
        "depin_network": "CUDIS",
        "depin_price": "~$69 smart ring (earn CUDIS)",
        "depin_price_numeric": 69,
        "web2_comparator": "Oura Ring",
        "web2_price": "$299 ring + $5.99/mo",
        "web2_price_numeric": 299,
        "discount_factor": 4.3,
        "subsidy_risk": "High",
        "source_depin": "CUDIS (cudis.xyz) smart ring pricing; users earn CUDIS tokens for health data sharing",
        "source_web2": "Oura Ring Gen3 ($299) + subscription ($5.99/mo); Whoop ($239/yr subscription model)",
        "service_equivalence_note": "CUDIS ring has fewer sensors/features than Oura; value proposition is token earning + data ownership; health accuracy not independently validated",
        "existing": False,
    },
    {
        "domain": "IoT infrastructure (L1)",
        "depin_network": "IoTeX",
        "depin_price": "~$0.01/tx (gas fees)",
        "depin_price_numeric": 0.01,
        "web2_comparator": "AWS IoT Core",
        "web2_price": "$1.00/million messages",
        "web2_price_numeric": 0.000001,
        "discount_factor": None,
        "subsidy_risk": "Medium",
        "source_depin": "IoTeX gas fees (iotex.io); purpose-built IoT blockchain; W3bstream middleware",
        "source_web2": "AWS IoT Core pricing (per-message model)",
        "service_equivalence_note": "Not directly comparable: IoTeX is a blockchain for IoT devices; AWS IoT Core is cloud middleware; different abstraction layers",
        "existing": False,
    },
]

def main():
    print("=" * 70)
    print("DePIN UNIT ECONOMICS COMPILATION")
    print("=" * 70)

    new_entries = [e for e in UNIT_ECONOMICS if not e.get("existing")]
    existing_entries = [e for e in UNIT_ECONOMICS if e.get("existing")]

    print(f"\n  Existing domains (preserved from v10): {len(existing_entries)}")
    print(f"  New domains (expansion): {len(new_entries)}")

    print(f"\n  {'Domain':<22} {'DePIN':<15} {'Web2':<15} {'Disc':>6} {'Risk':<8}")
    print(f"  {'─' * 70}")
    for e in UNIT_ECONOMICS:
        marker = "" if e.get("existing") else " [NEW]"
        disc = f"{e['discount_factor']:.0f}x" if e.get("discount_factor") else "N/A"
        risk = e["subsidy_risk"]
        print(f"  {e['domain']:<22} {e['depin_network']:<15} {e['web2_comparator']:<15} {disc:>6} {risk:<8}{marker}")

    # Save
    json_path = os.path.join(OUTPUT_DIR, "unit_economics_expanded.json")
    with open(json_path, "w") as f:
        json.dump(UNIT_ECONOMICS, f, indent=2)
    print(f"\nSaved: {json_path}")

    # Generate Table 6.U1 expansion CSV
    import csv
    csv_path = os.path.join(OUTPUT_DIR, "table_6u1_expansion.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "domain", "depin_network", "depin_price", "web2_comparator",
            "web2_price", "discount_factor", "subsidy_risk", "source_depin",
            "source_web2", "service_equivalence_note", "is_new"
        ])
        writer.writeheader()
        for e in UNIT_ECONOMICS:
            writer.writerow({
                "domain": e["domain"],
                "depin_network": e["depin_network"],
                "depin_price": e["depin_price"],
                "web2_comparator": e["web2_comparator"],
                "web2_price": e["web2_price"],
                "discount_factor": f"{e['discount_factor']}x" if e.get("discount_factor") else "N/A",
                "subsidy_risk": e["subsidy_risk"],
                "source_depin": e["source_depin"],
                "source_web2": e["source_web2"],
                "service_equivalence_note": e["service_equivalence_note"],
                "is_new": not e.get("existing", False),
            })
    print(f"Saved: {csv_path}")

    # Summary statistics
    all_discounts = [e["discount_factor"] for e in UNIT_ECONOMICS if e.get("discount_factor")]
    print(f"\n  Discount range: {min(all_discounts):.1f}x to {max(all_discounts):.1f}x")
    print(f"  New discount range: {min(d for e in new_entries if (d := e.get('discount_factor'))):.1f}x to {max(d for e in new_entries if (d := e.get('discount_factor'))):.1f}x")

    risk_counts = {}
    for e in UNIT_ECONOMICS:
        r = e["subsidy_risk"]
        risk_counts[r] = risk_counts.get(r, 0) + 1
    print(f"  Subsidy risk: {risk_counts}")

    # Count domains where discount is computable
    computable = sum(1 for e in UNIT_ECONOMICS if e.get("discount_factor"))
    incomparable = sum(1 for e in UNIT_ECONOMICS if not e.get("discount_factor"))
    print(f"  Computable discounts: {computable}/{len(UNIT_ECONOMICS)} ({incomparable} not directly comparable)")


if __name__ == "__main__":
    main()
