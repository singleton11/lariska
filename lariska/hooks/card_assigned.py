from __future__ import annotations

import logging
import sqlite3
from typing import Any

from lariska.config import Config
from lariska.trello.client import TrelloClient
from lariska.workflow.db import create_task

logger = logging.getLogger(__name__)

_NOTIFICATION_TYPE = "addedToCard"


class CardAssignedHook:
    """Hook that fires when the configured member is assigned to a Trello card.

    It verifies that the card is in the configured list (matched by name), then
    creates (or no-ops if already present) a task in the database with state
    ``'ready'``.

    Raises:
        ValueError: On construction if ``config.trello.list_name`` is not set.
    """

    def __init__(self, config: Config) -> None:
        if not config.trello.list_name:
            raise ValueError(
                "trello.list_name must be set in the configuration file"
            )
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

        card = client.get_card(card_id, fields="idBoard,idList,name")
        board_id = card.get("idBoard", "")
        card_list_id = card.get("idList", "")

        if not board_id:
            logger.warning("Card %s has no idBoard, skipping", card_id)
            return

        board_lists = client.get_board_lists(board_id)
        target_list = next(
            (lst for lst in board_lists if lst.get("name") == self._config.trello.list_name),
            None,
        )

        if target_list is None:
            logger.debug(
                "List named %r not found on board %s — skipping",
                self._config.trello.list_name,
                board_id,
            )
            return

        if card_list_id != target_list["id"]:
            logger.debug(
                "Card %s is in list %s, not %r (%s) — skipping",
                card_id,
                card_list_id,
                self._config.trello.list_name,
                target_list["id"],
            )
            return

        task_id = create_task(conn, card_id, state="ready")
        logger.info(
            "Task %d created/found for card %s (state=ready)", task_id, card_id
        )
