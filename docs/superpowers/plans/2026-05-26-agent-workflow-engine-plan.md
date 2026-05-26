# Agent Workflow Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first workflow engine that takes a message, resolves an intent, finds the matching tool, runs it, and returns a structured result without connecting to LINE flow.

**Architecture:** Keep `services/agent/workflow_engine.py` as the orchestration layer for the agent path. It should depend only on `decision_engine` and `tool_registry`, then execute the returned function in a small, explicit dispatch path. Add focused unit tests that stub the decision and tool lookup steps so the workflow is verified without touching LINE bot code, Supabase, Gemini, or scheduler code.

**Tech Stack:** Python, `unittest`, `unittest.mock`

---

### Task 1: Implement workflow orchestration

**Files:**
- Modify: `services/agent/workflow_engine.py`
- Create: `tests/test_agent_workflow_engine.py`

- [ ] **Step 1: Write the failing test**

```python
import unittest
from unittest.mock import patch

from services.agent.workflow_engine import run_agent_workflow


class WorkflowEngineTest(unittest.TestCase):
    def test_price_query_workflow(self):
        with patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={"intent": "price_query", "coin": "BTC", "confidence": 0.9},
        ), patch(
            "services.agent.workflow_engine.tool_registry.get_tool_for_intent",
            return_value=lambda user_id, coin: {"user_id": user_id, "coin": coin},
        ):
            result = run_agent_workflow("test-user", "btc")

        assert result == {
            "intent": "price_query",
            "coin": "BTC",
            "result": {"user_id": "test-user", "coin": "BTC"},
        }

    def test_analysis_workflow(self):
        with patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={"intent": "market_analysis", "coin": "ETH", "confidence": 0.9},
        ), patch(
            "services.agent.workflow_engine.tool_registry.get_tool_for_intent",
            return_value=lambda user_id, coin: {"analysis": f"{user_id}:{coin}"},
        ):
            result = run_agent_workflow("test-user", "analyze eth")

        assert result == {
            "intent": "market_analysis",
            "coin": "ETH",
            "result": {"analysis": "test-user:ETH"},
        }


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m unittest tests.test_agent_workflow_engine -v`

Expected: FAIL because `run_agent_workflow` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
"""Workflow engine scaffold.

Workflow engine is the Agent's flow controller.
It takes a user message, asks the decision engine for an intent,
looks up the matching tool, runs it, and returns a structured result.
This version is intentionally isolated from LINE flow, Gemini, and Supabase.
"""

from __future__ import annotations

from services.agent import decision_engine, tool_registry


def run_agent_workflow(user_id: str, message: str):
    decision = decision_engine.decide_user_intent(message)
    intent = str(decision.get("intent") or "unknown").strip().lower()
    coin = str(decision.get("coin") or "").strip().upper()
    tool = tool_registry.get_tool_for_intent(intent)

    if tool is None:
        return {"intent": "unknown", "result": "unknown_intent"}

    if intent in {"price_query", "market_analysis"}:
        result = tool(coin)
    elif intent == "set_favorite_coin":
        result = tool(user_id, coin)
    elif intent == "get_favorite_coin":
        result = tool(user_id)
    elif intent == "help":
        result = tool()
    else:
        return {"intent": "unknown", "result": "unknown_intent"}

    return {
        "intent": intent,
        "coin": coin,
        "result": result,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -m unittest tests.test_agent_workflow_engine -v`

Expected: PASS for `btc` and `analyze eth` workflows.

- [ ] **Step 5: Commit**

```bash
git add services/agent/workflow_engine.py tests/test_agent_workflow_engine.py docs/superpowers/plans/2026-05-26-agent-workflow-engine-plan.md
git commit -m "feat: add agent workflow engine"
```
