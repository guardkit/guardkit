"""Telling the code generator where its own code sits against the repository's rules.

The step after watching. When ``GUARDKIT_ARCH_CONFORMANCE_BLOCKING`` is set, a place
in the code the code generator just wrote that sits somewhere this repository's own
architecture rules do not name comes back to it as one fix-this issue on its next
turn, with nobody involved.

What is proven here:

1. The switch is named and read exactly like the two that came before it, and it is
   off by default. Off means nothing at all happens: no check is added, no command
   runs, no verdict changes.
2. **The check only ever judges the files the task itself changed.** A place that was
   already in the repository before the task began, that the task never touched,
   passes. This is the whole of the design: the pilot repository's main branch carries
   three known places on purpose, and a whole-tree check would fail every task in
   every build forever on somebody else's code.
3. A brand-new file git has not been told about yet is still read. Missing it would be
   a check that runs, looks in the wrong place, and reports success.
4. A repository that has written no rules file gets no check, and no failure.
5. A checker that cannot run says so and exits 0. It never becomes a wall.
6. End to end through the machinery that already exists: the check is frozen before
   the first turn beside every other one, the failure comes back through the same
   reviewer guard as exactly one must-fix issue, and the words in it are the checker's
   own -- the rule's id, the file and line, and the sentence the rule quotes from the
   architecture record.

Local only: real git repositories under ``tmp_path``, no network, no broker, no
container, no model.
"""

from __future__ import annotations

import json
import logging
import subprocess
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from guardkit.orchestrator import arch_conformance
from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.arch_conformance import (
    BLOCKING_ENV_VAR,
    RULE_ID,
    blocking_requested,
    build_arch_conformance_rule,
    check_changed_files,
    files_changed_since,
    main,
    starting_commit,
)
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.quality_gates.spec_conformance import (
    AssertCommandRule,
    evaluate_from_snapshot,
    load_snapshot,
    snapshot_paths,
    snapshot_task_conformance,
)

TASK_ID = "TASK-ARCH-RUNG3"

# The rules file the fixture repository writes about itself. It quotes a sentence and
# names where the sentence came from, because that is what the checker prints and what
# the code generator is meant to read.
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

CLEAN_FILE = """from shared.client import get


def fetch_the_thing(url):
    return get(url)
"""

FILE_WITH_A_BREAK = """import urllib.request


def fetch_the_thing(url):
    return urllib.request.urlopen(url)
"""


# ---------------------------------------------------------------------------
# Fixture material
# ---------------------------------------------------------------------------


def git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, text=True, check=True, timeout=60)
    return done.stdout


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path):
    """A small git repository that has written its own architecture rules.

    ``files`` is what is committed as the starting point -- everything the task
    inherits and did not write. It comes back with the repository path and the commit
    the task starts from.
    """

    def _make(files: dict[str, str], *, rules: str | None = RULES) -> tuple[Path, str]:
        root = tmp_path / "worktree"
        root.mkdir(parents=True, exist_ok=True)
        for rel, text in files.items():
            write(root, rel, text)
        if rules is not None:
            write(root, "docs/architecture-rules.yaml", rules)
        git(root, "init", "-q")
        git(root, "add", ".")
        git(root, "-c", "user.email=t@example.com", "-c", "user.name=T",
            "commit", "-q", "-m", "the starting point")
        return root, git(root, "rev-parse", "HEAD").strip()

    return _make


# ---------------------------------------------------------------------------
# 1. The switch: the same name, the same shape, off by default
# ---------------------------------------------------------------------------


def test_the_switch_is_named_after_the_two_that_came_before_it():
    from guardkit.orchestrator import boot_smoke_gate, zero_test_gate

    assert BLOCKING_ENV_VAR == "GUARDKIT_ARCH_CONFORMANCE_BLOCKING"
    assert zero_test_gate.BLOCKING_ENV_VAR == "GUARDKIT_ZERO_TEST_BLOCKING"
    assert boot_smoke_gate.BLOCKING_ENV_VAR == "GUARDKIT_BOOT_SMOKE_BLOCKING"
    # The same words mean yes for all three, so an operator learns one thing once.
    assert arch_conformance._TRUTHY == zero_test_gate._TRUTHY
    assert arch_conformance._TRUTHY == boot_smoke_gate._TRUTHY


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " on "])
def test_the_switch_is_on_for_the_words_the_other_gates_accept(value):
    assert blocking_requested({BLOCKING_ENV_VAR: value}) is True


@pytest.mark.parametrize("env", [{}, {BLOCKING_ENV_VAR: ""},
                                 {BLOCKING_ENV_VAR: "0"},
                                 {BLOCKING_ENV_VAR: "please"}])
def test_the_switch_is_off_unless_it_is_clearly_set(env):
    assert blocking_requested(env) is False


def test_the_switch_is_off_when_nothing_sets_it(monkeypatch):
    monkeypatch.delenv(BLOCKING_ENV_VAR, raising=False)
    assert blocking_requested() is False


# ---------------------------------------------------------------------------
# 2. Working out the check to add
# ---------------------------------------------------------------------------


def test_no_check_is_added_when_the_switch_is_off(repo):
    root, _sha = repo({"src/search/router.py": FILE_WITH_A_BREAK})
    assert build_arch_conformance_rule(root, TASK_ID, env={}) is None


def test_no_check_is_added_when_the_repository_has_no_rules_file(repo):
    root, _sha = repo({"src/search/router.py": FILE_WITH_A_BREAK}, rules=None)
    rule = build_arch_conformance_rule(
        root, TASK_ID, env={BLOCKING_ENV_VAR: "1"})
    assert rule is None


def test_the_check_names_the_commit_the_task_starts_from(repo):
    root, sha = repo({"src/search/router.py": CLEAN_FILE})
    rule = build_arch_conformance_rule(
        root, TASK_ID, env={BLOCKING_ENV_VAR: "1"})

    assert rule is not None
    assert rule["id"] == RULE_ID
    assert rule["type"] == "assert_command"
    assert rule["expected_exit"] == 0
    assert "-m guardkit.orchestrator.arch_conformance" in rule["command"]
    assert f"--since {sha}" in rule["command"]
    # It is a shape the machinery that runs it already accepts.
    AssertCommandRule.model_validate(rule)


def test_no_check_is_added_when_the_starting_commit_cannot_be_read(tmp_path, caplog):
    root = tmp_path / "not-a-git-repo"
    write(root, "src/search/router.py", FILE_WITH_A_BREAK)
    write(root, "docs/architecture-rules.yaml", RULES)

    with caplog.at_level(logging.WARNING):
        rule = build_arch_conformance_rule(
            root, TASK_ID, env={BLOCKING_ENV_VAR: "1"})

    assert rule is None
    assert "could not be read" in caplog.text


def test_working_out_the_check_never_raises(repo, caplog):
    root, _sha = repo({"src/search/router.py": CLEAN_FILE})
    with patch.object(arch_conformance, "starting_commit",
                      side_effect=RuntimeError("boom")):
        with caplog.at_level(logging.WARNING):
            rule = build_arch_conformance_rule(
                root, TASK_ID, env={BLOCKING_ENV_VAR: "1"})
    assert rule is None
    assert "RuntimeError" in caplog.text


# ---------------------------------------------------------------------------
# 3. The scope: only the files this task changed
# ---------------------------------------------------------------------------


def test_a_place_the_task_wrote_is_reported(repo):
    root, sha = repo({"src/search/router.py": CLEAN_FILE})
    write(root, "src/search/router.py", FILE_WITH_A_BREAK)

    code, text = check_changed_files(root, sha)

    assert code == 1
    assert "R-NO-URLLIB" in text
    assert "src/search/router.py:1" in text
    # The sentence from the record, word for word, and the document it came from.
    assert "Outbound HTTP goes through the shared client, never urllib." in text
    assert "docs/architecture/adr-009.md" in text


def test_a_place_the_task_never_touched_passes(repo):
    """The whole of the design. The pilot repository's main carries known places."""
    root, sha = repo({
        "src/search/router.py": FILE_WITH_A_BREAK,   # already here, and not this task's
        "src/stats/router.py": CLEAN_FILE,
    })
    write(root, "src/stats/router.py", CLEAN_FILE.replace("get(url)", "get(url)  # tidy"))

    code, text = check_changed_files(root, sha)

    assert code == 0
    assert "src/search/router.py" not in text

    # And the checker did see it -- it is narrowing that keeps it off this task's
    # plate, not blindness. A checker that had missed it would pass for the wrong
    # reason, and this test would then be proving nothing.
    from guardkit.conformance import run
    whole_tree = run(root)
    assert [s.where for s in whole_tree.all_findings] == ["src/search/router.py:1"]


def test_a_brand_new_file_git_has_not_been_told_about_is_still_read(repo):
    root, sha = repo({"src/search/router.py": CLEAN_FILE})
    write(root, "src/search/fetcher.py", FILE_WITH_A_BREAK)   # never git-added

    assert "src/search/fetcher.py" in files_changed_since(root, sha)

    code, text = check_changed_files(root, sha)
    assert code == 1
    assert "src/search/fetcher.py:1" in text


def test_a_task_that_has_changed_nothing_yet_passes(repo):
    root, sha = repo({"src/search/router.py": FILE_WITH_A_BREAK})
    code, text = check_changed_files(root, sha)
    assert code == 0
    assert "changed no files yet" in text


def test_the_starting_commit_is_the_worktrees_own_head(repo):
    root, sha = repo({"src/search/router.py": CLEAN_FILE})
    assert starting_commit(root) == sha


# ---------------------------------------------------------------------------
# 4. A check that cannot run is never a wall
# ---------------------------------------------------------------------------


def test_no_rules_file_means_nothing_was_checked_and_nothing_is_stopped(repo):
    root, sha = repo({"src/search/router.py": CLEAN_FILE}, rules=None)
    write(root, "src/search/router.py", FILE_WITH_A_BREAK)

    code, text = check_changed_files(root, sha)

    assert code == 0
    assert "not the same as clean" in text


def test_a_checker_that_raises_does_not_stop_anything(repo):
    root, sha = repo({"src/search/router.py": CLEAN_FILE})
    write(root, "src/search/router.py", FILE_WITH_A_BREAK)

    with patch("guardkit.conformance.run", side_effect=RuntimeError("boom")):
        code, text = check_changed_files(root, sha)

    assert code == 0
    assert "RuntimeError" in text
    assert "not the same as clean" in text


def test_git_that_cannot_answer_does_not_stop_anything(repo):
    root, _sha = repo({"src/search/router.py": CLEAN_FILE})
    code, text = check_changed_files(root, "not-a-commit")
    assert code == 0
    assert "not the same as clean" in text


def test_a_rule_the_checker_cannot_run_is_said_out_loud_but_stops_nothing(repo):
    unreadable = RULES.replace("kind: forbidden-imports", "kind: telepathy")
    root, sha = repo({"src/search/router.py": CLEAN_FILE}, rules=unreadable)
    write(root, "src/search/router.py", FILE_WITH_A_BREAK)

    code, text = check_changed_files(root, sha)

    assert code == 0
    assert "could not be checked at all" in text
    assert "R-NO-URLLIB" in text


def test_the_command_prints_what_it_found_and_returns_the_code(repo, capsys):
    root, sha = repo({"src/search/router.py": CLEAN_FILE})
    write(root, "src/search/router.py", FILE_WITH_A_BREAK)

    code = main(["--repo", str(root), "--since", sha])

    assert code == 1
    assert "src/search/router.py:1" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# 5. End to end, through the machinery that already exists
# ---------------------------------------------------------------------------


def _snapshot(root: Path, *, frontmatter: dict | None = None):
    """Freeze this task's checks before turn 1, as the build loop does."""
    task_data = {"frontmatter": frontmatter or {}}
    with patch("guardkit.tasks.task_loader.TaskLoader.load_task",
               return_value=task_data):
        return snapshot_task_conformance(
            task_id=TASK_ID, worktree_path=root, repo_root=root)


def _guard(decision: dict, leg, tmp_path: Path) -> dict:
    inv = AgentInvoker.__new__(AgentInvoker)
    coach_path = tmp_path / "coach_turn_1.json"
    coach_path.write_text(json.dumps(decision))
    inv._apply_spec_conformance_guard(
        decision=decision,
        evidence_bundle=CoachEvidenceBundle(honesty=None, spec_conformance=leg),
        task_id=TASK_ID,
        turn=1,
        coach_output_path=coach_path,
        acceptance_criteria=None,
    )
    return decision


def test_with_the_switch_off_nothing_is_frozen_and_no_verdict_changes(repo, monkeypatch,
                                                                     tmp_path):
    monkeypatch.delenv(BLOCKING_ENV_VAR, raising=False)
    root, _sha = repo({"src/search/router.py": CLEAN_FILE})
    write(root, "src/search/router.py", FILE_WITH_A_BREAK)

    assert _snapshot(root) is None
    assert not snapshot_paths(TASK_ID, root)["block"].exists()

    decision = {"decision": "approve", "issues": []}
    assert _guard(decision, None, tmp_path)["decision"] == "approve"


def test_with_the_switch_on_a_place_the_task_wrote_comes_back_as_one_fix_this_issue(
        repo, monkeypatch, tmp_path):
    monkeypatch.setenv(BLOCKING_ENV_VAR, "1")
    root, _sha = repo({"src/search/router.py": CLEAN_FILE})

    snapshot_dir = _snapshot(root)
    assert snapshot_dir is not None
    block, _authority = load_snapshot(snapshot_dir)
    assert [r.id for r in block.rules] == [RULE_ID]

    # The code generator now writes the break, after the check was frozen.
    write(root, "src/search/router.py", FILE_WITH_A_BREAK)

    leg = evaluate_from_snapshot(snapshot_dir, root, task_id=TASK_ID)
    assert leg["status"] == "failed"
    assert [f["rule_id"] for f in leg["failures"]] == [RULE_ID]

    decision = {"decision": "approve", "issues": []}
    _guard(decision, leg, tmp_path)

    assert decision["decision"] == "feedback"
    must_fix = [i for i in decision["issues"] if i["severity"] == "must_fix"]
    assert len(must_fix) == 1
    description = must_fix[0]["description"]
    assert RULE_ID in description
    assert "R-NO-URLLIB" in description
    assert "src/search/router.py:1" in description
    assert "Outbound HTTP goes through the shared client, never urllib." in description
    # The checker's own words, unchanged: no score, no severity of its own, no telling-off.
    assert "score" not in description.lower()


def test_with_the_switch_on_a_place_the_task_never_touched_leaves_the_verdict_alone(
        repo, monkeypatch, tmp_path):
    monkeypatch.setenv(BLOCKING_ENV_VAR, "1")
    root, _sha = repo({
        "src/search/router.py": FILE_WITH_A_BREAK,   # already here before the task
        "src/stats/router.py": CLEAN_FILE,
    })

    snapshot_dir = _snapshot(root)
    assert snapshot_dir is not None

    write(root, "src/stats/router.py", CLEAN_FILE + "\n# the task's own tidy-up\n")

    leg = evaluate_from_snapshot(snapshot_dir, root, task_id=TASK_ID)
    assert leg["status"] == "passed", leg

    decision = {"decision": "approve", "issues": []}
    assert _guard(decision, leg, tmp_path)["decision"] == "approve"
    assert decision["issues"] == []


def test_with_the_switch_on_a_repository_with_no_rules_file_freezes_nothing(
        repo, monkeypatch):
    monkeypatch.setenv(BLOCKING_ENV_VAR, "1")
    root, _sha = repo({"src/search/router.py": FILE_WITH_A_BREAK}, rules=None)

    assert _snapshot(root) is None
    assert not snapshot_paths(TASK_ID, root)["block"].exists()


def test_a_tasks_own_declared_checks_are_kept_and_the_architecture_one_is_added(
        repo, monkeypatch):
    monkeypatch.setenv(BLOCKING_ENV_VAR, "1")
    root, _sha = repo({"src/search/router.py": CLEAN_FILE})

    frontmatter = {
        "conformance": {
            "rules": [
                {"id": "the-task-said-so", "type": "assert_command",
                 "command": "true", "expected_exit": 0},
            ]
        }
    }
    snapshot_dir = _snapshot(root, frontmatter=frontmatter)
    assert snapshot_dir is not None
    block, _authority = load_snapshot(snapshot_dir)
    assert [r.id for r in block.rules] == ["the-task-said-so", RULE_ID]


def test_what_matters_survives_the_two_thousand_character_tail(repo):
    """The code generator sees only the end of this, so the end must carry the point.

    The build loop hands a failing command's last 2000 characters to the code
    generator and drops the rest. A run with many places listed therefore loses its
    opening lines, so the sentence telling the reader what these words are and what to
    do about them is written at the END, where it cannot be cut.
    """
    from guardkit.orchestrator.quality_gates.spec_conformance import (
        _OUTPUT_TAIL_CHARS,
    )

    files = {f"src/feature{n}/router.py": CLEAN_FILE for n in range(12)}
    root, sha = repo(files)
    for n in range(12):
        write(root, f"src/feature{n}/router.py", FILE_WITH_A_BREAK)

    code, text = check_changed_files(root, sha)
    tail = text[-_OUTPUT_TAIL_CHARS:]

    assert code == 1
    assert len(text) > _OUTPUT_TAIL_CHARS, "this fixture is meant to overflow the tail"
    assert "Fix the code, or say so if the rule is the thing that is wrong." in tail
    assert "12 place(s) above" in tail
    # And a whole finding still reaches the reader, rule and record sentence intact.
    assert "R-NO-URLLIB" in tail
    assert "Outbound HTTP goes through the shared client, never urllib." in tail
