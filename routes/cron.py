"""External cron endpoints."""

from __future__ import annotations

from flask import Blueprint, jsonify

from services.jobs.scheduler_service import (
    run_daily_guide_job,
    run_favorite_coin_push_job,
    run_market_update_job,
)


cron_bp = Blueprint("cron", __name__)


def _run_external_cron(job_name, handler):
    print(f"[ExternalCron] {job_name} called")
    try:
        handler()
    except Exception as error:
        print(f"[ExternalCron][ERROR] {job_name} failed: {error}")
        return jsonify({"status": "error", "message": str(error)}), 500

    print(f"[ExternalCron] {job_name} completed")
    return jsonify({"status": "success", "message": f"{job_name} executed"})


@cron_bp.route("/update-market-data", methods=["GET"])
def update_market_data():
    return _run_external_cron("/update-market-data", run_market_update_job)


@cron_bp.route("/push-favorite-coin", methods=["GET"])
def push_favorite_coin():
    return _run_external_cron("/push-favorite-coin", run_favorite_coin_push_job)


@cron_bp.route("/daily-guide", methods=["GET"])
def daily_guide():
    return _run_external_cron("/daily-guide", run_daily_guide_job)
