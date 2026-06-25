"""Regression tests for [tool.uv.sources] redirection in the per-dependency
install path (TASK-FIX-UVSRCDEP01).

Root cause (FEAT-HARV wave 1): guardkit-py is detected as an *incomplete*
project (its distribution name ``guardkit-py`` does not match its ``guardkit/``
package dir), so the bootstrap takes the per-dependency fallback path
(``_python_dep_commands``) instead of the editable ``uv pip install -e .``
path. That fallback emitted a plain ``pip install nats-core>=0.4,<1`` for the
``memory`` extra, ignoring the ``[tool.uv.sources]`` editable-sibling override.
Plain pip resolved ``nats-core`` from PyPI — where an *unrelated* public
package (only 0.0.0/0.1.0/0.2.0) lives — and failed the version constraint, so
``nats_core`` never landed in the worktree venv. The deliverable then ran its
tests against a self-mocked ``nats_core``, producing absent integration
evidence.

The fix makes the per-dependency path honour ``[tool.uv.sources]``: a dependency
pinned to a local path is installed editably from that path, fail-open to plain
pip when the path does not resolve.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from guardkit.orchestrator.environment_bootstrap import (
    DetectedManifest,
    _normalise_dist_name,
    _requirement_dist_name,
    _uv_sources_editable_targets,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_pyproject(
    directory: Path,
    *,
    name: str = "myapp",
    dependencies: list[str],
    extras: dict[str, list[str]] | None = None,
    uv_sources: dict[str, str] | None = None,
) -> Path:
    """Write a minimal pyproject.toml and return its path."""
    lines = ["[project]", f'name = "{name}"', "version = \"0.0.0\""]
    deps = ", ".join(f'"{d}"' for d in dependencies)
    lines.append(f"dependencies = [{deps}]")

    if extras:
        lines.append("")
        lines.append("[project.optional-dependencies]")
        for group, members in extras.items():
            members_str = ", ".join(f'"{m}"' for m in members)
            lines.append(f"{group} = [{members_str}]")

    if uv_sources:
        lines.append("")
        lines.append("[tool.uv.sources]")
        for key, rel_path in uv_sources.items():
            lines.append(f'"{key}" = {{ path = "{rel_path}", editable = true }}')

    path = directory / "pyproject.toml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _make_manifest(pyproject: Path, extras: tuple[str, ...]) -> DetectedManifest:
    return DetectedManifest(
        path=pyproject.resolve(),
        stack="python",
        is_lock_file=False,
        install_command=[sys.executable, "-m", "pip", "install", "-e", "."],
        python_extras=extras,
    )


# ---------------------------------------------------------------------------
# Name-normalisation / requirement-parsing helpers
# ---------------------------------------------------------------------------


class TestNameHelpers:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("nats-core", "nats-core"),
            ("nats_core", "nats-core"),
            ("Nats.Core", "nats-core"),
            ("  GuardKit_Factory  ", "guardkit-factory"),
        ],
    )
    def test_normalise_dist_name(self, raw: str, expected: str) -> None:
        assert _normalise_dist_name(raw) == expected

    @pytest.mark.parametrize(
        "requirement,expected",
        [
            ("nats-core>=0.4,<1", "nats-core"),
            ("nats_core==0.5", "nats-core"),
            ("graphiti-core[falkordb] @ git+https://example/x.git@v1", "graphiti-core"),
            ("click >= 8.0.0", "click"),
            ("pytest", "pytest"),
            ("", ""),
        ],
    )
    def test_requirement_dist_name(self, requirement: str, expected: str) -> None:
        assert _requirement_dist_name(requirement) == expected


# ---------------------------------------------------------------------------
# _uv_sources_editable_targets
# ---------------------------------------------------------------------------


class TestUvSourcesEditableTargets:
    def test_path_entry_present_sibling_is_mapped(self, tmp_path: Path) -> None:
        proj = tmp_path / "app"
        proj.mkdir()
        sibling = tmp_path / "nats-core"
        sibling.mkdir()
        pyproject = _write_pyproject(
            proj,
            dependencies=["click>=8.0"],
            uv_sources={"nats-core": "../nats-core"},
        )

        targets = _uv_sources_editable_targets(pyproject.resolve())

        assert targets == {"nats-core": str(sibling.resolve())}

    def test_missing_sibling_is_omitted_fail_open(self, tmp_path: Path) -> None:
        proj = tmp_path / "app"
        proj.mkdir()
        # No ../nats-core directory created.
        pyproject = _write_pyproject(
            proj,
            dependencies=["click>=8.0"],
            uv_sources={"nats-core": "../nats-core"},
        )

        assert _uv_sources_editable_targets(pyproject.resolve()) == {}

    def test_no_uv_sources_table_returns_empty(self, tmp_path: Path) -> None:
        proj = tmp_path / "app"
        proj.mkdir()
        pyproject = _write_pyproject(proj, dependencies=["click>=8.0"])
        assert _uv_sources_editable_targets(pyproject.resolve()) == {}

    def test_resolution_follows_bridge_symlink(self, tmp_path: Path) -> None:
        # Mirror the worktree bridge: ../nats-core is a symlink to the real repo.
        real = tmp_path / "real-nats-core"
        real.mkdir()
        proj = tmp_path / "app"
        proj.mkdir()
        (tmp_path / "nats-core").symlink_to(real, target_is_directory=True)
        pyproject = _write_pyproject(
            proj,
            dependencies=["click>=8.0"],
            uv_sources={"nats-core": "../nats-core"},
        )

        targets = _uv_sources_editable_targets(pyproject.resolve())

        # .resolve() follows the symlink to the real checkout.
        assert targets == {"nats-core": str(real.resolve())}


# ---------------------------------------------------------------------------
# End-to-end: get_dependency_install_commands() redirect (the reproducer)
# ---------------------------------------------------------------------------


class TestPerDependencyUvSourcesRedirect:
    def test_uv_sources_extra_dep_is_editable_install(self, tmp_path: Path) -> None:
        """The FEAT-HARV reproducer: a uv-sources dep in an extra installs
        editably from the sibling, not from PyPI."""
        proj = tmp_path / "app"
        proj.mkdir()
        sibling = tmp_path / "nats-core"
        sibling.mkdir()
        pyproject = _write_pyproject(
            proj,
            dependencies=["click>=8.0.0"],
            extras={"memory": ["nats-core>=0.4,<1"]},
            uv_sources={"nats-core": "../nats-core"},
        )
        manifest = _make_manifest(pyproject, extras=("memory",))

        commands = manifest.get_dependency_install_commands()

        assert commands is not None
        # Base dep: plain pip (no uv-source for click).
        assert [sys.executable, "-m", "pip", "install", "click>=8.0.0"] in commands
        # Extra dep redirected by [tool.uv.sources] -> editable install.
        assert [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-e",
            str(sibling.resolve()),
        ] in commands
        # And the broken plain-pip form must NOT be emitted for nats-core.
        assert [
            sys.executable,
            "-m",
            "pip",
            "install",
            "nats-core>=0.4,<1",
        ] not in commands

    def test_missing_sibling_falls_back_to_plain_pip(self, tmp_path: Path) -> None:
        """Fail-open: no sibling checkout -> behave exactly as before the fix."""
        proj = tmp_path / "app"
        proj.mkdir()
        pyproject = _write_pyproject(
            proj,
            dependencies=["click>=8.0.0"],
            extras={"memory": ["nats-core>=0.4,<1"]},
            uv_sources={"nats-core": "../nats-core"},  # sibling not created
        )
        manifest = _make_manifest(pyproject, extras=("memory",))

        commands = manifest.get_dependency_install_commands()

        assert commands is not None
        assert [
            sys.executable,
            "-m",
            "pip",
            "install",
            "nats-core>=0.4,<1",
        ] in commands
        # No editable command emitted.
        assert not any("-e" in cmd for cmd in commands)

    def test_underscore_named_dep_matches_hyphen_source(self, tmp_path: Path) -> None:
        """A dep written ``nats_core`` matches a ``nats-core`` uv-source (PEP 503)."""
        proj = tmp_path / "app"
        proj.mkdir()
        sibling = tmp_path / "nats-core"
        sibling.mkdir()
        pyproject = _write_pyproject(
            proj,
            dependencies=["nats_core>=0.4"],
            uv_sources={"nats-core": "../nats-core"},
        )
        manifest = _make_manifest(pyproject, extras=())

        commands = manifest.get_dependency_install_commands()

        assert commands == [
            [sys.executable, "-m", "pip", "install", "-e", str(sibling.resolve())]
        ]

    def test_no_uv_sources_unchanged(self, tmp_path: Path) -> None:
        """A project without [tool.uv.sources] emits plain pip for every dep
        (no behavioural change)."""
        proj = tmp_path / "app"
        proj.mkdir()
        pyproject = _write_pyproject(
            proj,
            dependencies=["click>=8.0.0", "rich>=13.0.0"],
        )
        manifest = _make_manifest(pyproject, extras=())

        commands = manifest.get_dependency_install_commands()

        assert commands == [
            [sys.executable, "-m", "pip", "install", "click>=8.0.0"],
            [sys.executable, "-m", "pip", "install", "rich>=13.0.0"],
        ]
