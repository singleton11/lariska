from __future__ import annotations

from typing import Any, Literal

from .client import TrelloAPIError, TrelloClient

ReadFilter = Literal["all", "read", "unread"]


def fetch_member_notifications(
    client: TrelloClient,
    member_id: str = "me",
    *,
    read_filter: ReadFilter | None = None,
    filter: str | None = None,
    limit: int | None = None,
    page: int | None = None,
    before: str | None = None,
    since: str | None = None,
    fields: str | None = None,
    entities: bool | None = None,
    display: bool | None = None,
    member_creator: bool | None = None,
) -> list[dict[str, Any]]:
    """
    GET /1/members/{id}/notifications — requires API key + member token (not Forge/OAuth2-only apps).

    Pagination: use ``since`` / ``before`` (ISO date strings per Trello) or ``page`` with ``limit``.
    """
    params: dict[str, str | int | bool] = {}
    if read_filter is not None:
        params["read_filter"] = read_filter
    if filter is not None:
        params["filter"] = filter
    if limit is not None:
        params["limit"] = limit
    if page is not None:
        params["page"] = page
    if before is not None:
        params["before"] = before
    if since is not None:
        params["since"] = since
    if fields is not None:
        params["fields"] = fields
    if entities is not None:
        params["entities"] = entities
    if display is not None:
        params["display"] = display
    if member_creator is not None:
        params["memberCreator"] = member_creator

    path = f"members/{member_id}/notifications"
    data = client.get_json(path, params=params)
    if not isinstance(data, list):
        raise TrelloAPIError(
            200,
            body=repr(data),
            detail=data,
        )
    return data
