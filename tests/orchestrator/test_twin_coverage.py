"""A hurl stamp with no twin must not clear the build unnoticed.

The hole these tests close (observed on api_test, 2026-08-26): FEAT-B8E3 and
FEAT-0E07 both stamped their scenarios ``verifier: hurl``; B8E3 wrote its twin
under ``qa/twins/``, 0E07 shipped ZERO ``.hurl`` files and completed 5/5 —
nothing between plan approval and build completion checked twin existence.

What is proven here:

1. A feature whose plan stamps scenarios ``verifier: hurl`` with no twin
   files yields the missing list by name; by default (advisory) the build is
   NOT failed, a plain receipt is written, and a warning is rendered.
2. With ``qa.enforce_twin_coverage: true`` (or the env override) the same
   miss fails the build.
3. A covered feature passes both ways, through both doors of the mapping
   rule: an existing file named by the stamp's ``test_ref``, and a twin
   whose comments carry the scenario title (the FEAT-B8E3 acceptance-file
   layout and the per-scenario-twin layout both carry it).
4. The finalize-phase wiring: a completed build stays green in advisory
   mode, fails under enforcement when twins are missing, passes under
   enforcement when covered, and an already-failed build is not touched.

Network-free, subprocess-free: tmp_path only. The orchestrator wiring tests
follow tests/orchestrator/test_boot_smoke_wiring.py (same construction, and
the same warning applies: do NOT move this file under tests/integration/,
where CI's default run would silently skip it).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    TaskExecutionResult,
    WaveExecutionResult,
)
from guardkit.orchestrator.twin_coverage import (
    ENFORCE_ENV,
    RECEIPT_RELATIVE_PATH,
    check_twin_coverage,
    is_twin_coverage_enforced,
    render_twin_coverage_lines,
    write_twin_coverage_receipt,
)
from guardkit.orchestrator.verifier_stamp import ScenarioStamp
from guardkit.worktrees import Worktree


# ---------------------------------------------------------------------------
# Fixture material — the real api_test conventions, miniaturised
# ---------------------------------------------------------------------------

TITLE_DELETE = "Deleting an existing user succeeds"
TITLE_COUNTS = "User deletion is reflected in all count endpoints"
TITLE_REFUSED = "Deleting a user that does not exist is refused"

#: The FEAT-B8E3 layout: ONE acceptance twin covering several scenarios, each
#: quoted verbatim in comments (``# Gherkin:`` / ``#   Scenario: <title>``).
ACCEPTANCE_TWIN = f"""\
# HURL ACCEPTANCE TESTS — User Deletion
# Gherkin:
#   Scenario: {TITLE_DELETE}
#     Given a user exists
#     Then deleting succeeds

DELETE {{{{host}}}}/users/1
HTTP 204

# Gherkin:
#   Scenario: {TITLE_COUNTS}

GET {{{{host}}}}/users/count
HTTP 200
"""

#: The per-scenario layout (FEAT-UDBE / FEAT-TIME): one twin per scenario,
#: title in the header comment with an approval annotation.
PER_SCENARIO_TWIN = f"""\
# HURL TWIN of spec 9.3
# Scenario: {TITLE_REFUSED} (APPROVED AS PROPOSED by Rich 2026-07-28)

DELETE {{{{host}}}}/users/by-email?email=missing@example.com
HTTP 404
"""


def _stamps(*titles: str) -> Dict[str, ScenarioStamp]:
    return {t: ScenarioStamp(verifier="hurl") for t in titles}


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 1. Missing twins: listed by name, advisory does not block
# ---------------------------------------------------------------------------


def test_hurl_stamps_with_no_twins_yield_the_missing_list(tmp_path: Path) -> None:
    scenarios = _stamps(TITLE_DELETE, TITLE_COUNTS)
    # A non-hurl stamp must be ignored entirely, not reported missing.
    scenarios["The endpoint survives a database outage"] = ScenarioStamp(
        verifier="probe:process"
    )

    report = check_twin_coverage("FEAT-TW01", scenarios, tmp_path, enforced=False)

    assert report.checked == 2
    assert report.missing == [TITLE_DELETE, TITLE_COUNTS]
    assert report.blocks_build is False  # advisory: never fails the build
    assert report.twins_scanned == 0


def test_enforcement_on_makes_the_same_miss_block_the_build(tmp_path: Path) -> None:
    report = check_twin_coverage(
        "FEAT-TW01", _stamps(TITLE_DELETE), tmp_path, enforced=True
    )
    assert report.missing == [TITLE_DELETE]
    assert report.blocks_build is True


# ---------------------------------------------------------------------------
# 2. Covered: both doors of the mapping rule
# ---------------------------------------------------------------------------


def test_a_twin_carrying_the_title_in_comments_covers_the_scenario(
    tmp_path: Path,
) -> None:
    """The FEAT-B8E3 shape: one acceptance file, several scenarios."""
    _write(tmp_path, "qa/twins/user-deletion/acceptance.hurl", ACCEPTANCE_TWIN)

    report = check_twin_coverage(
        "FEAT-TW01", _stamps(TITLE_DELETE, TITLE_COUNTS), tmp_path, enforced=True
    )

    assert report.missing == []
    assert report.blocks_build is False
    for status in report.statuses:
        assert status.found is True
        assert status.matched_by == "scenario title"
        assert status.twin == "qa/twins/user-deletion/acceptance.hurl"


def test_a_stamp_naming_its_twin_file_covers_the_scenario(tmp_path: Path) -> None:
    """The FEAT-TIME / FEAT-UDBE shape: test_ref names the twin outright."""
    _write(tmp_path, "qa/twins/users-delete/refused.hurl", "DELETE x\nHTTP 404\n")
    scenarios = {
        TITLE_REFUSED: ScenarioStamp(
            verifier="hurl", test_ref="qa/twins/users-delete/refused.hurl"
        )
    }

    report = check_twin_coverage("FEAT-TW01", scenarios, tmp_path, enforced=True)

    assert report.missing == []
    (status,) = report.statuses
    assert status.matched_by == "named file"
    assert status.twin == "qa/twins/users-delete/refused.hurl"


def test_a_missing_named_file_falls_back_to_the_title_scan(tmp_path: Path) -> None:
    _write(tmp_path, "qa/twins/users-delete/refused.hurl", PER_SCENARIO_TWIN)
    scenarios = {
        TITLE_REFUSED: ScenarioStamp(
            verifier="hurl", test_ref="qa/twins/somewhere-else/gone.hurl"
        )
    }

    report = check_twin_coverage("FEAT-TW01", scenarios, tmp_path, enforced=True)

    assert report.missing == []
    (status,) = report.statuses
    assert status.matched_by == "scenario title"


def test_title_matching_is_exact_with_only_setoff_decoration_tolerated(
    tmp_path: Path,
) -> None:
    # Annotation and compiler rule-off forms both count...
    _write(
        tmp_path,
        "qa/twins/a/annotated.hurl",
        f"# Scenario: {TITLE_DELETE} (APPROVED AS PROPOSED by Rich 2026-07-28)\nGET x\nHTTP 200\n",
    )
    _write(
        tmp_path,
        "qa/twins/a/compiled.hurl",
        f"# --- Scenario: {TITLE_COUNTS} ---\nGET x\nHTTP 200\n",
    )
    # ...but a LONGER title never satisfies a shorter stamp, and a title in a
    # request body (not a comment) is not a claim of coverage.
    _write(
        tmp_path,
        "qa/twins/a/longer.hurl",
        f"# Scenario: {TITLE_REFUSED} loudly and twice\nGET x\nHTTP 200\n",
    )
    _write(
        tmp_path,
        "qa/twins/a/body-only.hurl",
        f'POST x\n{{"note": "Scenario: {TITLE_REFUSED}"}}\nHTTP 200\n',
    )

    report = check_twin_coverage(
        "FEAT-TW01",
        _stamps(TITLE_DELETE, TITLE_COUNTS, TITLE_REFUSED),
        tmp_path,
        enforced=False,
    )

    assert report.missing == [TITLE_REFUSED]


# ---------------------------------------------------------------------------
# 3. Receipt and rendered lines
# ---------------------------------------------------------------------------


def test_receipt_lists_every_stamped_scenario_found_or_missing(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "qa/twins/user-deletion/acceptance.hurl", ACCEPTANCE_TWIN)
    report = check_twin_coverage(
        "FEAT-TW01", _stamps(TITLE_DELETE, TITLE_REFUSED), tmp_path, enforced=False
    )

    receipt_path = write_twin_coverage_receipt(report, tmp_path)

    assert receipt_path == tmp_path / RECEIPT_RELATIVE_PATH
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert payload["feature"] == "FEAT-TW01"
    assert payload["enforcement"] == "off (advisory)"
    by_name = {row["scenario"]: row for row in payload["scenarios"]}
    assert by_name[TITLE_DELETE]["twin_found"] is True
    assert by_name[TITLE_REFUSED]["twin_found"] is False
    assert payload["missing"] == [TITLE_REFUSED]


def test_rendered_lines_warn_in_plain_english_and_stay_silent_without_stamps(
    tmp_path: Path,
) -> None:
    report = check_twin_coverage(
        "FEAT-TW01", _stamps(TITLE_DELETE), tmp_path, enforced=False
    )
    lines = render_twin_coverage_lines(report)
    joined = "\n".join(lines)
    assert "WARNING" in joined
    assert TITLE_DELETE in joined
    assert "advisory" in joined
    assert "qa.enforce_twin_coverage" in joined

    # No hurl stamps at all -> no twin-coverage noise.
    empty = check_twin_coverage("FEAT-TW01", {}, tmp_path, enforced=False)
    assert render_twin_coverage_lines(empty) == []


# ---------------------------------------------------------------------------
# 4. Flag resolution: config key + env override, default off
# ---------------------------------------------------------------------------


def test_flag_defaults_off_and_reads_config_and_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ENFORCE_ENV, raising=False)
    assert is_twin_coverage_enforced(tmp_path) is False

    _write(tmp_path, ".guardkit/config.yaml", "qa:\n  enforce_twin_coverage: true\n")
    assert is_twin_coverage_enforced(tmp_path) is True

    # A falsy env value wins over the config file...
    monkeypatch.setenv(ENFORCE_ENV, "0")
    assert is_twin_coverage_enforced(tmp_path) is False
    # ...and a truthy one needs no config file at all.
    monkeypatch.setenv(ENFORCE_ENV, "1")
    assert is_twin_coverage_enforced(tmp_path / "elsewhere") is True


# ---------------------------------------------------------------------------
# 5. Finalize-phase wiring (the boot-smoke-wiring construction)
# ---------------------------------------------------------------------------


def _make_orchestrator(repo_root: Path) -> FeatureOrchestrator:
    return FeatureOrchestrator(
        repo_root=repo_root,
        max_turns=1,
        worktree_manager=MagicMock(),
        quiet=True,
    )


def _make_worktree(path: Path) -> Worktree:
    path.mkdir(parents=True, exist_ok=True)
    return Worktree(
        task_id="FEAT-TW01",
        branch_name="autobuild/FEAT-TW01",
        path=path,
        base_branch="main",
    )


def _make_feature(scenarios: Dict[str, ScenarioStamp]):
    feature = MagicMock()
    feature.id = "FEAT-TW01"
    feature.name = "Twin Coverage Test Feature"
    feature.scenarios = scenarios
    task = MagicMock()
    task.id = "TASK-TW-001"
    feature.tasks = [task]
    return feature


def _wave(success: bool) -> WaveExecutionResult:
    return WaveExecutionResult(
        wave_number=1,
        task_ids=["TASK-TW-001"],
        results=[
            TaskExecutionResult(
                task_id="TASK-TW-001",
                success=success,
                total_turns=1,
                final_decision="approved" if success else "rejected",
            )
        ],
        all_succeeded=success,
    )


def _finalize(orchestrator, feature, waves: List[WaveExecutionResult], worktree):
    with patch(
        "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature"
    ):
        return orchestrator._finalize_phase(feature, waves, worktree)


def test_finalize_advisory_missing_twins_stays_green_and_writes_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ENFORCE_ENV, raising=False)
    orchestrator = _make_orchestrator(tmp_path / "repo")
    (tmp_path / "repo").mkdir()
    worktree = _make_worktree(tmp_path / "wt")
    feature = _make_feature(_stamps(TITLE_DELETE, TITLE_COUNTS))

    result = _finalize(orchestrator, feature, [_wave(True)], worktree)

    assert result.success is True
    assert result.status == "completed"
    receipt = tmp_path / "wt" / RECEIPT_RELATIVE_PATH
    assert receipt.is_file()
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["missing"] == [TITLE_DELETE, TITLE_COUNTS]


def test_finalize_enforced_missing_twins_fails_the_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ENFORCE_ENV, raising=False)
    repo_root = tmp_path / "repo"
    _write(repo_root, ".guardkit/config.yaml", "qa:\n  enforce_twin_coverage: true\n")
    orchestrator = _make_orchestrator(repo_root)
    worktree = _make_worktree(tmp_path / "wt")
    feature = _make_feature(_stamps(TITLE_DELETE))

    result = _finalize(orchestrator, feature, [_wave(True)], worktree)

    assert result.success is False
    assert result.status == "failed"
    assert feature.status == "failed"
    assert "twin" in (result.error or "").lower()


def test_finalize_enforced_covered_build_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ENFORCE_ENV, raising=False)
    repo_root = tmp_path / "repo"
    _write(repo_root, ".guardkit/config.yaml", "qa:\n  enforce_twin_coverage: true\n")
    orchestrator = _make_orchestrator(repo_root)
    worktree = _make_worktree(tmp_path / "wt")
    _write(tmp_path / "wt", "qa/twins/user-deletion/acceptance.hurl", ACCEPTANCE_TWIN)
    feature = _make_feature(_stamps(TITLE_DELETE, TITLE_COUNTS))

    result = _finalize(orchestrator, feature, [_wave(True)], worktree)

    assert result.success is True
    assert result.status == "completed"
    assert result.error is None


def test_finalize_leaves_an_already_failed_build_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed build keeps its own answer; no twin receipt is piled on."""
    monkeypatch.delenv(ENFORCE_ENV, raising=False)
    orchestrator = _make_orchestrator(tmp_path / "repo")
    (tmp_path / "repo").mkdir()
    worktree = _make_worktree(tmp_path / "wt")
    feature = _make_feature(_stamps(TITLE_DELETE))

    result = _finalize(orchestrator, feature, [_wave(False)], worktree)

    assert result.success is False
    assert result.error == "1 task(s) failed"
    assert not (tmp_path / "wt" / RECEIPT_RELATIVE_PATH).exists()
