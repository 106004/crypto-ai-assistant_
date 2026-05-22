import requests


# CoinGecko API 是一個提供加密貨幣市場資料的免費 API。
# 我們這裡先用它的 simple price endpoint 取得幣價和 24 小時漲跌。
COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"


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
    except requests.RequestException as error:
        print(f"查詢 CoinGecko API 失敗，可能是網路或 API 暫時有問題：{error}")
        return None
    except ValueError as error:
        print(f"CoinGecko API 回傳的內容不是合法 JSON：{error}")
        return None

    # CoinGecko 回傳格式大概會像：
    # {"bitcoin": {"usd": 105000, "usd_24h_change": 2.3}}
    coin_data = data.get(coin["id"])
    if not coin_data:
        print(f"CoinGecko 沒有回傳 {coin['id']} 的市場資料。")
        return None

    price_usd = coin_data.get("usd")
    change_24h = coin_data.get("usd_24h_change")

    # 如果少了必要欄位，就不要硬組結果，避免給使用者錯誤資訊。
    if price_usd is None or change_24h is None:
        print(f"CoinGecko 回傳資料不完整，缺少價格或 24 小時漲跌：{coin_data}")
        return None

    # 回傳整理好的資料，讓 line_bot.py 可以專心負責排版和回覆。
    return {
        "name": coin["name"],
        "symbol": coin["symbol"],
        "price_usd": price_usd,
        "change_24h": change_24h,
    }
