"""What the checker does around the edges: what it refuses, and what it says out loud.

The tests that matter most here are the two about a rule the engine cannot run. Silent
success — a check that runs, matches nothing because it was never able to look, and
reports clean — is this estate's known failure class, and these are the tests that keep
this program out of it.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from guardkit.conformance.cli import main
from guardkit.conformance.engine import files_touched_by, run
from guardkit.conformance.report import to_json, to_text
from tests.conformance.conftest import outcome

MINIMAL_FILES = {"src/users/router.py": "router = 1\n"}

CLEAN_RULES = """
format_version: "1.0"
layout:
  source_root: src
rules:
  - id: R-ROUTER-REQUIRED
    rule: Every feature module contains a router.py.
    source_document: docs/architecture/adr-001.md
    source_sentence: "router.py — required in every feature"
    signals:
      kind: file-layout
      scope: feature_modules
      required_files: [router.py]
"""

UNKNOWN_KIND_RULES = """
format_version: "1.0"
layout:
  source_root: src
rules:
  - id: R-JUDGEMENT
    rule: Business logic lives in a service file, not in router.py.
    source_document: docs/architecture/00-system-overview.md
    source_sentence: "Service Layer (service.py) orchestrates business logic."
    signals:
      kind: is-this-business-logic
      scope: feature_modules
"""


# --------------------------------------------------------------------------
# A rule the engine cannot run is never reported as clean
# --------------------------------------------------------------------------


def test_a_rule_naming_a_check_this_program_does_not_have_says_so_loudly(check):
    report = check(MINIMAL_FILES, UNKNOWN_KIND_RULES)
    rule = outcome(report, "R-JUDGEMENT")
    assert rule.status == "unsupported"
    assert "is-this-business-logic" in rule.unsupported_reason
    assert "Nothing was checked for it" in rule.unsupported_reason
    text = to_text(report)
    assert "R-JUDGEMENT  —  UNSUPPORTED" in text
    assert "these are NOT clean" in text


def test_an_unsupported_rule_makes_the_exit_code_two_not_zero(check):
    report = check(MINIMAL_FILES, UNKNOWN_KIND_RULES)
    assert report.all_findings == []
    assert report.exit_code() == 2, "exit 0 here would report success for work never done"


def test_a_rule_missing_the_names_its_own_check_needs_is_unsupported_not_clean(check):
    rules = """
    format_version: "1.0"
    layout:
      source_root: src
    rules:
      - id: R-HALF-WRITTEN
        rule: Route handlers are declared with async def.
        source_document: docs/architecture/adr-002.md
        source_sentence: "Synchronous blocking calls are forbidden in route handlers."
        signals:
          kind: handler-shape
          require: AsyncFunctionDef
    """
    report = check(MINIMAL_FILES, rules)
    rule = outcome(report, "R-HALF-WRITTEN")
    assert rule.status == "unsupported"
    assert "no HTTP method names" in rule.unsupported_reason


def test_a_requirement_written_in_words_the_engine_cannot_test_is_unsupported(check):
    rules = """
    format_version: "1.0"
    layout:
      source_root: src
    rules:
      - id: R-VAGUE
        rule: The configuration should be sensible.
        source_document: docs/architecture/adr-005.md
        source_sentence: "Configuration is checked in."
        signals:
          kind: config-file-fact
          file: pyproject.toml
          require:
            - "it should feel right"
    """
    report = check({**MINIMAL_FILES, "pyproject.toml": "[tool.ruff]\n"}, rules)
    rule = outcome(report, "R-VAGUE")
    assert rule.status == "unsupported"
    assert "it should feel right" in rule.unsupported_reason


# --------------------------------------------------------------------------
# Exit codes
# --------------------------------------------------------------------------


def test_a_repository_with_nothing_to_report_exits_zero(check):
    report = check(MINIMAL_FILES, CLEAN_RULES)
    assert report.exit_code() == 0
    assert outcome(report, "R-ROUTER-REQUIRED").status == "clean"


def test_a_repository_with_something_to_report_exits_one(check):
    report = check({"src/stats/__init__.py": ""}, CLEAN_RULES)
    assert report.exit_code() == 1
    assert len(report.all_findings) == 1


def test_a_repository_with_no_rules_file_exits_two_and_is_not_called_clean(tmp_path):
    (tmp_path / "src").mkdir()
    report = run(tmp_path)
    assert report.exit_code() == 2
    assert report.ran is False
    assert "not the same as clean" in report.could_not_run
    assert "COULD NOT RUN" in to_text(report)


def test_a_rules_file_that_will_not_read_exits_two(make_repo):
    repo = make_repo(MINIMAL_FILES, "rules: [ this is not\n  valid: yaml: at all\n")
    report = run(repo)
    assert report.exit_code() == 2
    assert "could not be read as YAML" in report.could_not_run


def test_a_rule_with_no_id_is_refused_rather_than_half_read(make_repo):
    repo = make_repo(MINIMAL_FILES, "rules:\n  - rule: something\n")
    report = run(repo)
    assert report.exit_code() == 2
    assert "has no id" in report.could_not_run


# --------------------------------------------------------------------------
# Rules belong to the repository they were written for
# --------------------------------------------------------------------------


def test_rules_written_for_another_repository_are_not_run_by_default(make_repo):
    repo = make_repo(MINIMAL_FILES, "repo: some_other_repo\n" + CLEAN_RULES)
    report = run(repo)
    assert report.exit_code() == 2
    assert "written for the repository 'some_other_repo'" in report.could_not_run


def test_rules_written_for_another_repository_run_when_asked_explicitly(make_repo):
    repo = make_repo(MINIMAL_FILES, "repo: some_other_repo\n" + CLEAN_RULES)
    report = run(repo, allow_foreign_rules=True)
    assert report.ran is True
    assert "NOT WRITTEN FOR THIS REPOSITORY" in " ".join(report.notes)


# --------------------------------------------------------------------------
# A file the checker could not read is named, never dropped
# --------------------------------------------------------------------------


def test_a_file_that_will_not_parse_is_named_in_the_report(check):
    report = check({"src/users/router.py": "def broken(:\n", "src/users/ok.py": "x = 1\n"},
                   CLEAN_RULES)
    assert [f["path"] for f in report.files_unparsed] == ["src/users/router.py"]
    assert report.files_scanned == 1
    assert "DID NOT PARSE" in to_text(report)


def test_bytecode_directories_are_not_mistaken_for_a_feature_module(check):
    """Any machine that has run the tests has a src/__pycache__ on disk."""
    report = check({"src/users/router.py": "router = 1\n",
                    "src/__pycache__/router.cpython-312.pyc": "not python"},
                   CLEAN_RULES)
    assert report.exit_code() == 0
    assert report.all_findings == []


# --------------------------------------------------------------------------
# What the two renderings say, and what they must never say
# --------------------------------------------------------------------------


def test_the_json_report_carries_the_rule_its_source_and_the_evidence(check):
    report = check({"src/stats/__init__.py": ""}, CLEAN_RULES)
    payload = to_json(report)
    finding = payload["findings"][0]
    assert finding["rule_id"] == "R-ROUTER-REQUIRED"
    assert finding["rule_source"]["document"] == "docs/architecture/adr-001.md"
    assert finding["rule_source"]["sentence"].startswith("router.py")
    assert finding["observed_at"] == "src/stats"
    assert "no file named router.py" in finding["how_observed"]
    assert payload["exit_code"] == 1


FORBIDDEN_WORDS = ("score", "confidence", "severity", "aligned", "misaligned",
                   "violation", "pass", "fail")


def test_nothing_the_checker_says_about_a_finding_scores_it_or_judges_it(check):
    """The findings themselves carry no word that concludes.

    The two renderings each open and close with a sentence saying what the checker is
    not — those sentences use the words on purpose. Everything the checker says about
    an actual place in the code is checked here, and it may not.
    """
    report = check({"src/stats/__init__.py": ""}, CLEAN_RULES)
    payload = to_json(report)
    for finding in payload["findings"]:
        flat = json.dumps(finding).lower()
        for word in FORBIDDEN_WORDS:
            assert word not in flat, f"a finding must not use the word {word!r}"
    for rule in payload["rules"]:
        assert rule["status"] in ("clean", "finding", "unsupported")
    for line in to_text(report).splitlines():
        stripped = line.strip().lower()
        if not stripped.startswith(("observed:", "how observed:", "also here:", "says:")):
            continue
        for word in FORBIDDEN_WORDS:
            assert word not in stripped, f"the text must not use the word {word!r}: {line}"


def test_every_rule_reports_what_it_looked_at_so_a_clean_line_can_be_believed(check):
    report = check(MINIMAL_FILES, CLEAN_RULES)
    assert outcome(report, "R-ROUTER-REQUIRED").examined == {"modules checked": 1}
    assert "looked at — modules checked: 1" in to_text(report)


# --------------------------------------------------------------------------
# The command line
# --------------------------------------------------------------------------


def test_the_command_prints_text_and_returns_the_exit_code(make_repo, capsys):
    repo = make_repo({"src/stats/__init__.py": ""}, CLEAN_RULES)
    code = main(["--repo", str(repo)])
    assert code == 1
    assert "Architecture rules check" in capsys.readouterr().out


def test_the_command_prints_json_and_can_write_it_to_a_file(make_repo, tmp_path, capsys):
    repo = make_repo(MINIMAL_FILES, CLEAN_RULES)
    out = tmp_path / "receipts" / "conformance.json"
    code = main(["--repo", str(repo), "--json", "--json-out", str(out)])
    assert code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["checker"] == "guardkit.conformance"
    assert json.loads(out.read_text())["exit_code"] == 0


def test_the_command_can_be_pointed_at_a_rules_file_somewhere_else(make_repo, tmp_path, capsys):
    repo = make_repo(MINIMAL_FILES, "rules: []\n")
    elsewhere = tmp_path / "elsewhere.yaml"
    elsewhere.write_text(CLEAN_RULES)
    assert main(["--repo", str(repo), "--rules", str(elsewhere)]) == 0
    assert "elsewhere.yaml" in capsys.readouterr().out


# --------------------------------------------------------------------------
# Reporting on one change rather than the whole repository
# --------------------------------------------------------------------------

TWO_FEATURES_MISSING_ROUTERS = {"src/stats/__init__.py": "", "src/uptime/__init__.py": ""}


def test_narrowing_to_a_change_lists_only_that_change_and_counts_the_rest(make_repo):
    repo = make_repo(TWO_FEATURES_MISSING_ROUTERS, CLEAN_RULES)
    report = run(repo, diff_scope=["src/stats"])
    assert [s.where for s in report.reported_findings] == ["src/stats"]
    assert len(report.all_findings) == 2, "the other one is still found, just not listed"
    assert report.exit_code() == 1
    text = to_text(report)
    assert "1 further finding(s) sit elsewhere in this repository" in text


def test_a_change_that_touches_nothing_the_rules_are_about_exits_zero(make_repo):
    repo = make_repo(TWO_FEATURES_MISSING_ROUTERS, CLEAN_RULES)
    report = run(repo, diff_scope=["README.md"])
    assert report.reported_findings == []
    assert report.exit_code() == 0
    assert to_json(report)["findings_elsewhere_in_the_repository"] == 2


def test_the_whole_repository_counts_stay_in_the_report_when_it_is_narrowed(make_repo):
    repo = make_repo(TWO_FEATURES_MISSING_ROUTERS, CLEAN_RULES)
    payload = to_json(run(repo, diff_scope=["src/stats"]))
    rule = payload["rules"][0]
    assert rule["findings_in_the_whole_repository"] == 2
    assert payload["findings"][0]["in_this_change"] is True
    assert payload["narrowed_to_the_files_this_change_touched"] == ["src/stats"]


def test_a_range_of_commits_is_turned_into_the_files_it_touched(tmp_path):
    """The one process this program starts: git, read-only, only when asked."""
    if shutil.which("git") is None:                      # pragma: no cover
        pytest.skip("git is not on this machine")
    repo = tmp_path / "repo"
    (repo / "src" / "users").mkdir(parents=True)
    (repo / "src" / "users" / "router.py").write_text("router = 1\n")

    def git_run(*args: str) -> None:
        subprocess.run(["git", "-C", str(repo), *args], check=True,
                       capture_output=True, text=True)

    git_run("init", "-q")
    git_run("config", "user.email", "test@example.com")
    git_run("config", "user.name", "Test")
    git_run("add", "-A")
    git_run("commit", "-qm", "first")
    (repo / "src" / "users" / "crud.py").write_text("x = 1\n")
    git_run("add", "-A")
    git_run("commit", "-qm", "second")

    assert files_touched_by(repo, "HEAD~1..HEAD") == ["src/users/crud.py"]


def test_a_range_git_cannot_read_is_could_not_run_rather_than_clean(make_repo):
    repo = make_repo(MINIMAL_FILES, CLEAN_RULES)
    report = run(repo, diff_range="no-such-ref..HEAD")
    assert report.exit_code() == 2
    assert "could not read the range" in report.could_not_run
