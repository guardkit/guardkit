"""
Unit tests for template pattern loader.

Tests the TemplatePatternContext dataclass and load_template_patterns()
function which resolve a project's source template and return available
template pattern files.

TDD: RED phase — these tests are written first, before implementation.
"""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def manifest_dir(tmp_path: Path) -> Path:
    """Create a .claude directory with a valid manifest.json."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    manifest = claude_dir / "manifest.json"
    manifest.write_text(json.dumps({
        "name": "fastapi-python",
        "schema_version": "1.0.0",
    }))
    return manifest


@pytest.fixture
def template_tree(tmp_path: Path) -> Path:
    """Create a fake template directory with .template files."""
    tpl_dir = tmp_path / "templates" / "fastapi-python"
    templates_subdir = tpl_dir / "templates"
    templates_subdir.mkdir(parents=True)

    # Create some .template files
    for name in ["router.py.template", "config.py.template", "models.py.template"]:
        (templates_subdir / name).write_text(f"# {name}")

    return tpl_dir


# ---------------------------------------------------------------------------
# TemplatePatternContext dataclass tests
# ---------------------------------------------------------------------------

class TestTemplatePatternContext:
    """Tests for the TemplatePatternContext dataclass."""

    def test_dataclass_has_expected_fields(self) -> None:
        """AC-1: Verify the dataclass has all specified fields."""
        from guardkit.knowledge.template_pattern_loader import TemplatePatternContext

        field_names = {f.name for f in fields(TemplatePatternContext)}
        expected = {
            "template_name",
            "template_dir",
            "available_files",
            "selected_files",
            "prompt_block",
            "warnings",
        }
        assert field_names == expected

    def test_dataclass_template_name_is_optional_str(self) -> None:
        """AC-1: template_name accepts None."""
        from guardkit.knowledge.template_pattern_loader import TemplatePatternContext

        ctx = TemplatePatternContext(
            template_name=None,
            template_dir=None,
            available_files=[],
            selected_files=[],
            prompt_block="",
            warnings=[],
        )
        assert ctx.template_name is None

    def test_dataclass_template_dir_is_optional_path(self) -> None:
        """AC-1: template_dir accepts None or Path."""
        from guardkit.knowledge.template_pattern_loader import TemplatePatternContext

        ctx = TemplatePatternContext(
            template_name="fastapi-python",
            template_dir=Path("/some/dir"),
            available_files=[],
            selected_files=[],
            prompt_block="",
            warnings=[],
        )
        assert ctx.template_dir == Path("/some/dir")

    def test_dataclass_instantiation_with_all_fields(self) -> None:
        """AC-1: Full instantiation succeeds."""
        from guardkit.knowledge.template_pattern_loader import TemplatePatternContext

        ctx = TemplatePatternContext(
            template_name="fastapi-python",
            template_dir=Path("/tpl/fastapi-python"),
            available_files=[Path("a.template"), Path("b.template")],
            selected_files=[],
            prompt_block="",
            warnings=["some warning"],
        )
        assert ctx.template_name == "fastapi-python"
        assert len(ctx.available_files) == 2
        assert ctx.warnings == ["some warning"]


# ---------------------------------------------------------------------------
# load_template_patterns() tests
# ---------------------------------------------------------------------------

class TestLoader:
    """Tests for the load_template_patterns() function."""

    def test_reads_name_field_from_manifest(
        self, manifest_dir: Path, template_tree: Path
    ) -> None:
        """AC-2: Loader reads the `name` field from manifest."""
        from guardkit.knowledge.template_pattern_loader import load_template_patterns

        with patch(
            "guardkit.knowledge.template_pattern_loader.resolve_template_source_dir",
            return_value=template_tree,
        ):
            ctx = load_template_patterns(manifest_dir)

        assert ctx.template_name == "fastapi-python"

    def test_missing_manifest_returns_none_with_warning(
        self, tmp_path: Path
    ) -> None:
        """AC-3: Missing manifest → graceful degradation, no raise."""
        from guardkit.knowledge.template_pattern_loader import load_template_patterns

        nonexistent = tmp_path / ".claude" / "manifest.json"
        ctx = load_template_patterns(nonexistent)

        assert ctx.template_name is None
        assert ctx.template_dir is None
        assert ctx.available_files == []
        assert len(ctx.warnings) >= 1
        assert "missing" in ctx.warnings[0].lower() or "not found" in ctx.warnings[0].lower()

    def test_invalid_json_returns_none_with_warning(
        self, tmp_path: Path
    ) -> None:
        """AC-3: Invalid JSON → graceful degradation, no raise."""
        from guardkit.knowledge.template_pattern_loader import load_template_patterns

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        manifest = claude_dir / "manifest.json"
        manifest.write_text("{ not valid json !!!")

        ctx = load_template_patterns(manifest)

        assert ctx.template_name is None
        assert len(ctx.warnings) >= 1

    def test_missing_name_field_returns_none_with_warning(
        self, tmp_path: Path
    ) -> None:
        """AC-3: Manifest without `name` field → graceful degradation."""
        from guardkit.knowledge.template_pattern_loader import load_template_patterns

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        manifest = claude_dir / "manifest.json"
        manifest.write_text(json.dumps({"schema_version": "1.0.0"}))

        ctx = load_template_patterns(manifest)

        assert ctx.template_name is None
        assert len(ctx.warnings) >= 1

    def test_unresolvable_template_returns_none_with_warning(
        self, manifest_dir: Path
    ) -> None:
        """AC-4: Unknown template name → graceful degradation."""
        from guardkit.knowledge.template_pattern_loader import load_template_patterns

        with patch(
            "guardkit.knowledge.template_pattern_loader.resolve_template_source_dir",
            return_value=None,
        ):
            ctx = load_template_patterns(manifest_dir)

        assert ctx.template_name == "fastapi-python"
        assert ctx.template_dir is None
        assert ctx.available_files == []
        assert len(ctx.warnings) >= 1

    def test_valid_template_populates_available_files(
        self, manifest_dir: Path, template_tree: Path
    ) -> None:
        """AC-5: available_files populated with .template files."""
        from guardkit.knowledge.template_pattern_loader import load_template_patterns

        with patch(
            "guardkit.knowledge.template_pattern_loader.resolve_template_source_dir",
            return_value=template_tree,
        ):
            ctx = load_template_patterns(manifest_dir)

        assert ctx.template_name == "fastapi-python"
        assert ctx.template_dir == template_tree
        assert len(ctx.available_files) == 3
        for f in ctx.available_files:
            assert str(f).endswith(".template")

    def test_no_templates_subdir_returns_warning(
        self, manifest_dir: Path, tmp_path: Path
    ) -> None:
        """AC-4: Template dir without templates/ subdir → graceful degradation."""
        from guardkit.knowledge.template_pattern_loader import load_template_patterns

        # Create a template dir but without a templates/ subdirectory
        tpl_dir = tmp_path / "tpl" / "fastapi-python"
        tpl_dir.mkdir(parents=True)

        with patch(
            "guardkit.knowledge.template_pattern_loader.resolve_template_source_dir",
            return_value=tpl_dir,
        ):
            ctx = load_template_patterns(manifest_dir)

        assert ctx.template_name == "fastapi-python"
        assert ctx.available_files == []
        assert len(ctx.warnings) >= 1

    def test_selected_files_and_prompt_block_default_empty(
        self, manifest_dir: Path, template_tree: Path
    ) -> None:
        """Selector and prompt block are populated by later tasks, start empty."""
        from guardkit.knowledge.template_pattern_loader import load_template_patterns

        with patch(
            "guardkit.knowledge.template_pattern_loader.resolve_template_source_dir",
            return_value=template_tree,
        ):
            ctx = load_template_patterns(manifest_dir)

        assert ctx.selected_files == []
        assert ctx.prompt_block == ""

    def test_never_raises_on_any_failure(self, tmp_path: Path) -> None:
        """AC-3/AC-4: Never raises on failures."""
        from guardkit.knowledge.template_pattern_loader import load_template_patterns

        # Test with completely bogus path
        ctx = load_template_patterns(tmp_path / "nonexistent" / "manifest.json")
        assert ctx.template_name is None

    def test_os_error_returns_warning(self, tmp_path: Path) -> None:
        """AC-3: OSError during manifest read → graceful degradation."""
        from guardkit.knowledge.template_pattern_loader import load_template_patterns

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        manifest = claude_dir / "manifest.json"
        manifest.write_text("valid")

        with patch(
            "guardkit.knowledge.template_pattern_loader.Path.read_text",
            side_effect=PermissionError("access denied"),
        ):
            ctx = load_template_patterns(manifest)

        assert ctx.template_name is None
        assert len(ctx.warnings) >= 1

    def test_empty_name_field_returns_warning(
        self, tmp_path: Path
    ) -> None:
        """Empty string name field should be treated as absent."""
        from guardkit.knowledge.template_pattern_loader import load_template_patterns

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        manifest = claude_dir / "manifest.json"
        manifest.write_text(json.dumps({"name": "", "schema_version": "1.0.0"}))

        ctx = load_template_patterns(manifest)

        assert ctx.template_name is None
        assert len(ctx.warnings) >= 1


# ---------------------------------------------------------------------------
# Seam test: MANIFEST_NAME contract
# ---------------------------------------------------------------------------

@pytest.mark.seam
def test_manifest_name_format(tmp_path: Path) -> None:
    """Verify .claude/manifest.json name field matches the expected contract.

    Contract: .claude/manifest.json must contain a top-level `name` field (str)
    identifying the source template.
    Producer: guardkit init (existing CLI command)
    """
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    manifest_path = claude_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps({"name": "fastapi-python", "schema_version": "1.0.0"})
    )

    # Consumer side: load and verify field presence + type
    data = json.loads(manifest_path.read_text())
    assert "name" in data, "manifest.json must contain a `name` field"
    assert isinstance(data["name"], str) and data["name"], \
        f"manifest name must be non-empty str, got: {data.get('name')!r}"
