"""Cron route for market update."""

from __future__ import annotations

from flask import Blueprint, jsonify

from services.jobs.scheduler_service import run_market_update_job


cron_bp = Blueprint("cron", __name__)


@cron_bp.route("/update-market-data", methods=["GET"])
def update_market_data():
    print("[Route] /update-market-data called")

    try:
        run_market_update_job()
    except Exception as error:
        print(f"[ExternalCron][ERROR] market update failed: {error}")
        return jsonify({"status": "error", "message": str(error)}), 500

    print("[Route] cron route complete")
    print("[ExternalCron] market update success")
    return jsonify({"status": "success", "message": "market data updated"})
