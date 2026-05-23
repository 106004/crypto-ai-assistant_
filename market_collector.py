import json
from datetime import datetime
from pathlib import Path

import requests


# market_collector.py 的角色：
# 這個檔案專門負責「收集市場資料」，也就是定時去外部 API 把 BTC、ETH、SOL
# 的最新價格抓回來，整理成我們自己的格式，再存到 market_data.json。
#
# 為什麼要多做一個 market_collector？
# 因為 LINE Bot 的主要工作是「回覆使用者訊息」，不適合把抓資料、整理資料、
# 寫檔案這些背景工作全部塞在 line_bot.py 裡。分開之後，程式比較好維護：
# - market_collector.py：負責跟 CoinGecko 溝通，更新本地市場資料
# - line_bot.py：負責接收 LINE 訊息，讀取資料，回覆使用者
#
# 為什麼不要每次使用者問價格時都直接打 API？
# 如果每次 LINE 使用者傳訊息都直接呼叫 CoinGecko，會有幾個問題：
# 1. API 可能被打太頻繁，容易遇到流量限制或暫時失敗。
# 2. 外部 API 變慢時，LINE Bot 回覆也會跟著變慢。
# 3. 如果很多人同時查詢，同一份價格資料會被重複抓很多次，浪費 API 額度。
#
# market_data.json 的用途：
# market_data.json 是一份「本地快取資料」。collector 先把市場資料存進這個檔案，
# 之後 line_bot 只要讀這份檔案就可以快速回覆使用者，不需要每次都等待外部 API。
# 這種做法可以讓 LINE Bot 更穩、更快，也比較不容易因為 API 暫時失敗而整個不能用。
#
# collector 與 line_bot 的差別：
# collector 像是後台資料更新工人，定時把最新行情準備好。
# line_bot 像是前台客服，使用者問問題時，它只負責拿準備好的資料來回答。


COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
MARKET_DATA_FILE = Path(__file__).resolve().parent / "market_data.json"

# 這裡只收集需求指定的三個幣種。
# key 是我們系統內部使用的簡短代號，id 是 CoinGecko API 使用的幣種 ID。
TRACKED_COINS = {
    "btc": {"id": "bitcoin", "name": "Bitcoin", "symbol": "BTC"},
    "eth": {"id": "ethereum", "name": "Ethereum", "symbol": "ETH"},
    "sol": {"id": "solana", "name": "Solana", "symbol": "SOL"},
}


def save_market_data(data):
    """把整理好的市場資料寫入 market_data.json。"""

    try:
        # ensure_ascii=False 讓中文或其他文字未來寫入時不會變成跳脫字元。
        # indent=2 讓 json 檔案比較好讀，方便開發時檢查內容。
        with MARKET_DATA_FILE.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        print("[MarketCollector] 已寫入 market_data.json")
    except OSError as error:
        # 寫檔失敗時不要讓整個程式崩潰，因為 LINE Bot 或排程器還可能繼續運作。
        print(f"[MarketCollector] 寫入 market_data.json 失敗：{error}")


def load_market_data():
    """讀取 market_data.json；如果檔案不存在、空檔或格式壞掉，就回傳空 dict。"""

    if not MARKET_DATA_FILE.exists():
        return {}

    try:
        if MARKET_DATA_FILE.stat().st_size == 0:
            return {}

        with MARKET_DATA_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        # 讀不到或 JSON 壞掉時，回傳 {} 讓呼叫端可以自己決定怎麼處理。
        print(f"[MarketCollector] 讀取 market_data.json 失敗：{error}")
        return {}


def collect_market_data():
    """從 CoinGecko 收集 BTC、ETH、SOL 的市場資料，並存進 market_data.json。"""

    print("[MarketCollector] 開始收集市場資料")

    params = {
        "ids": ",".join(coin["id"] for coin in TRACKED_COINS.values()),
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }

    try:
        # timeout 可以避免 API 卡住太久，拖慢排程或主程式。
        response = requests.get(COINGECKO_PRICE_URL, params=params, timeout=10)
        response.raise_for_status()
        api_data = response.json()
    except requests.RequestException as error:
        print("[MarketCollector] CoinGecko API 暫時失敗")
        print(f"[MarketCollector] 錯誤原因：{error}")
        return load_market_data()
    except ValueError as error:
        print("[MarketCollector] CoinGecko 回傳資料格式暫時不正常")
        print(f"[MarketCollector] 錯誤原因：{error}")
        return load_market_data()

    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    market_data = {}

    for key, coin in TRACKED_COINS.items():
        coin_data = api_data.get(coin["id"], {})
        price_usd = coin_data.get("usd")
        change_24h = coin_data.get("usd_24h_change")

        if price_usd is None or change_24h is None:
            print(f"[MarketCollector] {coin['symbol']} 資料暫時不完整，先略過")
            continue

        market_data[key] = {
            "name": coin["name"],
            "symbol": coin["symbol"],
            "price_usd": price_usd,
            "change_24h": change_24h,
            "updated_at": updated_at,
        }

        print(f"[MarketCollector] 成功更新 {coin['symbol']}")

    if market_data:
        save_market_data(market_data)
    else:
        print("[MarketCollector] 這次沒有成功取得任何市場資料")

    return market_data


if __name__ == "__main__":
    collect_market_data()
