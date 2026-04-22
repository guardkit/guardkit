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

See installer/core/commands/feature-plan.md § "Smoke gates" and the parent
review TASK-REV-4D190.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


_NOTICE_TEMPLATE = (
    "━" * 39 + "\n"
    "ℹ️  Feature-level smoke gates (R3) not configured\n"
    + "━" * 39 + "\n"
    "This feature has {wave_count} waves but no smoke_gates: key in the "
    "generated YAML.\n"
    "Between-wave smoke checks will not fire during autobuild.\n"
    "\n"
    "This is the gate that catches composition failures (e.g., the "
    "PEX-014..020\n"
    "\"13/13 green + e2e broken\" pattern) that per-task Coach approval "
    "misses.\n"
    "\n"
    "To activate: add a smoke_gates: block to the feature YAML before "
    "running\n"
    "/feature-build. Minimal example:\n"
    "    smoke_gates:\n"
    "      after_wave_1:\n"
    "        - python -c \"import your_package\"\n"
    "      after_wave_2:\n"
    "        - pytest tests/smoke -x\n"
    "\n"
    "See installer/core/commands/feature-plan.md § \"Smoke gates\".\n"
    + "━" * 39
)


def check_smoke_gates_activation(
    feature_yaml_path: Path,
    quiet: bool = False,
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

    return _NOTICE_TEMPLATE.format(wave_count=wave_count)
