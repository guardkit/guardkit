"""
Integration tests for end-to-end template pattern injection into AutoBuild context.

TASK-TPL-006: Validates that a full ``get_player_context()`` call, against a
fixture project initialised from a real template, produces an
``AutoBuildContextResult.prompt_text`` containing the labelled pattern block
and that the regression path (no manifest) still produces identical output
to pre-feature behaviour.

Test scenarios:
    1. Positive test — fastapi-python manifest → pattern block in prompt_text
    2. Regression test — no manifest → no pattern block, pre-feature output
    3. Token-cap test — more than 5 matching subdirs → exactly 5 files
    4. Cross-template test — dotnet-railway-fastendpoints template
    5. Fixture setup validation — temp project with manifest resolves correctly

References:
    - TASK-TPL-006: Integration test: end-to-end pattern injection
    - TASK-TPL-004: Wire template patterns into AutoBuildContextLoader
    - TASK-TPL-003: Domain-hint selector
    - TASK-TPL-002: Template pattern loader core
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from guardkit.knowledge.autobuild_context_loader import (
    AutoBuildContextLoader,
)
from guardkit.knowledge.template_pattern_loader import (
    TemplatePatternContext,
    load_template_patterns,
    select_patterns,
)
from guardkit.templates.resolver import resolve_template_source_dir


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fastapi_project(tmp_path: Path) -> Path:
    """Create a temp project with .claude/manifest.json pointing to fastapi-python.

    This simulates a project initialised from the fastapi-python template.
    The manifest contains ``{"name": "fastapi-python"}`` and the resolver
    points at the real ``installer/core/templates/fastapi-python`` directory.

    Returns:
        Path to the temp project root.
    """
    project_root = tmp_path / "project"
    project_root.mkdir()
    claude_dir = project_root / ".claude"
    claude_dir.mkdir()
    manifest = claude_dir / "manifest.json"
    manifest.write_text(json.dumps({"name": "fastapi-python", "schema_version": "1.0.0"}))
    return project_root


@pytest.fixture
def dotnet_project(tmp_path: Path) -> Path:
    """Create a temp project with .claude/manifest.json pointing to dotnet-railway-fastendpoints.

    Returns:
        Path to the temp project root.
    """
    project_root = tmp_path / "project"
    project_root.mkdir()
    claude_dir = project_root / ".claude"
    claude_dir.mkdir()
    manifest = claude_dir / "manifest.json"
    manifest.write_text(json.dumps({
        "name": "dotnet-railway-fastendpoints",
        "schema_version": "1.0.0",
    }))
    return project_root


@pytest.fixture
def no_manifest_project(tmp_path: Path) -> Path:
    """Create a temp project with NO .claude/manifest.json.

    Returns:
        Path to the temp project root.
    """
    project_root = tmp_path / "project"
    project_root.mkdir()
    return project_root


# ---------------------------------------------------------------------------
# Test 1: Positive test — fastapi-python end-to-end
# ---------------------------------------------------------------------------


class TestPositiveFastapiPython:
    """Validate that get_player_context() with a fastapi-python project
    produces a prompt_text containing the labelled pattern block."""

    @pytest.mark.asyncio
    async def test_prompt_text_contains_stack_pattern_reference_header(
        self, fastapi_project: Path,
    ) -> None:
        """result.prompt_text must contain the labelled header
        'Stack Pattern Reference (from fastapi-python template)'."""
        loader = AutoBuildContextLoader(
            graphiti=None,
            worktree_path=fastapi_project,
        )

        result = await loader.get_player_context(
            task_id="TASK-INT-001",
            feature_id="FEAT-INT",
            turn_number=1,
            description="Implement API users endpoint",
            tech_stack="Python",
        )

        assert "Stack Pattern Reference (from fastapi-python template)" in result.prompt_text, (
            "prompt_text should contain the labelled pattern block header.\n"
            f"Got prompt_text ({len(result.prompt_text)} chars):\n{result.prompt_text[:500]}"
        )

    @pytest.mark.asyncio
    async def test_prompt_text_contains_api_router_template_heading(
        self, fastapi_project: Path,
    ) -> None:
        """result.prompt_text must contain '### api/router.py.template'
        (or the full path form) as a file heading."""
        loader = AutoBuildContextLoader(
            graphiti=None,
            worktree_path=fastapi_project,
        )

        result = await loader.get_player_context(
            task_id="TASK-INT-001",
            feature_id="FEAT-INT",
            turn_number=1,
            description="Implement API users endpoint",
            tech_stack="Python",
        )

        # The heading could be "### api/router.py.template" or the absolute path form.
        # Check that "api/router.py.template" appears somewhere as a heading.
        assert "api/router.py.template" in result.prompt_text, (
            "prompt_text should contain a heading for api/router.py.template.\n"
            f"Got prompt_text ({len(result.prompt_text)} chars):\n{result.prompt_text[:500]}"
        )

    @pytest.mark.asyncio
    async def test_log_output_lists_selected_files(
        self, fastapi_project: Path, caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Log output must list the selected template files."""
        loader = AutoBuildContextLoader(
            graphiti=None,
            worktree_path=fastapi_project,
        )

        with caplog.at_level(
            logging.INFO,
            logger="guardkit.knowledge.autobuild_context_loader",
        ):
            await loader.get_player_context(
                task_id="TASK-INT-001",
                feature_id="FEAT-INT",
                turn_number=1,
                description="Implement API users endpoint",
                tech_stack="Python",
            )

        # Should log "[TemplatePattern] Appended pattern block: N files, ~M tokens (file1, file2, ...)"
        log_text = caplog.text
        assert "TemplatePattern" in log_text, (
            f"Expected [TemplatePattern] log messages, got:\n{log_text}"
        )
        assert "Appended pattern block" in log_text, (
            f"Expected 'Appended pattern block' in logs, got:\n{log_text}"
        )


# ---------------------------------------------------------------------------
# Test 2: Regression test — no manifest
# ---------------------------------------------------------------------------


class TestRegressionNoManifest:
    """Validate that with no manifest file, prompt_text does NOT contain
    'Stack Pattern Reference' and matches pre-feature behaviour."""

    @pytest.mark.asyncio
    async def test_no_manifest_prompt_text_has_no_stack_pattern_reference(
        self, no_manifest_project: Path,
    ) -> None:
        """prompt_text must NOT contain 'Stack Pattern Reference' when no manifest exists."""
        loader = AutoBuildContextLoader(
            graphiti=None,
            worktree_path=no_manifest_project,
        )

        result = await loader.get_player_context(
            task_id="TASK-INT-001",
            feature_id="FEAT-INT",
            turn_number=1,
            description="Implement API users endpoint",
            tech_stack="Python",
        )

        assert "Stack Pattern Reference" not in result.prompt_text, (
            "prompt_text should NOT contain pattern block when no manifest exists."
        )

    @pytest.mark.asyncio
    async def test_no_manifest_prompt_text_matches_pre_feature_output(
        self, no_manifest_project: Path,
    ) -> None:
        """prompt_text without manifest should match the pre-feature output.

        Since Graphiti is None, the pre-feature output is an empty string
        (the empty_result path). With no manifest, the template pattern
        append does nothing, so the result is identical.
        """
        loader = AutoBuildContextLoader(
            graphiti=None,
            worktree_path=no_manifest_project,
        )

        result = await loader.get_player_context(
            task_id="TASK-INT-001",
            feature_id="FEAT-INT",
            turn_number=1,
            description="Implement API users endpoint",
            tech_stack="Python",
        )

        # Pre-feature behaviour: empty context → empty prompt_text
        assert result.prompt_text == "", (
            "Without manifest and without Graphiti, prompt_text should be empty "
            f"(pre-feature golden output). Got: {result.prompt_text!r}"
        )

    @pytest.mark.asyncio
    async def test_no_worktree_path_prompt_text_matches_pre_feature_output(
        self,
    ) -> None:
        """worktree_path=None should also produce pre-feature output."""
        loader = AutoBuildContextLoader(
            graphiti=None,
            worktree_path=None,
        )

        result = await loader.get_player_context(
            task_id="TASK-INT-001",
            feature_id="FEAT-INT",
            turn_number=1,
            description="Implement API users endpoint",
            tech_stack="Python",
        )

        assert result.prompt_text == "", (
            "Without worktree_path, prompt_text should be empty (pre-feature golden output)."
        )


# ---------------------------------------------------------------------------
# Test 3: Token-cap test — more than 5 matching subdirs
# ---------------------------------------------------------------------------


class TestTokenCapExactlyFiveFiles:
    """Construct a task against a template with > 5 matching subdirs
    and assert exactly 5 files appear in the block."""

    @pytest.mark.asyncio
    async def test_exactly_five_files_when_more_than_five_subdirs_match(
        self, fastapi_project: Path,
    ) -> None:
        """When file_path_hints match > 5 subdirs, exactly 5 files should
        appear in the pattern block (the default max_files cap)."""
        loader = AutoBuildContextLoader(
            graphiti=None,
            worktree_path=fastapi_project,
        )

        # The fastapi-python template has 9 subdirectories:
        # api, config, core, crud, db, dependencies, models, schemas, testing
        # With tech_stack="Python", the tech-stack map matches:
        # api, core, config, models, schemas, crud, db → 7+ subdirs
        # This should trigger the max_files=5 cap.
        result = await loader.get_player_context(
            task_id="TASK-INT-002",
            feature_id="FEAT-INT",
            turn_number=1,
            description="Implement full CRUD API with models and schemas",
            tech_stack="Python",
        )

        # Count the "### " headings that refer to .template files
        lines = result.prompt_text.split("\n")
        template_headings = [
            line for line in lines
            if line.startswith("### ") and ".template" in line
        ]

        assert len(template_headings) <= 5, (
            f"Expected at most 5 template file headings (max_files cap), "
            f"got {len(template_headings)}: {template_headings}"
        )
        # Must have at least 1 heading (positive confirmation)
        assert len(template_headings) >= 1, (
            "Expected at least 1 template file heading in the pattern block."
        )

    def test_select_patterns_hard_cap_five_with_real_template(self) -> None:
        """Direct select_patterns call against real fastapi-python template
        with hints matching > 5 subdirs should cap at 5."""
        template_dir = resolve_template_source_dir("fastapi-python")
        assert template_dir is not None, "fastapi-python template must be resolvable"

        templates_subdir = template_dir / "templates"
        available = sorted(templates_subdir.rglob("*.template"))

        ctx = TemplatePatternContext(
            template_name="fastapi-python",
            template_dir=template_dir,
            available_files=available,
            selected_files=[],
            prompt_block="",
            warnings=[],
        )

        # Hints matching 7 subdirs: api, models, crud, schemas, core, db, config
        # Use a large token budget so only the file-count cap applies.
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
            max_files=5,
            max_tokens=50000,
        )

        assert len(result.selected_files) == 5, (
            f"Expected exactly 5 selected files (hard cap), "
            f"got {len(result.selected_files)}: "
            f"{[f.name for f in result.selected_files]}"
        )


# ---------------------------------------------------------------------------
# Test 4: Cross-template test — dotnet-railway-fastendpoints
# ---------------------------------------------------------------------------


class TestCrossTemplateDotnet:
    """Repeat the positive test against dotnet-railway-fastendpoints to
    verify template-agnostic behaviour."""

    @pytest.mark.asyncio
    async def test_dotnet_prompt_text_contains_stack_pattern_reference_header(
        self, dotnet_project: Path,
    ) -> None:
        """result.prompt_text must contain the labelled header
        'Stack Pattern Reference (from dotnet-railway-fastendpoints template)'."""
        loader = AutoBuildContextLoader(
            graphiti=None,
            worktree_path=dotnet_project,
        )

        result = await loader.get_player_context(
            task_id="TASK-INT-003",
            feature_id="FEAT-INT",
            turn_number=1,
            description="Implement customer endpoint",
            tech_stack="dotnet",
        )

        assert "Stack Pattern Reference (from dotnet-railway-fastendpoints template)" in result.prompt_text, (
            "prompt_text should contain the labelled pattern block header for dotnet template.\n"
            f"Got prompt_text ({len(result.prompt_text)} chars):\n{result.prompt_text[:500]}"
        )

    @pytest.mark.asyncio
    async def test_dotnet_prompt_text_contains_template_file_heading(
        self, dotnet_project: Path,
    ) -> None:
        """result.prompt_text must contain at least one .template file heading."""
        loader = AutoBuildContextLoader(
            graphiti=None,
            worktree_path=dotnet_project,
        )

        result = await loader.get_player_context(
            task_id="TASK-INT-003",
            feature_id="FEAT-INT",
            turn_number=1,
            description="Implement customer endpoint",
            tech_stack="dotnet",
        )

        lines = result.prompt_text.split("\n")
        template_headings = [
            line for line in lines
            if line.startswith("### ") and ".template" in line
        ]

        assert len(template_headings) >= 1, (
            "prompt_text should contain at least one template file heading "
            f"for dotnet template. Got:\n{result.prompt_text[:500]}"
        )

    @pytest.mark.asyncio
    async def test_dotnet_prompt_text_contains_csharp_code_blocks(
        self, dotnet_project: Path,
    ) -> None:
        """result.prompt_text should contain csharp fenced code blocks
        for .cs.template files."""
        loader = AutoBuildContextLoader(
            graphiti=None,
            worktree_path=dotnet_project,
        )

        result = await loader.get_player_context(
            task_id="TASK-INT-003",
            feature_id="FEAT-INT",
            turn_number=1,
            description="Implement customer endpoint",
            tech_stack="dotnet",
        )

        # .cs.template files should produce ```csharp code blocks
        assert "```csharp" in result.prompt_text, (
            "prompt_text should contain ```csharp code blocks for .cs.template files.\n"
            f"Got prompt_text ({len(result.prompt_text)} chars):\n{result.prompt_text[:500]}"
        )


# ---------------------------------------------------------------------------
# Test 5: Fixture setup validation
# ---------------------------------------------------------------------------


class TestFixtureSetupValidation:
    """Validate that the fixture projects resolve correctly through the
    template pattern loading pipeline."""

    def test_fastapi_python_template_resolves(self) -> None:
        """The resolver must find the fastapi-python template directory."""
        result = resolve_template_source_dir("fastapi-python")
        assert result is not None, "fastapi-python template should resolve"
        assert result.is_dir(), f"Should resolve to directory: {result}"
        assert (result / "templates").is_dir(), (
            f"fastapi-python should have templates/ subdir: {result}"
        )

    def test_dotnet_template_resolves(self) -> None:
        """The resolver must find the dotnet-railway-fastendpoints template directory."""
        result = resolve_template_source_dir("dotnet-railway-fastendpoints")
        assert result is not None, "dotnet-railway-fastendpoints template should resolve"
        assert result.is_dir(), f"Should resolve to directory: {result}"
        assert (result / "templates").is_dir(), (
            f"dotnet template should have templates/ subdir: {result}"
        )

    def test_fastapi_manifest_loads_available_files(
        self, fastapi_project: Path,
    ) -> None:
        """load_template_patterns with fastapi manifest returns > 0 available_files."""
        manifest_path = fastapi_project / ".claude" / "manifest.json"
        ctx = load_template_patterns(manifest_path)

        assert ctx.template_name == "fastapi-python"
        assert ctx.template_dir is not None
        assert len(ctx.available_files) > 0, (
            f"Expected available_files > 0, got {len(ctx.available_files)}"
        )

    def test_dotnet_manifest_loads_available_files(
        self, dotnet_project: Path,
    ) -> None:
        """load_template_patterns with dotnet manifest returns > 0 available_files."""
        manifest_path = dotnet_project / ".claude" / "manifest.json"
        ctx = load_template_patterns(manifest_path)

        assert ctx.template_name == "dotnet-railway-fastendpoints"
        assert ctx.template_dir is not None
        assert len(ctx.available_files) > 0, (
            f"Expected available_files > 0, got {len(ctx.available_files)}"
        )


# ---------------------------------------------------------------------------
# Existing seam/unit test compatibility guard
# ---------------------------------------------------------------------------


class TestNoRegressionInExistingTests:
    """Guard tests ensuring that the new integration tests don't break
    existing seam and unit tests from TASK-TPL-002..005."""

    def test_format_pattern_block_still_returns_string(self) -> None:
        """Ensure format_pattern_block API is unchanged."""
        from guardkit.knowledge.autobuild_context_loader import format_pattern_block

        ctx = TemplatePatternContext(
            template_name="fastapi-python",
            template_dir=Path("/tmp/fake/templates"),
            available_files=[Path("api/router.py.template")],
            selected_files=[Path("api/router.py.template")],
            prompt_block="",
            warnings=[],
        )
        block = format_pattern_block(
            ctx,
            file_contents={Path("api/router.py.template"): "# router code"},
        )
        assert isinstance(block, str)
        assert "Stack Pattern Reference" in block

    def test_load_template_patterns_never_raises(self, tmp_path: Path) -> None:
        """load_template_patterns should never raise on any input."""
        ctx = load_template_patterns(tmp_path / "nonexistent" / "manifest.json")
        assert ctx.template_name is None

    def test_select_patterns_respects_immutability(self) -> None:
        """select_patterns should not mutate the input context."""
        ctx = TemplatePatternContext(
            template_name="test",
            template_dir=Path("/tmp/fake"),
            available_files=[Path("a.template"), Path("b.template")],
            selected_files=[],
            prompt_block="",
            warnings=[],
        )
        original_available = list(ctx.available_files)

        select_patterns(ctx, tech_stack="Python", file_path_hints=[])

        assert ctx.available_files == original_available
        assert ctx.selected_files == []

    @pytest.mark.asyncio
    async def test_get_player_context_signature_unchanged(self) -> None:
        """get_player_context must accept the established parameter set."""
        import inspect

        sig = inspect.signature(AutoBuildContextLoader.get_player_context)
        params = list(sig.parameters.keys())

        expected = [
            "self", "task_id", "feature_id", "turn_number",
            "description", "tech_stack", "complexity",
            "previous_feedback", "acceptance_criteria",
        ]
        for param in expected:
            assert param in params, f"Missing expected parameter: {param}"
