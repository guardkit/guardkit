"""
Tests for guardkit init --with-mcp MCP configuration generation.

Coverage Target: >=85%
Test Count: 20+ tests
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.cli.init import (
    _find_uv_command,
    discover_graphiti_mcp_path,
    generate_mcp_json_entry,
    generate_mcp_server_config,
    write_mcp_json,
    write_mcp_server_config,
    _MCP_SERVER_PATH_CONFIG,
    _GRAPHITI_MCP_PATH_ENV,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(
    llm_base_url="http://host:8000/v1",
    llm_model="test-model",
    llm_max_tokens=4096,
    embedding_base_url="http://host:8001/v1",
    embedding_model="nomic-embed-text-v1.5",
    falkordb_host="whitestocks",
    falkordb_port=6379,
    embedding_dimensions=None,
):
    s = MagicMock()
    s.llm_base_url = llm_base_url
    s.llm_model = llm_model
    s.llm_max_tokens = llm_max_tokens
    s.embedding_base_url = embedding_base_url
    s.embedding_model = embedding_model
    s.falkordb_host = falkordb_host
    s.falkordb_port = falkordb_port
    s.embedding_dimensions = embedding_dimensions
    return s


# ============================================================================
# 1. _find_uv_command
# ============================================================================


class TestFindUvCommand:
    def test_returns_path_when_uv_found(self):
        with patch("guardkit.cli.init.shutil.which", return_value="/opt/homebrew/bin/uv"):
            result = _find_uv_command()
        assert result == "/opt/homebrew/bin/uv"

    def test_returns_fallback_when_uv_not_found(self):
        with patch("guardkit.cli.init.shutil.which", return_value=None):
            result = _find_uv_command()
        assert result == "uv"


# ============================================================================
# 2. discover_graphiti_mcp_path
# ============================================================================


class TestDiscoverGraphitiMcpPath:
    def test_discovers_via_env_var(self, tmp_path, monkeypatch):
        monkeypatch.setenv(_GRAPHITI_MCP_PATH_ENV, str(tmp_path))
        result = discover_graphiti_mcp_path(prompt_if_missing=False)
        assert result == tmp_path.resolve()

    def test_ignores_nonexistent_env_var_path(self, tmp_path, monkeypatch):
        nonexistent = str(tmp_path / "does_not_exist")
        monkeypatch.setenv(_GRAPHITI_MCP_PATH_ENV, nonexistent)
        result = discover_graphiti_mcp_path(prompt_if_missing=False)
        assert result is None

    def test_discovers_via_config_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv(_GRAPHITI_MCP_PATH_ENV, raising=False)
        mcp_dir = tmp_path / "mcp_server"
        mcp_dir.mkdir()
        config_file = tmp_path / "mcp-server-path"
        config_file.write_text(str(mcp_dir))

        with patch("guardkit.cli.init._MCP_SERVER_PATH_CONFIG", config_file):
            result = discover_graphiti_mcp_path(prompt_if_missing=False)

        assert result == mcp_dir.resolve()

    def test_ignores_nonexistent_config_file_path(self, tmp_path, monkeypatch):
        monkeypatch.delenv(_GRAPHITI_MCP_PATH_ENV, raising=False)
        config_file = tmp_path / "mcp-server-path"
        config_file.write_text(str(tmp_path / "gone"))

        with patch("guardkit.cli.init._MCP_SERVER_PATH_CONFIG", config_file):
            result = discover_graphiti_mcp_path(prompt_if_missing=False)

        assert result is None

    def test_returns_none_when_nothing_found(self, tmp_path, monkeypatch):
        monkeypatch.delenv(_GRAPHITI_MCP_PATH_ENV, raising=False)
        config_file = tmp_path / "mcp-server-path-nonexistent"
        with patch("guardkit.cli.init._MCP_SERVER_PATH_CONFIG", config_file):
            result = discover_graphiti_mcp_path(prompt_if_missing=False)
        assert result is None

    def test_stores_path_after_prompt(self, tmp_path, monkeypatch):
        monkeypatch.delenv(_GRAPHITI_MCP_PATH_ENV, raising=False)
        mcp_dir = tmp_path / "mcp_server"
        mcp_dir.mkdir()
        config_file = tmp_path / "mcp-server-path"

        with patch("guardkit.cli.init._MCP_SERVER_PATH_CONFIG", config_file), \
             patch("guardkit.cli.init.Prompt.ask", return_value=str(mcp_dir)):
            result = discover_graphiti_mcp_path(prompt_if_missing=True)

        assert result == mcp_dir.resolve()
        assert config_file.exists()
        assert config_file.read_text().strip() == str(mcp_dir.resolve())

    def test_prompt_nonexistent_path_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.delenv(_GRAPHITI_MCP_PATH_ENV, raising=False)
        config_file = tmp_path / "no-config"

        with patch("guardkit.cli.init._MCP_SERVER_PATH_CONFIG", config_file), \
             patch("guardkit.cli.init.Prompt.ask", return_value=str(tmp_path / "missing")):
            result = discover_graphiti_mcp_path(prompt_if_missing=True)

        assert result is None

    def test_env_var_takes_priority_over_config_file(self, tmp_path, monkeypatch):
        env_dir = tmp_path / "env_mcp"
        env_dir.mkdir()
        config_dir = tmp_path / "config_mcp"
        config_dir.mkdir()
        config_file = tmp_path / "mcp-server-path"
        config_file.write_text(str(config_dir))

        monkeypatch.setenv(_GRAPHITI_MCP_PATH_ENV, str(env_dir))

        with patch("guardkit.cli.init._MCP_SERVER_PATH_CONFIG", config_file):
            result = discover_graphiti_mcp_path(prompt_if_missing=False)

        assert result == env_dir.resolve()


# ============================================================================
# 3. generate_mcp_server_config
# ============================================================================


class TestGenerateMcpServerConfig:
    def test_structure_is_correct(self):
        settings = _make_settings()
        config = generate_mcp_server_config("myproject", settings)

        assert config["server"]["transport"] == "stdio"
        assert config["llm"]["model"] == "test-model"
        assert config["llm"]["max_tokens"] == 4096
        assert config["embedder"]["model"] == "nomic-embed-text-v1.5"
        # Resolver (tier 2) maps nomic-embed-text-v1.5 to 768.
        assert config["embedder"]["dimensions"] == 768
        assert config["database"]["provider"] == "falkordb"
        assert config["graphiti"]["group_id"] == "myproject"

    def test_falkordb_uri_uses_settings(self):
        settings = _make_settings(falkordb_host="mynas", falkordb_port=1234)
        config = generate_mcp_server_config("proj", settings)
        uri = config["database"]["providers"]["falkordb"]["uri"]
        assert uri == "redis://mynas:1234"

    def test_llm_api_url_contains_default(self):
        settings = _make_settings(llm_base_url="http://gpu:8000/v1")
        config = generate_mcp_server_config("proj", settings)
        api_url = config["llm"]["providers"]["openai"]["api_url"]
        assert "http://gpu:8000/v1" in api_url

    def test_embedding_api_url_contains_default(self):
        settings = _make_settings(embedding_base_url="http://gpu:8001/v1")
        config = generate_mcp_server_config("proj", settings)
        api_url = config["embedder"]["providers"]["openai"]["api_url"]
        assert "http://gpu:8001/v1" in api_url

    def test_entity_types_present(self):
        settings = _make_settings()
        config = generate_mcp_server_config("proj", settings)
        assert isinstance(config["graphiti"]["entity_types"], list)
        assert len(config["graphiti"]["entity_types"]) > 0

    def test_openai_api_key_placeholder(self):
        settings = _make_settings()
        config = generate_mcp_server_config("proj", settings)
        assert "${OPENAI_API_KEY}" in config["llm"]["providers"]["openai"]["api_key"]

    def test_dimensions_resolves_from_known_model_when_not_set(self):
        # _make_settings defaults to embedding_model="nomic-embed-text-v1.5",
        # which is in KNOWN_EMBEDDING_DIMS as 768. The resolver (tier 2)
        # returns 768 rather than the legacy hardcoded 1024.
        settings = _make_settings(embedding_dimensions=None)
        config = generate_mcp_server_config("proj", settings)
        assert config["embedder"]["dimensions"] == 768

    def test_dimensions_uses_explicit_value_when_set(self):
        settings = _make_settings(embedding_dimensions=768)
        config = generate_mcp_server_config("proj", settings)
        assert config["embedder"]["dimensions"] == 768

    def test_dimensions_1024_explicit(self):
        settings = _make_settings(embedding_dimensions=1024)
        config = generate_mcp_server_config("proj", settings)
        assert config["embedder"]["dimensions"] == 1024


# ============================================================================
# 4. write_mcp_server_config
# ============================================================================


class TestWriteMcpServerConfig:
    def test_writes_yaml_file(self, tmp_path):
        settings = _make_settings()
        result = write_mcp_server_config("myproj", tmp_path, settings)

        assert result is not None
        config_path = tmp_path / "config" / "config-myproj.yaml"
        assert config_path.exists()
        assert result == config_path

    def test_creates_config_dir_if_missing(self, tmp_path):
        settings = _make_settings()
        mcp_path = tmp_path / "mcp_server"
        mcp_path.mkdir()
        write_mcp_server_config("proj", mcp_path, settings)
        assert (mcp_path / "config").is_dir()

    def test_returns_none_on_write_exception(self, tmp_path):
        settings = _make_settings()
        # Make the directory read-only to trigger a write failure
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_dir.chmod(0o444)
        try:
            result = write_mcp_server_config("proj", tmp_path, settings)
            assert result is None
        finally:
            config_dir.chmod(0o755)

    def test_yaml_content_is_valid(self, tmp_path):
        import yaml
        settings = _make_settings(falkordb_host="nas", falkordb_port=6379)
        result = write_mcp_server_config("testproj", tmp_path, settings)
        assert result is not None
        content = yaml.safe_load(result.read_text())
        assert content["graphiti"]["group_id"] == "testproj"
        assert content["database"]["providers"]["falkordb"]["uri"] == "redis://nas:6379"


# ============================================================================
# 5. generate_mcp_json_entry
# ============================================================================


class TestGenerateMcpJsonEntry:
    def test_entry_structure(self, tmp_path):
        settings = _make_settings()
        mcp_dir = tmp_path / "mcp_server"
        config_path = mcp_dir / "config" / "config-proj.yaml"

        with patch("guardkit.cli.init.shutil.which", return_value="/usr/bin/uv"):
            entry = generate_mcp_json_entry("proj", mcp_dir, config_path, settings)

        assert entry["type"] == "stdio"
        assert entry["command"] == "/usr/bin/uv"
        assert "--directory" in entry["args"]
        assert str(mcp_dir) in entry["args"]
        assert str(config_path) in entry["args"]

    def test_env_vars_present(self, tmp_path):
        settings = _make_settings(
            llm_base_url="http://llm:8000/v1",
            embedding_base_url="http://emb:8001/v1",
        )
        entry = generate_mcp_json_entry("proj", tmp_path, tmp_path / "config.yaml", settings)

        assert entry["env"]["CONFIG_PATH"] == str(tmp_path / "config.yaml")
        assert entry["env"]["LLM_API_URL"] == "http://llm:8000/v1"
        assert entry["env"]["EMBEDDING_API_URL"] == "http://emb:8001/v1"
        # Resolver returns 768 for nomic-embed-text-v1.5 (tier 2 via
        # KNOWN_EMBEDDING_DIMS), not the legacy hardcoded 1024.
        assert entry["env"]["EMBEDDING_DIM"] == "768"
        assert entry["env"]["OPENAI_API_KEY"] == "not-needed-vllm-local"

    def test_main_py_in_args(self, tmp_path):
        settings = _make_settings()
        entry = generate_mcp_json_entry("proj", tmp_path, tmp_path / "cfg.yaml", settings)
        assert "main.py" in entry["args"]
        assert "--transport" in entry["args"]
        assert "stdio" in entry["args"]

    def test_embedding_dim_resolves_from_known_model(self, tmp_path):
        # _make_settings defaults model to "nomic-embed-text-v1.5" (768-dim).
        settings = _make_settings(embedding_dimensions=None)
        entry = generate_mcp_json_entry("proj", tmp_path, tmp_path / "cfg.yaml", settings)
        assert entry["env"]["EMBEDDING_DIM"] == "768"

    def test_embedding_dim_uses_explicit_value(self, tmp_path):
        settings = _make_settings(embedding_dimensions=768)
        entry = generate_mcp_json_entry("proj", tmp_path, tmp_path / "cfg.yaml", settings)
        assert entry["env"]["EMBEDDING_DIM"] == "768"


# ============================================================================
# 6. write_mcp_json
# ============================================================================


class TestWriteMcpJson:
    def test_creates_mcp_json(self, tmp_path):
        settings = _make_settings()
        mcp_dir = tmp_path / "mcp_server"
        mcp_dir.mkdir()

        result = write_mcp_json(tmp_path, mcp_dir, "myproj", settings)

        assert result is True
        mcp_file = tmp_path / ".mcp.json"
        assert mcp_file.exists()

    def test_mcp_json_has_correct_structure(self, tmp_path):
        settings = _make_settings()
        mcp_dir = tmp_path / "mcp_server"
        mcp_dir.mkdir()

        write_mcp_json(tmp_path, mcp_dir, "myproj", settings)

        with open(tmp_path / ".mcp.json") as f:
            data = json.load(f)

        assert "mcpServers" in data
        assert "graphiti" in data["mcpServers"]
        assert data["mcpServers"]["graphiti"]["type"] == "stdio"

    def test_merges_existing_mcp_json(self, tmp_path):
        """Existing mcpServers entries are preserved."""
        settings = _make_settings()
        mcp_dir = tmp_path / "mcp_server"
        mcp_dir.mkdir()

        existing = {
            "mcpServers": {
                "other-server": {"type": "stdio", "command": "other"}
            }
        }
        with open(tmp_path / ".mcp.json", "w") as f:
            json.dump(existing, f)

        write_mcp_json(tmp_path, mcp_dir, "myproj", settings)

        with open(tmp_path / ".mcp.json") as f:
            data = json.load(f)

        assert "other-server" in data["mcpServers"]
        assert "graphiti" in data["mcpServers"]

    def test_overwrites_existing_graphiti_entry(self, tmp_path):
        """Existing graphiti entry is replaced, not duplicated."""
        settings = _make_settings(llm_base_url="http://new-host:8000/v1")
        mcp_dir = tmp_path / "mcp_server"
        mcp_dir.mkdir()

        old_data = {
            "mcpServers": {
                "graphiti": {"type": "stdio", "command": "old-uv"}
            }
        }
        with open(tmp_path / ".mcp.json", "w") as f:
            json.dump(old_data, f)

        write_mcp_json(tmp_path, mcp_dir, "myproj", settings)

        with open(tmp_path / ".mcp.json") as f:
            data = json.load(f)

        # Should not still have 'old-uv'
        assert data["mcpServers"]["graphiti"]["command"] != "old-uv"

    def test_handles_invalid_existing_json(self, tmp_path):
        """Invalid existing .mcp.json is overwritten gracefully."""
        settings = _make_settings()
        mcp_dir = tmp_path / "mcp_server"
        mcp_dir.mkdir()

        (tmp_path / ".mcp.json").write_text("not valid json!!!!")

        result = write_mcp_json(tmp_path, mcp_dir, "myproj", settings)

        assert result is True
        with open(tmp_path / ".mcp.json") as f:
            data = json.load(f)
        assert "mcpServers" in data

    def test_uses_custom_server_key(self, tmp_path):
        settings = _make_settings()
        mcp_dir = tmp_path / "mcp_server"
        mcp_dir.mkdir()

        write_mcp_json(tmp_path, mcp_dir, "myproj", settings, server_key="my-graphiti")

        with open(tmp_path / ".mcp.json") as f:
            data = json.load(f)

        assert "my-graphiti" in data["mcpServers"]


# ============================================================================
# 7. Integration: init --with-mcp CLI flag
# ============================================================================


class TestInitWithMcpFlag:
    def test_with_mcp_flag_shown_in_help(self):
        from click.testing import CliRunner
        from guardkit.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "with-mcp" in result.output

    def test_init_with_mcp_generates_mcp_json(self, tmp_path, monkeypatch):
        from click.testing import CliRunner
        from unittest.mock import AsyncMock
        from guardkit.cli.main import cli

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        mcp_dir = tmp_path / "mcp_server"
        mcp_dir.mkdir()

        with patch("guardkit.cli.init.seed_project_knowledge", new_callable=AsyncMock) as mock_seed, \
             patch("guardkit.cli.init.GraphitiClient") as mock_client_class, \
             patch("guardkit.cli.init.discover_graphiti_mcp_path", return_value=mcp_dir), \
             patch("guardkit.cli.init.load_graphiti_config") as mock_cfg:

            mock_client = MagicMock()
            mock_client.enabled = False
            mock_client.initialize = AsyncMock(return_value=False)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_seed.return_value = MagicMock(success=True)
            mock_cfg.return_value = _make_settings()

            result = runner.invoke(cli, ["init", "--skip-graphiti", "--with-mcp"])

        assert result.exit_code == 0
        assert (tmp_path / ".mcp.json").exists()

    def test_init_without_mcp_no_mcp_json(self, tmp_path, monkeypatch):
        from click.testing import CliRunner
        from unittest.mock import AsyncMock
        from guardkit.cli.main import cli

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch("guardkit.cli.init.seed_project_knowledge", new_callable=AsyncMock), \
             patch("guardkit.cli.init.GraphitiClient") as mock_client_class:

            mock_client = MagicMock()
            mock_client.enabled = False
            mock_client.initialize = AsyncMock(return_value=False)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["init", "--skip-graphiti"])

        assert result.exit_code == 0
        assert not (tmp_path / ".mcp.json").exists()

    def test_init_with_mcp_no_path_shows_warning(self, tmp_path, monkeypatch):
        from click.testing import CliRunner
        from unittest.mock import AsyncMock
        from guardkit.cli.main import cli

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch("guardkit.cli.init.seed_project_knowledge", new_callable=AsyncMock), \
             patch("guardkit.cli.init.GraphitiClient") as mock_client_class, \
             patch("guardkit.cli.init.discover_graphiti_mcp_path", return_value=None), \
             patch("guardkit.cli.init.load_graphiti_config") as mock_cfg:

            mock_client = MagicMock()
            mock_client.enabled = False
            mock_client.initialize = AsyncMock(return_value=False)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_cfg.return_value = _make_settings()

            result = runner.invoke(cli, ["init", "--skip-graphiti", "--with-mcp"])

        assert result.exit_code == 0
        assert not (tmp_path / ".mcp.json").exists()
        assert "Warning" in result.output or "not found" in result.output
