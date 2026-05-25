"""Backend service health aggregation."""

from __future__ import annotations

import importlib

from config.settings import (
    LINE_BOT_BASIC_ID,
    LINE_CHANNEL_ACCESS_TOKEN,
    GEMINI_API_KEY,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_URL,
)


def _check_import(module_name):
    try:
        importlib.import_module(module_name)
        return "ok"
    except Exception as error:
        return f"unavailable: {error}"


def _check_supabase():
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return "missing env"

    try:
        from data.clients.supabase_client import get_supabase_client

        client = get_supabase_client()
        return "ok" if client is not None else "unavailable"
    except Exception as error:
        return f"unavailable: {error}"


def _check_gemini():
    if not GEMINI_API_KEY:
        print("[SystemHealth][WARNING] Gemini key missing")
        return "missing env"

    try:
        from gemini_client import get_gemini_client

        client = get_gemini_client()
        return "ok" if client is not None else "unavailable"
    except Exception as error:
        return f"unavailable: {error}"


def _check_coingecko():
    if not _check_import("data.clients.coingecko_client") == "ok":
        return "unavailable"
    return "ok"


def _check_line():
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_BOT_BASIC_ID:
        return "missing env"

    if _check_import("line_bot") != "ok":
        return "unavailable"

    return "ok"


def get_system_health():
    print("[SystemHealth] checking services")

    services = {
        "supabase": _check_supabase(),
        "gemini": _check_gemini(),
        "coingecko": _check_coingecko(),
        "line": _check_line(),
    }

    if services["supabase"] == "ok":
        print("[SystemHealth] supabase ok")
    if services["gemini"] == "ok":
        print("[SystemHealth] gemini ok")
    if services["coingecko"] == "ok":
        print("[SystemHealth] coingecko ok")
    if services["line"] == "ok":
        print("[SystemHealth] line ok")

    return {
        "status": "ok",
        "services": services,
    }
