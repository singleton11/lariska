from __future__ import annotations

import logging
import sqlite3
from typing import Any

from lariska.config import Config
from lariska.db import create_task
from lariska.trello.client import TrelloClient

logger = logging.getLogger(__name__)

_NOTIFICATION_TYPE = "addedToCard"


class CardAssignedHook:
    """Hook that fires when the configured member is assigned to a Trello card.

    It verifies that the card is in the configured list, then creates (or
    no-ops if already present) a task in the database with state ``'ready'``.
    """

    def __init__(self, config: Config) -> None:
        self._config = config

    def matches(self, notification: dict[str, Any]) -> bool:
        return notification.get("type") == _NOTIFICATION_TYPE

    def handle(
        self,
        notification: dict[str, Any],
        client: TrelloClient,
        conn: sqlite3.Connection,
    ) -> None:
        data = notification.get("data", {})
        card_data = data.get("card", {})
        card_id = card_data.get("id")
        if not card_id:
            logger.warning("addedToCard notification missing card id, skipping")
            return

        card = client.get_card(card_id, fields="idList,name")
        card_list_id = card.get("idList", "")

        configured_list_id = self._config.trello.list_id
        if configured_list_id and card_list_id != configured_list_id:
            logger.debug(
                "Card %s is in list %s, not the configured list %s — skipping",
                card_id,
                card_list_id,
                configured_list_id,
            )
            return

        task_id = create_task(conn, card_id, state="ready")
        logger.info(
            "Task %d created/found for card %s (state=ready)", task_id, card_id
        )
