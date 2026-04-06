from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
import yaml

import lariska.config as _lariska_config_module

from lariska.config import Config, TrelloConfig, load_config
from lariska.hooks.base import Hook
from lariska.hooks.card_assigned import CardAssignedHook
from lariska.trello import TrelloAPIError, TrelloClient
from lariska.workflow.db import create_task, get_task_by_card_id, init_db
from lariska.workflow.runner import run_iteration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mocked_client(handler: httpx.MockTransport) -> TrelloClient:
    inner = httpx.Client(
        base_url="https://api.trello.com/1/",
        transport=handler,
        timeout=5.0,
    )
    return TrelloClient(api_key="testkey", token="testtoken", client=inner)


def _in_memory_db() -> sqlite3.Connection:
    return init_db(":memory:")


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_load_from_explicit_path(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "main.yaml"
        cfg_file.write_text(
            yaml.dump({"trello": {"member_id": "abc123", "list_name": "Inbox"}})
        )
        config = load_config(cfg_file)
        assert config.trello.member_id == "abc123"
        assert config.trello.list_name == "Inbox"

    def test_missing_file_creates_defaults(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cfg_file = tmp_path / "sub" / "main.yaml"
        monkeypatch.setattr(_lariska_config_module, "_CONFIG_FILE", cfg_file)
        monkeypatch.setattr(_lariska_config_module, "_CONFIG_DIR", cfg_file.parent)
        config = load_config(cfg_file)
        assert config.trello.member_id == "me"
        assert cfg_file.exists()

    def test_partial_config_uses_defaults(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "main.yaml"
        cfg_file.write_text(yaml.dump({"trello": {"member_id": "custom"}}))
        config = load_config(cfg_file)
        assert config.trello.member_id == "custom"
        assert config.trello.list_name == ""


# ---------------------------------------------------------------------------
# DB tests
# ---------------------------------------------------------------------------

class TestDb:
    def test_init_creates_tasks_table(self) -> None:
        conn = _in_memory_db()
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "tasks" in tables
        conn.close()

    def test_create_task_returns_id(self) -> None:
        conn = _in_memory_db()
        task_id = create_task(conn, "card-1")
        assert isinstance(task_id, int)
        assert task_id > 0
        conn.close()

    def test_create_task_default_state_is_ready(self) -> None:
        conn = _in_memory_db()
        create_task(conn, "card-2")  # return value unused; testing that row state is set correctly
        row = get_task_by_card_id(conn, "card-2")
        assert row is not None
        assert row["state"] == "ready"
        conn.close()

    def test_create_task_idempotent(self) -> None:
        conn = _in_memory_db()
        id1 = create_task(conn, "card-dup")
        id2 = create_task(conn, "card-dup")
        assert id1 == id2
        conn.close()

    def test_get_task_by_card_id_not_found(self) -> None:
        conn = _in_memory_db()
        assert get_task_by_card_id(conn, "nonexistent") is None
        conn.close()

    def test_init_db_file(self, tmp_path: Path) -> None:
        db_path = tmp_path / "tasks.db"
        conn = init_db(db_path)
        conn.close()
        assert db_path.exists()


# ---------------------------------------------------------------------------
# TrelloClient extensions
# ---------------------------------------------------------------------------

class TestTrelloClientExtensions:
    def test_get_card_returns_dict(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert "/cards/card123" in str(request.url.path)
            return httpx.Response(200, json={"id": "card123", "idList": "list1", "idBoard": "board1"})

        client = _mocked_client(httpx.MockTransport(handler))
        try:
            card = client.get_card("card123")
        finally:
            client.close()
        assert card["id"] == "card123"
        assert card["idList"] == "list1"

    def test_get_card_fields_param(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert "fields=" in str(request.url)
            return httpx.Response(200, json={"idList": "list1", "idBoard": "board1"})

        client = _mocked_client(httpx.MockTransport(handler))
        try:
            client.get_card("card1", fields="idBoard,idList,name")
        finally:
            client.close()

    def test_mark_notification_read_sends_put(self) -> None:
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["method"] = request.method
            captured["path"] = str(request.url.path)
            assert "unread=false" in str(request.url)
            return httpx.Response(200, json={"id": "notif1", "unread": False})

        client = _mocked_client(httpx.MockTransport(handler))
        try:
            client.mark_notification_read("notif1")
        finally:
            client.close()

        assert captured["method"] == "PUT"
        assert captured["path"].endswith("/notifications/notif1")

    def test_get_board_lists_returns_list(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert "/boards/board1/lists" in str(request.url.path)
            return httpx.Response(
                200, json=[{"id": "list-a", "name": "Inbox"}, {"id": "list-b", "name": "Done"}]
            )

        client = _mocked_client(httpx.MockTransport(handler))
        try:
            lists = client.get_board_lists("board1")
        finally:
            client.close()
        assert len(lists) == 2
        assert lists[0]["name"] == "Inbox"


# ---------------------------------------------------------------------------
# CardAssignedHook tests
# ---------------------------------------------------------------------------

class TestCardAssignedHook:
    def _config(self, list_name: str = "Inbox") -> Config:
        return Config(trello=TrelloConfig(member_id="me", list_name=list_name))

    def test_raises_when_list_name_not_configured(self) -> None:
        with pytest.raises(ValueError, match="list_name"):
            CardAssignedHook(self._config(list_name=""))

    def test_matches_added_to_card(self) -> None:
        hook = CardAssignedHook(self._config())
        assert hook.matches({"type": "addedToCard"}) is True

    def test_no_match_other_type(self) -> None:
        hook = CardAssignedHook(self._config())
        assert hook.matches({"type": "commentCard"}) is False

    def test_handle_creates_task_when_list_matches(self) -> None:
        notification: dict[str, Any] = {
            "type": "addedToCard",
            "data": {"card": {"id": "card-x"}},
        }

        def handler(request: httpx.Request) -> httpx.Response:
            path = str(request.url.path)
            if "/cards/card-x" in path:
                return httpx.Response(200, json={"id": "card-x", "idBoard": "board1", "idList": "list-in"})
            if "/boards/board1/lists" in path:
                return httpx.Response(200, json=[{"id": "list-in", "name": "Inbox"}])
            return httpx.Response(404, text="not found")

        client = _mocked_client(httpx.MockTransport(handler))
        conn = _in_memory_db()
        hook = CardAssignedHook(self._config(list_name="Inbox"))
        try:
            hook.handle(notification, client, conn)
        finally:
            client.close()

        row = get_task_by_card_id(conn, "card-x")
        assert row is not None
        assert row["state"] == "ready"
        conn.close()

    def test_handle_skips_wrong_list(self) -> None:
        notification: dict[str, Any] = {
            "type": "addedToCard",
            "data": {"card": {"id": "card-y"}},
        }

        def handler(request: httpx.Request) -> httpx.Response:
            path = str(request.url.path)
            if "/cards/card-y" in path:
                return httpx.Response(200, json={"id": "card-y", "idBoard": "board1", "idList": "list-other"})
            if "/boards/board1/lists" in path:
                return httpx.Response(200, json=[{"id": "list-in", "name": "Inbox"}, {"id": "list-other", "name": "Backlog"}])
            return httpx.Response(404, text="not found")

        client = _mocked_client(httpx.MockTransport(handler))
        conn = _in_memory_db()
        hook = CardAssignedHook(self._config(list_name="Inbox"))
        try:
            hook.handle(notification, client, conn)
        finally:
            client.close()

        assert get_task_by_card_id(conn, "card-y") is None
        conn.close()

    def test_handle_skips_when_list_name_not_found_on_board(self) -> None:
        notification: dict[str, Any] = {
            "type": "addedToCard",
            "data": {"card": {"id": "card-z"}},
        }

        def handler(request: httpx.Request) -> httpx.Response:
            path = str(request.url.path)
            if "/cards/card-z" in path:
                return httpx.Response(200, json={"id": "card-z", "idBoard": "board1", "idList": "list-in"})
            if "/boards/board1/lists" in path:
                return httpx.Response(200, json=[{"id": "list-in", "name": "Backlog"}])
            return httpx.Response(404, text="not found")

        client = _mocked_client(httpx.MockTransport(handler))
        conn = _in_memory_db()
        hook = CardAssignedHook(self._config(list_name="Inbox"))
        try:
            hook.handle(notification, client, conn)
        finally:
            client.close()

        assert get_task_by_card_id(conn, "card-z") is None
        conn.close()

    def test_handle_missing_card_id_skips(self) -> None:
        notification: dict[str, Any] = {"type": "addedToCard", "data": {}}
        client = MagicMock()
        conn = _in_memory_db()
        hook = CardAssignedHook(self._config())
        hook.handle(notification, client, conn)
        client.get_card.assert_not_called()
        conn.close()


# ---------------------------------------------------------------------------
# Workflow tests
# ---------------------------------------------------------------------------

class TestRunIteration:
    def _make_handler(
        self,
        notifications: list[dict[str, Any]],
        card_responses: dict[str, dict[str, Any]] | None = None,
        board_lists: list[dict[str, Any]] | None = None,
    ) -> httpx.MockTransport:
        """Build a mock transport for a full workflow run."""
        card_map = card_responses or {}
        lists = board_lists or []

        def handler(request: httpx.Request) -> httpx.Response:
            path = str(request.url.path)
            if "/members/" in path and "/notifications" in path:
                return httpx.Response(200, json=notifications)
            for card_id, card_data in card_map.items():
                if f"/cards/{card_id}" in path:
                    return httpx.Response(200, json=card_data)
            if "/boards/" in path and "/lists" in path:
                return httpx.Response(200, json=lists)
            if "/notifications/" in path and request.method == "PUT":
                return httpx.Response(200, json={"unread": False})
            return httpx.Response(404, text="not found")

        return httpx.MockTransport(handler)

    def test_empty_notifications_no_tasks(self) -> None:
        config = Config(trello=TrelloConfig(member_id="me", list_name="Inbox"))
        client = _mocked_client(self._make_handler([]))
        conn = _in_memory_db()
        try:
            run_iteration(client, config=config, conn=conn)
        finally:
            client.close()
        rows = conn.execute("SELECT * FROM tasks").fetchall()
        assert rows == []
        conn.close()

    def test_added_to_card_creates_task(self) -> None:
        notifications: list[dict[str, Any]] = [
            {
                "id": "notif-1",
                "type": "addedToCard",
                "data": {"card": {"id": "card-wf"}},
            }
        ]
        card_responses = {"card-wf": {"id": "card-wf", "idBoard": "board1", "idList": "list-in"}}
        board_lists = [{"id": "list-in", "name": "Inbox"}]
        client = _mocked_client(self._make_handler(notifications, card_responses, board_lists))
        conn = _in_memory_db()
        config = Config(trello=TrelloConfig(member_id="me", list_name="Inbox"))
        try:
            run_iteration(client, config=config, conn=conn)
        finally:
            client.close()
        row = get_task_by_card_id(conn, "card-wf")
        assert row is not None
        assert row["state"] == "ready"
        conn.close()

    def test_notification_marked_read_even_on_hook_error(self) -> None:
        """Notification is marked read even when the hook raises."""
        marked_read: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            path = str(request.url.path)
            if "/notifications" in path and request.method == "GET":
                return httpx.Response(
                    200,
                    json=[{"id": "notif-err", "type": "addedToCard", "data": {"card": {"id": "c1"}}}],
                )
            if "/cards/c1" in path:
                return httpx.Response(500, text="server error")
            if "/notifications/notif-err" in path and request.method == "PUT":
                marked_read.append("notif-err")
                return httpx.Response(200, json={"unread": False})
            return httpx.Response(404, text="not found")

        client = _mocked_client(httpx.MockTransport(handler))
        conn = _in_memory_db()
        config = Config(trello=TrelloConfig(member_id="me", list_name="Inbox"))
        try:
            run_iteration(client, config=config, conn=conn)
        finally:
            client.close()
        assert "notif-err" in marked_read
        conn.close()
