"""``lariska add-provider`` — register a new LLM provider."""
from __future__ import annotations

import click

from lariska.providers import add_provider as _add_provider


@click.command("add-provider")
@click.option("--type", "provider_type", default=None, help="Provider type (e.g. OpenAI)")
@click.option("--endpoint", default=None, help="Provider API endpoint URL")
@click.option("--api-key", default=None, help="Provider API key")
@click.pass_context
def add_provider(
    ctx: click.Context,
    provider_type: str | None,
    endpoint: str | None,
    api_key: str | None,
) -> None:
    """Add a new LLM provider to providers.yaml."""
    if provider_type is None:
        provider_type = click.prompt("Provider type (e.g. OpenAI)")
    if endpoint is None:
        endpoint = click.prompt("Endpoint URL")
    if api_key is None:
        api_key = click.prompt("API key")

    providers_path: str | None = ctx.obj.get("providers") if ctx.obj else None
    _add_provider(provider_type, endpoint, api_key, path=providers_path)
    click.echo(f"Provider '{provider_type}' added.")
