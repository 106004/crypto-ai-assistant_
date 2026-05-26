"""State manager scaffold.

State manager is the Agent's short-term memory.
It keeps a small in-memory record for each user during the current process.
This version does not use Supabase, LINE flow, or Gemini.
"""

from __future__ import annotations


DEFAULT_USER_STATE = {
    "last_coin": None,
    "last_intent": None,
    "conversation_count": 0,
}

# In-memory state only. This resets when the process restarts.
USER_STATE = {}


def _build_default_state():
    return dict(DEFAULT_USER_STATE)


def get_user_state(user_id: str):
    """Return the current state for a user, creating a default one if needed."""

    user_key = str(user_id or "").strip()
    if not user_key:
        return _build_default_state()

    if user_key not in USER_STATE:
        USER_STATE[user_key] = _build_default_state()

    return USER_STATE[user_key]


def update_user_state(user_id: str, updates: dict):
    """Update a user's short-term memory and count this as one conversation turn."""

    state = get_user_state(user_id)
    state.update(dict(updates or {}))
    state["conversation_count"] = int(state.get("conversation_count") or 0) + 1
    return state


def reset_user_state(user_id: str):
    """Clear one user's short-term memory."""

    user_key = str(user_id or "").strip()
    if user_key in USER_STATE:
        del USER_STATE[user_key]

    return _build_default_state()
