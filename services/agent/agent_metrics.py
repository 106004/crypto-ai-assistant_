"""In-memory metrics for the Agent layer.

This is a lightweight observability baseline.
It stays in memory for now so it cannot break Supabase, Gemini, or LINE flow.
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock

AGENT_METRICS = {
    "workflow_success": 0,
    "workflow_failure": 0,
    "fallback_count": 0,
    "intent_counts": {},
    "workflow_latency_ms": [],
    "last_workflow": None,
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


def record_last_workflow(intent: str, success: bool, latency_ms: float) -> None:
    with METRICS_LOCK:
        AGENT_METRICS["last_workflow"] = {
            "intent": str(intent or "unknown").strip().lower() or "unknown",
            "success": bool(success),
            "latency_ms": float(latency_ms),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def reset_agent_metrics():
    with METRICS_LOCK:
        AGENT_METRICS["workflow_success"] = 0
        AGENT_METRICS["workflow_failure"] = 0
        AGENT_METRICS["fallback_count"] = 0
        AGENT_METRICS["intent_counts"] = {}
        AGENT_METRICS["workflow_latency_ms"] = []
        AGENT_METRICS["last_workflow"] = None
    print("[AgentMetrics] metrics reset")


def _build_summary_snapshot(metrics: dict) -> dict:
    total_workflows = int(metrics.get("workflow_success", 0)) + int(metrics.get("workflow_failure", 0))
    workflow_success = int(metrics.get("workflow_success", 0))
    workflow_failure = int(metrics.get("workflow_failure", 0))
    fallback_count = int(metrics.get("fallback_count", 0))
    success_rate = workflow_success / total_workflows if total_workflows else 0
    failure_rate = workflow_failure / total_workflows if total_workflows else 0
    fallback_rate = fallback_count / total_workflows if total_workflows else 0

    intent_counts = dict(metrics.get("intent_counts", {}))
    top_intents = [
        {"intent": intent, "count": count}
        for intent, count in sorted(
            intent_counts.items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        )[:5]
    ]

    latencies = list(metrics.get("workflow_latency_ms", []))
    if latencies:
        avg_latency_ms = sum(latencies) / len(latencies)
        min_latency_ms = min(latencies)
        max_latency_ms = max(latencies)
        last_latency_ms = latencies[-1]
    else:
        avg_latency_ms = 0
        min_latency_ms = 0
        max_latency_ms = 0
        last_latency_ms = 0

    summary = {
        "summary": {
            "total_workflows": total_workflows,
            "workflow_success": workflow_success,
            "workflow_failure": workflow_failure,
            "success_rate": success_rate,
            "failure_rate": failure_rate,
            "fallback_count": fallback_count,
            "fallback_rate": fallback_rate,
        },
        "intents": {
            "intent_counts": intent_counts,
            "top_intents": top_intents,
        },
        "latency": {
            "avg_latency_ms": avg_latency_ms,
            "min_latency_ms": min_latency_ms,
            "max_latency_ms": max_latency_ms,
            "last_latency_ms": last_latency_ms,
            "samples": latencies,
        },
        "last_workflow": metrics.get("last_workflow"),
    }
    print("[AgentMetrics] summary generated")
    return summary


def get_agent_metrics():
    with METRICS_LOCK:
        snapshot = {
            "workflow_success": int(AGENT_METRICS.get("workflow_success", 0)),
            "workflow_failure": int(AGENT_METRICS.get("workflow_failure", 0)),
            "fallback_count": int(AGENT_METRICS.get("fallback_count", 0)),
            "intent_counts": dict(AGENT_METRICS.get("intent_counts", {})),
            "workflow_latency_ms": list(AGENT_METRICS.get("workflow_latency_ms", [])),
            "last_workflow": AGENT_METRICS.get("last_workflow"),
        }
    return _build_summary_snapshot(snapshot)
