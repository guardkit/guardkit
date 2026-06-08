# Coach verdict GBNF grammars

GBNF grammars that enforce the AutoBuild **Coach verdict-emission contract**
(COACHOUT01 / FB-004) at the llama.cpp inference layer for the `gemma4-coach`
model alias on the GB10. Closes **F24 / I-013** (gemma4-coach under
`--reasoning auto` is unreliable at the structured fenced-JSON contract).

**Task:** [`TASK-OPS-COACHGRAMMAR`](../../../../tasks/backlog/autobuild-harness-migration/TASK-OPS-COACHGRAMMAR-enforce-coach-verdict-schema-via-llama-cpp-gbnf.md)
(Path 1A). **Full runbook:** [`AUTOBUILD-ON-LLAMA-SWAP-findings.md §9.13.1`](../AUTOBUILD-ON-LLAMA-SWAP-findings.md).

| File | Role |
|---|---|
| [`coach-verdict.gbnf`](coach-verdict.gbnf) | **Primary.** Free reasoning prefix + guaranteed final verdict fence + forced EOS. |
| [`coach-verdict-strict.gbnf`](coach-verdict-strict.gbnf) | **Fallback.** No-backtick prelude; biases toward early emission at the cost of reasoning depth. Use only if the primary under-emits in run 13. |

Installed (live) at `/opt/llama-swap/grammars/` on `promaxgb10-41b1`. The in-repo
copies here are the version-tracked source of truth — keep them in sync.

---

## Why the drafted §9.13.1 grammar was replaced

The grammar drafted in §9.13.1 of the findings doc was **cross-checked against the
real parser + downstream schema and found defective on four counts**, any one of
which would have broken run 13:

1. **`issues` modelled as an array of strings.** The real Coach feedback verdict
   (agent_invoker.py:2483-2500) emits `issues` as an array of **objects**
   `{type, severity, description, requirement, suggestion}`, consumed by
   `_parse_coach_feedback` (agent_invoker.py:4508-4519). The draft would have
   **forbidden the real feedback shape**.
2. **Wrong field name `criteria_results`.** The real field is `criteria_verification`
   (array of `{criterion_id, result, notes}`), consumed by
   `parse_criteria_verifications` (agent_invoker.py:6458-6483).
3. **`validation_results` omitted** — required by the canonical *approve* shape.
4. **Multi-line rule bodies that do not compile.** llama.cpp parses top-level rule
   bodies with `newline_ok=false`, so a `verdict-obj` split across 6 lines fails
   with `expecting ::=`; an alternation split across lines fails with `expecting
   name`. (Verified with `test-gbnf-validator`.)

The replacement uses a **fixed required-field prefix + generic trailing JSON
members**, so the three hard-required fields are *guaranteed* while every optional
field — and any future one — passes through unconstrained. Optional-field **values**
are deliberately not enumerated (e.g. `result` is any string, not a
`verified|rejected` enum): gemma4 emitted `result:"pass"` in testing, which a value
enum would have forbidden mid-generation. Field-value wording is Path 1B's job
(prompt tightening), not the grammar's.

---

## Cross-check: grammar ⇄ parser ⇄ downstream schema

Source of truth: [`coach_output_parser.py`](../../../../guardkit/orchestrator/coach_output_parser.py)
and [`agent_invoker.py`](../../../../guardkit/orchestrator/agent_invoker.py).

| Contract element | Source | Grammar enforces |
|---|---|---|
| Ends with a fenced ```` ```json ```` block | `_FENCE_PATTERN` | `root ::= prefix code-fence` (fence is last, forced EOS) |
| Block is a JSON object | parser `isinstance(dict)` | `verdict-obj ::= "{" ... "}"` |
| `task_id` present, string | `_REQUIRED_TOP_LEVEL_KEYS`, `COACH_DECISION_SCHEMA` | `req-task-id ::= ... json-string` |
| `turn` present, **bare integer** | `COACH_DECISION_SCHEMA` `isinstance(int)` | `req-turn ::= ... json-integer` (no frac/exp) |
| `decision` ∈ {approve, feedback} | parser + `_validate_coach_decision` | `decision-val ::= "\"approve\"" \| "\"feedback\""` |
| `validation_results`, `criteria_verification`, `issues` (objects), `rationale`, … | prompt + `_parse_coach_feedback`, `parse_criteria_verifications` | permitted via generic `member` / `json-value` (never forbidden) |
| Parser must not truncate on a stray ```` ``` ```` in a string value | `_FENCE_PATTERN` is non-greedy | `char` **excludes backtick** from JSON string content |
| "last fenced block wins" | parser `matches[-1]` | fence is guaranteed last (root ends at it) |

---

## Empirical validation (2026-06-08, live `gemma4-coach`, inline `grammar` param)

All tests run against the already-loaded `gemma4:26b` via the request-level
`grammar` field — **zero llama-swap config change, zero fleet impact**.

- **AC-1:** `llama-server --help` on the live build (llama.cpp **b9430**,
  `/home/richardwoollcott/llama.cpp-new/build/bin/llama-server`) confirms
  `--grammar-file FNAME`. ✓
- **Compile:** `test-gbnf-validator` accepts both grammars; 10/10 behavioral
  cases each (accepts both canonical verdict shapes; rejects missing fields,
  string-`turn`, bad enum, backtick-in-string, wrong order).
- **Grammar reaches the reasoning channel** (whole-stream constraint): under the
  no-backtick prelude, reasoning-channel backtick count dropped 80 → 6 (= just the
  fence delimiters). This is *why* the primary grammar permits backticks in the
  prefix.
- **A/B (small prompt):** control (no grammar) reasoned 10,727 chars and emitted
  **no verdict** (F24 reproduced); the grammar produced a valid parsed verdict.
- **Primary (C) @ 16384 budget, substantive prompt, through the REAL parser:**
  `finish_reason=stop`, ~1900 tokens, CoT → `reasoning_content` (backticks intact),
  verdict → `content`; `coach_output_parser.extract_and_write` extracted a valid
  `approve` with sound per-criterion `criteria_verification` and a coherent
  rationale. No whitespace padding.
- **Fallback (D):** forces a valid verdict in ~139 tokens / 3 s — guarantees
  emission aggressively but with shallow reasoning (premature verdict risk).

### Why not a strict single-fence grammar

`root ::= prelude code-fence ws` (an earlier candidate) failed two ways on the live
model: (1) the trailing `ws*` let the model **pad 9,865 whitespace chars** to the
token cap (`finish_reason=length`) — burning the whole budget; (2) the optional
prelude let it emit the verdict after ~128 chars, **short-circuiting reasoning**.
Dropping the trailing `ws` fixes padding; permitting backticks in the prefix
(Option C) fixes the reasoning short-circuit.

---

## Operator handoff

**Status (2026-06-08, on `promaxgb10-41b1`):** AC-1 ✓, AC-2 ✓, **AC-3 ✓, AC-4 ✓**.
The grammar is wired into the live `gemma4-coach` route and verified end-to-end on
the real Coach path. Only **AC-5 (run 13)** remains, and it is launched from the
**orchestrator host (the Mac)**, not this box.

### AC-3 ✓ — wired into the `gemma4-coach` route (done)

`--grammar-file /opt/llama-swap/grammars/coach-verdict.gbnf` was appended to the
`gemma4-coach` `cmd:` block in `/opt/llama-swap/config/config.yaml` (line ~320;
backup at `config.yaml.bak-2026-06-08-pre-coachgrammar`). llama-swap runs with
`-watch-config`, so the edit hot-reloads only that route; `/unload?model=gemma4-coach`
forces a clean recycle. The same one-line edit reproduces this on a 2nd GB10.

### AC-4 ✓ — verified on the real path (done)

**Key finding:** the server-level `--grammar-file` IS applied to the OpenAI-compat
endpoints — both `/v1/chat/completions` and **`/v1/responses`** (the deepagents Coach
path). Verified with a `root ::= "PONG"` probe that forced exactly `PONG` on both
endpoints. (Note: a permissive-prefix grammar like the primary will *not* visibly
constrain a non-verdict prompt — the model stays in the prefix — so use a trivial
always-output probe like `PONG` to confirm application, not a "say hello" check.)

End-to-end: a substantive Coach prompt sent via `/v1/responses` relying on the
**config-level** grammar (no inline grammar) produced a valid verdict extracted by
the real `coach_output_parser` — `status=completed`, sound `approve` with 3
`criteria_verification` entries, reasoning preserved. The no-grammar control arm
reproduced F24 (no verdict). When re-verifying, measure `finish_reason` (want
`completed`/`stop`, not `length`) and `reasoning` char count vs the §9.14 ~4450 baseline.

### AC-5 — run 13 (launch from the Mac orchestrator host)

This GB10 is the model host; `guardkitfactory` + the langgraph/deepagents stack are
not installed in its guardkit `.venv` (run-9/10 ran from the Mac per §9.15). Launch
from the Mac — it points at this box's now-grammar-enforced llama-swap. Use the
**§9.15 run-10 command** (NOT the stale §9.13.1 copy, which omits the timeout/context
flags):

The grammar lives at llama-swap, so the launch command is the **§9.15 run-10
command** (NOT the stale §9.13.1 copy, which omits the timeout/context flags):

```bash
mkdir -p .guardkit/autobuild/TASK-REV-HMIG-feature-run/
GUARDKIT_HARNESS=langgraph \
  OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 \
  OPENAI_API_KEY=llama-swap-local-key \
  guardkit autobuild feature FEAT-AOF \
    --fresh --model qwen36-workhorse --coach-model gemma4:26b \
    --task-timeout 4800 --no-context \
    2>&1 | tee .guardkit/autobuild/TASK-REV-HMIG-feature-run/run-13-stdout.log
```

Memory prep first (the GB10 froze at this exact workload before — see findings §9.4,
§9.13 OOM notes): pause the keepalive timer, ensure headroom, close GUI apps.

**Run-13 pass criteria (reworded — emission rate is now ~100% by construction, so it
is no longer the falsifier):** (i) `finish_reason=stop` on Coach turns (no
grammar-induced `length` truncation), (ii) reasoning-channel size within ~2× of the
un-grammared baseline, (iii) a human spot-check of ≥6 verdicts confirms decisions
match the Player diff. If decisions are coerced-but-wrong, fall to Path 1B
(TASK-FIX-COACHSCHEMA) / Path 2 (nemotron-3-super).
