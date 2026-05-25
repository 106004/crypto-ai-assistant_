"""Compatibility wrapper for the new data.clients.supabase_client module."""

from config.settings import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL
from data.clients.supabase_client import get_supabase_client


__all__ = [
    "get_supabase_client",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
]
