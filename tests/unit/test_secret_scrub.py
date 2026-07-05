"""Regression suite for TASK-AB-SECRETSCRUB01 — secret scrubbing at the
evidence→publication boundary.

Pins the five acceptance criteria:

- AC-001: deterministic scrubber (URL userinfo → ``scheme://user:***@host``,
  token shapes masked, localhost fixture DSNs preserved);
- AC-002: applied at the task-md turn-history writer and the review-summary
  writer — publication, never verification;
- AC-003: fail-closed (scrub failure → whole block redacted with a marker,
  never the unscrubbed content, never a crash);
- AC-004: the tracked-artifact lint catches a planted non-localhost DSN and
  its failure output contains no secret material;
- AC-005: this file.

The planted "secrets" below are synthetic (AWS's documented example key id,
invented passwords) — they exist to be caught.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from guardkit.lib import secret_scrub
from guardkit.lib.secret_scrub import (
    REDACTION_FAILURE_MARKER,
    find_secret_matches,
    iter_hazards,
    scrub_for_publication,
    scrub_secrets,
)

# A synthetic "live" DSN in the exact ABL-001 run-3 leak shape.
LIVE_DSN = "postgresql://fleet_memory:hunter2secret@nas-store.tail1234.ts.net:5432/fleet"
LIVE_DSN_MASKED = "postgresql://fleet_memory:***@nas-store.tail1234.ts.net"
LOCALHOST_DSN = "postgresql://fleet_memory:postgres@localhost:5432/fleet_memory_test"


# ============================================================================
# 1. Scrubber unit behaviour (AC-001)
# ============================================================================


class TestScrubSecrets:
    def test_masks_non_localhost_url_password_preserving_user_and_host(self):
        text = f"AssertionError: expected X, got {LIVE_DSN} instead"
        scrubbed = scrub_secrets(text)
        assert "hunter2secret" not in scrubbed
        assert LIVE_DSN_MASKED in scrubbed
        assert "fleet_memory" in scrubbed  # user preserved
        assert "nas-store.tail1234.ts.net" in scrubbed  # host preserved

    def test_localhost_fixture_dsn_untouched(self):
        text = f"connected via {LOCALHOST_DSN} ok"
        assert scrub_secrets(text) == text

    def test_127_0_0_1_fixture_dsn_untouched(self):
        text = "redis://user:secretpw@127.0.0.1:6379/0"
        assert scrub_secrets(text) == text

    def test_deterministic_and_idempotent(self):
        text = f"first {LIVE_DSN} then AKIAIOSFODNN7EXAMPLE done"
        once = scrub_secrets(text)
        assert scrub_secrets(text) == once  # same input → same output
        assert scrub_secrets(once) == once  # already-masked is stable

    def test_aws_access_key_id_masked(self):
        scrubbed = scrub_secrets("key id AKIAIOSFODNN7EXAMPLE in output")
        assert "AKIAIOSFODNN7EXAMPLE" not in scrubbed
        assert "AKIA***" in scrubbed

    def test_sk_prefixed_key_masked(self):
        scrubbed = scrub_secrets("used sk-abc123def456ghi789 for the call")
        assert "sk-abc123def456ghi789" not in scrubbed
        assert "sk-***" in scrubbed

    def test_github_token_masked(self):
        scrubbed = scrub_secrets("push with ghp_AbCdEf123456789012345 failed")
        assert "ghp_AbCdEf123456789012345" not in scrubbed
        assert "ghp_***" in scrubbed

    def test_bearer_jwt_masked(self):
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMiJ9.sig-part_123"
        scrubbed = scrub_secrets(f"Authorization: Bearer {jwt}")
        assert jwt not in scrubbed
        assert "Bearer ***" in scrubbed

    def test_multiple_secrets_in_one_block(self):
        text = f"{LIVE_DSN}\nAKIAIOSFODNN7EXAMPLE\nghp_AbCdEf123456789012345"
        scrubbed = scrub_secrets(text)
        for secret in ("hunter2secret", "AKIAIOSFODNN7EXAMPLE", "ghp_AbCdEf"):
            assert secret not in scrubbed

    def test_sk_token_as_url_password_single_coherent_mask(self):
        text = "amqp://svc:sk-abc123def456ghi789@queue.internal/vhost"
        scrubbed = scrub_secrets(text)
        assert "sk-abc123def456ghi789" not in scrubbed
        assert "amqp://svc:***@queue.internal" in scrubbed

    def test_clean_text_unchanged(self):
        text = "34 passed in 0.18s — see https://example.com/docs for details"
        assert scrub_secrets(text) == text

    def test_credential_free_url_with_at_in_query_untouched(self):
        # Review finding 3: an @ in the PATH/QUERY must never be misparsed
        # as userinfo (the password class excludes / ? #).
        for text in (
            "https://example.com:8080/path?q=foo@bar",
            "http://localhost:8080/notify?email=a@b.com",
            "https://example.com:8080?x=a@b.com",
        ):
            assert scrub_secrets(text) == text

    def test_empty_and_none_inputs(self):
        assert scrub_secrets("") == ""
        assert scrub_for_publication(None) is None

    def test_non_string_passthrough(self):
        assert scrub_for_publication(42) == 42  # type: ignore[arg-type]


# ============================================================================
# 2. Fail-closed publication wrapper (AC-003)
# ============================================================================


class TestScrubForPublication:
    def test_scrub_failure_redacts_whole_block_never_raises(self, caplog):
        with patch.object(
            secret_scrub, "scrub_secrets", side_effect=RuntimeError("boom")
        ):
            with caplog.at_level("WARNING"):
                result = scrub_for_publication(f"output with {LIVE_DSN}")
        assert result == REDACTION_FAILURE_MARKER
        assert "hunter2secret" not in result
        assert any("scrubbing failed" in r.message for r in caplog.records)

    def test_none_survives_the_wrapper(self):
        # Absence must survive: None in → None out, never a marker.
        assert scrub_for_publication(None) is None


# ============================================================================
# 3. Lint-grade hazard detection (AC-004 heuristics)
# ============================================================================


class TestIterHazards:
    def test_planted_live_dsn_is_a_hazard_with_masked_label(self):
        hazards = list(iter_hazards(f"line1\nline2 {LIVE_DSN}\nline3"))
        assert len(hazards) == 1
        lineno, match = hazards[0]
        assert lineno == 2
        assert "hunter2secret" not in match.safe_label
        assert "nas-store.tail1234.ts.net" in match.safe_label

    def test_localhost_dsn_is_not_a_hazard(self):
        assert list(iter_hazards(LOCALHOST_DSN)) == []

    def test_placeholder_docs_credential_is_not_a_hazard_but_still_scrubbed(self):
        text = "redis://user:pass@your-instance.falkordb.cloud:6379"
        assert list(iter_hazards(text)) == []
        # ...while the publication scrubber still masks it (over-masking safe)
        assert "user:***@" in scrub_secrets(text)

    def test_prose_after_bearer_is_not_a_hazard(self):
        assert list(iter_hazards("the bearer responsibility clause")) == []

    def test_real_bearer_token_is_a_hazard(self):
        hazards = list(iter_hazards("Bearer eyJhbGciOiJIUzI1NiJ9.payload9.sig3"))
        assert [m.kind for _, m in hazards] == ["bearer-token"]


# ============================================================================
# 4. Turn-history publication writer (AC-002) — the ABL-001 leak vector
# ============================================================================


def _make_orchestrator():
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    invoker = Mock()
    invoker.invoke_player = AsyncMock()
    invoker.invoke_coach = AsyncMock()
    display = Mock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    return AutoBuildOrchestrator(
        repo_root=Path("/tmp/test"),
        max_turns=5,
        worktree_manager=Mock(worktrees_dir=Path("/tmp/worktrees")),
        agent_invoker=invoker,
        progress_display=display,
    )


def _make_turn_record(feedback=None, player_error=None, notes="all good"):
    from guardkit.orchestrator.agent_invoker import AgentInvocationResult
    from guardkit.orchestrator.autobuild import TurnRecord

    success = player_error is None
    player_result = AgentInvocationResult(
        task_id="TASK-AB-SECRETSCRUB01",
        turn=1,
        agent_type="player",
        success=success,
        report={"implementation_notes": notes} if success else {},
        duration_seconds=1.0,
        error=player_error,
    )
    coach_result = AgentInvocationResult(
        task_id="TASK-AB-SECRETSCRUB01",
        turn=1,
        agent_type="coach",
        success=True,
        report={"decision": "feedback"},
        duration_seconds=1.0,
        error=None,
    )
    return TurnRecord(
        turn=1,
        player_result=player_result,
        coach_result=coach_result,
        decision="feedback",
        feedback=feedback,
        timestamp="2026-07-05T10:00:00",
    )


class TestTurnHistoryPublicationScrub:
    def test_dsn_in_coach_feedback_is_masked(self):
        orchestrator = _make_orchestrator()
        orchestrator._turn_history = [
            _make_turn_record(
                feedback=f"Test failed: expected sentinel, got {LIVE_DSN}"
            )
        ]
        [serialized] = orchestrator._serialize_turn_history()
        assert "hunter2secret" not in serialized["feedback"]
        assert LIVE_DSN_MASKED in serialized["feedback"]

    def test_dsn_in_player_error_is_masked(self):
        orchestrator = _make_orchestrator()
        orchestrator._turn_history = [
            _make_turn_record(player_error=f"crashed connecting to {LIVE_DSN}")
        ]
        [serialized] = orchestrator._serialize_turn_history()
        assert "hunter2secret" not in serialized["player_summary"]

    def test_localhost_fixture_dsn_survives_untouched(self):
        orchestrator = _make_orchestrator()
        orchestrator._turn_history = [
            _make_turn_record(feedback=f"fixture used {LOCALHOST_DSN}")
        ]
        [serialized] = orchestrator._serialize_turn_history()
        assert LOCALHOST_DSN in serialized["feedback"]

    def test_scrub_runs_before_truncation_no_partial_secret(self):
        # A DSN straddling the 500-char truncation point must never leak a
        # partial password (the incident leaked 14/32 chars via truncation).
        orchestrator = _make_orchestrator()
        notes = ("x" * 490) + f" {LIVE_DSN} trailing"
        orchestrator._turn_history = [_make_turn_record(notes=notes)]
        [serialized] = orchestrator._serialize_turn_history()
        assert "hunter2secret" not in serialized["player_summary"]
        assert len(serialized["player_summary"]) <= 500

    def test_none_feedback_stays_none(self):
        orchestrator = _make_orchestrator()
        orchestrator._turn_history = [_make_turn_record(feedback=None)]
        [serialized] = orchestrator._serialize_turn_history()
        assert serialized["feedback"] is None

    def test_save_state_writes_masked_content_to_task_md(self, tmp_path):
        orchestrator = _make_orchestrator()
        orchestrator._turn_history = [
            _make_turn_record(feedback=f"diff printed {LIVE_DSN}")
        ]
        task_file = tmp_path / "TASK-AB-SECRETSCRUB01-test.md"
        task_file.write_text(
            "---\nid: TASK-AB-SECRETSCRUB01\nstatus: in_progress\n---\n\n# T\n"
        )
        worktree = Mock()
        worktree.path = Path("/tmp/worktrees/TASK-AB-SECRETSCRUB01")
        worktree.base_branch = "main"

        orchestrator._save_state(task_file, worktree, "in_progress")

        written = task_file.read_text()
        assert "hunter2secret" not in written
        assert "fleet_memory:***@" in written


# ============================================================================
# 5. Review-summary publication writer (AC-002)
# ============================================================================


class TestReviewSummaryPublicationScrub:
    def _make_result_with_error(self, error: str):
        from guardkit.orchestrator.feature_orchestrator import (
            FeatureOrchestrationResult,
            TaskExecutionResult,
            WaveExecutionResult,
        )

        task = TaskExecutionResult(
            task_id="TASK-001",
            success=False,
            total_turns=3,
            final_decision="unrecoverable_stall",
            error=error,
            recovery_count=0,
            sdk_ceiling_hits=0,
            sdk_total_invocations=1,
            sdk_turns_per_invocation=[3],
        )
        wave = WaveExecutionResult(
            wave_number=1,
            task_ids=[task.task_id],
            results=[task],
            all_succeeded=False,
        )
        return FeatureOrchestrationResult(
            feature_id="FEAT-TEST",
            success=False,
            status="failed",
            total_tasks=1,
            tasks_completed=0,
            tasks_failed=1,
            wave_results=[wave],
            worktree=MagicMock(),
        )

    def test_dsn_in_task_error_masked_in_written_summary(self, tmp_path):
        from guardkit.orchestrator.review_summary import ReviewSummaryGenerator

        result = self._make_result_with_error(
            f"stalled; failing test printed {LIVE_DSN}"
        )
        outcome = ReviewSummaryGenerator(output_dir=tmp_path).generate(result)
        assert outcome.success
        written = outcome.output_path.read_text()
        assert "hunter2secret" not in written
        assert LIVE_DSN_MASKED in written

    def test_fail_closed_writes_marker_not_raw_content(self, tmp_path):
        from guardkit.orchestrator import review_summary as review_summary_mod
        from guardkit.orchestrator.review_summary import ReviewSummaryGenerator

        result = self._make_result_with_error(f"boom {LIVE_DSN}")
        with patch.object(
            review_summary_mod,
            "scrub_for_publication",
            return_value=REDACTION_FAILURE_MARKER,
        ):
            outcome = ReviewSummaryGenerator(output_dir=tmp_path).generate(result)
        assert outcome.success
        written = outcome.output_path.read_text()
        assert "hunter2secret" not in written
        assert REDACTION_FAILURE_MARKER in written


# ============================================================================
# 6. Tracked-artifact lint self-test (AC-004)
# ============================================================================


class TestTrackedArtifactLint:
    def _scan(self, tmp_path: Path):
        import importlib.util

        lint_path = (
            Path(__file__).resolve().parents[1]
            / "rules"
            / "test_no_secrets_in_tracked_artifacts.py"
        )
        spec = importlib.util.spec_from_file_location("secret_lint", lint_path)
        lint = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lint)
        files = [p for p in tmp_path.rglob("*") if p.is_file()]
        return lint.scan_files_for_secrets(files, tmp_path)

    def test_lint_catches_planted_non_localhost_dsn(self, tmp_path):
        planted = tmp_path / "tasks" / "TASK-PLANTED.md"
        planted.parent.mkdir(parents=True)
        planted.write_text(f"# Task\n\nrun output: {LIVE_DSN}\n")
        violations = self._scan(tmp_path)
        assert len(violations) == 1
        assert violations[0].startswith("tasks/TASK-PLANTED.md:3")
        # The violation line itself must contain no secret material.
        assert "hunter2secret" not in violations[0]

    def test_lint_ignores_localhost_fixture_dsn(self, tmp_path):
        benign = tmp_path / "docs" / "guide.md"
        benign.parent.mkdir(parents=True)
        benign.write_text(f"fixture: {LOCALHOST_DSN}\n")
        assert self._scan(tmp_path) == []

    def test_lint_ignores_placeholder_docs_credential(self, tmp_path):
        benign = tmp_path / "docs" / "spec.md"
        benign.parent.mkdir(parents=True)
        benign.write_text('connection = "redis://user:pass@your-host.cloud:6379"\n')
        assert self._scan(tmp_path) == []

    def test_current_tracked_tree_is_clean(self):
        # The live lint over the real repo must pass — this duplicates the
        # tests/rules gate so a regression is caught from the unit suite too.
        import importlib.util

        lint_path = (
            Path(__file__).resolve().parents[1]
            / "rules"
            / "test_no_secrets_in_tracked_artifacts.py"
        )
        spec = importlib.util.spec_from_file_location("secret_lint", lint_path)
        lint = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lint)
        files = lint._tracked_files(lint.REPO_ROOT, lint.SCAN_ROOTS)
        assert lint.scan_files_for_secrets(files, lint.REPO_ROOT) == []
