"""Agent metrics route."""

from __future__ import annotations

from flask import Blueprint, jsonify

from services.agent.agent_metrics import get_agent_metrics


agent_metrics_bp = Blueprint("agent_metrics", __name__)


@agent_metrics_bp.route("/agent-metrics", methods=["GET"])
def agent_metrics():
    print("[AgentMetricsAPI] metrics requested")
    metrics = get_agent_metrics()
    latencies = metrics.get("workflow_latency_ms", [])
    avg_latency_ms = sum(latencies) / len(latencies) if latencies else 0.0
    payload = {
        "workflow_success": metrics.get("workflow_success", 0),
        "workflow_failure": metrics.get("workflow_failure", 0),
        "fallback_count": metrics.get("fallback_count", 0),
        "intent_counts": metrics.get("intent_counts", {}),
        "workflow_latency_ms": latencies,
        "avg_latency_ms": avg_latency_ms,
    }
    return jsonify(payload)
