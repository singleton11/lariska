from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_CONFIG_DIR = Path.home() / ".lariska" / "config"
_PROVIDERS_FILE = _CONFIG_DIR / "providers.yaml"


@dataclass
class ProviderConfig:
    type: str
    endpoint: str
    api_key: str


@dataclass
class ProvidersConfig:
    providers: list[ProviderConfig] = field(default_factory=list)


def _providers_to_dict(config: ProvidersConfig) -> dict[str, Any]:
    """Convert a :class:`ProvidersConfig` instance to a plain dict suitable for YAML."""
    return {
        "providers": [
            {
                "type": p.type,
                "endpoint": p.endpoint,
                "api_key": p.api_key,
            }
            for p in config.providers
        ]
    }


def load_providers(path: str | Path | None = None) -> ProvidersConfig:
    """Load providers from *path* (defaults to ``~/.lariska/config/providers.yaml``).

    If the file does not exist an empty :class:`ProvidersConfig` is returned.
    """
    providers_path = Path(path) if path is not None else _PROVIDERS_FILE
    if not providers_path.exists():
        return ProvidersConfig()

    with providers_path.open() as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}

    providers = [
        ProviderConfig(
            type=p.get("type", ""),
            endpoint=p.get("endpoint", ""),
            api_key=p.get("api_key", ""),
        )
        for p in raw.get("providers", [])
    ]
    return ProvidersConfig(providers=providers)


def save_providers(config: ProvidersConfig, path: str | Path | None = None) -> None:
    """Persist *config* to *path* (defaults to ``~/.lariska/config/providers.yaml``)."""
    providers_path = Path(path) if path is not None else _PROVIDERS_FILE
    providers_path.parent.mkdir(parents=True, exist_ok=True)
    with providers_path.open("w") as fh:
        yaml.dump(_providers_to_dict(config), fh, default_flow_style=False)


def add_provider(
    provider_type: str,
    endpoint: str,
    api_key: str,
    path: str | Path | None = None,
) -> ProviderConfig:
    """Add a new LLM provider entry and persist it.

    Returns the newly created :class:`ProviderConfig`.
    """
    config = load_providers(path)
    provider = ProviderConfig(type=provider_type, endpoint=endpoint, api_key=api_key)
    config.providers.append(provider)
    save_providers(config, path)
    return provider
