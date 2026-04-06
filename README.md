# Lariska — agent orchestrator

[![codecov](https://codecov.io/gh/singleton11/lariska/branch/main/graph/badge.svg)](https://codecov.io/gh/singleton11/lariska)

## Trello notifications

Set `TRELLO_API_KEY` and `TRELLO_TOKEN` (member token from [Trello Power-Up / API key admin](https://trello.com/power-ups/admin)). The members notifications endpoint does not work for Forge/OAuth2-only app credentials; use API key plus user token.

Copy the environment template and fill in your credentials:

```
cp .env.example .env
```

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
