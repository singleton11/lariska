"""``lariska run`` — execute one workflow iteration."""
from __future__ import annotations

import click

from lariska.config import load_config


@click.command()
@click.pass_context
def run(ctx: click.Context) -> None:
    """Run one workflow iteration."""
    from dotenv import load_dotenv

    from lariska.trello.client import TrelloClient
    from lariska.workflow.runner import run_iteration

    load_dotenv()

    config_path: str | None = ctx.obj["config"]
    config = load_config(config_path)

    api_key = config.trello.api_key or None
    token = config.trello.token or None

    with TrelloClient(api_key=api_key, token=token) as client:
        run_iteration(client, config=config)
