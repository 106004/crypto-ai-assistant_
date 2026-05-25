"""Compatibility wrapper for repository-backed database access."""

from __future__ import annotations

from data.clients.supabase_client import get_supabase_client
import data.repositories.market_data_repository as market_data_repository
import data.repositories.user_repository as user_repository


def _bind_client_provider(repo_module):
    repo_module.get_supabase_client = get_supabase_client


def get_user_by_line_id(line_user_id):
    _bind_client_provider(user_repository)
    return user_repository.get_user(line_user_id)


def get_all_users_from_db():
    _bind_client_provider(user_repository)
    return user_repository.get_all_users()


def upsert_user(user_data):
    _bind_client_provider(user_repository)
    result = user_repository.save_user(user_data)
    line_user_id = str((user_data or {}).get("line_user_id") or (user_data or {}).get("user_id") or "").strip()
    if result:
        print("[Supabase] users update success")
    else:
        error = getattr(user_repository.save_user, "last_error", None)
        if line_user_id and error is not None:
            print(f"[Supabase] {line_user_id} 更新失敗：{error}")
    return result


def get_market_data_by_symbol(symbol):
    _bind_client_provider(market_data_repository)
    return market_data_repository.get_market_data(symbol)


def get_all_market_data_from_db():
    _bind_client_provider(market_data_repository)
    return market_data_repository.get_all_market_data()


def upsert_market_data(coin_data):
    _bind_client_provider(market_data_repository)
    normalized_symbol = str((coin_data or {}).get("symbol") or "").strip().upper()
    result = market_data_repository.save_market_data(coin_data)
    if result:
        print(f"[Supabase] {normalized_symbol} 更新成功")
    else:
        error = getattr(market_data_repository.save_market_data, "last_error", None)
        if normalized_symbol and error is not None:
            print(f"[Supabase] {normalized_symbol} 更新失敗：{error}")
    return result
