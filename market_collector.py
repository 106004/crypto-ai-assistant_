import json
from datetime import datetime
from pathlib import Path

import requests


COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
MARKET_DATA_FILE = Path(__file__).resolve().parent / "data" / "market_data.json"

# 這裡是 LINE Bot 目前支援的 10 種幣。
# key 是使用者會輸入的代號，id 是 CoinGecko simple price API 要用的 coin id。
TRACKED_COINS = {
    "btc": {"id": "bitcoin", "name": "Bitcoin", "symbol": "BTC"},
    "eth": {"id": "ethereum", "name": "Ethereum", "symbol": "ETH"},
    "sol": {"id": "solana", "name": "Solana", "symbol": "SOL"},
    "bnb": {"id": "binancecoin", "name": "BNB", "symbol": "BNB"},
    "xrp": {"id": "ripple", "name": "XRP", "symbol": "XRP"},
    "doge": {"id": "dogecoin", "name": "Dogecoin", "symbol": "DOGE"},
    "ada": {"id": "cardano", "name": "Cardano", "symbol": "ADA"},
    "ton": {"id": "the-open-network", "name": "Toncoin", "symbol": "TON"},
    "trx": {"id": "tron", "name": "TRON", "symbol": "TRX"},
    "avax": {"id": "avalanche-2", "name": "Avalanche", "symbol": "AVAX"},
}


def save_market_data(data):
    """把整理好的市場資料寫入 data/market_data.json。"""

    try:
        MARKET_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with MARKET_DATA_FILE.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        print(f"[MarketCollector] 已寫入 {MARKET_DATA_FILE}")
    except OSError as error:
        print(f"[MarketCollector] 寫入 market_data.json 失敗：{error}")


def load_market_data():
    """讀取 data/market_data.json；如果檔案不存在、空檔或格式壞掉，就回傳空 dict。"""

    if not MARKET_DATA_FILE.exists():
        return {}

    try:
        if MARKET_DATA_FILE.stat().st_size == 0:
            return {}

        with MARKET_DATA_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"[MarketCollector] 讀取 market_data.json 失敗：{error}")
        return {}


def collect_market_data():
    """用 CoinGecko batch request 收集 10 種幣，並存進 data/market_data.json。"""

    print("[MarketCollector] 開始收集市場資料")

    # 使用 batch request，是因為 CoinGecko simple price API 可以用逗號一次查多個 id。
    # 10 種幣如果打 10 次 API，會讓 collector 變慢，也更容易碰到 API rate limit。
    # 先定時收集資料，再讓 LINE Bot 讀本地檔案，可以讓使用者查價更快，
    # 也避免每一則 LINE 訊息都直接打外部 API。
    params = {
        "ids": ",".join(coin["id"] for coin in TRACKED_COINS.values()),
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }

    try:
        response = requests.get(COINGECKO_PRICE_URL, params=params, timeout=10)
        response.raise_for_status()
        api_data = response.json()
    except requests.RequestException as error:
        print("[MarketCollector] CoinGecko API 暫時失敗，改用既有本地資料")
        print(f"[MarketCollector] 錯誤：{error}")
        return load_market_data()
    except ValueError as error:
        print("[MarketCollector] CoinGecko 回傳不是合法 JSON，改用既有本地資料")
        print(f"[MarketCollector] 錯誤：{error}")
        return load_market_data()

    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    market_data = {}

    for key, coin in TRACKED_COINS.items():
        coin_data = api_data.get(coin["id"], {})
        price_usd = coin_data.get("usd")
        change_24h = coin_data.get("usd_24h_change")

        if price_usd is None or change_24h is None:
            print(f"[MarketCollector] {coin['symbol']} 資料不完整，略過")
            continue

        market_data[key] = {
            "name": coin["name"],
            "symbol": coin["symbol"],
            "price_usd": price_usd,
            "change_24h": change_24h,
            "updated_at": updated_at,
        }

        print(f"[MarketCollector] 已收集 {coin['symbol']}")

    if market_data:
        save_market_data(market_data)
    else:
        print("[MarketCollector] 沒有可寫入的市場資料，保留既有本地資料")
        return load_market_data()

    return market_data


# collect_market_data() 放在檔案最外層，scheduler.py 才能 import 後定時呼叫。
# 下面這段只保留給開發者手動執行 python market_collector.py 測試用。
if __name__ == "__main__":
    collect_market_data()
