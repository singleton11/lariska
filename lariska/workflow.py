from __future__ import annotations

import logging
import sqlite3
from typing import Any

from lariska.config import Config, load_config
from lariska.db import init_db
from lariska.hooks import Hook
from lariska.hooks.card_assigned import CardAssignedHook
from lariska.trello.client import TrelloAPIError, TrelloClient
from lariska.trello.notifications import fetch_member_notifications

logger = logging.getLogger(__name__)


def _build_hooks(config: Config) -> list[Hook]:
    return [CardAssignedHook(config)]


def run_iteration(
    client: TrelloClient,
    *,
    config: Config | None = None,
    conn: sqlite3.Connection | None = None,
    hooks: list[Hook] | None = None,
) -> None:
    """Run one complete workflow iteration.

    1. Fetch all unread notifications for the authenticated member.
    2. Process each notification through every matching hook.
    3. Mark the notification as read.

    *config*, *conn*, and *hooks* may be injected for testing; when omitted
    they are created from the environment / default paths.
    """
    if config is None:
        config = load_config()

    _owns_conn = conn is None
    if conn is None:
        conn = init_db()

    if hooks is None:
        hooks = _build_hooks(config)

    try:
        notifications: list[dict[str, Any]] = fetch_member_notifications(
            client,
            member_id=config.trello.member_id,
            read_filter="unread",
        )
        logger.info("Fetched %d unread notification(s)", len(notifications))

        for notification in notifications:
            notification_id: str = notification.get("id", "")
            try:
                for hook in hooks:
                    if hook.matches(notification):
                        hook.handle(notification, client, conn)
            except Exception:
                logger.exception(
                    "Error processing notification %s", notification_id
                )
            finally:
                if notification_id:
                    try:
                        client.mark_notification_read(notification_id)
                    except TrelloAPIError:
                        logger.exception(
                            "Failed to mark notification %s as read", notification_id
                        )
    finally:
        if _owns_conn:
            conn.close()
