---
id: TASK-OPS-COACHGRAMMAR
title: Enforce Coach verdict schema at the inference layer via llama.cpp GBNF grammar on gemma4-coach
status: blocked
task_type: ops
created: 2026-06-08T00:00:00Z
updated: 2026-06-08T14:30:00Z
blocked_reason: "Path 1A (route-level --grammar-file) invalidated by run 13 — llama.cpp bypasses the server grammar when a request carries tools, and the deepagents Coach sends built-in tools on every call, so the grammar never reaches the Coach. Needs re-scoping to a toolless verdict-synthesis call (code change) or Path 1B / Path 2."
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

- [x] **AC-1**: `llama-server --help` confirms `--grammar-file` support on the GB10 build. ✓ **Verified 2026-06-08** — live build `/home/richardwoollcott/llama.cpp-new/build/bin/llama-server` is llama.cpp **b9430** (`d48a56eff`, aarch64) and advertises `--grammar-file FNAME`. No upgrade needed.

- [x] **AC-2**: Coach verdict GBNF grammar authored, cross-checked against `coach_output_parser.py`, committed to a stable path, and version-tracked. ✓ **Done 2026-06-08.** In-repo source of truth: [`docs/research/dgx-spark/grammars/coach-verdict.gbnf`](../../../docs/research/dgx-spark/grammars/coach-verdict.gbnf) (+ `coach-verdict-strict.gbnf` fallback + [`README.md`](../../../docs/research/dgx-spark/grammars/README.md)). Installed live at `/opt/llama-swap/grammars/coach-verdict.gbnf`. Cross-checked against BOTH `coach_output_parser.py` and `agent_invoker.py` (COACH_DECISION_SCHEMA, `_validate_coach_decision`, `_parse_coach_feedback`, `parse_criteria_verifications`, Coach prompt examples). **The §9.13.1 draft grammar was found defective** (issues-as-strings, wrong field `criteria_results`, missing `validation_results`, non-compiling multi-line rules) and replaced; see README. Compile-verified with `test-gbnf-validator`; 10/10 behavioral cases.

- [~] **AC-3 (REVERTED)**: the `--grammar-file` line was added to the `gemma4-coach` route, hot-reloaded, and verified applied on `/v1/chat/completions` + `/v1/responses` via a `root ::= "PONG"` probe — **then removed 2026-06-08** after run 13 proved it is a no-op for the agentic Coach (see AC-5). Config restored (the one added line was deleted; backup at `config.yaml.bak-2026-06-08-pre-coachgrammar`); route recycled. No live route references the grammar.

- [✗] **AC-4 (INVALID — superseded)**: the on-config smoke that "passed" used a **no-tools, single-shot** `/v1/responses` request, where `--grammar-file` *does* apply. The real autobuild Coach is a `deepagents` agent that sends DeepAgents' **built-in tools** on every call, and **llama.cpp bypasses `--grammar-file` whenever a request includes `tools`** (verified on the GB10: tools-present requests returned a clean `tool_call` / a free-text `DONE`, never a forced verdict). So AC-4 never exercised the real Coach path. F24 is **not** closed by route-level wiring.

- [✗] **AC-5 (falsifier — run 13: FAILED)**: Run 13 ([log](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-13.md)) launched from the Mac. Player succeeded (46 files, 360s); **Coach SDK-timed-out at 2340s with no verdict** — `error`, feature FAILED 0/3. **Root cause: the grammar was a no-op** (bypassed on every Coach call because DeepAgents binds built-in tools; confirmed via `guardkitfactory` `harness/langgraph_harness.py` TASK-FIX-LGTOOLS + `harness/backend_config.py`, and live GB10 probes). The timeout is the **same substrate-quality wall as run 12** (gemma4-coach is a slow, unreliable agentic verifier), not a grammar effect — the Mac session's "grammar over-constrains / reason-forever" hypotheses (run-13-artifacts/README.md) are based on the false premise that the grammar applied. **Path 1A (route-level `--grammar-file`) is architecturally incompatible with the tool-bound agentic Coach.** Forward options (all non-zero-code) recorded in [`grammars/README.md`](../../../docs/research/dgx-spark/grammars/README.md): (1) a toolless verdict-synthesis call that *is* grammar-constrained, (2) `response_format`/`json_schema` on that call, (3) Path 1B prompt-tightening, (4) Path 2 nemotron.

## Implementation log (2026-06-08)

Worked through on the GB10 (`promaxgb10-41b1`) directly.

- **AC-1 ✓ / AC-2 ✓** as above.
- **Grammar design decision (C over D)**: empirical A/B on the live `gemma4-coach`
  showed the grammar constrains the *whole* sampled stream (reasoning included), so:
  - A strict no-backtick prelude + trailing `ws*` (initial candidate) **padded 9,865
    whitespace chars to the token cap** (`finish_reason=length`) and emitted the
    verdict after ~128 chars (short-circuited reasoning). Rejected.
  - **Primary `coach-verdict.gbnf` (Option C)** — free reasoning prefix (backticks
    allowed) + guaranteed final verdict fence + forced EOS — gives `finish_reason=stop`,
    preserves CoT, and produced a sound `approve` (correct per-AC `criteria_verification`)
    through the real parser at the production 16384-token budget.
  - **Fallback `coach-verdict-strict.gbnf` (Option D)** — no-backtick prelude — kept
    as a knob if run 13 under-emits (it forces early emission at the cost of depth).
- **Adversarial verification**: a 4-lens review (parser conformance, downstream
  schema, GBNF syntax, reasoning/ops) caught a run-breaking blocker the draft and my
  first candidate shared — a backtick inside a verdict JSON string makes the parser's
  non-greedy fence regex truncate the body → `json.loads` fails. Fixed by excluding
  the backtick from `char` (JSON string content only; reasoning prefix still allows it).
- **Findings doc**: §9.13.1 annotated with a CORRECTED banner + the 4 draft defects;
  run-13/smoke recipe flagged stale vs §9.15.

### Run-13 outcome (2026-06-08) — Path 1A invalidated

Run 13 FAILED: Coach SDK-timeout at 2340s, no verdict. Root-caused on the GB10:

- **The route-level grammar was a NO-OP for the Coach.** llama.cpp does not apply
  a CLI `--grammar-file` to any request carrying `tools`; it uses the tool-call
  grammar instead. The Coach is a `deepagents.create_deep_agent` agent whose
  built-in tool set (filesystem + execute + planning + sub-agents) is sent on every
  `/v1/responses` call, so the grammar never applied — verified by live probes
  (tools-present → clean `tool_call` / free `DONE`; no-tools → grammar applied) and
  by the harness source (`guardkitfactory` TASK-FIX-LGTOOLS / `backend_config.py`).
- **The AC-4 "pass" was invalid** — it tested a no-tools single-shot request.
- **Run-13's timeout = the substrate wall (run-12 shape), not the grammar.**
- **`--grammar-file` reverted** from the live `gemma4-coach` route.
- **Meta-lesson (candidate `.claude/rules/` seed):** a substrate-layer enforcement
  must be validated against the *real* request shape the runtime emits (tools
  present), not a simplified single-shot — same meta-frame as `namespace-hygiene.md`
  ("local decisions touching externally-defined contracts must be checked against the
  external contract").

## Implementation notes

- **Path 1A premise FALSIFIED**: "enforce the schema at the inference layer via a
  route-level `--grammar-file`, zero code change" does NOT work — the tool-bound
  agentic Coach bypasses the server grammar (see Run-13 outcome above). Enforcement
  requires reaching a *toolless* Coach request, which is a code change, not config.
- **Reasoning channel preserved (for a toolless call)**: the `root ::= prefix
  code-fence` shape allows free-form prose (incl. backticks) before the fence, so
  gemma4 keeps `reasoning_content` under `--reasoning auto` — validated on a
  single-shot call; still correct if the grammar is applied to a toolless
  verdict-synthesis call.
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
