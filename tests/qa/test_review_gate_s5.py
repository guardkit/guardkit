"""S5 gate — the R-b advisory review wired into the gate flow (2026-07-13).

Spec of record: ``ai-transition/docs/factory-code-quality-seat-options-2026-07.md``
R-b build-lane stage **S-5** ("wire to the flow, pre-merge advisory first"), and
the P2 handoff clause: the review runs as an ADVISORY step behind the default-OFF
flag, its F14 record attached to the flow's artifacts, and it NEVER fails the
flow. Layers exercised:

1. The gate-flow step (:func:`run_review_gate_step`):
   - flag OFF ⇒ a PROVABLE no-op (the payload factory is never called → no git),
   - flag ON ⇒ emits an F14 record and NEVER blocks (``blocking`` stays False),
   - a seat outage / an unreadable subject is a NAMED outcome, never a raise,
   - the DF-017 ``route`` seam is called with the record; a router that raises is
     swallowed (advisory), never propagated.
2. The on-demand ``guardkit qa review`` CLI entry:
   - flag OFF ⇒ no-op, exit 0, git never touched,
   - flag ON ⇒ emits, exit 0 (advisory never blocks) — full offline wiring,
   - a bad range ⇒ exit 2 (a subject we cannot read is loud, never faked green),
   - ``--blocking`` ⇒ exit 2 (honest: blocking is gated on the S-4 bar),
   - conflicting subject selectors ⇒ exit 2.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from guardkit.cli.qa import qa
from guardkit.qa.diff_ingest import DiffIngestError, ReviewPayload, parse_unified_diff
from guardkit.qa.formats import validate_instance
from guardkit.qa.formats.review_findings import ReviewFindings
from guardkit.qa.review_seat import (
    REVIEW_SEAT_ENV,
    ReviewOutcome,
    default_merge_candidate_payload,
    run_review_gate_step,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_DIFF = """\
diff --git a/pkg/calc.py b/pkg/calc.py
index 1111111..2222222 100644
--- a/pkg/calc.py
+++ b/pkg/calc.py
@@ -1,2 +1,3 @@
 def average(xs):
-    return sum(xs) / len(xs)
+    return sum(xs) / len(xs)  # ZeroDivisionError on []
+    # trailing
"""

# A well-formed seat completion (one medium finding — never earns confirmed).
SEAT_JSON = json.dumps(
    {
        "summary": "Adds a comment; no behaviour change.",
        "findings": [
            {
                "id": "F1",
                "dimension": "correctness",
                "severity": "medium",
                "file": "pkg/calc.py",
                "line": 2,
                "summary": "average([]) raises ZeroDivisionError",
                "failing_scenario": "average([]) -> ZeroDivisionError",
                "executed_reproduction": None,
                "refuters": [{"who": "r1", "verdict": "refuted", "note": "guarded upstream?"}],
            }
        ],
    }
)


def _payload() -> ReviewPayload:
    return ReviewPayload(
        subject_kind="commit",
        ref="HEAD",
        context_lines=3,
        files=parse_unified_diff(SAMPLE_DIFF),
    )


@pytest.fixture(autouse=True)
def _flag_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the review-seat flag OFF unless a test sets it — no ambient env leak."""
    monkeypatch.setenv(REVIEW_SEAT_ENV, "0")


def _flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(REVIEW_SEAT_ENV, "1")


def _idle_probe():
    return lambda: [{"model": "qwen36-workhorse", "state": "ready"}]


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    (r / "calc.py").write_text("def average(xs):\n    return sum(xs) / len(xs)\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "seed")
    return r


# ===========================================================================
# 1. The gate-flow step — flag OFF is a PROVABLE no-op.
# ===========================================================================


def test_gate_step_off_is_provable_noop(tmp_path: Path) -> None:
    calls = {"factory": 0, "seat": 0}

    def factory() -> ReviewPayload:
        calls["factory"] += 1
        return _payload()

    def seat_call(_s: str, _u: str, _m: str) -> str:  # pragma: no cover - must not run
        calls["seat"] += 1
        return SEAT_JSON

    outcome = run_review_gate_step(
        tmp_path,
        payload_factory=factory,
        seat_call=seat_call,
        running_probe=_idle_probe(),
    )
    assert outcome.enabled is False
    assert outcome.record is None
    assert outcome.blocking is False
    # The provable-no-op guarantee: neither the payload nor the seat was touched.
    assert calls == {"factory": 0, "seat": 0}


# ===========================================================================
# 2. The gate-flow step — flag ON emits and NEVER blocks.
# ===========================================================================


def test_gate_step_on_emits_and_never_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _flag_on(monkeypatch)
    outcome = run_review_gate_step(
        tmp_path,
        payload_factory=_payload,
        write=False,
        seat_call=lambda _s, _u, _m: SEAT_JSON,
        running_probe=_idle_probe(),
    )
    assert outcome.enabled is True
    assert outcome.blocking is False  # advisory — never blocks
    assert outcome.error is None
    assert isinstance(outcome.record, ReviewFindings)
    assert outcome.record.stats.findings_total == 1
    # Reading is not a verdict: a reading-only seat never earns confirmed.
    assert outcome.record.stats.confirmed == 0


def test_gate_step_on_writes_f14_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _flag_on(monkeypatch)
    outcome = run_review_gate_step(
        tmp_path,
        payload_factory=_payload,
        write=True,
        seat_call=lambda _s, _u, _m: SEAT_JSON,
        running_probe=_idle_probe(),
    )
    assert outcome.emitted_path is not None
    written = Path(outcome.emitted_path)
    assert written.is_file()
    # The artifact round-trips through the pinned F14 loader (schema-valid).
    record = validate_instance("review-findings", written)
    assert record.stats.findings_total == 1


# ===========================================================================
# 3. The gate-flow step never raises — a seat outage / bad subject is named.
# ===========================================================================


def test_gate_step_seat_outage_is_named_not_raised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _flag_on(monkeypatch)

    def boom(_s: str, _u: str, _m: str) -> str:
        raise ConnectionError("seat unreachable")

    outcome = run_review_gate_step(
        tmp_path,
        payload_factory=_payload,
        seat_call=boom,
        running_probe=_idle_probe(),
    )
    assert outcome.enabled is True
    assert outcome.blocking is False
    assert outcome.record is None
    assert outcome.error is not None and "seat call failed" in outcome.error


def test_gate_step_unreadable_subject_is_named_not_raised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _flag_on(monkeypatch)

    def bad_factory() -> ReviewPayload:
        raise DiffIngestError("git exploded")

    outcome = run_review_gate_step(
        tmp_path,
        payload_factory=bad_factory,
        seat_call=lambda _s, _u, _m: SEAT_JSON,
        running_probe=_idle_probe(),
    )
    assert outcome.enabled is True
    assert outcome.blocking is False
    assert outcome.record is None
    assert outcome.error is not None and "could not build the review subject" in outcome.error


# ===========================================================================
# 4. The DF-017 route seam — called with the record; a raising router is swallowed.
# ===========================================================================


def test_gate_step_route_hook_receives_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _flag_on(monkeypatch)
    routed: list[ReviewFindings] = []
    outcome = run_review_gate_step(
        tmp_path,
        payload_factory=_payload,
        write=False,
        route=routed.append,
        seat_call=lambda _s, _u, _m: SEAT_JSON,
        running_probe=_idle_probe(),
    )
    assert len(routed) == 1
    assert routed[0] is outcome.record


def test_gate_step_route_hook_raising_is_swallowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _flag_on(monkeypatch)

    def bad_route(_record: ReviewFindings) -> None:
        raise RuntimeError("router bug")

    outcome = run_review_gate_step(
        tmp_path,
        payload_factory=_payload,
        write=False,
        route=bad_route,
        seat_call=lambda _s, _u, _m: SEAT_JSON,
        running_probe=_idle_probe(),
    )
    # Advisory: the record still emitted; the router failure is a named note.
    assert outcome.record is not None
    assert outcome.blocking is False
    assert any("finding router raised" in n for n in outcome.notes)


# ===========================================================================
# 5. default_merge_candidate_payload — merge view, commit fallback.
# ===========================================================================


def test_default_payload_falls_back_to_commit_when_not_a_merge() -> None:
    seen: list[list[str]] = []

    def fake_git(args):
        seen.append(list(args))
        # ingest_merge does `git diff <ref>^1 <ref>` — a non-merge ref has no
        # ^1, so git fails; ingest_commit's `git show` then succeeds.
        if args[0] == "diff":
            return subprocess.CompletedProcess(args, 128, stdout="", stderr="no ^1")
        if args[0] == "show":
            return subprocess.CompletedProcess(args, 0, stdout=SAMPLE_DIFF, stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    payload = default_merge_candidate_payload(Path("/x"), git_run=fake_git)
    assert payload.subject_kind == "commit"  # fell back
    assert len(payload.files) == 1
    assert any(a[0] == "diff" for a in seen) and any(a[0] == "show" for a in seen)


# ===========================================================================
# 6. The CLI `guardkit qa review` — flag OFF is a no-op, git untouched.
# ===========================================================================


def test_cli_off_is_noop_git_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Prove the flag-OFF path never builds a payload: any ingest call blows up.
    def _forbidden(*_a, **_k):  # pragma: no cover - must not run
        raise AssertionError("git/ingest must not run when the flag is OFF")

    monkeypatch.setattr("guardkit.qa.diff_ingest.ingest_working_tree", _forbidden)
    result = CliRunner().invoke(qa, ["review", "--repo", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "OFF" in result.output


# ===========================================================================
# 7. The CLI — flag ON emits, exit 0 (full offline wiring through the seat edge).
# ===========================================================================


def test_cli_on_emits_and_exits_zero(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _flag_on(monkeypatch)
    # Stub the two impure seat edges so the whole path runs offline.
    monkeypatch.setattr(
        "guardkit.qa.review_seat._default_seat_call",
        lambda *a, **k: (lambda _s, _u, _m: SEAT_JSON),
    )
    monkeypatch.setattr(
        "guardkit.qa.review_seat._default_running_probe",
        lambda _base: _idle_probe(),
    )
    result = CliRunner().invoke(
        qa, ["review", "--repo", str(repo), "--commit", "HEAD", "--no-write", "--json"]
    )
    assert result.exit_code == 0, result.output
    assert "Advisory Code Review" in result.output
    # The --json dump carries the schema-valid record.
    assert '"format_kind"' in result.output or '"review_id"' in result.output


# ===========================================================================
# 8. The CLI — a bad range is loud (exit 2), never a faked clean review.
# ===========================================================================


def test_cli_bad_range_exits_two(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _flag_on(monkeypatch)
    result = CliRunner().invoke(
        qa, ["review", "--repo", str(repo), "--base", "no-such-ref-xyz"]
    )
    assert result.exit_code == 2, result.output
    assert "could not read the review subject" in result.output


# ===========================================================================
# 9. The CLI — --blocking is refused (blocking is gated on the S-4 bar).
# ===========================================================================


def test_cli_blocking_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _flag_on(monkeypatch)
    result = CliRunner().invoke(
        qa, ["review", "--repo", str(tmp_path), "--blocking"]
    )
    assert result.exit_code == 2
    assert "--blocking is not available" in result.output
    assert "S-4" in result.output


# ===========================================================================
# 10. The CLI — conflicting subject selectors are rejected (exit 2).
# ===========================================================================


def test_cli_conflicting_selectors_exit_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _flag_on(monkeypatch)
    result = CliRunner().invoke(
        qa,
        ["review", "--repo", str(tmp_path), "--commit", "HEAD", "--merge", "HEAD"],
    )
    assert result.exit_code == 2
    assert "choose one review subject" in result.output


def test_cli_head_without_base_exit_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _flag_on(monkeypatch)
    result = CliRunner().invoke(
        qa, ["review", "--repo", str(tmp_path), "--head", "feature"]
    )
    assert result.exit_code == 2
    assert "--head requires --base" in result.output
