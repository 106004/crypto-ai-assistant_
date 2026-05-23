from apscheduler.schedulers.background import BackgroundScheduler

from crypto_api import get_coin_from_local_data, get_coin_from_supabase, get_coin_price
from line_bot import DAILY_MANUAL_TEXT, push_message
from market_collector import collect_market_data
from user_manager import get_all_users


# scheduler 是「背景排程器」。
# 白話來說，就是 Flask server 還在跑的時候，它會在旁邊看時間，
# 時間到了就自動執行指定的函式。
#
# 這裡有兩種推播：
# 1. 每日提醒：每天早上 9:00 傳一次使用說明，提醒使用者有哪些指令可以用。
# 2. 每小時幣價：每小時檢查一次使用者最愛幣種，推播該幣種的最新價格。
# 3. 市場資料更新：每 5 分鐘更新 data/market_data.json，讓 LINE Bot 查價時讀本地檔案。
#
# 注意：APScheduler 在本機測試很好用，因為你的電腦和 Flask server 通常會一直開著。
# 但 Render 免費版沒流量時會 sleep，服務睡著後背景 scheduler 也不會準時跑。
# 所以正式雲端環境要更新市場資料時，建議用外部 cron 服務每 5 分鐘呼叫
# app.py 的 /update-market-data endpoint，讓外部服務負責準時觸發更新。
_scheduler = None


def _format_hourly_coin_price_message(coin_data):
    """把幣價資料整理成每小時推播訊息。"""

    change_24h = float(coin_data["change_24h"])
    change_text = f"{change_24h:+.2f}%"
    price_text = f"{float(coin_data['price_usd']):,.2f}"
    source = coin_data.get("source", "即時 API")
    if source not in ("Supabase", "本地 market_data.json"):
        source = "即時 API"

    return (
        f"Crypto AI Assistant 每小時幣價提醒\n\n"
        f"你設定的最愛幣種：{coin_data['symbol']}\n"
        f"{coin_data['name']} 目前價格：{price_text} USD\n"
        f"24H 漲跌：{change_text}\n\n"
        f"資料來源：{source}"
    )


def _get_favorite_coin_price(symbol):
    """Use the same market data priority as LINE price lookup."""

    coin_data = get_coin_from_supabase(symbol)
    if coin_data is not None:
        return coin_data

    coin_data = get_coin_from_local_data(symbol)
    if coin_data is not None:
        return coin_data

    return get_coin_price(symbol)


def send_daily_manual_to_all_users():
    """讀取所有使用者，並用 LINE Push API 推播每日提醒。"""

    users = get_all_users()

    if not users:
        print("目前 users.json 沒有使用者，所以每日提醒沒有推播對象。")
        return

    print(f"開始推播每日提醒，使用者數量：{len(users)}")

    for user in users:
        user_id = user.get("user_id")
        if not user_id:
            print("發現一筆沒有 user_id 的資料，略過這筆。")
            continue

        push_message(user_id, DAILY_MANUAL_TEXT)


def send_hourly_favorite_coin_price():
    """每小時推播使用者最愛幣種的價格。"""

    users = get_all_users()

    if not users:
        print("目前 users.json 沒有使用者，所以每小時幣價沒有推播對象。")
        return

    print(f"開始執行每小時最愛幣種價格推播，使用者數量：{len(users)}")

    for user in users:
        user_id = user.get("user_id")
        favorite_coin = str(user.get("favorite_coin", "")).strip().lower()

        if not user_id:
            print("發現一筆沒有 user_id 的資料，略過這筆。")
            continue

        # 使用者還沒有設定最愛幣種時，不推播價格，避免打擾使用者。
        if not favorite_coin:
            print(f"{user_id} 尚未設定 favorite_coin，略過每小時幣價推播。")
            continue

        try:
            coin_data = _get_favorite_coin_price(favorite_coin)
        except Exception as error:
            # scheduler 不能因為單次 CoinGecko 失敗就整個停止。
            # 所以這裡只記錄錯誤，然後繼續處理下一位使用者。
            print(f"查詢 {user_id} 的 {favorite_coin.upper()} 價格時發生錯誤，已略過：{error}")
            continue

        if coin_data is None:
            print(f"CoinGecko 暫時查不到 {favorite_coin.upper()} 價格，已略過 {user_id}。")
            continue

        if isinstance(coin_data, str):
            print(f"CoinGecko 暫時限流，已略過 {user_id}：{coin_data}")
            continue

        message = _format_hourly_coin_price_message(coin_data)
        push_message(user_id, message)


def update_market_data_job():
    """排程用：定時更新 data/market_data.json。"""

    # 幣價會一直變，但 LINE Bot 不需要每次查詢都即時打外部 API。
    # 每 5 分鐘更新一次，對一般提醒和查詢已經夠新，也能降低 CoinGecko 限流風險。
    print("[Scheduler] 開始更新 market_data.json")

    try:
        collect_market_data()
    except Exception as error:
        # 單次更新失敗不能讓整個 scheduler 停掉；先記錄錯誤，下一輪 5 分鐘後會再試。
        print(f"[Scheduler] market_data.json 更新失敗：{error}")
        return

    print("[Scheduler] market_data.json 更新完成")


def test_daily_manual():
    """測試用：手動執行每日提醒，不用等到早上 9:00。"""

    send_daily_manual_to_all_users()


def test_hourly_favorite_coin_price():
    """測試用：手動執行每小時幣價推播，不用真的等一小時。"""

    send_hourly_favorite_coin_price()


def start_scheduler():
    """啟動每日 9:00 提醒、每小時最愛幣種推播，以及每 5 分鐘市場資料更新。"""

    global _scheduler

    # 避免 Flask debug reloader 或重複 import 時，排程被啟動兩次。
    if _scheduler and _scheduler.running:
        print("scheduler 已經在執行中，不需要重複啟動。")
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="Asia/Taipei")

    # 每日提醒：固定每天早上 9:00 執行一次。
    _scheduler.add_job(
        send_daily_manual_to_all_users,
        trigger="cron",
        hour=9,
        minute=0,
        id="daily_manual_9am",
        replace_existing=True,
    )

    # 每小時幣價：每 1 小時執行一次，推播使用者 favorite_coin 的最新價格。
    _scheduler.add_job(
        send_hourly_favorite_coin_price,
        trigger="interval",
        hours=1,
        id="hourly_favorite_coin_price",
        replace_existing=True,
    )

    # 市場資料更新：本機測試時可用 APScheduler 每 5 分鐘抓一次最新資料。
    # Render 免費版會 sleep，這個內建排程不保證準時；正式雲端更新應改由
    # 外部 cron 服務呼叫 /update-market-data，比較能穩定地喚醒服務並觸發更新。
    # LINE Bot 應該優先讀這份資料，因為快取資料回應快、穩定，也能減少外部 API 壓力。
    print("[Scheduler] 啟動市場資料更新排程：每 5 分鐘")
    _scheduler.add_job(
        update_market_data_job,
        trigger="interval",
        minutes=5,
        id="market_data_update_5min",
        replace_existing=True,
    )

    _scheduler.start()

    print("scheduler 已啟動：每天早上 9:00 推播每日提醒、每小時推播最愛幣種價格，並且每 5 分鐘更新市場資料。")
    return _scheduler
