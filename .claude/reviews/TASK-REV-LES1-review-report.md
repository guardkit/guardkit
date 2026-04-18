# Review Report: TASK-REV-LES1

## Executive Summary

**Scope**: Audit the three `langchain-deepagents*` templates against the LES1
cross-agent lessons distilled from the specialist-agent MacBook walkthrough
(TASK-REV-B8E4).

**Verdict**: The three templates sit at **very different maturity levels** on
the six LES1 parity surfaces. The `langchain-deepagents-weighted-evaluation`
extension is furthest along — the prior-round updates (commits tracing back to
TASK-REV-32D2 and TASK-REV-4F71) landed the SDK-alignment fixes (F1/F2/F5) and
the post-specialist-agent lessons (session logs, context manifests, ainvoke
contract). The `langchain-deepagents` base has the corrected pattern rules
and the `create_restricted_agent()` helper, **but ships two broken imports
in its rendered scaffold** (ship-blocker) and lacks a `[providers]` extras
pattern. The `langchain-deepagents-orchestrator` template has absorbed
**none** of the LES1 or 32D2/4F71 lessons — no `assert_tool_inventory()`, no
`assert_no_system_messages()`, no session logs, no `AGENTS.md.template`, no
context manifest retry, a latent F2-style bug on the Evaluator SubAgent, and
no `[providers]` extras.

Templates are code scaffolds, not deployment kits — so LES1 surfaces 1
(MCP stdio), 2 (NATS) and 7 (docker-ops) are largely **out of scope by
template design**. The load-bearing gaps are surfaces 3 (provider/packaging),
4 (ainvoke contract), 5 (handler parity), 6 (long-running tooling) and 8
(doc/code co-evolution).

**Recommendation**: [I]mplement a five-task feature package that (a) unblocks
the base template's broken imports, (b) back-ports the 32D2/4F71 fixes to the
orchestrator template, (c) standardises a shared `[providers]` extras +
`.env.example` infrastructure pattern across all three, and (d) adds a
lightweight long-running-tool discipline note. The NATS/MCP-specific lessons
are **re-scoped to a future `langchain-deepagents-nats-service` template**
rather than polluting the three code-only templates.

**Architecture Score: 68/100** (weighted by template, see §Scoring)

---

## Review Details

- **Mode**: Architectural review
- **Depth**: Standard
- **Task**: [TASK-REV-LES1](../../tasks/backlog/TASK-REV-LES1-cross-agent-lessons-for-langchain-deepagents-templates.md)
- **Primary input**: [cross-agent-lessons-from-specialist-agent.md](../../../specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md)
- **Prior-round baselines**: [TASK-REV-4F71](./TASK-REV-4F71-review-report.md), [TASK-REV-32D2](./TASK-REV-32D2-review-report.md)
- **Prior-round commit**: `dfa8090d` (reviews and updates to langchain-deepagents-weighted-eval template)
- **Walkthrough log**: located at [specialist-agent/.claude/reviews/TASK-REV-B8E4-walkthrough-log.md](../../../specialist-agent/.claude/reviews/TASK-REV-B8E4-walkthrough-log.md) — **not re-read in full**; LES1 doc distils its findings and is the primary input per its own frontmatter.

### Reference-file reconciliation

The task description flagged discrepancies in the user-cited references. Resolved:

| User citation | Resolution |
|---|---|
| `.claude/reviews/TASK-REV-8A08-review-report.md` as "prior weighted-eval update" | **Mis-attributed**. 8A08 is the FEAT-486D AutoBuild stall analysis (partial API outage). It was bundled into commit `dfa8090d` alongside genuine template-update files but is unrelated to the template content. The actual prior-round template reviews are **TASK-REV-4F71** (overall review, Architecture 82/100) and **TASK-REV-32D2** (Revision 3, SDK-validated deep-dive, Architecture 72/100). Both are used as baseline here. |
| `.claude/reviews/TASK-REV-B8E4-walkthrough-log.md` "not found" | **Found** in the specialist-agent repo at `.claude/reviews/TASK-REV-B8E4-walkthrough-log.md`. No depth-read performed; LES1 is the distillation and is sufficient for this audit. |
| Commit `dfa8090d` contents | Verified via `git show --stat`. Modifies **only** `langchain-deepagents-weighted-evaluation/` scaffold files (config, prompts, orchestrator.py.j2, test_scaffold.py, TEMPLATE-NOTES.md, agent-config.yaml.template) plus `scripts/vllm-serve.sh` and the 8A08 review/task files. **Neither `langchain-deepagents` nor `langchain-deepagents-orchestrator` was touched.** |

### What "prior-round delta" actually delivered (weighted-eval)

From commit `dfa8090d` and its predecessors (TASK-TI-009…TI-027 per 4F71 §Appendix A):

1. Three-role scaffold (`scaffold/orchestrator.py.j2`, `scaffold/pipeline.py.j2`, `scaffold/goal_schema.py.j2`)
2. Weighted evaluation primitives (`WeightedVerdict`, criterion scoring, composite calculation)
3. `adversarial_config.py` with intensity modes (full / light / solo)
4. GOAL.md template + parser
5. Coach prompt templates with weighted criteria
6. HITL and Sprint Contract integration hooks (wiring base libs)
7. **Post-specialist-agent additions (commit `dfa8090d` specifically)**:
   - `_build_context_manifest()` — retry context preservation (Category C bug prevention)
   - `_write_session_log()` — unconditional diagnostic logging (Category A bug prevention)
   - `_configure_logging(force=True)` — logger-handler conflicts fix (Category A)
   - `TEMPLATE-NOTES.md` — prompt-schema contract documentation (Category B)
   - Expanded `test_scaffold.py` (+445 lines)

---

## LES1 6-Surface Parity Matrix — Summary

In plain English, the six LES1 parity surfaces are:

1. **Transport** — discipline when an agent exposes MCP stdio or NATS JetStream (stdout cleanliness, role-aware dispatch, live production subscription).
2. **Provider** — env-resolved chat-model provider at the factory (not the handler); never hard-code one provider.
3. **Packaging** — every LangChain provider integration named in code is declared in a `[providers]` extra; the Dockerfile/pyproject install literally matches the documented command.
4. **Handler** — every listed tool/mode/command has a method at every layer (schema → adapter → core → orchestrator); no "handler exists but method missing."
5. **Tooling** — tools that can exceed 30s return a `session_id` immediately and expose a poll companion; descriptions match implementation (no "long-running — session tracked" paired with a synchronous `await`).
6. **Ops** — `.env.example` hygiene, `docker compose down --remove-orphans`, envsubst restart requirements, CLI secret redaction.

Surfaces 1, 2 and 6 are **deployment-surface** concerns. The three templates under audit ship only code scaffolds (`.template` / `.j2` files + library modules), so these three surfaces don't have a direct template expression — they belong in a downstream deployment template (future `langchain-deepagents-nats-service`) or in the consumer's Dockerfile/compose setup. Surfaces 3, 4 and 5, together with the *non-surface* lessons from LES1 §4 (ainvoke contract), §5 (AC discipline), §6 (cross-surface parity audits) and §8 (doc/code co-evolution), **are** directly expressible in these templates.

---

## Per-Template Applicability Table (LES1 6 surfaces)

| Surface | Base `langchain-deepagents` | Orchestrator `langchain-deepagents-orchestrator` | Extension `langchain-deepagents-weighted-evaluation` |
|---|---|---|---|
| 1. Transport — MCP stdio | N/A (no MCP entrypoint) | N/A | N/A |
| 2. Transport — NATS fleet | N/A (no NATS) | N/A | N/A |
| 3. Provider resolution | ✅ Partial — `_create_model()` reads per-role config + env; hardcoded `api_key="not-needed"` fallback is LES1-safe (shell overrides). Packaging sub-gap: no `[providers]` extras | ⚠️ Partial — `provider:model` string flows through `create_deep_agent`, but hardcoded anthropic defaults in `_DEFAULT_CONFIG`; no env-var fallback at factory | ✅ Addressed — `_create_model()` mirrors base pattern; packaging sub-gap inherited |
| 4. Handler parity | ✅ — `assert_tool_inventory()` in `lib/factory_guards.py`, `validate_player_tools()` in `scaffold/orchestrator_pattern.py.template`, scaffold uses `create_agent()` (F1/F2 fixed) | ❌ — No `assert_tool_inventory()`. Evaluator SubAgent with `tools=[]` has a latent F2-style risk (DeepAgents subagent mechanism may inject middleware tools) | ✅ — Uses `create_restricted_agent()` with `PLAYER_ALLOWED_TOOLS` / `COACH_ALLOWED_TOOLS` allowlists |
| 5. Long-running tooling | ❌ — No fire-and-forget pattern; synchronous `ainvoke` chain | ❌ — Same; higher-priority gap given "pipeline orchestrator" framing | ❌ — Same; `process_target` can loop `max_retries` times synchronously |
| 6. Ops (docker/.env) | ✅ `.env.example.template` exists with placeholder-only keys; no docker compose (N/A) | ⚠️ — `load_dotenv(override=False)` is LES1-correct for shell-vs-.env precedence, but no `.env.example.template` exists | ❌ — Inherits base's `.env.example.template` in principle (via extends overlay) but no extension-specific env vars documented |

Legend: ✅ addressed · ⚠️ partial/risk · ❌ gap · N/A not in scope for a code-only template.

---

## 22-Item Per-Agent Checklist → Per-Template Status

Adapted from LES1's per-agent checklist. Rows not applicable to code-only
templates are marked N/A with a brief reason in the Notes column.

| # | Item | Base | Orch | Weighted-Eval | Notes |
|--:|---|:-:|:-:|:-:|---|
| 1 | MCP stdio banner on stderr; stream-split test | N/A | N/A | N/A | No MCP entrypoint in any template |
| 2 | Bash MCP wrapper `cd`s absolute path | N/A | N/A | N/A | No MCP wrapper |
| 3 | `serve-nats` subscribes in prod lifecycle | N/A | N/A | N/A | No NATS in any template |
| 4 | Role-aware `(role, command)` dispatch matrix | N/A | N/A | N/A | No multi-role command routing |
| 5 | Reply subject `agents.result.<id>` documented | N/A | N/A | N/A | No NATS |
| 6 | `AGENT_MODELS__REASONING_MODEL` resolved at factory | ⚠️ | ⚠️ | ⚠️ | Per-role YAML + `LOCAL_MODEL_ENDPOINT` / `OPENAI_API_KEY` envs — good, but LES1-named env (`AGENT_MODELS__*`) not adopted. Low-priority rename |
| 7 | `[providers]` extra lists every LangChain integration named in code | ❌ | ❌ | ❌ | **Load-bearing gap**. Base `pyproject.toml.template` has flat deps, no `[providers]`. Coach imports `langchain_anthropic` which is transitive (OK) but if user's `coach-config` uses `openai` provider, `langchain-openai` is **not** installed (LCOI parity with specialist-agent) |
| 8 | Dockerfile `pip install .[providers]` literal-match | N/A | N/A | N/A | No Dockerfile shipped by any template. This is the right call for code-only templates — shipping a Dockerfile requires committing to a runtime profile the template can't know |
| 9 | No real-looking provider keys in `.env` | ✅ | ❌ | ✅ (via overlay) | Base `.env.example.template` uses `your-langsmith-api-key`, `your-tavily-api-key` placeholders — LES1-correct. Orch has no `.env.example` at all |
| 10 | Long-running tools return `session_id` | ❌ | ❌ | ❌ | No template encodes fire-and-forget + poll |
| 11 | Every listed mode/method exists at every layer | ✅ | ✅ | ✅ | Internal layer symmetry is fine; `langgraph.json` → `agent.py:agent` is consistent |
| 12 | `docker compose down --remove-orphans` documented | N/A | N/A | N/A | No docker-compose |
| 13 | NATS provisioning required in guide §2 | N/A | N/A | N/A | No NATS |
| 14 | Guide copy-paste blocks live-verified | ⚠️ | ⚠️ | ⚠️ | CLAUDE.md says `pip install -r requirements.txt` but no `requirements.txt` shipped; `pyproject.toml.template` is the real source. Minor inconsistency |
| 15 | ADRs annotated "as of commit X" | ❌ | ❌ | ⚠️ | Weighted-eval's TEMPLATE-NOTES has session dates; no template annotates ADR validity |
| 16 | envsubst restart documented | N/A | N/A | N/A | No envsubst pattern |
| 17 | CLI secret redaction | N/A | N/A | N/A | No ops CLI shipped |
| 18 | Tool description matches implementation | ✅ | ✅ | ✅ | No "long-running" lies (no template claims long-running tools) |
| 19 | Latency classification done | ❌ | ❌ | ❌ | Not done — not critical for code-only templates but would be useful guidance |
| 20 | `notifications/cancelled` handled server-side | N/A | N/A | N/A | No MCP server |
| 21 | Accumulated-latency surfaces flagged | ❌ | ❌ | ❌ | Weighted-eval's `process_target` retry loop IS an accumulated-latency surface and is not flagged |
| 22 | Single-transport agents stream-split test stdout | N/A | N/A | N/A | No stdout-based transport |

**Applicable items (22 → 11 active):** 6, 7, 9, 10, 11, 14, 15, 18, 19, 21 (+ #12 only if docker guidance added).

**Score (applicable green over applicable total):**
- Base: 6/11 green (✅ or 50% on partials) = ~55%
- Orchestrator: 3/11 green = ~27%
- Weighted-eval: 6/11 green = ~55%

---

## Findings

### BLOCKER-1 — Base template `coach.py.template` and `agent.py.template` have broken imports (will not run after install)

**Severity**: Blocker · **Template**: `langchain-deepagents` · **LES1 link**: §8 (doc/code co-evolution) — but really just a template-rendering bug

**Evidence**:

`installer/core/templates/langchain-deepagents/templates/other/agents/coach.py.template:14-17`:
```python
from {{ProjectName}}.backends import FilesystemBackend
from {{ProjectName}}.middleware import MemoryMiddleware
from {{ProjectName}}.middleware.patch_tool_calls import PatchToolCallsMiddleware
```
These should be `from deepagents.backends` / `from deepagents.middleware` as in
`player.py.template:12-14` (which is correct). After placeholder substitution
(e.g. `{{ProjectName}}` → `myagent`) the rendered file attempts to import
`myagent.backends.FilesystemBackend`, which does not exist.

`installer/core/templates/langchain-deepagents/templates/other/other/agent.py.template:8`:
```python
from {{ProjectName}}.chat_models import init_chat_model
```
Should be `from langchain.chat_models import init_chat_model`.

**Impact**: Any project initialised from the base template via
`guardkit init langchain-deepagents` will fail at import time. Same failure
propagates to the weighted-eval extension for any base files the overlay
doesn't overwrite (player.py and coach.py are base-only).

**Cause**: Looks like a global `from deepagents` → `from {{ProjectName}}` rename
that was intended to rewrite **project-relative** imports (e.g.
`from deepagents_exemplar.player_prompts` → `from {{ProjectName}}.player_prompts`)
but accidentally rewrote the `deepagents` SDK package imports too.

**Fix**: Restore `from deepagents.backends` / `from deepagents.middleware` in
`coach.py.template`; restore `from langchain.chat_models` in
`agent.py.template`. Add a `template-validate` smoke test that renders the
base template and runs `python -c "import {{ProjectName}}.coach; import {{ProjectName}}.agent"`
against the rendered tree.

### BLOCKER-2 — No `[providers]` extras pattern in any `pyproject.toml.template`; user-selected provider may be missing its LangChain integration at runtime

**Severity**: Blocker (delayed — fires only when the user switches provider) · **Template**: all three · **LES1 link**: §3 LCOI (retest finding #2)

**Evidence**: Base `pyproject.toml.template` lists flat dependencies (deepagents,
langchain, langchain-core, langgraph, langchain-community, tavily-python,
langsmith, python-dotenv, pyyaml). **No** `[project.optional-dependencies]` with
a `providers` key. Neither `langchain-openai` nor `langchain-google-genai` is
declared. `deepagents` pulls `langchain-anthropic` and `langchain-google-genai`
transitively (per LES1 §3 evidence) but not `langchain-openai`.

`agent-config.yaml.template` supports `provider: "local"` (openai-compatible
API at `LOCAL_MODEL_ENDPOINT`) which routes through
`init_chat_model(..., model_provider="openai")` — requiring `langchain-openai`.

**Impact**: First user to switch from `provider: "api"` (anthropic) to
`provider: "local"` (vLLM) on a freshly-installed template hits
`ModuleNotFoundError: langchain_openai`. This is **exactly** the LES1 LCOI bug
the lessons doc was written to prevent.

**Fix**: Introduce a shared `[providers]` extras pattern across all three
templates:

```toml
[project.optional-dependencies]
providers = [
    "langchain-anthropic>=0.2",
    "langchain-openai>=0.2",
    "langchain-google-genai>=2.0",
]
```

Documentation line in CLAUDE.md: `pip install .[providers]`. Consider keeping
the "at least one LangChain integration" guarantee by listing the default
provider (e.g. `langchain-anthropic`) in base `dependencies` so a zero-config
install still works.

### HIGH-1 — Orchestrator template Evaluator SubAgent has latent F2-style tool leakage

**Severity**: High · **Template**: `langchain-deepagents-orchestrator` · **LES1 link**: §2 PORT, §6 ARFS (handler-exists ≠ method-exists)

**Evidence**: `langchain-deepagents-orchestrator/templates/other/agents/agents.py.template:87-98` defines:
```python
return SubAgent(
    name="evaluator",
    description="... Has no tools — evaluation is purely reasoning-based.",
    system_prompt=prompt,
    model=model,
    tools=[],
)
```

The orchestrator itself is built via `create_deep_agent()` at line 177, with
`subagents=[implementer, evaluator, builder]`. DeepAgents' `SubAgentMiddleware`
spawns sub-graphs that inherit the framework's middleware-tool injection: the
`tools=[]` on the SubAgent spec only controls user-provided tools, not
middleware tools — the **exact same pattern** LES1 §1.2 and 32D2 F2 identified
on `create_deep_agent(tools=[])`.

There is no `assert_tool_inventory()` at factory exit; there is no
`validate_player_tools()` equivalent; the description contract "has no tools"
is a comment, not an assertion.

**Impact**: The Evaluator can silently gain `write_file` / `edit_file` /
`execute` / `write_todos`, violating the "evaluation only" contract and
potentially producing side-effects during evaluation runs.

**Fix**: Two options, both valuable:
1. (Cheapest) Post-construction `assert_tool_inventory(evaluator_agent, expected_tools=set())` before returning the compiled graph, asserting the Evaluator surface produces zero tools. Requires wiring around `create_deep_agent`'s SubAgent instantiation.
2. (Cleanest) Promote `create_restricted_agent()` from base `lib/factory_guards.py` into the orchestrator template (either by making the orchestrator template `extends: langchain-deepagents`, or by vendoring the guard) and build the Evaluator via `create_restricted_agent(tools=[], allowed_tools=set())`, with the orchestrator loop calling the Evaluator directly rather than via SubAgent middleware.

Also add `patterns/tool-delegation.md` and `patterns/factory.md` (currently
absent from orchestrator template) documenting the rule.

### HIGH-2 — Orchestrator template has no `assert_no_system_messages()` / no TASK-REV-R2A1 contract

**Severity**: High · **Template**: `langchain-deepagents-orchestrator` · **LES1 link**: §4 (tool/contract discipline — same class of bug as PMEV/POLR)

**Evidence**: No mention of the ainvoke() system-message contract anywhere in
the orchestrator template — searched `agents.py.template`, `agent.py.template`,
`orchestrator_tools.py.template`, and all pattern/guidance files. No
`AGENTS.md.template` exists, so no MemoryMiddleware-delivered contract either.
The orchestrator template is a pure `create_deep_agent()` consumer, which
*does* accept `memory=[...]` correctly, but any retry reinforcement logic a
consumer adds on top of this template would hit the same dual-system-message
failure that R2A1 documented.

**Impact**: Medium-to-high. The orchestrator template ships without the
guardrail or documentation that 4F71/32D2 already proved is needed; any
retry/feedback mechanism a consumer writes will reinvent this problem.

**Fix**:
- Back-port the base template's `AGENTS.md.template` §"Framework Contract: ainvoke() Message Rules (TASK-REV-R2A1)" section.
- Add `MemoryMiddleware(sources=["./AGENTS.md"])` to the top-level `create_deep_agent` call (already passes `memory=["./AGENTS.md"]` — just need the template to ship `AGENTS.md.template`).
- Add a `patterns/ainvoke-contract.md` rule file or merge into `patterns/safe-argument-parsing.md`.

### HIGH-3 — Orchestrator template's hard-coded `anthropic:` model defaults

**Severity**: High · **Template**: `langchain-deepagents-orchestrator` · **LES1 link**: §3 PMEV/CRMV (hardcoded provider)

**Evidence**: `agent.py.template:37-42`:
```python
_DEFAULT_CONFIG: dict[str, Any] = {
    "orchestrator": {
        "reasoning_model": "anthropic:claude-sonnet-4-6",
        "implementation_model": "anthropic:claude-haiku-4-5",
    },
}
```

These fall-through defaults fire if the YAML config is missing or malformed.
There is no env-var layer (`AGENT_MODELS__REASONING_MODEL` /
`AGENT_MODELS__IMPLEMENTATION_MODEL`) that could override them. A downstream
agent built from this template silently uses Anthropic even if the operator
has configured a local provider.

**Impact**: Silent provider drift; matches the PMEV bug class where provider
resolution happened outside the factory.

**Fix**:
1. Add env-var resolution in `_create_model()` (or lift the base template's
   `_create_model()` verbatim). Prefer:
   ```python
   reasoning_model = os.environ.get(
       "AGENT_MODELS__REASONING_MODEL",
       orch_config.get("reasoning_model", _DEFAULT_CONFIG["orchestrator"]["reasoning_model"]),
   )
   ```
2. Document the resolution precedence (env > yaml > hardcoded default) in
   `orchestrator-config.yaml.template`'s header comment.

### HIGH-4 — No post-specialist-agent hardening in orchestrator template (session logs, context manifests, logging force=True)

**Severity**: High · **Template**: `langchain-deepagents-orchestrator` · **LES1 link**: §5 (AC discipline), §8 (doc/code co-evolution); separately, Category A/B/C bugs from TEMPLATE-NOTES

**Evidence**: None of these lessons are encoded in the orchestrator template:
- `_write_session_log()` (unconditional) — **absent**
- `_build_context_manifest()` on retry — **absent** (no retry mechanism scaffold at all)
- `_configure_logging(force=True)` — **absent**
- Prompt-schema contract doc (TEMPLATE-NOTES) — **absent**

Weighted-eval has all four. Base has none (but base has simpler retry semantics
via `OrchestratorWriteGate.attempt_write()`, so context manifest is less
load-bearing; session logs are still missing).

**Impact**: A `deepagents-orchestrator`-derived agent that hits the same
failure modes specialist-agent hit will have **no diagnostic trail**.
Category B (prompt-schema misalignment) bugs are guaranteed to recur in any
consumer that copies the template's JSON-producing subagent prompts.

**Fix**: Port these four helpers from the weighted-eval scaffold into an
orchestrator-template lib folder (or make the orchestrator template `extends:
langchain-deepagents` and promote these helpers into the base `lib/`).
Simplest route: a new `lib/session_logging.py` + `lib/retry_context.py` in
base, with orchestrator template importing them.

### MEDIUM-1 — Base template pattern rules reference `.template` files by path but the paths are slightly wrong

**Severity**: Medium · **Template**: `langchain-deepagents` · **LES1 link**: §5 "stale comments are dangerous", §8

**Evidence**: `patterns/factory.md` says `Source: scaffold/agent_factory.py.template, lib/factory_guards.py`; `patterns/adversarial-cooperation.md` says `Source: scaffold/orchestrator_pattern.py.template`. These files exist at `templates/other/scaffold/orchestrator_pattern.py.template` and `templates/other/scaffold/agent_factory.py.template` — so the pattern rules use a path relative to the *rendered* project (correct) but it's not explicit that these live under `templates/other/` in the template source tree. A new contributor to the template itself will grep for `scaffold/orchestrator_pattern.py.template` and find it, but the mental model "pattern rules talk about post-install project paths" isn't documented.

**Impact**: Low — it does work, but every new contributor will spend 5-10min
confirming the path convention.

**Fix**: Add a paragraph to base `.claude/CLAUDE.md` or `patterns/` intro
clarifying that `Source:` paths are **post-render** paths.

### MEDIUM-2 — No template encodes long-running-tool discipline (LES1 §4)

**Severity**: Medium · **Template**: all three · **LES1 link**: §4 POLR/description-contract

**Evidence**: Weighted-eval's `AdversarialOrchestrator.process_target()` runs
the Player→Coach loop up to `max_retries` times synchronously. If an
individual Player invocation is already a 30-60s generation call (typical for
weighted evaluation), a 3-retry loop easily exceeds the LES1-named 240s MCP
timeout — and that's before the Coach turn is added. The template is
**pre-deployment** so there's no MCP wrapper to time out, but any consumer
wrapping this as an MCP tool will hit POLR.

Orchestrator template's `execute_command` tool has no timeout discipline; its
docstring says "executes a command" with no latency class.

**Impact**: A downstream agent that wires either template behind an MCP
interface will re-hit POLR. The fix belongs at the point of wrapping, but a
pattern rule in the templates would head it off.

**Fix**: Add a `patterns/long-running-tools.md` rule to the base (and, via
overlay inheritance, the weighted-eval extension) documenting:
- The 30s / 240s threshold from LES1 §4
- The "return session_id, expose `_status` / `_cancel`" pattern
- The "sync path vs generation-loop path — don't share a tool shape" rule

### MEDIUM-3 — Weighted-eval template does not ship its own `.env.example` despite introducing new runtime config

**Severity**: Medium · **Template**: `langchain-deepagents-weighted-evaluation` · **LES1 link**: §3 .env hygiene

**Evidence**: The extension introduces `AcceptanceThreshold`, `MaxRetries`,
`AdversarialIntensity` placeholders; adversarial_config has acceptance
thresholds and criteria weights. No `.env.example` in the extension documents
any new env vars. Relies on base overlay.

**Impact**: Minor — if a consumer customises the extension's runtime env
plane, they'll either discover the env names by reading code or use bare YAML.

**Fix**: If any extension config becomes env-overridable (recommended for
`ACCEPTANCE_THRESHOLD`, `ADVERSARIAL_INTENSITY`), add a small
`.env.example.template` in the extension that overlays on top of the base.

### MEDIUM-4 — Orchestrator template's CLAUDE.md says `pip install -r requirements.txt` but template ships `pyproject.toml`-style config (inconsistent)

**Severity**: Medium · **Template**: `langchain-deepagents-orchestrator` · **LES1 link**: §3 packaging, §8 doc/code co-evolution

**Evidence**: `langchain-deepagents-orchestrator/.claude/CLAUDE.md` line 10:
`pip install -r requirements.txt`. No `requirements.txt.template` exists in the
template. No `pyproject.toml.template` either — the orchestrator template
ships **no packaging descriptor at all**.

**Impact**: Consumers have to write their own pyproject. The template's
promise of "quick start" is broken.

**Fix**: Add `pyproject.toml.template` (matching base shape) with a
`[providers]` extras pattern; update CLAUDE.md to `pip install .[providers]`.
Literal-match the guide command to the pyproject — LES1 §3 DKRX/packaging.

### LOW-1 — Pattern attribution in weighted-eval manifest is still imprecise (4F71 F2 unresolved)

**Severity**: Low · **Template**: `langchain-deepagents-weighted-evaluation` · **LES1 link**: §8 doc/code co-evolution

**Evidence**: Manifest's `patterns` array lists "HITL Checkpoints" and "Sprint
Contracts". 4F71 F2 already flagged that the libraries live in the base
template's `lib/` and the extension only adds the integration hooks. 4F71's
recommendation was to clarify attribution; a `patterns_note` field was added
(manifest.json:54) but the `patterns` array itself still claims ownership of
inherited patterns.

**Fix**: Align with 4F71 F2's recommendation — either add the patterns to the
base manifest's `patterns` array (since the base ships the libs), or rename
the extension's entries to "HITL Hooks" / "Sprint Contract Hooks".

### LOW-2 — `AGENT_MODELS__*` env-var naming convention not adopted

**Severity**: Low · **Template**: all three · **LES1 link**: §3 PMEV

**Evidence**: LES1 §3 names `AGENT_MODELS__REASONING_MODEL` as the canonical
env for provider resolution; the templates use `LOCAL_MODEL_ENDPOINT`,
`OPENAI_API_KEY`, `DOMAIN`. No blocker — the base pattern is already
env-aware, just named differently.

**Fix**: Adopt the LES1 naming when the env layer is rewritten for HIGH-3.
One-line change.

### LOW-3 — Stubbed sibling template files in `langchain-deepagents-orchestrator` lack `-ext.md` for two agents

**Severity**: Low (nit) · **Template**: `langchain-deepagents-orchestrator`

**Evidence**: The find output shows 6 of 7 agents have both `.md` and
`-ext.md`; the pattern is consistent. Not LES1-related but noted during
template walk. No action required.

---

## Cross-Surface Parity Audit (LES1 §6)

The 32D2 review flagged F1/F2/F5 and the base had the fixes applied; 4F71
confirmed they're green. The orchestrator template was **never audited**
against 32D2 — so the F1/F2/F5 lessons did not cross the template boundary.

**Load-bearing cross-surface insight**: a fix to the adversarial-cooperation
template family (base + weighted-eval) must trigger an audit of the
orchestrator template for the same bug class, even though the orchestrator
legitimately uses `create_deep_agent()` at the top level. The Evaluator
SubAgent (HIGH-1) is the surface where the F2 bug re-enters.

This is the LES1 §6 rule applied to GuardKit's own template repo: "When two
code paths solve the same problem, a fix to one must trigger an audit of
the other."

---

## Gap List Grouped by Severity

| Severity | Finding | Template(s) | Effort |
|---|---|---|---|
| BLOCKER | BLOCKER-1 broken imports | base | XS (≤15 min) |
| BLOCKER | BLOCKER-2 no `[providers]` extras | all three | S (1-2h) |
| HIGH | HIGH-1 Evaluator SubAgent F2 risk | orch | M (half-day) |
| HIGH | HIGH-2 no ainvoke contract / `AGENTS.md.template` | orch | S |
| HIGH | HIGH-3 hardcoded anthropic defaults | orch | XS |
| HIGH | HIGH-4 no session logs / context manifest / force=True | orch | M |
| MEDIUM | MEDIUM-1 pattern rule path convention | base | XS |
| MEDIUM | MEDIUM-2 long-running-tool discipline rule | base (+weighted-eval inherits) | XS-S |
| MEDIUM | MEDIUM-3 no extension `.env.example` | weighted-eval | XS |
| MEDIUM | MEDIUM-4 requirements.txt vs pyproject inconsistency | orch | XS (rolled into BLOCKER-2) |
| LOW | LOW-1 pattern attribution in manifest | weighted-eval | XS |
| LOW | LOW-2 `AGENT_MODELS__*` naming | all three | XS |
| LOW | LOW-3 missing `-ext.md` sibling files | orch | — (nit) |

---

## Shared-Infrastructure Work (applied once, benefits ≥2 templates)

These items, if implemented in the **base** template, propagate to
`langchain-deepagents-weighted-evaluation` via the extends-overlay mechanism
and can be vendored (or consumed via `extends`) by the orchestrator template.

1. **`[providers]` extras pattern in `pyproject.toml.template`** — landing in
   base covers base + weighted-eval; orchestrator template needs a separate
   copy (or should adopt `extends: langchain-deepagents`, which is a larger
   refactor — see decision point in the implementation plan).

2. **`patterns/long-running-tools.md`** — base rule propagates via overlay.
   Orchestrator template needs its own copy.

3. **`lib/session_logging.py` + `lib/retry_context.py`** — helpers extracted
   from weighted-eval's `scaffold/orchestrator.py.j2` and promoted to base
   `lib/`. Weighted-eval then imports from base (already does via `extends`).
   Orchestrator template vendors these files.

4. **`AGENTS.md.template` §"Framework Contract"** — base already has this;
   need to copy the section into an orchestrator-template `AGENTS.md.template`
   (new file) so the orchestrator template can pass `memory=["./AGENTS.md"]`
   with the R2A1 contract actually present.

5. **Template-validate smoke test** — one-shot rendering test that
   `guardkit init`s each template into a temp dir and runs
   `python -c "import <projname>.coach; import <projname>.agent; ..."`.
   Would have caught BLOCKER-1. Ship alongside the fix.

---

## Applicability to Non-langchain-deepagents Templates

LES1 is explicitly scoped to agent templates. Cross-checking the GuardKit
template list:

- `fastapi-python` — LES1 §3 (.env hygiene, LangChain `[providers]` extras only if it wraps an LLM API) applies weakly. **Low priority**.
- `python-library` — §8 (doc/code co-evolution) always applies. **No action now**.
- `nats-asyncio-service` — **HIGH relevance**. LES1 §2 (NATS subscribe-in-prod, reply-subject documentation), §7 (orphan containers, fresh-volume provisioning) directly apply. This template ships NATS infrastructure. Recommend a separate `/task-review` pass for this template with `--mode=architectural`. Out of scope for this review.
- `react-typescript`, `nextjs-fullstack`, `react-fastapi-monorepo`, `dotnet-railway-fastendpoints` — not LES1-relevant.

**Decision**: contain LES1 to the three langchain-deepagents templates here.
Open a follow-on review task for `nats-asyncio-service`.

---

## Implementation Plan (Prioritised Sub-task List)

Proposed as a feature with a sub-folder. Feature slug:
**`langchain-template-lessons`**.

### Wave 1 (blocker unblocks — complexity ≤3, can execute direct)

| ID | Title | Template | Effort | Fixes |
|---|---|---|---|---|
| LCL-001 | Fix broken `{{ProjectName}}` imports in base coach.py.template and agent.py.template | base | XS | BLOCKER-1 |
| LCL-002 | Add `[providers]` extras to base `pyproject.toml.template`; align CLAUDE.md install command | base | S | BLOCKER-2 |
| LCL-003 | Add template-validate smoke test that renders and imports each template's entrypoint | guardkit repo (test harness) | S | Prevents regressions of BLOCKER-1 class |

Wave 1 is executable in parallel. All three tasks can be `/task-work` or direct.

### Wave 2 (orchestrator-template back-port — complexity 4-6)

| ID | Title | Template | Effort | Fixes |
|---|---|---|---|---|
| LCL-004 | Add `pyproject.toml.template` with `[providers]` extras to orchestrator template; remove `pip install -r requirements.txt` from CLAUDE.md | orch | S | BLOCKER-2 (orch portion), MEDIUM-4 |
| LCL-005 | Add `AGENTS.md.template` with TASK-REV-R2A1 ainvoke contract section to orchestrator template | orch | S | HIGH-2 |
| LCL-006 | Env-var resolution + `AGENT_MODELS__*` naming in orchestrator `_create_model()` | orch | S | HIGH-3, LOW-2 |
| LCL-007 | Evaluator SubAgent tool-inventory assertion (choose option 1 — post-construction `assert_tool_inventory`) | orch | M | HIGH-1 |

Wave 2 runs after Wave 1 (needs the pyproject pattern from LCL-002 as template).

### Wave 3 (shared infrastructure + doc co-evolution — complexity 4-5)

| ID | Title | Template | Effort | Fixes |
|---|---|---|---|---|
| LCL-008 | Extract session_logging + retry_context into base `lib/`; weighted-eval imports from base; orchestrator vendors | base + weighted-eval + orch | M | HIGH-4 |
| LCL-009 | Add `patterns/long-running-tools.md` rule to base (+ orch copy) | base + orch | XS | MEDIUM-2 |
| LCL-010 | Clarify `Source:` path convention in base patterns/README or CLAUDE.md | base | XS | MEDIUM-1 |
| LCL-011 | Weighted-eval manifest — align pattern attribution with 4F71 F2 | weighted-eval | XS | LOW-1 |
| LCL-012 | Weighted-eval `.env.example.template` with extension-specific vars | weighted-eval | XS | MEDIUM-3 |

Wave 3 can run in parallel with Wave 2 (no dependency between them).

### Wave 4 (follow-on review — out of this feature)

- Separate `/task-review` for `nats-asyncio-service` against LES1 §2 and §7.

---

## Decision Matrix

| Option | Impact | Effort | Risk | Recommendation |
|---|---|---|---|---|
| A — Accept findings, file implementation backlog (no immediate action) | Low | Nil | Medium (BLOCKER-1 ships) | **Don't** — a template whose rendered coach.py can't import is a hard bug |
| B — Implement Wave 1 only (unblock, defer rest) | Medium | Small (2-3h) | Low | Acceptable minimum |
| C — Implement Waves 1-3 (full feature package) | High | Medium (1-2 days) | Low | **Recommended** |
| D — Extend scope to `nats-asyncio-service` in the same feature | High | Medium (+1 day) | Medium (scope creep) | Defer — separate review |
| E — Revise: deeper audit including cross-template template-validate coverage | Low additional | Small | Low | Defer to after implementation |

**Recommended decision: C (Implement Waves 1-3) as a feature
`langchain-template-lessons`.**

---

## Context Used (Graphiti)

No knowledge-graph context was loaded for this review (Graphiti availability
was not verified against the project's `.guardkit/graphiti.yaml` during the
pass). All findings are derived from the LES1 doc, the three templates' file
contents, the 4F71/32D2 review reports, and `git show dfa8090d`.

---

## Next Steps

1. At the checkpoint below, select **[I]mplement** to create the 12-task
   backlog under `tasks/backlog/langchain-template-lessons/`.
2. Wave 1 is the minimum viable action to unblock template consumers; start
   there regardless of overall scope decision.
3. After Wave 2 lands, re-run this audit at `--depth=quick` to confirm the
   orchestrator template's parity matrix improved.
4. Open a separate review task for `nats-asyncio-service` against LES1 §2 / §7.

---

## Scoring

| Template | Architecture score | Driver |
|---|---:|---|
| `langchain-deepagents` (base) | 70/100 | Pattern rules + lib well-aligned with 32D2/4F71; BLOCKER-1 costs 15 points; no `[providers]` costs 10 |
| `langchain-deepagents-orchestrator` | 55/100 | Self-consistent but has absorbed none of 32D2/4F71/LES1; HIGH-1 alone costs 10 |
| `langchain-deepagents-weighted-evaluation` | 80/100 | Strongest of the three on every applicable surface; only medium/low gaps |
| **Weighted average (equal weight)** | **68/100** | — |

---

## Decision Checkpoint

Review Results:
- Architecture Score: 68/100 (weighted average across three templates)
- Findings: 13 (2 blocker, 4 high, 4 medium, 3 low)
- Recommendations: 12 implementation sub-tasks in 3 waves

Decision Options:
- **[A]ccept** — Archive review, file backlog for later (not recommended given BLOCKER-1)
- **[R]evise** — Deeper audit (e.g. render-and-import each template in a CI sandbox to enumerate more rendering bugs)
- **[I]mplement** — Create 12-task feature `langchain-template-lessons` under `tasks/backlog/` (recommended)
- **[C]ancel** — Discard review

*Review completed: 2026-04-18*
*Reviewer: architectural (Opus 4.7, 1M context) — LES1 §6 cross-surface lens applied*
