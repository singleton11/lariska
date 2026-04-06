"""Lariska command-line interface."""
from __future__ import annotations

import logging

import click

from lariska.cli.create_agent import create_agent
from lariska.cli.init_cmd import init
from lariska.cli.run import run


@click.group(invoke_without_command=True)
@click.option(
    "--config",
    default=None,
    type=click.Path(),
    help="Path to configuration file (default: ~/.lariska/config/main.yaml)",
)
@click.pass_context
def cli(ctx: click.Context, config: str | None) -> None:
    """Lariska — agent orchestrator."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


cli.add_command(init)
cli.add_command(create_agent)
cli.add_command(run)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    cli(args=argv, standalone_mode=True)
