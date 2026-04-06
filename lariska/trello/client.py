from __future__ import annotations

import os
from typing import Any

import httpx


class TrelloAPIError(Exception):
    """Raised when Trello returns a non-success status or the body cannot be parsed as expected."""

    def __init__(
        self,
        status_code: int,
        *,
        body: str | None = None,
        detail: Any = None,
    ) -> None:
        self.status_code = status_code
        self.body = body
        self.detail = detail
        msg = f"Trello API error {status_code}"
        if body:
            msg = f"{msg}: {body[:500]}{'…' if body and len(body) > 500 else ''}"
        super().__init__(msg)


class TrelloClient:
    """Thin HTTP client for Trello REST API v1 (API key + member token)."""

    DEFAULT_BASE = "https://api.trello.com/1/"

    def __init__(
        self,
        api_key: str | None = None,
        token: str | None = None,
        *,
        base_url: str = DEFAULT_BASE,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get("TRELLO_API_KEY", "")
        self.token = token if token is not None else os.environ.get("TRELLO_TOKEN", "")
        if not self.api_key or not self.token:
            raise ValueError("TRELLO_API_KEY and TRELLO_TOKEN (or constructor arguments) are required")

        self._base_url = base_url if base_url.endswith("/") else f"{base_url}/"
        self._owns_client = client is None
        self._client = client or httpx.Client(base_url=self._base_url, timeout=timeout)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> TrelloClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _auth_params(self) -> dict[str, str]:
        return {"key": self.api_key, "token": self.token}

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        params = dict(kwargs.pop("params") or {})
        params = {**self._auth_params(), **params}
        response = self._client.request(method, path, params=params, **kwargs)
        if response.status_code >= 400:
            detail: Any = None
            try:
                detail = response.json()
            except ValueError:
                pass
            raise TrelloAPIError(
                response.status_code,
                body=response.text,
                detail=detail,
            )
        return response

    def get_json(self, path: str, **kwargs: Any) -> Any:
        response = self.request("GET", path, **kwargs)
        try:
            return response.json()
        except ValueError as exc:
            raise TrelloAPIError(
                response.status_code,
                body=response.text,
                detail=None,
            ) from exc

    def get_card(self, card_id: str, fields: str | None = None) -> dict[str, Any]:
        """Fetch a single card by ID.  Returns the card JSON as a dict.

        Args:
            card_id: The Trello card ID.
            fields: Optional comma-separated list of card fields to include
                (e.g. ``"idList,name"``).  When omitted, Trello returns a
                default set of fields.
        """
        params: dict[str, str] = {}
        if fields is not None:
            params["fields"] = fields
        data = self.get_json(f"cards/{card_id}", params=params)
        if not isinstance(data, dict):
            raise TrelloAPIError(200, body=repr(data), detail=data)
        return data

    def mark_notification_read(self, notification_id: str) -> None:
        """Mark a single notification as read (``unread=false``)."""
        self.request("PUT", f"notifications/{notification_id}", params={"unread": "false"})

    def get_board_lists(self, board_id: str) -> list[dict[str, Any]]:
        """Return all lists on a board as a list of dicts (each with ``id`` and ``name``)."""
        data = self.get_json(f"boards/{board_id}/lists", params={"fields": "id,name"})
        if not isinstance(data, list):
            raise TrelloAPIError(200, body=repr(data), detail=data)
        return data
