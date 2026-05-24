from config import GEMINI_API_KEY


def get_gemini_client():
    """建立 Google Gemini client；缺少 API key 時回傳 None。"""

    if not GEMINI_API_KEY:
        print("[Gemini] 找不到 GEMINI_API_KEY，請先在 .env 或 Render 環境變數設定 Gemini API key。")
        return None

    try:
        from google import genai
    except ImportError as error:
        print(f"[Gemini] google-genai 套件尚未安裝：{error}")
        return None

    return genai.Client(api_key=GEMINI_API_KEY)
