from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_CONFIG_DIR = Path.home() / ".lariska" / "config"
_CONFIG_FILE = _CONFIG_DIR / "main.yaml"

_DEFAULT_CONFIG: dict[str, Any] = {
    "trello": {
        "member_id": "me",
        "list_name": "",
    }
}


@dataclass
class TrelloConfig:
    member_id: str = "me"
    list_name: str = ""


@dataclass
class Config:
    trello: TrelloConfig = field(default_factory=TrelloConfig)


def _write_default_config(config_path: Path) -> None:
    """Write the default configuration to *config_path*, creating parent dirs."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w") as fh:
        yaml.dump(_DEFAULT_CONFIG, fh, default_flow_style=False)


def load_config(path: str | Path | None = None) -> Config:
    """Load configuration from *path* (defaults to ``~/.lariska/config/main.yaml``).

    If the file does not exist it is created with the built-in defaults at
    *path* (or at the default location when *path* is ``None``).
    """
    config_path = Path(path) if path is not None else _CONFIG_FILE
    if not config_path.exists():
        _write_default_config(config_path)

    with config_path.open() as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}

    trello_raw = raw.get("trello", {})
    trello = TrelloConfig(
        member_id=trello_raw.get("member_id", "me"),
        list_name=trello_raw.get("list_name", ""),
    )
    return Config(trello=trello)
