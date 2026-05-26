"""Agent metrics route."""

from __future__ import annotations

from flask import Blueprint, jsonify

from services.agent.agent_metrics import get_agent_metrics


agent_metrics_bp = Blueprint("agent_metrics", __name__)


@agent_metrics_bp.route("/agent-metrics", methods=["GET"])
def agent_metrics():
    print("[AgentMetricsAPI] metrics requested")
    metrics = get_agent_metrics()
    return jsonify(metrics)
