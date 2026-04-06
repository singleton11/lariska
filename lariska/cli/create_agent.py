"""``lariska create-agent`` — scaffold a new agent workspace."""
from __future__ import annotations

import sys

import click

from lariska.agents import create_agent as _create_agent_workspace


@click.command("create-agent")
@click.option("--name", default=None, help="Agent name (required)")
def create_agent(name: str | None) -> None:
    """Create a new agent workspace."""
    if name is None:
        name = click.prompt("Agent name")

    try:
        workspace = _create_agent_workspace(name)
    except (FileExistsError, ValueError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Agent '{name}' created at {workspace}")
