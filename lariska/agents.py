"""Agent workspace management for Lariska."""
from __future__ import annotations

from pathlib import Path

_AGENTS_DIR = Path.home() / ".lariska" / "agents"

_AGENT_MD = """\
# Agent memory

<!-- This file stores the agent's memory and context. -->
"""

_SOUL_MD = """\
# Agent identity

<!-- This file describes the agent's identity and behaviour. -->
"""

_USER_MD = """\
# User info

<!-- This file stores information about the user. -->
"""


def get_agents_dir() -> Path:
    """Return the base directory for all agent workspaces."""
    return _AGENTS_DIR


def create_agent(name: str, *, agents_dir: Path | None = None) -> Path:
    """Create a new agent workspace and return the workspace path.

    The workspace contains:
    - ``AGENT.md``  – agent memory
    - ``SOUL.md``   – agent identity
    - ``USER.md``   – user information
    - ``skills/``   – skill modules

    Raises:
        FileExistsError: If an agent with *name* already exists.
        ValueError: If *name* is empty.
    """
    if not name or not name.strip():
        raise ValueError("Agent name must not be empty")

    base = agents_dir if agents_dir is not None else _AGENTS_DIR
    workspace = base / name

    if workspace.exists():
        raise FileExistsError(f"Agent '{name}' already exists at {workspace}")

    workspace.mkdir(parents=True)
    (workspace / "AGENT.md").write_text(_AGENT_MD)
    (workspace / "SOUL.md").write_text(_SOUL_MD)
    (workspace / "USER.md").write_text(_USER_MD)
    (workspace / "skills").mkdir()

    return workspace
