"""In-memory metrics for the Agent layer.

This is a lightweight observability baseline.
It stays in memory for now so it cannot break Supabase, Gemini, or LINE flow.
"""

from __future__ import annotations

from threading import Lock

AGENT_METRICS = {
    "workflow_success": 0,
    "workflow_failure": 0,
    "fallback_count": 0,
    "intent_counts": {},
    "workflow_latency_ms": [],
}

METRICS_LOCK = Lock()


def _increment_intent_count(intent: str) -> None:
    intent_key = str(intent or "unknown").strip().lower() or "unknown"
    with METRICS_LOCK:
        intent_counts = AGENT_METRICS.setdefault("intent_counts", {})
        intent_counts[intent_key] = int(intent_counts.get(intent_key, 0)) + 1


def record_intent_usage(intent):
    _increment_intent_count(intent)
    print(f"[AgentMetrics] intent usage recorded: {intent}")


def record_workflow_success(intent):
    with METRICS_LOCK:
        AGENT_METRICS["workflow_success"] = int(AGENT_METRICS.get("workflow_success", 0)) + 1
    print(f"[AgentMetrics] workflow success: {intent}")


def record_workflow_failure(intent):
    with METRICS_LOCK:
        AGENT_METRICS["workflow_failure"] = int(AGENT_METRICS.get("workflow_failure", 0)) + 1
    print(f"[AgentMetrics] workflow failure: {intent}")


def record_fallback(intent):
    with METRICS_LOCK:
        AGENT_METRICS["fallback_count"] = int(AGENT_METRICS.get("fallback_count", 0)) + 1
    print(f"[AgentMetrics] fallback recorded: {intent}")


def record_latency(ms):
    latency_ms = float(ms)
    with METRICS_LOCK:
        AGENT_METRICS.setdefault("workflow_latency_ms", []).append(latency_ms)
    print(f"[AgentMetrics] latency recorded: {latency_ms:.3f}")


def get_agent_metrics():
    with METRICS_LOCK:
        return {
            "workflow_success": int(AGENT_METRICS.get("workflow_success", 0)),
            "workflow_failure": int(AGENT_METRICS.get("workflow_failure", 0)),
            "fallback_count": int(AGENT_METRICS.get("fallback_count", 0)),
            "intent_counts": dict(AGENT_METRICS.get("intent_counts", {})),
            "workflow_latency_ms": list(AGENT_METRICS.get("workflow_latency_ms", [])),
        }
