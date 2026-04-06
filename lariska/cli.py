"""Lariska command-line interface."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

from lariska.agents import create_agent
from lariska.config import Config, TrelloConfig, load_config, save_config


def _prompt(label: str, *, default: str | None = None, required: bool = True) -> str:
    """Prompt the user for a value on *stdin*.

    When *default* is set the prompt shows ``[default]`` and pressing Enter
    returns that value.  If *required* is ``True`` the prompt repeats until a
    non-empty value is given.
    """
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if not value and default is not None:
            return default
        if value or not required:
            return value
        print("  This field is required. Please enter a value.")


# -- init --------------------------------------------------------------------

def _do_init(args: argparse.Namespace) -> None:
    """Run the ``init`` subcommand."""
    config_path: str | None = getattr(args, "config", None)
    config = load_config(config_path)

    api_key: str | None = args.api_key
    token: str | None = args.token
    list_name: str | None = args.list_name

    if api_key is None:
        api_key = _prompt(
            "Trello API key",
            default=config.trello.api_key or None,
        )
    if token is None:
        token = _prompt(
            "Trello token",
            default=config.trello.token or None,
        )
    if list_name is None:
        list_name = _prompt(
            "Trello list name",
            default=config.trello.list_name or "To Do",
        )

    config.trello.api_key = api_key
    config.trello.token = token
    config.trello.list_name = list_name

    save_config(config, config_path)
    print("Configuration saved.")


# -- create-agent ------------------------------------------------------------

def _do_create_agent(args: argparse.Namespace) -> None:
    """Run the ``create-agent`` subcommand."""
    name: str | None = args.name

    if name is None:
        name = _prompt("Agent name", required=True)

    try:
        workspace = create_agent(name)
    except (FileExistsError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Agent '{name}' created at {workspace}")


# -- run ---------------------------------------------------------------------

def _do_run(args: argparse.Namespace) -> None:
    """Run the ``run`` subcommand (default workflow iteration)."""
    from dotenv import load_dotenv

    from lariska.trello.client import TrelloClient
    from lariska.workflow.runner import run_iteration

    load_dotenv()

    config_path: str | None = getattr(args, "config", None)
    config = load_config(config_path)

    api_key = config.trello.api_key or None
    token = config.trello.token or None

    with TrelloClient(api_key=api_key, token=token) as client:
        run_iteration(client, config=config)


# -- entry point -------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="lariska",
        description="Lariska — agent orchestrator",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to configuration file (default: ~/.lariska/config/main.yaml)",
    )

    subparsers = parser.add_subparsers(dest="command")

    # -- init ----------------------------------------------------------------
    init_parser = subparsers.add_parser(
        "init",
        help="Initialise Lariska configuration interactively",
    )
    init_parser.add_argument("--api-key", default=None, help="Trello API key")
    init_parser.add_argument("--token", default=None, help="Trello member token")
    init_parser.add_argument("--list-name", default=None, help="Trello list name")

    # -- create-agent --------------------------------------------------------
    agent_parser = subparsers.add_parser(
        "create-agent",
        help="Create a new agent workspace",
    )
    agent_parser.add_argument("--name", default=None, help="Agent name (required)")

    # -- run -----------------------------------------------------------------
    subparsers.add_parser(
        "run",
        help="Run one workflow iteration (default)",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    handlers: dict[str | None, Callable[[argparse.Namespace], None]] = {
        "init": _do_init,
        "create-agent": _do_create_agent,
        "run": _do_run,
        None: lambda _: parser.print_help(),
    }

    handler = handlers.get(args.command, lambda _: parser.print_help())
    handler(args)
