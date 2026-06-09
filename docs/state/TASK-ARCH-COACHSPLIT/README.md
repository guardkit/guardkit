# TASK-ARCH-COACHSPLIT — design state (strict intensity, complexity 7)

> Status: **gate PASSED 2026-06-09 → implementation in progress.**
> `/task-work` ran Phases 1–2 (context + grounded planning), stopped at the
> mandatory Phase 2.8 checkpoint, operator decisions captured below, then the
> GB10 probe validated the architecture.

## Gate result (2026-06-09) — `probe_toolless_grammar.py` against `gemma4:31b`

| Case | Request | Result | Meaning |
|---|---|---|---|
| **A** | toolless + per-request grammar (THE DESIGN) | **PASS** — real `{task_id,turn,decision:"approve"}` verdict | grammar **honoured toolless** ⇒ architecture validated |
| B | toolless + no grammar | PASS (conformant) | g31 prompt-only is strong; grammar is still the *guarantee* we ship |
| C | tool-bound + grammar (run-13 control) | **HTTP 400 "Cannot use custom grammar constraints with tools."** | this build *explicitly rejects* grammar+tools — the toolless split is the ONLY path to grammar enforcement |

CASE C is a stronger confirmation than run-13's "silent no-op": the request-validation
layer hard-rejects grammar+tools, so there is no way to keep the Coach tool-bound and
get a grammar guarantee. Proceed to wire `invoke_synthesis()`.

## Operator decisions (Phase 2.8 checkpoint, 2026-06-09)

| Decision | Choice |
|---|---|
| Realization | **B-min** — toolless grammar-enforced synthesis directly over the deterministic `CoachEvidenceBundle`; no LLM tool-investigation phase. |
| Harness interface shape | **New `invoke_synthesis()` method** on the `HarnessAdapter` ABC (default falls back to `invoke(tools=[])`). |
| Sequencing | **Probe GB10 grammar FIRST.** Confirm "grammar honoured when toolless" on the real llama.cpp build before wiring orchestration. |

## Verified code-surface findings (the plan rests on these)

1. **LangGraph harness is never truly toolless via `allowed_tools`.** It drops the
   caller's `tools` and always calls `create_deep_agent(..., tools=[])`, which still
   binds DeepAgents' built-in tool surface → the llama.cpp request always carries
   `tools` → grammar bypassed (run-13) + tool-parse-500 (run-18).
   `langgraph_harness.py:294-320`. **⇒ the synthesis path must BYPASS
   `create_deep_agent` and invoke the bare resolved model.**
2. `HarnessAdapter.invoke()` has **no** grammar/structured-output param —
   `adapter.py:149-182`. New `invoke_synthesis()` adds it (no-op for SDK).
3. Resolved model is a `ChatOpenAI`→llama-swap `BaseChatModel`
   (`model_config.py:245-316`). Grammar attaches per-request via
   `.bind(extra_body={"grammar": <gbnf>})` → a no-tools request → grammar honoured.
4. `gather_evidence()` already produces `CoachEvidenceBundle`
   (`coach_validator.py:1709`), already passed to `invoke_coach` → `_build_coach_prompt`
   (`agent_invoker.py:1966-1990`). B-min reuses this verbatim.
5. `coach_output_parser.extract_and_write` consumes `AssistantMessageEvent.text`
   — **unchanged**; both harnesses emit it (substrate parity, FB-004).
6. `CoachVerifier` honesty runs in `gather_evidence` Stage 1 → `evidence_bundle.honesty`;
   `invoke_coach` already uses it as the canonical honesty channel (AC-6 holds as long
   as the synthesis path keeps consuming `evidence_bundle.honesty`).
7. Reusable GBNF: `docs/research/dgx-spark/grammars/coach-verdict.gbnf` (primary,
   free-reasoning prefix + guaranteed final verdict fence) and `coach-verdict-strict.gbnf`
   (early-emission fallback). Authored under TASK-OPS-COACHGRAMMAR; never wired because
   route `--grammar-file` was a no-op for tool-bound requests — now applicable toolless.
8. **AC-4 (run-19)** needs the GB10 llama-swap box (`GUARDKIT_HARNESS=langgraph`,
   `http://promaxgb10-41b1:9000/v1`, `gemma4:31b`, ctx 98304, `--no-context`,
   minimal `coach31` fleet) — operator falsifier run, not codeable here.

## The gate: `probe_toolless_grammar.py`

Run it before any orchestration is wired (see the script header for preconditions):

```bash
OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 \
OPENAI_API_KEY=llama-swap-local-key \
python3 docs/state/TASK-ARCH-COACHSPLIT/probe_toolless_grammar.py
```

- **CASE A** (toolless + per-request grammar) conformant ⇒ **architecture validated**,
  proceed to implementation.
- **CASE A** not conformant ⇒ **STOP**, pivot to fallback (llama.cpp b9570+ upgrade or
  alt/higher-quant g31 GGUF) per the task Implementation notes.
- CASE C (tool-bound + grammar) reproduces run-13/18 (grammar bypassed / HTTP 500) — expected.

## Planned implementation (post-probe, B-min)

1. **`HarnessAdapter`** (`guardkit/orchestrator/harness/adapter.py`): add
   `async def invoke_synthesis(self, prompt, role, *, grammar, cwd, timeout_seconds)`
   with a default that delegates to `invoke(tools=[])` (SDK-safe, grammar ignored).
2. **`LangGraphHarness.invoke_synthesis`** (`guardkitfactory/.../langgraph_harness.py`):
   bypass `create_deep_agent`; `resolved = self._resolve_model_for_invoke(role)`;
   `await resolved.bind(extra_body={"grammar": grammar}).ainvoke(_build_input(prompt))`;
   emit the same `AssistantMessageEvent` + `ResultMessageEvent` (reuse extractors,
   keep the CTOUT01 cancel-task wrap).
3. **`ClaudeSDKHarness.invoke_synthesis`**: `allowed_tools=[]`, grammar ignored
   (Claude reliably emits JSON; no GBNF on that substrate).
4. **`agent_invoker`**: add `role="coach_synthesis"` to `_invoke_with_role` (and the
   COACHBUDG01 model-override branch); route it through `invoke_synthesis` with the
   verdict grammar loaded from a wired asset path. `invoke_coach` switches its single
   LLM call to the synthesis role (no tool investigation).
5. **`_build_coach_prompt`**: add a synthesis variant — "emit ONLY the fenced verdict
   from the evidence; do not investigate" — keeping the absence-of-failure guards
   (AC-5: empty bundle must NOT auto-approve).
6. **Grammar asset**: promote `coach-verdict.gbnf` to a code-wired location
   (packaged with guardkit or guardkitfactory) so the harness can load it at runtime.
7. **Tests** (AC-2/3/5/6): synthesis request carries no `tools` + grammar present
   (inspect the bound request); malformed-prone prompt still yields schema-valid JSON;
   zero-evidence bundle ⇒ feedback not approve; `evidence_bundle.honesty` still consumed.

## AC mapping

- AC-1 ← step 1/2/4 (toolless, grammar-present synthesis request — verify the bound request)
- AC-2 ← step 2 (no tool markers ⇒ no HTTP 500; regression test)
- AC-3 ← gate + step 6 (grammar active toolless; malformed-prone test)
- AC-4 ← **operator run-19** (post-implementation falsifier; not codeable here)
- AC-5 ← step 5/7 (two-phase incl. zero-evidence; absence-of-failure guard preserved)
- AC-6 ← finding 6 + step 4 (CoachVerifier honesty still consumed on synthesis output)

## Implementation landed (2026-06-09)

| Piece | File |
|---|---|
| `invoke_synthesis()` on the harness ABC (default → toolless `invoke(tools=[])`, grammar ignored) | `guardkit/orchestrator/harness/adapter.py` |
| Packaged grammar + loader | `guardkit/orchestrator/coach_grammar.py`, `guardkit/orchestrator/grammars/coach-verdict.gbnf` |
| `_coach_synthesis_enabled()` gate (`GUARDKIT_COACH_SYNTHESIS`, default ON), toolless+grammar `invoke_coach`, synthesis `_build_coach_prompt`, `_invoke_with_role` synthesis branch | `guardkit/orchestrator/agent_invoker.py` |
| LangGraph `invoke_synthesis` + `_build_synthesis_model` (bypass `create_deep_agent`; chat-completions `ChatOpenAI` + `extra_body={"grammar":…}`; reuse extractors; CTOUT01 cancel parity) | `guardkitfactory/.../langgraph_harness.py` |
| Tests | `tests/orchestrator/test_coach_synthesis_split.py`, `guardkitfactory/tests/harness/test_langgraph_harness_synthesis.py`, updated `test_agent_invoker.py` |

**Tests:** guardkit synthesis suite + parser parity + affected coach/agent tests all green
(513 passed in the focused sweep); factory harness suite 71 passed (incl. 6 new). Remaining
sweep failures are **pre-existing on HEAD** (py3.10 `asyncio.timeout` gap in the dev shell,
a worktree-`.venv` env test, an already-broken dead-task-id lint with 14 pre-existing refs —
this change adds **0** new dead refs).

## Adversarial review outcome (7 dimensions, each finding verified)

10 raw findings → **2 confirmed** (one root cause, flagged from two dimensions); 8 correctly
dismissed (e.g. the byte-parity test exists under a different name; `langchain_openai` is a
pre-existing dep).

**Confirmed + FIXED — synthesis must be gated on bundle presence.** When `invoke_coach` ran
with synthesis enabled (default) but **no `evidence_bundle`** (the `GUARDKIT_COACH_LEGACY=1`
fallback after a `CoachValidator` exception — `autobuild.py::_invoke_coach_legacy`), the
synthesis prompt asserted a bundle that was never rendered AND dropped the structured
absence-of-failure guards — a latent false-green hazard
(`.claude/rules/absence-of-failure-is-not-success.md`).

Fix: `synthesis_enabled = _coach_synthesis_enabled() and evidence_bundle is not None`. A
toolless "synthesise over the bundle" call is incoherent with no bundle; the no-bundle path
now keeps the tool-using Coach (which can investigate to compensate for the absent
deterministic evidence). The autobuild PRIMARY path always passes a bundle → always
synthesises. Defence-in-depth: `_build_coach_prompt`'s synthesis banner no longer claims a
bundle exists when one wasn't rendered. New test `test_no_bundle_falls_back_to_legacy_tools`
pins it; `test_invoke_coach_success` reverted to the (now-correct) read-only assertion.

## Remaining to close the task

**AC-4 — run-19 falsifier (operator, GB10):** with the code merged, run an autobuild on
`gemma4:31b` as Coach (minimal `coach31` fleet, ctx 98304, `--no-context`,
`GUARDKIT_HARNESS=langgraph`). Synthesis is ON by default; the Coach turns should produce
real fenced-JSON verdicts with NO F20 / F23A / tool-parse-500. See `run-15-recipe.md` for the
launch command.
