"""Workflow engine scaffold.

Workflow engine is the Agent's flow controller.
It can execute a single intent or a sequential multi-intent task list.
"""

from __future__ import annotations

from time import perf_counter

from services.agent import agent_metrics
from services.agent import agent_policy, decision_engine, state_manager, tool_registry
from services.agent.unsupported_coin_service import build_unsupported_coin_message
from services.line.analysis_service import handle_analysis_query
from services.line.message_service import (
    format_clarification_message,
    format_unknown_command_message,
)
from services.line.price_service import handle_price_query


def _execute_tool(intent: str, user_id: str, coin: str, tool):
    """Run the tool for a supported single intent."""

    if intent in {"price_query", "market_analysis"}:
        return tool(coin)

    if intent == "set_favorite_coin":
        return tool(user_id, coin)

    if intent == "get_favorite_coin":
        return tool(user_id)

    if intent == "help":
        return tool()

    return None


def _normalize_task(task: dict[str, object]) -> dict[str, str]:
    intent = str((task or {}).get("intent") or "").strip().lower()
    coin = str((task or {}).get("coin") or "").strip().upper()
    return {"intent": intent, "coin": coin}


def _task_label(intent: str, coin: str) -> str:
    if intent == "price_query":
        return f"{coin} price"
    if intent == "market_analysis":
        return f"{coin} analysis"
    if intent == "unsupported_coin":
        return f"{coin} unsupported coin"
    if intent == "clarification_needed":
        return "clarification needed"
    return "unknown task"


def _build_task_message(task: dict[str, str], result_text: str, total_tasks: int) -> str:
    if total_tasks <= 1:
        return result_text
    return f"{_task_label(task['intent'], task['coin'])}\n{result_text}".strip()


def _run_task(task: dict[str, object]) -> dict[str, object]:
    normalized_task = _normalize_task(task)
    intent = normalized_task["intent"]
    coin = normalized_task["coin"]

    if intent == "price_query":
        return {"ok": True, "result": handle_price_query(coin)}

    if intent == "market_analysis":
        return {"ok": True, "result": handle_analysis_query(coin)}

    if intent == "unsupported_coin":
        return {"ok": True, "result": build_unsupported_coin_message(coin)}

    if intent == "clarification_needed":
        return {"ok": True, "result": format_clarification_message([], reason="low_confidence")}

    if intent == "unknown":
        return {"ok": True, "result": format_unknown_command_message()}

    return {"ok": True, "result": format_unknown_command_message()}


def _compose_task_results(task_results: list[dict[str, object]]) -> str:
    sections = [
        str(item.get("message") or "").strip()
        for item in task_results
        if str(item.get("message") or "").strip()
    ]
    return "\n\n".join(sections).strip()


def _build_state_updates(intent: str, coin: str, extra_updates: dict | None = None):
    """Build the minimal state update payload."""

    updates = {"last_intent": intent}
    if coin:
        updates["last_coin"] = coin
    if extra_updates:
        updates.update(dict(extra_updates))
    return updates


def execute_tasks(tasks: list[dict[str, object]], user_context: dict | None = None):
    """Execute a multi-intent task list sequentially and compose one response."""

    task_list = [dict(task or {}) for task in (tasks or [])]
    user_context = dict(user_context or {})
    user_id = str(user_context.get("user_id") or "").strip()

    print(f"[WorkflowEngine] execute_tasks called: tasks_length={len(task_list)}")

    if not task_list:
        state = None
        if user_id:
            state = state_manager.update_user_state(user_id, _build_state_updates("unknown", ""))
        return {
            "intent": "unknown",
            "coin": "",
            "confidence": 0.0,
            "tasks": [],
            "results": [],
            "result": format_unknown_command_message(),
            "state": state,
        }

    task_results: list[dict[str, object]] = []
    total_tasks = len(task_list)
    any_success = False

    for index, raw_task in enumerate(task_list, start=1):
        task = _normalize_task(raw_task)
        intent = task["intent"] or "unknown"
        coin = task["coin"]
        print(f"[WorkflowEngine] executing task {index}/{total_tasks}: intent={intent} coin={coin}")

        try:
            execution = _run_task(task)
            task_message = _build_task_message(task, str(execution.get("result") or ""), total_tasks)
            execution.update(
                {
                    "task": task,
                    "intent": intent,
                    "coin": coin,
                    "message": task_message,
                }
            )
            task_results.append(execution)
            any_success = any_success or bool(execution.get("ok"))
            agent_metrics.record_intent_usage(intent)
            print("[WorkflowEngine] task completed")
        except Exception as error:
            failure_message = f"{_task_label(intent, coin)}\n分析失敗，請稍後再試。"
            task_results.append(
                {
                    "task": task,
                    "intent": intent,
                    "coin": coin,
                    "ok": False,
                    "error": str(error),
                    "message": failure_message,
                }
            )
            agent_metrics.record_intent_usage(intent)
            agent_metrics.record_fallback(intent)
            print("[WorkflowEngine] task failed")

    combined_result = _compose_task_results(task_results)
    print("[WorkflowEngine] combined response generated")

    last_task = task_results[-1]["task"] if task_results else {"intent": "unknown", "coin": ""}
    last_intent = str((last_task or {}).get("intent") or "unknown").strip().lower() or "unknown"
    last_coin = str((last_task or {}).get("coin") or "").strip().upper()

    state = None
    if user_id:
        state = state_manager.update_user_state(
            user_id,
            _build_state_updates(last_intent, last_coin),
        )
        print("[AgentWorkflow] state updated")

    confidence = 0.9 if any_success else 0.0
    overall_intent = last_intent if total_tasks == 1 else "multi_task"
    return {
        "intent": overall_intent,
        "coin": last_coin,
        "confidence": confidence,
        "tasks": task_list,
        "results": task_results,
        "result": combined_result,
        "state": state,
    }


def run_agent_workflow(user_id: str, message: str):
    """Run the current workflow.

    This supports both the legacy single-intent path and the new multi-task path.
    """

    start_time = perf_counter()
    intent = "unknown"
    coin = ""
    confidence = 0.0
    workflow_success = False
    try:
        user_state_before = state_manager.get_user_state(user_id)

        decision = decision_engine.decide_user_intent(message, user_state=user_state_before)
        intent = str(decision.get("intent") or "unknown").strip().lower()
        coin = str(decision.get("coin") or "").strip().upper()
        confidence = float(decision.get("confidence") or 0.0)
        candidates = list(decision.get("candidates") or [])
        tasks = list(decision.get("tasks") or [])
        agent_metrics.record_intent_usage(intent)
        print(f"[AgentWorkflow] intent decided: {intent}")

        if tasks:
            multi_result = execute_tasks(
                tasks,
                user_context={
                    "user_id": user_id,
                    "user_state": user_state_before,
                },
            )
            workflow_success = any(bool(item.get("ok")) for item in multi_result.get("results", []))
            print(f"[WorkflowEngine] execute_tasks returned: tasks_length={len(tasks)}")
            if workflow_success:
                agent_metrics.record_workflow_success("multi_task")
            else:
                agent_metrics.record_workflow_failure("multi_task")
                agent_metrics.record_fallback("multi_task")
            return multi_result

        if intent == "clarification_needed":
            print("[Clarification] clarification triggered")
            print(f"[Clarification] candidates suggested: {candidates}")
            clarification_message = format_clarification_message(
                candidates,
                reason=str(decision.get("reason") or "low_confidence"),
            )
            state = state_manager.update_user_state(
                user_id,
                _build_state_updates(
                    intent,
                    coin,
                    extra_updates={"last_clarification_candidates": candidates},
                ),
            )
            print("[AgentWorkflow] state updated")
            agent_metrics.record_workflow_success(intent)
            workflow_success = True
            return {
                "intent": intent,
                "candidates": candidates,
                "reason": str(decision.get("reason") or "low_confidence"),
                "message": clarification_message,
                "state": state,
            }

        if intent == "unsupported_coin":
            print("[UnsupportedCoin] unsupported workflow triggered")
            unsupported_message = build_unsupported_coin_message(coin)
            state = state_manager.update_user_state(
                user_id,
                _build_state_updates(intent, coin),
            )
            print("[AgentWorkflow] state updated")
            print("[UnsupportedCoin] response returned")
            agent_metrics.record_workflow_success(intent)
            workflow_success = True
            return {
                "intent": intent,
                "coin": coin,
                "reason": str(decision.get("reason") or "coin_not_supported"),
                "message": unsupported_message,
                "state": state,
            }

        tool = tool_registry.get_tool_for_intent(intent)
        policy_decision = agent_policy.should_execute_intent(
            intent,
            context={
                "market_data_fresh": user_state_before.get("market_data_fresh", True),
                "user_state": user_state_before,
            },
        )

        if not policy_decision.get("allowed", False):
            agent_metrics.record_fallback(intent)
            state = state_manager.update_user_state(
                user_id,
                _build_state_updates(intent, coin),
            )
            print("[AgentWorkflow] state updated")
            agent_metrics.record_workflow_success(intent)
            workflow_success = False
            return {
                "intent": intent,
                "blocked": True,
                "reason": policy_decision.get("reason", "blocked"),
                "fallback_action": policy_decision.get("fallback_action", ""),
                "state": state,
            }

        result = "unknown_intent"
        if tool is not None:
            result = _execute_tool(intent, user_id, coin, tool)
            print("[AgentWorkflow] tool executed")
        else:
            agent_metrics.record_fallback(intent)

        state = state_manager.update_user_state(
            user_id,
            _build_state_updates(intent, coin),
        )
        print("[AgentWorkflow] state updated")
        agent_metrics.record_workflow_success(intent)
        workflow_success = True

        return {
            "intent": intent,
            "coin": coin,
            "confidence": confidence,
            "result": result,
            "state": state,
        }
    except Exception:
        agent_metrics.record_workflow_failure(intent)
        agent_metrics.record_fallback(intent)
        raise
    finally:
        latency_ms = (perf_counter() - start_time) * 1000.0
        agent_metrics.record_latency(latency_ms)
        agent_metrics.record_last_workflow(intent, workflow_success, latency_ms)
