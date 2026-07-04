"""Conversation memory for Open Claw agents, with optional disk persistence.

Agents need to hold multi-turn context in DMs and threads instead of replying
one-shot. ``ConversationStore`` keeps a bounded, per-conversation history keyed
by an opaque string (typically a Slack channel id, optionally combined with a
thread timestamp).

The store is thread-safe (all mutations are guarded by a ``threading.Lock``) so
it is safe to share across the threaded orchestrator. When constructed with a
``path`` it also persists to a JSON file: history is loaded on start and written
back atomically after every mutation, so memory survives process restarts. With
no ``path`` the store stays purely in-memory (and trivially unit-testable).
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

Role = str  # "user" | "assistant"
Turn = dict[str, str]  # {"role": Role, "content": str}

DEFAULT_MAX_TURNS = 12
_PERSIST_VERSION = 1


@dataclass
class ConversationStore:
    """Bounded per-conversation history, thread-safe and optionally persistent.

    Each conversation key maps to a list of turns ordered oldest-first. Only the
    ``max_turns`` most recent turns are retained per key; older turns are trimmed
    as new ones arrive. When ``path`` is set, the whole store is mirrored to that
    JSON file after every mutation and reloaded from it on construction.
    """

    max_turns: int = DEFAULT_MAX_TURNS
    path: Path | None = None
    _store: dict[str, list[Turn]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        if self.max_turns < 1:
            raise ValueError("max_turns must be >= 1")
        if self.path is not None:
            self.path = Path(self.path)
            self._load()

    # -- persistence ---------------------------------------------------------

    def _load(self) -> None:
        """Populate the store from ``path`` if it exists; tolerate corruption."""
        if self.path is None or not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            log.warning("Could not read memory at %s; starting empty", self.path)
            return
        conversations = raw.get("conversations", {}) if isinstance(raw, dict) else {}
        cleaned: dict[str, list[Turn]] = {}
        for key, turns in conversations.items():
            if not isinstance(turns, list):
                continue
            kept = [
                {"role": str(t["role"]), "content": str(t["content"])}
                for t in turns
                if isinstance(t, dict) and "role" in t and "content" in t
            ]
            if kept:
                cleaned[str(key)] = kept[-self.max_turns :]
        self._store = cleaned

    def _snapshot(self) -> dict[str, list[Turn]]:
        """A deep copy of the store, safe to hand off for writing outside the lock."""
        return {k: [dict(t) for t in v] for k, v in self._store.items()}

    def _persist(self, snapshot: dict[str, list[Turn]]) -> None:
        """Atomically write ``snapshot`` to ``path`` (temp file + os.replace)."""
        if self.path is None:
            return
        payload = json.dumps(
            {"version": _PERSIST_VERSION, "conversations": snapshot}, ensure_ascii=False
        )
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".mem-", suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp, self.path)
        except OSError:
            log.exception("Failed to persist memory to %s", self.path)

    def save(self) -> None:
        """Force a persist to disk (no-op when the store has no ``path``)."""
        with self._lock:
            snap = self._snapshot() if self.path is not None else None
        if snap is not None:
            self._persist(snap)

    # -- mutation / reads ----------------------------------------------------

    def add(self, key: str, role: Role, content: str) -> None:
        """Append a turn for ``key``, trim to ``max_turns``, and persist if backed."""
        turn: Turn = {"role": role, "content": content}
        with self._lock:
            turns = self._store.setdefault(key, [])
            turns.append(turn)
            if len(turns) > self.max_turns:
                del turns[: len(turns) - self.max_turns]
            snap = self._snapshot() if self.path is not None else None
        if snap is not None:
            self._persist(snap)

    def history(self, key: str) -> list[Turn]:
        """Return a copy of the stored turns for ``key`` (oldest-first)."""
        with self._lock:
            return [dict(turn) for turn in self._store.get(key, ())]

    def history_for(self, keys: list[str]) -> list[Turn]:
        """Concatenate history across ``keys`` in order, de-duplicating keys.

        Used so a thread inherits its parent channel's history: pass
        ``[channel, channel:thread_ts]`` and the parent channel turns come first,
        followed by the thread's own turns.
        """
        out: list[Turn] = []
        seen: set[str] = set()
        with self._lock:
            for key in keys:
                if key in seen:
                    continue
                seen.add(key)
                out.extend(dict(turn) for turn in self._store.get(key, ()))
        return out

    def clear(self, key: str) -> None:
        """Forget all history for ``key`` (no-op if unknown); persist if backed."""
        with self._lock:
            self._store.pop(key, None)
            snap = self._snapshot() if self.path is not None else None
        if snap is not None:
            self._persist(snap)
