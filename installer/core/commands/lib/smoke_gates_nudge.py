"""Interim R3 ergonomics: nudge users when a generated feature YAML has
multiple waves but no top-level ``smoke_gates:`` key.

Without smoke gates configured, the feature-level smoke oracle (see
TASK-SMK-F703A) will not fire between waves during autobuild, so composition
failures like the PEX-014..020 "13/13 green + e2e broken" pattern go
undetected. Authors with multi-wave features are one edit away from activating
R3 — this helper returns a notice string the caller can print before the
final ``/feature-plan`` summary telling them so.

Twin to ``bdd_oracle_nudge`` (TASK-FP-NDG1): same shape, same pure-read
contract, same suppression hook. Single-wave features intentionally do not
trigger the nudge — there is nothing to gate between — which matches the
AutoBuild smoke-gate model ("fires between waves, not tasks").

When the caller supplies ``repo_root``, the notice is grounded in the target
repo's actual ``tests/`` subdirectories (TASK-FPSG-003): the example pytest
command uses real paths from the repo, and a "Available test roots" preamble
lists what the agent has to choose from. This stops downstream agents from
inventing paths like ``tests/cli/`` that don't exist in the target.

See installer/core/commands/feature-plan.md § "Smoke gates" and the parent
review TASK-REV-4D190.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional


_BAR = "━" * 39

# Directory names that are never test roots even when present under tests/.
_TEST_ROOT_SKIP_NAMES = frozenset({"__pycache__", ".pytest_cache", "node_modules"})

# Maximum number of test roots to surface in the notice. Beyond this we
# truncate with "…" so the banner stays readable on standard terminals.
_MAX_TEST_ROOTS_IN_BANNER = 12


def discover_test_roots(repo_root: Path) -> List[str]:
    """Return sorted ``tests/<name>`` paths for the target repo's test tree.

    Walks ``<repo_root>/tests/`` one level deep and returns each immediate
    subdirectory as a ``tests/<name>`` string suitable for direct use in a
    ``pytest`` command. Skips cache/build directories and any name beginning
    with ``.``.

    The returned strings are paths relative to ``repo_root`` (always rooted
    at ``tests/``), so the caller can drop them into a smoke gate command
    without further manipulation.

    Args:
        repo_root: Filesystem root of the target repo (e.g. the value of
            ``args.base_path`` in ``generate_feature_yaml``).

    Returns:
        Sorted list of ``tests/<name>`` paths. Empty list when the
        ``tests/`` directory does not exist, is not a directory, or contains
        no eligible subdirectories. Any ``OSError`` while iterating is
        swallowed and yields ``[]`` — this helper must never be the reason a
        ``/feature-plan`` run surfaces a traceback.
    """
    tests_dir = repo_root / "tests"
    if not tests_dir.is_dir():
        return []

    try:
        roots: List[str] = []
        for child in tests_dir.iterdir():
            if not child.is_dir():
                continue
            name = child.name
            if name.startswith("."):
                continue
            if name in _TEST_ROOT_SKIP_NAMES:
                continue
            roots.append(f"tests/{name}")
        return sorted(roots)
    except OSError:
        return []


def _format_test_roots_listing(test_roots: List[str]) -> str:
    """Format discovered roots as an indented multi-column listing.

    Caps at ``_MAX_TEST_ROOTS_IN_BANNER`` entries and appends a "… (N more)"
    line when truncated.
    """
    truncated = test_roots[:_MAX_TEST_ROOTS_IN_BANNER]
    overflow = len(test_roots) - len(truncated)

    if not truncated:
        return ""

    column_width = max(len(r) for r in truncated) + 4
    cols_per_row = 3

    rows = []
    for i in range(0, len(truncated), cols_per_row):
        chunk = truncated[i : i + cols_per_row]
        row = "    " + "".join(r.ljust(column_width) for r in chunk).rstrip()
        rows.append(row)

    if overflow > 0:
        rows.append(f"    … ({overflow} more)")

    return "\n".join(rows)


def _render_notice(wave_count: int, test_roots: List[str]) -> str:
    """Build the full notice text, optionally grounded in discovered roots.

    When ``test_roots`` is non-empty, the notice includes a
    "Available test roots in this repo" preamble and the example block uses
    real discovered paths in the ``pytest`` command. Otherwise it falls back
    to the historical generic ``pytest tests/smoke -x`` placeholder with a
    note explaining that no ``tests/`` directory was discovered.

    The example block (between the "Minimal example:" and "See ..." anchors)
    is always a valid YAML mapping that round-trips through
    ``SmokeGates.model_validate`` — see
    ``test_notice_example_validates_against_smoke_gates_schema``.
    """
    if test_roots:
        sample_paths = " ".join(test_roots[:2])
        example_command = (
            f"pytest {sample_paths} -x      # uses discovered roots"
        )
        roots_block = (
            "\n"
            "Available test roots in this repo "
            "(use these, not invented paths):\n"
            f"{_format_test_roots_listing(test_roots)}\n"
        )
        no_tests_note = ""
    else:
        example_command = "pytest tests/smoke -x"
        roots_block = ""
        no_tests_note = (
            "\n"
            "Note: no `tests/` directory discovered in this repo — replace "
            "the path below\n"
            "with the directory that holds your test suite.\n"
        )

    return (
        f"{_BAR}\n"
        "ℹ️  Feature-level smoke gates (R3) not configured\n"
        f"{_BAR}\n"
        f"This feature has {wave_count} waves but no smoke_gates: key in "
        "the generated YAML.\n"
        "Between-wave smoke checks will not fire during autobuild.\n"
        "\n"
        "This is the gate that catches composition failures (e.g., the "
        "PEX-014..020\n"
        "\"13/13 green + e2e broken\" pattern) that per-task Coach approval "
        "misses.\n"
        f"{roots_block}"
        f"{no_tests_note}"
        "\n"
        "To activate: add a smoke_gates: block to the feature YAML before "
        "running\n"
        "/feature-build. Minimal example:\n"
        "    # smoke_gates is ONE object per feature (not a dict-of-waves).\n"
        "    # after_wave selects which wave(s) the single command fires "
        "after.\n"
        "    smoke_gates:\n"
        "      after_wave: [2, 3]          # int | list[int] | \"all\"\n"
        "      command: |                  # single shell command "
        "(multi-line OK)\n"
        "        set -e\n"
        f"        {example_command}\n"
        "      expected_exit: 0            # optional, default 0\n"
        "      timeout: 120                # optional, default 120s, "
        "bounds [1, 600]\n"
        "\n"
        "See installer/core/commands/feature-plan.md § \"Smoke gates\".\n"
        f"{_BAR}"
    )


def check_smoke_gates_activation(
    feature_yaml_path: Path,
    quiet: bool = False,
    repo_root: Optional[Path] = None,
) -> Optional[str]:
    """Return a notice string iff the feature YAML should be nudged to
    configure feature-level smoke gates.

    Fires the notice only when:
    - the file at ``feature_yaml_path`` parses as a YAML mapping, AND
    - it declares ``>= 2`` waves under ``orchestration.parallel_groups``
      (single-wave features have nothing to gate between), AND
    - the top-level ``smoke_gates:`` key is absent.

    Partial configuration (``smoke_gates:`` present but empty or null)
    intentionally suppresses the nudge — the author has signalled
    awareness, which is enough. Any error reading or parsing the file
    silently suppresses the nudge; this helper must never be the reason
    ``/feature-plan`` surfaces a traceback.

    Args:
        feature_yaml_path: Path to the generated feature YAML, typically
            ``.guardkit/features/FEAT-XXXX.yaml``.
        quiet: When True, always return None. Used to honour
            ``--no-questions`` and equivalent quiet flags so CI runs do not
            emit the banner.
        repo_root: Optional filesystem root of the target repo. When
            supplied, the notice is grounded in the actual ``tests/``
            subdirectories discovered via :func:`discover_test_roots`. When
            ``None`` (or when discovery returns no roots), the notice falls
            back to a generic ``pytest tests/smoke -x`` placeholder with a
            note explaining the discovery shortfall.

    Returns:
        Notice text (str) when the nudge should fire, otherwise None.

    Branches (see AC):
    - ``smoke_gates:`` present (any value)                   -> None
    - fewer than 2 waves (single-wave feature)               -> None
    - ``>= 2`` waves and no ``smoke_gates:`` key             -> notice
    - YAML missing, unreadable, malformed, or not a mapping  -> None
    """
    if quiet:
        return None

    try:
        import yaml
    except ImportError:
        return None

    if not feature_yaml_path.is_file():
        return None

    try:
        text = feature_yaml_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return None

    if not isinstance(data, dict):
        return None

    if "smoke_gates" in data:
        return None

    orchestration = data.get("orchestration")
    if not isinstance(orchestration, dict):
        return None

    parallel_groups = orchestration.get("parallel_groups")
    if not isinstance(parallel_groups, list):
        return None

    wave_count = len(parallel_groups)
    if wave_count < 2:
        return None

    test_roots = discover_test_roots(repo_root) if repo_root is not None else []
    return _render_notice(wave_count, test_roots)
