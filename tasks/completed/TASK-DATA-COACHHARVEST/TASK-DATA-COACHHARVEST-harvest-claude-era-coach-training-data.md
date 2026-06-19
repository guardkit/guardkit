---
id: TASK-DATA-COACHHARVEST
title: Harvest preserved Claude-era Coach trajectories + verdict pairs into a training-ready corpus
status: completed
task_type: ops
created: 2026-06-08T00:00:00Z
updated: 2026-06-19T00:00:00Z
completed: 2026-06-19T00:00:00Z
completed_location: tasks/completed/TASK-DATA-COACHHARVEST/
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

> **Update 2026-06-11**: TASK-ARCH-COACHSPLIT's toolless grammar-constrained
> synthesis was validated 2026-06-09 — verdict JSON/schema validity is now
> enforced at serving time via GBNF. The fine-tune target is therefore
> **verdict judgment quality**, not schema emission (the run-12 rationale has
> partially expired). This shifts the value of this corpus toward the
> outcome-joined examples (AC-5) and away from raw pair volume.

> **Update 2026-06-19 (readiness review — run-readiness + scope upgrade).**
> A forensic re-sweep on the GB10 (`promaxgb10-41b1`, the same box as the
> 2026-06-08 sweep) found the inventory below has both **drifted** and **grown
> a much better source**. Four load-bearing corrections — the implementation
> steps and ACs that follow are updated to match:
>
> 1. **The guardkit set is NOT lost — but the AC-1 glob would miss it.** Live
>    `guardkit/.guardkit/autobuild/` now holds only **2** files (both
>    2026-06-12); the ~305 "missing" Claude-era pairs were git-untracked +
>    gitignored on 2026-04-12 by commit `d7f14b0e7` (TASK-AC-001, *"local copies
>    preserved"*) and locally pruned. They survive in **git main history** at
>    `d7f14b0e7^` (an ancestor of `main`: **333 coach + 319 player**, blobs
>    intact, recoverable READ-ONLY via `git -C guardkit show d7f14b0e7^:<path>`
>    — never a working-tree checkout), and live on disk in the **TASK-GLI-004
>    worktree** (`guardkit/.guardkit/worktrees/TASK-GLI-004/.guardkit/autobuild/`,
>    300/263, genuine Feb-23 originals). **AC-1's top-level
>    `*/.guardkit/autobuild/` glob does not recurse into `worktrees/` → as
>    written it reaches 2 guardkit files, not 307.** Fix mandated in step 1.
> 2. **Provenance-by-harness reveals ~450 rich teacher pairs, NOT the ~63 a date
>    cutoff implies (corrected 2026-06-19 after a per-repo harness audit).** A
>    date-only classification wrongly tags April–May runs as "local-era"; reading
>    the committed run-logs shows the GuardKit autobuild **harness stayed on
>    Claude SDK / Claude Code (`claude-agent-sdk 0.1.66`) through April–May for
>    EVERY repo audited.** The gemma/qwen/llama-swap/`:9000` strings in those
>    repos are the **apps under test** (jarvis = local LangGraph voice agent,
>    study-tutor/forge/specialist build local-LLM products), NOT the build
>    harness — the exact trap point 4 warns about. Per-repo teacher-quality (rich,
>    Claude-harness, `confidence: high`):
>
>    | repo | rich pairs | harness | dates | note |
>    |---|---|---|---|---|
>    | fleet-memory | 75 | claude_sdk | Jun | FEAT-MEM-01…07; has false-positive-gate retro (feedback turns) |
>    | forge | 120 | claude_code | Apr | Cloud rate-limits in log = Anthropic, not local |
>    | jarvis | 108 | claude_code | Apr–May | 97 approve / 11 feedback |
>    | study-tutor | 77 | claude_sdk | Apr–May | incl. fail-run/reject turns (adversarial depth) |
>    | agentic-dataset-factory | 46 | claude (Mar) | Mar | pure Claude-era |
>    | api_test | 17 | claude (Feb) | Feb | 17/17 rich |
>    | specialist-agent | 5 (10 files, dup dir) | claude_code | Apr | all approve, turn-1 (low depth) |
>    | **GB10 total now** | **≈448** | — | — | + ~30–50 guardkit git-recovery rich; + ~40 lpa after the Mac step |
>
>    The guardkit Feb worktree/git set (~300) stays ~92% **thin** (volume/eval
>    only). So the rich Claude-harness teacher corpus is **~448 reachable on the
>    GB10 today, ~490+ with lpa** — well past the threshold for a *meaningful*
>    fine-tune, not the ~63 a naive date filter would have salvaged.
> 3. **NEW + BETTER source — the 2026-06 Claude-SDK runs (operator-confirmed
>    Claude SDK harness).** Recent, rich, in-distribution teacher data; now the
>    PRIMARY harvest target over the decaying Feb set:
>    - **fleet-memory: 75 coach + 76 player, git-TRACKED, already on the GB10**
>      (synced Mac→GB10 via git — this repo does NOT gitignore its autobuild dir;
>      mtime 2026-06-17 = checkout date, not run date). Rich
>      (`criteria_verification` populated). Campaign FEAT-MEM-01…07 — retros in
>      `fleet-memory/docs/retros/`.
>    - **lpa-platform-poc: Claude-SDK voice-autobuild runs (FEAT-POC-004 ~15,
>      FEAT-POC-006 ~14, FEAT-5A64 ~10–15 pairs; POC-005 ~17 low-value re-run;
>      FEAT-9A4B failed = exclude) ≈ 37–46 usable pairs — STILL stranded on the
>      MacBook.** Root cause: `.guardkit/autobuild/` is gitignored on BOTH
>      machines (lpa `.gitignore:235`), and the "harvest" commit `9589c61`
>      force-added only summaries (`events.jsonl`/`review-summary.md`/`progress.log`),
>      NOT the per-turn JSON — so the commit+pull moved zero coach/player turns.
>      **Recovery is a Mac-side step:** on the Mac, first VERIFY the JSON still
>      exists (`find .guardkit -name 'coach_turn_*.json' | wc -l`), then
>      `git add -f '.guardkit/**/coach_turn_*.json' '...player_turn_*.json'
>      '...task_work_results.json'`, commit, push; pull on the GB10. (Or rsync the
>      gitignored files directly over Tailscale.) **FEAT-POC-006 is the
>      green-but-broken case that seeded
>      `.claude/rules/per-task-green-is-not-feature-green.md`** — exactly the AC-5
>      false-approval hard-negative material (relabel, don't distil-as-approve).
> 4. **Provenance axis is HARNESS, not date.** `coach_turn_*.json` carries **no
>    model field**, and mtime is unreliable (git checkout re-stamps it; copied
>    repos inode-touch). The Claude-SDK weekend runs are dated 2026-06 yet are
>    teacher quality; April/May local runs are also mid-2026 by mtime. The
>    reliable discriminator is the **harness** (Claude SDK / Claude Code vs
>    LangGraph + llama-swap local), read from the **committed retros + run logs**
>    (`docs/**/autobuild-*.md`, `docs/reviews/autobuild-migration/`), which name
>    the substrate. Tag every harvested pair `provenance: claude_sdk |
>    claude_code | local | unknown` and gate teacher-distillation on
>    `claude_sdk`/`claude_code`, NOT on `mtime < cutoff` (keep the date cutoff
>    only as a coarse secondary signal).
>
> **Net readiness:** RUN IT — read-only, low-risk, and the corpus is decaying out
> of accessible paths (the guardkit prune is the warning shot). The provenance
> correction (point 2) **changes the fine-tune calculus**: with ~448–490 rich
> Claude-harness pairs the dataset now **crosses the threshold for a *meaningful*
> LoRA on the 26B-A4B MoE** (the validated 71-min GB10 recipe applies) — so a
> fine-tune is genuinely viable as a **judgment-quality / reasoning-economy
> investment**, which is the right way to judge it. Two guardrails stand:
> (a) it is NOT the fix for the *live* false-greens — those are *structural* and
> already gated by TASK-AB-PERTASKFG01 / TASK-AB-WIREGATE01 / the post-wave smoke
> gate (so judge a fine-tune on "is the Coach's judgment better," not "did the
> false-greens stop"); and (b) the corpus is **approve-skewed and contains the
> old Coach's blind spots** (jarvis 97/108 approve; specialist 5/5; lpa FEAT-POC-006
> "green-but-broken" approved) — so the **AC-5 outcome-join is mandatory**: distil
> the outcome-verified *clean* set, up-weight the scarcer feedback/reject turns
> (study-tutor fail-runs, jarvis's 11, fleet-memory's MEM-07), and relabel the
> false-approvals (POC-006) as hard negatives — never raw-distil all approves, or
> you train a more confident rubber-stamp. The fine-tune **base** decision
> (Gemma-4 26B-A4B MoE, per TASK-OPS-COACHMOE01) still holds.

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

1. **Sweeps RECURSIVELY** for `**/.guardkit/autobuild/<task>/` under
   `~/Projects/appmilla_github/*/` — the glob MUST descend into
   `.guardkit/worktrees/*/.guardkit/autobuild/` (where ~300 of the guardkit
   Claude-era pairs live) and de-duplicate worktree copies against the canonical
   run by `(repo, task_id, turn, content-hash)`. For each dir, pairs
   `coach_turn_N.json` ↔ `player_turn_N.json` (tolerating an unmatched sibling —
   e.g. agentic-dataset-factory is 48 coach / 49 player) ↔ the task file
   (requirements + acceptance_criteria). For **guardkit**, also read the
   pre-prune set READ-ONLY from git history at `d7f14b0e7^`
   (`git -C guardkit show d7f14b0e7^:.guardkit/autobuild/<task>/coach_turn_N.json`,
   333/319) rather than a working-tree checkout. **Names ALL sources the glob
   actually hits** in the MANIFEST, including the unannounced `fleet-memory` and
   `specialist-agent-backup-2026-05-06` (the "+5") directories.
   - **PRIMARY source (2026-06 Claude-SDK runs — see Update 2026-06-19):**
     `fleet-memory/.guardkit/autobuild/` (75/76, git-tracked, on the GB10, rich)
     and the **lpa-platform-poc** voice-autobuild runs (FEAT-POC-004/005/006,
     FEAT-5A64, FEAT-9A4B) — the latter's artefacts are on the **MacBook**, so
     the harvester must be run there too (or those dirs committed/rsync'd to the
     GB10 first). These are operator-confirmed Claude SDK = teacher quality and
     supersede the decaying Feb set in value.
2. **Classifies provenance by HARNESS, not date.** Tags each example
   `provenance: claude_sdk | claude_code | local | unknown` by cross-referencing
   the run's **committed retro / run log** (`docs/**/autobuild-*.md`,
   `docs/reviews/autobuild-migration/` — markers: `--coach-model`, `qwen`,
   `gemma4`, `OPENAI_BASE_URL=...:9000`, llama-swap = `local`; Claude SDK / Claude
   Code CLI = teacher). Keep `--cutoff` (default `mtime < 2026-04-15`) only as a
   coarse SECONDARY signal — mtime is unreliable (git checkout re-stamps it).
   Also tags source repo, task id, turn, date, and a `schema_complete` flag (has
   a non-empty `criteria_verification`/`acceptance_criteria_verification` array —
   state which in the MANIFEST). **Gate teacher-distillation on
   `provenance ∈ {claude_sdk, claude_code}`, never on date alone.**
3. **Sweeps** `~/.claude.backup.*/projects/*/subagents/agent-*.jsonl` +
   `~/.claude/projects/.../subagents/*.jsonl` for transcripts containing the Coach
   prompt AND ≥1 `tool_use` block; **discriminate by the transcript's `model`
   field, NOT by date** — these Claude Code subagent transcripts stayed on
   genuine Claude models (`claude-haiku-4-5`, `claude-sonnet-4-6`) through June
   (the local-model migration only touched the orchestrator's LangGraph harness,
   never the Claude Code harness that writes these). **Excludes** design-workflow
   /prompt-engineering false positives (path contains `/workflows/`, or the first
   user turn is a *"You are designing … the Coach prompt"* meta-prompt) and any
   non-`claude-*` model transcript. Of ~27 candidates, ~6 survive exclusion and
   all 6 are genuine Claude trajectories (two heavyweight: 44 and 139 `tool_use`
   blocks). Note the autobuild **SDK harness does not write `~/.claude` subagent
   jsonl** — Tier-B gold comes only from `/feature-build` via the Claude Code
   CLI, which is why it is scarce; the 2026-06 SDK runs (step 1) contribute
   Tier-A verdict pairs, not Tier-B trajectories.
4. **Joins outcomes** (AC-5): for each harvested task ID, sweep the same
   repos for downstream evidence — `TASK-REV-*` reviews that flag the task,
   follow-up `TASK-FIX-*` tasks, rework commits touching the same files — and
   tag each verdict pair `outcome: clean | later_revised | unknown`.
   Approved-but-`later_revised` pairs form the **false-approval set**: real
   in-distribution cases where the Coach approved unwired / under-tested work
   (the exact failure mode the QA Test Verifier targets). These are reserved
   as hard negatives for relabelling via the dataset factory
   (Coach-as-relabeller) — never as direct distillation examples.
5. **Exports** to a clean corpus:
   - `coach_verdict_pairs.jsonl` — Tier A: `{task, player_report, verdict,
     outcome}` per line — **raw, unformatted**. Serving-contract
     transformation (reasoning-prefix + grammar-fence shape per
     COACHBFULL/COACHSPLIT) is a separate curation step, so the corpus can be
     re-curated as the B-phase contract evolves without re-sweeping.
   - `coach_trajectories.jsonl` — Tier B: full message streams (system, user,
     assistant w/ tool_use, tool_result, final verdict), one trajectory per line
     or per file.
   - `MANIFEST.md` — hard counts: total pairs, schema-complete pairs, Claude-era
     pairs by repo, outcome split (clean / later_revised / unknown), Tier-B
     trajectory count, what was excluded and why.
6. Writes to a NEW dir (e.g. `~/coach-dataset/` or a `--out` path) — does NOT
   modify any source repo.

## Acceptance criteria

- [x] **AC-1**: `harvest_coach_dataset.py` runs read-only, sweeps all repos
  **recursively** (descending into `.guardkit/worktrees/*/.guardkit/autobuild/`)
  **plus guardkit git history at `d7f14b0e7^`** plus the `~/.claude*` transcript
  dirs, and produces `coach_verdict_pairs.jsonl`, `coach_trajectories.jsonl`, and
  `MANIFEST.md`. The harvester is **multi-machine**: it must run on BOTH the GB10
  (historical + fleet-memory) and the MacBook (the stranded lpa-platform-poc
  Claude-SDK runs), merging the two MANIFESTs. Each pair is tagged
  `provenance: claude_sdk | claude_code | local | unknown` (AC-1 fails if the
  guardkit sweep yields only the 2 live top-level files — proof the recursive /
  git-history path was not taken).
- [x] **AC-2**: Verdict pairs are correctly joined (`coach_turn_N` ↔
  `player_turn_N` ↔ task) and date-filtered; the MANIFEST gives the hard count
  of **schema-complete, Claude-era** pairs (this number decides whether Tier A
  alone is worth a fine-tune vs needing the factory to generate the bulk).
- [x] **AC-3**: Tier-B trajectories exclude the 2026-06-08 GB10-session /
  design-workflow false positives and any local-model runs; each retained
  trajectory contains the Coach prompt + ≥1 tool_use/tool_result pair + a final
  verdict.
- [x] **AC-4**: MANIFEST documents the provenance method (date-based, no model
  field) and lists per-repo counts so the operator can sanity-check the
  Claude-era classification.
- [x] **AC-5**: Outcome join executed: every Tier-A pair carries
  `outcome: clean | later_revised | unknown`, joined from `TASK-REV-*` /
  `TASK-FIX-*` artefacts in the source repos. MANIFEST reports the outcome
  split and lists the false-approval set (approved + `later_revised`) by task
  ID — reserved as hard negatives / relabelling input for the QA Test Verifier
  dataset, NOT as direct distillation examples.

## Harvest executed — 2026-06-19 (GB10)

Ran `scripts/harvest_coach_dataset.py` (read-only) on `promaxgb10-41b1`. Output
corpus: **`~/coach-dataset/`** (`coach_verdict_pairs.jsonl` 17 MB,
`coach_trajectories.jsonl` 1.9 MB, `MANIFEST.md`).

| metric | value |
|---|---|
| Total verdict pairs | **812** |
| Teacher-quality (Claude harness) | **812** — claude_sdk 713 / claude_code 99 / unknown 0 |
| Rich (schema-complete) | **514** |
| Approve / feedback | 587 / 225 (72% approve) |
| Rich + feedback (top judgment signal) | **84** |
| Outcome (AC-5) | clean 571 / later_revised 30 / unknown 211 |
| False-approval candidates | 16 (guardkit 13, forge 3 — noisy, relabeller input) |
| Tier-B trajectories | 6 (claude-sonnet-4-6 + claude-haiku-4-5, 21–55 tool_use) |

AC mapping: **AC-1** ✓ (read-only, recursive + guardkit git-recovery + `~/.claude*`,
3 outputs); **AC-2** ✓ (coach↔player↔task joined, de-duped, schema_complete flagged,
514 rich); **AC-3** ✓ (Tier-B excludes `/workflows/` + non-Claude-model, keeps 6 with
prompt+tool_use+verdict); **AC-4** ✓ (MANIFEST documents the harness-not-date method +
per-repo provenance); **AC-5** ✓ (outcome join executed, false-approval candidates listed).
**lpa-platform-poc** contributed 0 — per-turn JSON permanently lost (gitignored + worktree
merge/delete); only summaries survive. Provenance signal used: per-run `sdk_turns` /
`sdk_turns_used` (SDK-only), repo run-logs, and the 2026-06-19 harness-audit allow-list.

## Implementation notes

- **This is a SEED + validation set, not a complete training set.** Tier A
  (~81–365 pairs) can bootstrap the *judgment/schema* dimension; Tier B (~4–6
  trajectories) is too few to train *agentic convergence* alone but is perfect as
  golden few-shot templates + a validation set + seeds the
  **agentic-dataset-factory** imitates to generate the bulk. Tier-B
  trajectories also double as **design reference for the Coach A-phase gather
  probes** — they show what evidence a strong Coach actually collects before
  rendering a verdict.
- **Do not distill the Claude-era verdicts uncritically.** This corpus
  contains the old Coach's blind spots — including approvals of features that
  were ~90% complete with unwired seams (the exact failure mode the QA Test
  Verifier exists to catch). Provenance (Claude vs local) is NOT the quality
  axis; *verdict correctness* is, and the outcome join (AC-5) is what
  separates the two. Primary value of this harvest, in order: (1)
  eval/validation backbone — hold out Claude-era pairs + ALL Tier-B
  trajectories; (2) few-shot + factory imitation seeds; (3) the
  false-approval hard-negative set. Bulk training volume still comes from the
  agentic-dataset-factory.
- **Intended downstream use**: distill into a QAT base. **Fine-tune base ← the
  Gemma 4 26B-A4B MoE** (`google/gemma-4-26B-A4B-it-qat-q4_0-unquantized` for
  training, re-quantize after) — **updated 2026-06-11 by TASK-OPS-COACHMOE01.**
  The earlier recommendation (Gemma 4 31B dense QAT, "not the 3.8B-active 26B-A4B
  that runs 12–14 proved insufficient") was scoped to the **tool-bound agentic
  Coach loop**, which TASK-ARCH-COACHSPLIT (D-3) removed from the verdict path.
  On the shipped **B-min toolless+grammar** path the 26B MoE is empirically a
  viable Coach: TASK-OPS-COACHMOE01's grammar gate contained its ramble (finish=
  `stop`, 24–40s synthesis, per-AC criteria populated) and its live FEAT-AOF A/B
  approved 3/3 with honest, substantive verdicts (it caught real Player
  dishonesty). The MoE is the only base with a **validated 71-min LoRA recipe on
  the GB10**, runs at ~47 tok/s (vs the dense 31B's ~10), and is ~11 GB lighter.
  One reliability caveat carries into the fine-tune target: the MoE emitted 1/6
  malformed verdicts under live GBNF (vs g31's 0/3) — the distilled model should
  be eval'd against the COACHSF01-recovered emission rate. Full evidence:
  [`docs/state/TASK-OPS-COACHMOE01/README.md`](../../docs/state/TASK-OPS-COACHMOE01/README.md).
  (g31 dense QAT remains the higher-reliability fallback substrate until the
  fine-tune lands.)
- **Provenance is by HARNESS, not date (superseded by Update 2026-06-19;
  retained for the April-bin technique).** The harness cross-reference is now the
  primary axis (step 2); the date/April-bin note below is the *technique* for
  classifying ambiguous in-place copies when no retro/run-log names the harness.
  The stated counts don't
  reconcile: "~365 Claude-era" = Feb+Mar only, yet the default cutoff
  2026-04-15 admits early April. Resolve via artefact markers: (a) run logs in
  `docs/reviews/autobuild-migration/` record full CLI invocations — any
  sibling artefact mentioning `--coach-model`, `qwen`, `gemma4`, or llama-swap
  env exports (`OPENAI_BASE_URL=...:9000`) is definitively **local-era**;
  (b) SDK/Claude-era runs carry none of these markers. A run-log
  cross-reference pass should classify most of April confidently instead of
  contaminating the teacher set or wasting 244 pairs.

## Related

- **Substrate problem**: runs 12–14 ([autobuild-FEAT-AOF-run-14.md](../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-14.md), [run-14-artifacts](../../docs/state/TASK-REV-HMIG/run-14-artifacts/README.md))
- **Path 1A (no-op)**: [TASK-OPS-COACHGRAMMAR](autobuild-harness-migration/TASK-OPS-COACHGRAMMAR-enforce-coach-verdict-schema-via-llama-cpp-gbnf.md)
- **Path 1B (failed)**: [TASK-FIX-COACHSCHEMA](autobuild-harness-migration/TASK-FIX-COACHSCHEMA-tighten-coach-prompt-schema-emission.md)
- **PRIMARY teacher source (2026-06 Claude-SDK)**: `fleet-memory/.guardkit/autobuild/` (75/76, git-tracked, on the GB10; retros `fleet-memory/docs/retros/FEAT-MEM-0*.md`) + `lpa-platform-poc` voice-autobuild (FEAT-POC-004/005/006, FEAT-5A64, FEAT-9A4B; retros `lpa-platform-poc/docs/poc/retros/` on the GB10, raw artefacts on the MacBook)
- **guardkit historical recovery**: `git -C guardkit show d7f14b0e7^:.guardkit/autobuild/...` (333/319, read-only) and the `TASK-GLI-004` worktree (300/263); untracked by `d7f14b0e7` (TASK-AC-001, 2026-04-12)
- **Green-but-broken / AC-5 hard-negative origin**: `.claude/rules/per-task-green-is-not-feature-green.md` (seeded by lpa-platform-poc FEAT-POC-006)
- **Generation harness**: `~/Projects/appmilla_github/agentic-dataset-factory` (Player-Coach loop; has `domains/architect-agent`, `gcse-english-tutor` — `domains/autobuild-coach` NOT yet created)
- **Gemma 4 QAT lineup**: `google/gemma-4-{26B-A4B,31B}-it-qat-q4_0-{gguf,unquantized}` on HuggingFace
