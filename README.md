# Lariska — agent orchestrator

## Trello notifications

Set `TRELLO_API_KEY` and `TRELLO_TOKEN` (member token from [Trello Power-Up / API key admin](https://trello.com/power-ups/admin)). The members notifications endpoint does not work for Forge/OAuth2-only app credentials; use API key plus user token.

## Test and run


### Install

```
uv sync --extra dev
```

### Run

```
uv run lariska
```

### Test

```
uv run pytest
```
