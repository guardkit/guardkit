# Review Report: TASK-REV-HM09

> **Subject**: Pre-loop harness bypass (F1) + worktree-manager cwd-branch gap (F4) surfaced by TASK-HMIG-009 pilot.
> **Mode**: architectural + decision (focused depth).
> **Reviewer**: Claude Opus 4.7, session 2026-05-27.
> **Parent**: [TASK-REV-HMIG](TASK-REV-HMIG-review-report.md) §§4, 5.3, 5.4, 7.3, 11.
> **Inputs**: [`docs/state/TASK-REV-HMIG/canary-analysis.md`](../../docs/state/TASK-REV-HMIG/canary-analysis.md) §§3 + 5; pilot smoke artefacts v1–v7.

---

## ✅ Success — v3.2 (2026-06-03, end of day) — AC-001D PASSED on LangGraph; cutover viable

**The full 6-layer LangGraph integration is fixed.** AC-001D run 6 (2026-06-03 15:08-15:21) reached **APPROVED in 1 turn** on `qwen36-workhorse` via the LangGraph harness, with metrics comparable to or better than the SDK baseline.

**SDK vs LangGraph parity** (TASK-FIX-A7D3 single-task canary):

| Metric | SDK (AC-001C, 2026-06-02) | LangGraph (AC-001D run 6, 2026-06-03) |
|---|---|---|
| Decision | APPROVED | APPROVED |
| Turns | 1 | 1 |
| Files created/modified | 3 / 16 | 4 / 16 |
| Tests passing | 1 | 2 |
| Honesty score | 1.00 | 0.96 |
| Player wall-clock | 500s / 40 turns | 341s / 34 turns |
| Coach wall-clock | 287s | **90s** (3× faster) |
| **Total wall-clock** | ~21 min | **~13.5 min** (~35% faster) |

**Full 6-run iteration journey** — each run unblocked exactly one layer:

| Run | Date | Symptom | Fix (location, who) |
|---|---|---|---|
| 1 | 2026-06-02 | `model=None: 'function' object has no attribute 'name'` | TASK-FIX-MODELPLUMB (guardkit) ✅ |
| 2 | 2026-06-03 | Same error with `model='openai:qwen36-workhorse'`; `tools=[strings]` crash in ToolNode | TASK-FIX-LGTOOLS (guardkitfactory) ✅ |
| 3 | 2026-06-03 | `backend=None` (factories existed but unused) | TASK-FIX-002R-CONSUME (guardkit selector wiring) ✅ |
| 4 | 2026-06-03 | `_PermissionMiddleware does not yet support backends with command execution` | TASK-HMIG-002R-NOPERMS (guardkitfactory) ✅ |
| 5 | 2026-06-03 | `virtual_mode=True` rewrote absolute paths into worktree-nested twins | TASK-HMIG-002R-NOVMODE (guardkitfactory) ✅ |
| **6** | **2026-06-03** | **none — predicted 6th layer dissolved** | TASK-HMIG-002R-PROMPT closed without code (DeepAgents runtime tool advertisement sufficed) |

**The "each fix reveals exactly one more layer" pattern broke at run 6** — meaningful signal that the integration is now properly aligned end-to-end. Remaining risk is variance across the 12-run batch (different task complexities, edge cases A7D3 didn't exercise), not a known-unknown layer.

**Three quality signals worth tracking across the AC-003 12-run batch**:

1. **LLM Coach overrides honesty oracle's must-fix flag** (run 6 line 194 + 218: `gather_evidence: honesty produced 1 must_fix issue(s) for TASK-FIX-A7D3; downstream gathering skipped` → final honesty 0.96 → Coach approved). The LLM Coach has override authority per TASK-HMIG-008R; the question is whether this is per-run noise or a systematic pattern. Track frequency across the batch + compare SDK vs LangGraph.
2. **`Criteria Progress 0/1 verified (0%)` with Coach approval** (line 219+221). LLM-Coach-as-fallback shape; consistent with AC-001C SDK behaviour. Track per-run; expected to be invariant across harness choice.
3. **One `/v1/responses` retry** (line 196). Transient under qwen36-workhorse. Track; if >2 of 12 runs retry, brief look at vLLM queue depth warranted.

**Cutover-deadline impact** vs §8 decision brief: **Path 2 (Partial close) recommended path is now fully viable.** Critical remaining work is AC-003 (~10h GB10 compute) + aggregate + TASK-HMIG-010 cutover decision against 2026-06-15. Comfortable margin.

**Cleanup applied 2026-06-03 EOD** (coordinated with parallel guardkitfactory-side cleanup):
- TASK-HMIG-009A status `blocked` → `backlog`; AC-001D marked ✅
- TASK-HMIG-002R-PROMPT **deleted** (closing criterion satisfied by run 6)
- README + IMPLEMENTATION-GUIDE subtask tables updated
- guardkitfactory side (operator-tracked): NOPERMS moved to `completed/`; NOVMODE filed + completed; PERMS-CUSTOM-MIDDLEWARE parked for post-cutover restoration

The SDK side (F1 + F4 + AC-001C) remains unchanged. v3 and v3.1 below preserved as historical record of the diagnostic journey.

---

## ⚠ Correction v3.1 (2026-06-03, later same day) — correction of v3's misdiagnosis

The v3 addendum below claimed AC-001D was blocked on TASK-HMIG-002R + TASK-HMIG-002R-PROMPT. **Operator caught a cross-repo coordination error**:

- **TASK-HMIG-002R has been COMPLETE in `../guardkitfactory/`** since 2026-05-20. The `build_autobuild_backend(worktree)` and `build_autobuild_permissions()` factories exist, are exported from `guardkitfactory.__init__`, and have integration tests covering the parent-review §7.1 Wave 1 falsifier dimensions. See [`../guardkitfactory/tasks/completed/TASK-HMIG-002R/`](../../../guardkitfactory/tasks/completed/TASK-HMIG-002R/).
- **The actual gap is consumer-side wiring in guardkit**: [`guardkit/orchestrator/harness/selector.py`](../../guardkit/orchestrator/harness/selector.py)'s `langgraph` branch constructs `LangGraphHarness(model=...)` without passing `backend=` or `permissions=`. The already-built factories sit unused.
- **Fix scope collapsed from 12h to ~1h**: filed as [TASK-FIX-002R-CONSUME](../../tasks/backlog/autobuild-harness-migration/TASK-FIX-002R-CONSUME-wire-guardkitfactory-backend-permissions-into-selector.md) — thread `cwd` through `select_harness`, call the existing factories. The v3-filed TASK-HMIG-002R in guardkit has been **deleted as a duplicate**. TASK-HMIG-002R-PROMPT marked **speculative** (`status: speculative`) — may not be needed once wiring lands; revisit after AC-001D re-run.

**Process gap to fix**: I filed cross-repo work without checking the other repo's state. Future cross-repo tasks should be preceded by `ls ../guardkitfactory/tasks/completed/` and a read of `../guardkitfactory/tasks/backlog/autobuild-harness-migration/README.md` (which has the explicit cross-repo task split table).

**Impact on §8 (decision brief) and cutover deadline**: dramatically improved. Critical path is now ~1h dev + AC-001D re-run + ~10h compute against the 12-day window. Comfortable margin. Option (a) "push and accept tight cutover" from the v3 contingency framing is now option (a) "push the 1h fix and ship on schedule."

The SDK side (F1 + F4 + AC-001C APPROVED) remains unchanged. The four-layer-discovery narrative in v3 below is correct in shape (Wave-2 layers exist) but the layer-3 fix is much smaller than v3 implied.

---

## ⚠ Correction v3 (2026-06-03) — LangGraph canary blocked on Wave-1 completion *(SUPERSEDED by v3.1 above)*

**AC-001D iteration surfaced that the LangGraph Wave-2 harness is a skeleton, not a working integration.** Three runs over 2 days exposed four distinct layers of the same root cause: the Wave-2 `LangGraphHarness` was unit-tested with mocks and `tools=[]` but never exercised end-to-end against a real Player/Coach prompt with real tools against a real model. Each fix unblocked one layer and revealed the next.

| Layer | Symptom | Diagnosis | Resolution |
|---|---|---|---|
| 1 | `LangGraphHarnessError: ... model=None: 'function' object has no attribute 'name'` | CLI `--model` never plumbed through to `select_harness(model=...)` | ✅ [TASK-FIX-MODELPLUMB](../../tasks/completed/2026-06/TASK-FIX-MODELPLUMB-thread-cli-model-through-harness.md) landed 2026-06-02 |
| 2 | Same error message but `model='openai:qwen36-workhorse'` | `tools=[strings]` shape crashes `langgraph.prebuilt.ToolNode.__init__` inside DeepAgents | ✅ [TASK-FIX-LGTOOLS](../../tasks/completed/2026-06/TASK-FIX-LGTOOLS-langgraph-harness-drop-sdk-tools.md) landed 2026-06-03 (guardkitfactory) |
| 3 | Coach + specialists run but produce no output; specialist burns 38.5min in /v1/responses loop; Coach fails with `Coach decision not found: coach_turn_1.json` | `backend=None`/`permissions=None` in LangGraphHarness → no real worktree access; AND Coach/specialist prompts use SDK tool names (`Read`/`Write`/`Bash`) but DeepAgents exposes different names (`read_file`/`write_file`/`execute`) | ⛔ [TASK-HMIG-002R](../../tasks/backlog/autobuild-harness-migration/TASK-HMIG-002R-configure-localshellbackend-and-permissions.md) (backend + permissions, 6h) + [TASK-HMIG-002R-PROMPT](../../tasks/backlog/autobuild-harness-migration/TASK-HMIG-002R-PROMPT-adapt-coach-specialist-prompts-to-deepagents-tool-surface.md) (prompt adaptation, 6h) — both filed 2026-06-03 |
| 4 (predicted) | After 002R lands but 002R-PROMPT still pending — Coach LLM may still produce nonsense due to prompt/tool mismatch | Same as layer 3 (prompt half) | Handled by 002R-PROMPT |

**Key finding**: TASK-HMIG-002R was **named in the parent review on 2026-05-19** (§7.1 Wave 1, line 1134 of this report) and referenced as a known gap in **9+ subsequent task files** — but **never filed as an actual task** until 2026-06-03. The Wave-2 dispatch refactor (TASK-HMIG-006) was treated as "harness migration complete" when really it was "harness *dispatch* complete; harness *backend* still skeleton." Future Wave-N completion claims should require both dispatch AND target-side integration tests, not just dispatch unit tests with mocks.

**Resolution applied 2026-06-03**:
1. Filed TASK-HMIG-002R per the parent review's §7.1 Wave 1 spec (6h).
2. Filed TASK-HMIG-002R-PROMPT as a companion (NEW from AC-001D run 3; not in parent review's scope) for the Coach/specialist prompt-adaptation problem. Estimated 6h.
3. TASK-HMIG-009A status changed to `blocked`. AC-001D marked blocked on both 002R + 002R-PROMPT.
4. README + IMPLEMENTATION-GUIDE updated with new dependency chain + collapsed timeline margin.

**Impact on §8 (decision brief) and cutover deadline**: Path 2 (partial close) is at risk. The pre-canary fixes landed but the LangGraph canary cannot produce signal until 002R + 002R-PROMPT close. Operator decision needed: (a) push 002R + 002R-PROMPT this week, accept tight cutover; (b) ship cutover on SDK-only canary signal; (c) defer cutover deadline. Per operator direction 2026-06-03: pursuing (a).

The SDK side of this review (F1 + F4 diagnoses, AC-001C SDK end-to-end PASSING APPROVED) is unchanged and remains valid.

---

## ⚠ Correction v2 (2026-06-02)

**The v1 correction below (2026-05-27) recommended reverting the canary to `qwen-coder-next`. That model was documented in operator state but not actually deployed on the live GB10 llama-swap.** TASK-HMIG-009A's preflight AC-001A caught this on 2026-05-27 (the cheap preflight design worked as intended — surfaced model-deployment drift before any compute was burned). After ~1 week of operator llama-swap reconfiguration work + benchmark/forum research, the operator selected **`qwen36-workhorse`** (Qwen3.6-35B-A3B) as the AutoBuild Player model — see [`docs/research/dgx-spark/gb10-memory-budget-and-macbook-offload.md:37`](../../docs/research/dgx-spark/gb10-memory-budget-and-macbook-offload.md#L37) (measured 2026-05-28): qwen36-workhorse serves `jarvis-reasoner, forge, autobuild, dataset-factory` as a shared workhorse, and NVIDIA developer-forum + benchmark evidence identifies it as the strongest agentic-coding model in the GB10's deployable range.

**Applied 2026-06-02**:

1. [canary-set.json](../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json) edited in-place — `model_choice_correction_v2` block added; harness models updated to `qwen36-workhorse` / `openai:qwen36-workhorse`; v1 `model_choice_correction` marked superseded; `preflight_findings.AC-001A_2026-05-27` blocker marked resolved-by-v2.
2. TASK-HMIG-009A unblocked (status: backlog); preflight ACs (001A–001D) reframed against `qwen36-workhorse`. AC-001B is the load-bearing post-reconfig gate (does the workhorse now emit well-formed `tool_use` blocks where smokes v2/v3 saw none pre-reconfig?). Expected pass per operator's benchmark + forum work.
3. README + IMPLEMENTATION-GUIDE updated.
4. Memory entries updated — the durable rule is now "**defer to operator on AutoBuild Player model selection; don't lock in a specific model name from documentation alone**." The current choice (qwen36-workhorse) may itself evolve as operator research continues.

**F2 reframe** (the meta-finding of this whole arc): F2 was *not* a parser-config defect, *not* a wrong-model-as-substitute, and not solvable by AI inference from docs. It was an evolving operator decision about model choice that took two corrections + ~1 week of focused infra work to settle. The right system response is: cheap preflights that catch drift, operator-driven decisions on model selection, AI maintaining the audit trail across revisions.

**Impact on §8 (decision brief)**: Path 2 remains the recommended approach. Critical path is now essentially complete: F1 fix landed (006.4 commit `f2c240a7`), F4 fix landed (WTBC in_review), model choice resolved (v2 swap applied). Remaining work is ~30min preflight + ~10h canary compute + cutover decision. Cutover margin against 2026-06-15: ~9 days. Comfortable.

The rest of this review (F1 + F4 diagnoses, recommended remediations, HMIG-009A/B split) is unchanged.

---

## ⚠ Correction v1 (2026-05-27, post-review — superseded by v2)

**§6 (AC-006) framed F2 as "audit llama-swap parser config for `qwen3-coder-30b` and `qwen36-workhorse`." That framing is wrong.** The operator's documented and empirically proven AutoBuild Player model is **Qwen3-Coder-Next** (already configured on llama-swap under alias `qwen-coder-next`; *"Current. Proven with AutoBuild"* per [`docs/research/dgx-spark/gb10-model-requirements-matrix.md:61`](../../docs/research/dgx-spark/gb10-model-requirements-matrix.md#L61)). The TASK-REV-HMIG pilot silently swapped this for `qwen3-coder-30b` post-2026-04-29 ([canary-set.json:21](../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json#L21)); the operator raised the model-choice question repeatedly during TASK-REV-HMIG execution and it was not actioned.

**Resolution applied 2026-05-27**:

1. The canary-set ([.guardkit/autobuild/TASK-REV-HMIG-canary-set.json](../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json)) was edited in-place to revert the model swap. Both harnesses now target `qwen-coder-next`. Audit trail preserved in the new `model_choice_correction` block.
2. **TASK-OPS-LSPC was deleted as a separate task.** The model-swap edit is done; end-to-end verification was folded into TASK-HMIG-009A's preflight ACs (001A–001D — direct endpoint smoke + one-rep smokes per harness, ~30min). Documentation + Graphiti capture folded into 009A's closing ACs (007–008).
3. **F2 is now treated as resolved-pending-empirical-confirmation**, with 009A's preflight serving as the empirical confirmation gate. If preflight fails (contradicting the operator's prior proof), the right diagnosis path is a parser-config audit against `qwen-coder-next` *specifically* — not the original framing's audit of the two wrong models.

**Impact on §8 (decision brief)**: Path 2 (Partial close) is now cheaper and faster than originally costed. F2 is no longer an open-ended operator-side infra blocker; it's a ~30min preflight in 009A. Cutover margin against 2026-06-15 widens from ~5 days to ~12 days.

The rest of this review (F1 + F4 diagnoses, recommended remediations, HMIG-009A/B split) is unchanged.

**Cross-references for the correction**:
- Feature folder: [tasks/backlog/hmig-pre-canary-fixes/](../../tasks/backlog/hmig-pre-canary-fixes/) — README + IMPLEMENTATION-GUIDE updated to reflect the 4-task list (TASK-OPS-LSPC removed).
- Operator-preference memory: `~/.claude/projects/.../memory/feedback_autobuild_player_model.md` — default to Qwen3-Coder-Next for any AutoBuild Player work.
- Incident memory: `~/.claude/projects/.../memory/project_canary_model_swap_incident_2026_05.md` — non-recurrence target.

---

## 0. Executive verdict

**Both F1 and F4 are real bugs, both are cheap to fix, both should land before the 2026-06-15 Wave-4 cutover.** The HMIG-006 completion claim is partially contested by F1 — the harness adapter covers ~25% of an `autobuild task` invocation's wall-clock; the pre-loop's ~60–90 minutes silently bypass it. F4 is an unambiguous omission in `WorktreeManager.create()` whose blast radius extends beyond TASK-HMIG-009 to `guardkit autobuild feature` and any caller running autobuild from a non-main branch.

**Recommended path**: file TASK-HMIG-006.4 (F1 fix) + TASK-FIX-WTBC (F4 fix), split TASK-HMIG-009 into 009A (partial-canary, runs immediately after the two fixes land) + 009B (full canary, runs after F2's operator-side fix). Ship the cutover with F2 as a documented limitation if 009A's signal is acceptable.

**Cost**: ~10h focused dev + ~10h GB10 canary compute for 009A. **Margin against 2026-06-15**: comfortable if started by 2026-05-30.

---

## 1. AC-001 — F1 dispatch chain diagnosis

### Confirmed: pre-loop does NOT consult `select_harness()`

The dispatch chain from `autobuild task --pre-loop` to the SDK subprocess is:

```
cli/autobuild.py:task()                                     # CLI entry
  └─ AutoBuildOrchestrator.orchestrate(task_id, ...)        # orchestrator/autobuild.py:1177
      └─ AutoBuildOrchestrator._pre_loop_phase(task_id, worktree)  # orchestrator/autobuild.py:1286
          └─ TaskWorkInterface.execute_design_phase(task_id, options)  # orchestrator/quality_gates/task_work_interface.py:138
              └─ TaskWorkInterface._execute_via_sdk(prompt)            # task_work_interface.py:407
                  └─ from claude_agent_sdk import (query, ...)         # task_work_interface.py:438-450 ← HARD-CODED
                      └─ query(prompt=prompt, options=ClaudeAgentOptions(...))  # task_work_interface.py:485
                          └─ claude_agent_sdk._internal.transport.subprocess_cli  # bundled Claude CLI
```

`guardkit/orchestrator/harness/selector.py:select_harness()` is **never consulted** on this path. Confirmed by:

- Direct read of `task_work_interface.py:407-485`: the imports at L438–450 are top-of-function direct imports of `claude_agent_sdk.{query, ClaudeAgentOptions, AssistantMessage, ...}`. No `select_harness` import anywhere in the module.
- Smoke v6 stderr (LangGraph + pre-loop ON) at `docs/state/TASK-REV-HMIG/canary-analysis.md` §3.F1: `INFO:guardkit.orchestrator.quality_gates.task_work_interface:Executing via SDK: ...` followed by `INFO:claude_agent_sdk._internal.transport.subprocess_cli:Using bundled Claude Code CLI: ...` regardless of `GUARDKIT_HARNESS=langgraph`.
- `grep -n "select_harness\|HarnessAdapter" guardkit/orchestrator/quality_gates/task_work_interface.py` returns no matches.

### Sequence diagram — missing adapter seam

```
┌─────────────────┐                                                ┌──────────────────┐
│  autobuild task │                                                │ HarnessAdapter   │
│  (pre-loop ON)  │                                                │  + select_harness│
└────────┬────────┘                                                └──────────────────┘
         │                                                                  ▲
         │ orchestrate(task_id)                                             │ ★ NOT CALLED
         ▼                                                                  │   (F1 gap)
┌─────────────────────┐                                                     │
│ AutoBuildOrchestrator│ _pre_loop_phase                                    │
└────────┬────────────┘                                                     │
         │                                                                  │
         │ execute_design_phase(task_id, options)                           │
         ▼                                                                  │
┌─────────────────────┐                                                     │
│ TaskWorkInterface   │ _execute_via_sdk(prompt)                            │
└────────┬────────────┘                                                     │
         │                                                                  │
         │ from claude_agent_sdk import query  ← HARD-CODED ────────────────┘
         │ (regardless of GUARDKIT_HARNESS env var)
         ▼
┌─────────────────────┐
│ claude_agent_sdk    │ query(...) → subprocess_cli → bundled claude CLI
└─────────────────────┘
```

### Implication for TASK-HMIG-006 completion claim

TASK-HMIG-006's commit `eaf6a1d5f` (and the three filed follow-ups `006.1`/`.2`/`.3`) cover:

| Site | Path | Status |
|---|---|---|
| Primary SDK call (Player/Coach turn) | `agent_invoker.py:2359-2740` `_invoke_with_role` | Migrated by HMIG-006 ✅ |
| Direct-mode TaskWork dispatch | `agent_invoker.py:5269+` | Filed as HMIG-006.1 ⏳ |
| Downstream helpers (`_extract_partial_from_messages`, `_track_tool_use`) | `agent_invoker.py` | Filed as HMIG-006.2 ⏳ |
| Coach independent SDK invocation | `coach_validator.py:1869+` | Filed as HMIG-006.3 ⏳ |
| **Pre-loop design phase** | **`task_work_interface.py:407-485`** | **Not filed** ❌ |

F1 is a **fourth uncovered call site** that was not enumerated when the HMIG-006 follow-ups were filed. The implementation plan §1 quoted in HMIG-006.1's task file describes only three follow-ups; the design-phase site was missed.

---

## 2. AC-002 — F4 worktree-manager dispatch diagnosis

### Confirmed: `WorktreeManager.create()` ignores cwd HEAD

The call chain:

```
cli/autobuild.py:task()                                # CLI entry — NO --base-branch flag
  └─ orchestrator.orchestrate(task_id=, requirements=, ...)  # orchestrator/autobuild.py:1177
                                                             # base_branch defaults to "main" (L1177)
      └─ self._setup_phase(task_id, base_branch)             # autobuild.py:1277 — passes default "main"
          └─ self._worktree_manager.create(                  # autobuild.py:1510-1513
                 task_id=task_id,
                 base_branch=base_branch,                     # still "main"
             )
              └─ WorktreeManager.create(task_id, base_branch="main")  # worktrees/manager.py:345-348
                  └─ git worktree add <path> -b autobuild/<task_id> main  # manager.py:296-301, 401
```

Read at `worktrees/manager.py:296-301`:

```python
def _build_worktree_add_cmd(self, worktree_path, branch_name, base_branch):
    return ["worktree", "add", str(worktree_path), "-b", branch_name, base_branch]
```

Read at `worktrees/manager.py:345-348`:

```python
def create(self, task_id: str, base_branch: str = "main") -> Worktree:
    ...
```

### The cwd-HEAD detection at `cli/autobuild.py:1190-1199` is wired to the wrong consumer

```python
def _find_worktree(manager, task_id):
    ...
    result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=worktree_path, ...)
    base_branch = result.stdout.strip() or "main"
    ...
    return Worktree(task_id=task_id, ..., base_branch=base_branch)
```

This is invoked **only by the `autobuild status` command** (line 555: `worktree = _find_worktree(worktree_manager, task_id)`). It populates the `Worktree` dataclass's `base_branch` attribute for **display** in `_display_status`. It is **never consulted by `create()`** — the create path runs through the orchestrator constructor parameter chain, which has no cwd-detection logic on it at all.

### Blast radius — same bug in `feature_orchestrator`

`grep -n "base_branch" guardkit/orchestrator/feature_orchestrator.py` confirms the same defect:

- `feature_orchestrator.py:736`: `base_branch: str = "main"` (orchestrate default)
- `feature_orchestrator.py:1026-1029`: `self._worktree_manager.create(task_id=feature_id, base_branch=base_branch)`

**`guardkit autobuild feature` reproduces the same F4 bug on the same call site** — so F4's blast radius is not limited to TASK-HMIG-009. Any caller of `guardkit autobuild {task,feature}` running from a non-main worktree (parallel feature-build, multi-feature worktrees, the canary-worktree wrapper) inherits the same defect.

### Classification

This is **a bug, not an intentional design choice**. Evidence:

- The cwd-detection code exists (CLI L1190) and is plumbed into the `Worktree.base_branch` display field. Its author understood that "the worktree was created from the current branch" was a meaningful concept.
- The bug surface is small (≤10 LOC at the CLI plumbing point) and well-isolated.
- No design doc, no architectural decision record, no commit message references "always branch from main" as a deliberate stance.
- The blast radius is larger than the symptom (affects `feature` too, breaks parallel-feature-build use case).

---

## 3. AC-003 — F1 remediation recommendation

### Options and defensibility

| Option | Description | Defensibility |
|---|---|---|
| **(i) — RECOMMENDED** | Extend HMIG-006's adapter coverage to the pre-loop design phase. Migrate `TaskWorkInterface._execute_via_sdk` to route through `select_harness()`. File as **TASK-HMIG-006.4** for symmetry with `.1/.2/.3`. | **High.** Without this, HMIG-006's "agent_invoker through HarnessAdapter" claim is misleading: the orchestrator advertises a harness seam that ~75–100% of wall-clock circumvents (per F1 evidence: 87–130s of pre-loop SDK turns vs 8187s of loop SDK turns means pre-loop is ~1.5% of wall-clock for v7-shape runs, but 100% of wall-clock for plan_validation-failure runs v2/v3/v5 — both bounds are non-trivial). The Wave-4 cutover would silently keep the design phase on claude-agent-sdk, defeating the migration's stated goal of removing claude-agent-sdk as a hard dependency. |
| (ii) | Document the limitation as out-of-scope; adjust TASK-HMIG-009's falsifier framing to "tests Player-Coach loop only, design phase always on SDK". | **Low.** The "design phase always runs on SDK" stance means the migration cannot deliver its primary value. The cutover plan becomes "ship LangGraph but keep SDK for the design phase forever" — a structurally worse end-state than today (SDK-only). Permanent dual-substrate maintenance burden. |
| (iii) | Deprecate the pre-loop entirely (cross-link with [TASK-REV-PL01](../../tasks/backlog/TASK-REV-PL01-preloop-architecture-review.md)). | **Aggressive.** TASK-REV-PL01 already raises the legitimacy question. But cancelling a major workflow feature on the basis of an architectural inconvenience is a much bigger scope change than the cutover needs, and a far weaker forcing function than just fixing the dispatch. Belongs in TASK-REV-PL01, not here. Out of scope for the 2026-06-15 cutover. |

### Recommendation: **(i)**

File **TASK-HMIG-006.4 — Migrate `TaskWorkInterface._execute_via_sdk` through HarnessAdapter**. Acceptance criteria template:

- AC-001: `task_work_interface.py:_execute_via_sdk` no longer imports `claude_agent_sdk` directly. Instead it routes through `select_harness()`.
- AC-002: `_translate_kwargs_for_langgraph` extended to translate `setting_sources=["project"]`, `max_turns=25`, `allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"]` and `permission_mode="acceptEdits"` (currently dropped silently — see selector.py:40-96).
- AC-003: AC-008 surface (existing 133 tests) continues to pass under `GUARDKIT_HARNESS=sdk`.
- AC-004: New regression test: `autobuild task --no-pre-loop=false` + `GUARDKIT_HARNESS=langgraph` produces zero `claude_agent_sdk.subprocess_cli` log lines during the design phase (matches TASK-REV-HM09's falsifier clause (a)).

---

## 4. AC-004 — F4 remediation recommendation

### Options and defensibility

| Option | Description | Defensibility |
|---|---|---|
| **(i) — RECOMMENDED** | Fix the worktree manager (or, more precisely, the CLI plumbing) to honour cwd HEAD when creating the inner branch. Two-line change at `cli/autobuild.py:task()` to detect cwd HEAD and pass it through `orchestrate(base_branch=...)`; equivalent change at `cli/autobuild.py:feature()`. Keep `WorktreeManager.create()`'s `base_branch="main"` default unchanged (it's a sensible library default; the CLI is the right place to detect cwd HEAD). | **High.** The bug is real, the blast radius extends beyond TASK-HMIG-009 (`guardkit autobuild feature` and parallel feature-build also affected per §2). Cheap fix. The cwd-detection logic already exists at `_find_worktree:1190`, just needs re-targeting. |
| (ii) | Leave behaviour unchanged, document the limitation in the canary methodology, narrow canary to backlog tasks (drop TASK-GLI-004, drop fixture-branch isolation). | **Low for the bug itself; acceptable as a temporary canary workaround.** The bug affects more than the canary; leaving it unfixed defers a real defect that will surface again at the first parallel feature-build attempt. Choosing (ii) for canary purposes does not preclude filing (i) as a separate fix — and in fact §5 recommends doing both. |

### Recommendation: **(i) + (ii)** in parallel

- **(i)** File **TASK-FIX-WTBC — Honour cwd HEAD in `autobuild task`/`autobuild feature` CLI**. Acceptance criteria template:
  - AC-001: `autobuild task` invoked from a non-main worktree creates the inner `autobuild/<task_id>` branch from cwd HEAD, not main HEAD.
  - AC-002: Same applies to `autobuild feature`.
  - AC-003: A `--base-branch` CLI flag is added to both commands as an explicit override; precedence is `--base-branch > cwd HEAD > "main"`.
  - AC-004: Regression test: invoke `autobuild task TASK-{fixture}` from a worktree on a non-main branch; assert `git -C .guardkit/worktrees/<task_id> rev-parse HEAD` matches the cwd HEAD. Equivalent test for `autobuild feature`.
- **(ii)** Run the partial-canary HMIG-009A (per §6, AC-007) with backlog tasks that don't need fixture-branch isolation, in parallel with (i)'s landing. (i) is cheap enough that it should land before HMIG-009B but does not block HMIG-009A from collecting useful comparative data immediately.

---

## 5. AC-005 — Effort, owners, and regression-test surface

| Remediation | Effort to landed+tested | Owner | Regression surface |
|---|---|---|---|
| **F1(i) — TASK-HMIG-006.4** | **5–7 hours.** Phase 3b refactor pattern is already established by HMIG-006. Main complication: extending `_translate_kwargs_for_langgraph` to map four additional SDK-only kwargs (`setting_sources`, `max_turns`, `allowed_tools`, `permission_mode`). The LangGraph-path translation of `setting_sources=["project"]` is the most subtle — DeepAgents has no direct analogue; needs either a no-op or a context-injection mechanism. | Same owner as TASK-HMIG-006 (Rich). | (1) `tests/orchestrator/quality_gates/test_task_work_interface.py` — existing tests must still pass under `GUARDKIT_HARNESS=sdk`. (2) New tests in same file covering `GUARDKIT_HARNESS=langgraph` path. (3) `tests/orchestrator/harness/test_byte_compat_parity.py` — pre-loop output shape parity assertion. (4) Smoke run: `autobuild task TASK-{fixture} --pre-loop` with both harnesses, assert zero `claude_agent_sdk.subprocess_cli` log lines on langgraph path. |
| **F4(i) — TASK-FIX-WTBC** | **3–4 hours.** Two small CLI changes, one `--base-branch` flag added to each command, one helper function for cwd-HEAD detection (factor out of `_find_worktree`), two regression tests. | Rich (CLI + worktree). | (1) New test in `tests/cli/test_autobuild.py` (or equivalent): invoke `autobuild task` from a non-main worktree fixture, assert inner branch HEAD matches cwd HEAD. (2) Equivalent for `autobuild feature`. (3) Test for the new `--base-branch` flag's precedence over cwd-HEAD detection. No external suites affected. |
| **F2 (cross-ref only — not in this task's scope)** | Unknown — depends on GB10 shell access. | Operator-side (TASK-OPS-{tbd}). | N/A (operator-side config audit; no GuardKit code surface). |

**Total dev for F1(i) + F4(i)**: ~8–11 hours, single owner, ~1–2 calendar days.

---

## 6. AC-006 — F2 cross-reference (llama-swap parser config)

F2 (pre-loop SDK + local Qwen tool-call wiring failure, documented at canary-analysis.md §3.F2) is **independent of F1**. The two compound but do not subsume each other:

- **F1**: The pre-loop path always uses claude-agent-sdk regardless of `GUARDKIT_HARNESS`.
- **F2**: The pre-loop path, *when the backing model is local Qwen via llama-swap*, fails to emit `tool_use` blocks because the llama-swap tool-call parser config does not match what claude-agent-sdk expects.

After F1(i) lands, calling `GUARDKIT_HARNESS=langgraph` will route the pre-loop through LangGraph's DeepAgents loop. **F2's underlying cause (llama-swap's tool-call parser config) still produces failures** — DeepAgents and claude-agent-sdk both expect well-formed `tool_use` shapes from the model, and the model is what's broken. The symptom may present differently (DeepAgents' failure mode is not yet observed), but the root cause is the same: the operator-side parser config on GB10's `/opt/llama-swap/config/config.yaml` for `qwen3-coder-30b` and `qwen36-workhorse` is not aligned with the SDK's tool-use response shape.

**Implication for the cutover decision**: **F1(i) is necessary but not sufficient for local-Qwen autobuild to work end-to-end with pre-loop ON.** The Wave-4 cutover should ship with **F2 documented as a known limitation** unless the operator-side audit closes it first. Users running local-Qwen substrate with pre-loop ON will continue to hit `plan_validation` failures until F2 is resolved.

**Action**: File **TASK-OPS-{tbd} — Audit llama-swap tool-call parser config on GB10 against claude-agent-sdk tool-use shape**. Owner: operator (Rich, with GB10 shell access). Cross-reference TASK-HMIG-006.4's documentation as a hard dependency for "local-Qwen autobuild end-to-end functionality".

---

## 7. AC-007 — TASK-HMIG-009 scope revision recommendation

### Options

| Path | Description | Compute cost | Cutover deadline risk |
|---|---|---|---|
| Hold | Block 18-rep canary until F1(i) + F4(i) + F2 all close. | ~40 hours GB10 compute. | **High.** F2 timeline is unbounded; if it slips past D-5 (~2026-06-10), the 18-rep run pushes the cutover. |
| **Split — RECOMMENDED** | HMIG-009A: partial canary (no fixture-branch isolation, `--no-pre-loop`, backlog tasks only). Runs after F1(i) lands. HMIG-009B: full original spec. Runs after all three close. | HMIG-009A: ~10 hours compute. HMIG-009B: ~40 hours compute (if it runs at all — may be redundant if 009A signal is sufficient). | **Low.** HMIG-009A is decoupled from F2's timeline; 009B is optional polish. |
| Cancel | Lean on the existing pilot signal for the cutover decision; document F1+F4+F2 as architectural debt the cutover inherits. | Zero. | **Medium.** No falsifier evidence for the cutover; relies on the parent review's analytical condition #2 holding without empirical confirmation. |

### Recommendation: Split into HMIG-009A + HMIG-009B

- **HMIG-009A** (depends on F1(i) landing — TASK-HMIG-006.4):
  - Scope: 2 backlog tasks (TASK-FIX-A7D3, TASK-DOC-267D — both small, no fixture-baseline needed), 3 reps per (task, harness), pre-loop OFF.
  - Total: 2 tasks × 2 harnesses × 3 reps = 12 runs.
  - Estimated compute: ~10 hours on GB10 (smoke v7 showed ~2h 16min per 3-turn loop run; backlog tasks are smaller, ~30–60 min per rep).
  - Falsifier: first-pass-success rate ≥75% on the LangGraph side, ≤30% absolute delta from SDK side. Provides empirical signal for the cutover decision.
  - Out of scope: fixture-branch isolation (waiting on F4(i) — TASK-FIX-WTBC), pre-loop comparison (waiting on F2 — operator-side), TASK-GLI-004 (drops because no fixture isolation).
- **HMIG-009B** (depends on F1(i) + F4(i) + F2 all landing):
  - Scope: TASK-HMIG-009 original spec — TASK-GLI-004 + 2 backlog tasks, fixture-branch baseline, pre-loop ON.
  - Optional polish if HMIG-009A's signal is already decisive.

**Cross-link with TASK-HMIG-010 readiness**: HMIG-009A's outcome is the gating signal for whether HMIG-010 (cutover) proceeds on schedule. HMIG-009B is gating only if 009A's signal is ambiguous.

---

## 8. AC-008 — One-page operator decision brief

> **Decision required by**: 2026-05-30 to preserve a 10-day implementation + canary window against the 2026-06-15 Wave-4 cutover deadline.

### The choice

**How much architectural debt do we ship with the LangGraph cutover?**

### Three paths

#### Path 1 — Full close

Land F1(i), F4(i), F2, then run the full 18-rep canary HMIG-009B.

- **Dev cost**: ~10h (F1+F4) + open-ended (F2, operator-side).
- **Compute**: ~40h GB10.
- **Cutover ships**: clean, fully validated, no documented limitations.
- **Risk**: F2 timeline is unknown. If F2 slips past D-5 (~2026-06-10), cutover slips.

#### Path 2 — Partial close (RECOMMENDED)

Land F1(i), F4(i). Run partial canary HMIG-009A. Defer F2 to a separate operator task. Ship cutover with F2 as a documented limitation.

- **Dev cost**: ~10h focused dev (F1+F4 only).
- **Compute**: ~10h GB10 (HMIG-009A only).
- **Cutover ships**: with F2 as documented limitation ("local-Qwen autobuild with pre-loop ON requires TASK-OPS-{tbd} fix; until then, run with `--no-pre-loop`").
- **Risk**: First production user to hit local-Qwen + pre-loop ON combo re-triggers F2. Mitigated by documentation and `--no-pre-loop` guidance.
- **Margin**: Comfortable if started by 2026-05-30 — ~10h dev + ~10h compute + 2 days buffer = ~5-day completion margin.

#### Path 3 — Workaround-only

Ship the cutover with all three findings unresolved. Narrow the canary to `--no-pre-loop` + backlog tasks; document everything as known limitations.

- **Dev cost**: zero.
- **Compute**: ~10h GB10 (partial canary).
- **Cutover ships**: with F1, F4, F2 all as documented limitations.
- **Risk**: HMIG-006's completion claim is contested. Every future autobuild invocation with pre-loop ON silently uses claude-agent-sdk regardless of `GUARDKIT_HARNESS` — the migration's primary value (removing claude-agent-sdk as a hard dependency) is not delivered. `autobuild feature` from non-main worktrees breaks.
- **Net**: The migration becomes a half-shipped state. Strongly discouraged.

### Recommendation: **Path 2 (Partial close)**

| | F1 fix | F4 fix | F2 fix | Canary scope | Total cost | Ships clean? |
|---|---|---|---|---|---|---|
| Path 1 | Yes | Yes | Yes | Full | ~10h dev + ~40h compute + open-ended F2 | Yes — but F2 risk |
| **Path 2** | **Yes** | **Yes** | **Defer** | **Partial** | **~10h dev + ~10h compute** | **With one documented limitation** |
| Path 3 | No | No | No | Narrow | ~10h compute only | No — three open architectural gaps |

Path 2 closes the two cheap, defensible bugs; defers the one expensive, operator-side bug to a separate track; and ships a migration that delivers its stated value (the harness adapter actually switches the full execution) at acceptable cost.

### Tasks to file on approval

- **TASK-HMIG-006.4** — Migrate `TaskWorkInterface._execute_via_sdk` through HarnessAdapter (per §3, AC-003 option (i)). Wave 3. Effort: 5–7h. Owner: Rich. Blocks HMIG-009A.
- **TASK-FIX-WTBC** — Honour cwd HEAD in `autobuild task`/`autobuild feature` CLI (per §4, AC-004 option (i)). Effort: 3–4h. Owner: Rich. Blocks HMIG-009B (HMIG-009A does not need it).
- **TASK-HMIG-009A** — Partial canary, backlog tasks, `--no-pre-loop`. Depends on TASK-HMIG-006.4. Effort: ~10h GB10 compute.
- **TASK-HMIG-009B** — Full canary per original TASK-HMIG-009 spec. Depends on TASK-HMIG-006.4 + TASK-FIX-WTBC + TASK-OPS-{tbd}. Optional — runs only if 009A signal is ambiguous.
- **TASK-OPS-{tbd}** — Audit llama-swap tool-call parser config on GB10 (per §6, AC-006). Owner: operator-side. Effort: unknown.

---

## 9. Decision options for this review

- **[A]ccept** — Approve findings; file the five tasks above; close TASK-REV-HM09.
- **[R]evise** — Request deeper analysis on a specific area (e.g. F1's translation kwargs for LangGraph, F4's `feature_orchestrator` blast radius, F2's operator-side timeline).
- **[I]mplement** — Auto-generate the five subtasks under a feature folder `tasks/backlog/hmig-pre-canary-fixes/`.
- **[C]ancel** — Discard the review and return TASK-REV-HM09 to backlog.

---

## Appendix A — Evidence pointers

- F1 source: [`guardkit/orchestrator/quality_gates/task_work_interface.py:407-485`](../../guardkit/orchestrator/quality_gates/task_work_interface.py#L407-L485)
- F1 stderr signature: `docs/state/TASK-REV-HMIG/canary-analysis.md` §3.F1 (smoke v6 trace)
- F4 source: [`guardkit/worktrees/manager.py:296-301, 345-348, 401`](../../guardkit/worktrees/manager.py#L296-L401), [`guardkit/orchestrator/autobuild.py:1177, 1277, 1510-1513`](../../guardkit/orchestrator/autobuild.py#L1510-L1513), [`guardkit/cli/autobuild.py:147-507, 1190-1199`](../../guardkit/cli/autobuild.py#L1190-L1199)
- F4 blast radius: [`guardkit/orchestrator/feature_orchestrator.py:736, 1026-1029`](../../guardkit/orchestrator/feature_orchestrator.py#L1026-L1029)
- F4 evidence: `docs/state/TASK-REV-HMIG/canary-analysis.md` §3.F4 (smoke v3 inner-worktree HEAD inspection)
- HMIG-006 follow-up tasks (none cover F1): [TASK-HMIG-006.1](../../tasks/backlog/autobuild-harness-migration/TASK-HMIG-006.1-migrate-direct-mode-sdk-dispatch.md), [TASK-HMIG-006.2](../../tasks/backlog/autobuild-harness-migration/TASK-HMIG-006.2-migrate-helpers-to-harness-event-dispatch.md), [TASK-HMIG-006.3](../../tasks/backlog/autobuild-harness-migration/TASK-HMIG-006.3-migrate-coach-independent-sdk-invocation.md)
- Parent review: [TASK-REV-HMIG review report](TASK-REV-HMIG-review-report.md) §§4, 5.3, 5.4, 7.3, 11
- Related: [TASK-REV-PL01 — preloop architecture review](../../tasks/backlog/TASK-REV-PL01-preloop-architecture-review.md)
