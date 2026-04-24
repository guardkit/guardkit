# TASK-REV-JMBP — Graphiti Preamble (Workstream A)

**Source**: TASK-REV-JMBP (Analyse jarvis FEAT-J002 autobuild failure on MacBook Pro)
**Author**: /task-review architectural, standard depth
**Captured**: 2026-04-24
**Pattern source**: mirrors TASK-REV-MCPS Workstream A (pre-flight of existing graph knowledge before remediation proposals).

## Queries executed

Five targeted queries against the guardkit knowledge graph, plus two supplementary to triangulate
the prior-art signal discovered in Q3.

### Q1 — "Coach agent-invocations gate missing phases"

- `mcp__graphiti__search_nodes("Coach agent-invocations gate missing phases", group_ids=["guardkit__project_decisions","guardkit__project_architecture"])`
- **Hits**: 10 nodes.
- **Load-bearing hits**:
  - `validate_agent_invocations` (uuid `1695f703-32eb-4072-94cb-e3948fd981e8`, group `guardkit__project_decisions`, 2026-04-22):
    > "validate_agent_invocations is a checkpoint in task-work.md, declared as the sole guard against
    > false reporting, but it has no runtime callers, making it the highest severity orphan in
    > task-work.md."
  - `Phase B Coach to Player retry feedback` (uuid `d510aec5-fa68-4abe-a238-77cfd42a4710`): feedback split
    into `[SHAPE]` (schema) vs `[CONTENT]` (semantic) modes to target patch vs regenerate — orthogonal
    product, but relevant: suggests the graph already knows that feedback-mode taxonomy matters.
- **Non-hits worth noting**: nothing links the string "agent-invocations gate" to a specific remediation
  task. The gate is mentioned as an orphan prior to 2026-04-22, and as wired via TASK-FIX-RWOP1.3.1
  after (inferable from code comment `coach_validator.py:636` "TASK-FIX-RWOP1.3.1" annotation).

### Q2 — "feedback stall identical feedback signature"

- `mcp__graphiti__search_memory_facts("feedback stall identical feedback signature", group_ids=["guardkit__project_decisions","guardkit__task_outcomes"])`
- **Hits**: 20 facts, mostly about *Phase B retry-feedback* semantics and unrelated review outcomes.
- **Load-bearing hits**: none. The *stall-detector-specific* feedback-signature concept
  (md5 hash of normalised Coach feedback used by `autobuild._is_feedback_stalled`) has no graph
  representation. **This is itself a finding**: the stall detector added in TASK-AB-SD01
  (referenced in code at `autobuild.py:3237`) was never captured as a Graphiti decision/procedure node.

### Q3 — "task-work results phases missing agent invocations"

- `mcp__graphiti__search_nodes("task-work results phases missing agent invocations", group_ids=["guardkit__project_decisions","guardkit__task_outcomes"])`
- **Hits**: 10 nodes.
- **Load-bearing hits**:
  - Re-confirms `validate_agent_invocations` orphan status (duplicate of Q1 hit).
  - `TASK-FIX-7B2E` (uuid `e3bd206b-9e65-4183-a636-9d084f8bfefd`): "remediation task addressing the
    *runner without producer* anti-pattern. Targets multiple command specs including feature-plan.md,
    feature-spec.md, and task-work.md, with high priority on cohort-blocking issues."
  - `TASK-REV-RWOP1` (uuid `df0dc485-6697-4b86-a6cc-2a7613315236`): "41 orphan sites across command specs."
- **Interpretation**: the graph already knows (a) task-work.md once had an orphaned validator, and
  (b) the "runner without producer" anti-pattern is the meta-class behind it. These are both directly
  relevant to the JMBP failure, but neither decomposes into the specific question "what happens when
  the wired validator fires in the producer path and Coach rejects downstream?"

### Q4 — "context pollution no passing checkpoint unrecoverable stall"

- `mcp__graphiti__search_nodes(..., group_ids=["guardkit__project_decisions"])`
- **Hits**: 0.
- **Absence-of-knowledge finding**: the context-pollution exit path added by TASK-AB-SD01
  (`autobuild.py:1957-1988`) has no corresponding graph node. The rule "rollback on 2+ consecutive
  test failures; if no passing checkpoint exists, exit unrecoverable" is code-only. Implication:
  if J002-013's checkpoint-loss behaviour (all-three-turns recorded `test_count: 0`, triggered by
  the bootstrap failure) was previously observed on any other project, it's not in the graph to find.

### Q5 — "environment bootstrap PEP 668 venv Coach pytest interpreter"

- `mcp__graphiti__search_nodes(..., group_ids=["guardkit__project_decisions"])`
- **Hits**: 0.
- **Absence-of-knowledge finding**: TASK-FIX-7A05 (wire bootstrap venv into Coach pytest) and
  the PEP-668 fallback observed in `forge-run-2.md:57` have no graph representation. The bootstrap
  → Coach-pytest interpreter-mismatch hazard is not captured anywhere queryable. Consistent with
  TASK-REV-E4F5 being a filed-but-unimplemented feature folder.

### Supplementary Q6 — "autobuild SDK stall resilience TASK-REV-E4F5 TASK-FIX-7A02 player invocation stall classification"

- `mcp__graphiti__search_nodes(..., group_ids=["guardkit__project_decisions","guardkit__task_outcomes","architecture_decisions"])`
- **Hits**: 10 nodes.
- **Load-bearing hits**:
  - `TASK-FIX-F584` (uuid `0eb3ce59-089a-4c7e-8910-383192695a2c`): "silent false-green defect in the R2
    BDD oracle where non-zero pytest return codes (excluding 5) with empty results lead to task
    approval". Not the same defect as JMBP, but structurally adjacent: the BDD oracle and the
    agent-invocations gate are both examples of *evidence-interpretation gates* that can produce
    wrong verdicts under specific empty-result shapes.
- **Non-hits**: no node for TASK-REV-E4F5, no node for any TASK-FIX-7A0x. TASK-REV-E4F5 outcomes
  appear to have never been seeded into the graph — which is consistent with those tasks being
  *filed but unimplemented*, and `[A]ccept` on TASK-REV-E4F5 (if it occurred) would have written to
  `guardkit__task_outcomes` but only a review-outcome summary, not per-subtask decisions.

### Supplementary Q7 — "runner without producer antipattern namespace hygiene local decisions external contracts"

- `mcp__graphiti__search_nodes(..., group_ids=["guardkit__project_decisions"])`
- **Hits**: 0 (despite the rule file `.claude/rules/namespace-hygiene.md` naming this uuid:
  `184731b0-3cb6-4eb2-a310-883421767dbf` as a sibling). The failure to retrieve it suggests either
  the rule-file citation is to a node in a *different* group, or the embedding-index is not ranking it
  highly for this phrasing. Not a defect for this review — but worth flagging: the sibling-rule
  citation at `.claude/rules/namespace-hygiene.md:125` may be stale.

## Summary findings

### Present in the graph (load-bearing for JMBP)

1. **`validate_agent_invocations` was declared in task-work.md as the sole guard but was orphan until
   TASK-FIX-RWOP1.3.1** — from Q1/Q3. The wiring fix (code comment `coach_validator.py:636` and
   `agent_invoker.py:5411`) turned the validator from "declared but never-called" into
   "runs on producer write, persists verdict, Coach reads verdict". **JMBP is the first observed
   case where the wired validator fires in production and blocks Coach approval.** This reframes
   TASK-REV-RWOP1.3.1 from "orphan-fix plumbing" into "protocol enforcement that now stops tasks."

2. **The "runner without producer" anti-pattern is the meta-class behind the orphan** — Q3 hit
   TASK-REV-RWOP1 (41 orphan sites). The JMBP failure is not itself an instance of that anti-pattern
   (the validator IS now wired), but its *architectural shape* — a checkpoint declared in one layer
   whose runtime invocation was never reconciled with the Player's execution model — is the same
   class as the anti-pattern. Worth citing in any remediation design.

3. **Feedback-mode taxonomy already exists for Phase B** (Q1): `[SHAPE]` vs `[CONTENT]` feedback
   modes. This is a *usable design primitive* for classifying the agent-invocations-violation
   feedback. It's neither `[SHAPE]` nor `[CONTENT]` — it's a *protocol* violation (Player skipped a
   required sub-agent). A future taxonomy extension could add `[PROTOCOL]` as a third mode.

### Absent from the graph (absence-of-knowledge findings)

- **A1** — No node for TASK-AB-SD01's feedback-stall detector or its md5-signature approach.
  The rule "3 identical Coach feedback signatures with zero criteria-progress → unrecoverable_stall"
  is code-only. Candidate for seeding on `[A]ccept`.
- **A2** — No node for the context-pollution rollback exit (`autobuild.py:1957-1988`). Same as above.
- **A3** — No node for the bootstrap-Coach-pytest-interpreter hazard (Workstream E subject).
  TASK-FIX-7A04/7A05 drafted this as a concern but neither is implemented, so no post-flight
  episode was ever written. Candidate for seeding on `[A]ccept`, at minimum as a decision-pending
  marker.
- **A4** — No node for the `_render_unrecoverable_stall_summary` fallback-hint misattribution
  (`autobuild.py:4552-4555`). The "Review task_type classification and acceptance criteria" default
  is not captured anywhere as "known-bad default hint".
- **A5** — No node for the bimodal implementation_mode routing behaviour. The fact that task-work
  mode triggers the agent-invocations gate with `expected_phases=3` while direct mode skips the
  gate entirely (via `_invoke_player_direct`) is the most load-bearing single fact about this
  failure, and it has no graph representation.

### Stale references to flag for the owner

- `.claude/rules/namespace-hygiene.md:~130` cites the "runner without producer" sibling rule by
  Graphiti uuid `184731b0-3cb6-4eb2-a310-883421767dbf`. Supplementary Q7 did not retrieve that node
  by text query — either the uuid citation is stale, or the node is in a group not queried here
  (most likely `architecture_decisions`). If a future reader follows that citation they may find a
  broken link. *Not this review's job to fix, but flag it.*

## Knowledge-graph remediation recommendations (on [A]ccept)

Write the following episodes (non-blocking; done by the /task-review Phase 5 `capture_review_to_graphiti` path):

1. **Findings episode** → `guardkit__project_decisions`:
   *"Autobuild agent-invocations gate failure taxonomy"* — 4 failure modes distinguished:
   `coach_agent_invocations_stall` (this run), `player_invocation_stall` (GB10/TASK-REV-E4F5),
   `context_pollution_stall_no_checkpoint` (this run, J002-013 secondary),
   `sdk_api_error_stall` (already hinted in `autobuild.py:4544`).

2. **Outcome episode** → `guardkit__task_outcomes`:
   *"Review outcome: TASK-REV-JMBP"* — workstream-by-workstream verdicts and the D-decision.

3. **Rule episode** (if D1 chosen) → `guardkit__project_decisions`:
   *"Task-work implementation_mode bimodal routing rule"* — documents that `implementation_mode: direct`
   bypasses the agent-invocations gate; task-work mode requires the three-agent pipeline
   (specialist + test-orchestrator + code-reviewer) to be *actually invoked* (not inlined).
