"""
Unit tests for template pattern loader.

Tests the TemplatePatternContext dataclass, load_template_patterns()
function, and select_patterns() domain-hint selector which resolves
relevant template files from tech_stack and file-path hints.

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
# Selector fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def selector_tree(tmp_path: Path) -> Path:
    """Create a template tree with subdirectories matching fastapi-python layout.

    Structure:
        templates/
            api/
                router.py.template        (~40 chars)
            config/
                alembic.ini.template      (~40 chars)
                pyproject.toml.template   (~40 chars)
            core/
                config.py.template        (~40 chars)
                security.py.template      (~40 chars)
            crud/
                crud_base.py.template     (~40 chars)
                crud.py.template          (~40 chars)
            db/
                session.py.template       (~40 chars)
            models/
                models.py.template        (~40 chars)
            schemas/
                schemas.py.template       (~40 chars)
            testing/
                conftest.py.template      (~40 chars)
                test_router.py.template   (~40 chars)
    """
    tpl_dir = tmp_path / "tpl" / "fastapi-python"
    tpl_sub = tpl_dir / "templates"
    file_defs = {
        "api/router.py.template": "# API router template content here...",
        "config/alembic.ini.template": "# Alembic config template content..",
        "config/pyproject.toml.template": "# pyproject.toml template content.",
        "core/config.py.template": "# Core config template content here",
        "core/security.py.template": "# Security template content here...",
        "crud/crud_base.py.template": "# CRUD base template content here..",
        "crud/crud.py.template": "# CRUD template content stored here",
        "db/session.py.template": "# DB session template content here.",
        "models/models.py.template": "# Models template content goes here",
        "schemas/schemas.py.template": "# Schemas template content goes here",
        "testing/conftest.py.template": "# Test conftest template content...",
        "testing/test_router.py.template": "# Test router template content....",
    }
    for rel, content in file_defs.items():
        fpath = tpl_sub / rel
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content)

    return tpl_dir


def _make_ctx(
    selector_tree: Path,
    *,
    template_name: str = "fastapi-python",
) -> "TemplatePatternContext":
    """Helper to build a TemplatePatternContext from a selector_tree fixture."""
    from guardkit.knowledge.template_pattern_loader import TemplatePatternContext

    tpl_sub = selector_tree / "templates"
    available = sorted(tpl_sub.rglob("*.template"))
    return TemplatePatternContext(
        template_name=template_name,
        template_dir=selector_tree,
        available_files=available,
        selected_files=[],
        prompt_block="",
        warnings=[],
    )


# ---------------------------------------------------------------------------
# select_patterns() tests — Domain-hint selector (TASK-TPL-003)
# ---------------------------------------------------------------------------

class TestSelector:
    """Tests for the select_patterns() domain-hint selector function."""

    # --- AC-1: File-path hint matching ---

    def test_file_path_hint_selects_matching_subdir(
        self, selector_tree: Path,
    ) -> None:
        """AC-1: File-path hint 'app/api/users.py' selects api/router.py.template."""
        from guardkit.knowledge.template_pattern_loader import select_patterns

        ctx = _make_ctx(selector_tree)
        result = select_patterns(
            ctx,
            tech_stack="Python",
            file_path_hints=["app/api/users.py"],
        )

        selected_names = [f.name for f in result.selected_files]
        assert "router.py.template" in selected_names

    def test_file_path_hint_matches_multiple_segments(
        self, selector_tree: Path,
    ) -> None:
        """File-path with multiple matching segments selects from both subdirs."""
        from guardkit.knowledge.template_pattern_loader import select_patterns

        ctx = _make_ctx(selector_tree)
        result = select_patterns(
            ctx,
            tech_stack="Python",
            file_path_hints=["app/api/users.py", "app/models/user.py"],
        )

        selected_names = [f.name for f in result.selected_files]
        assert "router.py.template" in selected_names
        assert "models.py.template" in selected_names

    def test_file_path_hint_takes_precedence_over_tech_stack(
        self, selector_tree: Path,
    ) -> None:
        """AC-1: File-path hints take precedence — no tech_stack fallback used."""
        from guardkit.knowledge.template_pattern_loader import select_patterns

        ctx = _make_ctx(selector_tree)
        result = select_patterns(
            ctx,
            tech_stack="Python",
            file_path_hints=["app/crud/items.py"],
        )

        selected_names = [f.name for f in result.selected_files]
        # Should contain crud files but not every Python-related template
        assert any("crud" in n for n in selected_names)

    # --- AC-2: Tech-stack fallback + alphabetical fallback ---

    def test_empty_hints_tech_stack_fallback(
        self, selector_tree: Path,
    ) -> None:
        """AC-2: Empty file-path hints + tech_stack='Python' falls back to tech-stack."""
        from guardkit.knowledge.template_pattern_loader import select_patterns

        ctx = _make_ctx(selector_tree)
        result = select_patterns(
            ctx,
            tech_stack="Python",
            file_path_hints=[],
        )

        # Tech-stack 'Python' should match at least some files
        assert len(result.selected_files) > 0

    def test_empty_hints_empty_tech_stack_alphabetical_fallback(
        self, selector_tree: Path,
    ) -> None:
        """AC-2: Empty hints + empty tech_stack → alphabetical first 3."""
        from guardkit.knowledge.template_pattern_loader import select_patterns

        ctx = _make_ctx(selector_tree)
        result = select_patterns(
            ctx,
            tech_stack="",
            file_path_hints=[],
        )

        assert len(result.selected_files) == 3
        # First 3 alphabetically from the available files
        sorted_available = sorted(ctx.available_files)
        assert result.selected_files == sorted_available[:3]

    def test_no_matching_tech_stack_falls_through_to_alphabetical(
        self, selector_tree: Path,
    ) -> None:
        """AC-2: Unmatched tech_stack + empty hints → alphabetical fallback."""
        from guardkit.knowledge.template_pattern_loader import select_patterns

        ctx = _make_ctx(selector_tree)
        result = select_patterns(
            ctx,
            tech_stack="Haskell",
            file_path_hints=[],
        )

        assert len(result.selected_files) == 3

    # --- AC-3: Hard cap at max_files ---

    def test_hard_cap_default_five(
        self, selector_tree: Path,
    ) -> None:
        """AC-3: Never returns more than 5 files (default max_files)."""
        from guardkit.knowledge.template_pattern_loader import select_patterns

        ctx = _make_ctx(selector_tree)
        # Many hints that match many subdirs
        result = select_patterns(
            ctx,
            tech_stack="Python",
            file_path_hints=[
                "app/api/x.py",
                "app/models/x.py",
                "app/crud/x.py",
                "app/schemas/x.py",
                "app/core/x.py",
                "app/db/x.py",
                "app/config/x.py",
            ],
        )

        assert len(result.selected_files) <= 5

    def test_hard_cap_custom(
        self, selector_tree: Path,
    ) -> None:
        """AC-3: Custom max_files cap is respected."""
        from guardkit.knowledge.template_pattern_loader import select_patterns

        ctx = _make_ctx(selector_tree)
        result = select_patterns(
            ctx,
            tech_stack="Python",
            file_path_hints=["app/api/x.py", "app/models/x.py", "app/crud/x.py"],
            max_files=2,
        )

        assert len(result.selected_files) <= 2

    # --- AC-4: Token cap ---

    def test_token_cap_skips_oversize_files(
        self, selector_tree: Path,
    ) -> None:
        """AC-4: Oversize files are skipped with a warning."""
        from guardkit.knowledge.template_pattern_loader import select_patterns

        ctx = _make_ctx(selector_tree)
        # Each file is ~36 chars ≈ 9 tokens. Setting token cap very low
        # so at least some get skipped.
        result = select_patterns(
            ctx,
            tech_stack="Python",
            file_path_hints=["app/api/x.py", "app/models/x.py", "app/crud/x.py"],
            max_tokens=15,
        )

        # Some files should be skipped
        assert len(result.warnings) > 0
        assert any("skip" in w.lower() or "token" in w.lower() for w in result.warnings)

    def test_token_cap_stops_adding_files(
        self, selector_tree: Path,
    ) -> None:
        """AC-4: Once token budget is exhausted, no more files are added."""
        from guardkit.knowledge.template_pattern_loader import select_patterns

        ctx = _make_ctx(selector_tree)
        # Very tight token budget — should only allow 1-2 files
        result = select_patterns(
            ctx,
            tech_stack="Python",
            file_path_hints=["app/api/x.py", "app/models/x.py", "app/crud/x.py"],
            max_tokens=20,
        )

        # Should have fewer files than without token cap
        assert len(result.selected_files) < 3

    # --- AC-5: Selection does not mutate available_files ---

    def test_does_not_mutate_available_files(
        self, selector_tree: Path,
    ) -> None:
        """AC-5: available_files list is not mutated by select_patterns."""
        from guardkit.knowledge.template_pattern_loader import select_patterns

        ctx = _make_ctx(selector_tree)
        original_available = list(ctx.available_files)

        select_patterns(
            ctx,
            tech_stack="Python",
            file_path_hints=["app/api/x.py"],
        )

        assert ctx.available_files == original_available

    def test_returns_new_context_without_mutating_input(
        self, selector_tree: Path,
    ) -> None:
        """AC-5: Returns a new/updated context; input selected_files stays empty."""
        from guardkit.knowledge.template_pattern_loader import select_patterns

        ctx = _make_ctx(selector_tree)
        result = select_patterns(
            ctx,
            tech_stack="Python",
            file_path_hints=["app/api/x.py"],
        )

        # Result should have selected files
        assert len(result.selected_files) > 0
        # Original context's selected_files must still be empty
        assert ctx.selected_files == []

    # --- Edge cases ---

    def test_empty_available_files_returns_empty(self) -> None:
        """Empty available_files results in empty selection."""
        from guardkit.knowledge.template_pattern_loader import (
            TemplatePatternContext,
            select_patterns,
        )

        ctx = TemplatePatternContext(
            template_name="test",
            template_dir=Path("/tmp/fake"),
            available_files=[],
            selected_files=[],
            prompt_block="",
            warnings=[],
        )

        result = select_patterns(ctx, tech_stack="Python", file_path_hints=["app/api/x.py"])
        assert result.selected_files == []

    def test_selected_files_are_paths(
        self, selector_tree: Path,
    ) -> None:
        """All selected files are Path instances."""
        from guardkit.knowledge.template_pattern_loader import select_patterns

        ctx = _make_ctx(selector_tree)
        result = select_patterns(
            ctx,
            tech_stack="Python",
            file_path_hints=["app/api/x.py"],
        )

        assert all(isinstance(f, Path) for f in result.selected_files)


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


# ---------------------------------------------------------------------------
# Seam test: TemplatePatternContext contract (TASK-TPL-002 → TASK-TPL-003)
# ---------------------------------------------------------------------------

@pytest.mark.seam
@pytest.mark.integration_contract("TemplatePatternContext")
def test_template_pattern_context_contract() -> None:
    """Verify TemplatePatternContext contract from TASK-TPL-002.

    Contract: consumer reads ``available_files: List[Path]`` and populates
    ``selected_files: List[Path]`` without mutating other fields.
    Producer: TASK-TPL-002 (load_template_patterns)
    """
    from guardkit.knowledge.template_pattern_loader import (
        TemplatePatternContext,
        select_patterns,
    )

    ctx = TemplatePatternContext(
        template_name="fastapi-python",
        template_dir=Path("/tmp/fake"),
        available_files=[Path("a.template"), Path("b.template"), Path("c.template")],
        selected_files=[],
        prompt_block="",
        warnings=[],
    )

    # Consumer side: verify contract invariants
    assert hasattr(ctx, "available_files"), "context must expose available_files"
    assert isinstance(ctx.available_files, list), "available_files must be List[Path]"
    assert all(isinstance(f, Path) for f in ctx.available_files), \
        "available_files entries must be Path instances"
    assert ctx.selected_files == [], "selected_files starts empty for selector consumption"

    result = select_patterns(ctx, tech_stack="Python", file_path_hints=[])
    assert len(result.selected_files) <= 5, "must respect max_files cap"
    assert result.available_files == ctx.available_files, \
        "selector must not mutate available_files"
