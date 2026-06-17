"""Lightweight, in-process conversation memory for Open Claw agents.

Agents need to hold multi-turn context in DMs and threads instead of replying
one-shot. ``ConversationStore`` keeps a bounded, per-conversation history keyed
by an opaque string (typically a Slack channel id, optionally combined with a
thread timestamp).

The store is deliberately pure: no Slack, no Anthropic, no I/O. That keeps it
trivially unit-testable and safe to share across the threaded orchestrator --
all mutations are guarded by a ``threading.Lock``.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

Role = str  # "user" | "assistant"
Turn = dict[str, str]  # {"role": Role, "content": str}

DEFAULT_MAX_TURNS = 12


@dataclass
class ConversationStore:
    """Bounded per-conversation history, safe for concurrent access.

    Each conversation key maps to a list of turns ordered oldest-first. Only the
    ``max_turns`` most recent turns are retained per key; older turns are
    trimmed as new ones arrive.
    """

    max_turns: int = DEFAULT_MAX_TURNS
    _store: dict[str, list[Turn]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        if self.max_turns < 1:
            raise ValueError("max_turns must be >= 1")

    def add(self, key: str, role: Role, content: str) -> None:
        """Append a turn for ``key`` and trim to ``max_turns`` most recent."""
        turn: Turn = {"role": role, "content": content}
        with self._lock:
            turns = self._store.setdefault(key, [])
            turns.append(turn)
            if len(turns) > self.max_turns:
                del turns[: len(turns) - self.max_turns]

    def history(self, key: str) -> list[Turn]:
        """Return a copy of the stored turns for ``key`` (oldest-first).

        A copy is returned so callers can pass it straight to the model without
        risking mutation of the shared store.
        """
        with self._lock:
            return [dict(turn) for turn in self._store.get(key, ())]

    def clear(self, key: str) -> None:
        """Forget all history for ``key`` (no-op if unknown)."""
        with self._lock:
            self._store.pop(key, None)
