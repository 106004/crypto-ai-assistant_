"""Gemini client wrapper for market analysis generation."""

from __future__ import annotations

from config.settings import GEMINI_MODEL


def generate_market_analysis(prompt):
    print("[GeminiClient] generating analysis")

    try:
        from market_analyzer import get_gemini_client

        client = get_gemini_client()
        if client is None:
            raise RuntimeError("missing Gemini API key or client unavailable")

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        text = str(getattr(response, "text", "")).strip()
        if not text:
            raise RuntimeError("empty Gemini response")

        print("[GeminiClient] generation success")
        generate_market_analysis.last_error = None
        return text
    except Exception as error:
        print(f"[GeminiClient][ERROR] generation failed: {error}")
        generate_market_analysis.last_error = error
        return None


generate_market_analysis.last_error = None
