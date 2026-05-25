"""Central coin catalog for supported market symbols."""

from __future__ import annotations


SUPPORTED_COINS = {
    "btc": {
        "name": "Bitcoin",
        "coingecko_id": "bitcoin",
        "coinglass_url": "https://www.coinglass.com/zh-TW/currencies/BTC",
    },
    "eth": {
        "name": "Ethereum",
        "coingecko_id": "ethereum",
        "coinglass_url": "https://www.coinglass.com/zh-TW/currencies/ETH",
    },
    "sol": {
        "name": "Solana",
        "coingecko_id": "solana",
        "coinglass_url": "https://www.coinglass.com/zh-TW/currencies/SOL",
    },
    "bnb": {
        "name": "BNB",
        "coingecko_id": "binancecoin",
        "coinglass_url": "https://www.coinglass.com/zh-TW/currencies/BNB",
    },
    "xrp": {
        "name": "XRP",
        "coingecko_id": "ripple",
        "coinglass_url": "https://www.coinglass.com/zh-TW/currencies/XRP",
    },
    "doge": {
        "name": "Dogecoin",
        "coingecko_id": "dogecoin",
        "coinglass_url": "https://www.coinglass.com/zh-TW/currencies/DOGE",
    },
    "ada": {
        "name": "Cardano",
        "coingecko_id": "cardano",
        "coinglass_url": "https://www.coinglass.com/zh-TW/currencies/ADA",
    },
    "ton": {
        "name": "Toncoin",
        "coingecko_id": "the-open-network",
        "coinglass_url": "https://www.coinglass.com/zh-TW/currencies/TON",
    },
    "trx": {
        "name": "TRON",
        "coingecko_id": "tron",
        "coinglass_url": "https://www.coinglass.com/zh-TW/currencies/TRX",
    },
    "avax": {
        "name": "Avalanche",
        "coingecko_id": "avalanche-2",
        "coinglass_url": "https://www.coinglass.com/zh-TW/currencies/AVAX",
    },
}


def is_supported_coin(symbol):
    normalized = str(symbol or "").strip().lower()
    supported = normalized in SUPPORTED_COINS
    if supported:
        print(f"[CoinCatalog] supported coin: {normalized.upper()}")
    else:
        print(f"[CoinCatalog] unsupported coin: {str(symbol or '').strip().upper() or 'UNKNOWN'}")
    return supported


def get_coin_info(symbol):
    normalized = str(symbol or "").strip().lower()
    coin_info = SUPPORTED_COINS.get(normalized)
    if coin_info is None:
        print(f"[CoinCatalog] unsupported coin: {str(symbol or '').strip().upper() or 'UNKNOWN'}")
        return None

    print(f"[CoinCatalog] supported coin: {normalized.upper()}")
    return coin_info
