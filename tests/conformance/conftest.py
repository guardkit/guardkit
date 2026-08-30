"""Building a small repository on disk, so every test states its own fixture.

Each test here writes the source files it is about and the rules file it is about,
then runs the checker over them. Nothing depends on another repository being present,
apart from the one integration test, which says so in its own name and skips when
api_test is not on this machine.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from guardkit.conformance.engine import run
from guardkit.conformance.model import Report


def write_tree(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")


@pytest.fixture
def make_repo(tmp_path: Path):
    """Write a source tree and a rules file, and return the repository path."""

    def _make(files: dict[str, str], rules: str, *, repo_name: str | None = None) -> Path:
        root = tmp_path / (repo_name or "fixture_repo")
        root.mkdir(parents=True, exist_ok=True)
        write_tree(root, files)
        rules_path = root / "docs" / "architecture-rules.yaml"
        rules_path.parent.mkdir(parents=True, exist_ok=True)
        rules_path.write_text(textwrap.dedent(rules).lstrip("\n"), encoding="utf-8")
        return root

    return _make


@pytest.fixture
def check(make_repo):
    """Write a fixture repository, run the checker over it, return the report."""

    def _check(files: dict[str, str], rules: str, **kwargs) -> Report:
        return run(make_repo(files, rules), **kwargs)

    return _check


def findings_at(report: Report, rule_id: str) -> set[str]:
    """Every place the named rule reported, as ``path:line`` strings."""
    return {s.where for r in report.rules if r.rule_id == rule_id for s in r.findings}


def outcome(report: Report, rule_id: str):
    for r in report.rules:
        if r.rule_id == rule_id:
            return r
    raise AssertionError(f"no rule {rule_id} in the report")


def every_site(report: Report, rule_id: str) -> set[str]:
    return {s.where for s in outcome(report, rule_id).sites}


def line_of(text: str, needle: str) -> int:
    """The 1-based line a marker sits on, once the fixture text is written out.

    Tests name the line they expect by quoting the code on it, so inserting a line
    into a fixture does not silently move an assertion onto the wrong statement.
    """
    body = textwrap.dedent(text).lstrip("\n").splitlines()
    for i, line in enumerate(body, 1):
        if needle in line:
            return i
    raise AssertionError(f"{needle!r} is not in this fixture")
