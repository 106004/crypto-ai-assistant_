import time

import requests


# CoinGecko API 是一個提供加密貨幣市場資料的免費 API。
# 我們這裡先用它的 simple price endpoint 取得幣價和 24 小時漲跌。
COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"

# Binance Spot API 也有免費公開的市場資料 endpoint。
# 這裡把它當作「備用 API」：
# 1. 平常先查 CoinGecko，維持原本功能。
# 2. 如果 CoinGecko 暫時失敗、限流或資料不完整，再改查 Binance。
# 3. Binance 的 /api/v3/ticker/24hr 可以拿到 lastPrice 和 priceChangePercent，
#    剛好能組成原本 line_bot.py 需要的價格和 24 小時漲跌資料。
BINANCE_TICKER_24HR_URL = "https://api.binance.com/api/v3/ticker/24hr"


# 使用者通常會輸入 btc、eth 這種交易所常見代號。
# 但 CoinGecko API 需要的是 coin id，例如 bitcoin、ethereum。
# 所以這裡建立一張轉換表，讓使用者可以用簡短代號查詢。
SUPPORTED_COINS = {
    "btc": {"id": "bitcoin", "name": "Bitcoin", "symbol": "BTC", "binance_symbol": "BTCUSDT"},
    "eth": {"id": "ethereum", "name": "Ethereum", "symbol": "ETH", "binance_symbol": "ETHUSDT"},
    "sol": {"id": "solana", "name": "Solana", "symbol": "SOL", "binance_symbol": "SOLUSDT"},
    "bnb": {"id": "binancecoin", "name": "BNB", "symbol": "BNB", "binance_symbol": "BNBUSDT"},
    "xrp": {"id": "ripple", "name": "XRP", "symbol": "XRP", "binance_symbol": "XRPUSDT"},
    "doge": {"id": "dogecoin", "name": "Dogecoin", "symbol": "DOGE", "binance_symbol": "DOGEUSDT"},
    "ada": {"id": "cardano", "name": "Cardano", "symbol": "ADA", "binance_symbol": "ADAUSDT"},
    "ton": {"id": "the-open-network", "name": "Toncoin", "symbol": "TON", "binance_symbol": "TONUSDT"},
    "trx": {"id": "tron", "name": "TRON", "symbol": "TRX", "binance_symbol": "TRXUSDT"},
    "avax": {"id": "avalanche-2", "name": "Avalanche", "symbol": "AVAX", "binance_symbol": "AVAXUSDT"},
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


def _build_price_result(coin, price_usd, change_24h):
    """把不同 API 回傳的資料整理成同一種格式，避免其他檔案需要改。"""

    return {
        "name": coin["name"],
        "symbol": coin["symbol"],
        "price_usd": price_usd,
        "change_24h": change_24h,
    }


def _save_price_cache(normalized_symbol, result, timestamp):
    """把成功查到的幣價寫進 cache；錯誤提示文字不寫入 cache。"""

    if result is None or isinstance(result, str):
        return

    price_cache[normalized_symbol] = {
        "data": result,
        "timestamp": timestamp,
    }


def _get_coin_price_from_binance(coin):
    """使用 Binance 免費公開 API 當作備用來源查詢幣價。"""

    print("改用備用 Binance API 查詢：")
    print(coin["symbol"])

    # Binance 查幣價時使用交易對 symbol。
    # 例如 BTC 的美元穩定幣交易對是 BTCUSDT，
    # 這裡用 USDT 價格近似 USD 價格，對一般查價機器人已經足夠。
    params = {
        "symbol": coin["binance_symbol"],
    }

    try:
        response = requests.get(BINANCE_TICKER_24HR_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.HTTPError as error:
        if error.response is not None and error.response.status_code == 429:
            return "目前查詢人數較多，\n請稍後再試。"

        print(f"查詢 Binance 備用 API 失敗：{error}")
        return None
    except requests.RequestException as error:
        print(f"查詢 Binance 備用 API 失敗，可能是網路或 API 暫時有問題：{error}")
        return None
    except ValueError as error:
        print(f"Binance 備用 API 回傳的內容不是合法 JSON：{error}")
        return None

    # Binance /api/v3/ticker/24hr 回傳格式大概會像：
    # {"symbol": "BTCUSDT", "lastPrice": "105000.00", "priceChangePercent": "2.3"}
    price_usd = data.get("lastPrice")
    change_24h = data.get("priceChangePercent")

    if price_usd is None or change_24h is None:
        print(f"Binance 備用 API 回傳資料不完整，缺少價格或 24 小時漲跌：{data}")
        return None

    return _build_price_result(coin, price_usd, change_24h)


def get_coin_price(symbol):
    """使用 CoinGecko 免費 API 查詢指定幣種的美元價格。"""

    # symbol 是使用者輸入的幣種代號，例如 btc、eth、sol。
    # 先轉成小寫並去掉前後空白，讓 BTC、 btc 這類輸入也能正常查。
    normalized_symbol = str(symbol).strip().lower()

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
        print("使用快取資料：")
        print(coin["symbol"])
        return cached_price["data"]

    print("重新查詢 CoinGecko API：")
    print(coin["symbol"])

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

        # 如果 CoinGecko 回傳 4xx 或 5xx，這行會丟出例外。
        # 我們在 except 裡用白話印出錯誤，不讓程式崩潰。
        response.raise_for_status()

        # 把 API 回傳的 JSON 轉成 Python dict。
        data = response.json()
    except requests.HTTPError as error:
        # 429 Too Many Requests 代表短時間內查太多次，被 CoinGecko 限流。
        # 這不是程式壞掉，而是免費 API 為了保護服務穩定性做的限制。
        # 所以這裡回傳友善文字，讓呼叫端可以直接提示使用者稍後再試。
        if error.response is not None and error.response.status_code == 429:
            print("CoinGecko API 目前限流，改查備用 API。")
            backup_result = _get_coin_price_from_binance(coin)
            if backup_result is not None:
                _save_price_cache(normalized_symbol, backup_result, now)
                return backup_result

            return "目前查詢人數較多，\n請稍後再試。"

        print(f"查詢 CoinGecko API 失敗，可能是網路或 API 暫時有問題：{error}")
        backup_result = _get_coin_price_from_binance(coin)
        _save_price_cache(normalized_symbol, backup_result, now)
        return backup_result
    except requests.RequestException as error:
        print(f"查詢 CoinGecko API 失敗，可能是網路或 API 暫時有問題：{error}")
        backup_result = _get_coin_price_from_binance(coin)
        _save_price_cache(normalized_symbol, backup_result, now)
        return backup_result
    except ValueError as error:
        print(f"CoinGecko API 回傳的內容不是合法 JSON：{error}")
        backup_result = _get_coin_price_from_binance(coin)
        _save_price_cache(normalized_symbol, backup_result, now)
        return backup_result

    # CoinGecko 回傳格式大概會像：
    # {"bitcoin": {"usd": 105000, "usd_24h_change": 2.3}}
    coin_data = data.get(coin["id"])
    if not coin_data:
        print(f"CoinGecko 沒有回傳 {coin['id']} 的市場資料。")
        backup_result = _get_coin_price_from_binance(coin)
        _save_price_cache(normalized_symbol, backup_result, now)
        return backup_result

    price_usd = coin_data.get("usd")
    change_24h = coin_data.get("usd_24h_change")

    # 如果少了必要欄位，就不要硬組結果，避免給使用者錯誤資訊。
    if price_usd is None or change_24h is None:
        print(f"CoinGecko 回傳資料不完整，缺少價格或 24 小時漲跌：{coin_data}")
        backup_result = _get_coin_price_from_binance(coin)
        _save_price_cache(normalized_symbol, backup_result, now)
        return backup_result

    # 回傳整理好的資料，讓 line_bot.py 可以專心負責排版和回覆。
    result = _build_price_result(coin, price_usd, change_24h)

    # API 查詢成功後，把結果放進 cache。
    # 下一次同一個幣種在 60 秒內被查詢時，就可以直接回傳這份 result。
    _save_price_cache(normalized_symbol, result, now)

    return result
