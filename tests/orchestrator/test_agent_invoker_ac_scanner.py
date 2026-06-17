"""Tests for ``AgentInvoker._scan_ac_for_missing_paths`` and the
``_compute_plan_audit_verdict`` escalation path it feeds.

Covers TASK-GK-AC-001: the AC scanner used to flag bare basenames
(``pipeline_consumer.py``) as missing whenever the file lived deeper in
the tree (``src/forge/adapters/nats/pipeline_consumer.py``). That false
positive propagated as ``plan_audit.violations > 0`` → Coach gate fail
→ Coach short-circuits → criteria_passed = 0 → FEAT-PEBR Wave-1
UNRECOVERABLE_STALL.

Coverage Target: >=85%
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.synthetic_report import (
    generate_file_existence_promises,
)


FIXTURE_ROOT = Path(__file__).parent.parent / "fixtures" / "feat_pebr_worktree"


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
    ac_lines: list[str],
    *,
    state: str = "in_progress",
) -> Path:
    body = "\n".join(f"- [ ] {line}" for line in ac_lines)
    content = (
        "---\n"
        f"id: {task_id}\n"
        "title: Test task\n"
        f"status: {state}\n"
        "---\n\n"
        "# Task: Test\n\n"
        "## Acceptance Criteria\n\n"
        f"{body}\n"
    )
    task_path = worktree / "tasks" / state / f"{task_id}.md"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    task_path.write_text(content)
    return task_path


# ==================== AC-1 / AC-2: Bare basenames ====================


class TestScanACBasenameSkipping:
    """A bare basename in AC text must not be flagged when the file
    exists anywhere under the worktree."""

    def test_bare_basename_with_file_at_deep_path_is_not_missing(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        """AC-2 reproducer: ``pipeline_consumer.py`` in AC text +
        ``src/forge/adapters/nats/pipeline_consumer.py`` on disk →
        scanner returns ``[]``.

        Pre-fix this returned ``["pipeline_consumer.py"]``.
        """
        deep = worktree / "src" / "forge" / "adapters" / "nats"
        deep.mkdir(parents=True)
        (deep / "pipeline_consumer.py").write_text("")
        _write_task(
            worktree,
            "TASK-PEBR-001",
            ["AC-1: `pipeline_consumer.py` publishes a recovery event."],
        )

        missing = invoker._scan_ac_for_missing_paths("TASK-PEBR-001")

        assert missing == []

    def test_bare_basename_default_skips_even_when_file_absent(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        """A bare basename that doesn't exist anywhere is still skipped
        with the new default (``flag_basenames=False``). The
        compensating signal lives in the synthetic-report path; this
        scanner is intentionally lenient on bare names because AC text
        rarely intends them as filesystem assertions."""
        _write_task(
            worktree,
            "TASK-PEBR-002",
            ["AC-1: Modify `does_not_exist.py` somewhere."],
        )

        missing = invoker._scan_ac_for_missing_paths("TASK-PEBR-002")

        assert missing == []

    def test_bare_basename_legacy_flag_restores_old_behaviour(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        """``flag_basenames=True`` opt-in preserves the pre-fix behaviour
        for any caller that genuinely wants every named token checked
        against the worktree root."""
        _write_task(
            worktree,
            "TASK-PEBR-003",
            ["AC-1: Modify `does_not_exist.py` somewhere."],
        )

        missing = invoker._scan_ac_for_missing_paths(
            "TASK-PEBR-003", flag_basenames=True
        )

        assert missing == ["does_not_exist.py"]


# ==================== AC-3: Fully-qualified missing paths still fire ====================


class TestScanACFullyQualifiedPaths:
    """Don't over-correct: fully-qualified paths that genuinely don't
    exist must keep firing."""

    def test_qualified_missing_path_is_reported(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        _write_task(
            worktree,
            "TASK-PEBR-004",
            ["AC-1: Add `src/foo/bar/missing.py` to the consumer."],
        )

        missing = invoker._scan_ac_for_missing_paths("TASK-PEBR-004")

        assert "src/foo/bar/missing.py" in missing

    def test_qualified_existing_path_is_not_reported(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        target_dir = worktree / "src" / "foo" / "bar"
        target_dir.mkdir(parents=True)
        (target_dir / "present.py").write_text("")
        _write_task(
            worktree,
            "TASK-PEBR-005",
            ["AC-1: Modify `src/foo/bar/present.py`."],
        )

        missing = invoker._scan_ac_for_missing_paths("TASK-PEBR-005")

        assert missing == []

    def test_qualified_and_basename_mix(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        """Mixed AC text — bare basename that exists deep + qualified
        path that's missing — reports only the qualified missing path."""
        deep = worktree / "src" / "forge" / "adapters" / "nats"
        deep.mkdir(parents=True)
        (deep / "pipeline_consumer.py").write_text("")
        _write_task(
            worktree,
            "TASK-PEBR-006",
            [
                "AC-1: `pipeline_consumer.py` publishes recovery events.",
                "AC-2: Add `src/foo/bar/totally_absent.py`.",
            ],
        )

        missing = invoker._scan_ac_for_missing_paths("TASK-PEBR-006")

        assert missing == ["src/foo/bar/totally_absent.py"]


# ==================== AC-4: synthetic_report path is unchanged ====================


class TestSyntheticReportNonRegression:
    """``synthetic_report.generate_file_existence_promises`` is the
    sibling regex consumer named in the scanner docstring. The fix to
    ``_scan_ac_for_missing_paths`` must not affect it."""

    def test_synthetic_report_still_promises_modified_basename(
        self, tmp_path: Path
    ) -> None:
        """The synthetic-report path matches a basename mentioned in AC
        text against the ``files_modified`` list and returns
        ``status="complete"``. This keeps working independently of the
        scanner's basename-skip behaviour."""
        promises = generate_file_existence_promises(
            files_created=[],
            files_modified=["src/forge/adapters/nats/pipeline_consumer.py"],
            acceptance_criteria=[
                "`pipeline_consumer.py` publishes a recovery event."
            ],
            worktree_path=tmp_path,
        )

        assert len(promises) == 1
        # The bare basename in AC text matches against the qualified
        # entry in files_modified by suffix — synthetic-report's job.
        assert promises[0]["status"] in {"complete", "partial"}

    def test_synthetic_report_still_flags_unmentioned_qualified_path(
        self, tmp_path: Path
    ) -> None:
        """Qualified path in AC text that's nowhere in modified/created
        and not on disk → ``status="incomplete"``. Unchanged by the
        scanner fix."""
        promises = generate_file_existence_promises(
            files_created=[],
            files_modified=[],
            acceptance_criteria=["Add `src/foo/bar/missing.py`."],
            worktree_path=tmp_path,
        )

        assert len(promises) == 1
        assert promises[0]["status"] == "incomplete"


# ==================== AC-5: End-to-end fixture regression ====================


class TestComputePlanAuditFixtureRegression:
    """Running the FEAT-PEBR fixture worktree through
    ``_compute_plan_audit_verdict`` must produce ``status="skipped"``
    (not ``"violation"``) — exercising the full path that
    ``coach_validator`` consumes."""

    def test_feat_pebr_fixture_does_not_escalate_to_violation(
        self, tmp_path: Path
    ) -> None:
        worktree = tmp_path / "worktree"
        shutil.copytree(FIXTURE_ROOT, worktree)

        invoker = AgentInvoker(
            worktree_path=worktree,
            max_turns_per_agent=1,
            sdk_timeout_seconds=10,
        )

        verdict = invoker._compute_plan_audit_verdict("TASK-FRR-PEB-001")

        # Pre-fix: status="violation", missing_files=["pipeline_consumer.py"].
        # Post-fix: no plan on disk + no qualified missing paths → skipped.
        assert verdict["status"] == "skipped", (
            f"expected skipped, got {verdict['status']}: "
            f"missing_files={verdict.get('missing_files')}, "
            f"message={verdict.get('message')}"
        )
        assert verdict["violations"] == 0
        assert verdict["missing_files"] == []


# ============ TASK-GK-PA-003: markdown-link hrefs + path suffixes ============


class TestScanACMarkdownLinkResolution:
    """TASK-GK-PA-003 AC-1: an AC line written as a markdown link
    ``[label](href)`` must be checked against the *href*, not the
    *label*. The label is a display string that may itself look like a
    path (``relay/service.py``); flagging it as missing when the href
    exists on disk is the FEAT-MEM-07 Error 2 false positive
    (RIP-002 unrecoverable_stall). Inverse-shape sibling of
    ``path-string-mismatch-is-not-dishonesty``.
    """

    def test_markdown_link_checks_href_not_label(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        """AC-4 reproducer: the label path ``relay/service.py`` is absent
        but the href ``src/pkg/relay/service.py`` exists → no violation.

        Pre-fix this returned ``["relay/service.py"]`` (the label).
        """
        href_dir = worktree / "src" / "pkg" / "relay"
        href_dir.mkdir(parents=True)
        (href_dir / "service.py").write_text("")
        _write_task(
            worktree,
            "TASK-PA003-001",
            ["AC-1: Wire up [relay/service.py](src/pkg/relay/service.py)."],
        )

        missing = invoker._scan_ac_for_missing_paths("TASK-PA003-001")

        assert missing == []

    def test_markdown_link_control_neither_exists_is_violation(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        """AC-4 control: when neither the label path nor the href exists,
        the *href* (the real referent, not the label) is reported missing
        — AC-003's no-masking guarantee."""
        _write_task(
            worktree,
            "TASK-PA003-002",
            ["AC-1: Wire up [relay/service.py](src/pkg/relay/service.py)."],
        )

        missing = invoker._scan_ac_for_missing_paths("TASK-PA003-002")

        assert missing == ["src/pkg/relay/service.py"]


class TestScanACPathSuffixMatching:
    """TASK-GK-PA-003 AC-2: a multi-segment token cited relative to a
    package root counts as present when a file anywhere in the tree ends
    with that path suffix (on segment boundaries)."""

    def test_path_suffix_match_is_not_missing(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        """``relay/service.py`` in AC text +
        ``src/fleet_memory/relay/service.py`` on disk → no violation,
        even though ``worktree / "relay/service.py"`` does not exist."""
        deep = worktree / "src" / "fleet_memory" / "relay"
        deep.mkdir(parents=True)
        (deep / "service.py").write_text("")
        _write_task(
            worktree,
            "TASK-PA003-003",
            ["AC-1: Implement `relay/service.py` for the relay."],
        )

        missing = invoker._scan_ac_for_missing_paths("TASK-PA003-003")

        assert missing == []

    def test_path_suffix_no_match_still_fires(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        """AC-003: a multi-segment token with no direct hit AND no
        tree-suffix match remains a violation (no masking)."""
        _write_task(
            worktree,
            "TASK-PA003-004",
            ["AC-1: Implement `relay/service.py` for the relay."],
        )

        missing = invoker._scan_ac_for_missing_paths("TASK-PA003-004")

        assert missing == ["relay/service.py"]

    def test_suffix_match_requires_segment_boundary(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        """A suffix match must align on path-segment boundaries. A file at
        ``src/myrelay/service.py`` shares the trailing *characters* of the
        token ``relay/service.py`` but not its *segments*, so the token is
        still missing — guards against a naive string ``endswith``."""
        deep = worktree / "src" / "myrelay"
        deep.mkdir(parents=True)
        (deep / "service.py").write_text("")
        _write_task(
            worktree,
            "TASK-PA003-005",
            ["AC-1: Implement `relay/service.py` for the relay."],
        )

        missing = invoker._scan_ac_for_missing_paths("TASK-PA003-005")

        assert missing == ["relay/service.py"]
