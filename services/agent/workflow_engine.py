"""Workflow engine scaffold.

Workflow engine is the Agent's flow controller.
It takes a user message, asks the decision engine for an intent,
looks up the matching tool, checks policy, runs the tool if allowed,
and returns a structured result.
This version is intentionally isolated from LINE flow, Gemini, and Supabase.
"""

from __future__ import annotations

from time import perf_counter

from services.agent import agent_metrics
from services.agent import agent_policy, decision_engine, state_manager, tool_registry


def _execute_tool(intent: str, user_id: str, coin: str, tool):
    """Run the tool for a supported intent.

    This is a small dispatch layer so the workflow stays easy to follow.
    The actual business logic still lives in the existing service functions.
    """

    if intent in {"price_query", "market_analysis"}:
        return tool(coin)

    if intent == "set_favorite_coin":
        return tool(user_id, coin)

    if intent == "get_favorite_coin":
        return tool(user_id)

    if intent == "help":
        return tool()

    return None


def _build_state_updates(intent: str, coin: str):
    """Build the minimal state update payload.

    We only write last_coin when we actually have a coin.
    That keeps an unknown message from wiping the user's previous coin.
    """

    updates = {"last_intent": intent}
    if coin:
        updates["last_coin"] = coin
    return updates


def run_agent_workflow(user_id: str, message: str):
    """Run the current first-pass agent workflow.

    Flow:
    1. decide intent
    2. find tool for intent
    3. execute tool
    4. update short-term state
    5. return a structured response
    """

    start_time = perf_counter()
    intent = "unknown"
    coin = ""
    confidence = 0.0
    try:
        # Step 1: Read the user's current short-term memory first.
        # The decision engine can use this to resolve vague follow-up messages.
        user_state_before = state_manager.get_user_state(user_id)

        # Step 2: Ask the decision engine what the user likely wants.
        decision = decision_engine.decide_user_intent(message, user_state=user_state_before)
        intent = str(decision.get("intent") or "unknown").strip().lower()
        coin = str(decision.get("coin") or "").strip().upper()
        confidence = float(decision.get("confidence") or 0.0)
        agent_metrics.record_intent_usage(intent)
        print(f"[AgentWorkflow] intent decided: {intent}")

        # Step 3: Look up the matching tool from the registry.
        tool = tool_registry.get_tool_for_intent(intent)

        # Step 4: Ask the policy layer whether this intent is allowed.
        policy_decision = agent_policy.should_execute_intent(
            intent,
            context={
                "market_data_fresh": user_state_before.get("market_data_fresh", True),
                "user_state": user_state_before,
            },
        )

        # Step 5: If policy blocks execution, return a safe blocked response.
        if not policy_decision.get("allowed", False):
            agent_metrics.record_fallback(intent)
            state = state_manager.update_user_state(
                user_id,
                _build_state_updates(intent, coin),
            )
            print("[AgentWorkflow] state updated")
            agent_metrics.record_workflow_success(intent)
            return {
                "intent": intent,
                "blocked": True,
                "reason": policy_decision.get("reason", "blocked"),
                "fallback_action": policy_decision.get("fallback_action", ""),
                "state": state,
            }

        # Step 6: Execute the tool if we have one; otherwise fall back safely.
        result = "unknown_intent"
        if tool is not None:
            result = _execute_tool(intent, user_id, coin, tool)
            print("[AgentWorkflow] tool executed")
        else:
            agent_metrics.record_fallback(intent)

        # Step 7: Update the agent's short-term memory after every workflow run.
        state = state_manager.update_user_state(
            user_id,
            _build_state_updates(intent, coin),
        )
        print("[AgentWorkflow] state updated")
        agent_metrics.record_workflow_success(intent)

        # Step 8: Return everything the caller may need.
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
