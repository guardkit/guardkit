---
id: TASK-GK-PR-001
title: Preflight check that all queued tasks' Files-to-Modify paths exist on disk
status: completed
created: 2026-05-07T00:00:00Z
updated: 2026-05-07T00:00:00Z
completed: 2026-05-07T00:00:00Z
completed_location: tasks/completed/2026-05/TASK-GK-PR-001/
previous_state: in_review
state_transition_reason: "All 10 ACs satisfied; 14/14 new preflight tests pass; 153/153 feature_orchestrator regression tests pass; ruff clean on new files"
priority: medium
priority_band: P2
task_type: feature
parent_run: autobuild-FEAT-PEBR-fail-run-4
parent_run_log: ../../../forge/docs/history/autobuild-FEAT-PEBR-fail-run-4.md
parent_review: TASK-REV-PEBR-002
parent_review_repo: forge
parent_feature_folder: autobuild-feat-pebr-failure-recovery-rev2
related_tasks:
  - TASK-GK-PA-002
  - TASK-FRR-PEB-FM-003
implementation_mode: task-work
wave: 3
complexity: 3
estimated_minutes: 60
dependencies: []
tags:
  - autobuild
  - preflight
  - plan-audit
  - prophylactic
  - operator-experience
  - P2
test_results:
  status: pass
  coverage: null  # not measured for this task — test suite asserts behaviour, not coverage targets
  last_run: 2026-05-07T00:00:00Z
  new_tests_added: 14
  new_tests_passing: 14
  regression_tests_passing: 153
---

# Task: Preflight check that all queued tasks' Files-to-Modify paths exist on disk

> **Target-repo agnostic.** This task is purely a guardkit-side
> improvement. The check operates on the **guardkit task-file
> convention** (`## Files to Modify` / `## Files to Create` sections,
> defined by guardkit's `PlanMarkdownParser` and consumed by
> guardkit's plan-audit pipeline). It reads paths via
> `feature.tasks[*].file_path`, `repo_root`, and `worktree_path`,
> all of which are already passed into `FeatureOrchestrator` from
> the target repo. No forge imports, no forge-specific path
> patterns, no hardcoded test fixtures. The discovery happened in
> a forge feature run (cited below for traceability) but the same
> bug class can fire on any guardkit-managed feature in any target
> repo (Python, TS/JS, C#, etc.) the moment a task author mistypes
> a path under `## Files to Modify`.

## Description

The bug class: a guardkit feature task declares one or more paths
under `## Files to Modify` that do not exist anywhere under
`{repo_root}` or `{worktree_path}`. TASK-GK-PA-002 (rev-2 fix)
treats `## Files to Modify` as authoritative `planned_files` and
correctly fires a `plan_audit` violation at Player turn 1. The
operator-visible failure mode is: 4 turns of identical
`missing_files` feedback, then either `max_turns_exceeded` or
`timeout_budget_exhausted` — typically 25-35 minutes of wall clock
per occurrence, regardless of how trivial the typo is.

The same typo is **discoverable in under 1 second** by a static
existence check at feature-load time, before any Player is
invoked.

### Discovery context (traceability)

The bug class was first surfaced in the forge repo's FEAT-PEBR
autobuild **run-4** (2026-05-07). TASK-FRR-PEB-006 declared
`src/forge/cli/_approval_subscriber.py` under `## Files to Modify`;
the real path is `src/forge/adapters/nats/approval_subscriber.py`.
The Player correctly modified the real file (Coach verified all 6
ACs); the audit nevertheless fired on the typo path for 4 turns,
then `timeout_budget_exhausted`. A parallel audit of the same
feature's other queued tasks turned up TASK-FRR-PEB-012 with the
identical shape. Both forge-side fixes are tracked in
TASK-FRR-PEB-FM-003 (forge repo). This guardkit-side preflight
prevents the same class of error from costing 30 minutes per
occurrence on **any** future feature in **any** target repo.

### What the preflight does

For every task in `feature.tasks`:

- For each path declared under `## Files to Modify` (parsed via
  `PlanMarkdownParser._extract_list_section` — the same parser
  PA-002 uses): the path MUST exist either at
  `{repo_root}/{path}` or at `{worktree_path}/{path}`. If
  neither, emit a structured error/warning naming the task, the
  line number, the declared path, and `difflib.get_close_matches`
  suggestions against the actual on-disk file tree.

- For each path declared under `## Files to Create`: the path
  MUST NOT exist (else the "to-create" semantics is wrong). If it
  does exist, emit a warning (don't fail — it could be a
  legitimate rewrite, or a previous run's artefact in the
  preserved worktree).

The check is **non-blocking by default** for backwards
compatibility (emits structured warnings; existing PA-002 still
catches at turn 1). A new feature-yaml field
`preflight_strict: bool` (default `false`) makes modify-axis
failures abort feature orchestration before wave 1 dispatch.

### Why this is structurally clean (not a forge-specific shim)

- **Inputs**: `feature.tasks` (a guardkit `Feature` model;
  populated from any target repo's `.guardkit/features/*.yaml`),
  `repo_root` (passed in), `worktree_path` (passed in). All three
  are already part of `FeatureOrchestrator.__init__`.
- **Parser**: reuses `PlanMarkdownParser._extract_list_section`
  from `installer/core/commands/lib/plan_markdown_parser.py` —
  the same code TASK-GK-PA-002 calls. No new parser, no
  forge-specific markup.
- **Suggestions**: `difflib.get_close_matches` against `rglob`
  results; works on any tree. The set of "source extensions" to
  index is configurable but defaults to a generic
  multi-language list (`.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.cs`,
  `.go`, `.java`, `.rb`, `.rs`).
- **Test fixtures**: synthetic minimal projects with arbitrary
  `src/foo/bar.py` paths — no forge files, no FEAT-PEBR-shaped
  acceptance criteria. The repro test's structure mirrors the
  bug class, not any specific incident.

### Operator-visible improvement

Today (post-PA-002 only), an operator with a typo'd
`## Files to Modify` sees:

```
WARNING: Plan audit detected high-severity discrepancies — 2 missing file(s):
  src/example/typo/path.py, tests/example/typo/path.py
... (repeated for 4 turns) ...
ERROR: timeout_budget_exhausted at turn 5: remaining=500.0s < min=600s
```

After this preflight (default warning-mode), the operator sees:

```
WARNING: TYPO in TASK-XXX line 157 (## Files to Modify):
  declared: src/example/typo/path.py
  not on disk under repo_root or worktree_path
  closest matches (top 3):
    - src/example/real/path.py (similarity 0.74)
    - src/example/other.py     (similarity 0.42)
    - src/example/path/v2.py   (similarity 0.38)
  plan-audit will fire on turn 1; correct before --resume to skip the loop.
```

— *before* the first Player invocation. With `preflight_strict: true`,
the run aborts at this point with a `PreflightTypoError`.

## Acceptance Criteria

- [ ] **AC-1 — Preflight runs at feature-load time.** After
  `feature_loader.load(feature_yaml_path)` succeeds and before wave
  dispatch begins, a new function (e.g.
  `feature_orchestrator._preflight_validate_task_paths(feature)`)
  runs once, reads each task file's `## Files to Modify` block via
  `PlanMarkdownParser._extract_list_section`, and probes the file
  system.
- [ ] **AC-2 — Modify-axis violations are reported with fuzzy
  suggestions.** For each declared modify-path that doesn't exist
  at either `{repo_root}/{path}` or
  `{worktree_path}/{path}`, the preflight emits a structured
  error of the form (paths are illustrative; the suggestion list
  is whatever `difflib` returns from probing the actual on-disk
  tree):

  ```
  TYPO in TASK-XXX line 157:
    declared: src/example/typo/path.py
    not on disk anywhere under {repo_root} or {worktree_path}
    closest matches (top 3):
      - src/example/real/path.py (similarity 0.74)
      - src/example/other.py     (similarity 0.42)
      - src/example/path/v2.py   (similarity 0.38)
  ```

  Use `difflib.get_close_matches(declared_path, all_indexed_files,
  n=3, cutoff=0.5)` for the suggestions. The indexed-files set is
  built from `repo_root.rglob('*.{py,ts,tsx,js,jsx,cs,go,java,rb,rs}')`
  with virtualenv / cache directories excluded.

- [ ] **AC-3 — Create-axis warnings, not errors.** For each declared
  create-path that DOES exist on disk, log a warning naming the
  task, path, and "expected to NOT exist; is this a re-run?" — but
  do not fail.
- [ ] **AC-4 — `preflight_strict` config knob.** Feature yaml
  accepts an optional `preflight_strict: bool` field (default
  `false`). When `true`, any modify-axis violation aborts feature
  orchestration before wave 1 dispatch. When `false`, violations
  are logged at WARNING level and orchestration proceeds (current
  TASK-GK-PA-002 will still catch them at turn 1, just slower).
- [ ] **AC-5 — Repro test (synthetic, target-repo agnostic).** Add
  `tests/unit/orchestrator/test_feature_preflight.py` with class
  `TestModifyPathExistenceCheck`:
  - Fixture is a `tmp_path`-rooted synthetic project: an empty
    `pyproject.toml`, a `src/sample/real.py` file on disk, a task
    file declaring `## Files to Modify: - src/sample/typo.py` (note
    different basename), and a minimal feature yaml referencing
    that task.
  - Expected (`preflight_strict=True`): preflight raises
    `PreflightTypoError`; the exception's `typos` attribute
    contains one entry whose `declared_path == "src/sample/typo.py"`
    and whose `suggestions` list contains `"src/sample/real.py"`.
  - Expected (`preflight_strict=False`): preflight logs exactly one
    WARNING line naming the task ID, the declared path, and at
    least one suggestion; returns the typo list; wave-1 dispatch
    proceeds.
  - **No real forge / target-repo paths** in the fixture; pure
    synthetic.
- [ ] **AC-6 — Performance: preflight completes in <1s for ≤50
  tasks.** Add a perf test that times the preflight against a
  synthetic 50-task fixture (each task declares 1-2 modify paths
  against an on-disk tree of ~500 `.py` files); assert wall-clock
  < 1 second. No sub-process or network calls; pure file-system
  probe.
- [ ] **AC-7 — Multi-typo, multi-task integration test (synthetic).**
  Synthetic feature yaml with three tasks: task A declares 2 typo
  modify paths, task B declares 1 typo modify path, task C
  declares 1 valid modify path that exists on disk. Expected with
  `preflight_strict=False`: 3 distinct WARNING log lines (one per
  typo across A and B); task C produces no output. Validates that
  the preflight handles multi-task feature graphs correctly.
  - The test's task content is **synthetic**; this AC is the
    pattern that PEB-006 + PEB-012 would have triggered, not a
    test that hard-codes those forge tasks.
- [ ] **AC-8 — Regression: existing feature_orchestrator test suite
  stays green.** All tests under
  `tests/unit/orchestrator/test_feature_orchestrator*.py` and
  `tests/integration/feature_orchestrator/` continue to pass.
- [ ] **AC-9 — All modified files pass project-configured lint/format
  checks** (ruff). New test files pass cleanly.
- [ ] **AC-10 — Documentation.** Update the feature-yaml schema doc
  to describe `preflight_strict`. Add a note to the autobuild CLI
  help describing the WARNING signal users may see. If a runbook
  exists for "task-author typos" / "diagnosing failed autobuild
  runs", link to this preflight section.

## Out of Scope

- **Auto-correcting typos** via fuzzy match. Suggesting candidates
  is enough; the operator decides. Auto-correction is a different
  surface (write-side mutation of task files) with its own
  regression risk.
- **Other declaration kinds** (e.g. `## Dependencies`,
  `## Test requirements`). Scope strictly to `## Files to Modify`
  and `## Files to Create` since those drive plan-audit.
- **Cross-task path consistency** (e.g. task A modifies a file that
  task B creates in an earlier wave). Out of scope — that requires
  inter-task / wave-aware reasoning and a richer feature graph
  representation.
- **Multi-language indexing beyond the listed extensions.** AC-2
  defaults to `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.cs`, `.go`,
  `.java`, `.rb`, `.rs`. Extending to additional extensions
  (`.kt`, `.swift`, `.rs` modules, `.proto`, etc.) is a follow-up
  if a target repo needs it; the indexed-extensions list should be
  configurable via a guardkit-side constant or feature-yaml override
  but the task only requires the multi-language default.
- **Auto-applying suggestions** to task files. Suggesting candidates
  is the contract; rewriting task files is a separate concern with
  different regression risk.

## Files to Create

- `tests/unit/orchestrator/test_feature_preflight.py`
- (Possibly) `guardkit/orchestrator/preflight.py` — new module for
  the preflight logic. Or fold into `feature_orchestrator.py` if
  small enough.

## Files to Modify

- `guardkit/orchestrator/feature_orchestrator.py` (call site for
  preflight; thread `preflight_strict` through)
- `guardkit/orchestrator/feature_loader.py` (or equivalent) — accept
  and validate the `preflight_strict` field

## Implementation notes

### Recommended approach

Add `guardkit/orchestrator/preflight.py`:

```python
import difflib
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PreflightTypo:
    task_id: str
    line: int
    declared_path: str
    suggestions: List[str]
    kind: str  # "modify" or "create"


class PreflightTypoError(Exception):
    """Raised when preflight_strict=True and modify-axis typos are found."""

    def __init__(self, typos: List[PreflightTypo]):
        self.typos = typos
        super().__init__(self._format(typos))

    @staticmethod
    def _format(typos: List[PreflightTypo]) -> str:
        lines = ["Preflight detected task-author typos in `## Files to Modify`:"]
        for t in typos:
            lines.append(f"  TYPO in {t.task_id} line {t.line}:")
            lines.append(f"    declared: {t.declared_path}")
            if t.suggestions:
                lines.append(f"    closest matches (top 3):")
                for s in t.suggestions:
                    lines.append(f"      - {s}")
            else:
                lines.append("    no close matches found on disk")
        return "\n".join(lines)


def preflight_validate(
    feature,
    repo_root: Path,
    worktree_path: Path,
    strict: bool = False,
) -> List[PreflightTypo]:
    """
    Validate every queued task's ## Files to Modify section against disk.

    Returns the list of typos found. When strict=True and the list is
    non-empty, raises PreflightTypoError instead of returning.
    """
    section_re = re.compile(
        r'^## Files to (Create|Modify)\s*\n(.*?)(?=\n##|\Z)',
        re.DOTALL | re.MULTILINE,
    )
    bullet_re = re.compile(r'^[-*]\s*`([^`]+)`|^[-*]\s*(\S+)', re.MULTILINE)

    # Build the on-disk file index once for fuzzy matching.
    # Multi-language by default; the indexed-extensions set is the
    # only language-aware piece and is held as a module-level
    # constant so a target repo can override it via feature yaml
    # or guardkit config without changing the algorithm.
    INDEXED_EXTENSIONS = (
        '.py', '.ts', '.tsx', '.js', '.jsx',
        '.cs', '.go', '.java', '.rb', '.rs',
    )
    EXCLUDED_PATH_FRAGMENTS = (
        '/.venv/', '/__pycache__/', '/.git/',
        '/node_modules/', '/dist/', '/build/',
        '/.guardkit/worktrees/',  # avoid double-indexing nested worktrees
    )
    all_files: List[str] = []
    for root in (repo_root, worktree_path):
        if not root.exists():
            continue
        for p in root.rglob('*'):
            if not p.is_file():
                continue
            if p.suffix not in INDEXED_EXTENSIONS:
                continue
            s = str(p)
            if any(frag in s for frag in EXCLUDED_PATH_FRAGMENTS):
                continue
            all_files.append(str(p.relative_to(root)))

    typos: List[PreflightTypo] = []
    for task in feature.tasks:
        task_path = Path(task.file_path)
        if not task_path.exists():
            continue
        body_lines = task_path.read_text().split('---', 2)
        body = body_lines[2] if len(body_lines) >= 3 else body_lines[0]
        for m in section_re.finditer(body):
            kind = m.group(1).lower()  # "create" or "modify"
            section_text = m.group(2)
            for line_offset, raw_line in enumerate(section_text.splitlines()):
                if not raw_line.strip().startswith(('-', '*')):
                    continue
                # Extract path token (backticked first, then bare)
                bm = re.match(r'^[-*]\s*`([^`]+)`', raw_line.strip())
                if bm:
                    declared = bm.group(1)
                else:
                    bm = re.match(r'^[-*]\s*(\S+)', raw_line.strip())
                    declared = bm.group(1) if bm else None
                if not declared:
                    continue
                if not declared.endswith(INDEXED_EXTENSIONS):
                    continue
                exists = (repo_root / declared).exists() or (worktree_path / declared).exists()
                if kind == 'modify' and not exists:
                    suggestions = difflib.get_close_matches(
                        declared, all_files, n=3, cutoff=0.5,
                    )
                    typos.append(PreflightTypo(
                        task_id=task.id,
                        line=line_offset,  # offset within section; absolute computable
                        declared_path=declared,
                        suggestions=suggestions,
                        kind=kind,
                    ))
                elif kind == 'create' and exists:
                    logger.warning(
                        "%s declares ## Files to Create: %s, "
                        "but file already exists on disk. "
                        "Is this a re-run of a previous attempt? "
                        "Player will treat as no-op or rewrite.",
                        task.id, declared,
                    )

    if typos:
        if strict:
            raise PreflightTypoError(typos)
        for t in typos:
            logger.warning(
                "TYPO in %s ## Files to Modify: declared %s not on disk. "
                "Closest match(es): %s. plan-audit will fire on turn 1; "
                "consider correcting before --resume.",
                t.task_id, t.declared_path, ", ".join(t.suggestions) or "(none)",
            )
    return typos
```

Call site in `feature_orchestrator.py` after feature load, before
wave dispatch:

```python
from .preflight import preflight_validate

# ...inside FeatureOrchestrator.run() or equivalent
typos = preflight_validate(
    feature,
    repo_root=self.repo_root,
    worktree_path=self.worktree_path,
    strict=feature.preflight_strict,
)
if typos:
    logger.info(
        "Preflight: %d task-author typo(s) detected; orchestration "
        "proceeding (preflight_strict=False). plan-audit will catch "
        "these at turn 1.",
        len(typos),
    )
```

### Why default-non-strict

Default-strict would be a behaviour change for existing features
that may have warnings-only acceptable. Default-non-strict gives the
operator a clear signal in the log without breaking existing flows.
Operators who want hard-fail can opt in per feature.

Eventually (post-rev-2 stabilisation) flipping the default to True
is reasonable — but that's a separate task with its own migration
plan.

### Regression risk

- Adds new file-system reads at startup; mitigated by AC-6's <1s
  perf budget and constraining rglob to `.py` files.
- Fuzzy matching could surprise operators with bad suggestions on
  ambiguous typos; cutoff=0.5 is conservative. Acceptable.
- `feature_loader` schema additions are additive; existing yamls
  without `preflight_strict` work unchanged.

## Test requirements

- Unit tests in `test_feature_preflight.py` per ACs 5-7.
- Performance test (AC-6) using a synthetic large fixture.
- Regression suite must stay green (AC-8).

## Coach validation commands

```bash
PYTHONPATH=. python -m pytest tests/unit/orchestrator/test_feature_preflight.py -x -v
PYTHONPATH=. python -m pytest tests/unit/orchestrator/test_feature_orchestrator*.py tests/integration/feature_orchestrator/ -x
ruff check guardkit/orchestrator/preflight.py guardkit/orchestrator/feature_orchestrator.py tests/unit/orchestrator/test_feature_preflight.py
```
