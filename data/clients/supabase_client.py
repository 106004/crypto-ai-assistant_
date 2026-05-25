"""Supabase client wrapper.

這層只負責建立 Supabase client，不碰任何業務流程。
"""

from __future__ import annotations

from config.settings import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL

_supabase_client = None


def get_supabase_client():
    """建立並快取 Supabase client。"""

    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print(
            "[SupabaseClient] Supabase 設定缺失，請確認本機 .env 或 Render Environment Variables。"
        )
        return None

    try:
        from supabase import create_client
    except ImportError:
        print("[SupabaseClient] 缺少 supabase 套件，請檢查 requirements.txt 是否已安裝。")
        return None

    try:
        print("[SupabaseClient] 使用新 wrapper 建立 Supabase client")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    except Exception as error:
        print(f"[SupabaseClient] 建立 Supabase client 失敗：{error}")
        return None

    return _supabase_client

