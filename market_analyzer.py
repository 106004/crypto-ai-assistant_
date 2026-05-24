from gemini_client import get_gemini_client


GEMINI_MODEL = "gemini-2.5-flash"
AI_FALLBACK_PREFIX = "⚠️ AI 額度暫時不足，以下使用規則分析。"
INSUFFICIENT_DATA_MESSAGE = "目前資料不足，無法產生分析。"


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_change_percent(change_24h):
    sign = "+" if change_24h > 0 else ""
    return f"{sign}{change_24h:.1f}%"


def _format_price(price_usd):
    price = _to_float(price_usd)
    if price is None:
        return "N/A"
    return f"{price:g}"


def rule_based_analysis(coin_data):
    """用固定規則做市場分析，作為 Gemini 不可用時的穩定 fallback。"""

    print("[Analyzer] 使用 rule_based_analysis")

    if not isinstance(coin_data, dict):
        return INSUFFICIENT_DATA_MESSAGE

    # 市場分析就是把價格、漲跌幅等資料整理成使用者看得懂的狀態判斷。
    # 這裡先用明確規則，是因為規則分析穩定、可預期，也不會受到 API 額度影響。
    # 之後如果 AI 服務穩定，可以讓 Gemini 根據更多資料做更細緻的語意分析。
    change_24h = _to_float(coin_data.get("change_24h"))
    if change_24h is None:
        return INSUFFICIENT_DATA_MESSAGE

    if change_24h >= 5:
        market_status = "強勢上漲"
        interpretation = "短線買盤明顯，但也要注意追高風險。"
    elif change_24h >= 2:
        market_status = "偏強"
        interpretation = "價格有上漲動能，但仍需觀察是否延續。"
    elif change_24h > -2:
        market_status = "震盪"
        interpretation = "目前漲跌幅不大，市場方向暫時不明顯。"
    elif change_24h > -5:
        market_status = "偏弱"
        interpretation = "價格短線承壓，需注意是否繼續下跌。"
    else:
        market_status = "明顯下跌"
        interpretation = "賣壓較強，短線波動風險較高。"

    symbol = str(coin_data.get("symbol") or "").strip().upper() or "UNKNOWN"
    price_text = _format_price(coin_data.get("price_usd"))

    return (
        f"{symbol} 市場簡易分析\n\n"
        f"價格：{price_text} USD\n"
        f"24H 漲跌：{_format_change_percent(change_24h)}\n\n"
        f"市場狀態：{market_status}\n\n"
        "解讀：\n"
        f"{interpretation}\n\n"
        "提醒：\n"
        "這不是投資建議，只是資料整理與簡單分析。"
    )


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

        print(f"[Gemini] 使用模型：{GEMINI_MODEL}")
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
        print("[Gemini] API 呼叫失敗，改用規則分析")
        return f"{AI_FALLBACK_PREFIX}\n\n{rule_based_analysis(coin_data)}"
