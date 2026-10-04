"""The harvest files under the resolved project (project initialisation design, 4 October 2026).

``harvest_walker`` and ``harvest_taxonomy`` used to write the literal
``"guardkit"`` into every episode's project, natural key and the corpus
manifest, whichever repository was harvested. They now take the project that
``resolve_memory_project`` resolves, and the command refuses when memory is off.
GuardKit's own repository declares ``memory.project: guardkit``, so its keys and
episode ids are byte-identical to before (the golden values below were computed
with the module at the base commit, c2cf6577).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

pytest.importorskip("nats_core")

from guardkit.cli.memory import memory as memory_cli  # noqa: E402
from guardkit.knowledge.memory_project import resolve_memory_project  # noqa: E402
from guardkit.memory.harvest_taxonomy import (  # noqa: E402
    derive_episode_id,
    manifest_json,
    natural_key_for,
)
from guardkit.memory.harvest_walker import walk_harvest_dirs  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]

# Computed with harvest_taxonomy at c2cf6577 (before this change).
BASE_KEYS = {
    ("docs/adr/0001-use-nats.md", "adr"): (
        "guardkit:docs/adr/0001-use-nats.md:adr",
        "ep-f6105ef0e49f1594",
    ),
    ("docs/guides/autobuild.md", "document"): (
        "guardkit:docs/guides/autobuild.md:document",
        "ep-18a8bf079ff84e21",
    ),
}


def test_guardkit_declares_its_own_memory_name() -> None:
    resolution = resolve_memory_project(REPO_ROOT, env={})
    assert resolution.project == "guardkit"
    assert resolution.source == "declaration"


@pytest.mark.parametrize("path,episode_type", sorted(BASE_KEYS))
def test_guardkit_keys_and_ids_unchanged(path: str, episode_type: str) -> None:
    project = resolve_memory_project(REPO_ROOT, env={}).project
    key = natural_key_for(path, episode_type, project=project)
    assert (key, derive_episode_id(key)) == BASE_KEYS[(path, episode_type)]


def test_guardkit_manifest_unchanged() -> None:
    project = resolve_memory_project(REPO_ROOT, env={}).project
    assert json.loads(manifest_json(project=project))["project"] == "guardkit"


def test_another_project_is_scoped(tmp_path: Path) -> None:
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    (tmp_path / "docs" / "adr" / "0001-use-nats.md").write_text("# Use NATS\n")
    alpha = walk_harvest_dirs(tmp_path, "alpha").episodes[0]
    guardkit = walk_harvest_dirs(tmp_path, "guardkit").episodes[0]
    assert alpha.project_id == "alpha"
    assert alpha.episode_id == derive_episode_id("alpha:docs/adr/0001-use-nats.md:adr")
    assert guardkit.episode_id == BASE_KEYS[("docs/adr/0001-use-nats.md", "adr")][1]
    assert json.loads(manifest_json(project="alpha"))["project"] == "alpha"


def test_harvest_refused_when_memory_is_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GUARDKIT_MEMORY_PROJECT", raising=False)
    monkeypatch.delenv("GUARDKIT_FACTORY_LAUNCH", raising=False)
    (tmp_path / ".git").mkdir()
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    with patch("guardkit.cli.memory.walk_harvest_dirs") as walker:
        result = CliRunner().invoke(
            memory_cli, ["harvest", "--dry-run", "--docs-root", str(tmp_path)]
        )
    assert result.exit_code == 1
    assert "no memory to harvest into" in result.output
    walker.assert_not_called()


def test_harvest_uses_the_declared_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GUARDKIT_MEMORY_PROJECT", raising=False)
    monkeypatch.delenv("GUARDKIT_FACTORY_LAUNCH", raising=False)
    (tmp_path / ".git").mkdir()
    (tmp_path / ".guardkit").mkdir()
    (tmp_path / ".guardkit" / "config.yaml").write_text("memory:\n  project: alpha\n")
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    (tmp_path / "docs" / "adr" / "0001.md").write_text("# One\n")
    with patch(
        "guardkit.cli.memory.walk_harvest_dirs", wraps=walk_harvest_dirs
    ) as walker:
        result = CliRunner().invoke(
            memory_cli, ["harvest", "--dry-run", "--docs-root", str(tmp_path)]
        )
    assert result.exit_code == 0, result.output
    assert walker.call_args.args[1] == "alpha"
