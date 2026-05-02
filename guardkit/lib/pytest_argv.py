"""Shared pytest-argv parser and message formatter for smoke-gate path
validation.

This module is the single source of truth for two helpers used across the
smoke-gate validation defense layers (TASK-FPSG-002 / L3b,
TASK-FPSG-004 / L3d, TASK-FPSG-005 / L4):

- ``parse_positional_paths(command)`` — extract positional pytest arguments
  (test paths / node IDs) from a smoke-gate ``command`` string. Returns
  ``[]`` when the command is not a pytest invocation, so callers can
  treat "non-pytest" as "nothing to validate".
- ``format_smoke_gate_path_error(missing, repo_root, available_roots)`` —
  format a path-existence error into a single canonical string used by
  ``generate-feature-yaml --validate-smoke-gates`` (TASK-FPSG-002), the
  ``feature validate`` wrapper (TASK-FPSG-004), and the
  ``FeatureLoader._parse_feature`` pre-flight check (TASK-FPSG-005).

Centralising the helpers means a YAML with ``tests/cli`` produces the
same error wording at every defense layer — agents see one message, not
three.
"""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import List

__all__ = [
    "parse_positional_paths",
    "format_smoke_gate_path_error",
]


# Pytest options that consume the *next* token as their value when not
# given in ``--key=value`` form. Tokens immediately following these flags
# must NOT be treated as positional paths.
_FLAGS_WITH_SEPARATE_VALUE = frozenset(
    {
        # short options
        "-k",  # keyword expression
        "-m",  # marker expression
        "-c",  # config file
        "-r",  # short test summary characters
        "-p",  # plugin
        "-o",  # config override
        "-W",  # warning filter
        # long options
        "--rootdir",
        "--ignore",
        "--ignore-glob",
        "--tb",
        "--junitxml",
        "--junit-xml",
        "--confcutdir",
        "--basetemp",
        "--maxfail",
        "--lfnf",
    }
)


def parse_positional_paths(command: str) -> List[str]:
    """Extract positional path arguments from a pytest smoke-gate command.

    A smoke-gate ``command`` may be a single line (``"pytest tests/foo -x"``)
    or a multi-line shell block scalar (``"set -e\\npytest tests/foo -x"``).
    This parser walks each line, finds the first one whose first non-shell
    token is ``pytest`` (or ends with ``/pytest``), and returns the
    positional arguments after it.

    Recognised pytest flags that consume their next token as a value
    (``-k``, ``-m``, ``--ignore``, etc.) are skipped along with that
    value, so ``pytest tests/foo -k "expr"`` returns ``["tests/foo"]``,
    not ``["tests/foo", "expr"]``. Tokens after a literal ``--``
    separator are ignored (they are pytest-passed args, not paths).

    Non-pytest commands (e.g. ``python3 .guardkit/smoke/foo.py``) return
    ``[]``. Callers should treat ``[]`` as "nothing to validate" rather
    than "valid pytest command with zero paths" — the smoke-gate
    validators only check pytest paths, not arbitrary script paths.

    Parameters
    ----------
    command : str
        Raw shell command from ``smoke_gates.command``.

    Returns
    -------
    list[str]
        Positional path/nodeid arguments after ``pytest``. Empty when
        the command does not invoke pytest, or when the command cannot
        be tokenized (malformed quoting).
    """
    for raw_line in command.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            tokens = shlex.split(line)
        except ValueError:
            # Unbalanced quotes — surface as "no paths" rather than
            # crash the validator. Pydantic / smoke_gates.py will catch
            # the syntactically broken command at execution time.
            continue
        if not tokens:
            continue

        pytest_idx = -1
        for i, tok in enumerate(tokens):
            if tok == "pytest" or tok.endswith("/pytest"):
                pytest_idx = i
                break
        if pytest_idx < 0:
            continue

        argv = tokens[pytest_idx + 1 :]
        positionals: List[str] = []
        i = 0
        while i < len(argv):
            tok = argv[i]
            if tok == "--":
                break
            if tok.startswith("-"):
                # Flag — consume value if needed.
                if "=" in tok:
                    i += 1
                    continue
                if tok in _FLAGS_WITH_SEPARATE_VALUE:
                    i += 2
                    continue
                i += 1
                continue
            positionals.append(tok)
            i += 1
        return positionals

    return []


def format_smoke_gate_path_error(
    missing: List[str],
    repo_root: Path,
    available_roots: List[str],
) -> str:
    """Format the canonical "smoke_gates.command path missing" error.

    Single source of truth for the message string surfaced by every
    defense layer that validates smoke-gate paths:

    - ``generate-feature-yaml --validate-smoke-gates`` (TASK-FPSG-002)
    - ``feature validate`` wrapper (TASK-FPSG-004)
    - ``FeatureLoader._parse_feature`` pre-flight (TASK-FPSG-005)

    Keeping the wording centralised means a stale ``tests/cli`` path
    produces byte-identical output regardless of which layer catches it.

    Parameters
    ----------
    missing : list[str]
        Paths from ``smoke_gates.command`` that did not exist under
        ``repo_root``.
    repo_root : Path
        Repository root the paths were resolved against. Surfaced to
        let agents disambiguate worktree vs. main-repo cases when the
        same path exists in one but not the other.
    available_roots : list[str]
        Sorted ``tests/<name>`` paths that *do* exist (typically from
        ``smoke_gates_nudge.discover_test_roots``). Empty list is fine.

    Returns
    -------
    str
        Multi-line error message ready to embed in a
        ``SchemaValidationError`` or print to stderr.
    """
    if len(missing) == 1:
        header = "smoke_gates.command references non-existent path:"
        body = f"  {missing[0]}   (repo root: {repo_root})"
    else:
        header = "smoke_gates.command references non-existent paths:"
        joined = "\n".join(f"  {p}" for p in missing)
        body = f"{joined}\n  (repo root: {repo_root})"

    if available_roots:
        roots_line = f"Available test roots: {', '.join(available_roots)}"
    else:
        roots_line = "Available test roots: (none — no tests/<name> subdirectories found)"

    return f"{header}\n{body}\n{roots_line}"
