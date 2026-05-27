"""Coin alias normalization helpers for the agent layer."""

from __future__ import annotations

import re


COIN_ALIASES = {
    # BTC
    "btc": "BTC",
    "BTC": "BTC",
    "bitcoin": "BTC",
    "Bitcoin": "BTC",
    "比特幣": "BTC",
    "大餅": "BTC",
    # ETH
    "eth": "ETH",
    "ETH": "ETH",
    "ethereum": "ETH",
    "Ethereum": "ETH",
    "以太幣": "ETH",
    "二餅": "ETH",
    "姨太": "ETH",
    # SOL
    "sol": "SOL",
    "SOL": "SOL",
    "solana": "SOL",
    "Solana": "SOL",
    "索拉納": "SOL",
    # DOGE
    "doge": "DOGE",
    "DOGE": "DOGE",
    "dogecoin": "DOGE",
    "Dogecoin": "DOGE",
    "狗狗幣": "DOGE",
    "狗幣": "DOGE",
    # BNB
    "bnb": "BNB",
    "BNB": "BNB",
    "binance coin": "BNB",
    "幣安幣": "BNB",
    # XRP
    "xrp": "XRP",
    "XRP": "XRP",
    "ripple": "XRP",
    "瑞波幣": "XRP",
    # ADA
    "ada": "ADA",
    "ADA": "ADA",
    "cardano": "ADA",
    "艾達幣": "ADA",
    # TON
    "ton": "TON",
    "TON": "TON",
    "the open network": "TON",
    "電報幣": "TON",
    # TRX
    "trx": "TRX",
    "TRX": "TRX",
    "tron": "TRX",
    "波場": "TRX",
    # AVAX
    "avax": "AVAX",
    "AVAX": "AVAX",
    "avalanche": "AVAX",
    "雪崩幣": "AVAX",
}

SUPPORTED_COINS = [
    "BTC",
    "ETH",
    "SOL",
    "DOGE",
    "BNB",
    "XRP",
    "ADA",
    "TON",
    "TRX",
    "AVAX",
]

_ALIASES_BY_LOWER = {alias.lower(): symbol for alias, symbol in COIN_ALIASES.items()}
_ALIAS_PATTERN = re.compile(
    "|".join(
        sorted(
            (
                rf"(?<![A-Za-z]){re.escape(alias)}(?![A-Za-z])"
                if re.fullmatch(r"[A-Za-z ]+", alias)
                else re.escape(alias)
                for alias in COIN_ALIASES
            ),
            key=len,
            reverse=True,
        )
    ),
    flags=re.IGNORECASE,
)
_SUPPORTED_COINS_SET = set(SUPPORTED_COINS)


def _surround_symbol_with_spaces(text: str, symbol: str) -> str:
    text = re.sub(
        rf"(?<=[0-9A-Za-z\u4e00-\u9fff]){re.escape(symbol)}",
        f" {symbol}",
        text,
    )
    text = re.sub(
        rf"{re.escape(symbol)}(?=[0-9A-Za-z\u4e00-\u9fff])",
        f"{symbol} ",
        text,
    )
    return text


def normalize_coin_alias(text: str) -> str:
    """Normalize coin aliases to their standard symbols while preserving text."""

    original_text = str(text or "")

    def _replace(match: re.Match[str]) -> str:
        alias = match.group(0).lower()
        return _ALIASES_BY_LOWER.get(alias, match.group(0))

    normalized = _ALIAS_PATTERN.sub(_replace, original_text)

    for symbol in SUPPORTED_COINS:
        normalized = _surround_symbol_with_spaces(normalized, symbol)

    normalized = re.sub(r"\s+", " ", normalized).strip()
    print(f"[Alias] normalized original={original_text} normalized={normalized}")
    return normalized


def is_supported_coin(symbol: str) -> bool:
    """Return True when the symbol is one of the supported coins."""

    return str(symbol or "").strip().upper() in _SUPPORTED_COINS_SET
