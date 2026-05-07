"""Tests for TASK-GK-PA-002: explicit ``## Files to Create`` /
``## Files to Modify`` sections must be authoritative when present, and
the prose AC scan must be restricted to the ``## Acceptance Criteria``
section when those explicit sections are absent.

Reproduces the FEAT-PEBR run-2 root cause:

- TASK-FRR-PEB-FM-001 (commit ``02aac9c``) added ``## Files to Create``
  / ``## Files to Modify`` sections to the FRR-PEB tasks.
- ``AgentInvoker._scan_ac_for_missing_paths`` (the AC-005 escalation
  helper for the plan-audit fallback path) ignored those sections and
  scanned the **whole post-frontmatter body** for path-shaped tokens.
- TASK-FRR-PEB-003's ``## Implementation notes`` contained a prose
  bullet referencing ``src/forge/dispatch/autobuild_async.py`` (a typo
  cross-reference; the real file lives at
  ``src/forge/pipeline/dispatchers/autobuild_async.py``).
- The scanner flagged the typo path as missing, plan-audit fired
  ``severity=high``, Coach rejected every turn → 5 wasted turns.

Coverage Target: >=85%
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker


FIXTURE_ROOT = (
    Path(__file__).parent.parent / "fixtures" / "feat_pebr_run2_worktree"
)


# ==================== Fixtures ====================


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """Empty worktree with the standard ``tasks/in_progress`` directory."""
    (tmp_path / "tasks" / "in_progress").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def invoker(worktree: Path) -> AgentInvoker:
    return AgentInvoker(
        worktree_path=worktree,
        max_turns_per_agent=1,
        sdk_timeout_seconds=10,
    )


def _write_task(
    worktree: Path,
    task_id: str,
    body: str,
    *,
    state: str = "in_progress",
) -> Path:
    """Write a task file with a hand-crafted body (no AC list templating)."""
    content = (
        "---\n"
        f"id: {task_id}\n"
        "title: Test task\n"
        f"status: {state}\n"
        "---\n\n"
        f"{body}\n"
    )
    task_path = worktree / "tasks" / state / f"{task_id}.md"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    task_path.write_text(content)
    return task_path


# ==================== AC-1: Explicit sections are authoritative ====================


class TestExplicitSectionsAuthoritative:
    """When ``## Files to Create`` / ``## Files to Modify`` are
    non-empty, ``_extract_explicit_planned_files`` returns their union
    and the audit path consults that set instead of the prose scan."""

    def test_extract_returns_union_of_create_and_modify(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        body = (
            "# Task: Demo\n\n"
            "## Acceptance Criteria\n\n"
            "- [ ] AC-1: do the thing.\n\n"
            "## Files to Create\n\n"
            "- `src/foo/new_module.py`\n"
            "- `tests/test_new_module.py`\n\n"
            "## Files to Modify\n\n"
            "- `src/foo/__init__.py`\n"
        )
        _write_task(worktree, "TASK-EXP-001", body)

        explicit = invoker._extract_explicit_planned_files("TASK-EXP-001")

        assert explicit == {
            "src/foo/new_module.py",
            "tests/test_new_module.py",
            "src/foo/__init__.py",
        }

    def test_extract_strips_em_dash_descriptions(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        body = (
            "# Task: Demo\n\n"
            "## Files to Create\n\n"
            "- `src/foo/a.py` — the new thing\n"
            "- `src/foo/b.py` - dash-space description\n"
            "- `src/foo/c.py`\n"
        )
        _write_task(worktree, "TASK-EXP-002", body)

        explicit = invoker._extract_explicit_planned_files("TASK-EXP-002")

        assert explicit == {
            "src/foo/a.py",
            "src/foo/b.py",
            "src/foo/c.py",
        }

    def test_extract_preserves_hyphenated_path_when_no_separator(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        """Hyphenated directory names (``feat-pebr-rev2``) must survive
        bullet extraction. We strip on em-dash or ``" - "`` only — bare
        ``-`` is part of the path."""
        body = (
            "# Task: Demo\n\n"
            "## Files to Create\n\n"
            "- `feat-pebr-rev2/file-name.py`\n"
        )
        _write_task(worktree, "TASK-EXP-003", body)

        explicit = invoker._extract_explicit_planned_files("TASK-EXP-003")

        assert explicit == {"feat-pebr-rev2/file-name.py"}

    def test_extract_skips_placeholder_bullets(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        body = (
            "# Task: Demo\n\n"
            "## Files to Create\n\n"
            "- `_none_`\n"
            "- N/A\n"
            "- TBD\n"
            "- `src/foo/real.py`\n"
        )
        _write_task(worktree, "TASK-EXP-004", body)

        explicit = invoker._extract_explicit_planned_files("TASK-EXP-004")

        assert explicit == {"src/foo/real.py"}

    def test_section_with_subsection_header_keeps_extracting(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        """``### Subsection`` inside ``## Files to Create`` is allowed —
        the boundary regex uses ``(?=\\n##(?!#)|\\Z)`` so subsections
        don't terminate the section."""
        body = (
            "# Task: Demo\n\n"
            "## Files to Create\n\n"
            "### Production code\n\n"
            "- `src/foo/a.py`\n\n"
            "### Tests\n\n"
            "- `tests/test_a.py`\n\n"
            "## Files to Modify\n\n"
            "- `src/foo/__init__.py`\n"
        )
        _write_task(worktree, "TASK-EXP-005", body)

        explicit = invoker._extract_explicit_planned_files("TASK-EXP-005")

        assert explicit == {
            "src/foo/a.py",
            "tests/test_a.py",
            "src/foo/__init__.py",
        }


# ==================== AC-3: FEAT-PEBR run-2 reproducer ====================


class TestRunTwoReproducer:
    """The TASK-FRR-PEB-003 body shape: 5 declared ``## Files to
    Create``, 2 declared ``## Files to Modify``, ``## Implementation
    notes`` references a typo path. Pre-fix:
    ``_scan_ac_for_missing_paths`` flagged the typo path because the
    scanner read the whole body. Post-fix:
    ``_extract_explicit_planned_files`` returns the 7 declared files
    (all present in the fixture worktree) and the prose typo is
    ignored."""

    def test_explicit_sections_returned_for_run2_shape(
        self, tmp_path: Path
    ) -> None:
        worktree = tmp_path / "worktree"
        shutil.copytree(FIXTURE_ROOT, worktree)
        invoker = AgentInvoker(
            worktree_path=worktree,
            max_turns_per_agent=1,
            sdk_timeout_seconds=10,
        )

        explicit = invoker._extract_explicit_planned_files(
            "TASK-FRR-PEB-003"
        )

        # All 7 declared paths from the fixture's task body.
        assert explicit == {
            "src/forge/lifecycle_bridge/translation.py",
            "src/forge/lifecycle_bridge/error_classifier.py",
            "src/forge/lifecycle_bridge/recovery_publisher.py",
            "src/forge/lifecycle_bridge/dead_letter_router.py",
            "tests/forge/lifecycle_bridge/test_translation.py",
            "src/forge/lifecycle_bridge/__init__.py",
            "src/forge/pipeline/dispatchers/autobuild_async.py",
        }

    def test_run2_typo_prose_path_is_not_in_extract_output(
        self, tmp_path: Path
    ) -> None:
        """The whole point: the typo path
        ``src/forge/dispatch/autobuild_async.py`` from
        ``## Implementation notes`` MUST NOT be in the extracted set,
        even though it's path-shaped and absent from the fixture
        worktree."""
        worktree = tmp_path / "worktree"
        shutil.copytree(FIXTURE_ROOT, worktree)
        invoker = AgentInvoker(
            worktree_path=worktree,
            max_turns_per_agent=1,
            sdk_timeout_seconds=10,
        )

        explicit = invoker._extract_explicit_planned_files(
            "TASK-FRR-PEB-003"
        )

        assert "src/forge/dispatch/autobuild_async.py" not in explicit


# ==================== AC-4: Missing declared file still fires ====================


class TestExplicitSectionsMissingFile:
    """Don't over-correct: when ``## Files to Create`` declares a path
    that doesn't exist in the worktree, the verdict still fires."""

    def test_compute_verdict_violation_when_declared_file_missing(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        body = (
            "# Task: Demo\n\n"
            "## Acceptance Criteria\n\n"
            "- [ ] AC-1: do the thing.\n\n"
            "## Files to Create\n\n"
            "- `src/foo/nonexistent.py`\n"
            "- `src/foo/also_missing.py`\n"
        )
        _write_task(worktree, "TASK-EXP-MISS-001", body)

        verdict = invoker._compute_plan_audit_verdict("TASK-EXP-MISS-001")

        assert verdict["status"] == "violation"
        assert verdict["severity"] == "high"
        assert verdict["missing_files"] == [
            "src/foo/also_missing.py",
            "src/foo/nonexistent.py",
        ]
        assert verdict["violations"] == 2

    def test_compute_verdict_passed_when_declared_file_present(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        (worktree / "src" / "foo").mkdir(parents=True)
        (worktree / "src" / "foo" / "real.py").write_text("")
        body = (
            "# Task: Demo\n\n"
            "## Acceptance Criteria\n\n"
            "- [ ] AC-1: do the thing.\n\n"
            "## Files to Create\n\n"
            "- `src/foo/real.py`\n"
        )
        _write_task(worktree, "TASK-EXP-MISS-002", body)

        verdict = invoker._compute_plan_audit_verdict("TASK-EXP-MISS-002")

        assert verdict["status"] == "passed"
        assert verdict["severity"] == "low"
        assert verdict["missing_files"] == []


# ==================== AC-2 + AC-5: AC-only fallback semantics ====================


class TestACOnlyFallback:
    """When neither ``## Files to Create`` nor ``## Files to Modify``
    is present, the prose scan runs — but only on the
    ``## Acceptance Criteria`` section. Prose paths in
    ``## Implementation notes`` etc. no longer trip the scanner."""

    def test_prose_path_in_implementation_notes_is_ignored(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        """AC-2 reproducer: a qualified missing path in
        ``## Implementation notes`` MUST NOT be flagged when the AC
        section itself doesn't reference it."""
        body = (
            "# Task: Demo\n\n"
            "## Acceptance Criteria\n\n"
            "- [ ] AC-1: ship the feature.\n\n"
            "## Implementation notes\n\n"
            "- Reference: `src/forge/dispatch/autobuild_async.py`'s "
            "existing pattern.\n"
        )
        _write_task(worktree, "TASK-AC-ONLY-001", body)

        missing = invoker._scan_ac_for_missing_paths("TASK-AC-ONLY-001")

        assert missing == []

    def test_qualified_missing_path_in_ac_section_is_flagged(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        """The AC-only slice still fires for genuine prose paths inside
        ``## Acceptance Criteria``."""
        body = (
            "# Task: Demo\n\n"
            "## Acceptance Criteria\n\n"
            "- [ ] AC-1: Modify `src/foo/totally_absent.py`.\n\n"
            "## Implementation notes\n\n"
            "- Reference: `src/forge/dispatch/autobuild_async.py`.\n"
        )
        _write_task(worktree, "TASK-AC-ONLY-002", body)

        missing = invoker._scan_ac_for_missing_paths("TASK-AC-ONLY-002")

        assert missing == ["src/foo/totally_absent.py"]

    def test_bare_basename_guard_preserved_on_ac_only_branch(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        """AC-5: TASK-GK-AC-001's basename guard still functions inside
        the AC-section slice. ``pipeline_consumer.py`` (no ``/``) in AC
        text where the file lives at
        ``src/forge/adapters/nats/pipeline_consumer.py`` MUST NOT be
        flagged."""
        deep = worktree / "src" / "forge" / "adapters" / "nats"
        deep.mkdir(parents=True)
        (deep / "pipeline_consumer.py").write_text("")
        body = (
            "# Task: Demo\n\n"
            "## Acceptance Criteria\n\n"
            "- [ ] AC-1: `pipeline_consumer.py` publishes a recovery "
            "event.\n"
        )
        _write_task(worktree, "TASK-AC-ONLY-003", body)

        missing = invoker._scan_ac_for_missing_paths("TASK-AC-ONLY-003")

        assert missing == []

    def test_subsection_inside_ac_does_not_terminate_slice(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        """``### Edge cases`` inside ``## Acceptance Criteria`` is part
        of the AC content — the slice's lookahead is ``(?=\\n##(?!#))``
        so subsections survive."""
        body = (
            "# Task: Demo\n\n"
            "## Acceptance Criteria\n\n"
            "- [ ] AC-1: ship the feature.\n\n"
            "### Edge cases\n\n"
            "- [ ] Modify `src/foo/totally_absent.py`.\n\n"
            "## Implementation notes\n\n"
            "- Reference: `src/forge/dispatch/autobuild_async.py`.\n"
        )
        _write_task(worktree, "TASK-AC-ONLY-004", body)

        missing = invoker._scan_ac_for_missing_paths("TASK-AC-ONLY-004")

        assert missing == ["src/foo/totally_absent.py"]


# ==================== AC-6: End-to-end through _compute_plan_audit_verdict ====================


class TestComputePlanAuditEndToEnd:
    """Full path: FEAT-PEBR run-2 fixture with explicit sections + typo
    prose → ``_compute_plan_audit_verdict`` returns ``status=passed``
    (was ``violation`` before TASK-GK-PA-002)."""

    def test_run2_fixture_passes_audit(self, tmp_path: Path) -> None:
        worktree = tmp_path / "worktree"
        shutil.copytree(FIXTURE_ROOT, worktree)
        invoker = AgentInvoker(
            worktree_path=worktree,
            max_turns_per_agent=1,
            sdk_timeout_seconds=10,
        )

        verdict = invoker._compute_plan_audit_verdict("TASK-FRR-PEB-003")

        # Pre-fix: status="violation", severity="high",
        # missing_files=["src/forge/dispatch/autobuild_async.py"].
        # Post-fix: explicit sections take precedence; all 7 declared
        # files are present on disk in the fixture.
        assert verdict["status"] == "passed", (
            f"expected passed, got {verdict['status']}: "
            f"missing_files={verdict.get('missing_files')}, "
            f"message={verdict.get('message')}"
        )
        assert verdict["violations"] == 0
        assert verdict["missing_files"] == []
        assert "src/forge/dispatch/autobuild_async.py" not in (
            verdict.get("missing_files") or []
        )

    def test_run2_fixture_violation_when_declared_file_removed(
        self, tmp_path: Path
    ) -> None:
        """Sanity check: deleting one of the declared files from the
        fixture worktree flips the verdict back to ``violation`` —
        confirms the explicit-sections branch is doing real work, not
        always passing."""
        worktree = tmp_path / "worktree"
        shutil.copytree(FIXTURE_ROOT, worktree)
        # Delete one of the declared ``## Files to Create`` entries.
        (worktree / "src" / "forge" / "lifecycle_bridge" / "translation.py").unlink()

        invoker = AgentInvoker(
            worktree_path=worktree,
            max_turns_per_agent=1,
            sdk_timeout_seconds=10,
        )

        verdict = invoker._compute_plan_audit_verdict("TASK-FRR-PEB-003")

        assert verdict["status"] == "violation"
        assert verdict["severity"] == "high"
        assert "src/forge/lifecycle_bridge/translation.py" in verdict[
            "missing_files"
        ]


# ==================== Empty-section semantics ====================


class TestEmptySectionSemantics:
    """A ``## Files to Create`` header with no parseable bullets is
    treated as **absent**, not authoritative-empty. Otherwise tasks
    with placeholder sections accidentally bypass the AC prose scan."""

    def test_header_only_section_is_treated_as_absent(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        body = (
            "# Task: Demo\n\n"
            "## Acceptance Criteria\n\n"
            "- [ ] AC-1: Modify `src/foo/missing_in_ac.py`.\n\n"
            "## Files to Create\n\n"
            "## Implementation notes\n\n"
            "- some prose.\n"
        )
        _write_task(worktree, "TASK-EMPTY-001", body)

        # Empty section → falls through to AC-only prose scan.
        explicit = invoker._extract_explicit_planned_files("TASK-EMPTY-001")
        assert explicit == set()

        verdict = invoker._compute_plan_audit_verdict("TASK-EMPTY-001")
        # AC names a missing qualified path — escalates via AC-005.
        assert verdict["status"] == "violation"
        assert "src/foo/missing_in_ac.py" in verdict["missing_files"]

    def test_section_with_only_placeholder_is_treated_as_absent(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        body = (
            "# Task: Demo\n\n"
            "## Acceptance Criteria\n\n"
            "- [ ] AC-1: ship the feature.\n\n"
            "## Files to Create\n\n"
            "- _none_\n"
        )
        _write_task(worktree, "TASK-EMPTY-002", body)

        explicit = invoker._extract_explicit_planned_files("TASK-EMPTY-002")
        assert explicit == set()


# ==================== Missing-task-file resilience ====================


class TestMissingTaskFile:
    """``_extract_explicit_planned_files`` must not crash when the task
    file is absent — same contract as ``_scan_ac_for_missing_paths``."""

    def test_unknown_task_id_returns_empty_set(
        self, invoker: AgentInvoker
    ) -> None:
        explicit = invoker._extract_explicit_planned_files("TASK-DOES-NOT-EXIST")
        assert explicit == set()
