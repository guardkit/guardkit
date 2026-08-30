"""The architecture-rules receipt: it is written, it is honest, and it never bites.

This is the first and smallest step of wiring ``guardkit.conformance`` into the build
loop. After each Coach turn the checker runs over the build worktree and its report is
written beside that turn's Coach verdict. Nothing reads it. Nothing blocks.

What is proven here:

1. A worktree that has written its own ``docs/architecture-rules.yaml`` and then broken
   one of its own rules gets a receipt naming that place, beside the turn's Coach
   verdict, with the rule's own sentence carried through.
2. The scope is this task's changed files: a break inside the task's files is listed, a
   break the task never touched is counted but not listed.
3. A worktree with no rules file still gets a receipt, and that receipt says nothing was
   checked — which is not the same as clean. The build is untouched.
4. A checker that raises costs one warning and nothing else. No receipt, no exception
   out, build untouched.
5. Receipt naming follows the turn number, exactly as the Coach verdict files do, and
   lands in the same per-task directory.
6. The hook really is at the per-turn Coach seam in the build loop.

Network-free, subprocess-free, no broker: ``tmp_path`` only.
"""

from __future__ import annotations

import inspect
import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from guardkit.orchestrator.arch_conformance import (
    observe_task_conformance,
    write_turn_receipt,
)
from guardkit.orchestrator.paths import TaskArtifactPaths

TASK_ID = "TASK-ARCH-001"


# ---------------------------------------------------------------------------
# Fixture material — a tiny repository that states its own rule and breaks it
# ---------------------------------------------------------------------------

RULES = """
format_version: "1.0"
layout:
  source_root: src
rules:
  - id: R-NO-URLLIB
    rule: A feature module does not reach the network directly; it uses the shared client.
    source_document: docs/architecture/adr-009.md
    source_section: "HTTP"
    source_sentence: "Outbound HTTP goes through the shared client, never urllib."
    signals:
      kind: forbidden-imports
      scope: feature_modules
      modules: [urllib.request]
"""

ROUTER_WITH_BREAK = """import urllib.request


def fetch_the_thing(url):
    return urllib.request.urlopen(url)
"""

ROUTER_CLEAN = """def fetch_the_thing(client, url):
    return client.get(url)
"""


def make_worktree(tmp_path: Path, *, files: dict[str, str], rules: str | None) -> Path:
    """A build worktree on disk: some source, and maybe a rules file."""
    root = tmp_path / "worktree"
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    if rules is not None:
        rules_path = root / "docs" / "architecture-rules.yaml"
        rules_path.parent.mkdir(parents=True, exist_ok=True)
        rules_path.write_text(rules, encoding="utf-8")
    root.mkdir(parents=True, exist_ok=True)
    return root


def write_coach_verdict(worktree: Path, turn: int) -> Path:
    """The Coach verdict file this turn's receipt is written beside."""
    path = TaskArtifactPaths.autobuild_dir(TASK_ID, worktree) / f"coach_turn_{turn}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"decision": "approve"}), encoding="utf-8")
    return path


def read_receipt(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. A rules file and a break in it: the receipt names the place
# ---------------------------------------------------------------------------


def test_a_broken_rule_in_the_task_s_own_file_is_named_in_the_receipt(tmp_path):
    worktree = make_worktree(
        tmp_path,
        files={"src/users/router.py": ROUTER_WITH_BREAK},
        rules=RULES,
    )
    coach_verdict = write_coach_verdict(worktree, 1)

    receipt = observe_task_conformance(
        worktree, task_id=TASK_ID, turn=1, changed_files=["src/users/router.py"]
    )

    assert receipt is not None
    assert receipt.exists(), "the receipt must be written"
    assert receipt.parent == coach_verdict.parent, (
        "the receipt belongs beside the Coach verdict for the same turn"
    )

    payload = read_receipt(receipt)
    assert payload["ran"] is True
    assert payload["could_not_run"] is None
    findings = payload["findings"]
    assert len(findings) == 1, findings
    assert findings[0]["rule_id"] == "R-NO-URLLIB"
    assert findings[0]["file"] == "src/users/router.py"
    assert findings[0]["line"] == 1
    # The rule's own sentence travels with the finding, so a reader never has to
    # go and look the rule up.
    assert "shared client" in findings[0]["rule_says"]
    assert findings[0]["rule_source"]["document"] == "docs/architecture/adr-009.md"
    # No verdict, no score, no severity — the checker's own promise, kept on disk.
    assert payload["reports"] == "facts only — no score, no verdict, no severity"
    assert "severity" not in json.dumps(findings)


def test_a_clean_task_file_gets_a_receipt_with_no_findings(tmp_path):
    worktree = make_worktree(
        tmp_path, files={"src/users/router.py": ROUTER_CLEAN}, rules=RULES
    )
    write_coach_verdict(worktree, 1)

    receipt = observe_task_conformance(
        worktree, task_id=TASK_ID, turn=1, changed_files=["src/users/router.py"]
    )

    payload = read_receipt(receipt)
    assert payload["ran"] is True
    assert payload["findings"] == []
    assert payload["exit_code"] == 0


# ---------------------------------------------------------------------------
# 2. The scope is this task's changed files
# ---------------------------------------------------------------------------


def test_a_break_the_task_never_touched_is_counted_but_not_listed(tmp_path):
    worktree = make_worktree(
        tmp_path,
        files={
            "src/users/router.py": ROUTER_CLEAN,
            "src/orders/router.py": ROUTER_WITH_BREAK,
        },
        rules=RULES,
    )
    write_coach_verdict(worktree, 1)

    receipt = observe_task_conformance(
        worktree, task_id=TASK_ID, turn=1, changed_files=["src/users/router.py"]
    )

    payload = read_receipt(receipt)
    assert payload["narrowed_to_the_files_this_change_touched"] == [
        "src/users/router.py"
    ]
    assert payload["findings"] == [], "orders/ is not this task's work"
    assert payload["findings_elsewhere_in_the_repository"] == 1, (
        "the break in orders/ is still counted, so the receipt is not read as clean"
    )


def test_an_absolute_changed_file_path_is_understood(tmp_path):
    worktree = make_worktree(
        tmp_path, files={"src/users/router.py": ROUTER_WITH_BREAK}, rules=RULES
    )
    write_coach_verdict(worktree, 1)

    receipt = observe_task_conformance(
        worktree,
        task_id=TASK_ID,
        turn=1,
        changed_files=[str(worktree / "src" / "users" / "router.py")],
    )

    payload = read_receipt(receipt)
    assert payload["narrowed_to_the_files_this_change_touched"] == [
        "src/users/router.py"
    ]
    assert len(payload["findings"]) == 1


def test_with_no_changed_files_named_the_whole_tree_is_reported_on_and_says_so(tmp_path):
    worktree = make_worktree(
        tmp_path, files={"src/orders/router.py": ROUTER_WITH_BREAK}, rules=RULES
    )
    write_coach_verdict(worktree, 1)

    receipt = observe_task_conformance(
        worktree, task_id=TASK_ID, turn=1, changed_files=[]
    )

    payload = read_receipt(receipt)
    assert payload["narrowed_to_the_files_this_change_touched"] is None
    assert len(payload["findings"]) == 1
    assert any("whole source tree" in note for note in payload["notes"]), payload["notes"]


# ---------------------------------------------------------------------------
# 3. No rules file: recorded, never silent, and the build is untouched
# ---------------------------------------------------------------------------


def test_a_repository_with_no_rules_file_still_gets_an_honest_receipt(tmp_path, caplog):
    worktree = make_worktree(
        tmp_path, files={"src/users/router.py": ROUTER_WITH_BREAK}, rules=None
    )
    coach_verdict = write_coach_verdict(worktree, 1)

    with caplog.at_level(logging.INFO, logger="guardkit.orchestrator.arch_conformance"):
        receipt = observe_task_conformance(
            worktree, task_id=TASK_ID, turn=1, changed_files=["src/users/router.py"]
        )

    assert receipt is not None and receipt.exists()
    payload = read_receipt(receipt)
    assert payload["ran"] is False
    assert payload["could_not_run"], "absence must be written down"
    assert "not the same as clean" in payload["could_not_run"]
    assert payload["findings"] == []
    assert payload["exit_code"] == 2, "could-not-run is never exit 0"

    # The build path is untouched: the Coach verdict is exactly as it was, and
    # nothing but the receipt was added to the task directory.
    assert json.loads(coach_verdict.read_text()) == {"decision": "approve"}
    assert sorted(p.name for p in receipt.parent.iterdir()) == [
        "arch_conformance_turn_1.json",
        "coach_turn_1.json",
    ]

    # Exactly one log line, at info, naming the receipt and the finding count.
    lines = [r for r in caplog.records if r.name.endswith("arch_conformance")]
    assert len(lines) == 1
    assert lines[0].levelno == logging.INFO
    assert str(receipt) in lines[0].getMessage()
    assert "0 finding(s)" in lines[0].getMessage()


def test_the_run_over_a_repository_with_no_rules_file_reads_no_source(tmp_path):
    """It must cost a build nothing but one small receipt."""
    worktree = make_worktree(
        tmp_path, files={"src/users/router.py": ROUTER_WITH_BREAK}, rules=None
    )
    receipt = observe_task_conformance(worktree, task_id=TASK_ID, turn=1)
    payload = read_receipt(receipt)
    assert payload["files_scanned"] == 0
    assert payload["rules"] == []


# ---------------------------------------------------------------------------
# 4. A checker that raises costs one warning and nothing else
# ---------------------------------------------------------------------------


def test_a_checker_exception_is_swallowed_with_one_warning(tmp_path, caplog):
    worktree = make_worktree(
        tmp_path, files={"src/users/router.py": ROUTER_WITH_BREAK}, rules=RULES
    )
    coach_verdict = write_coach_verdict(worktree, 1)

    with patch("guardkit.conformance.run", side_effect=RuntimeError("boom")):
        with caplog.at_level(
            logging.INFO, logger="guardkit.orchestrator.arch_conformance"
        ):
            result = observe_task_conformance(
                worktree, task_id=TASK_ID, turn=1, changed_files=["src/users/router.py"]
            )

    assert result is None, "no receipt path is claimed when none was written"
    assert not (
        TaskArtifactPaths.arch_conformance_path(TASK_ID, 1, worktree).exists()
    )
    # The build path is untouched.
    assert json.loads(coach_verdict.read_text()) == {"decision": "approve"}

    warnings = [
        r
        for r in caplog.records
        if r.name.endswith("arch_conformance") and r.levelno == logging.WARNING
    ]
    assert len(warnings) == 1
    assert "RuntimeError" in warnings[0].getMessage()
    assert "build is untouched" in warnings[0].getMessage()


def test_a_receipt_that_cannot_be_written_is_also_only_a_warning(tmp_path, caplog):
    worktree = make_worktree(
        tmp_path, files={"src/users/router.py": ROUTER_CLEAN}, rules=RULES
    )
    with patch(
        "guardkit.orchestrator.arch_conformance._receipt_path",
        side_effect=OSError("read-only"),
    ):
        with caplog.at_level(
            logging.WARNING, logger="guardkit.orchestrator.arch_conformance"
        ):
            assert (
                observe_task_conformance(worktree, task_id=TASK_ID, turn=1) is None
            )
    assert any("OSError" in r.getMessage() for r in caplog.records)


def test_write_turn_receipt_itself_raises_so_the_swallowing_is_in_one_place(tmp_path):
    """The swallowing lives in ``observe_task_conformance`` and nowhere else."""
    worktree = make_worktree(
        tmp_path, files={"src/users/router.py": ROUTER_CLEAN}, rules=RULES
    )
    with patch("guardkit.conformance.run", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            write_turn_receipt(worktree, TASK_ID, 1)


# ---------------------------------------------------------------------------
# 5. Naming and turn numbering follow the Coach verdict files
# ---------------------------------------------------------------------------


def test_the_receipt_is_named_and_numbered_like_the_coach_verdict(tmp_path):
    worktree = tmp_path / "worktree"
    for turn in (1, 2, 11):
        coach = write_coach_verdict(worktree, turn)
        receipt = TaskArtifactPaths.arch_conformance_path(TASK_ID, turn, worktree)
        assert receipt.name == f"arch_conformance_turn_{turn}.json"
        assert coach.name == f"coach_turn_{turn}.json"
        assert receipt.parent == coach.parent
        assert receipt.parent == TaskArtifactPaths.autobuild_dir(TASK_ID, worktree)


def test_each_turn_gets_its_own_receipt(tmp_path):
    worktree = make_worktree(
        tmp_path, files={"src/users/router.py": ROUTER_WITH_BREAK}, rules=RULES
    )
    written = []
    for turn in (1, 2, 3):
        write_coach_verdict(worktree, turn)
        written.append(
            observe_task_conformance(
                worktree,
                task_id=TASK_ID,
                turn=turn,
                changed_files=["src/users/router.py"],
            )
        )
    assert len({p.name for p in written}) == 3
    assert all(p.exists() for p in written)
    assert [p.name for p in written] == [
        "arch_conformance_turn_1.json",
        "arch_conformance_turn_2.json",
        "arch_conformance_turn_3.json",
    ]


def test_the_path_template_matches_the_helper(tmp_path):
    assert TaskArtifactPaths.ARCH_CONFORMANCE == (
        ".guardkit/autobuild/{task_id}/arch_conformance_turn_{turn}.json"
    )
    assert TaskArtifactPaths.arch_conformance_path(
        TASK_ID, 4, tmp_path
    ) == tmp_path / ".guardkit" / "autobuild" / TASK_ID / "arch_conformance_turn_4.json"


# ---------------------------------------------------------------------------
# 6. The hook is at the per-turn Coach seam, and reads nothing back
# ---------------------------------------------------------------------------


def test_the_hook_is_wired_at_the_per_turn_coach_seam():
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    source = inspect.getsource(AutoBuildOrchestrator._execute_turn)
    assert "observe_task_conformance" in source, (
        "the receipt must be written from the per-turn Coach seam"
    )
    # After the Coach has spoken for this turn, not before.
    assert source.index("_invoke_coach_safely") < source.index(
        "observe_task_conformance"
    )
    # And nothing reads it back: the call's return value is not used, and no
    # verdict, issue or feedback is derived from it.
    call_line = next(
        line for line in source.splitlines()
        if line.strip().startswith("observe_task_conformance(")
    )
    assert "=" not in call_line, (
        f"the receipt is written and not read back; got {call_line!r}"
    )
    call = source[source.index("observe_task_conformance(") :][:400]
    assert "must_fix" not in call and "decision" not in call


def test_relative_file_tidying_strips_prefixes_not_characters(tmp_path):
    """The coach's driving inputs, pinned: './' tidies, '.hidden' survives,
    '../outside' is dropped instead of becoming an invented in-tree path."""
    from guardkit.orchestrator.arch_conformance import _relative_files

    got = _relative_files(
        ["./src/a.py", ".hidden/pkg/mod.py", "../elsewhere/mod.py", "src/b.py"],
        tmp_path,
    )
    assert "src/a.py" in got
    assert ".hidden/pkg/mod.py" in got
    assert "src/b.py" in got
    assert all("elsewhere" not in g for g in got)
