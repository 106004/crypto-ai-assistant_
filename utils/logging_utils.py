"""Backward-compatible logging helpers."""

from __future__ import annotations

from utils.logger import log_error as _log_error
from utils.logger import log_info as _log_info


def log_info(prefix, message):
    _log_info(prefix, message)


def log_error(prefix, message):
    _log_error(prefix, message)
