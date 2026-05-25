"""User repository for Supabase users table."""

from __future__ import annotations

from data.clients.supabase_client import get_supabase_client


def _first_row(response):
    data = getattr(response, "data", None)
    if isinstance(data, list) and data:
        return data[0]
    return None


def _normalize_user_data(user_data):
    normalized = dict(user_data or {})
    if "line_user_id" not in normalized and "user_id" in normalized:
        normalized["line_user_id"] = normalized.pop("user_id")
    return normalized


def get_user(line_user_id):
    print("[UserRepository] fetching user")
    client = get_supabase_client()
    if client is None:
        return None

    try:
        response = (
            client.table("users")
            .select("*")
            .eq("line_user_id", line_user_id)
            .limit(1)
            .execute()
        )
        result = _first_row(response)
        get_user.last_error = None
        return result
    except Exception as error:
        get_user.last_error = error
        print(f"[UserRepository][ERROR] fetching user failed: {error}")
        return None


def save_user(user_data):
    normalized = _normalize_user_data(user_data)
    line_user_id = str(normalized.get("line_user_id") or "").strip()
    if not line_user_id:
        print("[UserRepository][ERROR] saving user failed: missing line_user_id")
        save_user.last_error = ValueError("missing line_user_id")
        return False

    client = get_supabase_client()
    if client is None:
        save_user.last_error = RuntimeError("missing supabase client")
        return False

    try:
        existing = (
            client.table("users")
            .select("line_user_id")
            .eq("line_user_id", line_user_id)
            .limit(1)
            .execute()
        )
        if _first_row(existing) is not None:
            client.table("users").update(normalized).eq("line_user_id", line_user_id).execute()
        else:
            client.table("users").insert(normalized).execute()
    except Exception as error:
        save_user.last_error = error
        print(f"[UserRepository][ERROR] saving user failed: {error}")
        return False

    save_user.last_error = None
    return True


def update_user_coin(line_user_id, symbol):
    print("[UserRepository] updating favorite coin")
    client = get_supabase_client()
    if client is None:
        update_user_coin.last_error = RuntimeError("missing supabase client")
        return False

    try:
        client.table("users").update({"favorite_coin": str(symbol).strip().lower()}).eq(
            "line_user_id", line_user_id
        ).execute()
    except Exception as error:
        update_user_coin.last_error = error
        print(f"[UserRepository][ERROR] updating favorite coin failed: {error}")
        return False

    update_user_coin.last_error = None
    return True


def get_all_users():
    client = get_supabase_client()
    if client is None:
        get_all_users.last_error = RuntimeError("missing supabase client")
        return []

    try:
        response = client.table("users").select("*").execute()
        data = getattr(response, "data", None)
        get_all_users.last_error = None
        return data if isinstance(data, list) else []
    except Exception as error:
        get_all_users.last_error = error
        print(f"[UserRepository][ERROR] fetching users failed: {error}")
        return []


get_user.last_error = None
save_user.last_error = None
update_user_coin.last_error = None
get_all_users.last_error = None
