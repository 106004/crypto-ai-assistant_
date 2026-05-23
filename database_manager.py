from supabase_client import get_supabase_client


# database_manager.py 是專案集中操作資料庫的地方。
# 其他檔案不用知道 Supabase API 怎麼寫，只要呼叫這裡的函式。
# Render 的檔案系統不適合長期存 JSON，因為部署、重開或多個 instance 時，
# 本機檔案可能不同步或被重建；Supabase 這種雲端資料庫比較適合保存正式資料。


def _execute_safely(action, fallback=None):
    try:
        return action()
    except Exception as error:
        print(f"[Supabase] 操作失敗，系統會改用 JSON fallback：{error}")
        return fallback


def _first_row(response):
    data = getattr(response, "data", None)
    if isinstance(data, list) and data:
        return data[0]
    return None


def _all_rows(response):
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return data
    return []


def _normalize_user_data(user_data):
    normalized = dict(user_data or {})

    if "line_user_id" not in normalized and "user_id" in normalized:
        normalized["line_user_id"] = normalized.pop("user_id")

    return normalized


def _normalize_market_data(coin_data):
    normalized = dict(coin_data or {})
    symbol = str(normalized.get("symbol", "")).strip().upper()
    if symbol:
        normalized["symbol"] = symbol
    return normalized


def get_user_by_line_id(line_user_id):
    """用 LINE user id 從 Supabase users table 查一筆使用者。"""

    client = get_supabase_client()
    if client is None:
        return None

    def query():
        response = (
            client.table("users")
            .select("*")
            .eq("line_user_id", line_user_id)
            .limit(1)
            .execute()
        )
        return _first_row(response)

    user = _execute_safely(query)
    if user is not None:
        print("[Supabase] 查詢 users 成功")
    return user


def get_all_users_from_db():
    """從 Supabase users table 讀取所有使用者。"""

    client = get_supabase_client()
    if client is None:
        return []

    def query():
        response = client.table("users").select("*").execute()
        return _all_rows(response)

    users = _execute_safely(query, [])
    if users:
        print("[Supabase] 查詢 users 成功")
    return users


def upsert_user(user_data):
    """新增或更新使用者。"""

    # upsert 的概念是「有資料就更新，沒有資料就新增」。
    # 這裡先查 line_user_id 是否存在，再決定 update 或 insert，方便 debug 時看懂流程。
    client = get_supabase_client()
    if client is None:
        return False

    normalized = _normalize_user_data(user_data)
    line_user_id = normalized.get("line_user_id")
    if not line_user_id:
        print("[Supabase] 寫入 users 失敗：缺少 line_user_id")
        return False

    def command():
        existing = get_user_by_line_id(line_user_id)
        if existing:
            response = (
                client.table("users")
                .update(normalized)
                .eq("line_user_id", line_user_id)
                .execute()
            )
        else:
            response = client.table("users").insert(normalized).execute()

        return response

    response = _execute_safely(command)
    if response is None:
        return False

    print("[Supabase] 寫入 users 成功")
    return True


def get_market_data_by_symbol(symbol):
    """用 symbol 從 Supabase market_data table 查一筆幣價資料。"""

    client = get_supabase_client()
    if client is None:
        return None

    normalized_symbol = str(symbol).strip().upper()

    def query():
        response = (
            client.table("market_data")
            .select("*")
            .eq("symbol", normalized_symbol)
            .limit(1)
            .execute()
        )
        return _first_row(response)

    coin_data = _execute_safely(query)
    if coin_data is not None:
        print("[Supabase] 查詢 market_data 成功")
    return coin_data


def get_all_market_data_from_db():
    """從 Supabase market_data table 讀取所有市場資料。"""

    client = get_supabase_client()
    if client is None:
        return []

    def query():
        response = client.table("market_data").select("*").execute()
        return _all_rows(response)

    market_data = _execute_safely(query, [])
    if market_data:
        print("[Supabase] 查詢 market_data 成功")
    return market_data


def upsert_market_data(coin_data):
    """新增或更新單一幣種市場資料。"""

    client = get_supabase_client()
    if client is None:
        return False

    normalized = _normalize_market_data(coin_data)
    symbol = normalized.get("symbol")
    if not symbol:
        print("[Supabase] 寫入 market_data 失敗：缺少 symbol")
        return False

    update_payload = {
        "price_usd": normalized.get("price_usd"),
        "change_24h": normalized.get("change_24h"),
        "updated_at": normalized.get("updated_at"),
    }

    try:
        existing_response = (
            client.table("market_data")
            .select("*")
            .eq("symbol", symbol)
            .limit(1)
            .execute()
        )
        existing = _first_row(existing_response)

        if existing:
            response = (
                client.table("market_data")
                .update(update_payload)
                .eq("symbol", symbol)
                .execute()
            )
        else:
            response = client.table("market_data").insert(normalized).execute()
    except Exception as error:
        print(f"[Supabase] {symbol} 更新失敗：{error}")
        return False

    if response is None:
        print(f"[Supabase] {symbol} 更新失敗：沒有回傳結果")
        return False

    print(f"[Supabase] {symbol} 更新成功")
    return True
