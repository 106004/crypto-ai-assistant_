import os

from flask import Flask, request

from line_bot import handle_webhook
from scheduler import start_scheduler


# 建立 Flask 應用程式；Render 和 gunicorn 會用 app:app 找到這個物件。
app = Flask(__name__)

_scheduler_started = False


def _start_scheduler_once():
    """啟動 scheduler，但避免 Flask debug reloader 重複啟動兩份背景排程。"""

    global _scheduler_started

    if _scheduler_started:
        print("[App] scheduler 已啟動過，略過重複啟動。")
        return

    # Flask debug reloader 會先開一個父程序，再開真正服務 request 的子程序。
    # 如果父程序也啟動 scheduler，就會變成兩份排程同時打 API、同時推播。
    is_flask_debug_parent = (
        os.environ.get("FLASK_DEBUG") == "1"
        and os.environ.get("WERKZEUG_RUN_MAIN") != "true"
    )
    if is_flask_debug_parent:
        print("[App] 偵測到 Flask debug reloader 父程序，先不啟動 scheduler。")
        return

    start_scheduler()
    _scheduler_started = True


# Flask 應用啟動時就啟動 scheduler，讓每日提醒、每小時推播和市場資料更新都會自動運作。
_start_scheduler_once()


@app.route("/")
def home():
    """健康檢查用首頁，確認 Flask server 正常啟動。"""

    return "Crypto AI Assistant is running"


@app.route("/callback", methods=["POST"])
def callback():
    """接收 LINE webhook POST request。"""

    # webhook 的處理邏輯維持交給 line_bot.py，避免破壞現有 LINE 功能。
    return handle_webhook(request)


if __name__ == "__main__":
    # 本機直接執行 python app.py 時才會跑這段；Render 正式部署會用 gunicorn 啟動 app。
    print("Crypto AI Assistant is running")

    # host 要設成 0.0.0.0，雲端平台才能從容器外部連進這個 Flask server。
    # 在 Render 上會有公開網址可以接 LINE webhook，所以雲端部署不需要 ngrok。
    # use_reloader=False 是為了避免本機 debug reloader 產生兩個程序，造成 scheduler 重複啟動。
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
