"""AI market analysis flow with Gemini fallback."""

from __future__ import annotations

from data.clients.gemini_client import generate_market_analysis
from services.ai.prompt_builder import build_market_analysis_prompt
from services.ai.rule_based_analyzer import (
    AI_FALLBACK_PREFIX,
    INSUFFICIENT_DATA_MESSAGE,
    rule_based_analysis,
)


def analyze_market_data(coin_data):
    if not isinstance(coin_data, dict):
        return INSUFFICIENT_DATA_MESSAGE

    if coin_data.get("change_24h") is None:
        return INSUFFICIENT_DATA_MESSAGE

    symbol = str(coin_data.get("symbol") or "").strip().upper() or "UNKNOWN"
    print("[AIService] 開始 Gemini analysis")
    print("[Gemini] 開始生成市場分析")

    prompt = build_market_analysis_prompt(coin_data)
    print("[AIService] prompt built")
    print("[Gemini] Prompt 已建立")

    try:
        print("[Gemini] 使用模型：gemini-2.5-flash")
        analysis_text = generate_market_analysis(prompt)
        if not analysis_text:
            error = getattr(generate_market_analysis, "last_error", None)
            if error is not None:
                print(f"[AIService] Gemini error：{error}")
                print(f"[Gemini] API 呼叫失敗：{error}")
            else:
                print("[AIService] Gemini error：Gemini analysis unavailable")
                print("[Gemini] API 呼叫失敗：Gemini analysis unavailable")
            raise RuntimeError("Gemini analysis unavailable")

        print("[Gemini] API 呼叫成功")
        print("[AIService] Gemini success")
        print("[Gemini] 分析生成完成")
        return f"{symbol} AI 市場分析\n\n{analysis_text}"
    except Exception:
        print("[AIService] fallback to rule-based analysis")
        print("[Gemini] API 呼叫失敗，改用規則分析")
        return f"{AI_FALLBACK_PREFIX}\n\n{rule_based_analysis(coin_data)}"
