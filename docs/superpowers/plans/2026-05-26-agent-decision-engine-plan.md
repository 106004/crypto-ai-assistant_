# Agent Decision Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first rule-based version of `decision_engine.py` so the project can classify simple user intents without using Gemini or any other LLM.

**Architecture:** Keep the decision engine isolated in `services/agent/decision_engine.py` with a single public function that normalizes text, detects a small set of command patterns, and returns a fixed dictionary shape. Add a focused unit test file that exercises the public function directly and proves the intent mapping works without touching LINE flow, Supabase, or Gemini.

**Tech Stack:** Python, `unittest`

---

### Task 1: Implement the rule-based decision engine

**Files:**
- Modify: `services/agent/decision_engine.py`
- Create: `tests/test_agent_decision_engine.py`

- [ ] **Step 1: Write the failing test**

```python
import unittest

from services.agent.decision_engine import decide_user_intent


class DecisionEngineTest(unittest.TestCase):
    def test_price_query(self):
        self.assertEqual(
            decide_user_intent("btc"),
            {"intent": "price_query", "coin": "BTC", "confidence": 0.9},
        )

    def test_market_analysis(self):
        self.assertEqual(
            decide_user_intent("analyze eth"),
            {"intent": "market_analysis", "coin": "ETH", "confidence": 0.9},
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m unittest tests.test_agent_decision_engine -v`

Expected: FAIL because `decide_user_intent` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
"""Decision engine scaffold.

Future role: decide what the user likely wants to do.
This first version is rule-based only and does not use Gemini or any LLM.
"""

from __future__ import annotations


def decide_user_intent(message: str):
    text = str(message or "").strip().lower()

    if text in {"help", "/help"}:
        return {"intent": "help", "coin": "", "confidence": 0.9}

    if text == "mycoin":
        return {"intent": "get_favorite_coin", "coin": "", "confidence": 0.9}

    if text.startswith("set "):
        coin = text.split(maxsplit=1)[1].strip().upper()
        if coin in {"BTC", "ETH", "SOL"}:
            return {"intent": "set_favorite_coin", "coin": coin, "confidence": 0.9}
        return {"intent": "unknown", "coin": "", "confidence": 0.1}

    if text.startswith("analyze "):
        coin = text.split(maxsplit=1)[1].strip().upper()
        if coin in {"BTC", "ETH", "SOL"}:
            return {"intent": "market_analysis", "coin": coin, "confidence": 0.9}
        return {"intent": "unknown", "coin": "", "confidence": 0.1}

    if text in {"btc", "eth", "sol"}:
        return {"intent": "price_query", "coin": text.upper(), "confidence": 0.9}

    return {"intent": "unknown", "coin": "", "confidence": 0.1}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -m unittest tests.test_agent_decision_engine -v`

Expected: PASS with the two intent examples and the fixed output shape.

- [ ] **Step 5: Commit**

```bash
git add services/agent/decision_engine.py tests/test_agent_decision_engine.py docs/superpowers/plans/2026-05-26-agent-decision-engine-plan.md
git commit -m "feat: add rule-based agent decision engine"
```
