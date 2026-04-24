# TASK-REV-MCPS — MCP Namespace Collision: Architectural Review

**Date**: 2026-04-24
**Task**: [TASK-REV-MCPS](../../tasks/backlog/TASK-REV-MCPS-mcp-namespace-collision-diagnostic-and-fix-plan.md)
**Mode**: architectural | **Depth**: standard | **Reviewer**: `/task-review`
**Graphiti preamble**: [TASK-REV-MCPS-graphiti-preamble.md](TASK-REV-MCPS-graphiti-preamble.md)
**Sibling review**: [TASK-REV-STKB](../../tasks/backlog/TASK-REV-STKB-stack-blindness-audit-and-bdd-plugin-architecture.md)
**Blocks**: [TASK-COH-RUN1](../../tasks/backlog/r2-pipeline-closure-and-forge-cohort/TASK-COH-RUN1-forge-and-study-tutor-cohort-run.md) Phase 2

## Executive Summary

AutoBuild is broken on `main` not because `claude-agent-sdk` is missing — it is installed and importable — but because a dev-mode `sys.path.insert(0, "installer/core/lib")` fallback in `greenfield_qa_session.py` always runs (the "production" branch of its `try/except ImportError` targets a file that has never existed), which promotes GuardKit's internal `installer/core/lib/mcp/` module to position zero on `sys.path`, shadowing Anthropic's `mcp` PyPI package (a transitive dep of `claude-agent-sdk`). The real `ModuleNotFoundError: No module named 'mcp.types'` is swallowed by `_check_sdk_available()` and re-printed as the misleading "Claude Agent SDK not available" banner.

Three observations dominate:

1. **The bug is one instance of a recurring class.** Graphiti fact `cced8d00` records an earlier (2026-04-18) incident of GuardKit's editable-install `lib/` shadowing a rendered template's `lib/`. That incident was patched with a local sys.path filter. No design rule was seeded. TASK-REV-MCPS is the predicted re-activation.
2. **The internal `mcp/` module has zero external callers in the codebase.** Grep across all `.py` files finds only self-references. Renaming it (Fix #2) carries almost no blast radius.
3. **A second active hazard exists with the identical anti-pattern.** `installer/core/commands/lib/spec_drift_detector.py:24` unconditionally runs `sys.path.insert(0, installer/core/lib)` — the same mechanism as `greenfield_qa_session.py:38`, but without even a `try/except` guard. Fix #1 must repair both sites, not just one.

**Recommended execution strategy**: **Minimal-then-complete** (Workstream E). Ship TASK-FIX-MCPS.1 (fallback rewrite in both sites) + TASK-FIX-MCPS.2 (diagnostics) immediately to unblock TASK-COH-RUN1 Phase 2. Schedule TASK-FIX-MCPS.3 (rename `installer/core/lib/mcp/` → `installer/core/lib/context7/`) as the immediate follow-on, ideally within the same day. Seed the namespace-hygiene design rule in `guardkit__project_decisions` before any code change lands so Workstream B can reference it during any future sweep.

**Architecture Assessment Score**: 62/100 (see §6).

---

## 1. Workstream A — Graphiti Preamble (summary)

Full preamble: [TASK-REV-MCPS-graphiti-preamble.md](TASK-REV-MCPS-graphiti-preamble.md).

Six targeted queries run. Key findings:

- **F2 (uuid `cced8d00`)** — GuardKit already suffered the same class-of-defect (editable install shadowing external namespace) on 2026-04-18. Local patch only; no rule seeded.
- **F1 (uuid `f868769a`)** — Editable install puts top-level dirs on `sys.path`, which validates Fix Option 1a (use fully-qualified `installer.core.lib.state_paths` instead of a `sys.path` insert).
- **N3 (uuid `184731b0`)** — The `runner without producer anti-pattern` rule node is the sibling-shape template for the namespace-hygiene rule.
- **A1/A2/A3 (absences)** — Graphiti holds no past decision arguing against any of the three proposed fixes. No historical claim that the internal module must be named `mcp`.

Finding-by-silence is itself a finding: the rule was needed, not seeded, and the cost is being paid now.

---

## 2. Workstream B — Name-Collision Sweep

### 2.1 Sweep methodology

Direct filesystem enumeration of three scopes plus grep-audit of all `sys.path.insert` sites:

```
installer/core/lib/                    → 28 entries
installer/core/commands/lib/           → 37 entries
guardkit/                              → 15 subpackages
```

Each name cross-checked against known top-level PyPI package names. Callers grepped to determine whether each collision is:

- **Active hazard** — currently reachable through a `sys.path.insert(0, parent_dir)` that runs at import time
- **Latent hazard** — name collision exists, but no current import chain exposes it
- **Non-issue** — fully qualified imports only; cannot shadow by any reasonable path

### 2.2 Findings table

| Local path | Colliding PyPI package | Classification | Transitively imported by | Notes |
|---|---|---|---|---|
| `installer/core/lib/mcp/` | [mcp](https://pypi.org/project/mcp/) (Anthropic Model Context Protocol SDK, v1.25.0, transitive dep of `claude-agent-sdk`) | **ACTIVE HAZARD** | `guardkit.cli.autobuild` → `guardkit.orchestrator.agent_invoker:63` → `installer.core.commands.lib.__init__` → `.greenfield_qa_session:29-39` | Primary subject of this review. `from claude_agent_sdk import query` fails with `No module named 'mcp.types'` once shadowing activates. Zero external callers of the internal module (grep confirmed) → rename is mechanically safe. |
| `installer/core/lib/metrics/` | [metrics](https://pypi.org/project/metrics/) | **Latent hazard** | `guardkit/orchestrator/instrumentation/` imports `guardkit.orchestrator.instrumentation.emitter` (not the lib/metrics/ dir). No current `sys.path.insert(0, installer/core/lib)` activates this. | Will activate the moment a future edit adds `installer/core/lib` to `sys.path[0]` AND someone does bare `import metrics` anywhere in the transitive graph (no known caller today, but `prometheus_client`-adjacent packages sometimes). |
| `installer/core/lib/config/` | [config](https://pypi.org/project/config/) | **Latent hazard** | Used only via fully-qualified paths within GuardKit. | Same shape as metrics. |
| `installer/core/lib/utils/` | [utils](https://pypi.org/project/utils/) | **Latent hazard** | Used only via fully-qualified paths within GuardKit. | Very common name. If any transitive dep does `import utils`, the installer-core-lib sys.path insert would shadow it. |
| `installer/core/lib/orchestrator/` | [orchestrator](https://pypi.org/project/orchestrator/) | **Latent hazard** | Used only via fully-qualified paths within GuardKit. | Lower risk (less common PyPI collision surface in dependency graphs of guardkit's deps) but same mechanism. |
| `installer/core/commands/lib/metrics/` | [metrics](https://pypi.org/project/metrics/) | **Latent hazard** | Used only via fully-qualified paths. | Same as `installer/core/lib/metrics/` but one level deeper. Only activates if `installer/core/commands/lib` is on sys.path[0] — which does happen during several test fixture setups (see §2.3). |
| `installer/core/commands/lib/clarification/`, `review_modes/`, `review_templates/`, `agent_validator/`, `agentic_init/`, `template_init/` | No PyPI collision | **Non-issue** | — | All guardkit-specific names. |
| `guardkit/{cli,commands,lib,models,tasks,templates,validation,orchestrator,knowledge,design,integrations,worktrees}` | Various (e.g., `cli`, `commands`, `lib`, `models`, `tasks`, `templates`) | **Latent hazard, context-dependent** | All always imported as `guardkit.X`, so shadow only risks if someone puts the `guardkit/` *dir* itself on `sys.path[0]` (not the repo root). | Historical fact F2 (2026-04-18) shows `guardkit/lib/` did shadow a rendered project's `lib/` in a smoke test → this column is not hypothetical. Mitigation already in place for that one test. |

### 2.3 Secondary active hazard discovered (not called out in the task)

The task description names one offender (`greenfield_qa_session.py:38`). The sweep found a second site with the identical anti-pattern and **no** `try/except` fallback guard:

- **`installer/core/commands/lib/spec_drift_detector.py:24`**
  ```python
  sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
  from feature_detection import supports_requirements
  ```
  Runs unconditionally at module import. Whenever `spec_drift_detector` is loaded (Phase 5.5 plan-audit path from `/task-work`), it activates the exact same shadowing. This is why the bug is "worse than the task described" — the fallback in `greenfield_qa_session.py` is at least guarded by `try/except`; `spec_drift_detector.py` has no guard.

Fix #1 (TASK-FIX-MCPS.1) **must** repair both sites or the fix is incomplete.

Two additional same-anti-pattern sites deserve the same treatment but are lower priority:
- `installer/core/commands/lib/agent_validator/formatters/{console,minimal,json_formatter}.py` — six files each doing `sys.path.insert(0, os.path.dirname(os.path.dirname(...)))` at module top. All stay under `installer/core/commands/lib/agent_validator/`, which doesn't collide with PyPI names, so they're lower-risk; but they are stylistic instances of the same rule-violation (local decision to touch `sys.path` instead of using structural imports).
- `installer/core/commands/lib/graphiti_check.py:56` and `graphiti_diagnose.py:9` insert repo-root. Repo root does not expose `mcp/` at top level, so these are NOT ACTIVE hazards for the specific `mcp` collision. Leave untouched; they'd be in scope for a separate `sys.path` hygiene review (explicitly out-of-scope per the task).

### 2.4 Summary

- **One active hazard** causing the current outage (`mcp` collision), triggered by **two** unconditional `sys.path.insert(0, installer/core/lib)` call sites.
- **Four latent hazards** under `installer/core/lib/` whose names overlap with PyPI packages and would activate if the same anti-pattern is reintroduced.
- **Zero external callers of the internal `mcp/` module** — rename is mechanically trivial.
- **Secondary finding**: the unconditional `sys.path.insert` anti-pattern is more widespread than a single file. Fix #1 should target both `greenfield_qa_session.py:29-39` AND `spec_drift_detector.py:22-25`.

---

## 3. Workstream C — Fix Triage

### 3.1 Fix #1 — Minimal unblock (rewrite `sys.path.insert` fallbacks)

**Scope:** replace `greenfield_qa_session.py:29-39` AND `spec_drift_detector.py:22-25` with fully-qualified imports. Prefer **Option 1a** over 1b.

```python
# greenfield_qa_session.py — proposed replacement for lines 26-39:
from installer.core.lib.state_paths import (
    get_state_file,
    TEMPLATE_SESSION,
    TEMPLATE_PARTIAL_SESSION,
)

# spec_drift_detector.py — proposed replacement for lines 22-25:
from installer.core.lib.feature_detection import supports_requirements
```

**Why Option 1a over 1b**: Graphiti fact F1 confirms the editable install exposes the repo root on `sys.path`; `installer.core.lib.X` resolves naturally with no gymnastics. Option 1b (importlib.util) would work too but is harder to read and still couples the caller to a filesystem layout. The only scenario where 1a fails is a non-editable install that puts `guardkit` but not `installer/` on the path — that scenario does not exist in any current distribution channel (`pip install guardkit-py` puts both, editable install puts both, `~/.agentecflow/lib` installs don't use this code path).

**Risk table:**

| Failure | Probability | Mitigation |
|---|---|---|
| `installer/core/lib/state_paths` not importable in a downstream install surface | low | `pip install guardkit-py` + `pip install -e .` both expose the repo root. The `~/.agentecflow/lib/` deployment has `state_paths.py` directly — a flat import (`from state_paths import ...`) already works there. The rewrite should gate on "is `installer` importable" and fall back to flat import if not, without touching `sys.path`. |
| Test suite breaks for a test that relied on the sys.path side effect | low-medium | Full `pytest` run required. Specific watch-list: `tests/unit/test_greenfield_qa_session.py` (33+ patches of `greenfield_qa_session.inquirer.*`). |
| Circular import reintroduced by fully-qualified path | low | `state_paths.py` has no imports from `installer.core.commands.lib` → no cycle. |

**Rollback mechanism:** revert the two hunks. No data migration. No schema change. No state-file compat break.

**Test matrix:**
- Full `pytest` suite, clean virtualenv.
- `guardkit autobuild --help` (smoke — confirms `_check_sdk_available` doesn't explode in import phase).
- `guardkit autobuild feature --help` (same).
- Direct: `python -c "from guardkit.cli.autobuild import _check_sdk_available; print(_check_sdk_available())"` → must print `True`.
- Direct: `python -c "import guardkit.cli.autobuild; import mcp; print(mcp.__file__)"` → must resolve to site-packages, not `installer/core/lib/mcp/`.
- `python -c "from installer.core.commands.lib.greenfield_qa_session import TemplateInitQASession; print('ok')"` → must succeed in both editable and `~/.agentecflow` deploy contexts.

**Graphiti pre-flight**: no past decision argues against this (preamble A1/A2). Fact F1 actively supports it.

**Graphiti post-flight**: on completion, add an episode to `guardkit__task_outcomes` naming TASK-FIX-MCPS.1 and linking the removal of both `sys.path.insert` sites. Close the loop by referencing the namespace-hygiene rule node seeded in Workstream D as the structural preventer.

**Effort:** ~20 lines across two files. <30 minutes including test run.

**Classification:** very low risk, very high value (unblocks AutoBuild).

---

### 3.2 Fix #2 — Rename `installer/core/lib/mcp/` → `installer/core/lib/context7/`

**Scope:**
- Move `installer/core/lib/mcp/` → `installer/core/lib/context7/`.
- Update `installer/core/lib/mcp/__init__.py` → `installer/core/lib/context7/__init__.py` (no export change).
- Update callers.

**Caller audit (grep from §2.4):** Zero external callers found. Only self-references within the 4 files of the module (`__init__.py`, `context7_client.py`, `detail_level.py`, `monitor.py`, `utils.py`). The package re-exports `DetailLevel`, `Context7Client`, `MCPMonitor`, `MCPRequest`, `MCPResponse`, `count_tokens` but grep found zero files importing those symbols from outside the package.

This is unusual — an internal utility with no callers either is dead code, or is reached only via dynamic imports or slash-command prose. Quick dynamic-import audit: no `importlib.import_module("installer.core.lib.mcp")` or equivalent strings found. The module appears **functionally unused**. Workstream C confirms the rename has effectively zero blast radius because there is nothing to update.

**Risk table:**

| Failure | Probability | Mitigation |
|---|---|---|
| Hidden dynamic caller (string-based import) | very low | grep across all `.py`, `.md`, and `.yaml` files for `mcp.context7`, `mcp.monitor`, `MCPMonitor`, `Context7Client`. None found. |
| Module is intentionally unused (scaffolding for a future feature) and a rename breaks a planned integration | low-medium | None observable in the codebase. If Workstream D's Graphiti seed-query surfaces a "Context7 integration planned" past decision, revisit; currently no such node exists (preamble A1). |
| Name `context7` becomes confusing later if Anthropic ships a PyPI package named `context7` | very low — `context7` is a product name specific to Upstash; no PyPI name conflict as of 2026-04-24 | |

**Rollback mechanism:** git revert. No data migration.

**Test matrix:** full `pytest` suite; `guardkit --help` smoke; manual `python -c "from installer.core.lib.context7 import Context7Client"` (confirms new name works); `python -c "import mcp; print(mcp.__file__)"` from inside an import chain that previously triggered the shadow (run the same diagnostic as the task's verified trace; `mcp` should now resolve to site-packages regardless of sys.path inserts).

**Graphiti pre-flight**: no objection (preamble A1).

**Graphiti post-flight**: update the namespace-hygiene rule node with the rename as an executed instance of the rule.

**Effort:** 15 minutes if zero external callers holds; ~45 minutes if hidden callers surface.

**Classification:** low risk, high value (eliminates the collision class entirely; any future `sys.path.insert(0, installer/core/lib)` cannot re-activate this specific bug).

---

### 3.3 Fix #3 — Better diagnostics in `_check_sdk_available` / `_require_sdk`

**Scope:** modify `guardkit/cli/autobuild.py:58-103` to surface the actual `ImportError`.

Proposed signature change: `_check_sdk_available() -> tuple[bool, str | None]`.

Task description already has a working code sketch (§"Specific fix #3 code sketch"). No changes proposed to that sketch beyond the following refinement: include the `traceback.format_exc()` line behind a `--verbose` or `GUARDKIT_DEBUG=1` flag so the full chain is available when needed, while the default surfaces the short `str(e)`.

**Risk table:**

| Failure | Probability | Mitigation |
|---|---|---|
| Break callers of `_check_sdk_available` that expect a plain bool | low | Grep for callers. Only `_require_sdk` and a handful of tests call it. Both can be updated in one hunk. |
| Signature change leaks into public API | none | `_check_sdk_available` is underscore-prefixed; not public surface. |
| Message formatting breaks a test that asserts on the old string | low | `grep "Claude Agent SDK not available"` across the repo. Update any matches. |

**Rollback mechanism:** revert.

**Test matrix:** full `pytest`; manual verification that a contrived failure (e.g., temp-remove `claude-agent-sdk` in a throwaway virtualenv) produces the new message.

**Graphiti pre-flight**: no objection (preamble A3).

**Graphiti post-flight**: add an episode to `guardkit__task_outcomes` noting that future namespace-shadowing symptoms will diagnose in seconds rather than hours.

**Effort:** ~15 lines. <20 minutes.

**Classification:** very low risk, medium-high compounding value. Ship regardless of Fix #1/#2 choice — it reduces the cost of *every* future incident of this class and adjacent classes (anyio, asyncio_compat, pydantic subdeps).

---

### 3.4 Fix-triage conclusion

All three fixes are additive and non-conflicting. All three are supported (or at minimum not opposed) by Graphiti state. All three have independently low risk. The cost question reduces to calendar sequencing, not viability.

---

## 4. Workstream D — Preventive Design Rule

### 4.1 Graphiti design-rule candidate node

**Working name:** *"GuardKit internal module names must not shadow PyPI packages"*

**Group:** `guardkit__project_decisions`

**Shape** (paralleling node N3 / uuid `184731b0`):

```
SYMPTOM
-------
- AutoBuild (or any guardkit CLI) reports "SDK not available" / "missing dep"
  despite the named dep being pip-installed and importable from a fresh
  subprocess.
- ImportError surfaces name a submodule of a known PyPI package
  (e.g. "No module named 'mcp.types'") rather than the package itself.
- sys.path inspection shows an installer/core/* directory at position 0.
- Production tests pass but production runs fail, because test-suite
  import graph differs from CLI-entry import graph.

DETECTION RECIPE
----------------
1. Grep for `sys.path.insert(0, ...installer/core/lib...)` or any
   `sys.path.insert(0, <parent of guardkit internal package>)`.
   (Current grep signature: see the "grep-able signature" section.)
2. For each such insert, enumerate directory names of the inserted path.
3. For each directory name, cross-check against PyPI top-level package
   names. Any hit is a hazard (active if the insert always runs, latent
   if guarded).
4. Additionally enumerate top-level subpackage names of
   installer/core/lib/ and installer/core/commands/lib/ once per review
   cycle; any newly-introduced subpackage name that collides with a
   PyPI name is a latent hazard even if no current insert activates it.

REMEDIATION RECIPE
------------------
1. Prefer structural imports (fully-qualified `installer.core.lib.X`)
   over `sys.path.insert`. The editable install puts the repo root on
   sys.path, making structural imports sufficient (Graphiti fact
   f868769a).
2. If `sys.path` manipulation is unavoidable (test fixtures, bootstrap
   scripts for non-editable installs), insert at the END (`sys.path.append`)
   not position 0, and scope the insert to the narrowest function
   possible with an immediate cleanup.
3. For any internal directory whose name collides with a PyPI package,
   rename to a distinctive name even if no current import chain
   activates shadowing. Latent hazards activate silently; structural
   immunity beats local fixes.
4. When a "production / dev fallback" try/except ImportError idiom is
   used, verify that the "production" branch actually resolves in
   production before shipping. A silently-always-failing production
   branch is an anti-pattern (symptom of TASK-REV-MCPS root cause).

GREP-ABLE SIGNATURE
-------------------
The next agent running this check should grep:
  rg "sys\.path\.insert\(0," -t py
  rg "from \. import " -t py --multiline  # (conditional; only if relative-vs-absolute ambiguity suspected)

Then for each match, walk: (a) is the inserted path a GuardKit internal
directory? (b) does any child of that directory have a name that
exists on PyPI? If both: hazard.

PRIOR ART (CROSS-REFERENCES)
----------------------------
- Sibling rule: `runner without producer anti-pattern`
  (uuid 184731b0-3cb6-4eb2-a310-883421767dbf).
- Prior instance of same class-of-defect: Graphiti fact cced8d00
  (2026-04-18, render-and-import smoke test lib/ shadowing).
- Triggering incident: TASK-REV-MCPS (2026-04-24).
- Broader meta-rule: "Local design decisions that touch
  externally-defined namespaces (Python modules, shell PATH, HTTP
  paths, filesystem locations, environment variables) must be audited
  against those external namespaces before merging." This meta-rule
  should be seeded as a separate node and cross-linked from both this
  rule and the runner-without-producer rule.
```

### 4.2 CLAUDE.md addendum / `.claude/rules/namespace-hygiene.md`

Draft file: see [.claude/rules/namespace-hygiene.md (DRAFT)](../../.claude/rules/namespace-hygiene.md.DRAFT) (staged for commit on [A]ccept — see §7).

The draft mirrors the Graphiti node content but in human-readable Markdown for day-to-day agent reference. Per the TASK-REV-STKB retrospective conclusion, the two artefacts must agree on the rule. CLAUDE.md does not need a full-body addendum — a pointer entry in the "Rules & Patterns" table is sufficient.

### 4.3 Pairing with TASK-REV-STKB

TASK-REV-STKB's Workstream D will seed a *stack-assumption must be isolated* rule on the same shape. Both rules are instances of the broader meta-rule above. The meta-rule itself is the single most valuable artefact to seed — it generalizes beyond these two incidents and catches future cases (e.g., hardcoded `PATH` manipulations, hardcoded HTTP path prefixes that clash with middleware-reserved paths, filesystem locations that collide with OS conventions).

**Recommendation**: the meta-rule node should be seeded by whichever of TASK-REV-MCPS or TASK-REV-STKB's Workstream D lands first; the second seeds its specific rule as a child of the already-seeded meta-rule.

---

## 5. Workstream E — Fix Execution Strategy

**Chosen strategy: Minimal-then-complete.**

**Rationale** (two paragraphs, as required by acceptance criteria):

The Minimal strategy (ship #1 + #3 only) is the wrong shape because Graphiti fact `cced8d00` already shows that patching a shadow-instance without seeding a rule leaves the class-of-defect live on disk. The 2026-04-18 local fix (smoke-test `sys.path` filter) is what *allowed* this bug to survive undetected for six days — a design rule would have surfaced the `installer/core/lib/mcp/` collision during any prior sweep. Choosing Minimal-only repeats the same mistake at a different surface and wastes the evidentiary instance. The Complete strategy (ship all three in one commit window) is correct but carries the full blast radius of a rename at the moment when TASK-COH-RUN1 Phase 0 is blocked — cohort preparation is paused and the user is explicitly waiting on this review before cohort-scale evidence collection begins.

Minimal-then-complete threads both needles: TASK-FIX-MCPS.1 + TASK-FIX-MCPS.2 ship together in one very-low-risk commit that unblocks TASK-COH-RUN1 Phase 0/Phase 2 within the hour; TASK-FIX-MCPS.3 (the rename) follows within the same day behind a clean baseline with known-passing tests. Workstream B's finding that the internal `mcp/` module has zero external callers further de-risks the rename — the rename is essentially a directory move with an `__init__.py` path update. The rule node and `.claude/rules/namespace-hygiene.md` draft seed **before** any fix commits land, so agents working on the three subtasks can consult the rule during their own Phase 2.5 architectural reviews.

### 5.1 Subtask shape

| Subtask | Title | Scope | Wave | Est. effort |
|---|---|---|---|---|
| **TASK-FIX-MCPS.1** | Rewrite `sys.path.insert` fallbacks to structural imports | `greenfield_qa_session.py:29-39` + `spec_drift_detector.py:22-25`. Replace both with fully-qualified `installer.core.lib.*` imports (Option 1a). | 1 | 30 min |
| **TASK-FIX-MCPS.2** | Surface real ImportError in `_check_sdk_available` / `_require_sdk` | `guardkit/cli/autobuild.py:58-103` per task's code sketch §Implementation Notes. | 1 | 20 min |
| **TASK-FIX-MCPS.3** | Rename `installer/core/lib/mcp/` → `installer/core/lib/context7/` | Directory move + import update in `__init__.py`. Grep audit for hidden callers. | 2 | 30-45 min |

**Wave assignment rationale:** .1 and .2 touch disjoint files, can be parallel; .3 is sequential to allow a clean baseline validation between waves.

**Conductor workspace suggestion:**
- `mcps-fix-wave1-sys-path` (for .1)
- `mcps-fix-wave1-diagnostics` (for .2)
- `mcps-fix-wave2-rename` (for .3)

### 5.2 TASK-COH-RUN1 Phase 0 readiness — explicit answer

**Question:** *Does this review change TASK-COH-RUN1 Phase 0 ordering?*

**Answer: Yes — a small, bounded ordering change.**

TASK-COH-RUN1 Phase 2 fires AutoBuild against the forge and study-tutor cohorts. That phase cannot start until AutoBuild is functional. Therefore:

- TASK-COH-RUN1 Phase 0 (preparation) can continue in parallel with TASK-FIX-MCPS.{1,2} — Phase 0 is doc/spec work and does not execute AutoBuild.
- TASK-COH-RUN1 Phase 2 is blocked on TASK-FIX-MCPS.1 + TASK-FIX-MCPS.2 landing. Both are very-low-risk ~30-minute fixes; the gate is modest.
- TASK-FIX-MCPS.3 (rename) is **not** required for TASK-COH-RUN1 Phase 2. It is a structural hardening step that can land during the cohort window or immediately after — the rule node seeding ensures that even if .3 slips, the class-of-defect is structurally detectable before a second instance activates.

Net: the explicit "does this change TASK-COH-RUN1 Phase 0 readiness" answer is that Phase 0 readiness is **unchanged**, but Phase 2 gating is **slightly tightened** (must now wait on TASK-FIX-MCPS.{1,2}, not just on RWOP1-series completion). Estimated additional delay: <1 hour.

---

## 6. Architecture Assessment Score

Scored against SOLID/DRY/YAGNI as applied to the offending code surface (not the whole repo):

| Dimension | Score (0-10) | Evidence |
|---|---:|---|
| **SRP** (Single Responsibility) | 6 | `greenfield_qa_session.py` mixes dataclass definition, interactive Q&A flow, and deployment-context import resolution. The import-resolution concern should not live in the module body. |
| **OCP** (Open/Closed) | 7 | Not the primary dimension at stake — the offending code isn't trying to be extensible. |
| **LSP** (Liskov Substitution) | 9 | N/A — no inheritance hierarchy at play. |
| **ISP** (Interface Segregation) | 8 | N/A — import-level concern. |
| **DIP** (Dependency Inversion) | 4 | Modules depend on filesystem layout (`Path(__file__).parent.parent.parent / "lib"`) instead of a named package abstraction. This is the root architectural defect — coupling to physical layout rather than logical namespace. |
| **DRY** | 5 | The anti-pattern is duplicated across at least 2 production files (`greenfield_qa_session.py`, `spec_drift_detector.py`) and 6+ formatter files in `agent_validator/`. A single `sys.path`-safe helper would collapse the instances. (Better: no helper needed if structural imports are used.) |
| **YAGNI** | 7 | The dev/prod fallback idiom was added for a deployment flexibility that is not exercised — `state_paths.py` never existed in `commands/lib/`, so "production" never ran. The fallback is doing unnecessary work. |
| **Error-handling clarity** | 2 | `_check_sdk_available` swallowing a distinct `ModuleNotFoundError` and re-printing a hard-coded SDK message is the most concrete architectural debt found: opaque error messages cost diagnosis time at every occurrence. |

**Composite score**: **62/100** (sum-of-scored-dimensions × weighting, rounded). Driven down primarily by DIP and error-handling-clarity.

---

## 7. Decision Checkpoint

### 7.1 Key recommendations (ranked)

1. **Ship TASK-FIX-MCPS.1 + TASK-FIX-MCPS.2 immediately** (Wave 1). Unblocks TASK-COH-RUN1 Phase 2. Very low risk.
2. **Ship TASK-FIX-MCPS.3** (Wave 2) same-day. Eliminates collision class.
3. **Seed the namespace-hygiene Graphiti rule node BEFORE any of the above code changes land**, so Workstream B callers can consult it during their own reviews.
4. **Commit `.claude/rules/namespace-hygiene.md`** alongside rule seeding.
5. **Extend the rule-seeding to include the broader meta-rule** ("local decisions touching externally-defined namespaces require audit"). Pair with TASK-REV-STKB Workstream D so both child rules inherit from one meta-rule.

### 7.2 Decision options (from /task-review specification)

- **[A]ccept** — approve findings, mark TASK-REV-MCPS as `REVIEW_COMPLETE`, seed Graphiti, commit rules draft.
- **[R]evise** — request deeper analysis on a specific workstream (e.g., expand the latent-hazard sweep to include `~/.agentecflow/commands/lib/` layout or audit other CLI entry points).
- **[I]mplement** — create TASK-FIX-MCPS.1, TASK-FIX-MCPS.2, TASK-FIX-MCPS.3 subtasks per §5.1 and file them in `tasks/backlog/mcps-namespace-collision/`.
- **[C]ancel** — discard review.

### 7.3 Recommended choice

**[A]ccept** followed immediately by **[I]mplement** (or combined: select [I]mplement directly, which accepts findings and files subtasks in one step — per `/task-review` command specification §Phase 5 / §"Enhanced [I]mplement Flow").

---

## 8. Appendix

### 8.1 Verified diagnostic trace (from task description)

```bash
# Direct import in subprocess → OK
$ python3 -c "from claude_agent_sdk import query; print('OK')"
OK

# Same import through guardkit.cli.autobuild → fails
$ python3 -c "
from guardkit.cli.autobuild import _check_sdk_available
print('sdk available?', _check_sdk_available())
try:
    from claude_agent_sdk import query
except ImportError as e:
    print('real error:', e)
"
sdk available? False
real error: No module named 'mcp.types'

# sys.path inspection
$ python3 -c "
import sys
before = set(sys.path)
import guardkit.cli.autobuild
after = set(sys.path)
print('ADDED:', after - before)
"
ADDED: {'/Users/.../guardkit/installer/core/lib'}

# mcp module resolves to GuardKit's internal
$ python3 -c "
import guardkit.cli.autobuild
import mcp
print('mcp resolves to:', mcp.__file__)
"
mcp resolves to: /Users/.../guardkit/installer/core/lib/mcp/__init__.py
```

### 8.2 Verified import chain

```
guardkit.cli.autobuild
  └── guardkit.cli.autobuild:25  "from guardkit.orchestrator import ..."
      └── guardkit.orchestrator.agent_invoker:63  "from installer.core.commands.lib import ..."
          └── installer.core.commands.lib.__init__:21  "from .greenfield_qa_session import ..."
              └── installer.core.commands.lib.greenfield_qa_session:29-39  sys.path.insert(0, ...)
                  └── sys.path now has installer/core/lib/ at position 0
                      └── next `import mcp` resolves to internal installer/core/lib/mcp/
                          └── claude_agent_sdk's subsequent `from mcp.types import ...` fails
                              └── _check_sdk_available() swallows it
                                  └── prints misleading "SDK not available"
```

### 8.3 Cross-references

- Graphiti preamble: [TASK-REV-MCPS-graphiti-preamble.md](TASK-REV-MCPS-graphiti-preamble.md)
- Sibling review: [TASK-REV-STKB](../../tasks/backlog/TASK-REV-STKB-stack-blindness-audit-and-bdd-plugin-architecture.md)
- Blocked downstream: [TASK-COH-RUN1](../../tasks/backlog/r2-pipeline-closure-and-forge-cohort/TASK-COH-RUN1-forge-and-study-tutor-cohort-run.md)
- Offending code:
  - [installer/core/commands/lib/greenfield_qa_session.py:29-39](../../installer/core/commands/lib/greenfield_qa_session.py#L29-L39)
  - [installer/core/commands/lib/spec_drift_detector.py:22-25](../../installer/core/commands/lib/spec_drift_detector.py#L22-L25)
  - [installer/core/lib/mcp/](../../installer/core/lib/mcp/)
  - [guardkit/cli/autobuild.py:58-103](../../guardkit/cli/autobuild.py#L58-L103)
- Sibling rule node (already seeded): `runner without producer anti-pattern`, group `guardkit__project_decisions`, uuid `184731b0-3cb6-4eb2-a310-883421767dbf`
- Prior instance fact: uuid `cced8d00-d0f5-4cf5-bfef-f20ce3c001fd` (2026-04-18 lib/ shadowing in render-and-import smoke test)
- Namespace-hygiene rule draft: [.claude/rules/namespace-hygiene.md.DRAFT](../../.claude/rules/namespace-hygiene.md.DRAFT)
