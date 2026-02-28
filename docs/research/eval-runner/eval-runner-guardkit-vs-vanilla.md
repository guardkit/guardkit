# GuardKit vs Vanilla — Eval Type Specification

**Eval type:** `guardkit_vs_vanilla`  
**Parent system:** guardkit/eval-runner  
**Date:** February 2026  

---

## 1. Purpose

This eval type answers the core question that justifies GuardKit's existence:

> **Does running `feature-spec → system-plan → feature-plan → autobuild` produce measurably better results than giving the same input to plain vanilla Claude Code?**

It is a scientific comparison with a controlled input (the same Linear ticket or requirement text) and two treatment arms:

- **Arm A — GuardKit pipeline:** `feature-spec` → `system-plan` → `feature-plan` → `autobuild` (Player/Coach loop)
- **Arm B — Vanilla Claude Code:** `claude "<same input>"` in an equivalent codebase, no project templates, no CLAUDE.md, no orchestration

The judge measures the delta across dimensions that matter: assumption surfacing, code quality, test coverage, architectural coherence, and turns-to-completion.

---

## 2. Why This Comparison Is Difficult to Get Right

Naively running two builds and comparing them misses several confounds:

### 2.1 Starting State Must Be Identical

Both arms must begin from the same codebase snapshot. If Arm A modifies the repo and Arm B starts from a different state, the comparison is meaningless. This requires **workspace forking** — creating a shared base state and copying it twice before either arm runs.

### 2.2 "Vanilla" Needs a Definition

Three options, with different interpretations:

| Vanilla definition | What it tests | Best for |
|---|---|---|
| Bare `claude "<ticket>"` — no project context | Whether orchestration alone matters | Showing worst-case Claude Code |
| `claude "<ticket>"` in the same repo (no GuardKit) | Whether it's the tooling or the prompting | **Most defensible comparison** |
| `claude` with a good system prompt but no GuardKit orchestration | Whether it's the methodology or the execution | Testing prompt engineering alone |

**Recommendation: Option 2.** This is what a real team would actually do — developer with Claude Code and the codebase vs developer with GuardKit and the same codebase. It controls for codebase context while isolating the GuardKit tooling.

### 2.3 The Same Input Must Drive Both Arms

The input (a Linear ticket URL, a requirement string, or a feature description file) is loaded once and passed identically to both arms. The eval agent cannot summarise or paraphrase it differently between runs.

### 2.4 Scoring Must Measure Delta, Not Absolute Quality

A feature that is inherently simple will score well in both arms. The judge should score on **relative improvement**, not absolute output quality.

---

## 3. Brief Schema

```yaml
eval_id: EVAL-007
title: "GuardKit vs Vanilla — YouTube channel stats endpoint"
version: "1.0"
type: guardkit_vs_vanilla
priority: high
tags: [guardkit-vs-vanilla, youtube-mcp, fastapi]

setup:
  workspace_template: guardkit-project   # has CLAUDE.md + .guardkit/ + existing codebase
  vanilla_workspace_template: plain-project  # same codebase, no GuardKit config
  timeout_minutes: 90                    # generous — two full builds
  max_turns_per_arm: 100

# The shared input — passed identically to both arms
input:
  source: linear_ticket                  # linear_ticket | text | file
  linear_ticket_url: "https://linear.app/appmilla/issue/AP-142"
  # OR:
  # source: text
  # text: |
  #   Add a GET /youtube/channel/{channel_id}/stats endpoint that returns
  #   subscriber count, view count, and video count. The data comes from
  #   an external YouTube API. Include error handling and caching.

# --- Arm A: GuardKit pipeline ---
guardkit_arm:
  description: "Full GuardKit pipeline"
  commands:
    - "guardkit feature-spec --from {input_file}"
    - "guardkit system-plan"
    - "guardkit feature-plan"
    - "guardkit autobuild"
  document:
    - turns_per_command: true
    - coach_feedback_cycles: true
    - assumptions_surfaced: true         # count of assumptions.md entries
    - files_created: true
    - test_coverage: true

# --- Arm B: Vanilla Claude Code ---
vanilla_arm:
  description: "Vanilla Claude Code — same codebase, no GuardKit"
  commands:
    - 'claude "{input_text}"'            # bare Claude Code invocation
  document:
    - turns_total: true
    - files_created: true
    - test_coverage: true

# Scoring criteria
criteria:
  - id: c1
    description: "GuardKit arm surfaced explicit assumptions that vanilla arm made silently"
    weight: 0.25
    check_type: llm_judge

  - id: c2
    description: "GuardKit arm produced higher or equal test coverage"
    weight: 0.20
    check_type: deterministic

  - id: c3
    description: "GuardKit arm code quality score ≥ vanilla (ruff/pylint/tsc)"
    weight: 0.20
    check_type: deterministic

  - id: c4
    description: "GuardKit arm output has clearer architectural rationale (ADRs, comments)"
    weight: 0.20
    check_type: llm_judge

  - id: c5
    description: "Both arms produced a runnable result (not just scaffolding)"
    weight: 0.15
    check_type: deterministic

pass_threshold: 0.65
escalate_threshold: 0.40

judge_context: |
  This is a comparison eval. Score criteria relative to the DELTA between
  the two arms, not on absolute quality.
  
  For c1: Look for an assumptions.md in the GuardKit arm workspace. Compare
  any architectural decisions explicitly documented vs implicit in vanilla output.
  
  For c4: Look for CLAUDE.md updates, ADR files, comments explaining WHY
  a design was chosen — not just what was implemented.
  
  A tie (both arms perform identically) should score 0.5 for delta criteria.
  GuardKit winning significantly = 1.0. GuardKit losing = 0.0.
```

---

## 4. Workspace Architecture

### 4.1 The Fork Problem

Standard `EvalWorkspace` provisions one temp directory per eval. `guardkit_vs_vanilla` needs two workspaces from the same starting state:

```
shared base (from workspace_template)
    ├── copy A  → guardkit arm workspace  (has CLAUDE.md, .guardkit/)
    └── copy B  → vanilla arm workspace   (no GuardKit config, just codebase)
```

This requires `EvalWorkspace.fork()` — provision one base, snapshot it as a git commit, then clone it twice.

### 4.2 Git-Based Forking

Using git for the fork gives two benefits: it is fast (shallow copy), and it gives the eval runner a clean diff after each arm runs.

```python
class EvalWorkspace:
    async def create_forked_pair(
        self,
        guardkit_template: str,
        vanilla_template: str,
    ) -> tuple[Path, Path]:
        """Provision two workspaces from their respective templates.
        
        Returns (guardkit_path, vanilla_path).
        Both are independent temp directories — no shared state after creation.
        """
```

**Why not a single template copied twice?** The GuardKit arm needs `CLAUDE.md` and `.guardkit/commands/` present. The vanilla arm must not have them — otherwise vanilla Claude Code will pick up the GuardKit methodology from the project context. They need different templates.

### 4.3 Template Requirements

| Template | Contents | Purpose |
|---|---|---|
| `guardkit-project` | Full codebase + `CLAUDE.md` + `.guardkit/` + `pyproject.toml` | GuardKit arm starting state |
| `plain-project` | Same codebase + `pyproject.toml` only. No `CLAUDE.md`, no `.guardkit/` | Vanilla arm starting state |

Both templates should be maintained in sync — same codebase version, only the GuardKit config differs. This can be automated: `plain-project` is `guardkit-project` minus `CLAUDE.md` and `.guardkit/`.

---

## 5. Runner Design

### 5.1 Execution Flow

```
Load brief
    ↓
Resolve input (Linear ticket → text, or use text directly)
    ↓
Provision workspaces
    EvalWorkspace.create_forked_pair()
    ├── guardkit_workspace  (guardkit-project template)
    └── vanilla_workspace   (plain-project template)
    ↓
Run Arm A — GuardKit pipeline
    EvalAgentInvoker(guardkit_workspace).invoke(guardkit_brief)
    → guardkit_trajectory
    ↓
Run Arm B — Vanilla
    EvalAgentInvoker(vanilla_workspace).invoke(vanilla_brief)
    → vanilla_trajectory
    ↓
Extract metrics from both workspaces
    MetricsExtractor.extract(guardkit_workspace, vanilla_workspace)
    → ComparisonMetrics
    ↓
Judge delta
    EvalJudge.evaluate_comparison(brief, guardkit_trajectory, vanilla_trajectory, metrics)
    → EvalResult (with per-arm breakdown)
    ↓
Publish + Store
```

### 5.2 Arms Run Sequentially, Not in Parallel

Running both arms simultaneously would contend for:
- Anthropic API rate limits (two SDK sessions simultaneously)
- Local vLLM throughput (one model serving two parallel queries)

Sequential execution doubles wall time but eliminates all contention. With a 90-minute timeout per eval, this is acceptable.

### 5.3 Input Resolution

```python
class InputResolver:
    async def resolve(self, brief: GuardKitVsVanillaBrief) -> str:
        """Returns the raw input text passed identically to both arms."""
        if brief.input.source == "linear_ticket":
            return await self._fetch_linear_ticket(brief.input.linear_ticket_url)
        elif brief.input.source == "file":
            return Path(brief.input.file_path).read_text()
        else:
            return brief.input.text
    
    async def _fetch_linear_ticket(self, url: str) -> str:
        """Fetch Linear ticket title + description via Linear API or web fetch."""
        # Uses Linear MCP if available, falls back to web fetch
        ...
```

The resolved text is written to `input.txt` in both workspaces before any agent runs, so both arms can reference it via the filesystem.

---

## 6. Per-Arm Agent Instructions

The eval agent receives different instructions per arm, but the same input text.

### Arm A — GuardKit Agent Instructions

```
You are evaluating the GuardKit pipeline against a given requirement.

The input requirement is in: ./input.txt

Execute the full GuardKit pipeline:
1. Run: guardkit feature-spec --from ./input.txt
   - Note: did it produce assumptions.md? How many assumptions were surfaced?
2. Run: guardkit system-plan
3. Run: guardkit feature-plan
4. Run: guardkit autobuild
   - Document: total turns, Coach feedback cycles, any blocking issues

After each command, write a brief note to ./guardkit-run-log.md:
  ## After [command]
  - Status: [success/failed/blocked]
  - Key outputs: [files created, assumptions surfaced, etc.]
  - Turns used: [N]
  - Coach feedback cycles: [N]

At the end, run the test suite and capture results.
Write test coverage to .eval/evidence/c2.txt: "coverage={N}%"
Write lint score to .eval/evidence/c3.txt: "violations={N}"
Write assumptions count to .eval/evidence/c1.txt: "assumptions_surfaced={N}"
Write runnable status to .eval/evidence/c5.txt: "runnable={yes|no}"

Write SUMMARY.md documenting what worked, what was surfaced, what failed.
```

### Arm B — Vanilla Agent Instructions

```
You are evaluating vanilla Claude Code against a given requirement.

The input requirement is in: ./input.txt

Execute vanilla Claude Code:
1. Run: claude "$(cat ./input.txt)"
   Do NOT use any guardkit commands.
   Do NOT create CLAUDE.md or .guardkit/ directories.
   Let Claude Code proceed entirely on its own.

After the run, document what happened:
- Total turns Claude Code used
- Files created
- Did it ask clarifying questions or proceed on assumptions?
- What assumptions were implicit in its implementation?

Write ./vanilla-run-log.md with the same structure as above.

Run the test suite and capture results.
Write test coverage to .eval/evidence/c2.txt: "coverage={N}%"
Write lint score to .eval/evidence/c3.txt: "violations={N}"
Write .eval/evidence/c1.txt: list of silent assumptions the vanilla run made
Write .eval/evidence/c5.txt: "runnable={yes|no}"

Write SUMMARY.md documenting what Claude Code produced and what it silently assumed.
```

---

## 7. Metrics Extraction

After both arms complete, the runner extracts comparable metrics programmatically before the judge runs.

```python
@dataclass
class ArmMetrics:
    arm: str                    # "guardkit" or "vanilla"
    turns_total: int
    files_created: list[str]
    files_modified: list[str]
    test_coverage_pct: float    # -1.0 if not measurable
    lint_violations: int        # -1 if not measurable
    assumptions_explicit: int   # from assumptions.md or evidence/c1.txt
    runnable: bool

@dataclass  
class ComparisonMetrics:
    guardkit: ArmMetrics
    vanilla: ArmMetrics
    
    def coverage_delta(self) -> float:
        """Positive = GuardKit better."""
        if self.guardkit.test_coverage_pct < 0 or self.vanilla.test_coverage_pct < 0:
            return 0.0
        return self.guardkit.test_coverage_pct - self.vanilla.test_coverage_pct
    
    def lint_delta(self) -> int:
        """Negative = GuardKit better (fewer violations)."""
        return self.guardkit.lint_violations - self.vanilla.lint_violations
    
    def assumption_surfacing_delta(self) -> int:
        """Positive = GuardKit surfaced more explicitly."""
        return self.guardkit.assumptions_explicit - self.vanilla.assumptions_explicit
```

These metrics are included in the judge's context to ground the LLM scoring with quantitative data.

---

## 8. Judge Prompt for Comparison Evals

The judge receives both trajectories plus the comparison metrics. The prompt emphasises delta scoring:

```
You are judging a GuardKit vs Vanilla comparison eval.

## Requirement
{input_text}

## Quantitative Metrics
GuardKit arm:
  - Turns: {guardkit.turns_total}
  - Test coverage: {guardkit.test_coverage_pct}%
  - Lint violations: {guardkit.lint_violations}
  - Explicit assumptions surfaced: {guardkit.assumptions_explicit}
  - Runnable: {guardkit.runnable}

Vanilla arm:
  - Turns: {vanilla.turns_total}
  - Test coverage: {vanilla.test_coverage_pct}%
  - Lint violations: {vanilla.lint_violations}
  - Explicit assumptions surfaced: {vanilla.assumptions_explicit}
  - Runnable: {vanilla.runnable}

## GuardKit Run Log
{guardkit_run_log}

## Vanilla Run Log
{vanilla_run_log}

## GuardKit SUMMARY.md
{guardkit_summary}

## Vanilla SUMMARY.md
{vanilla_summary}

Score each criterion as a DELTA:
  1.0 = GuardKit clearly better
  0.5 = Roughly equal
  0.0 = Vanilla equal or better

Return JSON: {"scores": {"c1": {"score": float, "reasoning": str}, ...}}
```

---

## 9. Graphiti Storage for Comparison Results

Comparison evals store additional fields for cross-run trend analysis:

```json
{
  "eval_id": "EVAL-007",
  "type": "guardkit_vs_vanilla",
  "status": "PASSED",
  "weighted_score": 0.74,
  "guardkit_arm": {
    "turns_total": 31,
    "test_coverage_pct": 87.0,
    "lint_violations": 0,
    "assumptions_explicit": 7,
    "runnable": true
  },
  "vanilla_arm": {
    "turns_total": 28,
    "test_coverage_pct": 62.0,
    "lint_violations": 4,
    "assumptions_explicit": 0,
    "runnable": true
  },
  "deltas": {
    "coverage": "+25pp",
    "lint": "-4 violations",
    "assumptions_surfaced": "+7"
  },
  "input_summary": "YouTube channel stats FastAPI endpoint",
  "notable_findings": [
    "GuardKit surfaced 7 explicit assumptions; vanilla made all silently",
    "Coverage delta +25pp driven by GuardKit's BDD test generation",
    "Vanilla completed in fewer turns but produced 4 lint violations"
  ]
}
```

---

## 10. Using Linear Tickets as Input

Linear tickets are the natural input because they are the real artefact both a GuardKit user and a vanilla Claude Code user would start from. The eval runner resolves them to raw text before either arm runs.

### Resolution Flow

```
Linear ticket URL
    ↓
Linear MCP (if connected) → ticket title + description + acceptance criteria
OR
Web fetch → parse HTML for ticket content
    ↓
Normalise to plain text:
  Title: {title}
  Description: {description}
  Acceptance criteria:
  - {criterion 1}
  - {criterion 2}
    ↓
Write to {workspace}/input.txt (both arms)
```

### Example Input (resolved from Linear ticket)

```
Title: Add YouTube channel statistics endpoint

Description:
We need to expose YouTube channel metrics through our API so the dashboard
can display them. The endpoint should aggregate subscriber count, total view
count, and video count for a given channel ID.

Acceptance criteria:
- GET /youtube/channel/{channel_id}/stats returns 200 with {subscribers, views, videos}
- Returns 404 if channel_id is not found
- Returns 503 with Retry-After header if YouTube API is unavailable  
- Responses cached for 1 hour
- Integration test against YouTube API sandbox
```

This is a realistic, under-specified ticket — exactly the kind of input where the GuardKit pipeline's assumption surfacing should shine.

---

## 11. Example Brief: YouTube MCP Feature

```yaml
eval_id: EVAL-007
title: "GuardKit vs Vanilla — YouTube channel stats endpoint"
type: guardkit_vs_vanilla
priority: high

setup:
  workspace_template: guardkit-project
  vanilla_workspace_template: plain-project
  timeout_minutes: 90
  max_turns_per_arm: 100

input:
  source: text
  text: |
    Title: Add YouTube channel statistics endpoint
    
    We need to expose YouTube channel metrics through our API so the dashboard
    can display them. The endpoint should aggregate subscriber count, total view
    count, and video count for a given channel ID.
    
    Acceptance criteria:
    - GET /youtube/channel/{channel_id}/stats returns subscriber count, views, videos
    - Returns 404 if channel_id is not found
    - Returns 503 with Retry-After if YouTube API is unavailable
    - Responses cached for 1 hour
    - Integration test required

guardkit_arm:
  description: "Feature-spec → system-plan → feature-plan → autobuild"
  
vanilla_arm:
  description: "Vanilla Claude Code — same codebase, no GuardKit"

criteria:
  - id: c1
    description: "GuardKit surfaced explicit assumptions; vanilla made them silently"
    weight: 0.25
    check_type: llm_judge
  - id: c2
    description: "GuardKit produced higher or equal test coverage"
    weight: 0.20
    check_type: deterministic
  - id: c3
    description: "GuardKit code has fewer lint violations"
    weight: 0.20
    check_type: deterministic
  - id: c4
    description: "GuardKit output has clearer architectural rationale"
    weight: 0.20
    check_type: llm_judge
  - id: c5
    description: "Both arms produced runnable result"
    weight: 0.15
    check_type: deterministic

pass_threshold: 0.65
escalate_threshold: 0.40

judge_context: |
  Score on DELTA. A tie = 0.5. GuardKit clearly better = 1.0. Vanilla equal or better = 0.0.
  Key signals for c1: assumptions.md existence and entry count, implicit vs explicit decisions.
  Key signals for c4: ADRs, design comments, CLAUDE.md updates, system-plan output quality.
```

---

## 12. Implementation Tasks

### Task 1: `EvalWorkspace` Fork Support

- **Complexity:** low
- **Files to create/modify:** `eval_workspace.py` (new, extracts from `eval_runner.py`)
- **Acceptance criteria:**
  - [ ] `EvalWorkspace.create_forked_pair(guardkit_template, vanilla_template) -> tuple[Path, Path]`
  - [ ] Each returned path is an independent temp directory
  - [ ] GuardKit workspace seeded from `guardkit_template`; vanilla from `vanilla_template`
  - [ ] Both workspaces have `.eval/evidence/` directory created
  - [ ] `EvalWorkspace.teardown_pair()` removes both directories
  - [ ] Existing `EvalWorkspace.create()` / `teardown()` behaviour unchanged

### Task 2: `InputResolver`

- **Complexity:** low
- **Files to create/modify:** `runners/guardkit_vs_vanilla_runner.py` (new)
- **Acceptance criteria:**
  - [ ] `InputResolver.resolve(brief) -> str` handles `source: text`, `source: file`, `source: linear_ticket`
  - [ ] For `linear_ticket`: fetches via Linear MCP if connected, falls back to web fetch
  - [ ] Resolved text written to `input.txt` in both workspaces before any agent runs
  - [ ] Resolution failure raises `InputResolutionError` with actionable message

### Task 3: `GuardKitVsVanillaRunner`

- **Complexity:** medium
- **Files to create/modify:** `runners/guardkit_vs_vanilla_runner.py`
- **Acceptance criteria:**
  - [ ] Runs Arm A (GuardKit) then Arm B (Vanilla) sequentially
  - [ ] Each arm uses `EvalAgentInvoker` with arm-specific prompt
  - [ ] Publishes `eval.status.{id}` between arms: `phase="arm_a_complete"` / `"arm_b_running"`
  - [ ] Arm failure (agent error) does not abort — records error and continues to judge
  - [ ] Returns `(guardkit_trajectory, vanilla_trajectory)` for judging

### Task 4: `MetricsExtractor`

- **Complexity:** low
- **Files to create/modify:** `runners/guardkit_vs_vanilla_runner.py`
- **Acceptance criteria:**
  - [ ] `MetricsExtractor.extract(guardkit_ws, vanilla_ws) -> ComparisonMetrics`
  - [ ] Reads `.eval/evidence/c2.txt` for coverage, `c3.txt` for lint, `c1.txt` for assumptions
  - [ ] Returns `-1` for metrics that are not present / not measurable (not an error)
  - [ ] `ComparisonMetrics.coverage_delta()`, `lint_delta()`, `assumption_surfacing_delta()` computed correctly

### Task 5: `EvalJudge` Comparison Mode

- **Complexity:** low
- **Files to create/modify:** `eval_judge.py`
- **Acceptance criteria:**
  - [ ] `EvalJudge.evaluate_comparison(brief, guardkit_traj, vanilla_traj, metrics) -> EvalResult`
  - [ ] Deterministic criteria use `ComparisonMetrics` deltas (not evidence files)
  - [ ] LLM judge receives both SUMMARY.md files and quantitative metrics in prompt
  - [ ] Judge prompt instructs delta scoring (1.0 = GuardKit wins, 0.5 = tie, 0.0 = vanilla wins)
  - [ ] `EvalResult.to_graphiti_episode()` includes `guardkit_arm`, `vanilla_arm`, `deltas` fields

### Task 6: Brief Schema Extension

- **Complexity:** low
- **Files to create/modify:** `eval_schemas.py`
- **Acceptance criteria:**
  - [ ] `EvalBrief` handles `type: guardkit_vs_vanilla`
  - [ ] `GuardKitVsVanillaBrief` dataclass with `input`, `guardkit_arm`, `vanilla_arm` fields
  - [ ] `InputSource` enum: `text`, `file`, `linear_ticket`
  - [ ] `EvalBrief.from_yaml()` dispatches to correct subclass based on `type` field

### Task 7: `EvalRunner` Dispatch

- **Complexity:** low
- **Files to create/modify:** `eval_runner.py`
- **Acceptance criteria:**
  - [ ] `process_brief()` dispatches to `GuardKitVsVanillaRunner` when `brief.type == "guardkit_vs_vanilla"`
  - [ ] Existing `integration`, `regression`, `baseline-comparison` dispatch unchanged
  - [ ] Timeout calculation uses `brief.setup.timeout_minutes * 60 * detect_timeout_multiplier()`

### Task 8: Example Brief and Workspace Templates

- **Complexity:** low
- **Files to create/modify:** `briefs/EVAL-007-guardkit-vs-vanilla-youtube.yaml`, `workspaces/guardkit-project/`, `workspaces/plain-project/`
- **Acceptance criteria:**
  - [ ] `EVAL-007-guardkit-vs-vanilla-youtube.yaml` matches schema above
  - [ ] `workspaces/guardkit-project/` has `CLAUDE.md`, `.guardkit/commands/`, `pyproject.toml`
  - [ ] `workspaces/plain-project/` has same codebase structure, no `CLAUDE.md`, no `.guardkit/`
  - [ ] Both templates have an installable Python project (so `pip install -e .` works in the workspace)

---

## 13. Open Questions

| Question | Context | Recommendation |
|---|---|---|
| Should arms run in Docker? | Vanilla arm needs clean env guarantee — no accidental guardkit in PATH | Use Docker for vanilla arm. GuardKit arm can use temp dir since it controls its own config. |
| What if vanilla Claude Code discovers and uses guardkit? | Claude Code might find `.guardkit/` somewhere on PATH or via pip | Ensure `plain-project` template has `pip uninstall guardkit` in setup script |
| Should we measure subjective code quality? | Hard to define, easy to dispute | Stick to measurable proxies: coverage, lint violations, test count, file count. Let LLM judge assess architectural rationale. |
| Multiple runs per brief? | Single run is noisy — Claude Code output is non-deterministic | Run 3× and report median. Add `runs: 3` to brief schema later. |
| What if GuardKit arm fails partway? | e.g. `feature-spec` succeeds but `autobuild` fails | Still judge what was produced. Partial output is a valid comparison data point. |
