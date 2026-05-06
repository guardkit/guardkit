# Review Report: TASK-REV-1B452 — REVISED v2 (causal-chain validated)

**Title**: Honesty verification false-fails when state-bridge moves task files mid-turn

**Mode**: Architectural · **Depth**: Standard (escalated to deep on revision)
**Reviewer**: `/task-review`
**Date**: 2026-05-06

**Revision history**:
- **v1**: Diagnosed the defect as a Player echo of pre-move path strings. Proposed three layers (canonical-path resolution, demote single-discrepancy short-circuit, inject canonical path into Player prompt).
- **v2 (this revision)**: Traced every data-flow link and boundary crossing in code. **The Player has no direct role.** The `tasks/backlog/...` path enters `files_modified` not from any Player report but from the orchestrator's own post-turn git-enrichment pass. Layer 3 (Player prompt injection) is **wrong target** and is replaced. Layers 1 and 2 remain correct. Confidence raised from "high" to "very high" with five independent verifications.

---

## 0. Headline (revised)

The defect is a **structural collision between three independent, individually-correct design decisions** in the autobuild orchestrator's own code. **The Player is not in the causal chain.** The path that triggers the false-fail is injected into `report["files_modified"]` by [`agent_invoker.py:2796-2797`](../../guardkit/orchestrator/agent_invoker.py) — the orchestrator's own post-turn git-enrichment pass — which sees state_bridge's `shutil.move` as a tracked-file delete relative to the per-task baseline.

The three colliding decisions:

1. **state_bridge** uses `shutil.move()` ([`state_bridge.py:518`](../../guardkit/tasks/state_bridge.py)) — not `git mv` — to move the task file. Reasonable: it's runtime orchestration state, not a commit-worthy event.
2. **`_detect_git_changes`** at [`agent_invoker.py:3062-3112`](../../guardkit/orchestrator/agent_invoker.py) uses `git diff --name-only <baseline>` without `-M`/rename detection. Reasonable: rename detection is heuristic and parallel-wave-unsafe.
3. **`_record_baseline`** runs at [`agent_invoker.py:1391-1392`](../../guardkit/orchestrator/agent_invoker.py) **before** state_bridge moves the file at [`agent_invoker.py:1438`](../../guardkit/orchestrator/agent_invoker.py). Reasonable: baseline must precede SDK invocation for parallel-wave attribution to work.

Each of these is correct in isolation. Together, they cause the post-turn `git diff --name-only` to report `tasks/backlog/TASK-FFC3-005-...md` as a "modified" path (it's actually a delete, but `--name-only` doesn't distinguish). The orchestrator's union-merge then injects this path into the Player's `files_modified` list. The Coach (running CoachVerifier wired in by TASK-AB-FIX-INVAB1 commit `b9a45694` on 2026-05-06) checks `Path.exists()` for every claim, the ghost path doesn't exist (it's in `tasks/design_approved/` now), critical discrepancy fires, short-circuit drops 16 ACs.

**The Player's `files_modified` claim from inside the SDK contains the production code paths. It does not contain `tasks/backlog/...`. The orchestrator put it there.** This was the missing piece in v1.

The fix surface is at the union-merge boundary plus identity-aware honesty resolution. v1's load-bearing Layer 1 (canonical-path resolution) is still correct; v2 replaces v1's Layer 3 (Player prompt injection — would not have helped) with Layer 3' (filter state-bridge-induced paths at union-merge).

---

## 1. Confidence statement (revised)

**Very high confidence**, validated by five independent ground-truth sources:

1. **Coach JSON** (`coach_turn_1.json`, FFC3 worktree): `decision: "feedback"`, `criteria_verification: []`, exact rationale string `"1 honesty discrepancy/discrepancies. Adversarial verification overrode gate evaluation."` — verbatim the f-string at [`coach_validator.py:866-869`](../../guardkit/orchestrator/quality_gates/coach_validator.py).
2. **Log line** at FFC3 line 257: `"Honesty verification produced 1 critical issue(s) for TASK-FFC3-005; short-circuiting gate evaluation."` — verbatim the `logger.warning` at [`coach_validator.py:853-857`](../../guardkit/orchestrator/quality_gates/coach_validator.py).
3. **Code reading**: `_record_baseline` runs at line 1391-1392 of `invoke_player`, **before** `_ensure_design_approved_state` at line 1438. The state_bridge move occurs after baseline capture and before any inner SDK invocation. `git diff --name-only <baseline>` therefore sees the move as a tracked-file delete.
4. **Code reading**: `_detect_git_changes` ([`agent_invoker.py:3082-3105`](../../guardkit/orchestrator/agent_invoker.py)) calls `git diff --name-only <baseline>` (no `-M`). Without rename detection, a `shutil.move` shows the source path in the diff output and the destination path in `git ls-files --others`. The post-merge at [`agent_invoker.py:2796-2797`](../../guardkit/orchestrator/agent_invoker.py) unions these into `report["files_modified"]` and `report["files_created"]` respectively.
5. **Code reading**: `state_bridge.transition_to_design_approved` ([`state_bridge.py:158-201`](../../guardkit/tasks/state_bridge.py)) calls `_update_task_frontmatter` (writes file) followed by `_move_task_to_state` which uses `shutil.move` ([`state_bridge.py:518`](../../guardkit/tasks/state_bridge.py)). No `git mv`. No commit. Move is invisible to git as a rename without explicit `-M`.

The five verifications converge on one causal chain. There is no plausible alternate hypothesis.

---

## 2. C4 component view — actual data flow (with boundary annotations)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ AutoBuildOrchestrator (Python process, parent)                                         │
│                                                                                        │
│  ┌────────────────────────────────────────────────────────────────────────────────┐   │
│  │ AgentInvoker.invoke_player(task_id, turn) [agent_invoker.py:1387]              │   │
│  │                                                                                │   │
│  │  T0  ┌─ _record_baseline()  [line 1391-1392]                                   │   │
│  │      │     └→ subprocess: git rev-parse HEAD                                   │   │
│  │      │     └→ self._baseline_commit = <sha>                                    │   │
│  │      │                                                                         │   │
│  │  T1  ├─ _ensure_design_approved_state(task_id)  [line 1438]                    │   │
│  │      │     └→ TaskStateBridge(task_id, worktree_path, in_autobuild_context=True│   │
│  │      │     └→ bridge.ensure_design_approved_state()                            │   │
│  │      │           └→ _update_task_frontmatter(task_path, {status: "design..."}) │   │
│  │      │           └→ shutil.move(backlog/X.md, design_approved/X.md)            │   │
│  │      │                  ╔═══════════════════════════════════════════════════╗  │   │
│  │      │                  ║  [FILESYSTEM BOUNDARY — worktree mutated]         ║  │   │
│  │      │                  ║  before:  tasks/backlog/TASK-X-foo.md  (tracked)  ║  │   │
│  │      │                  ║  after:   tasks/design_approved/...   (untracked) ║  │   │
│  │      │                  ║  git view: tracked-file-delete + untracked-file   ║  │   │
│  │      │                  ║  (no rename info — shutil.move ≠ git mv)          ║  │   │
│  │      │                  ╚═══════════════════════════════════════════════════╝  │   │
│  │      │                                                                         │   │
│  │  T2  ├─ _invoke_task_work_implement(task_id, turn)  [line 1440]                │   │
│  │      │     ╔═════════════════════════════════════════════════════════════════╗ │   │
│  │      │     ║  [PROCESS BOUNDARY — Claude Agent SDK subprocess]               ║ │   │
│  │      │     ║                                                                 ║ │   │
│  │      │     ║   inner SDK process (Player LLM via Anthropic API)              ║ │   │
│  │      │     ║   • Read tasks/design_approved/TASK-X-foo.md  (post-move path)  ║ │   │
│  │      │     ║   • Edit src/x.py, src/y.py, tests/test_x.py                    ║ │   │
│  │      │     ║   • Run pytest internally                                       ║ │   │
│  │      │     ║   • TaskWorkStreamParser tracks Edit/Write tool calls →         ║ │   │
│  │      │     ║       _files_modified = {src/x.py, src/y.py, ...}              ║ │   │
│  │      │     ║       (does NOT contain tasks/backlog/* — file is gone)        ║ │   │
│  │      │     ║   • inner agent writes task_work_results.json with these paths ║ │   │
│  │      │     ╚═════════════════════════════════════════════════════════════════╝ │   │
│  │      │                                                                         │   │
│  │  T3  ├─ _create_player_report_from_task_work(task_id, turn, result)            │   │
│  │      │     [line 2680-2826]                                                    │   │
│  │      │                                                                         │   │
│  │      │     • report["files_modified"] = task_work_data["files_modified"]      │   │
│  │      │       (Player-side: production code paths only — honest)                │   │
│  │      │                                                                         │   │
│  │      │     • git_changes = self._detect_git_changes()  [line 2788]             │   │
│  │      │           └→ subprocess: git diff --name-only <baseline_commit>         │   │
│  │      │                ╔════════════════════════════════════════════════════╗   │   │
│  │      │                ║ [SUBPROCESS BOUNDARY — git CLI returns text]      ║   │   │
│  │      │                ║ stdout includes:                                  ║   │   │
│  │      │                ║   tasks/backlog/TASK-X-foo.md  ← state-bridge     ║   │   │
│  │      │                ║                                  ghost (delete)   ║   │   │
│  │      │                ║   src/x.py, src/y.py, tests/...  ← real Player    ║   │   │
│  │      │                ╚════════════════════════════════════════════════════╝   │   │
│  │      │                                                                         │   │
│  │      │     • UNION MERGE  [line 2796-2797]:  ★ ROOT-CAUSE INJECTION POINT ★    │   │
│  │      │           report["files_modified"] = sorted(list(                       │   │
│  │      │               original_modified | git_modified                          │   │
│  │      │           ))                                                             │   │
│  │      │           # Player's honest claim ∪ git's ghost path                    │   │
│  │      │                                                                         │   │
│  │      │     • write player_turn_N.json                                          │   │
│  │      │                                                                         │   │
│  │  T4  └─ Coach phase (next: validate)                                           │   │
│  │            ↓                                                                   │   │
│  │  ┌──────────────────────────────────────────────────────────────────────────┐ │   │
│  │  │ CoachValidator.validate(task, task_work_results, turn)                   │ │   │
│  │  │   [coach_validator.py:??-??, position 1.4]                                │ │   │
│  │  │                                                                          │ │   │
│  │  │   honesty_verification = self._verify_honesty(task_work_results)        │ │   │
│  │  │     [line 850; impl at 5039-5076]                                        │ │   │
│  │  │     └→ verifier = CoachVerifier(self.worktree_path)                      │ │   │
│  │  │     └→ verifier._verify_files_exist(task_work_results)                   │ │   │
│  │  │          [coach_verification.py:231-257]                                 │ │   │
│  │  │          ╔═══════════════════════════════════════════════════════════╗   │ │   │
│  │  │          ║ for file_path in claimed_files:                          ║   │ │   │
│  │  │          ║     if not (worktree_path / file_path).exists():         ║   │ │   │
│  │  │          ║         Discrepancy(severity="critical", ...)            ║   │ │   │
│  │  │          ║                                                          ║   │ │   │
│  │  │          ║ For tasks/backlog/TASK-X-foo.md:                         ║   │ │   │
│  │  │          ║   exists() == False → critical discrepancy               ║   │ │   │
│  │  │          ║ For src/x.py, src/y.py, tests/test_x.py:                 ║   │ │   │
│  │  │          ║   exists() == True  → no discrepancy                     ║   │ │   │
│  │  │          ╚═══════════════════════════════════════════════════════════╝   │ │   │
│  │  │                                                                          │ │   │
│  │  │   honesty_issues = self._honesty_issues_from(honesty_verification)      │ │   │
│  │  │     [line 851; impl at 5078-5107]                                        │ │   │
│  │  │     └→ for d in discrepancies: if d.severity == "critical":              │ │   │
│  │  │           issue = {severity: "must_fix", category: "honesty", ...}       │ │   │
│  │  │                                                                          │ │   │
│  │  │   if honesty_issues:  ★ SHORT-CIRCUIT FIRES — 16 ACs DROPPED ★           │ │   │
│  │  │     [line 852-872]                                                       │ │   │
│  │  │     return CoachValidationResult(                                        │ │   │
│  │  │         decision="feedback",                                             │ │   │
│  │  │         quality_gates=None,                                              │ │   │
│  │  │         independent_tests=None,                                          │ │   │
│  │  │         requirements=None,                                               │ │   │
│  │  │         issues=honesty_issues,                                           │ │   │
│  │  │         rationale="...Adversarial verification overrode gate eval...",  │ │   │
│  │  │     )                                                                    │ │   │
│  │  └──────────────────────────────────────────────────────────────────────────┘ │   │
│  └────────────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

**Boundary crossings, summarised:**

| Boundary | Component A | Component B | What flows | Validated? |
|---|---|---|---|---|
| Time T0→T1 | `_record_baseline` | state_bridge | git baseline SHA precedes filesystem mutation | ✓ code |
| Filesystem | state_bridge | git CLI | shutil.move; git observes as unstaged delete + untracked add | ✓ code + git semantics |
| Process | parent orchestrator | SDK subprocess (Player) | task spec read after move; inner agent never sees pre-move path | ✓ code |
| Subprocess | parent orchestrator | git CLI | text output from `git diff --name-only`; lumps deletes with modifies | ✓ code + git semantics |
| In-process | union-merge at line 2797 | `report["files_modified"]` | orchestrator-induced ghost path appears alongside Player-real paths | ✓ code |
| In-process | `report["files_modified"]` | CoachVerifier | path strings checked one-by-one with `Path.exists()`; first failure → critical | ✓ code |
| Decision | CoachValidator | turn outcome | first critical honesty issue short-circuits 16 ACs | ✓ code + Coach JSON |

Every link is verified against running code. There is no inferred or assumed link.

---

## 3. Sequence diagram — current behaviour (false-fail reproducer)

```
participant ORCH as AutoBuildOrchestrator
participant INV as AgentInvoker
participant SB as TaskStateBridge
participant FS as Worktree filesystem
participant GIT as git CLI (subprocess)
participant SDK as inner Player SDK (subprocess)
participant TWR as task_work_results.json
participant PR as player_turn_N.json
participant CV as CoachValidator
participant VER as CoachVerifier
participant FS2 as Worktree filesystem
participant CT as coach_turn_N.json

note over ORCH,INV: T0 — record baseline
ORCH->>INV: invoke_player(TASK-FFC3-005, turn=1)
INV->>GIT: git rev-parse HEAD
GIT-->>INV: <baseline_sha>
INV->>INV: self._baseline_commit = <baseline_sha>
note right of INV: Baseline now contains:\n  tasks/backlog/TASK-FFC3-005-*.md (tracked)

note over ORCH,SB: T1 — state_bridge mutates filesystem
INV->>SB: ensure_design_approved_state()
SB->>FS: read tasks/backlog/TASK-FFC3-005-*.md
SB->>FS: write frontmatter status:design_approved
SB->>FS: shutil.move(backlog/.../X.md, design_approved/.../X.md)
note right of FS: AFTER MOVE:\n  tasks/backlog/TASK-FFC3-005-*.md  ← gone\n  tasks/design_approved/TASK-FFC3-005-*.md  ← present (untracked)

note over ORCH,SDK: T2 — Player runs in worktree (post-move)
INV->>SDK: spawn task-work --implement-only
SDK->>FS: Read tasks/design_approved/TASK-FFC3-005-*.md   [post-move path]
SDK->>FS: Edit src/specialist_agent/comparison/verdict.py
SDK->>FS: Edit src/specialist_agent/comparison/report.py
SDK->>FS: Write tests/test_ffc3_005_verdict_report.py
SDK->>FS: run pytest → 26 passed
SDK->>TWR: write {files_modified: [verdict.py, report.py, ...],\n              completion_promises: [...]}\nNote: tasks/backlog/...md NOT in this list
SDK-->>INV: SDK done (exit 0)

note over INV,GIT: T3 — orchestrator post-turn enrichment
INV->>TWR: read task_work_results.json
INV->>INV: report["files_modified"] = [verdict.py, report.py, ...]
INV->>GIT: git diff --name-only <baseline>
GIT-->>INV: stdout = "tasks/backlog/TASK-FFC3-005-*.md\nverdict.py\nreport.py\n..."
note right of INV: ★ Ghost path injected by git's view\n   of state_bridge's shutil.move
INV->>GIT: git ls-files --others --exclude-standard
GIT-->>INV: stdout = "tasks/design_approved/TASK-FFC3-005-*.md\ntests/test_ffc3_005_*.py"
INV->>INV: report["files_modified"] = sorted(\n    Player-claim ∪ git_modified\n)\n# Now contains tasks/backlog/...md
INV->>PR: write player_turn_1.json

note over CV,FS2: T4 — Coach honesty verification
ORCH->>CV: validate(task, task_work_results, turn=1)
CV->>VER: _verify_files_exist(report)
loop for each path in files_modified
    VER->>FS2: Path(worktree / path).exists()
end
note right of FS2: tasks/backlog/TASK-FFC3-005-*.md → False  ★ CRITICAL\nverdict.py → True\nreport.py → True\n... (15 others True)
VER-->>CV: discrepancies=[Discrepancy(file_existence, critical, "tasks/backlog/...")]

CV->>CV: _honesty_issues_from(verification)\n→ [{severity:must_fix, category:honesty, ...}]
CV->>CV: SHORT-CIRCUIT — return CoachValidationResult(\n    decision="feedback",\n    quality_gates=None,           ★ never evaluated\n    independent_tests=None,       ★ never evaluated\n    requirements=None,            ★ never evaluated\n    issues=honesty_issues\n)
CV->>CT: write coach_turn_1.json
note right of CT: criteria_verification: []                        ← 16 ACs unchecked\nacceptance_criteria_verification: {criteria_results: []}\nrationale: "1 honesty discrepancy/discrepancies. Adversarial verification overrode gate evaluation."
```

The **load-bearing bug** in this diagram is at `T3`: the union-merge unconditionally injects orchestrator-induced ghost paths into the Player's file-list, then asks CoachVerifier to validate that list as if it were Player work.

---

## 4. Sequence diagram — counter-factual: each layer's effect

### 4.1 Layer 1 alone (canonical-path resolution in CoachVerifier)

```
participant INV as AgentInvoker
participant CV as CoachValidator
participant VER as CoachVerifier (Layer 1 patched)
participant SB as TaskStateBridge

note over INV: T3 — same as before; ghost path still in report["files_modified"]

ORCH->>CV: validate(task, task_work_results, turn=1)
CV->>VER: _verify_files_exist(report, task_id="TASK-FFC3-005",\n                       state_bridge=SB)

loop for each path in files_modified
    VER->>FS2: Path(worktree / path).exists()
    alt exists
        note over VER: no discrepancy
    else does not exist
        VER->>SB: canonical_path_for("TASK-FFC3-005")
        SB-->>VER: tasks/design_approved/TASK-FFC3-005-*.md
        VER->>FS2: Path(worktree / canonical).exists()
        alt canonical exists
            note over VER: SUPPRESS — ghost path resolved\nrecord on resolved_paths[]
        else canonical also missing
            note over VER: keep critical discrepancy
        end
    end
end

VER-->>CV: HonestyVerification(verified=True, resolved_paths=[\n    {claimed: "tasks/backlog/...", resolved_to: "tasks/design_approved/..."}\n])

CV->>CV: _honesty_issues_from(verification) → []
CV->>CV: NO short-circuit → proceed to gates
CV->>CV: run_independent_tests, evaluate 16 ACs, etc.
CV->>CT: write coach_turn_1.json with full evaluation
```

**Property guarantees of Layer 1:**
- **Identity-bounded resolution**: only the validated task's canonical path is consulted. A claim referencing some other task's path won't be resolved.
- **Existence-gated**: resolution only succeeds when canonical path actually exists; genuine missing files still produce critical discrepancies.
- **Auditable**: every resolution recorded under `HonestyVerification.resolved_paths` and serialised to `coach_turn_N.json`. Reviewers can grep `resolved_paths` post-hoc.
- **Backwards-compatible fallback**: when state_bridge injection is missing or returns None, current exact-match behaviour preserved.

### 4.2 Layer 2 alone (don't short-circuit on single discrepancy)

```
participant CV as CoachValidator (Layer 2 patched)

VER-->>CV: HonestyVerification(\n    discrepancies=[Discrepancy(file_existence, critical, ...)],\n    verified=False\n)

CV->>CV: classify discrepancies\n  if all critical are file_existence and count == 1:\n      severity = "should_fix"\n  else:\n      severity = "must_fix"

CV->>CV: SHORT-CIRCUIT GUARD:\n  if any issue.severity == "must_fix":\n      return feedback\n  else:\n      proceed

note over CV: With single file_existence discrepancy:\n  severity="should_fix" → no must_fix issues\n  → no short-circuit → 16 ACs evaluated\n  → honesty issue still surfaces in feedback as "should_fix"
```

**Property guarantees of Layer 2:**
- Single `file_existence` discrepancy: demoted to `should_fix`, gates run, AC verification runs, honesty issue still visible in feedback for next turn.
- **Adversarial property preserved for sophisticated lies**: `promise_file_existence` (FEAT-6CC5 case), `test_result`, `test_count`, and any case with count > 1 retain `must_fix` and short-circuit.
- **Pattern detection preserved**: multiple file_existence discrepancies are pattern, not accident → must_fix.

### 4.3 Layer 3' (REVISED) — filter state-bridge-induced paths at union-merge

```
participant INV as AgentInvoker (Layer 3' patched)
participant SB as TaskStateBridge

note over INV,SB: T1 — state_bridge records its mutation

INV->>SB: ensure_design_approved_state()
SB->>SB: track move: pre="tasks/backlog/.../X.md",\n           post="tasks/design_approved/.../X.md"
SB->>SB: persist to .guardkit/autobuild/TASK-XXX/state_transitions.json

note over INV: T3 — union-merge filters orchestrator-induced paths

INV->>GIT: git diff --name-only <baseline>
GIT-->>INV: stdout = "tasks/backlog/...\nverdict.py\nreport.py\n..."
INV->>SB: orchestrator_induced_paths_for(task_id)
SB-->>INV: {"tasks/backlog/.../X.md"}  # paths state_bridge mutated this turn
INV->>INV: git_modified = git_modified - orchestrator_induced_paths
INV->>INV: report["files_modified"] = sorted(\n    Player-claim ∪ git_modified\n)
note right of INV: Ghost path filtered out — never reaches Coach
```

**Property guarantees of Layer 3':**
- **Targeted at correct component**: paths are filtered at the source of injection (`agent_invoker.py:2796-2797`), not after they've propagated to Coach.
- **Auditable**: state_transitions.json provides a forensic trail of every orchestrator-induced filesystem mutation.
- **Defence-in-depth**: even if Layer 1 fails for some edge case, Layer 3' prevents the ghost path from reaching CoachVerifier in the first place.

**Why v1's Layer 3 was wrong**: v1 proposed injecting the post-move canonical path into the Player's prompt context so the Player would quote the correct path. **But the Player never put `tasks/backlog/...` in `files_modified`** — the orchestrator's union-merge did. Changing the Player's prompt would not affect the union-merge's output. v1's Layer 3 would have been a no-op against FFC3.

### 4.4 Combined effect (Layers 1 + 2 + 3' applied)

```
participant INV as AgentInvoker (3' patched)
participant CV as CoachValidator (2 patched)
participant VER as CoachVerifier (1 patched)

INV->>INV: union-merge filters out tasks/backlog/...  [Layer 3']
INV->>INV: report["files_modified"] = [verdict.py, report.py, ...]
INV->>PR: write player_turn_1.json

CV->>VER: _verify_files_exist(...)
VER->>FS2: Path.exists() for each entry
VER-->>CV: HonestyVerification(verified=True, discrepancies=[])  [Layer 1 unused — nothing to resolve]

CV->>CV: 0 discrepancies → no must_fix → no short-circuit  [Layer 2 unused — gate runs naturally]
CV->>CV: run_independent_tests, evaluate 16 ACs, requirements
CV->>CT: write coach_turn_1.json (full evaluation)
```

**With all three layers**: Layer 3' prevents the ghost path. Layer 1 is the safety net if 3' misses an edge case. Layer 2 is the safety net if Layer 1 misses an edge case. Defence in depth across three independent components.

---

## 5. AC-by-AC findings (revised)

### AC-1 — Short-circuit call site

**Confirmed unchanged from v1.** [`coach_validator.py:850-872`](../../guardkit/orchestrator/quality_gates/coach_validator.py).

```python
honesty_verification = self._verify_honesty(task_work_results)
honesty_issues = self._honesty_issues_from(honesty_verification)
if honesty_issues:
    logger.warning(...)
    return CoachValidationResult(
        decision="feedback",
        quality_gates=None, independent_tests=None, requirements=None,
        issues=honesty_issues,
        rationale=f"{len(honesty_issues)} honesty discrepancy/discrepancies. "
                  f"Adversarial verification overrode gate evaluation.",
        ...
    )
```

The position (1.4 in the validator's gate sequence) is deliberate per the inline comment at lines 829-849. The branching condition (`if honesty_issues:`) is the over-eager part.

### AC-2 — Path-string equality logic

**Confirmed unchanged from v1.** [`coach_verification.py:231-257`](../../guardkit/orchestrator/coach_verification.py).

**v2 adds**: `_verify_files_exist` iterates the lists `["files_created", "files_modified", "tests_written"]`. The naive `worktree_path / file_path` exists() check has no awareness that `files_modified` may contain orchestrator-injected paths (see AC-3 expansion below).

### AC-3 — `state_bridge.canonical_path_for(task_id)` lookup

**Confirmed unchanged from v1.** Internal lookup exists at [`state_bridge.py:287-316`](../../guardkit/tasks/state_bridge.py); public surface is missing; ~5-line addition exposes it.

**v2 expands AC-3 with a sibling finding (F4'): the union-merge injection point.**

The `tasks/backlog/...` path enters `report["files_modified"]` at [`agent_invoker.py:2796-2797`](../../guardkit/orchestrator/agent_invoker.py):

```python
report["files_modified"] = sorted(list(original_modified | git_modified))
```

…where `git_modified` comes from `git diff --name-only <baseline>` ([line 3082-3092](../../guardkit/orchestrator/agent_invoker.py)) and the baseline was captured at [line 1391-1392](../../guardkit/orchestrator/agent_invoker.py) — **before** state_bridge mutated the filesystem. The ghost path is the orchestrator's own observation of its own state-machine mutation, attributed to the Player.

This is a separate component from the honesty verifier and admits a separate, additive fix (Layer 3'). It is the **best place to stop the ghost path from existing in the first place**, before any Coach-side logic ever sees it.

### AC-4 — Relationship to `absence-of-failure-is-not-success`

**Confirmed unchanged from v1.** Inverse-shape sibling rule warranted. v2 adds: the meta-frame extends not only to honesty oracles but to any orchestrator pipeline where an in-process side effect is observed by a downstream component as if it were upstream work. The union-merge bug is itself an instance of this meta-frame (the orchestrator's own state-bridge move is observed by `_detect_git_changes` as Player work).

### AC-5 — Layer 2 separability

**Confirmed unchanged from v1.** Layer 2 is separable. Wave 2 placement preserved.

### AC-6 — Implementation task breakdown (revised)

Five follow-on tasks (was four). Layer 3 reframed; new TASK-DOC entry for the rule sibling unchanged.

#### TASK-FIX-1B452-A — Layer 1 (load-bearing) — ~3 hours, Wave 1

**Title**: Resolve `files_modified` claims through state-bridge canonical path before honesty verification

(unchanged from v1; full spec preserved)

**Files modified**: `guardkit/tasks/state_bridge.py` (+~5), `guardkit/orchestrator/coach_verification.py` (+~20), `guardkit/orchestrator/quality_gates/coach_validator.py` (~5).

**ACs**: AC-A1..AC-A5 from v1.

**Tests**: new module `tests/unit/test_coach_verification_state_bridge.py`.

**Parallelisation**: independent. Wave 1.

#### TASK-FIX-1B452-B — Layer 2 (robustness) — ~2 hours, Wave 2 (depends on A)

**Title**: Demote single path-only honesty discrepancies from `must_fix` to `should_fix` so gate evaluation continues

(unchanged from v1; full spec preserved)

**ACs**: AC-B1..AC-B5 from v1.

**Tests**: extend `tests/unit/test_coach_validator.py`.

**Parallelisation**: depends on Layer 1 fixture changes. Wave 2.

#### TASK-FIX-1B452-C' — Layer 3' (REVISED preventative) — ~3 hours, Wave 1 (parallel with A)

**Title**: Filter orchestrator-induced state-bridge moves out of post-turn git enrichment

**Replaces v1's TASK-FIX-1B452-C** (Player prompt injection — wrong target, would not have fixed FFC3).

**Files modified**:
- `guardkit/tasks/state_bridge.py` (+~25 lines): track moves performed during a turn (in-memory list of `(task_id, pre_path, post_path, timestamp)` tuples) and persist on each move to `.guardkit/autobuild/{task_id}/state_transitions.json`. Add public method `orchestrator_induced_paths_for(task_id) -> Set[str]` returning the set of pre-move paths recorded for that task.
- `guardkit/orchestrator/agent_invoker.py` (+~15 lines): in `_create_player_report_from_task_work` after the union-merge at line 2796-2797, subtract `state_bridge.orchestrator_induced_paths_for(task_id)` from `report["files_modified"]`. Log how many ghost paths were filtered for observability.

**ACs**:
- AC-C1: state_bridge persists every `shutil.move` to `state_transitions.json` keyed by task_id, with pre_path, post_path, and ISO timestamp.
- AC-C2: `orchestrator_induced_paths_for(task_id)` returns the set of pre-move paths for the task, or empty set if no transitions recorded.
- AC-C3: `_create_player_report_from_task_work` filters orchestrator-induced paths from `report["files_modified"]` before writing player_turn_N.json.
- AC-C4: Observability — logger emits `"Filtered N orchestrator-induced ghost path(s) from {task_id} files_modified"` when the filter fires.
- AC-C5: Backwards-compat — when no `state_transitions.json` exists (e.g., older turns, missing fixture), filter is a no-op.

**Tests**: new module `tests/unit/test_orchestrator_induced_path_filter.py`.
- Test: state_bridge.transition_to_design_approved persists transition entry.
- Test: union-merge filters out the persisted pre-move path.
- Test: missing state_transitions.json → no-op (no exception, no filter).
- Test: multiple state_bridge moves in same turn → all pre-paths filtered.

**Parallelisation**: independent of Layer 1 in code (touches `agent_invoker.py` and `state_bridge.py`, not `coach_*`). Wave 1, parallel to A. **Defence-in-depth — both A and C' should ship; C' alone closes the FFC3 reproducer; A alone also closes it; together they close it under broader edge cases.**

**Why both C' and A**: C' targets the symptom at the orchestrator boundary; A targets the broader class of "Path.exists() should consult task identity, not raw string". Both are small, independently testable, additive. Shipping both gives the orchestrator two independent guards against the same class of false-fail.

#### TASK-FIX-1B452-D — Manual-recovery hazard — ~2 hours, **deferred** (don't build until Layer 1+2+3' land)

(unchanged from v1)

#### TASK-DOC-1B452 — Sibling rule + Graphiti node — ~30 min, Wave 3 (after Layer 1+3' land)

(unchanged from v1)

### AC-7 — Regression test shape (revised)

**Two test surfaces** instead of v1's one:

**Surface 1**: `tests/unit/test_coach_verification_state_bridge.py` — Layer 1 honesty resolution. (Same as v1's spec.)

**Surface 2 (new)**: `tests/unit/test_orchestrator_induced_path_filter.py` — Layer 3' union-merge filter. Shape:

```python
def test_state_bridge_move_filtered_from_files_modified(tmp_path):
    # Arrange: real worktree, real state_bridge, real git
    worktree = init_test_worktree(tmp_path)
    backlog_path = worktree / "tasks" / "backlog" / "TASK-X-foo.md"
    backlog_path.write_text("---\nid: TASK-X\nstatus: backlog\n---\n# Task")
    subprocess.run(["git", "add", "-A"], cwd=worktree, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=worktree, check=True)

    # Simulate orchestrator: record baseline, then state_bridge moves the file
    invoker = AgentInvoker(worktree_path=worktree)
    invoker._record_baseline()

    bridge = TaskStateBridge("TASK-X", worktree, in_autobuild_context=True)
    bridge.ensure_design_approved_state()
    # bridge writes state_transitions.json now

    # Sanity check: git would show the ghost path
    git_changes = invoker._detect_git_changes()
    assert "tasks/backlog/TASK-X-foo.md" in git_changes["modified"]

    # Act: simulate union-merge with Player-honest report
    task_work_data = {"files_modified": ["src/x.py"]}
    # ... write task_work_results.json ...

    invoker._create_player_report_from_task_work("TASK-X", 1, task_work_result)

    # Assert: Player report has src/x.py but NOT tasks/backlog/...
    player_report = json.loads(player_turn_path.read_text())
    assert "src/x.py" in player_report["files_modified"]
    assert "tasks/backlog/TASK-X-foo.md" not in player_report["files_modified"]
```

**End-to-end Coach test** (`tests/unit/test_coach_validator.py`) — Layers 1+3' combined:

```python
def test_state_bridge_move_does_not_short_circuit_with_full_pipeline(tmp_path):
    # Build realistic fixture: worktree, baseline, state_bridge move, Player
    # output, run full _create_player_report_from_task_work, then CoachValidator.validate.
    # Assert: result.acceptance_criteria_verification.criteria_results has 16 entries
    # Assert: "Adversarial verification overrode" NOT in result.rationale
    # Assert: result.honesty_verification.resolved_paths is empty (3' filtered before A
    #         had to resolve) OR has the resolution recorded (depending on which layer
    #         lands first; either is acceptable).
```

### AC-8 — Risk assessment (revised)

#### Layer 1 risk: masking genuine Player honesty violations

(unchanged from v1; mitigation patterns preserved)

#### Layer 2 risk: weakening adversarial property

(unchanged from v1)

#### Layer 3' risk: filter scope creep

The new risk: state_bridge tracks more mutations over time (status flips, frontmatter rewrites, future autobuild-internal file moves). Each of those mutations could become a "filtered" path the orchestrator hides from the Coach. If state_bridge starts moving files for non-bookkeeping reasons (e.g., refactoring real source code), the filter would silently hide that mutation from the Coach's view.

**Mitigations**:
1. **Scope of the filter**: only `transition_to_design_approved`-induced moves are recorded for now. Other state_bridge methods do not write to state_transitions.json. The filter is narrow by construction.
2. **Audit trail**: state_transitions.json is preserved in `.guardkit/autobuild/{task_id}/`; reviewers can grep these post-mortem.
3. **Single allow-list**: only paths state_bridge moved are filtered. Any other path the orchestrator might mutate is still visible to git-detect, even if it shouldn't be.
4. **Test coverage**: AC-C5 (no-op when fixture missing) ensures fail-open behaviour.

Residual risk: a future contributor adds a new state_bridge method that mutates source code AND records to state_transitions.json. **Mitigation**: a future architectural review for state_bridge changes; for now, tightly bound the recording to `transition_to_design_approved`.

#### Sibling rule risk

None. Documentation-only.

### AC-9 — Manual-recovery hazard

(unchanged from v1)

---

## 6. Findings summary (revised)

| ID | Severity | Component | Description | v1→v2 |
|----|----------|-----------|-------------|-------|
| F1 | **must_fix** | `coach_validator.py:852-872` (short-circuit) + `coach_verification.py:240-256` (path-string equality) | Naive `worktree_path / claimed_path` exists() check, no identity resolution, raises critical discrepancy on every state-bridge move. Short-circuit then drops 16 ACs. **Load-bearing.** | unchanged |
| F2 | **should_fix** | `coach_validator.py:850-872` (short-circuit semantics) | Single path-only discrepancy short-circuits the gate even when production code on disk is otherwise consistent. Should be demoted to `should_fix`. **Robustness.** | unchanged |
| F3' | **must_fix** | `agent_invoker.py:2796-2797` (union-merge) + `state_bridge.py` (no transition tracking) | Orchestrator's post-turn `git diff --name-only` reports state-bridge `shutil.move` as a tracked-file delete; union-merge injects this orchestrator-induced ghost path into `files_modified` and attributes it to the Player. **Source of injection.** | NEW (replaces v1's Layer-3 misdiagnosis) |
| F4 | **info** | `state_bridge.py` (lookup data) | Lookup mechanism exists internally; public surface missing. **Mechanical.** | unchanged |
| F5 | **must_fix (doc)** | `.claude/rules/` (rule-base) | No sibling rule for false-red shape. | unchanged |
| F6 | **info** | YAML-flip workaround | Manual recovery bypasses Coach audit trail. | unchanged |

---

## 7. Recommendations (revised)

1. **R1 (load-bearing)** — TASK-FIX-1B452-A (Layer 1, ~3h, Wave 1).
2. **R2 (robustness)** — TASK-FIX-1B452-B (Layer 2, ~2h, Wave 2; depends on A).
3. **R3' (REVISED preventative)** — TASK-FIX-1B452-C' (Layer 3', ~3h, Wave 1, parallel with A). **Replaces v1's R3.** Filters orchestrator-induced ghost paths at the union-merge.
4. **R4 (documentation)** — TASK-DOC-1B452 (sibling rule + Graphiti node, ~30min, Wave 3, after R1+R3' land).
5. **R5 (deferred)** — Defer TASK-FIX-1B452-D. Reassess after R1+R2+R3' land.
6. **R6 (operational)** — Document the FFC3 reproduction and the three-decision collision in `docs/guides/autobuild-instrumentation-guide.md`. The collision pattern itself is worth a sub-section (state_bridge + git-enrichment + honesty-check) so future autobuild changes recognise the shape.
7. **R7 (separate triage)** — Bug 2 (`_record_honesty()` NoneType) and Bug 3 (`--resume` worktree-recreation) need their own review tasks. Architecturally disjoint from this review's findings.

**Wave-1 ship criteria for unblocking development**: R1 (Layer 1) and R3' (Layer 3') in parallel, both must land before next autobuild attempt. Layer 2 (R2) is fast-follow but not load-bearing. Together R1+R3' provide defence-in-depth: R3' filters the ghost at source, R1 catches it if the filter ever misses.

---

## 8. Decision checkpoint inputs (revised)

- **Architectural score**: **64/100** (raised from v1's 62 because v2 has a higher-confidence root cause and a better-targeted Layer 3'. Below 70 because the test-coverage gap that admitted this regression — no test exercises the post-baseline state_bridge interaction — is still a real architectural-test gap, only partially closed by Layers 1 and 3').
- **Findings**: 6 (F1, F2, F3', F4, F5, F6).
- **Recommendations**: 7 (R1-R7).
- **Recommended next step**: `[I]mplement` → creates TASK-FIX-1B452-A (Wave 1), TASK-FIX-1B452-C' (Wave 1, parallel), TASK-FIX-1B452-B (Wave 2 depends on A), TASK-DOC-1B452 (Wave 3 depends on A+C'). Defer TASK-FIX-1B452-D. File TASK-REV tasks for Bugs 2 and 3 separately.

---

## Appendix A — Verified file:line citations (revised)

| Component | Path | Line(s) |
|-----------|------|---------|
| `_record_baseline` (T0 timing) | `guardkit/orchestrator/agent_invoker.py` | 1389-1392, 3035-3060 |
| `_ensure_design_approved_state` (T1 timing) | `guardkit/orchestrator/agent_invoker.py` | 1438, 5464-5505 |
| state_bridge invoked with worktree_path | `guardkit/orchestrator/agent_invoker.py` | 5491-5495 |
| `transition_to_design_approved` (the move) | `guardkit/tasks/state_bridge.py` | 158-201 |
| `_move_task_to_state` using `shutil.move` (no git mv) | `guardkit/tasks/state_bridge.py` | 486-528 |
| `_detect_git_changes` (`git diff --name-only` no `-M`) | `guardkit/orchestrator/agent_invoker.py` | 3062-3112 |
| union-merge with git changes | `guardkit/orchestrator/agent_invoker.py` | 2785-2825 |
| `_create_player_report_from_task_work` (full T3 method) | `guardkit/orchestrator/agent_invoker.py` | 2680-2826 |
| Honesty short-circuit | `guardkit/orchestrator/quality_gates/coach_validator.py` | 850-872 |
| `_verify_honesty` (CoachVerifier wiring) | `guardkit/orchestrator/quality_gates/coach_validator.py` | 5039-5076 |
| `_honesty_issues_from` (must_fix translation) | `guardkit/orchestrator/quality_gates/coach_validator.py` | 5078-5107 |
| Path-string equality check | `guardkit/orchestrator/coach_verification.py` | 240-256 |
| `_verify_files_exist` declaration | `guardkit/orchestrator/coach_verification.py` | 231-257 |
| `_verify_completion_promises_files_exist` (FEAT-6CC5 case) | `guardkit/orchestrator/coach_verification.py` | 259-305 |
| Internal canonical-path lookup | `guardkit/tasks/state_bridge.py` | 287-316 |
| Prior-art rule | `.claude/rules/absence-of-failure-is-not-success.md` | (whole) |

## Appendix B — Cross-references (unchanged)

- **TASK-AB-FIX-INVAB1** (commit `b9a45694`, 2026-05-06): wired CoachVerifier into deterministic Coach path. Necessary; activated this latent collision. No fault attaches.
- **TASK-REV-0414** (2025-12-30): Option D delegation pattern. Origin of CoachValidator.
- **`.claude/rules/absence-of-failure-is-not-success.md`**: prior-art for false-green direction.
- **TASK-INV-AB1 review report** (`.claude/reviews/TASK-INV-AB1-review-report.md`): provided the C4 + sequence-diagram framing this review extends.
- **TASK-FIX-VL06**: introduced per-task baselines that this review's F3' analysis depends on (the baseline-before-state-bridge timing is correct for parallel-wave attribution; the bug isn't in baseline timing but in the union-merge attributing orchestrator mutations to the Player).

## Appendix C — What v1 got wrong, recorded for posterity

v1 stated: *"the Player's self-report path was sourced from the task spec it read at turn start, which still contained `tasks/backlog/...` references"*. This was a plausible inference but wrong. Three corrections:

1. **The Player reads the post-move file** (state_bridge runs at T1, before SDK at T2). The Player has no view of `tasks/backlog/...` — that file is gone before the Player exists.
2. **The inner SDK's TaskWorkStreamParser tracks Edit/Write tool calls only** (`agent_invoker.py:587-596`). The Player doesn't Edit the task spec, so its view of `files_modified` does not contain the spec path.
3. **The orchestrator-side union-merge is the injection point**. Without union-merge with `_detect_git_changes`, the ghost path would not exist in the Player report.

The v1 Layer 3 (inject canonical path into Player prompt) targeted a non-existent problem and would not have fixed FFC3. The v2 Layer 3' (filter at union-merge) targets the actual injection site.

This is a useful negative result to preserve: future review tasks should explicitly trace **every component that writes to a field**, not just the components that read from it. The honesty verifier reads `files_modified`; v1 only traced who *might* have written it. v2 traced who *actually* wrote it, and the answer was different.
