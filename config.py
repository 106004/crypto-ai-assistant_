import os

from dotenv import load_dotenv


# 這行會讀取專案裡的 .env 檔案。
# 之後我們就可以用 os.getenv() 拿到裡面設定好的密鑰或帳號資料。
load_dotenv()


# LINE_CHANNEL_ACCESS_TOKEN 是 LINE Bot 用來呼叫 LINE 官方 API 的通行證。
# 實際值請放在 .env 裡，不要直接寫死在程式碼，這樣比較安全。
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")


# LINE_BOT_BASIC_ID 是 LINE Bot 的基本 ID。
# 這裡只負責從環境變數讀取，app.py 會拿它來測試設定是否讀取成功。
LINE_BOT_BASIC_ID = os.getenv("LINE_BOT_BASIC_ID")


# Supabase 是雲端資料庫服務。這個專案會用它保存 users 和 market_data，
# 讓 Render 重開機或重新部署後，資料不會只留在本機 JSON 檔裡。
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


# Gemini API key，用在 market_analyzer.py 產生 AI 市場分析。
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
