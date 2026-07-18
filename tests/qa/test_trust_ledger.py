"""Hermetic tests for the H-A Stage 3 DF-021 TRUST LEDGER + auto-merge.

Spec: ``docs/ways-of-working/retire-the-coordinator-build-handoff-2026-07-17.md``
§3 Stage 3. The coach-gate scenarios (all hermetic — temp-dir git fixtures +
real ``git`` for the merge primitive; no network, no seats, no service, no
docker):

* 5 clean MG-3 records ⇒ the lane graduates ⇒ the 6th merge auto-runs
  ``manager.merge()`` (a real ``--no-ff`` merge on a fixture repo);
* one confirmed-blocker MG-3 record mid-streak ⇒ INSTANT demotion, streak resets,
  the next merge is attended (never auto);
* a constitutional-class target ⇒ NEVER auto, regardless of streak;
* a live-gate demotion-event file ⇒ demote.

The MG-3 records are written in the exact F14 ``review-findings`` shape forge's
``dispatch_merge_review_gate`` emits (``review_id`` + ``findings[]`` with
``severity``/``status``) so the ledger is proven against the real Stage 2 output.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from guardkit.orchestrator.auto_merge import (
    AutoMergeDecision,
    auto_merge_if_graduated,
    clean_signal,
    should_auto_merge,
)
from guardkit.orchestrator.machine_verify import (
    SIGNAL_CATCH,
    SIGNAL_CLEAN,
    MachineVerifyReport,
)
from guardkit.qa.trust_ledger import (
    STATE_ATTENDED,
    STATE_GRADUATED,
    ConstitutionalRegistry,
    LedgerRecordError,
    TrustLedger,
    classify_mg3_record,
    load_demotion_event,
)
from guardkit.worktrees.manager import Worktree, WorktreeManager


# ---------------------------------------------------------------------------
# MG-3 record fixtures — the exact F14 shape forge's Stage 2 dispatch writes
# ---------------------------------------------------------------------------


def _write_mg3(
    qa_dir: Path,
    review_id: str,
    *,
    findings: list[dict] | None = None,
) -> Path:
    """Write an F14 ``review-findings`` record (Stage 2 MG-3 shape)."""
    findings = findings or []
    confirmed = sum(1 for f in findings if f.get("status") == "confirmed")
    refuted = sum(1 for f in findings if f.get("status") == "refuted")
    record = {
        "format_version": 1,
        "review_id": review_id,
        "subject": {"kind": "merge", "ref": review_id},
        "dimensions": ["correctness"],
        "findings": findings,
        "stats": {
            "findings_total": len(findings),
            "confirmed": confirmed,
            "refuted": refuted,
            "refutations_attempted": len(findings),
        },
    }
    qa_dir.mkdir(parents=True, exist_ok=True)
    out = qa_dir / f"review-{review_id}.yaml"
    out.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
    return out


def _clean_record(qa_dir: Path, review_id: str) -> Path:
    """A clean MG-3: either no findings, or only refuted / non-serious ones."""
    return _write_mg3(
        qa_dir,
        review_id,
        findings=[
            {
                "id": "F-lint",
                "dimension": "style",
                "severity": "low",
                "status": "confirmed",
                "summary": "a nit — not a merge blocker",
            },
            {
                "id": "F-maybe",
                "dimension": "correctness",
                "severity": "high",
                "status": "refuted",
                "summary": "high but refuted by the adversarial quorum",
            },
        ],
    )


def _blocker_record(qa_dir: Path, review_id: str) -> Path:
    """A confirmed-blocker MG-3: a confirmed critical/high finding."""
    return _write_mg3(
        qa_dir,
        review_id,
        findings=[
            {
                "id": "F-crash",
                "dimension": "correctness",
                "severity": "critical",
                "status": "confirmed",
                "summary": "a confirmed critical regression — blocks the merge",
            },
        ],
    )


# ---------------------------------------------------------------------------
# classify_mg3_record
# ---------------------------------------------------------------------------


class TestClassifyMg3:
    def test_clean_record_is_not_a_blocker(self, tmp_path: Path):
        rec = _clean_record(tmp_path, "feat-a-merge-review")
        verdict = classify_mg3_record(rec)
        assert verdict.is_blocker is False
        assert verdict.verdict == "clean"
        assert verdict.review_id == "feat-a-merge-review"
        assert verdict.confirmed_serious == ()

    def test_confirmed_serious_is_a_blocker(self, tmp_path: Path):
        rec = _blocker_record(tmp_path, "feat-b-merge-review")
        verdict = classify_mg3_record(rec)
        assert verdict.is_blocker is True
        assert verdict.verdict == "blocker"
        assert "F-crash" in verdict.confirmed_serious

    def test_confirmed_but_low_is_not_a_blocker(self, tmp_path: Path):
        rec = _write_mg3(
            tmp_path,
            "feat-c",
            findings=[
                {
                    "id": "F-nit",
                    "dimension": "style",
                    "severity": "medium",
                    "status": "confirmed",
                    "summary": "confirmed but only medium — not serious",
                }
            ],
        )
        assert classify_mg3_record(rec).is_blocker is False

    def test_unreadable_record_raises_loud(self, tmp_path: Path):
        with pytest.raises(LedgerRecordError):
            classify_mg3_record(tmp_path / "does-not-exist.yaml")

    def test_non_f14_shape_raises_loud(self, tmp_path: Path):
        bad = tmp_path / "review-bad.yaml"
        bad.write_text("just a string, not a mapping\n", encoding="utf-8")
        with pytest.raises(LedgerRecordError):
            classify_mg3_record(bad)


# ---------------------------------------------------------------------------
# Streak → graduation (5 clean MG-3 records graduate the lane)
# ---------------------------------------------------------------------------


class TestStreakGraduation:
    def test_five_clean_records_graduate_the_lane(self, tmp_path: Path):
        qa = tmp_path / "qa"
        ledger = TrustLedger(tmp_path / "ledger")
        lane = "api_test"

        for i in range(4):
            rec = _clean_record(qa, f"feat-{i}-merge-review")
            state = ledger.record_merge(lane, mg3_path=rec)
            assert state.streak == i + 1
            assert ledger.graduated(lane) is False  # not yet at N=5

        # The 5th clean record crosses N=5 ⇒ graduated.
        rec5 = _clean_record(qa, "feat-4-merge-review")
        state = ledger.record_merge(lane, mg3_path=rec5)
        assert state.streak == 5
        assert state.state == STATE_GRADUATED
        assert ledger.graduated(lane) is True

    def test_streak_only_counts_mg3_records(self, tmp_path: Path):
        # A fresh lane with no records has streak 0 and is not graduated (no
        # retroactive credit for pre-format merges).
        ledger = TrustLedger(tmp_path / "ledger")
        assert ledger.streak("brand_new") == 0
        assert ledger.graduated("brand_new") is False

    def test_ledger_state_is_an_observable_file(self, tmp_path: Path):
        qa = tmp_path / "qa"
        root = tmp_path / "ledger"
        ledger = TrustLedger(root)
        rec = _clean_record(qa, "feat-x-merge-review")
        ledger.record_merge("api_test", mg3_path=rec)
        state_file = root / "api_test.yaml"
        assert state_file.exists()
        doc = yaml.safe_load(state_file.read_text())
        assert doc["lane"] == "api_test"
        assert doc["streak"] == 1
        assert doc["events"][0]["verdict"] == "clean"


# ---------------------------------------------------------------------------
# Demotion on a confirmed-blocker MG-3 mid-streak
# ---------------------------------------------------------------------------


class TestBlockerDemotion:
    def test_blocker_midstreak_demotes_instantly_and_resets(self, tmp_path: Path):
        qa = tmp_path / "qa"
        ledger = TrustLedger(tmp_path / "ledger")
        lane = "api_test"

        for i in range(3):
            ledger.record_merge(lane, mg3_path=_clean_record(qa, f"clean-{i}"))
        assert ledger.streak(lane) == 3

        # One confirmed-blocker MG-3 ⇒ instant demotion, streak reset.
        state = ledger.record_merge(lane, mg3_path=_blocker_record(qa, "blocker-1"))
        assert state.streak == 0
        assert state.state == STATE_ATTENDED
        assert ledger.graduated(lane) is False
        assert state.events[-1]["verdict"] == "blocker"
        assert state.events[-1]["source"] == "mg3"

    def test_nonempty_charged_failures_is_a_blocker_even_on_a_clean_mg3(
        self, tmp_path: Path
    ):
        qa = tmp_path / "qa"
        ledger = TrustLedger(tmp_path / "ledger")
        lane = "api_test"
        ledger.record_merge(lane, mg3_path=_clean_record(qa, "clean-0"))
        # The MG-3 is clean, but Stage 1 charged a regression ⇒ blocker.
        state = ledger.record_merge(
            lane,
            mg3_path=_clean_record(qa, "clean-1"),
            charged_failures=["tests/new.py::test_regress"],
        )
        assert state.streak == 0
        assert state.state == STATE_ATTENDED
        assert state.events[-1]["source"] == "charged_failures"

    def test_fresh_streak_after_demotion_regraduates(self, tmp_path: Path):
        qa = tmp_path / "qa"
        ledger = TrustLedger(tmp_path / "ledger")
        lane = "api_test"
        ledger.record_merge(lane, mg3_path=_blocker_record(qa, "b0"))
        for i in range(5):
            ledger.record_merge(lane, mg3_path=_clean_record(qa, f"fresh-{i}"))
        assert ledger.graduated(lane) is True


# ---------------------------------------------------------------------------
# Live-gate demotion-event file
# ---------------------------------------------------------------------------


def _write_demotion_event(qa_dir: Path, feature_id: str, lane: str) -> Path:
    qa_dir.mkdir(parents=True, exist_ok=True)
    event = {
        "feature_id": feature_id,
        "lane": lane,
        "source": "live_gate",
        "verdict": "fail",
        "timestamp": "2026-07-20T09:00:00Z",
        "receipt_ref": f"qa/live-gate-{feature_id}.yaml",
    }
    out = qa_dir / f"demotion-{feature_id}.yaml"
    out.write_text(yaml.safe_dump(event, sort_keys=False), encoding="utf-8")
    return out


class TestLiveGateDemotion:
    def test_load_demotion_event_shape(self, tmp_path: Path):
        path = _write_demotion_event(tmp_path, "FEAT-Z", "api_test")
        event = load_demotion_event(path)
        assert event.feature_id == "FEAT-Z"
        assert event.lane == "api_test"
        assert event.source == "live_gate"
        assert event.timestamp == "2026-07-20T09:00:00Z"

    def test_malformed_demotion_event_raises_loud(self, tmp_path: Path):
        bad = tmp_path / "demotion-bad.yaml"
        bad.write_text(yaml.safe_dump({"lane": "x"}), encoding="utf-8")  # missing keys
        with pytest.raises(LedgerRecordError):
            load_demotion_event(bad)

    def test_live_gate_event_demotes_a_graduated_lane(self, tmp_path: Path):
        qa = tmp_path / "qa"
        ledger = TrustLedger(tmp_path / "ledger")
        lane = "api_test"
        for i in range(5):
            ledger.record_merge(lane, mg3_path=_clean_record(qa, f"c-{i}"))
        assert ledger.graduated(lane) is True

        event = _write_demotion_event(qa, "FEAT-Z", lane)
        state = ledger.record_demotion(lane, event_path=event)
        assert state.streak == 0
        assert state.state == STATE_ATTENDED
        assert ledger.graduated(lane) is False
        assert state.events[-1]["kind"] == "demotion"
        assert state.events[-1]["source"] == "live_gate"


# ---------------------------------------------------------------------------
# Constitutional classes NEVER graduate
# ---------------------------------------------------------------------------


class TestConstitutional:
    def test_constitutional_lane_never_graduates(self, tmp_path: Path):
        qa = tmp_path / "qa"
        registry = ConstitutionalRegistry(targets=frozenset({"schema_migrations"}))
        ledger = TrustLedger(tmp_path / "ledger", constitutional=registry)
        lane = "schema_migrations"
        # Even after 5 clean records, a constitutional lane is never graduated.
        for i in range(5):
            ledger.record_merge(lane, mg3_path=_clean_record(qa, f"c-{i}"))
        assert ledger.streak(lane) == 5
        assert ledger.graduated(lane) is False

    def test_default_registry_mirrors_forge_override_targets(self, tmp_path: Path):
        ledger = TrustLedger(tmp_path / "ledger")
        assert ledger.constitutional("review_pr") is True
        assert ledger.constitutional("create_pr_after_review") is True
        assert ledger.constitutional("api_test") is False
        assert ledger.constitutional(None) is False


# ---------------------------------------------------------------------------
# clean_signal + should_auto_merge (the pure gate)
# ---------------------------------------------------------------------------


def _clean_report() -> MachineVerifyReport:
    return MachineVerifyReport(signal=SIGNAL_CLEAN, charged_failures=[])


def _catch_report() -> MachineVerifyReport:
    return MachineVerifyReport(
        signal=SIGNAL_CATCH, charged_failures=["tests/x.py::t"]
    )


class TestCleanSignal:
    def test_clean_report_is_clean(self):
        assert clean_signal(_clean_report()) is True

    def test_catch_report_is_not_clean(self):
        assert clean_signal(_catch_report()) is False

    def test_none_report_is_not_clean(self):
        assert clean_signal(None) is False

    def test_observed_unavailable_forces_not_clean(self):
        rep = MachineVerifyReport(signal=SIGNAL_CLEAN, observed_available=False)
        assert rep.disposition_required is True
        assert clean_signal(rep) is False


class TestShouldAutoMerge:
    def _graduated_ledger(self, tmp_path: Path, lane: str = "api_test") -> TrustLedger:
        qa = tmp_path / "qa"
        ledger = TrustLedger(tmp_path / "ledger")
        for i in range(5):
            ledger.record_merge(lane, mg3_path=_clean_record(qa, f"c-{i}"))
        return ledger

    def test_graduated_clean_nonconstitutional_fires(self, tmp_path: Path):
        ledger = self._graduated_ledger(tmp_path)
        d = should_auto_merge(ledger, "api_test", "main", _clean_report())
        assert d.fired is True

    def test_ungraduated_does_not_fire(self, tmp_path: Path):
        ledger = TrustLedger(tmp_path / "ledger")
        d = should_auto_merge(ledger, "api_test", "main", _clean_report())
        assert d.fired is False

    def test_constitutional_target_never_fires(self, tmp_path: Path):
        ledger = self._graduated_ledger(tmp_path)
        d = should_auto_merge(ledger, "api_test", "review_pr", _clean_report())
        assert d.fired is False
        assert "constitutional" in d.reason

    def test_catch_signal_does_not_fire(self, tmp_path: Path):
        ledger = self._graduated_ledger(tmp_path)
        d = should_auto_merge(ledger, "api_test", "main", _catch_report())
        assert d.fired is False


# ---------------------------------------------------------------------------
# auto_merge_if_graduated — the 6th merge auto-runs manager.merge() (real git)
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def merge_fixture(tmp_path: Path) -> tuple[Path, Worktree, WorktreeManager]:
    """A real git repo on ``main`` + a feature branch worktree ready to merge."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")

    # A feature branch with one commit — the change to be merged.
    _git(repo, "checkout", "-q", "-b", "feat/thing")
    (repo / "feature.py").write_text("y = 2\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feature work")
    _git(repo, "checkout", "-q", "main")

    manager = WorktreeManager(repo_root=repo)
    worktree = Worktree(
        task_id="FEAT-THING",
        branch_name="feat/thing",
        path=repo,
        base_branch="main",
    )
    return repo, worktree, manager


class TestAutoMergeIntegration:
    def test_sixth_merge_auto_runs_manager_merge(
        self, tmp_path: Path, merge_fixture, monkeypatch
    ):
        repo, worktree, manager = merge_fixture
        monkeypatch.setenv("GUARDKIT_AUTO_MERGE", "1")  # master switch ON

        qa = tmp_path / "qa"
        ledger = TrustLedger(tmp_path / "ledger")
        lane = "api_test"
        for i in range(5):
            ledger.record_merge(lane, mg3_path=_clean_record(qa, f"c-{i}"))
        assert ledger.graduated(lane) is True

        before = _git(repo, "rev-parse", "HEAD")
        decision = auto_merge_if_graduated(
            manager, worktree, ledger, lane, _clean_report(), cleanup=False
        )
        assert decision.fired is True
        after = _git(repo, "rev-parse", "HEAD")
        assert after != before  # a real merge commit landed
        # --no-ff ⇒ a merge commit with two parents.
        parents = _git(repo, "rev-list", "--parents", "-n", "1", "HEAD").split()
        assert len(parents) == 3  # commit + 2 parents
        # The feature file is now on main.
        assert (repo / "feature.py").exists()

    def test_master_switch_off_never_merges(
        self, tmp_path: Path, merge_fixture, monkeypatch
    ):
        repo, worktree, manager = merge_fixture
        monkeypatch.delenv("GUARDKIT_AUTO_MERGE", raising=False)  # switch OFF (default)

        qa = tmp_path / "qa"
        ledger = TrustLedger(tmp_path / "ledger")
        lane = "api_test"
        for i in range(5):
            ledger.record_merge(lane, mg3_path=_clean_record(qa, f"c-{i}"))

        before = _git(repo, "rev-parse", "HEAD")
        decision = auto_merge_if_graduated(
            manager, worktree, ledger, lane, _clean_report()
        )
        assert decision.fired is False
        assert "switch OFF" in decision.reason
        assert _git(repo, "rev-parse", "HEAD") == before  # nothing merged

    def test_demoted_lane_does_not_auto_merge(
        self, tmp_path: Path, merge_fixture, monkeypatch
    ):
        repo, worktree, manager = merge_fixture
        monkeypatch.setenv("GUARDKIT_AUTO_MERGE", "1")

        qa = tmp_path / "qa"
        ledger = TrustLedger(tmp_path / "ledger")
        lane = "api_test"
        for i in range(5):
            ledger.record_merge(lane, mg3_path=_clean_record(qa, f"c-{i}"))
        # A confirmed blocker demotes the lane — the next merge is attended.
        ledger.record_merge(lane, mg3_path=_blocker_record(qa, "blk"))

        before = _git(repo, "rev-parse", "HEAD")
        decision = auto_merge_if_graduated(
            manager, worktree, ledger, lane, _clean_report()
        )
        assert decision.fired is False
        assert _git(repo, "rev-parse", "HEAD") == before

    def test_constitutional_target_never_merges_even_at_streak(
        self, tmp_path: Path, merge_fixture, monkeypatch
    ):
        repo, worktree, manager = merge_fixture
        monkeypatch.setenv("GUARDKIT_AUTO_MERGE", "1")

        qa = tmp_path / "qa"
        registry = ConstitutionalRegistry(targets=frozenset({"main"}))
        ledger = TrustLedger(tmp_path / "ledger", constitutional=registry)
        lane = "api_test"
        for i in range(5):
            ledger.record_merge(lane, mg3_path=_clean_record(qa, f"c-{i}"))

        before = _git(repo, "rev-parse", "HEAD")
        decision = auto_merge_if_graduated(
            manager, worktree, ledger, lane, _clean_report()
        )
        assert decision.fired is False
        assert _git(repo, "rev-parse", "HEAD") == before
