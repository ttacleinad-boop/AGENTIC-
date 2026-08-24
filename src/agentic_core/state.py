from __future__ import annotations

from collections import defaultdict, deque
from typing import Protocol

from .models import Checkpoint


class CheckpointStore(Protocol):
    def append(self, checkpoint: Checkpoint) -> None: ...

    def latest(self, task_id: str) -> Checkpoint | None: ...

    def history(self, task_id: str) -> list[Checkpoint]: ...


class InMemoryCheckpointStore:
    """Deterministic local adapter; replace with PostgreSQL or Redis at installation time."""

    def __init__(self) -> None:
        self._history: dict[str, list[Checkpoint]] = defaultdict(list)

    def append(self, checkpoint: Checkpoint) -> None:
        history = self._history[checkpoint.task_id]
        if history and checkpoint.sequence != history[-1].sequence + 1:
            raise ValueError("checkpoint sequence must be monotonic per task")
        if not history and checkpoint.sequence != 1:
            raise ValueError("first checkpoint sequence must be 1")
        history.append(checkpoint)

    def latest(self, task_id: str) -> Checkpoint | None:
        history = self._history.get(task_id, [])
        return history[-1] if history else None

    def history(self, task_id: str) -> list[Checkpoint]:
        return list(self._history.get(task_id, []))


class LongTermMemory(Protocol):
    def retrieve(self, query: str, limit: int = 5) -> list[str]: ...

    def remember(self, text: str) -> None: ...


class DisabledLongTermMemory:
    """Safe default that stores no external data until an adapter is installed."""

    def retrieve(self, query: str, limit: int = 5) -> list[str]:
        return []

    def remember(self, text: str) -> None:
        return None


class SessionMemory:
    def __init__(self, window_size: int) -> None:
        self._window_size = window_size
        self._messages: dict[str, deque[str]] = defaultdict(lambda: deque(maxlen=window_size))

    def add(self, task_id: str, message: str) -> None:
        self._messages[task_id].append(message)

    def snapshot(self, task_id: str) -> list[str]:
        return list(self._messages.get(task_id, []))

    def restore(self, task_id: str, messages: list[str]) -> None:
        self._messages[task_id] = deque(messages[-self._window_size :], maxlen=self._window_size)
