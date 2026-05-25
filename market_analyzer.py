"""Compatibility wrapper for market analysis.

The real implementation now lives under services.ai.
"""

from gemini_client import get_gemini_client
from services.ai.market_analysis_service import analyze_market_data
from services.ai.rule_based_analyzer import (
    AI_FALLBACK_PREFIX,
    INSUFFICIENT_DATA_MESSAGE,
    rule_based_analysis,
)
