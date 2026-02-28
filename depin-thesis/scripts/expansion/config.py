"""
Configuration for DePIN protocol expansion.
11 new protocols to add to the thesis.
"""

DUNE_API_KEY = "yGLinKdcZaQEr5b121QnW84jWDxzC8Ou"

# Known exchange hot wallets to EXCLUDE from governance concentration
EXCHANGE_ADDRESSES = {
    "0x28c6c06298d514db089934071355e5743bf21d60",  # Binance 14
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549",  # Binance 15
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d",  # Binance 16
    "0x56eddb7aa87536c09ccc2793473599fd21a8b17f",  # Binance 17
    "0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43",  # Coinbase 2
    "0x503828976d22510aad0201ac7ec88293211d23da",  # Coinbase 3
    "0xf977814e90da44bfa03b6295a0616a897441acec",  # Binance 8
    "0x47ac0fb4f2d84898e4d9e7b4dab3c24507a6d503",  # Binance cold
    "0xbe0eb53f46cd790cd13851d5eff43d12404d33e8",  # Binance cold 2
    "0x1d42064fc4beb5f8aaf85f4617ae8b3b5b8bd801",  # Uniswap: UNI Token Distributor
    "0x51c72848c68a965f66fa7a88855f9f7784502a7f",  # Coinbase 10
    "0x0000000000000000000000000000000000000000",  # Null address
    "0x000000000000000000000000000000000000dead",  # Dead address
    "0x5a52e96bacdabb82fd05763e25335261b270efcb",  # Binance hot
    "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",  # Binance old hot
    "0xd24400ae8bfebb18ca49be86258a3c749cf46853",  # Gemini
    "0x2910543af39aba0cd09dbb2d50200b3e800a63d2",  # Kraken
    "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b",  # OKX
}

# ── New DePIN Protocol Tokens ────────────────────────────────
# Tokens that can be queried via Dune (EVM chains)
EVM_TOKENS = {
    "DIMO": {
        "address": "0xE261D618a959aFfFd53168Cd07D12E37B26761db",
        "chain": "polygon",
        "decimals": 18,
        "protocol": "DIMO",
        "total_supply": 1_000_000_000,
        "coingecko_id": "dimo",
    },
    "WXM": {
        "address": "0xB6093B61544572Ab42A0E43AF08aBaFd41bF25a6",
        "chain": "arbitrum",
        "decimals": 18,
        "protocol": "WeatherXM",
        "total_supply": 100_000_000,
        "coingecko_id": "weatherxm",
    },
    "ANYONE": {
        "address": "0xFEaC2eAE96899709a43e252b6b92971d32f9c0f9",
        "chain": "ethereum",
        "decimals": 18,
        "protocol": "Anyone Protocol",
        "total_supply": 100_000_000,
        "coingecko_id": "anyone-protocol",
    },
    "IOTX": {
        "address": "0x6fB3e0A217407EFFf7Ca062D46c26E5d60a14d69",
        "chain": "ethereum",
        "decimals": 18,
        "protocol": "IoTeX",
        "total_supply": 9_540_779_324,
        "coingecko_id": "iotex",
    },
}

# Solana SPL tokens — need different Dune query approach
SOLANA_TOKENS = {
    "HONEY": {
        "mint": "4vMsoUT2BWatFweudnQM1xedRLfJgJ7hsWhs4xExf2Au",
        "protocol": "Hivemapper",
        "decimals": 9,
        "total_supply": 10_000_000_000,
        "coingecko_id": "hivemapper",
    },
    "GRASS": {
        "mint": "Grass7B4RdKfBCjTKgSqnXkqjwiGvQyFbuSCUJr3XXjs",
        "protocol": "Grass",
        "decimals": 9,
        "total_supply": 1_000_000_000,
        "coingecko_id": "grass",
    },
}

# Tokens without on-chain governance or no liquid token
NO_GOVERNANCE_TOKENS = {
    "UpRock": {"ticker": "UPT", "chain": "Solana", "note": "Early-stage; limited exchange listings; governance structure TBD"},
    "Wayru": {"ticker": "WRU", "chain": "Solana", "note": "Community WiFi; Solana-based; limited governance data"},
    "WiFiDabba": {"ticker": "N/A", "chain": "Polygon", "note": "Pre-token or limited distribution; centralized governance"},
    "CUDIS": {"ticker": "CUDIS", "chain": "Solana", "note": "Wearable health DePIN; early-stage token"},
    "ROVR": {"ticker": "ROVR", "chain": "Solana", "note": "Autonomous delivery; early-stage"},
}

# CoinGecko IDs for all protocols (for market data pull)
COINGECKO_IDS = {
    "iotex": "IoTeX",
    "dimo": "DIMO",
    "hivemapper": "Hivemapper",
    "weatherxm": "WeatherXM",
    "grass": "Grass",
    "anyone-protocol": "Anyone Protocol",
    "uprock": "UpRock",
    "wayru": "Wayru",
    "cudis": "CUDIS",
}

# Unit economics domains to research
UNIT_ECONOMICS_DOMAINS = [
    {"domain": "Bandwidth/proxy", "depin": "UpRock", "web2": ["Bright Data", "Oxylabs"], "unit": "$/GB residential proxy"},
    {"domain": "AI data", "depin": "Grass", "web2": ["Scale AI", "Appen"], "unit": "$/task or $/hour"},
    {"domain": "Vehicle data", "depin": "DIMO", "web2": ["Otonomo", "Wejo"], "unit": "$/vehicle/month"},
    {"domain": "Weather data", "depin": "WeatherXM", "web2": ["DTN", "Tomorrow.io"], "unit": "$/station/month"},
    {"domain": "VPN relay", "depin": "Anyone", "web2": ["NordVPN", "ExpressVPN"], "unit": "$/month"},
    {"domain": "Community WiFi", "depin": "Wayru/WiFiDabba", "web2": ["ISP retail"], "unit": "$/GB or $/month"},
    {"domain": "Wearable health", "depin": "CUDIS", "web2": ["Oura", "Whoop"], "unit": "$/device + $/month"},
    {"domain": "Street mapping", "depin": "Hivemapper", "web2": ["Google Maps Platform", "HERE"], "unit": "$/1000 tile requests"},
    {"domain": "Mobility/delivery", "depin": "ROVR", "web2": ["DoorDash", "Uber Eats"], "unit": "$/delivery"},
]
