import json
import time
from datetime import datetime
from pathlib import Path

import requests


# CoinGecko API 是一個提供加密貨幣市場資料的免費 API。
# 我們這裡先用它的 simple price endpoint 取得幣價和 24 小時漲跌。
COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"

# CoinCap API 也有免費公開的市場資料 endpoint。
# 這裡把它當作「備用 API」：
# 1. 平常先查 CoinGecko，維持原本功能。
# 2. 如果 CoinGecko 暫時失敗、限流或資料不完整，再改查 CoinCap。
# 3. CoinCap 的 /v2/assets/{id} 可以拿到 priceUsd 和 changePercent24Hr，
#    剛好能組成原本 line_bot.py 需要的價格和 24 小時漲跌資料。
COINCAP_ASSET_URL = "https://api.coincap.io/v2/assets/{asset_id}"
BACKUP_API_NAME = "CoinCap"
LOCAL_MARKET_DATA_FILE = Path(__file__).resolve().parent / "data" / "market_data.json"
ALL_MARKET_DATA_BUSY_MESSAGE = "目前所有市場資料來源都忙碌中，\n請稍後再試。"


# 使用者通常會輸入 btc、eth 這種交易所常見代號。
# 但 CoinGecko API 需要的是 coin id，例如 bitcoin、ethereum。
# 所以這裡建立一張轉換表，讓使用者可以用簡短代號查詢。
SUPPORTED_COINS = {
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


# CoinCap 的 asset id 和使用者輸入的代號不一定完全一樣。
# 例如使用者輸入 btc，但 CoinCap URL 要用 bitcoin。
# 先用明確表格管理轉換，debug 時也比較容易檢查是否打到正確 endpoint。
def get_coin_from_local_data(symbol):
    """先從 data/market_data.json 讀幣價；讀不到或檔案壞掉時回傳 None。"""

    # 優先讀本地資料，是為了讓 LINE 使用者查常用幣種時可以很快拿到
    # market_collector.py 事先整理好的結果，不必每一則訊息都等外部 API 回應。
    # 不要每次都打外部 API，因為 CoinGecko/CoinCap 可能限流、變慢或短暫失敗；
    # 本地檔案可降低 API 壓力，也能讓 Bot 在外部服務不穩時仍有資料可回。
    # market_data.json 是 collector 寫到硬碟的共享市場資料，重開程式還在；
    # price_cache 則是 get_coin_price() 裡的記憶體快取，只活在目前這個 Python 程序。
    normalized_symbol = str(symbol).strip().lower()

    try:
        from database_manager import get_market_data_by_symbol

        db_coin_data = get_market_data_by_symbol(normalized_symbol)
        if isinstance(db_coin_data, dict):
            result = dict(db_coin_data)
            result["source"] = "本地 market_data.json"
            return result
    except Exception as error:
        print(f"[Supabase] 查詢 market_data 失敗，改讀 data/market_data.json：{error}")

    print("[LocalData] 嘗試讀取 data/market_data.json")
    print(f"[LocalData] 檔案是否存在：{LOCAL_MARKET_DATA_FILE.exists()}")

    if not LOCAL_MARKET_DATA_FILE.exists():
        print("[LocalData] 找不到 market_data.json，所以改用即時 API。")
        print("[LocalData] 目前 JSON keys：[]")
        print(f"[LocalData] 使用者查詢 symbol：{normalized_symbol}")
        print("[LocalData] 是否找到資料：False")
        return None

    try:
        with LOCAL_MARKET_DATA_FILE.open("r", encoding="utf-8") as file:
            market_data = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"[LocalData] 讀取 market_data.json 失敗：{error}")
        print("[LocalData] 目前 JSON keys：[]")
        print(f"[LocalData] 使用者查詢 symbol：{normalized_symbol}")
        print("[LocalData] 是否找到資料：False")
        return None

    if not isinstance(market_data, dict):
        print("[LocalData] market_data.json 不是物件格式")
        print("[LocalData] 目前 JSON keys：[]")
        print(f"[LocalData] 使用者查詢 symbol：{normalized_symbol}")
        print("[LocalData] 是否找到資料：False")
        return None

    print(f"[LocalData] 目前 JSON keys：{list(market_data.keys())}")
    print(f"[LocalData] 使用者查詢 symbol：{normalized_symbol}")

    coin_data = market_data.get(normalized_symbol)
    if not isinstance(coin_data, dict):
        print("[LocalData] 是否找到資料：False")
        return None

    required_fields = ("name", "symbol", "price_usd", "change_24h", "updated_at")
    if any(field not in coin_data for field in required_fields):
        print("[LocalData] 是否找到資料：False")
        return None

    print("[LocalData] 是否找到資料：True")
    result = dict(coin_data)
    result["source"] = "本地 market_data.json"
    return result


COINCAP_ASSET_IDS = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
}


# price_cache 是一個很簡單的記憶體快取。
# 白話來說，就是程式先把剛查到的幣價暫存在這個 dict 裡。
# 如果短時間內又有人查同一個幣種，就可以直接拿剛剛查過的結果，
# 不需要每次都真的打到 CoinGecko API。
#
# 免費 API 通常都會有限流，因為服務商的伺服器、資料庫、頻寬都有成本。
# 如果每個使用者、每個機器人都無限制一直查詢，免費服務很快就會被打爆，
# 所以 CoinGecko 這類 API 會用 429 Too Many Requests 來提醒我們「查太多次了」。
#
# 大型 AI 系統也很依賴 cache。
# 原因很直接：AI 回答、API 查詢、資料庫查詢通常都很花時間也很花錢。
# 把短時間內重複使用的結果快取起來，可以降低成本、減少等待時間，
# 也能避免外部 API 被重複請求壓垮。
#
# 格式範例：
# {
#     "btc": {
#         "data": {...},
#         "timestamp": 1710000000
#     }
# }
price_cache = {}


def _build_price_result(source, coin, price_usd, change_24h):
    """把不同 API 回傳的資料整理成同一種格式，避免其他檔案需要改。"""

    return {
        "source": source,
        "name": coin["name"],
        "symbol": coin["symbol"],
        "price_usd": price_usd,
        "change_24h": change_24h,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _print_final_source(source):
    """集中印出最後資料來源，方便 debug 時一眼看懂這次查詢結果。"""

    print(f"[CryptoAPI] 最終資料來源：{source}")


def _save_price_cache(normalized_symbol, result, timestamp):
    """把成功查到的幣價寫進 cache；錯誤提示文字不寫入 cache。"""

    if result is None or isinstance(result, str):
        return

    price_cache[normalized_symbol] = {
        "data": result,
        "timestamp": timestamp,
    }


def _get_coin_price_from_coingecko(coin):
    """使用 CoinGecko 主 API 查詢幣價；失敗時回傳 None，讓外層切換備用 API。"""

    print("[CryptoAPI] 嘗試主 API：CoinGecko")

    # CoinGecko simple price API 的參數。
    # ids 使用 CoinGecko 的 coin id。
    # vs_currencies=usd 代表查美元價格。
    # include_24hr_change=true 代表順便取得 24 小時漲跌百分比。
    params = {
        "ids": coin["id"],
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }

    try:
        # 對 CoinGecko 發出 HTTP GET request。
        # timeout=10 是為了避免外部 API 卡住時，整個 webhook 也跟著卡太久。
        response = requests.get(COINGECKO_PRICE_URL, params=params, timeout=10)
        print(f"[CryptoAPI] CoinGecko 狀態碼：{response.status_code}")
        if response.status_code == 429:
            print("[CryptoAPI] CoinGecko 限流")

        # 如果 CoinGecko 回傳 4xx 或 5xx，這行會丟出例外。
        # 429 Too Many Requests 代表主 API 限流；外層一定會切換備用 API。
        response.raise_for_status()

        # 把 API 回傳的 JSON 轉成 Python dict。
        data = response.json()
    except requests.HTTPError as error:
        print(f"[CryptoAPI] CoinGecko 失敗原因：HTTP 錯誤：{error}")
        return None
    except requests.RequestException as error:
        print("[CryptoAPI] CoinGecko 狀態碼：無回應")
        print(f"[CryptoAPI] CoinGecko 失敗原因：網路或 API 暫時有問題：{error}")
        return None
    except ValueError as error:
        print("[CryptoAPI] CoinGecko 失敗原因：回傳內容不是合法 JSON")
        print(f"[CryptoAPI] CoinGecko JSON 錯誤：{error}")
        return None

    # CoinGecko 回傳格式大概會像：
    # {"bitcoin": {"usd": 105000, "usd_24h_change": 2.3}}
    coin_data = data.get(coin["id"])
    if not coin_data:
        print(f"[CryptoAPI] CoinGecko 失敗原因：沒有回傳 {coin['id']} 的市場資料")
        return None

    price_usd = coin_data.get("usd")
    change_24h = coin_data.get("usd_24h_change")

    # 如果少了必要欄位，就不要硬組結果，避免給使用者錯誤資訊。
    if price_usd is None or change_24h is None:
        print(f"[CryptoAPI] CoinGecko 失敗原因：資料不完整，缺少價格或 24 小時漲跌：{coin_data}")
        return None

    return _build_price_result("CoinGecko", coin, price_usd, change_24h)


def _get_coin_price_from_coincap(normalized_symbol):
    """使用 CoinCap 免費公開 API 當作備用來源查詢幣價。"""

    print("[CryptoAPI] 切換 CoinCap API")

    asset_id = COINCAP_ASSET_IDS.get(normalized_symbol)
    if asset_id is None:
        print(f"[CryptoAPI] CoinCap API 失敗：沒有 {normalized_symbol.upper()} 的 CoinCap asset id 對照")
        return None

    print(f"[CryptoAPI] CoinCap symbol 對照：{normalized_symbol} -> {asset_id}")
    url = COINCAP_ASSET_URL.format(asset_id=asset_id)

    try:
        response = requests.get(url, timeout=10)
        print(f"[CryptoAPI] CoinCap 狀態碼：{response.status_code}")
        response.raise_for_status()
        payload = response.json()
    except requests.HTTPError as error:
        print(f"[CryptoAPI] CoinCap API 失敗：HTTP 錯誤：{error}")
        return None
    except requests.RequestException as error:
        print("[CryptoAPI] CoinCap 狀態碼：無回應")
        print(f"[CryptoAPI] CoinCap API 失敗：網路或 API 暫時有問題：{error}")
        return None
    except ValueError as error:
        print(f"[CryptoAPI] CoinCap API 失敗：回傳內容不是合法 JSON：{error}")
        return None

    # CoinCap /v2/assets/{id} 回傳格式大概會像：
    # {"data": {"id": "bitcoin", "name": "Bitcoin", "symbol": "BTC",
    #           "priceUsd": "105000.00", "changePercent24Hr": "2.3"}}
    data = payload.get("data", {})
    price_usd = data.get("priceUsd")
    change_24h = data.get("changePercent24Hr")

    if price_usd is None or change_24h is None:
        print(f"[CryptoAPI] CoinCap API 失敗：資料不完整，缺少價格或 24 小時漲跌：{payload}")
        return None

    print("[CryptoAPI] CoinCap API 成功")
    return {
        "source": BACKUP_API_NAME,
        "name": data.get("name", asset_id.title()),
        "symbol": data.get("symbol", normalized_symbol.upper()),
        "price_usd": price_usd,
        "change_24h": change_24h,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_coin_price(symbol):
    """使用 CoinGecko 免費 API 查詢指定幣種的美元價格。"""

    # symbol 是使用者輸入的幣種代號，例如 btc、eth、sol。
    # 先轉成小寫並去掉前後空白，讓 BTC、 btc 這類輸入也能正常查。
    normalized_symbol = str(symbol).strip().lower()
    print(f"[CryptoAPI] 使用者查詢：{normalized_symbol.upper()}")

    # 檢查這個幣種是否在我們支援的清單裡。
    # 如果不支援，就回傳 None，讓呼叫端決定要怎麼提示使用者。
    coin = SUPPORTED_COINS.get(normalized_symbol)
    if coin is None:
        print(f"目前不支援這個幣種：{symbol}")
        return None

    now = time.time()
    cached_price = price_cache.get(normalized_symbol)

    # cache 的用途是擋掉「短時間內重複查同一筆資料」。
    # 幣價每秒都可能變動，但對一般 LINE Bot 查詢來說，
    # 60 秒內重複使用同一筆資料通常已經足夠，也能大幅減少 API 呼叫次數。
    if cached_price and now - cached_price["timestamp"] < 60:
        source = cached_price["data"].get("source", "未知")
        print(f"[CryptoAPI] 使用快取資料：{coin['symbol']}")
        print(f"[CryptoAPI] 快取資料來源：{source}")
        _print_final_source("cache")
        return cached_price["data"]

    result = _get_coin_price_from_coingecko(coin)
    if result is not None:
        _save_price_cache(normalized_symbol, result, now)
        _print_final_source("CoinGecko")
        return result

    backup_result = _get_coin_price_from_coincap(normalized_symbol)
    if backup_result is not None:
        _save_price_cache(normalized_symbol, backup_result, now)
        _print_final_source(BACKUP_API_NAME)
        return backup_result

    print("[CryptoAPI] 備用 API 失敗")
    _print_final_source("全部失敗")
    return ALL_MARKET_DATA_BUSY_MESSAGE
