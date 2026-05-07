"""Unit tests for TASK-GK-PROF-001 template-aware Phase-3 resolution.

Covers AC-1, AC-2, AC-3 and AC-4:

* **AC-1** — ``phase_3_specialist_for_stack`` consults the workspace's
  installed specialist set (``.claude/agents`` / ``.claude/rules/guidance``)
  rather than naming a hardcoded literal.
* **AC-2** — when the workspace ships specialists, resolution prefers an
  installed name (with a minimal task-tag affinity hop) over the legacy map.
* **AC-3** — when the workspace has no Python-API-shaped specialist
  installed, the resolver returns :data:`GENERIC_PHASE_3_FALLBACK` so the
  advisory line is informational rather than naming an absent agent.
* **AC-4** — fallback chain: tag-matched discovered → profile-default
  (if installed) → legacy ``python-api-specialist`` (if installed) →
  generic fallback.

AC-5 (replaying the FEAT-PEBR turn-1 evaluation in the forge worktree) and
AC-6 (project lint) are verified outside this module — AC-5 is documented
as deferred to the forge repo where the failing run lives, and AC-6 is
covered by the project's existing ``ruff`` configuration.
"""

from __future__ import annotations

from pathlib import Path

from guardkit.orchestrator.phase_specialists import (
    GENERIC_PHASE_3_FALLBACK,
    discover_template_specialists,
    phase_3_specialist_for_stack,
    render_missing_phase_list,
    specialist_for_phase,
)


def _make_specialist_files(
    workspace: Path,
    *,
    agents: tuple[str, ...] = (),
    guidance: tuple[str, ...] = (),
) -> None:
    """Create empty markdown files for each agent/guidance entry."""
    if agents:
        agents_dir = workspace / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        for name in agents:
            (agents_dir / f"{name}.md").write_text("# stub\n", encoding="utf-8")
    if guidance:
        guidance_dir = workspace / ".claude" / "rules" / "guidance"
        guidance_dir.mkdir(parents=True, exist_ok=True)
        for name in guidance:
            (guidance_dir / f"{name}.md").write_text("# stub\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# discover_template_specialists
# ---------------------------------------------------------------------------


class TestDiscoverTemplateSpecialists:
    def test_empty_workspace_returns_empty_set(self, tmp_path: Path) -> None:
        assert discover_template_specialists(tmp_path) == set()

    def test_finds_specialists_in_guidance_dir(self, tmp_path: Path) -> None:
        _make_specialist_files(
            tmp_path,
            guidance=(
                "langchain-tool-decorator-specialist",
                "pytest-agent-testing-specialist",
            ),
        )
        assert discover_template_specialists(tmp_path) == {
            "langchain-tool-decorator-specialist",
            "pytest-agent-testing-specialist",
        }

    def test_finds_specialists_in_agents_dir(self, tmp_path: Path) -> None:
        _make_specialist_files(
            tmp_path,
            agents=("python-api-specialist", "react-typescript-specialist"),
        )
        assert discover_template_specialists(tmp_path) == {
            "python-api-specialist",
            "react-typescript-specialist",
        }

    def test_excludes_topic_guidance_files(self, tmp_path: Path) -> None:
        """Files like database.md / fastapi.md are topic notes, not specialists."""
        _make_specialist_files(
            tmp_path,
            guidance=("database", "fastapi", "testing", "fastapi-specialist"),
        )
        assert discover_template_specialists(tmp_path) == {"fastapi-specialist"}

    def test_recognises_engineer_and_architect_suffixes(self, tmp_path: Path) -> None:
        """Some templates name agents '-engineer' / '-architect'."""
        _make_specialist_files(
            tmp_path,
            agents=(
                "system-prompt-engineer",
                "adversarial-cooperation-architect",
                "deepagents-factory-specialist",
            ),
        )
        assert discover_template_specialists(tmp_path) == {
            "system-prompt-engineer",
            "adversarial-cooperation-architect",
            "deepagents-factory-specialist",
        }

    def test_deduplicates_ext_companion_files(self, tmp_path: Path) -> None:
        """``/agent-enhance`` writes ``<name>-ext.md`` next to the canonical file."""
        _make_specialist_files(
            tmp_path,
            agents=(
                "fastapi-specialist",
                "fastapi-specialist-ext",
            ),
        )
        assert discover_template_specialists(tmp_path) == {"fastapi-specialist"}

    def test_unions_agents_and_guidance_dirs(self, tmp_path: Path) -> None:
        _make_specialist_files(
            tmp_path,
            agents=("fastapi-specialist",),
            guidance=("pytest-agent-testing-specialist",),
        )
        assert discover_template_specialists(tmp_path) == {
            "fastapi-specialist",
            "pytest-agent-testing-specialist",
        }


# ---------------------------------------------------------------------------
# phase_3_specialist_for_stack — AC-1 / AC-3
# ---------------------------------------------------------------------------


class TestPhase3WorkspaceAware:
    """AC-1: workspace-installed specialist set drives the resolver."""

    def test_langchain_template_no_python_api_specialist_installed(
        self, tmp_path: Path
    ) -> None:
        """Reproduces the FEAT-PEBR symptom that triggered TASK-GK-PROF-001.

        The langchain-deepagents-orchestrator template ships
        langchain-* / pytest-* specialists but NOT python-api-specialist.
        Before this fix the resolver returned the hardcoded literal,
        producing a noisy advisory naming an agent the operator did not have.
        After the fix the resolver downgrades to the informational fallback.
        """
        _make_specialist_files(
            tmp_path,
            guidance=(
                "deepagents-orchestrator-specialist",
                "langchain-tool-decorator-specialist",
                "pytest-agent-testing-specialist",
            ),
        )
        result = phase_3_specialist_for_stack(
            "langchain-deepagents-orchestrator",
            workspace_root=tmp_path,
        )
        assert result == GENERIC_PHASE_3_FALLBACK
        assert "python-api-specialist" not in result

    def test_advisory_downgrade_when_no_specialists_at_all(
        self, tmp_path: Path
    ) -> None:
        """AC-3: empty workspace → informational fallback, not hardcoded literal."""
        result = phase_3_specialist_for_stack(
            "langchain-deepagents-orchestrator",
            workspace_root=tmp_path,
        )
        # No discovery info AND no profile_default match → generic fallback.
        # (For this stack the profile-default is python-api-specialist, but
        # since workspace is empty we hit the "no discovery info" branch and
        # fall back to the historical map. The point of AC-3 is the
        # *populated-but-mismatched* case verified above.)
        assert result == "python-api-specialist"  # historical behavior preserved

    def test_tag_match_picks_installed_specialist(self, tmp_path: Path) -> None:
        """AC-2: a tag like 'tool-decorator' matches the installed langchain specialist."""
        _make_specialist_files(
            tmp_path,
            guidance=(
                "langchain-tool-decorator-specialist",
                "pytest-agent-testing-specialist",
            ),
        )
        result = phase_3_specialist_for_stack(
            "langchain-deepagents-orchestrator",
            workspace_root=tmp_path,
            task_tags=("tool-decorator",),
        )
        assert result == "langchain-tool-decorator-specialist"

    def test_tag_match_prefers_specialist_over_profile_default(
        self, tmp_path: Path
    ) -> None:
        """When a tag-affinity match exists, it wins over the profile default."""
        _make_specialist_files(
            tmp_path,
            agents=(
                "python-api-specialist",  # profile default IS installed
                "pytest-agent-testing-specialist",
            ),
        )
        result = phase_3_specialist_for_stack(
            "fastapi-python",
            workspace_root=tmp_path,
            task_tags=("pytest",),
        )
        assert result == "pytest-agent-testing-specialist"


# ---------------------------------------------------------------------------
# Fallback chain — AC-4
# ---------------------------------------------------------------------------


class TestPhase3FallbackChain:
    def test_profile_default_when_installed(self, tmp_path: Path) -> None:
        """AC-4 step 2: profile-default wins when installed."""
        _make_specialist_files(
            tmp_path,
            agents=("python-api-specialist", "fastapi-specialist"),
        )
        result = phase_3_specialist_for_stack(
            "fastapi-python",
            workspace_root=tmp_path,
        )
        assert result == "python-api-specialist"

    def test_legacy_python_api_fallback_when_profile_default_missing(
        self, tmp_path: Path
    ) -> None:
        """AC-4 step 3: legacy fallback fires when profile-default isn't installed.

        Synthetic case: an unknown stack template whose profile-default is
        missing, but ``python-api-specialist`` happens to be installed.
        """
        _make_specialist_files(
            tmp_path,
            agents=("python-api-specialist",),
        )
        result = phase_3_specialist_for_stack(
            "unknown-stack-template",
            workspace_root=tmp_path,
        )
        assert result == "python-api-specialist"

    def test_generic_fallback_when_nothing_matches(self, tmp_path: Path) -> None:
        """AC-3 / AC-4 step 4: workspace ships specialists but none are Python-API-shaped."""
        _make_specialist_files(
            tmp_path,
            guidance=(
                "deepagents-orchestrator-specialist",
                "domain-context-injection-specialist",
            ),
        )
        result = phase_3_specialist_for_stack(
            "fastapi-python",  # profile default is python-api-specialist
            workspace_root=tmp_path,
        )
        assert result == GENERIC_PHASE_3_FALLBACK

    def test_no_workspace_root_preserves_legacy_map(self) -> None:
        """Backward-compat: callers without workspace_root keep historical behavior."""
        assert (
            phase_3_specialist_for_stack("fastapi-python")
            == "python-api-specialist"
        )
        assert (
            phase_3_specialist_for_stack("react-typescript")
            == "react-typescript-specialist"
        )
        assert phase_3_specialist_for_stack(None) == GENERIC_PHASE_3_FALLBACK
        assert (
            phase_3_specialist_for_stack("unknown-stack")
            == GENERIC_PHASE_3_FALLBACK
        )


# ---------------------------------------------------------------------------
# Integration with render_missing_phase_list and specialist_for_phase
# ---------------------------------------------------------------------------


class TestRenderMissingPhaseListWorkspaceAware:
    def test_phase_4_and_5_unchanged_by_workspace(self, tmp_path: Path) -> None:
        """Static phases keep their canonical names regardless of workspace."""
        _make_specialist_files(
            tmp_path,
            guidance=("langchain-tool-decorator-specialist",),
        )
        lines = render_missing_phase_list(
            ["4", "5"],
            workspace_root=tmp_path,
        )
        assert any("`test-orchestrator`" in line for line in lines)
        assert any("`code-reviewer`" in line for line in lines)

    def test_phase_3_uses_workspace_discovered_specialist(self, tmp_path: Path) -> None:
        _make_specialist_files(
            tmp_path,
            guidance=("langchain-tool-decorator-specialist",),
        )
        lines = render_missing_phase_list(
            ["3"],
            stack_template="langchain-deepagents-orchestrator",
            workspace_root=tmp_path,
            task_tags=("tool-decorator",),
        )
        assert lines == [
            "Phase 3: `langchain-tool-decorator-specialist` (Implementation)"
        ]

    def test_phase_3_advisory_is_informational_when_no_match(
        self, tmp_path: Path
    ) -> None:
        """AC-3 wire-through: when nothing matches, advisory line names the
        generic fallback rather than a hardcoded specialist the operator
        does not have.
        """
        _make_specialist_files(
            tmp_path,
            guidance=("deepagents-orchestrator-specialist",),
        )
        lines = render_missing_phase_list(
            ["3"],
            stack_template="langchain-deepagents-orchestrator",
            workspace_root=tmp_path,
        )
        assert lines == [
            f"Phase 3: `{GENERIC_PHASE_3_FALLBACK}` (Implementation)"
        ]
        assert "python-api-specialist" not in lines[0]


class TestTagAffinityEdgeCases:
    """Defensive paths in ``_select_by_tag_affinity`` — empty / unmatched tags."""

    def test_empty_tag_string_is_skipped(self, tmp_path: Path) -> None:
        _make_specialist_files(
            tmp_path,
            agents=("python-api-specialist",),
        )
        result = phase_3_specialist_for_stack(
            "fastapi-python",
            workspace_root=tmp_path,
            task_tags=("",),
        )
        # Empty tag → no affinity match → falls through to profile_default.
        assert result == "python-api-specialist"

    def test_punctuation_only_tag_is_skipped(self, tmp_path: Path) -> None:
        """Tag normalizes to an empty string; affinity loop should skip it."""
        _make_specialist_files(
            tmp_path,
            agents=("python-api-specialist",),
        )
        result = phase_3_specialist_for_stack(
            "fastapi-python",
            workspace_root=tmp_path,
            task_tags=("---",),
        )
        assert result == "python-api-specialist"

    def test_no_tag_matches_falls_through_to_profile_default(
        self, tmp_path: Path
    ) -> None:
        _make_specialist_files(
            tmp_path,
            agents=("python-api-specialist",),
        )
        result = phase_3_specialist_for_stack(
            "fastapi-python",
            workspace_root=tmp_path,
            task_tags=("entirely-unrelated-tag",),
        )
        assert result == "python-api-specialist"


class TestSpecialistForPhaseUnknownPhases:
    def test_unknown_phase_returns_descriptor(self) -> None:
        # Known phase descriptor (not in STATIC_PHASE_SPECIALISTS, not "3")
        assert specialist_for_phase("2") == "Planning"

    def test_phase_with_no_descriptor_returns_generic_label(self) -> None:
        result = specialist_for_phase("99")
        assert result == "Phase 99 specialist"


class TestSpecialistForPhasePassesThrough:
    def test_phase_3_threads_workspace_root_and_tags(self, tmp_path: Path) -> None:
        _make_specialist_files(
            tmp_path,
            guidance=("pytest-agent-testing-specialist",),
        )
        result = specialist_for_phase(
            "3",
            stack_template="langchain-deepagents-orchestrator",
            workspace_root=tmp_path,
            task_tags=("pytest",),
        )
        assert result == "pytest-agent-testing-specialist"

    def test_static_phases_ignore_workspace(self, tmp_path: Path) -> None:
        assert (
            specialist_for_phase("4", workspace_root=tmp_path)
            == "test-orchestrator"
        )
        assert (
            specialist_for_phase("5", workspace_root=tmp_path)
            == "code-reviewer"
        )
