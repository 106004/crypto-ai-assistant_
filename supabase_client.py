from config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL


_supabase_client = None


def get_supabase_client():
    """建立並回傳 Supabase client；設定缺失時回傳 None，避免 app 直接崩潰。"""

    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("找不到 Supabase 設定，請確認 .env 已設定 SUPABASE_URL 和 SUPABASE_SERVICE_ROLE_KEY。")
        return None

    try:
        from supabase import create_client
    except ImportError:
        print("找不到 supabase 套件，請先確認 requirements.txt 已安裝 supabase。")
        return None

    try:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    except Exception as error:
        print(f"Supabase client 建立失敗，系統會繼續使用 JSON fallback：{error}")
        return None

    print("[Supabase] 成功連線")
    return _supabase_client
