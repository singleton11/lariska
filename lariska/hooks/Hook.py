from __future__ import annotations

import sqlite3
from typing import Any, Protocol

from lariska.trello.client import TrelloClient


class Hook(Protocol):
    """Interface every hook must implement."""

    def matches(self, notification: dict[str, Any]) -> bool:
        """Return ``True`` when this hook should handle *notification*."""
        ...

    def handle(
        self,
        notification: dict[str, Any],
        client: TrelloClient,
        conn: sqlite3.Connection,
    ) -> None:
        """Process *notification* (side-effects only)."""
        ...
