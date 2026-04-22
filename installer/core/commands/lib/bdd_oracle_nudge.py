"""Interim R2 ergonomics: nudge users when a features/*.feature file exists
but no scenarios carry @task:<TASK-ID> tags.

Without task-scope tags the R2 BDD oracle (see TASK-BDD-E8954) will not fire
during autobuild, so users who have written a feature file are one edit away
from activating R2 but may not realise it. This helper inspects the feature
files and returns a notice string the caller can print before the final
`/feature-plan` summary.

This is a pure-read helper. It does not rewrite `.feature` files; that is
TASK-FP-LINK's job. When LINK ships, this nudge can either remain as a
fallback (low-confidence tagging, interactive skip) or be removed.

See installer/core/commands/feature-plan.md § "Task-scope tag convention"
and the parent review TASK-REV-4D190.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

_TASK_TAG_PREFIX = "@task:"

_NOTICE = (
    "━" * 39 + "\n"
    "ℹ️  BDD oracle (R2) not activated\n"
    + "━" * 39 + "\n"
    "A features/*.feature file was found but no scenarios carry "
    "@task:<TASK-ID> tags.\n"
    "Task-level BDD oracle (R2) will not fire during autobuild.\n"
    "\n"
    "To activate: edit features/<name>.feature and add @task:<TASK-ID> on "
    "the line\n"
    "above each Scenario: that should run for a given task.\n"
    "\n"
    "Example:\n"
    "    @key-example @task:TASK-XXX-001\n"
    "    Scenario: User signs in with valid credentials\n"
    "\n"
    "See installer/core/commands/feature-spec.md § "
    "\"Task-scope tag convention\".\n"
    + "━" * 39
)


def check_bdd_oracle_activation(
    project_root: Path,
    quiet: bool = False,
) -> Optional[str]:
    """Return a notice string iff the user should be nudged to add @task: tags.

    Fires the notice only when at least one `features/*.feature` file exists
    AND none of those files contain any `@task:` tag. Partial activation
    (some scenarios tagged, some not) is intentionally NOT flagged — the
    assumption is the user is mid-tagging and further prodding is noise.

    Args:
        project_root: Path to the feature's project root. The helper looks
            for `project_root/features/*.feature`.
        quiet: When True, always return None. Used to honour `--no-questions`
            and equivalent quiet flags so CI runs don't emit the banner.

    Returns:
        Notice text (str) when the nudge should fire, otherwise None.

    Branches (see AC):
    - no `features/*.feature` file              -> None
    - any `.feature` file contains `@task:`     -> None
    - `.feature` files exist, none with `@task:` -> notice string
    """
    if quiet:
        return None

    features_dir = project_root / "features"
    if not features_dir.is_dir():
        return None

    feature_files = sorted(features_dir.glob("*.feature"))
    if not feature_files:
        return None

    for feature_file in feature_files:
        try:
            text = feature_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if _TASK_TAG_PREFIX in text:
            return None

    return _NOTICE
