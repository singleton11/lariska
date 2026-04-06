# Lariska — agent orchestrator

[![codecov](https://codecov.io/gh/singleton11/lariska/branch/main/graph/badge.svg)](https://codecov.io/gh/singleton11/lariska)

Agent orchestrator that uses Trello as UI.

## Lariska CLI

For now it's only possible to use version built from sources

For onboarding, run:

```
uv run lariska init
```

to add an agent:

```
uv run lariska create-agent
```

for additional info you can use `--help` flag:

```
uv run lariska --help
```

## How to obtain credentials

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
