# Run-18 autobuild artifacts snapshot

> **Purpose**: snapshot the `.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/`
> artifacts from run 18 to a tracked path so the GB10 Claude session can
> pick them up for diagnosis. Same pattern as the run-13 through run-17
> snapshots.
>
> **Source**: live worktree artifacts copied 2026-06-09T07:40Z from
> `.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/`.
> **Run log**: [`autobuild-FEAT-AOF-run-18.md`](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-18.md)
> (committed in the same change as this snapshot).

## TL;DR — Brand-new failure class on gemma4:31b (likely chat-template / tokenizer mismatch)

Run 18 changed failure mode AGAIN. Four distinct shapes now seen across recent runs:

| Run | Player files | HTTP | Failure class | Wall |
|---:|---:|---|---|---:|
| 15 | 30 | 200 (✓) / 502 | turn-1 ✓ verdict, turn-2 F23A OOM | 23m 40s |
| 16 | 71 | 502 | turn-1 F23A OOM | 20m 25s |
| 17 | 41 | 400 | F20 ctx overflow at 66,687 tokens | 24m 52s |
| **18** | **42** | **500** | **NEW: server_error "Failed to parse input"** | **13m 21s** |

The run-18 error body ([log:223-226](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-18.md#L223-L226)):

```json
{"error": {"code": 500,
  "message": "Failed to parse input at pos 0: <|channel>�thought\nI'll read more.\n<channel|><|tool_call>call:read_file{file_path:<|\"|>/Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/guardkit/orchestrator/agent_invoker.py<|\"|>,offset:400}<tool_call|>",
  "type": "server_error"}}
```

## Why this matters — three diagnostic flags

### 🚩 Flag 1: Unicode REPLACEMENT CHARACTER in the error body

`<|channel>�thought` contains **U+FFFD (REPLACEMENT CHARACTER)** — `�`.
This means **byte-level UTF-8 decode failed**. The model produced
token bytes that don't form valid UTF-8 sequences. This is a strong
signal of:

- **Tokenizer/model mismatch**: the GGUF file's tokenizer doesn't match
  the actual weights (or vice versa)
- **Quantization corruption**: some quants of newer models (especially
  pre-release / experimental variants) can produce token IDs that map
  to malformed bytes
- **`--chat-template` argument mismatch** in llama-swap: the template
  passed to llama-server doesn't match what the model expects to see

### 🚩 Flag 2: The token structure looks like OpenAI-Harmony / GPT-OSS format

`<|channel>...thought...<channel|><|tool_call>...<tool_call|>` matches
the **Harmony response format** used by OpenAI's `gpt-oss-20b/120b` and
some Llama-4 / GLM-4.5 / DeepSeek variants — but with garbled syntax
(missing pipe closures, broken nesting):

| Harmony expected | Model produced |
|---|---|
| `<\|channel\|>analysis<\|message\|>...<\|end\|>` | `<\|channel>�thought\n...<channel\|>` |
| `<\|channel\|>commentary to=tool_X.func<\|message\|>{...}<\|end\|>` | `<\|tool_call>call:read_file{...}<tool_call\|>` |

This is **almost-Harmony-but-not-quite**. Either:

- The GB10 swapped to a Harmony-format model variant but llama-server's
  parser is configured for the old plain-format response
- Or vice versa: model expects plain format but the chat template /
  jinja was switched to Harmony

### 🚩 Flag 3: Player wrote a passing test this time

[run-18:152](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-18.md#L152):
`success - 42 files created, 1 modified, 1 tests (passing)`. First
run with **Player actually shipping a passing test**. That's positive
substrate evidence for the Player half — it's only the Coach call that
broke, and the break is structural (parser failure), not substantive
(reasoning failure).

## Run progression at a glance

| Phase | Time | Result |
|---|---|---|
| Wave 1 / IA03 start | 06:27:16 UTC | task budget 4800s |
| **Turn 1 Player** | → 06:30:16 (~180s) | ✓ **42 created**, 1 modified, **1 test passing** |
| Turn 1 test-orchestrator | SPECHANG 150s, contained by SPECCOCH01 | ✓ as designed |
| Coach independent tests | ran | ✓ |
| **Turn 1 Coach LLM start** | 06:32:46 | — |
| Coach LLM progress | HTTP 200s through ~420s elapsed | working initially |
| **HTTP 500 #1** | ~440s elapsed | first malformed output triggered server_error |
| OpenAI retries (2x) | 200 OK retry, then 500 #2, retry, 500 #3 | model keeps emitting malformed tokens |
| **Coach failed** | 06:40:37 | server_error, NOT routed through COACHSF01 (right call) |
| FEATURE | FAILED | total **13m 21s** |

The 200 OK calls before and between the 500s suggest **non-deterministic
output formatting** — gemma4:31b sometimes emits valid format, sometimes
emits the malformed Harmony-ish tokens. That's also consistent with the
tokenizer/template mismatch hypothesis: certain prompts trigger the
broken path, others don't.

## What's in this snapshot

| File | Size | What | Useful for |
|---|---:|---|---|
| `player_turn_1.json` | 8109 B | Coach input — the 42-file Player payload | What Coach was asked to validate |
| `task_work_results.json` | 10700 B | Player's enriched task-work output | Specialist + Player full state, plus the passing test |
| `turn_state_turn_1.json` | 4920 B | Orchestrator's post-turn-1 snapshot | State record incl. Coach `error` result |
| `specialist_results.json` | 540 B | test-orchestrator SPECHANG (contained) | Specialist failure mode (graceful, SPECCOCH01 working) |
| `turn_context.json` | 763 B | Per-thread context loader state | Graphiti / loader inspection |
| `state_transitions.json` | 340 B | state_bridge mutations log | Ghost-path filter / state-bridge inspection |

## What's NOT in this snapshot

- **`coach_turn_1.json`** — doesn't exist. Coach failed before
  emitting (parser error wrapping the server_error response, not a
  COACHSF01-recoverable decision-emission failure).
- The malformed token stream itself (only its tail visible in the
  error message). The **full ~25 successful HTTP 200 bodies** before
  the 500 are in llama-swap / llama.cpp logs on `promaxgb10-41b1`.
  Window: **2026-06-09T06:32:46 → 06:40:37 UTC**. The interesting
  diagnostic question is: **did the 200 OKs contain valid-format
  output, or were they ALL malformed and llama-server only started
  reporting the malformation after a state change?**

## Diagnostic hypotheses for the GB10 session

1. **Verify the gemma4:31b llama-swap entry's chat template config.**
   Specifically:
   - `--chat-template` arg (if any) — is it set to something like
     `harmony`, `gpt-oss`, or a path to a jinja template?
   - `--chat-template-file` arg (if any) — what file?
   - The GGUF's embedded chat template metadata (`llama-server` logs
     this at startup) — what jinja does it claim?
   - Cross-check the model's HuggingFace `tokenizer_config.json` for
     the canonical chat template

2. **Verify the model file is what you think it is.** Run
   `llama-gguf-info /opt/llama-swap/models/gemma4-31b/<file>.gguf`
   (or equivalent) and confirm:
   - Architecture name matches expectation (`gemma3`, `llama4`, etc.)
   - Tokenizer model matches
   - No `chat.template` metadata key set to a Harmony-style template
     if the model isn't actually Harmony-format

3. **Re-check what changed between run 17 and run 18.** Run 17 hit
   F20 (HTTP 400 ctx overflow); run 18 hit HTTP 500 parser error.
   Between them the GB10 likely changed the llama-swap entry to bump
   n_ctx per run-17's recommendation. If that bump came with any
   other arg changes (model swap, template change, grammar add/remove),
   the new error is downstream of that.

4. **Try the smoke recipe with a minimal prompt.** Send a tiny
   `/v1/chat/completions` to gemma4:31b and check whether output
   format is well-formed:

   ```bash
   curl -sS http://localhost:9000/v1/chat/completions \
        -H "Content-Type: application/json" \
        -d '{"model":"gemma4:31b",
             "messages":[{"role":"user","content":"Say hello"}],
             "max_tokens":50}' | jq '.choices[0].message.content'
   ```

   If the output contains `<|channel>` or `<|tool_call>` markers, the
   chat template is wrong. If it returns plain text, the issue is
   only triggered by larger prompts / tool-bound Coach paths.

5. **Test with `tools=[]` (toolless).** Per the run-13 grammar-no-op
   finding, the deepagents Coach sends tools on every call. If you
   send a toolless `/v1/chat/completions` request matching the Coach
   shape, you can isolate whether the parser break is tool-related.

## Cross-reference

- **Run-13 grammar-no-op finding**: tool-bound deepagents Coach calls
  go through a different code path than toolless ones —
  [`../run-13-artifacts/README.md`](../run-13-artifacts/README.md)
- **Run-17 F20 recurrence on gemma4:31b**:
  [`../run-17-artifacts/README.md`](../run-17-artifacts/README.md) —
  if the GB10 bumped n_ctx between 17 and 18, the chat-template / tokenizer
  config to check is whatever else changed in the same edit
- **Run-15 F23A diagnosis**: commit `1ee4baab`
- **TASK-OPS-COACH31B** (the 31B QAT Coach setup): commit `8ed242ae`
  — this is the task file to cross-check for the current llama-swap
  config of gemma4:31b
- **Architecture invariants still all working**: SPECCOCH01 contained
  test-orchestrator SPECHANG; orchestrator classified Coach correctly
  as `error` (substrate parser failure, NOT decision-emission failure
  — the COACHSF01 substring-pinned invariant held); CTOUT01 silent;
  no code regressions
