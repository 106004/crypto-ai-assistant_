# Unified Intent Resolver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Centralize intent classification in one resolver so every path returns the same intent for the same message.

**Architecture:** Add a dedicated `intent_resolver` module that maps raw message text to a single intent using one ordered keyword policy. `decision_engine.py` will call this resolver both in the LLM fallback path and in rule-based flows, so keywords are no longer duplicated in multiple branches. Coin validation and unsupported-coin short-circuiting remain separate concerns.

**Tech Stack:** Python, unittest, existing agent routing modules

---

### Task 1: Add a single intent resolver and tests for keyword priority

**Files:**
- Create: `services/agent/intent_resolver.py`
- Create: `tests/test_intent_resolver.py`

- [ ] **Step 1: Write the failing test**

```python
import unittest

from services.agent.intent_resolver import resolve_intent


class IntentResolverTest(unittest.TestCase):
    def test_priority_and_defaults(self):
        cases = [
            ("BTC價格", "price_query"),
            ("BTC多少", "price_query"),
            ("analyze BTC", "market_analysis"),
            ("分析 BTC", "market_analysis"),
            ("幫我看看 BTC", "market_analysis"),
            ("BTC 怎麼樣", "market_analysis"),
            ("set BTC", "set_favorite_coin"),
            ("BTC 是我最愛", "set_favorite_coin"),
            ("help", "help"),
            ("怎麼用", "help"),
            ("asd123@@", "unknown"),
        ]

        for message, expected in cases:
            with self.subTest(message=message):
                self.assertEqual(resolve_intent(message), expected)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m unittest -v tests.test_intent_resolver`
Expected: `ModuleNotFoundError` for `services.agent.intent_resolver`

- [ ] **Step 3: Write minimal implementation**

```python
import re

ANALYSIS_KEYWORDS = ("analyze", "分析", "看看", "研究", "怎麼樣", "怎麼看")
SET_KEYWORDS = ("set", "設定", "設成", "我的幣", "最愛")
PRICE_KEYWORDS = ("price", "價格", "多少", "幾塊", "幾元")
HELP_KEYWORDS = ("help", "幫助", "指令", "怎麼用")


def resolve_intent(message: str) -> str:
    normalized = str(message or "").strip().lower()
    if not normalized:
        return "unknown"

    if any(keyword in normalized for keyword in ANALYSIS_KEYWORDS):
        return "market_analysis"
    if any(keyword in normalized for keyword in SET_KEYWORDS):
        return "set_favorite_coin"
    if any(keyword in normalized for keyword in PRICE_KEYWORDS):
        return "price_query"
    if any(keyword in normalized for keyword in HELP_KEYWORDS):
        return "help"
    return "unknown"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -m unittest -v tests.test_intent_resolver`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add services/agent/intent_resolver.py tests/test_intent_resolver.py
git commit -m "feat: add unified intent resolver"
```

### Task 2: Route decision_engine through the resolver

**Files:**
- Modify: `services/agent/decision_engine.py`
- Modify: `services/agent/llm_intent_classifier.py`
- Modify: `services/agent/workflow_engine.py`
- Modify: `services/line/command_router.py`
- Modify: `tests/test_agent_decision_engine.py`
- Modify: `tests/test_general_unsupported_coin_rule.py`
- Modify: `tests/test_unsupported_coin_workflow.py`

- [ ] **Step 1: Write the failing tests**

```python
import unittest
from services.agent.intent_resolver import resolve_intent


class DecisionEngineResolverCoverageTest(unittest.TestCase):
    def test_keyword_priority(self):
        self.assertEqual(resolve_intent("分析 BTC 價格"), "market_analysis")
```

- [ ] **Step 2: Run the tests to verify the current split logic still exists**

Run: `py -m unittest -v tests.test_agent_decision_engine tests.test_general_unsupported_coin_rule tests.test_unsupported_coin_workflow`
Expected: existing intent paths still pass before refactor

- [ ] **Step 3: Replace duplicated keyword matching with resolver calls**

```python
from services.agent.intent_resolver import resolve_intent


def _resolve_base_intent(message: str) -> str:
    return resolve_intent(message)


# In rule-based and fallback paths:
# - use resolve_intent(message)
# - keep coin extraction separate
# - keep unsupported_coin validation separate
```

- [ ] **Step 4: Run the tests to verify the unified path passes**

Run: `py -m unittest -v tests.test_agent_decision_engine tests.test_general_unsupported_coin_rule tests.test_unsupported_coin_workflow`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add services/agent/decision_engine.py services/agent/llm_intent_classifier.py services/agent/workflow_engine.py services/line/command_router.py tests/test_agent_decision_engine.py tests/test_general_unsupported_coin_rule.py tests/test_unsupported_coin_workflow.py
git commit -m "refactor: unify intent resolution"
```

### Task 3: Full regression run and final verification

**Files:**
- Review: `services/agent/intent_resolver.py`
- Review: `services/agent/decision_engine.py`
- Review: `services/agent/llm_intent_classifier.py`
- Review: `services/agent/workflow_engine.py`

- [ ] **Step 1: Run the full test suite**

Run: `py -m unittest discover -v`
Expected: `OK` with existing skips only

- [ ] **Step 2: Verify no routing conflicts remain**

Check the logs for one consistent decision path per message:
- `BTC價格` -> `price_query`
- `BTC多少` -> `price_query`
- `analyze BTC` -> `market_analysis`
- `分析 BTC` -> `market_analysis`
- `幫我看看 BTC` -> `market_analysis`
- `BTC 怎麼樣` -> `market_analysis`
- `set BTC` -> `set_favorite_coin`
- `BTC 是我最愛` -> `set_favorite_coin`
- `help` -> `help`
- `怎麼用` -> `help`
- `asd123@@` -> `unknown`

- [ ] **Step 3: Commit the full feature**

```bash
git add .
git commit -m "feat: unify intent resolver"
git push
```

### Coverage Check

- `resolve_intent()` covers the keyword priority and default fallback.
- `decision_engine.py` uses the resolver instead of duplicate keyword branching.
- Existing unsupported coin validation remains separate and still short-circuits before service calls.
- Regression tests cover all required examples and the full suite confirms no conflicts.

