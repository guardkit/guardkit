# FEAT-SCG — the mechanical spec-conformance guard (scope + buildplan)
## 2026-07-27 · BINDING SPEC for the orchestrated build · the plan of record's NEXT #1 (step-5 cheapest bite)

> Grounded in the two sources of truth (ai-transition: mission
> `docs/software-factory-mission-statement-2026-07-25.md` + plan
> `docs/software-factory-plan-of-record.md`). Lane claim: ai-transition exec-plan §7,
> 2026-07-27 night. Measurables: **M5** (a verification surface WITH its fix dispatch)
> and **M0** (shrinks the step-5 frontier residual). No frontier calls added anywhere —
> the guard is deterministic code.

## The one-minute version

On 2026-07-26 the local coach APPROVED spec-divergent work three times (receipts below).
Each drift was caught only by the frontier coordinator re-running the same **mechanical**
check class by hand: byte-parity against the spec'd contract, and AC-presence against the
task's acceptance criteria. Mechanical, not judgment — so it belongs IN the chain. This
lane builds a deterministic **spec-conformance guard** into guardkit's Player-Coach loop:
declarative per-task rules run on every Coach turn; a failure flips `approve` →
`feedback` with a must-fix the Player repairs next turn — the fix-and-re-verify law,
executing locally. Report-only verification is forbidden by the mission; this surface
ships WITH its fix dispatch by construction.

**What breaks on a non-Python repo: nothing** — the executor is text/path/subprocess
only (byte comparison, token grep, command exit codes); it never imports or parses the
target app's language; anything stack-specific rides the `assert_command` escape hatch.

## Why guardkit and not forge (design-pass verdict, seams pinned against real code)

- Forge is spec-blind (reads `.guardkit/features/<id>.yaml` only to COUNT tasks —
  `src/forge/subagents/autobuild_runner.py:999`) and on success the sidecar REMOVES the
  worktree before the daemon sees anything (`autobuild_runner.py` "remove on SUCCESS,
  keep on failure"). A forge-side observer is structurally report-and-escalate
  (`src/forge/lifecycle_bridge/budget_observer.py:5-13`) — it can never feed a fix turn.
- Guardkit already owns the exact pattern: the **deterministic verdict-override guard
  chain** in `AgentInvoker.invoke_coach` (`guardkit/orchestrator/agent_invoker.py`,
  chain calls ≈2448–2528). Contract stated in-code: only `approve` verdicts are ever
  FLIPPED to `feedback`. Template: `_apply_behavioural_oracle_guard` (≈:7082) — flip,
  prepend a `must_fix` issue, re-persist via `_persist_coach_decision`; the text reaches
  the Player through `_extract_feedback` (`guardkit/orchestrator/autobuild.py:7640`).
- Structured ACs are ALREADY in scope: `invoke_coach(acceptance_criteria:
  Optional[List[Dict[str,str]]])` (`agent_invoker.py:2190`, `[{"id","text"}]`) — they
  are just not threaded into the guard calls yet.
- Evidence seam: `validator.gather_evidence(...)` (`autobuild.py:6743`) builds the
  `CoachEvidenceBundle` (`guardkit/orchestrator/quality_gates/coach_evidence.py:172`).
  The new signal rides the bundle like `behavioural_oracle` does.

## The three receipts this must mechanize (the lane's acceptance evidence)

| catch | drift | why the coach's green was false | mechanical form |
|---|---|---|---|
| **CV4M fence re-teach** (fix `041098ad`) | the v4 Decision Format block re-taught fenced output + extra keys | the Player byte-compared against ITS OWN divergent fixture — both sides editable together; **that hole is still open today** (no test links `tests/fixtures/coach-contract/v4_decision_format_spec.txt` to the adf authority) | byte-parity where the AUTHORITY side is captured out of the Player's reach |
| **SBHO rename-not-relocation** (fix `4a37bacc`) | `task_private_dir` resolved INSIDE the shared worktree (rename, not relocation) | the AC test passed a plain `tmp_path` root — broken and correct code resolve identically; **still unpinned today** (`tests/unit/orchestrator/test_holdout_relocation.py` uses bare `tmp_path`) | invariant assertion exercised under a REALISTIC (worktree-shaped) root |
| **CMIR-003 missing config tier** (fix `33ed5e0a`) | AC-1's config tier simply never built; two duplicated env-only resolvers; a comment claimed otherwise | an OMISSION produces no failing test — the coach graded what was present | AC-token coverage: required tokens present, duplicate reads bounded, required tier-tests exist |

## The design (build exactly this)

### 1. Rule schema + declaration (`conformance:` block, per task)

A task declares rules in its task-file YAML frontmatter under `conformance:`. Three rule
types ONLY (no DSL growth — YAGNI):

```yaml
conformance:
  ac_paths: true            # optional: AC-cited-path presence over the structured ACs
  rules:
    - id: R-1
      type: byte_parity     # the CV4M class
      authority: docs/spec/decision-format.golden.txt   # captured pre-build (see §2)
      subject: guardkit/orchestrator/agent_invoker.py
      subject_region: {start: "_V4_DECISION_FORMAT_BLOCK = ", end: '"""'}  # optional marker-delimited region; whole file when absent
    - id: R-2
      type: token_coverage  # the CMIR-003 omission class
      paths: ["guardkit/orchestrator/coach_contract.py"]
      require_tokens: ["config.yaml", "autobuild", "coach", "contract"]
      unique_token: {token: "GUARDKIT_COACH_CONTRACT", max_count: 1, paths: ["guardkit/orchestrator/**/*.py"]}
      require_test_tokens: {paths: ["tests/**/*.py"], tokens: ["config-only tier"]}
    - id: R-3
      type: assert_command  # the SBHO invariant class; the stack-agnostic escape hatch
      command: "python scripts/check_containment.py"    # any command; exit 0 = pass
      expected_exit: 0
      timeout: 120
```

Schema = pydantic, strict (`extra="forbid"`, loud on unknown type/typo — the CMIR
loud-degrade lesson). Absent block ⇒ the whole feature is a **byte-equivalent no-op**
(proven by test; the UBS-002 attended/NULL equivalence discipline). `ac_paths` and
`rules` are both opt-in in v1 — flipping any default ON later is a separate,
data-backed decision, not this lane's.

### 2. Snapshot at task load (the CV4M bypass-resistance crux)

BEFORE Player turn 1, the orchestrator snapshots into the task-private dir
(`TaskArtifactPaths.task_private_dir`, `guardkit/orchestrator/paths.py:616` — outside
the worktree post-SBHO): (a) the parsed `conformance` block; (b) the BYTES of every
rule's `authority` file. All later comparisons run against the snapshot. A Player that
edits both sides inside the worktree can no longer stay green — the exact CV4M hole,
closed structurally. Builder pins the load seam in stage 1 (the task-frontmatter parse
path in the orchestrator) and documents it file:line in the code.

### 3. Executor (pure, stack-agnostic)

New module `guardkit/orchestrator/quality_gates/spec_conformance.py`: pure functions,
no I/O beyond reading declared paths/snapshot + running `assert_command` via
subprocess with timeout. Output: `{status: absent|passed|failed, failures:
[{rule_id, kind, detail}]}` where `detail` is actionable (unified diff for
byte_parity; missing/duplicated tokens for token_coverage; exit code + output tail for
assert_command; missing paths for ac_paths). Absence-of-failure discipline throughout:
absent block, absent authority snapshot, or executor crash ⇒ `absent` + a logged
warning, NEVER a fabricated pass/fail.

### 4. Evidence leg + the guard

- `gather_evidence` gains a `spec_conformance` leg (same shape discipline as
  `behavioural_oracle`).
- New `_apply_spec_conformance_guard` appended to the guard chain (after
  `_apply_behavioural_oracle_guard`, before narrative reconciliation), modeled on it
  byte-for-byte: fires ONLY on `status == failed`; flips `approve` → `feedback`;
  prepends one `severity=must_fix, category=spec_conformance_failure` issue per failed
  rule (rule id + detail verbatim); re-persists. `acceptance_criteria` is threaded into
  the guard call for the `ac_paths` check (reuse `_scan_ac_for_missing_paths`'s
  extraction approach, `agent_invoker.py:≈10350`, generalized and made non-Python-safe).
- The flip is persisted in `coach_turn_N.json` — that trail IS the M5 receipt (find →
  fix turn → same check green next turn, all on disk).

### 5. Proof against history (stage 3 — the lane's acceptance)

1. Three **would-have-fired** tests: drive the executor with rules reconstructing each
   2026-07-26 drift (pre-fix shapes) and assert each yields the blocking failure.
2. Close the two live holes as permanent regression tests:
   - **Provenance pin (CV4M):** vendor the authoritative v4 Decision Format bytes as a
     guardkit golden with a dated provenance header naming its source
     (`agentic-dataset-factory/domains/coach-agent/build_v4_sft.py::V4_DECISION_FORMAT`);
     test asserts the rendered prompt block == the golden. Do NOT import across repos
     and do NOT modify adf — vendor + header is the contract.
   - **Containment pin (SBHO):** a test that builds a worktree-SHAPED root
     (`<root>/.guardkit/worktrees/<id>`) and asserts
     `task_private_dir(...)` is NOT a descendant of that worktree.

## Stages (each = builder + independent coach; blocker ⇒ one fix pass + re-coach)

- **SCG-001 — schema + executor + snapshot.** The pydantic rule schema, the executor
  module, the task-load snapshot into the private dir. Unit tests for every rule type
  incl. absent/crash → `absent`. No wiring into the loop yet.
- **SCG-002 — evidence leg + guard + threading.** The `spec_conformance` bundle leg,
  the guard in the chain, `acceptance_criteria` threading, `ac_paths`. Tests modeled on
  `tests/unit/orchestrator/test_runtime_parity.py`. A test PROVES byte-equivalence when
  no `conformance` block exists (no behavior change for every existing repo/task).
- **SCG-003 — history proofs + the two regression pins.** §5 above, exactly.

## Fences (binding on every builder and coach)

- Venue: **guardkit ONLY**. No writes to forge, api_test, agentic-dataset-factory, or
  any other repo. The adf authority is VENDORED (bytes + provenance header), never
  imported, never edited at source.
- NOTHING under `installer/**` (DF-019). `.guardkit/**` and `uv.lock` untouched.
- No coach prompt-text changes; no grammar changes; no changes to the v4 wire contract.
- No service restarts, no NATS/broker access of any kind, no pushes, no deploys —
  local path-limited commits only; the coordinator reviews before anything leaves the
  machine.
- Builds without a `conformance` block MUST be byte-equivalent (tested, not asserted).
- Plain language in all docs/errors; failure text must be actionable to a local Player.

## Measurables (honest statement)

- **M5**: this creates the surface AND its receipts (guard flips + next-turn green in
  `coach_turn_N.json`). Baseline stays "unmeasured" until a rule fires on an organic
  build; the machinery + the three history proofs are this lane's deliverable.
- **M0**: the byte-parity/AC-presence check class stops being frontier-coordinator-only
  — it runs in-chain, locally, zero LLM calls. The coordinator's manual re-checks
  remain until specs start carrying `conformance` blocks (the next routine sit can
  stage the first one) — that residual is named, not hidden.
