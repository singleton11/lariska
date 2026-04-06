"""``lariska init`` — interactive onboarding."""
from __future__ import annotations

import click

from lariska.config import load_config, save_config


@click.command()
@click.option("--trello-api-key", default=None, help="Trello API key")
@click.option("--trello-token", default=None, help="Trello member token")
@click.option("--trello-list-name", default=None, help="Trello list name")
@click.pass_context
def init(
    ctx: click.Context,
    trello_api_key: str | None,
    trello_token: str | None,
    trello_list_name: str | None,
) -> None:
    """Initialise Lariska configuration interactively."""
    config_path: str | None = ctx.obj["config"]
    config = load_config(config_path)

    if trello_api_key is None:
        trello_api_key = click.prompt(
            "Trello API key",
            default=config.trello.api_key or "",
        )
    if trello_token is None:
        trello_token = click.prompt(
            "Trello token",
            default=config.trello.token or "",
        )
    if trello_list_name is None:
        trello_list_name = click.prompt(
            "Trello list name",
            default=config.trello.list_name or "To Do",
        )

    config.trello.api_key = trello_api_key
    config.trello.token = trello_token
    config.trello.list_name = trello_list_name

    save_config(config, config_path)
    click.echo("Configuration saved.")
