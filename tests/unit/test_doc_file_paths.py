"""Validate that file paths referenced in documentation are not dead links.

TASK-TPL-007 AC-004: All referenced file paths in docs match reality (no dead links).

This test parses key documentation files and verifies that:
1. Source code paths referenced in the AutoBuild Instrumentation Guide exist.
2. Relative markdown links in task files resolve to existing files.
3. The feature spec file referenced from the guide exists.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Project root — the FEAT-4396 worktree
_WORKTREE = Path(__file__).resolve().parent.parent.parent


class TestAutoBuildInstrumentationGuideFilePaths:
    """Verify source-code paths referenced in the instrumentation guide."""

    GUIDE_PATH = _WORKTREE / "docs" / "guides" / "autobuild-instrumentation-guide.md"

    # Source code paths from the File Locations table
    SOURCE_CODE_PATHS = [
        "guardkit/orchestrator/instrumentation/schemas.py",
        "guardkit/orchestrator/instrumentation/emitter.py",
        "guardkit/orchestrator/instrumentation/redaction.py",
        "guardkit/orchestrator/instrumentation/digests.py",
        "guardkit/orchestrator/instrumentation/prompt_profile.py",
        "guardkit/orchestrator/instrumentation/concurrency.py",
        "guardkit/orchestrator/instrumentation/llm_instrumentation.py",
        "guardkit/knowledge/template_pattern_loader.py",
        "guardkit/templates/resolver.py",
        "guardkit/knowledge/autobuild_context_loader.py",
        "tests/unit/test_template_pattern_loader.py",
    ]

    # Source directories from the File Locations table
    SOURCE_DIRS = [
        "tests/orchestrator/instrumentation",
    ]

    # Related documentation links (relative to docs/guides/)
    RELATED_DOCS = [
        "docs/guides/autobuild-workflow.md",
        "docs/guides/local-backend-autobuild-guide.md",
        "docs/guides/cli-vs-claude-code.md",
        "docs/features/FEAT-TPL-PLAYER-template-pattern-player-context.md",
    ]

    def test_guide_exists(self) -> None:
        """The AutoBuild Instrumentation Guide itself exists."""
        assert self.GUIDE_PATH.is_file(), (
            f"Guide not found at {self.GUIDE_PATH}"
        )

    @pytest.mark.parametrize("rel_path", SOURCE_CODE_PATHS)
    def test_source_code_path_exists(self, rel_path: str) -> None:
        """Each source code file referenced in the File Locations table exists."""
        full_path = _WORKTREE / rel_path
        assert full_path.is_file(), (
            f"Dead reference in instrumentation guide: {rel_path} "
            f"(resolved to {full_path})"
        )

    @pytest.mark.parametrize("rel_dir", SOURCE_DIRS)
    def test_source_dir_exists(self, rel_dir: str) -> None:
        """Each source directory referenced in the File Locations table exists."""
        full_path = _WORKTREE / rel_dir
        assert full_path.is_dir(), (
            f"Dead directory reference in instrumentation guide: {rel_dir} "
            f"(resolved to {full_path})"
        )

    @pytest.mark.parametrize("rel_path", RELATED_DOCS)
    def test_related_doc_exists(self, rel_path: str) -> None:
        """Each related documentation link in the guide resolves to a real file."""
        full_path = _WORKTREE / rel_path
        assert full_path.is_file(), (
            f"Dead doc link in instrumentation guide: {rel_path} "
            f"(resolved to {full_path})"
        )

    def test_template_pattern_context_section_exists(self) -> None:
        """The Template Pattern Context section was added to the guide."""
        content = self.GUIDE_PATH.read_text(encoding="utf-8")
        assert "## Template Pattern Context" in content, (
            "Missing 'Template Pattern Context' section in instrumentation guide"
        )

    def test_template_pattern_context_has_data_flow(self) -> None:
        """The Template Pattern Context section includes a data flow diagram."""
        content = self.GUIDE_PATH.read_text(encoding="utf-8")
        assert "### Data Flow" in content, (
            "Missing 'Data Flow' subsection in Template Pattern Context"
        )

    def test_template_pattern_context_has_key_components(self) -> None:
        """The Template Pattern Context section includes key components table."""
        content = self.GUIDE_PATH.read_text(encoding="utf-8")
        assert "### Key Components" in content, (
            "Missing 'Key Components' subsection in Template Pattern Context"
        )

    def test_template_pattern_context_has_graceful_degradation(self) -> None:
        """The Template Pattern Context section documents graceful degradation."""
        content = self.GUIDE_PATH.read_text(encoding="utf-8")
        assert "### Graceful Degradation" in content, (
            "Missing 'Graceful Degradation' subsection in Template Pattern Context"
        )


class TestTaskFileReferences:
    """Verify relative markdown links in task files resolve."""

    def test_f4b8a_points_at_feature_spec(self) -> None:
        """F4B8a (TASK-DRF-F4B8) references FEAT-TPL-PLAYER spec."""
        task_path = (
            _WORKTREE / "tasks" / "backlog"
            / "TASK-DRF-F4B8-clarify-template-scaffolding-vs-config-layer.md"
        )
        content = task_path.read_text(encoding="utf-8")
        assert "FEAT-TPL-PLAYER" in content, (
            "F4B8a does not reference FEAT-TPL-PLAYER"
        )
        assert "TASK-TPL-007" in content, (
            "F4B8a does not reference TASK-TPL-007 (the doc task that completed it)"
        )

    def test_f4b8b_closed_with_rationale(self) -> None:
        """F4B8b (TASK-REN-B9F2) is closed with 'consumer exists' rationale."""
        task_path = (
            _WORKTREE / "tasks" / "backlog" / "template-pattern-layer"
            / "TASK-REN-B9F2-rename-templates-to-patterns.md"
        )
        content = task_path.read_text(encoding="utf-8")
        assert "status: closed" in content, (
            "TASK-REN-B9F2 is not marked as closed"
        )
        assert "Consumer exists, no rename needed" in content, (
            "TASK-REN-B9F2 does not contain required closure rationale"
        )

    def test_doc_c3d7_completed(self) -> None:
        """TASK-DOC-C3D7 is marked as completed by TASK-TPL-007."""
        task_path = (
            _WORKTREE / "tasks" / "backlog" / "template-pattern-layer"
            / "TASK-DOC-C3D7-document-two-layer-template-model.md"
        )
        content = task_path.read_text(encoding="utf-8")
        assert "status: completed" in content, (
            "TASK-DOC-C3D7 is not marked as completed"
        )
        assert "TASK-TPL-007" in content, (
            "TASK-DOC-C3D7 does not reference TASK-TPL-007"
        )

    def test_f4b8a_subtask_links_resolve(self) -> None:
        """All relative links in F4B8a resolve to existing files."""
        task_dir = _WORKTREE / "tasks" / "backlog"
        task_path = task_dir / "TASK-DRF-F4B8-clarify-template-scaffolding-vs-config-layer.md"
        content = task_path.read_text(encoding="utf-8")

        # Extract markdown links: [text](path)
        links = re.findall(r'\[.*?\]\(((?!http)[^)]+)\)', content)

        # Filter to .md file links only (skip anchor-only links)
        md_links = [
            link.split("#")[0]  # strip anchor fragments
            for link in links
            if link.endswith(".md") or ".md#" in link
        ]

        broken = []
        for link in md_links:
            resolved = (task_dir / link).resolve()
            if not resolved.is_file():
                broken.append(f"{link} → {resolved}")

        assert not broken, (
            f"Broken links in TASK-DRF-F4B8:\n" + "\n".join(broken)
        )

    def test_doc_c3d7_guide_link_resolves(self) -> None:
        """TASK-DOC-C3D7's link to the instrumentation guide resolves."""
        task_dir = (
            _WORKTREE / "tasks" / "backlog" / "template-pattern-layer"
        )
        # The link from TASK-DOC-C3D7: ../../../docs/guides/autobuild-instrumentation-guide.md
        guide_path = (task_dir / "../../../docs/guides/autobuild-instrumentation-guide.md").resolve()
        assert guide_path.is_file(), (
            f"TASK-DOC-C3D7's link to instrumentation guide is broken: {guide_path}"
        )


class TestGuideConsistencyWithCode:
    """Verify that documentation claims match the actual code."""

    def test_manifest_name_field_documented_correctly(self) -> None:
        """The guide says manifest uses `name` field — verify the code agrees."""
        loader_path = _WORKTREE / "guardkit" / "knowledge" / "template_pattern_loader.py"
        content = loader_path.read_text(encoding="utf-8")
        # The code should extract `name` from the manifest, not `template`
        assert 'data.get("name")' in content, (
            "template_pattern_loader.py does not use `name` field as documented"
        )

    def test_max_files_default_documented_correctly(self) -> None:
        """The guide says max 5 files — verify the code agrees."""
        loader_path = _WORKTREE / "guardkit" / "knowledge" / "template_pattern_loader.py"
        content = loader_path.read_text(encoding="utf-8")
        assert "max_files: int = 5" in content, (
            "select_patterns max_files default does not match documented value of 5"
        )

    def test_max_tokens_default_documented_correctly(self) -> None:
        """The guide says ~3000 tokens — verify the code agrees."""
        loader_path = _WORKTREE / "guardkit" / "knowledge" / "template_pattern_loader.py"
        content = loader_path.read_text(encoding="utf-8")
        assert "max_tokens: int = 3000" in content, (
            "select_patterns max_tokens default does not match documented value of 3000"
        )

    def test_prompt_header_documented_correctly(self) -> None:
        """The guide mentions 'Stack Pattern Reference' — verify the code uses it."""
        loader_path = _WORKTREE / "guardkit" / "knowledge" / "autobuild_context_loader.py"
        content = loader_path.read_text(encoding="utf-8")
        assert "Stack Pattern Reference" in content, (
            "format_pattern_block does not use 'Stack Pattern Reference' header"
        )

    def test_append_template_patterns_method_exists(self) -> None:
        """The documented _append_template_patterns method exists in the code."""
        loader_path = _WORKTREE / "guardkit" / "knowledge" / "autobuild_context_loader.py"
        content = loader_path.read_text(encoding="utf-8")
        assert "def _append_template_patterns(" in content, (
            "_append_template_patterns method not found in autobuild_context_loader.py"
        )
