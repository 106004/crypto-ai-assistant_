"""Background job helpers for scheduled tasks."""

from __future__ import annotations

from services.market.collector_service import collect_market_data
from utils.logger import log_error, log_info


def run_market_update_job():
    log_info("Scheduler", "market update job started")

    try:
        collect_market_data()
    except Exception as error:
        log_error("Scheduler", f"market update failed: {error}")
        raise

    log_info("Scheduler", "market update success")
    return True
