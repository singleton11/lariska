from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from lariska.agents import create_agent
from lariska.cli import _prompt, build_parser, main
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
# _prompt helper
# ---------------------------------------------------------------------------

class TestPrompt:
    def test_returns_user_input(self) -> None:
        with patch("builtins.input", return_value="hello"):
            assert _prompt("Label") == "hello"

    def test_strips_whitespace(self) -> None:
        with patch("builtins.input", return_value="  world  "):
            assert _prompt("Label") == "world"

    def test_default_used_when_blank(self) -> None:
        with patch("builtins.input", return_value=""):
            assert _prompt("Label", default="fallback") == "fallback"

    def test_required_re_prompts(self) -> None:
        with patch("builtins.input", side_effect=["", "ok"]):
            assert _prompt("Label", required=True) == "ok"

    def test_not_required_returns_empty(self) -> None:
        with patch("builtins.input", return_value=""):
            assert _prompt("Label", required=False) == ""


# ---------------------------------------------------------------------------
# CLI: init subcommand
# ---------------------------------------------------------------------------

class TestInitCommand:
    def test_non_interactive_init(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "main.yaml"
        main([
            "--config", str(cfg_file),
            "init",
            "--api-key", "mykey",
            "--token", "mytoken",
            "--list-name", "My List",
        ])
        config = load_config(cfg_file)
        assert config.trello.api_key == "mykey"
        assert config.trello.token == "mytoken"
        assert config.trello.list_name == "My List"

    def test_interactive_init(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "main.yaml"
        inputs = iter(["ikey", "itok", "My Board"])
        with patch("builtins.input", side_effect=inputs):
            main(["--config", str(cfg_file), "init"])
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
        # User presses Enter for all prompts → keeps existing values
        with patch("builtins.input", return_value=""):
            main(["--config", str(cfg_file), "init"])
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
        main(["create-agent", "--name", "bot1"])
        assert (tmp_path / "bot1" / "AGENT.md").is_file()

    def test_interactive_create_agent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import lariska.agents as _agents_module
        monkeypatch.setattr(_agents_module, "_AGENTS_DIR", tmp_path)
        with patch("builtins.input", return_value="bot2"):
            main(["create-agent"])
        assert (tmp_path / "bot2" / "AGENT.md").is_file()

    def test_duplicate_agent_exits_with_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import lariska.agents as _agents_module
        monkeypatch.setattr(_agents_module, "_AGENTS_DIR", tmp_path)
        main(["create-agent", "--name", "dup"])
        with pytest.raises(SystemExit) as exc_info:
            main(["create-agent", "--name", "dup"])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "already exists" in captured.err

    def test_empty_name_exits_with_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import lariska.agents as _agents_module
        monkeypatch.setattr(_agents_module, "_AGENTS_DIR", tmp_path)
        # Pass empty name directly instead of going interactive
        with pytest.raises(SystemExit) as exc_info:
            main(["create-agent", "--name", ""])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "empty" in captured.err


# ---------------------------------------------------------------------------
# CLI: parser structure
# ---------------------------------------------------------------------------

class TestBuildParser:
    def test_parser_has_init_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["init", "--api-key", "k"])
        assert args.command == "init"
        assert args.api_key == "k"

    def test_parser_has_create_agent_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["create-agent", "--name", "mybot"])
        assert args.command == "create-agent"
        assert args.name == "mybot"

    def test_parser_has_run_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["run"])
        assert args.command == "run"

    def test_no_subcommand_prints_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        main([])
        captured = capsys.readouterr()
        assert "lariska" in captured.out.lower()
