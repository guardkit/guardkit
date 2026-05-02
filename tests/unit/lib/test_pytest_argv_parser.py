"""Unit tests for ``guardkit.lib.pytest_argv``.

Pins the parser/formatter contract relied on by every smoke-gate path
defense layer:

- ``parse_positional_paths`` — TASK-FPSG-002 (validator), TASK-FPSG-004
  (``feature validate`` wrapper), TASK-FPSG-005 (load-time pre-flight).
- ``format_smoke_gate_path_error`` — single source of truth for the
  user-facing error wording so all three callsites emit the same message
  for the same defect.

Coverage Target: >=90% (pure-function module, no side effects).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guardkit.lib.pytest_argv import (
    format_smoke_gate_path_error,
    parse_positional_paths,
)


# ---------------------------------------------------------------------------
# parse_positional_paths
# ---------------------------------------------------------------------------


class TestParsePositionalPaths:
    """Exercises the AC-listed parser cases for TASK-FPSG-002."""

    def test_multi_line_block_scalar_with_set_e_prefix(self):
        """``set -e`` line is skipped; the pytest line's positionals win.

        Mirrors the canonical YAML smoke-gate shape:

            command: |
              set -e
              pytest tests/foo -x
        """
        command = "set -e\npytest tests/foo -x"
        assert parse_positional_paths(command) == ["tests/foo"]

    def test_flag_before_positional(self):
        """A flag ahead of the path must not eat the path.

        ``-x`` takes no value, so the next token is the positional.
        """
        assert parse_positional_paths("pytest -x tests/foo") == ["tests/foo"]

    def test_double_dash_separator_excludes_pytest_passthrough(self):
        """Tokens after ``--`` are pytest pass-through, not test paths.

        ``--junit-xml=out.xml`` should NOT be treated as a path the
        validator must resolve on disk — it is a flag pytest forwards
        to its own argv parser.
        """
        command = "pytest tests/foo -- --junit-xml=out.xml"
        assert parse_positional_paths(command) == ["tests/foo"]

    def test_multiple_positionals_with_value_taking_flag(self):
        """``-k EXPR`` must not consume the second positional path.

        Without the ``_FLAGS_WITH_SEPARATE_VALUE`` skip, ``"expr"`` would
        leak into the returned list and the validator would resolve it
        as a non-existent path.
        """
        command = 'pytest tests/foo tests/bar -k "expr"'
        assert parse_positional_paths(command) == ["tests/foo", "tests/bar"]

    def test_non_pytest_command_returns_empty_list(self):
        """``python3 .guardkit/smoke/foo.py`` is not pytest; skip silently.

        The validator branches on ``[]`` to mean "nothing to check"
        (vs "valid pytest command with zero paths"). Returning ``[]``
        here keeps the AC's escape hatch intact.
        """
        assert parse_positional_paths("python3 .guardkit/smoke/foo.py") == []

    # --- defensive branches ------------------------------------------------

    def test_empty_command_returns_empty_list(self):
        """Empty input must not crash."""
        assert parse_positional_paths("") == []
        assert parse_positional_paths("   \n  \n") == []

    def test_blank_lines_and_comments_are_skipped(self):
        """Lines that are blank or shell comments are not pytest lines.

        The parser keeps scanning until it finds the real pytest invocation.
        """
        command = "\n# leading comment\n\npytest tests/foo\n"
        assert parse_positional_paths(command) == ["tests/foo"]

    def test_python_dash_m_pytest_form(self):
        """``python -m pytest`` is the same invocation as ``pytest``.

        Treating the ``python`` form as non-pytest would let a stale
        path slip past load-time validation when the author used
        ``python -m pytest tests/cli`` instead of ``pytest tests/cli``.
        """
        assert parse_positional_paths("python -m pytest tests/foo") == ["tests/foo"]
        assert parse_positional_paths("python3 -m pytest tests/foo -x") == [
            "tests/foo"
        ]

    def test_path_to_pytest_binary(self):
        """``./venv/bin/pytest`` should be treated as ``pytest``.

        Smoke gates inside container/venv-style projects routinely
        invoke pytest via an absolute or relative path; missing this
        shape would let those projects silently bypass validation.
        """
        assert parse_positional_paths("./venv/bin/pytest tests/foo") == [
            "tests/foo"
        ]
        assert parse_positional_paths("/usr/local/bin/pytest tests/foo -x") == [
            "tests/foo"
        ]

    def test_no_positional_returns_empty(self):
        """``pytest -x`` with no paths returns ``[]``.

        Validator treats this as "nothing to check" and exits 0 — pytest
        will scan the rootdir for tests at runtime.
        """
        assert parse_positional_paths("pytest -x") == []

    def test_unbalanced_quotes_skipped_silently(self):
        """A line that ``shlex`` rejects must not propagate the error.

        Validator falls back to "no paths to check" rather than crash —
        the malformed command will be caught elsewhere (Pydantic /
        ``run_smoke_gate`` at execution time).
        """
        # No pytest line at all — the unbalanced line is the only one.
        assert parse_positional_paths('echo "unbalanced') == []

    def test_value_flag_with_equals_form_self_contained(self):
        """``--ignore=tests/foo`` consumes itself; no skip-next required.

        Confirms the ``"=" in tok`` branch — a long flag in
        ``--key=value`` form does NOT eat the next token.
        """
        command = "pytest --ignore=tests/skip tests/foo"
        assert parse_positional_paths(command) == ["tests/foo"]

    def test_node_id_with_double_colon_treated_as_positional(self):
        """``tests/foo.py::test_bar`` is a pytest node ID, valid positional.

        These DO need disk validation — the file portion must exist
        even if the validator does not resolve the ``::test_bar``
        portion. Returning the full string preserves that contract.
        """
        command = "pytest tests/foo.py::test_bar -x"
        assert parse_positional_paths(command) == ["tests/foo.py::test_bar"]

    def test_first_pytest_line_wins(self):
        """If multiple lines invoke pytest, the first one defines the argv.

        Smoke gates are conventionally a single pytest call; guarding
        against multi-line pytest blocks keeps the validator's behaviour
        predictable in the rare case an author scripted two runs.
        """
        command = "pytest tests/foo -x\npytest tests/bar -x"
        # Per current parser contract, only the first pytest invocation
        # is parsed for positionals.
        assert parse_positional_paths(command) == ["tests/foo"]


# ---------------------------------------------------------------------------
# format_smoke_gate_path_error
# ---------------------------------------------------------------------------


class TestFormatSmokeGatePathError:
    """Pin the canonical error wording shared across defense layers."""

    def test_single_missing_path_includes_path_repo_and_roots(self):
        """Single missing path renders all three required pieces.

        The message must let the agent fix the YAML in one edit:
        bad path, repo root (so worktree vs main is unambiguous), and
        the available roots to choose from.
        """
        msg = format_smoke_gate_path_error(
            ["tests/cli"],
            Path("/Users/foo/forge"),
            ["tests/forge", "tests/integration", "tests/unit"],
        )
        assert "tests/cli" in msg
        assert "/Users/foo/forge" in msg
        assert "tests/forge" in msg
        assert "tests/integration" in msg
        assert "tests/unit" in msg
        assert "Available test roots" in msg

    def test_multiple_missing_paths_each_listed(self):
        """All bad paths must appear so the agent fixes them in one pass."""
        msg = format_smoke_gate_path_error(
            ["tests/cli", "tests/missing_other"],
            Path("/Users/foo/forge"),
            ["tests/forge"],
        )
        assert "tests/cli" in msg
        assert "tests/missing_other" in msg

    def test_empty_available_roots_renders_explanatory_line(self):
        """Repos without ``tests/<name>`` subdirs still get a useful message.

        An empty roots list could otherwise produce a confusing
        "Available test roots: " line; the explanatory parenthetical
        tells the agent why the listing is empty.
        """
        msg = format_smoke_gate_path_error(
            ["tests/cli"],
            Path("/Users/foo/forge"),
            [],
        )
        assert "Available test roots" in msg
        # No trailing colon-and-empty — there must be an explanation.
        assert "Available test roots:\n" not in msg
        assert "Available test roots: \n" not in msg

    def test_message_is_stable_across_callers(self):
        """Two callers with the same input must get byte-identical output.

        This is the pin that lets ``--validate-smoke-gates``,
        ``feature validate``, and ``_parse_feature`` pre-flight all
        emit the same wording — agents see one error, not three.
        """
        a = format_smoke_gate_path_error(
            ["tests/cli"], Path("/repo"), ["tests/foo"]
        )
        b = format_smoke_gate_path_error(
            ["tests/cli"], Path("/repo"), ["tests/foo"]
        )
        assert a == b
