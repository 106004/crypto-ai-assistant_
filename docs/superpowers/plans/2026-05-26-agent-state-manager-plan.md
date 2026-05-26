# Agent State Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a small in-memory state manager so the agent can remember a user's last coin, last intent, and conversation count during the current process.

**Architecture:** Keep `services/agent/state_manager.py` as a pure short-term memory layer backed by a module-level dictionary. The API should stay tiny and explicit: read state, update state, and reset state. Add one focused unit test that updates a user and verifies the stored values can be read back without involving Supabase, LINE, or Gemini.

**Tech Stack:** Python, `unittest`

---

### Task 1: Implement in-memory user state storage

**Files:**
- Modify: `services/agent/state_manager.py`
- Create: `tests/test_agent_state_manager.py`

- [ ] **Step 1: Write the failing test**

```python
import unittest

from services.agent.state_manager import get_user_state, update_user_state


class StateManagerTest(unittest.TestCase):
    def test_update_and_read_back_state(self):
        update_user_state(
            "user-1",
            {
                "last_coin": "BTC",
                "last_intent": "market_analysis",
            },
        )

        state = get_user_state("user-1")
        assert state == {
            "last_coin": "BTC",
            "last_intent": "market_analysis",
            "conversation_count": 1,
        }


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m unittest tests.test_agent_state_manager -v`

Expected: FAIL because the state functions do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
"""State manager scaffold.

State manager is the Agent's short-term memory.
It keeps a small in-memory record for each user during the current process.
This version does not use Supabase, LINE flow, or Gemini.
"""

from __future__ import annotations

USER_STATE = {}


def get_user_state(user_id: str):
    user_key = str(user_id or "").strip()
    if not user_key:
        return {
            "last_coin": None,
            "last_intent": None,
            "conversation_count": 0,
        }

    if user_key not in USER_STATE:
        USER_STATE[user_key] = {
            "last_coin": None,
            "last_intent": None,
            "conversation_count": 0,
        }

    return USER_STATE[user_key]


def update_user_state(user_id: str, updates: dict):
    state = get_user_state(user_id)
    state.update(dict(updates or {}))
    state["conversation_count"] = int(state.get("conversation_count") or 0) + 1
    return state


def reset_user_state(user_id: str):
    user_key = str(user_id or "").strip()
    if user_key in USER_STATE:
        del USER_STATE[user_key]

    return {
        "last_coin": None,
        "last_intent": None,
        "conversation_count": 0,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -m unittest tests.test_agent_state_manager -v`

Expected: PASS and the stored state should show `last_coin = BTC`, `last_intent = market_analysis`, `conversation_count = 1`.

- [ ] **Step 5: Commit**

```bash
git add services/agent/state_manager.py tests/test_agent_state_manager.py docs/superpowers/plans/2026-05-26-agent-state-manager-plan.md
git commit -m "feat: add agent state manager"
```
