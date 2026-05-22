from flask import Flask, request

from line_bot import handle_webhook
from scheduler import start_scheduler


# 建立 Flask 應用程式；Render 和 gunicorn 會用 app:app 找到這個物件。
app = Flask(__name__)


# 啟動排程器；保留在這裡，避免影響既有的定時提醒功能。
start_scheduler()


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
    app.run(host="0.0.0.0", port=5000)
