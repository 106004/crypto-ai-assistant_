"""Lightweight UTC logger used by new code paths."""

from __future__ import annotations

from datetime import datetime, timezone


def _utc_prefix():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def log_info(prefix, message):
    print(f"{_utc_prefix()} [{prefix}] {message}")


def log_error(prefix, message):
    print(f"{_utc_prefix()} [{prefix}][ERROR] {message}")


def log_warning(prefix, message):
    print(f"{_utc_prefix()} [{prefix}][WARNING] {message}")
