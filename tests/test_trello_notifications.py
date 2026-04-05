from __future__ import annotations

import httpx
import pytest

from lariska.trello import TrelloAPIError, TrelloClient, fetch_member_notifications


def _mocked_client(handler: httpx.MockTransport) -> TrelloClient:
    inner = httpx.Client(
        base_url="https://api.trello.com/1/",
        transport=handler,
        timeout=5.0,
    )
    return TrelloClient(api_key="testkey", token="testtoken", client=inner)


def test_fetch_notifications_success_includes_auth_and_params() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = str(request.url.path)
        q = str(request.url)
        assert "key=testkey" in q
        assert "token=testtoken" in q
        assert "read_filter=unread" in q
        assert "limit=10" in q
        return httpx.Response(200, json=[{"id": "n1", "unread": True}])

    client = _mocked_client(httpx.MockTransport(handler))
    try:
        out = fetch_member_notifications(
            client,
            read_filter="unread",
            limit=10,
        )
    finally:
        client.close()

    assert captured["path"].endswith("/members/me/notifications")
    assert out == [{"id": "n1", "unread": True}]


def test_fetch_notifications_member_creator_query_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        q = str(request.url)
        assert "memberCreator=true" in q
        return httpx.Response(200, json=[])

    client = _mocked_client(httpx.MockTransport(handler))
    try:
        fetch_member_notifications(client, member_creator=True)
    finally:
        client.close()


def test_401_raises_trello_api_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "invalid key"})

    client = _mocked_client(httpx.MockTransport(handler))
    try:
        with pytest.raises(TrelloAPIError) as exc_info:
            fetch_member_notifications(client)
    finally:
        client.close()

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == {"message": "invalid key"}


def test_429_raises_trello_api_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    client = _mocked_client(httpx.MockTransport(handler))
    try:
        with pytest.raises(TrelloAPIError) as exc_info:
            fetch_member_notifications(client)
    finally:
        client.close()

    assert exc_info.value.status_code == 429


def test_invalid_json_on_success_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    client = _mocked_client(httpx.MockTransport(handler))
    try:
        with pytest.raises(TrelloAPIError) as exc_info:
            fetch_member_notifications(client)
    finally:
        client.close()

    assert exc_info.value.status_code == 200
    assert "not json" in (exc_info.value.body or "")


def test_non_list_json_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": True})

    client = _mocked_client(httpx.MockTransport(handler))
    try:
        with pytest.raises(TrelloAPIError) as exc_info:
            fetch_member_notifications(client)
    finally:
        client.close()

    assert exc_info.value.status_code == 200
    assert exc_info.value.detail == {"unexpected": True}


def test_client_requires_credentials() -> None:
    with pytest.raises(ValueError, match="TRELLO_API_KEY"):
        TrelloClient(api_key="", token="")
