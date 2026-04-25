"""CI lint: every hardcoded TASK-ID literal in orchestrator code must resolve
to an actual filed task.

Seeded by TASK-FIX-7A0A (FEAT-F3D7). The forge-run-3 investigation
(TASK-REV-F3D7) surfaced a dead ``TASK-FIX-7A08`` reference hardcoded in
two orchestrator modules, pointing at a task that never existed at the
time. This test prevents that class of defect from regressing: whenever
orchestrator code names a task ID, that ID must exist as a file (or
directory) under ``tasks/`` or ``docs/state/``.

Scope
-----
Lint only ``guardkit/orchestrator/**/*.py`` for the first pass. Broadening
to CLI code, ``guardkit/knowledge``, or the tests tree can be a separate
follow-up if valuable — the original incident was orchestrator-localised.

Placeholder handling
--------------------
Docstrings and examples routinely use placeholder IDs such as
``TASK-XXX-YYYY``. Any ID whose body contains ``XXX``, ``YYY``, ``ZZZ``,
or ``NNN`` is treated as a placeholder and skipped. IDs without any digit
in the body (``TASK-ID``, ``TASK-FIX``) are treated as incomplete prefixes
and skipped as well — real hash-based IDs always include a digit (see
``.claude/rules/hash-based-ids.md``).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATOR_ROOT = REPO_ROOT / "guardkit" / "orchestrator"
TASKS_ROOT = REPO_ROOT / "tasks"
DOCS_STATE_ROOT = REPO_ROOT / "docs" / "state"

TASK_ID_RE = re.compile(
    r"\bTASK-[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*(?:\.\d+(?:\.\d+)*)?\b"
)

PLACEHOLDER_TOKENS = ("XXX", "YYY", "ZZZ", "NNN")


def _id_is_placeholder(task_id: str) -> bool:
    body = task_id.removeprefix("TASK-")
    if any(token in body for token in PLACEHOLDER_TOKENS):
        return True
    if not any(ch.isdigit() for ch in body):
        return True
    return False


def _task_id_resolves(task_id: str) -> bool:
    for root in (TASKS_ROOT, DOCS_STATE_ROOT):
        if not root.exists():
            continue
        for path in root.rglob(f"{task_id}*"):
            name = path.name
            if (
                name == task_id
                or name == f"{task_id}.md"
                or name.startswith(f"{task_id}-")
                or name.startswith(f"{task_id}.")
            ):
                return True
    return False


def test_no_dead_task_id_references_in_orchestrator() -> None:
    unresolved: list[str] = []
    for py_file in sorted(ORCHESTRATOR_ROOT.rglob("*.py")):
        text = py_file.read_text(encoding="utf-8", errors="replace")
        rel = py_file.relative_to(REPO_ROOT)
        for lineno, line in enumerate(text.splitlines(), start=1):
            for match in TASK_ID_RE.finditer(line):
                task_id = match.group(0)
                if _id_is_placeholder(task_id):
                    continue
                if not _task_id_resolves(task_id):
                    unresolved.append(f"{rel}:{lineno}  {task_id}")

    assert not unresolved, (
        "Hardcoded TASK-ID references in orchestrator code that do not "
        "resolve to any filed task (searched tasks/ and docs/state/).\n"
        "Either file the missing task, fix the typo, or rewrite the "
        "reference as a placeholder (e.g. TASK-XXX-YYYY).\n  "
        + "\n  ".join(unresolved)
    )


def test_known_live_references_resolve() -> None:
    """Spot-check live references so that a future refactor that relocates
    them still trips this assertion if the referenced task is ever removed.

    Historical context: TASK-FIX-7A08 was reverted by TASK-REV-F4A1 because
    the prompt-mandate fix-class did not change Player behaviour across three
    fresh runs on two repos. The canary references for the lint mechanism
    are now the surviving phase-2 task (7A09) and this rule's own task (7A0A).
    """

    assert _task_id_resolves("TASK-FIX-7A09"), (
        "TASK-FIX-7A09 must resolve — it is a surviving phase-2 reference "
        "whose removal would indicate code rot."
    )
    assert _task_id_resolves("TASK-FIX-7A0A"), (
        "TASK-FIX-7A0A (this task) must be filed somewhere under tasks/."
    )
