from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from click.testing import CliRunner

from lariska.agents import create_agent
from lariska.cli import cli
from lariska.config import Config, TrelloConfig, load_config, save_config


# ---------------------------------------------------------------------------
# Config: save_config / load_config round-trip
# ---------------------------------------------------------------------------

class TestSaveConfig:
    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "main.yaml"
        config = Config(
            trello=TrelloConfig(
                api_key="key123",
                token="tok456",
                member_id="me",
                list_name="Inbox",
            )
        )
        save_config(config, cfg_file)
        loaded = load_config(cfg_file)
        assert loaded.trello.api_key == "key123"
        assert loaded.trello.token == "tok456"
        assert loaded.trello.member_id == "me"
        assert loaded.trello.list_name == "Inbox"

    def test_save_creates_parent_directories(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "deep" / "nested" / "main.yaml"
        save_config(Config(), cfg_file)
        assert cfg_file.exists()

    def test_default_config_includes_api_key_and_token(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "main.yaml"
        load_config(cfg_file)
        with cfg_file.open() as fh:
            raw = yaml.safe_load(fh)
        assert "api_key" in raw["trello"]
        assert "token" in raw["trello"]


# ---------------------------------------------------------------------------
# Agent workspace creation
# ---------------------------------------------------------------------------

class TestCreateAgent:
    def test_creates_workspace_structure(self, tmp_path: Path) -> None:
        workspace = create_agent("test-agent", agents_dir=tmp_path)
        assert workspace == tmp_path / "test-agent"
        assert (workspace / "AGENT.md").is_file()
        assert (workspace / "SOUL.md").is_file()
        assert (workspace / "USER.md").is_file()
        assert (workspace / "skills").is_dir()

    def test_agent_md_has_content(self, tmp_path: Path) -> None:
        workspace = create_agent("a1", agents_dir=tmp_path)
        content = (workspace / "AGENT.md").read_text()
        assert "memory" in content.lower()

    def test_soul_md_has_content(self, tmp_path: Path) -> None:
        workspace = create_agent("a2", agents_dir=tmp_path)
        content = (workspace / "SOUL.md").read_text()
        assert "identity" in content.lower()

    def test_user_md_has_content(self, tmp_path: Path) -> None:
        workspace = create_agent("a3", agents_dir=tmp_path)
        content = (workspace / "USER.md").read_text()
        assert "user" in content.lower()

    def test_duplicate_agent_raises(self, tmp_path: Path) -> None:
        create_agent("dup", agents_dir=tmp_path)
        with pytest.raises(FileExistsError, match="dup"):
            create_agent("dup", agents_dir=tmp_path)

    def test_empty_name_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="empty"):
            create_agent("", agents_dir=tmp_path)

    def test_whitespace_name_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="empty"):
            create_agent("   ", agents_dir=tmp_path)


# ---------------------------------------------------------------------------
# CLI: init subcommand
# ---------------------------------------------------------------------------

class TestInitCommand:
    def test_non_interactive_init(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "main.yaml"
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(cfg_file),
            "init",
            "--trello-api-key", "mykey",
            "--trello-token", "mytoken",
            "--trello-list-name", "My List",
        ])
        assert result.exit_code == 0
        config = load_config(cfg_file)
        assert config.trello.api_key == "mykey"
        assert config.trello.token == "mytoken"
        assert config.trello.list_name == "My List"

    def test_interactive_init(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "main.yaml"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--config", str(cfg_file), "init"],
            input="ikey\nitok\nMy Board\n",
        )
        assert result.exit_code == 0
        config = load_config(cfg_file)
        assert config.trello.api_key == "ikey"
        assert config.trello.token == "itok"
        assert config.trello.list_name == "My Board"

    def test_interactive_init_uses_existing_defaults(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "main.yaml"
        save_config(
            Config(trello=TrelloConfig(api_key="old", token="old", list_name="Old")),
            cfg_file,
        )
        runner = CliRunner()
        # User presses Enter for all prompts → keeps existing values
        result = runner.invoke(
            cli,
            ["--config", str(cfg_file), "init"],
            input="\n\n\n",
        )
        assert result.exit_code == 0
        config = load_config(cfg_file)
        assert config.trello.api_key == "old"
        assert config.trello.token == "old"
        assert config.trello.list_name == "Old"


# ---------------------------------------------------------------------------
# CLI: create-agent subcommand
# ---------------------------------------------------------------------------

class TestCreateAgentCommand:
    def test_non_interactive_create_agent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import lariska.agents as _agents_module
        monkeypatch.setattr(_agents_module, "_AGENTS_DIR", tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["create-agent", "--name", "bot1"])
        assert result.exit_code == 0
        assert (tmp_path / "bot1" / "AGENT.md").is_file()

    def test_interactive_create_agent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import lariska.agents as _agents_module
        monkeypatch.setattr(_agents_module, "_AGENTS_DIR", tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["create-agent"], input="bot2\n")
        assert result.exit_code == 0
        assert (tmp_path / "bot2" / "AGENT.md").is_file()

    def test_duplicate_agent_exits_with_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import lariska.agents as _agents_module
        monkeypatch.setattr(_agents_module, "_AGENTS_DIR", tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["create-agent", "--name", "dup"])
        result = runner.invoke(cli, ["create-agent", "--name", "dup"])
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_empty_name_exits_with_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import lariska.agents as _agents_module
        monkeypatch.setattr(_agents_module, "_AGENTS_DIR", tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["create-agent", "--name", ""])
        assert result.exit_code == 1
        assert "empty" in result.output


# ---------------------------------------------------------------------------
# CLI: top-level group
# ---------------------------------------------------------------------------

class TestCliGroup:
    def test_no_subcommand_prints_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "lariska" in result.output.lower() or "agent orchestrator" in result.output.lower()

    def test_help_flag(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "init" in result.output
        assert "create-agent" in result.output
        assert "run" in result.output

    def test_init_help_shows_trello_prefix(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "--trello-api-key" in result.output
        assert "--trello-token" in result.output
        assert "--trello-list-name" in result.output
