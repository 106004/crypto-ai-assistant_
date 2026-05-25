"""Health check route."""

from __future__ import annotations

from flask import Blueprint, jsonify

from services.system.system_health_service import get_system_health


health_bp = Blueprint("health", __name__)


@health_bp.route("/health")
def health_check():
    print("[Health] health check called")
    return jsonify({"status": "ok", "service": "crypto_ai_assistant"})


@health_bp.route("/health/details")
def health_details():
    print("[Health] health details called")
    return jsonify(get_system_health())
