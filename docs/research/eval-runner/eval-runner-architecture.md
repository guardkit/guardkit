# GuardKit Eval Runner — Architecture & Implementation

**Project:** guardkit/eval-runner  
**Status:** Design — ready for `/system-plan`  
**Date:** February 2026  

---

## 1. Purpose

GuardKit AutoBuild has a growing backlog of untested features — design mode (Figma/Zeplin), the `/feature-spec` command, assumption detection, Graphiti local embeddings, and the YouTube MCP pipeline. The constraint is not implementation capacity; it is human orchestration. Testing each feature requires manually briefing an agent, monitoring runs, and reviewing outputs.

The Eval Runner removes this bottleneck. It is an autonomous loop that:

1. Picks up YAML eval briefs from a NATS JetStream work queue
2. Provisions a sandboxed workspace per eval run
3. Runs the eval agent via Claude Agent SDK (same patterns as AutoBuild Player)
4. Judges results via deterministic checks + LLM-as-judge
5. Stores outcomes in Graphiti for cross-run querying
6. Escalates low-confidence or failed evals to a NATS topic for human review

Write briefs one evening. Review Graphiti results the next morning.

---

## 2. Grounding in Proven Patterns

All SDK invocation is built directly on `guardkit/orchestrator/agent_invoker.py`. No new patterns are invented.

| Pattern | Source in `agent_invoker.py` | Eval Runner usage |
|---|---|---|
| SDK invocation core | `_invoke_with_role()` | `EvalAgentInvoker._invoke_sdk()` |
| Local vLLM 4× timeout | `detect_timeout_multiplier()` | Identical — reads `ANTHROPIC_BASE_URL` |
| Progress heartbeat | `async_heartbeat()` | Identical — 30s interval |
| Async cleanup noise | `_install_sdk_cleanup_handler()` | Identical |
| SDK bug #472 defence | `check_assistant_message_error()` | Imported from `sdk_utils.py` |
| Stream parsing | `AssistantMessage / TextBlock / ToolUseBlock` loop | Identical iteration |
| Timeout constants | `DEFAULT_SDK_TIMEOUT`, `MAX_SDK_TIMEOUT` | `DEFAULT_EVAL_TIMEOUT`, `MAX_EVAL_TIMEOUT` |
| Permission model | `permission_mode="acceptEdits"` (Player) | Eval agent uses same model |

The eval agent is equivalent to the Player. The judge uses the Anthropic API directly (like `coach_verification.py`) to ensure consistent scoring quality even when the eval agent runs on local vLLM.

### Environment Configuration

```bash
# Cloud mode — Anthropic API for both agent and judge
ANTHROPIC_API_KEY=sk-ant-...

# Local vLLM mode — GB10 for agent, Anthropic API for judge
ANTHROPIC_BASE_URL=http://localhost:8000/v1
ANTHROPIC_API_KEY=sk-ant-...   # still needed for judge

# Optional overrides
GUARDKIT_EVAL_TIMEOUT=1800     # base timeout seconds (default 30 min)
GUARDKIT_TIMEOUT_MULTIPLIER=4  # explicit override (usually auto-detected)
```

No configuration changes are needed to switch between local and cloud — same env vars as AutoBuild.

---

## 3. System Architecture

### 3.1 Component Map

| Component | File | Role |
|---|---|---|
| `EvalAgentInvoker` | `eval_agent_invoker.py` | Runs eval agent via Claude Agent SDK. Mirrors `AgentInvoker`. |
| `EvalJudge` | `eval_judge.py` | Deterministic + LLM scoring of agent trajectories. |
| `EvalRunner` | `eval_runner.py` | NATS subscriber — orchestrates brief → agent → judge → store. |
| `BriefWatcher` | `brief_watcher.py` | Publishes YAML brief files to NATS. CLI: `--publish`, `--publish-all`. |
| `EvalWorkspace` | `eval_workspace.py` | Temp directory seeded from template. Fork support for A/B runs. |
| `EvalBrief` | `eval_schemas.py` | Parsed YAML brief. Loaded via `EvalBrief.from_yaml()`. |
| `EvalResult` | `eval_schemas.py` | Scored result. Serialises to Graphiti episode JSON. |
| `Trajectory` | `eval_agent_invoker.py` | Accumulated SDK stream content for judge consumption. |

### 3.2 Message Flow

```
briefs/EVAL-001.yaml
       ↓  brief_watcher.py --publish
eval.briefs.pending  (NATS JetStream work queue — exactly-once delivery)
       ↓  eval_runner.py subscribes
EvalWorkspace.create()  →  temp dir seeded from template
       ↓
EvalAgentInvoker.invoke(brief)  →  Trajectory
       ↓
EvalJudge.evaluate(brief, trajectory, workspace)  →  EvalResult
       ↓                            ↓
eval.results.{eval_id}    eval.escalate.{eval_id}   (NATS)
       ↓
Graphiti  ←  result.to_graphiti_episode()
       ↓
results/{eval_id}.json   (local cache)
```

### 3.3 NATS Topic Namespace

| Topic | Publisher | Subscriber | Content |
|---|---|---|---|
| `eval.briefs.pending` | `brief_watcher.py` | `eval_runner.py` | Brief payload: `eval_id`, `brief_path`, `type`, `priority` |
| `eval.results.{id}` | `eval_runner.py` | Dashboard / Human | Outcome: `status`, `weighted_score`, `run_date` |
| `eval.escalate.{id}` | `eval_runner.py` | Rich (human) | Escalation: `reason`, `score`, `action_required` |
| `eval.status.{id}` | `eval_runner.py` | Dashboard | Progress: `phase`, `detail` (best-effort) |

---

## 4. YAML Brief Schema

All eval briefs live in `briefs/` as YAML files. Two types are in active use:

### 4.1 Integration Brief

```yaml
eval_id: EVAL-001
title: "Design Mode — Figma Community file integration"
type: integration       # integration | regression | baseline-comparison | chain | guardkit_vs_vanilla
priority: high
tags: [design-mode, figma, react]

setup:
  workspace_template: react-app-empty
  timeout_minutes: 30

objective: |
  Given a public Figma URL, verify design mode produces a working
  React component with extracted design tokens.

agent_instructions: |
  1. Find a public Figma Community file
  2. Run: guardkit design-mode --figma-url <url>
  3. Check component compiles: npx tsc --noEmit
  4. Write .eval/evidence/{criterion_id}.txt for each criterion
  5. Write SUMMARY.md

criteria:
  - id: c1
    description: "Agent retrieved a public Figma design"
    weight: 0.10
    check_type: deterministic
  - id: c2
    description: "React component has meaningful design structure"
    weight: 0.35
    check_type: llm_judge

pass_threshold: 0.70
escalate_threshold: 0.40
```

### 4.2 GuardKit vs Vanilla Brief

See `eval-runner-guardkit-vs-vanilla.md` for the full schema and implementation design for this eval type.

---

## 5. Judging Pipeline

### 5.1 Two-Phase Evaluation

| Phase | Mechanism | Cost | Speed |
|---|---|---|---|
| Deterministic | Filesystem checks, evidence file parsing, exit code signals | Free | Instant |
| LLM Judge | Direct Anthropic API call to `claude-sonnet-4-6` | ~$0.01–0.05 per eval | 5–30s |

The LLM judge always uses Anthropic API regardless of what model the eval agent used — ensures consistent scoring quality across local and cloud runs.

### 5.2 Evidence Convention

The eval agent writes criterion evidence files at:

```
.eval/evidence/{criterion_id}.txt
```

This gives deterministic checks a reliable filesystem location and gives the LLM judge focused per-criterion context rather than the full trajectory. The eval agent's system prompt requires these files in every run.

### 5.3 Escalation Logic

| Weighted Score | Outcome | Action |
|---|---|---|
| ≥ `pass_threshold` (e.g. 0.70) | PASSED | Stored in Graphiti |
| < `pass_threshold`, ≥ `escalate_threshold` | FAILED | Stored as actionable issue in Graphiti |
| < `escalate_threshold` (e.g. 0.40) | ESCALATED | Published to `eval.escalate.{id}` for human review |
| SDK/agent error | ERROR | Published to `eval.escalate.{id}` with full error |

---

## 6. Graphiti Storage Schema

Each completed eval is stored as a Graphiti episode:

```json
{
  "eval_id": "EVAL-001",
  "title": "Design Mode — Figma",
  "status": "PASSED",
  "weighted_score": 0.82,
  "pass_threshold": 0.70,
  "run_date": "2026-02-28T09:14:00Z",
  "duration_minutes": 18.4,
  "model_used": "claude-sonnet-4-6",
  "cost_usd": 0.03,
  "criterion_scores": {
    "c1": { "score": 1.0, "reasoning": "Evidence file confirms Figma URL fetched" },
    "c3": { "score": 0.75, "reasoning": "Compiled, 1 minor type warning" }
  },
  "notable_failures": [],
  "notable_successes": ["Design tokens extracted correctly"],
  "next_actions": ["Fix colour token → CSS variable mapping"]
}
```

Query patterns:

```
"Which evals failed in the last two weeks?"
"What are recurring failure patterns in design-mode?"
"Has /feature-spec improved Coach feedback cycles across three runs?"
"What is the GuardKit vs Vanilla score delta for the YouTube MCP feature?"
```

---

## 7. File Structure

```
eval-runner/
├── briefs/                              # YAML eval briefs (git versioned)
│   ├── EVAL-001-design-mode-figma.yaml
│   ├── EVAL-002-feature-spec-comparison.yaml
│   ├── EVAL-007-guardkit-vs-vanilla-youtube.yaml
│   └── ...
├── workspaces/                          # Workspace templates
│   ├── react-app-empty/
│   ├── fastapi-minimal/
│   ├── guardkit-project/                # Has CLAUDE.md + .guardkit/ set up
│   └── blank/
├── results/                             # Local result cache (JSON)
├── eval_schemas.py                      # EvalBrief, EvalResult, data classes
├── eval_agent_invoker.py                # SDK invocation — mirrors agent_invoker.py
├── eval_judge.py                        # Deterministic + LLM judge
├── eval_runner.py                       # NATS subscriber — main orchestrator
├── eval_workspace.py                    # EvalWorkspace with fork() for A/B runs
├── brief_watcher.py                     # Publishes briefs to NATS
├── runners/
│   ├── integration_runner.py            # Handles type: integration, regression
│   ├── baseline_runner.py               # Handles type: baseline-comparison
│   └── guardkit_vs_vanilla_runner.py    # Handles type: guardkit_vs_vanilla
└── requirements.txt
```

---

## 8. Decision Log

| ID | Decision | Rationale | Alternatives Considered |
|---|---|---|---|
| D1 | Reuse `agent_invoker.py` patterns verbatim | These patterns are proven in production. No new SDK risk. | Invent new patterns — rejected, unnecessary risk |
| D2 | Judge always uses Anthropic API | Consistent scoring across local/cloud agent runs | Local model for judge — rejected, inconsistent scoring |
| D3 | Evidence files at `.eval/evidence/{id}.txt` | Gives deterministic judge a reliable location without parsing trajectories | Parse trajectory only — rejected, too fragile |
| D4 | NATS JetStream work queue for brief delivery | Exactly-once delivery, retry on failure, matches Ship's Computer architecture | File polling — rejected, no retry semantics |
| D5 | Temp directories for workspace isolation | Fast, no Docker dependency, sufficient for most evals | Docker containers — reconsidered for `guardkit_vs_vanilla` (see separate spec) |
| D6 | ESCALATED status for score < `escalate_threshold` | Human review for genuinely uncertain results vs just FAILED | Binary pass/fail — rejected, loses escalation signal |
| D7 | `guardkit_vs_vanilla` as a first-class eval type | The most valuable eval — validates the entire GuardKit value proposition | Treat as two sequential integration evals — rejected, loses the comparison semantic |

---

## 9. Implementation Phases

| Phase | Scope | Effort | Validation |
|---|---|---|---|
| 1 — Scaffolding | Directory structure, schemas, brief watcher, basic NATS pub/sub | 1 day | Publish EVAL-001 and see it received |
| 2 — Agent | `EvalAgentInvoker` wired up, saves trajectory. No judging yet | 1 day | EVAL-001 runs command and creates SUMMARY.md |
| 3 — Judge | Deterministic + LLM judge, NATS results. EVAL-001 end-to-end | 1 day | EVAL-001 produces scored `EvalResult` |
| 4 — Graphiti + Escalation | Store results, escalation path | 0.5 day | Results queryable in Graphiti |
| 5 — Baseline Comparison | Two-run pattern for EVAL-002 | 1 day | EVAL-002 produces comparative result |
| 6 — GuardKit vs Vanilla | Fork workspace, dual-pipeline runner, delta judge | 1.5 days | EVAL-007 produces A/B delta result |
| 7 — Backlog Clearance | Write remaining briefs, run all evals | 2 hours writing + overnight | Full backlog results in Graphiti |

---

## 10. Open Questions

| Question | Options | Recommendation |
|---|---|---|
| Eval Runner location | MacBook (simpler) vs Spark (collocated with local models) | MacBook for Phase 1–5. Move to Spark if eval agent benefits from local models. |
| Workspace isolation depth | Temp dirs (current) vs Docker containers | Temp dirs for integration evals. `guardkit_vs_vanilla` warrants Docker for clean environment guarantee. |
| Escalation UX | NATS topic only vs desktop notification | NATS + Graphiti first. Add notification once proven. |
| Linear ticket as input | Manual copy-paste vs Linear MCP integration | Manual for now, Linear MCP when Ship's Computer pipeline is live. |
