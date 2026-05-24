from gemini_client import get_gemini_client


GEMINI_MODEL = "gemini-2.0-flash"
AI_ANALYSIS_ERROR_MESSAGE = "⚠️ AI 市場分析服務暫時異常\n請稍後再試。"
INSUFFICIENT_DATA_MESSAGE = "目前資料不足，無法產生分析。"


def _build_market_analysis_prompt(coin_data):
    symbol = str(coin_data.get("symbol") or "").strip().upper()
    price_usd = coin_data.get("price_usd")
    change_24h = coin_data.get("change_24h")
    updated_at = coin_data.get("updated_at")

    return (
        "請根據以下加密貨幣市場資料產生市場分析。\n\n"
        f"symbol：{symbol}\n"
        f"價格：{price_usd}\n"
        f"24H 漲跌：{change_24h}\n"
        f"updated_at：{updated_at}\n\n"
        "請用繁體中文，\n"
        "以簡短、專業、白話的方式，\n"
        "分析目前市場狀態。\n\n"
        "不要超過 120 字。\n\n"
        "不要使用誇張語氣。\n"
        "不要提供投資保證。\n"
        "最後加一句：\n"
        "『這不是投資建議。』"
    )


def _extract_response_text(response):
    text = getattr(response, "text", "")
    return str(text).strip()


def analyze_market_data(coin_data):
    """使用 Gemini API 依據 market_data 產生 LINE 可直接發送的市場分析。"""

    if not isinstance(coin_data, dict):
        return INSUFFICIENT_DATA_MESSAGE

    change_24h = coin_data.get("change_24h")
    if change_24h is None:
        return INSUFFICIENT_DATA_MESSAGE

    symbol = str(coin_data.get("symbol") or "").strip().upper() or "UNKNOWN"

    print("[Gemini] 開始生成市場分析")
    prompt = _build_market_analysis_prompt(coin_data)
    print("[Gemini] Prompt 已建立")

    try:
        client = get_gemini_client()
        if client is None:
            raise RuntimeError("Gemini client 未建立，請確認 GEMINI_API_KEY 與 google-genai 套件。")

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        print("[Gemini] API 呼叫成功")

        analysis_text = _extract_response_text(response)
        if not analysis_text:
            raise RuntimeError("Gemini 回覆為空")

        print("[Gemini] 分析生成完成")
        return f"{symbol} AI 市場分析\n\n{analysis_text}"
    except Exception as error:
        print(f"[Gemini] API 呼叫失敗：{error}")
        return AI_ANALYSIS_ERROR_MESSAGE
