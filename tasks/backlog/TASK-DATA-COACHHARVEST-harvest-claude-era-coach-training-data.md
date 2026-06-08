---
id: TASK-DATA-COACHHARVEST
title: Harvest preserved Claude-era Coach trajectories + verdict pairs into a training-ready corpus
status: backlog
task_type: ops
created: 2026-06-08T00:00:00Z
updated: 2026-06-08T00:00:00Z
priority: high
complexity: 4
effort_hours: 4
parent_task: TASK-HMIG-010
related: [TASK-FIX-COACHSCHEMA, TASK-OPS-COACHGRAMMAR]
implementation_mode: direct
intensity: standard
---

# Task: Harvest preserved Claude-era Coach training data into a clean corpus

## Why this task exists

**Strategic context (cost-driven local Coach).** Anthropic API tokens are
prohibitively expensive for non-client development work, so AutoBuild needs a
capable **local** Coach. Runs 12–14 proved the current local Coach substrate
(base Gemma 4 26B-A4B-IT, 3.8B active) **cannot** do reliable agentic verdict
emission — and that grammar enforcement (Path 1A, no-op), prompt-tightening
(Path 1B, TASK-FIX-COACHSCHEMA), and bigger timeouts (`--sdk-timeout 3600`) all
failed. The substrate must change. Two non-hardware options are on the table:
(a) a **bigger/QAT base** (Gemma 4 31B dense QAT — 30.7B active, ~17.7 GB,
≈ same memory as today's Coach), and (b) **distilling Coach behaviour** from a
strong teacher (Claude) into a local model — *pay the teacher once, run free
forever* (the economics that fit the cost constraint).

This task builds the **dataset for (b)** by harvesting the Coach training data
that *already exists* from past AutoBuild runs that used Claude Sonnet — before
any of it is lost. A GB10 forensic sweep on 2026-06-08 confirmed it is **not**
all lost, but it is **scattered across 10 repos** and mixed with weak-model
(post-migration) runs that must be excluded.

## Preserved data inventory (forensic sweep, 2026-06-08)

Three tiers — confirmed counts:

### Tier A — verdict pairs (abundant, immediately usable)
- **776 `coach_turn_*.json`** + **738 `player_turn_*.json`** across
  `~/Projects/appmilla_github/{guardkit(307), forge(119), jarvis(108),
  study-tutor(77), agentic-dataset-factory(48), nats-core(30), api_test(29),
  nats-infrastructure(20), specialist-agent(10+5)}` (in `.guardkit/autobuild/<task>/`).
- Date split: **2026-02 (317), 03 (48), 04 (244), 05 (167)**. The local-model
  migration was ~late-April/May 2026 (findings doc dated 2026-05-14). So the
  **~365 Feb–Mar verdicts are Claude-era** (teacher quality); May+ are the weak
  local model (EXCLUDE — that's what we're trying to beat).
- Each verdict is rich: `decision`, `validation_results`, `criteria_verification`,
  `issues`, `rationale`. **~81 of the Claude-era ones carry full
  `criteria_verification`**; the rest are simpler/older-format.
- **No model field is recorded** in the verdict files → provenance is **by date
  only**. The harvester MUST filter on the pre-migration window and should let the
  operator tune the cutoff.
- Pair `coach_turn_N.json` with its sibling `player_turn_N.json` (the Coach's
  INPUT) + the task file → `(task, player_report) → coach_verdict` triples. These
  teach **verdict judgment + schema discipline** (the run-12 problem), NOT the
  tool-use trajectory.

### Tier B — full agentic trajectories (scarce, GOLD)
- Only **~4–6 genuine** Claude-era full Coach trajectories survive, as Claude
  Code **Task-subagent transcripts** at
  `~/.claude.backup.*/projects/*/subagents/agent-*.jsonl` (and a few in
  `~/.claude/projects/...`), from `/feature-build` runs (mostly guardkit, Feb–Apr).
- Each is *complete*: e.g. one had **614 json lines, 85 assistant msgs, 58
  tool_use + 58 tool_result** — the whole read-files → run-tests → reason →
  emit-verdict behaviour. **This is the premium data for the run-13/14
  convergence fix** (it shows the *trajectory*, not just the answer).
- ⚠️ **De-dupe / filter false positives**: grepping `"You are the Coach"` also
  hits (a) this 2026-06-08 GB10 analysis session's own transcripts + design
  workflows, and (b) May+ study-tutor runs that may be local-model. Exclude both.

### What is LOST
- The full LLM streams for the **~760 CLI (`guardkit autobuild`) runs** — the
  orchestrator persists only the final verdict **by design** (confirmed: zero
  `agent-*.jsonl` dumps inside any repo; run-13/14-artifacts READMEs say the
  same). Those survive as Tier-A verdicts, not trajectories.

## What to do

Write a **read-only harvester** (a Python script, e.g.
`scripts/harvest_coach_dataset.py`) that:

1. **Sweeps** `~/Projects/appmilla_github/*/` for `.guardkit/autobuild/<task>/`
   dirs; for each, pairs `coach_turn_N.json` ↔ `player_turn_N.json` ↔ the task
   file (requirements + acceptance_criteria).
2. **Filters by date** (default: keep `mtime < 2026-04-15`, operator-tunable via
   `--cutoff`) to isolate the Claude-era teacher set; tags each example with its
   source repo, task id, turn, date, and a `schema_complete` flag
   (has full `criteria_verification`).
3. **Sweeps** `~/.claude.backup.*/projects/*/subagents/agent-*.jsonl` +
   `~/.claude/projects/.../subagents/*.jsonl` for transcripts containing the Coach
   prompt AND ≥1 `tool_use` block; **excludes** the 2026-06-08 GB10-session
   transcripts and design-workflow agents (path contains `/workflows/` or dates
   `2026-06-08`) and May+ study-tutor (operator-confirm each Tier-B file).
4. **Exports** to a clean corpus:
   - `coach_verdict_pairs.jsonl` — Tier A: `{task, player_report, verdict}` per line.
   - `coach_trajectories.jsonl` — Tier B: full message streams (system, user,
     assistant w/ tool_use, tool_result, final verdict), one trajectory per line
     or per file.
   - `MANIFEST.md` — hard counts: total pairs, schema-complete pairs, Claude-era
     pairs by repo, Tier-B trajectory count, what was excluded and why.
5. Writes to a NEW dir (e.g. `~/coach-dataset/` or a `--out` path) — does NOT
   modify any source repo.

## Acceptance criteria

- [ ] **AC-1**: `harvest_coach_dataset.py` runs read-only, sweeps all 10 repos +
  the `~/.claude*` transcript dirs, and produces `coach_verdict_pairs.jsonl`,
  `coach_trajectories.jsonl`, and `MANIFEST.md`.
- [ ] **AC-2**: Verdict pairs are correctly joined (`coach_turn_N` ↔
  `player_turn_N` ↔ task) and date-filtered; the MANIFEST gives the hard count
  of **schema-complete, Claude-era** pairs (this number decides whether Tier A
  alone is worth a fine-tune vs needing the factory to generate the bulk).
- [ ] **AC-3**: Tier-B trajectories exclude the 2026-06-08 GB10-session /
  design-workflow false positives and any local-model runs; each retained
  trajectory contains the Coach prompt + ≥1 tool_use/tool_result pair + a final
  verdict.
- [ ] **AC-4**: MANIFEST documents the provenance method (date-based, no model
  field) and lists per-repo counts so the operator can sanity-check the
  Claude-era classification.

## Implementation notes

- **This is a SEED + validation set, not a complete training set.** Tier A
  (~81–365 pairs) can bootstrap the *judgment/schema* dimension; Tier B (~4–6
  trajectories) is too few to train *agentic convergence* alone but is perfect as
  golden few-shot templates + a validation set + seeds the
  **agentic-dataset-factory** imitates to generate the bulk.
- **Intended downstream use**: distill into a QAT base. Per the substrate
  analysis, the eventual fine-tune base should be **Gemma 4 31B dense QAT**
  (`google/gemma-4-31B-it-qat-q4_0-unquantized` for training, re-quantize after),
  not the 3.8B-active 26B-A4B that runs 12–14 proved insufficient.
- **Provenance is date-only** — no model field exists in the verdicts. If any run
  log survives that records `coach_model`, cross-reference it to sharpen the
  Claude-era classification.

## Related

- **Substrate problem**: runs 12–14 ([autobuild-FEAT-AOF-run-14.md](../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-14.md), [run-14-artifacts](../../docs/state/TASK-REV-HMIG/run-14-artifacts/README.md))
- **Path 1A (no-op)**: [TASK-OPS-COACHGRAMMAR](autobuild-harness-migration/TASK-OPS-COACHGRAMMAR-enforce-coach-verdict-schema-via-llama-cpp-gbnf.md)
- **Path 1B (failed)**: [TASK-FIX-COACHSCHEMA](autobuild-harness-migration/TASK-FIX-COACHSCHEMA-tighten-coach-prompt-schema-emission.md)
- **Generation harness**: `~/Projects/appmilla_github/agentic-dataset-factory` (Player-Coach loop; has `domains/architect-agent`, `gcse-english-tutor` — add a `domains/autobuild-coach`)
- **Gemma 4 QAT lineup**: `google/gemma-4-{26B-A4B,31B}-it-qat-q4_0-{gguf,unquantized}` on HuggingFace
