---
id: TASK-OPS-COACHGRAMMAR
title: Enforce Coach verdict schema at the inference layer via llama.cpp GBNF grammar on gemma4-coach
status: backlog
task_type: ops
created: 2026-06-08T00:00:00Z
updated: 2026-06-08T00:00:00Z
priority: high
complexity: 3
effort_hours: 1
deadline: 2026-06-15
parent_review: TASK-REV-HMIG
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
implementation_mode: operator
intensity: standard
blocker: true
surfaced_in: docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-12.md
falsifier: "After landing: run 13 of `guardkit autobuild feature FEAT-AOF --fresh --model qwen36-workhorse --coach-model gemma4:26b` (no code or env changes from run 12) produces ≥1 natural fenced-JSON verdict per Coach turn with all required fields present (`task_id`, `turn`, `decision`). COACHSF01 synthetic-feedback fallback fires <5% of turns across ≥6 total Coach turns. AC-006 + AC-009 of TASK-HMIG-013 satisfied empirically."
---

# Task: Enforce Coach verdict schema via llama.cpp GBNF grammar

## Why this task exists

Run 12 ([autobuild-FEAT-AOF-run-12.md](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-12.md))
demonstrated that **architecture has delivered** — every F1-F22 code-side
finding closed empirically — but surfaced **F24** (recorded as
[I-013](../../../docs/state/TASK-REV-HMIG/feature-run-incidents.md)):
gemma4-coach under `--reasoning auto` is unreliable at the structured
fenced-JSON contract.

Across three Coach turns of 15-22 minutes each, gemma4 produced three
different failure shapes:

| Turn | Failure shape | COACHSF01 matcher |
|---|---|---|
| 1 | Emitted fenced JSON but **missing required fields `['task_id', 'turn']`** | `decision invalid` |
| 2 | **No fenced JSON in either content (2094 chars) or reasoning_content (5438 chars)** | `decision not found` |
| 3 | Cancelled by task-level 4800s timeout before Coach completed | n/a |

Cumulative natural verdict-emission rate: 0/3 = 0% (AC-006 needs ≥95%).
The COACHBUDG01 parser is proven reading both channels (turn-2 diagnostic
explicitly counts both); the COACHSF01 safety net catches both failure
shapes correctly. The gap is squarely substrate-quality: the model
*can* emit fenced JSON (turn 1) and *can* use the reasoning channel
substantively (turn 2's 5438 chars), but doesn't *reliably* terminate
with a schema-correct verdict block.

**This task closes F24 at the substrate** — using llama.cpp's GBNF
(Grammar-Based Next Form) constraint sampling to make structurally
invalid emissions *impossible* at the inference layer. Zero code change
in the orchestrator, parser, COACHSF01 safety net, or Coach prompt
template.

## What to do

Three-step operator runbook (full detail in
[§9.13.1 of the findings doc](../../../docs/research/dgx-spark/AUTOBUILD-ON-LLAMA-SWAP-findings.md);
this task summarises and tracks acceptance).

### Step 1: Verify llama.cpp GBNF support on the GB10's `llama-server` build

```bash
which llama-server
llama-server --help 2>&1 | grep -iE 'grammar|gbnf'
# Expected: --grammar-file FNAME              file to read grammar from
```

If `--grammar-file` is absent, upgrade llama.cpp first (any release
~b3000+ has it). Block this task on the upgrade.

### Step 2: Author and install the Coach verdict GBNF grammar

Save at `/opt/llama-swap/grammars/coach-verdict.gbnf` on the GB10.
Drafted shape per [§9.13.1](../../../docs/research/dgx-spark/AUTOBUILD-ON-LLAMA-SWAP-findings.md);
**operator should cross-check against the actual parser schema at
[`guardkit/orchestrator/coach_output_parser.py`](../../../guardkit/orchestrator/coach_output_parser.py)
before final approval.**

Key invariants the grammar MUST enforce:

- Response ends with a fenced ```json ``` block
- The block parses as a JSON object containing required fields:
  `task_id` (string), `turn` (integer), `decision` ("approve" or
  "feedback")
- Free-form prose is allowed *before* the fence (so `--reasoning auto`
  thinking still flows into the reasoning_content channel)
- Optional fields (`rationale`, `feedback`, `issues`, `criteria_results`)
  follow the COACHOUT01 schema

### Step 3: Wire into the gemma4-coach llama-swap route

Append `--grammar-file /opt/llama-swap/grammars/coach-verdict.gbnf` to
the `gemma4-coach` model's `cmd:` line in the llama-swap config.
Reload llama-swap:

```bash
sudo systemctl --user restart llama-swap
```

### Step 4: Smoke-test the grammar with the run-12 turn-2 Coach prompt

Replay the run-12 turn-2 Coach prompt 5 times and assert each response
ends with a fenced JSON block containing all required fields. Full
smoke recipe in §9.13.1 of the findings doc. Pass criterion: 5/5
attempts with `task_id`, `turn`, `decision` all present.

### Step 5: Run 13

```bash
mkdir -p .guardkit/autobuild/TASK-REV-HMIG-feature-run/
GUARDKIT_HARNESS=langgraph \
  OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 \
  OPENAI_API_KEY=llama-swap-local-key \
  guardkit autobuild feature FEAT-AOF \
    --fresh --model qwen36-workhorse --coach-model gemma4:26b \
    2>&1 | tee .guardkit/autobuild/TASK-REV-HMIG-feature-run/run-13-stdout.log
```

## Acceptance criteria

- [ ] **AC-1**: `llama-server --help` confirms `--grammar-file` support on the GB10 build. If absent, llama.cpp upgraded first.

- [ ] **AC-2**: Coach verdict GBNF grammar authored, cross-checked against `coach_output_parser.py`, committed to a stable path (`/opt/llama-swap/grammars/coach-verdict.gbnf`), and version-tracked (operator preference: in-repo at `docs/research/dgx-spark/grammars/coach-verdict.gbnf` for traceability).

- [ ] **AC-3**: `gemma4-coach` llama-swap route updated with `--grammar-file <path>` arg; llama-swap restarted; the route serves requests without grammar-compile errors.

- [ ] **AC-4 (smoke)**: 5× replay of the run-12 turn-2 Coach prompt produces 5/5 responses with fenced JSON containing `task_id`, `turn`, `decision` required fields. If <5/5, iterate on the GBNF before Run 13.

- [ ] **AC-5 (falsifier — downstream verification)**: Run 13 (same invocation as run 12, no code or env changes) produces **Coach verdict-emission rate ≥95%** across ≥6 Coach turns. COACHSF01 synthetic-feedback fallback fires <5% of turns. AC-006 + AC-009 of TASK-HMIG-013 satisfied empirically.

## Implementation notes

- **Architecturally correct fix**: enforces the schema *where it's
  serviceable* — at the inference layer. The orchestrator, parser, and
  COACHSF01 safety net don't need to know about the grammar; they keep
  working as defence-in-depth.
- **No code change** in `guardkit/` or guardkitfactory. This is purely
  llama-swap config + a small grammar file.
- **Reasoning channel preserved**: the `root ::= prelude code-fence`
  shape allows free-form prose before the fence, so gemma4 can still
  use `reasoning_content` substantively under `--reasoning auto`. The
  grammar only constrains the *final* response shape.
- **Operator should consider committing the GBNF file in-repo** at
  `docs/research/dgx-spark/grammars/coach-verdict.gbnf` (or
  similar) so future runs / different GB10s / 2nd GB10 can pick up the
  same enforced schema.
- **If GBNF compile fails**: the most common cause is escaping the
  triple-backtick fence. llama.cpp's GBNF doesn't have native
  multi-char literal escaping for backticks — try `"\\u0060\\u0060\\u0060json"`
  or use a literal `[\`]{3}` if supported by the build's GBNF parser.

## Related

- **Surfaces**: F24 in [feature-run-analysis.md §6](../../../docs/state/TASK-REV-HMIG/feature-run-analysis.md)
- **Incident**: I-013 in [feature-run-incidents.md](../../../docs/state/TASK-REV-HMIG/feature-run-incidents.md)
- **Full operator runbook**: [§9.13.1 of AUTOBUILD-ON-LLAMA-SWAP-findings.md](../../../docs/research/dgx-spark/AUTOBUILD-ON-LLAMA-SWAP-findings.md)
- **Parser schema source-of-truth**: [`guardkit/orchestrator/coach_output_parser.py`](../../../guardkit/orchestrator/coach_output_parser.py)
- **COACHOUT01 schema invariant**: [`.claude/rules/feature-build-invariants.md`](../../../.claude/rules/feature-build-invariants.md) FB-004
- **Code fallback if 1A unavailable**: [TASK-FIX-COACHSCHEMA](TASK-FIX-COACHSCHEMA-tighten-coach-prompt-schema-emission.md) (Path 1B)
- **Escalation path if 1A insufficient on semantic quality**: TASK-HMIG-013 AC-007 (nemotron-3-super:120b-a12b, gated on 2nd GB10 + ConnectX-7)
- **Blocks**: TASK-HMIG-010 AC-006 / AC-009 / AC-008 (Wave 4 cutover decision), TASK-HMIG-011 (cutover ceremony)
