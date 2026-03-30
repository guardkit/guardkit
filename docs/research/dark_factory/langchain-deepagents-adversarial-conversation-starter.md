# langchain-deepagents-adversarial Template — Conversation Starter

## For: `/template-create` session · Phase 5 of Pipeline Orchestrator build plan · March 2026

---

## Purpose of this document

This is the context brief for creating a new GuardKit template: `langchain-deepagents-adversarial`. This template will be **harvested from the working Pipeline Orchestrator** — NOT built speculatively upfront. It encodes the Orchestrator + Implementer + Evaluator pattern with a reasoning model driving tool selection as a reusable scaffold for the LangChain DeepAgents SDK.

**IMPORTANT — What this template is NOT:** It is NOT a re-creation of patterns that already exist in the base and weighted-evaluation templates. Those templates already contain the universal fixes (JsonExtractor, factory guards, domain validator, observability, preflight) and the adversarial patterns (intensity routing, HITL, weighted Coach, sprint contracts). This template captures what is **genuinely new** in the Pipeline Orchestrator.

**When to create this template:** After the Pipeline Orchestrator (`guardkit/guardkitfactory`) is working in production and has been validated through real use. This follows the proven methodology: exemplar → template → project → update template.

---

## What already exists (DO NOT REBUILD)

The following components are already implemented and working in existing GuardKit templates. This template extends them; it does not replace them.

### Base `langchain-deepagents` template — Universal fixes (all at `installer/core/templates/langchain-deepagents/`)

| Component | File | What It Does |
|-----------|------|--------------|
| `JsonExtractor` | `lib/json_extractor.py` | 5-strategy cascade extraction (prevents 9/31 TRF fixes) |
| Factory guards | `lib/factory_guards.py` | Tool allowlisting + assertions (prevents 4/31 fixes) |
| Domain validator | `lib/domain_validator.py` | Type-aware validation with coercion (prevents 4/31 fixes) |
| Observability | `lib/observability.py` | Token tracking, stage timing, error context |
| Pre-flight | `lib/preflight.py` | Import resolution, config validation |
| Content pipeline | `lib/content_pipeline.py` | Canonical normalize → extract → validate → write |
| Checkpoint hooks | `lib/checkpoint_hooks.py` | Checkpoint/resume/lock management |
| Sprint contract | `lib/sprint_contract.py` | Sprint contract negotiation pattern |
| Player/Coach templates | `templates/other/agents/` | Agent factory templates with tool separation |
| Orchestrator scaffold | `templates/other/scaffold/orchestrator_pattern.py.template` | Three-role wiring scaffold |
| Agent factory | `templates/other/scaffold/agent_factory.py.template` | Factory with tool allowlisting |
| Prompt templates | `templates/other/prompts/` | Player + Coach prompt builders with CRITICAL section |
| Domain config | `templates/other/example-domain/DOMAIN.md.template` | GOAL.md equivalent scaffold |
| Model compatibility | `docs/reference/model-compatibility.md` | Per-model/parser known issues |
| 7 specialist guidance files | `.claude/rules/guidance/` | Adversarial cooperation, DeepAgents factory, domain config, tools, testing, prompts, entrypoint |
| 5 pattern docs | `.claude/rules/patterns/` | Adversarial cooperation, domain-driven config, factory, memory injection, tool delegation |

### `langchain-deepagents-weighted-evaluation` template — Adversarial patterns (all at `installer/core/templates/langchain-deepagents-weighted-evaluation/`)

| Component | File | What It Does |
|-----------|------|--------------|
| `IntensityRouter` | `config/adversarial_config.py` | `AdversarialIntensity` enum (FULL/LIGHT/SOLO), sampling rates, bypass config |
| Weighted criteria config | `config/adversarial_config.py` | `load_adversarial_config()`, weight validation, intensity overrides |
| HITL checkpoints | `hooks/hitl.py` | `CheckpointAction` (approve/reject/override/adjust_weights/halt) |
| Sprint contract | `hooks/sprint_contract.py` | Contract negotiation hooks |
| Three-role orchestrator | `scaffold/orchestrator.py.j2` | Jinja2 scaffold for Orchestrator + Player + Coach wiring |
| Weighted pipeline | `scaffold/pipeline.py.j2` | Weighted evaluation with acceptance thresholds |
| Coach prompt | `prompts/coach_template.py` | Scepticism-tuned Coach prompt builder |
| Adversarial base | `prompts/adversarial_base.py` | Player system prompt with domain injection |
| Goal schema | `scaffold/goal_schema.py.j2` + `templates/goal.md.j2` | GOAL.md parser and Pydantic models |
| 4 test files | `tests/` | Coach, goal, orchestrator, scaffold tests |

---

## What this template adds (genuinely new from Pipeline Orchestrator)

These patterns will be proven in the Pipeline Orchestrator and then extracted into this template. They do not exist in either existing template.

### 1. Reasoning Model Orchestration Layer

A reasoning model (Gemini 3.1 Pro API, Claude API, or local vLLM) drives which tools to invoke, in what order, and with what context. This is NOT the same as the existing plain Python orchestrator loop — it's an LLM making tool-selection decisions.

The reasoning model:
- Reads the project's architectural context from Graphiti
- Selects the appropriate pipeline mode (greenfield / feature / review-fix)
- Chooses which slash commands to invoke and in what order
- Assembles context parameters for each command
- Evaluates outputs and decides whether to proceed or revise

**Key constraint:** The reasoning model MUST differ from the implementation model (Block paper + Anthropic validation: self-evaluation fails). Provider-agnostic via `orchestrator-config.yaml`.

### 2. External Tools as DeepAgents Tools

The template provides a pattern for wrapping external CLI commands or API calls as DeepAgents tools. In the orchestrator, this means GuardKit slash commands (`/system-arch`, `/feature-spec`, `autobuild`, `/task-review`) become tools the reasoning model can invoke.

**Phase 1 pattern:** Each tool wraps a call to Claude Code SDK (`AgentInvoker`). The tool sends a prompt, waits for completion, returns structured output.

**Phase 2 pattern (future):** Replace SDK calls with native DeepAgents subagents. Each slash command becomes a `SubAgent` with its own tools.

**Critical constraint:** Tool interface signatures are identical across both phases. The reasoning model calls the same tools with the same signatures — only the implementation behind the tool changes.

### 3. AsyncSubAgent for Long-Running Operations (SDK 0.5.0a2)

The DeepAgents SDK 0.5.0a2 introduces `AsyncSubAgent` — remote background subagents on LangGraph servers. The template encodes a pattern for:

- **Synchronous `SubAgent`** for quick operations (Graphiti queries, context assembly, schema validation)
- **`AsyncSubAgent`** for long-running operations (AutoBuild feature builds that take 15+ turns over hours)

The orchestrator launches `AsyncSubAgent` tasks with `start_async_task`, continues working on other projects or pipeline stages, and checks back via `check_async_task`. Task state persists across context compaction.

**Exemplar source:** `deepagents/libs/deepagents/deepagents/middleware/async_subagents.py` — full `AsyncSubAgentMiddleware` with start/check/update/cancel/list tools.

### 4. Multi-Project Pipeline Management

- Project registry (YAML) with per-project configuration: provider mode, checkpoint level, Graphiti endpoint, Git remote
- Active pipeline tracking: which projects are running, at which stage
- GPU queue scheduling: cloud API calls run in parallel across projects; local GB10 inference is sequential (FIFO queue)
- NATS topic prefix isolation for multi-tenancy

### 5. NATS Integration Hooks

- Subscribe to `pipeline.{project}.orchestrator.commands` for incoming work
- Publish to `pipeline.{project}.orchestrator.progress` at each stage transition
- Publish to `agents.approval.requests` at checkpoint gates
- Subscribe to `agents.approval.responses` for human approval/rejection
- Configurable checkpoint levels: minimal (post-build only), standard (spec review + post-build), full (every stage)

### 6. Provider-Agnostic Multi-Model Execution

- Cloud mode: Gemini 3.1 Pro / Claude API for reasoning + Claude Code SDK for implementation
- Local mode: Local model for reasoning + vLLM (Qwen3-Coder-Next on GB10) for implementation
- Runtime switchability via config — zero code changes between cloud and local modes
- Uses `init_chat_model()` for provider-agnostic model resolution (pattern from `nvidia_deep_agent` example)

---

## Exemplar sources (for the Pipeline Orchestrator, which feeds this template)

The Pipeline Orchestrator exemplar combines patterns from these DeepAgents repo sources:

| Source | Repo Location | Pattern It Provides |
|--------|--------------|---------------------|
| `nvidia_deep_agent` | `deepagents/examples/nvidia_deep_agent/` | Multi-model architecture (frontier model as orchestrator, different model per subagent). `init_chat_model()` for provider resolution. `context_schema` for runtime config. Skills integration. |
| `deep_research` | `deepagents/examples/deep_research/` | Orchestrator with subagent delegation via `task` tool. Multi-step planning with reflection. Research subagent pattern. |
| `content-builder-agent` | `deepagents/examples/content-builder-agent/` | Config-driven agent (`AGENTS.md`, `skills/`, `subagents.yaml`). `load_subagents()` from YAML. |
| `deepagents-player-coach-exemplar` | `appmilla_github/deepagents-player-coach-exemplar/` | Player-Coach adversarial pattern. `coach-config.yaml` provider switching (local/API). `domains/` directory. |
| `AsyncSubAgent` middleware | `deepagents/libs/deepagents/deepagents/middleware/async_subagents.py` | Non-blocking remote subagent execution. 5 tools (start/check/update/cancel/list). Task state persistence. |

**Exemplar approach:** Same methodology used for original template:
1. Combine sources into `deepagents-orchestrator-exemplar`
2. Validate with TASK-REV (3 reviews)
3. Build pipeline-orchestrator from validated exemplar
4. Prove in production
5. Harvest this template via `/template-create` on the working orchestrator

---

## Evidence base

### Why adversarial cooperation

- **Block AI Research** (December 2025): "Adversarial Cooperation in Code Synthesis" — introduced Player-Coach pattern and demonstrated effectiveness across code synthesis tasks.
- **Anthropic Engineering** (March 2026): "Harness Design for Long-Running Application Development" — independently validated the same Generator-Evaluator architecture. Key insight: evaluator scepticism is more tractable than generator self-criticism.
- **Anthropic meta-insight**: "Every component in a harness essentially encodes an assumption that the model can't actually carry out that task itself... those assumptions go stale as the models improve." This drives the configurable intensity (full/light/solo) in the existing weighted-evaluation template.

### Why the orchestrator pattern deserves a template

- **TASK-REV-F5F5**: Manual pipeline run across 43 tasks showed 93% default acceptance rate, only 3 high-impact human decisions. An agent can drive this.
- **TASK-REV-7549**: 50-70% of dev time lost to re-learning architecture across sessions. Persistent memory (Graphiti) solves this.
- **TASK-REV-TRF12**: 84% of agentic-dataset-factory bugs were template-preventable. Better scaffolding prevents recurring failures.

---

## Key constraints from existing code

These patterns are proven and MUST be preserved in the template:

| Pattern | Source | Constraint |
|---------|--------|------------|
| `create_deep_agent()` middleware injection | TRF-003, TRF-012 | Coach MUST use `create_agent()` or manual LangGraph, NOT `create_deep_agent()` |
| Provider mapping `local` → `openai` | agents/model_factory.py | `init_chat_model` doesn't recognise `"local"` as a provider |
| `memory=["./AGENTS.md"]` | Both factories | AGENTS.md must exist at repo root |
| Qwen3 thinking mode incompatibility | vllm-graphiti.sh | Thinking models cause timeouts in structured output extraction |
| `xgrammar` for JSON schema enforcement | vllm-graphiti.sh | Required when using vLLM with structured output requirements |
| Two-model separation | Block paper + Anthropic | Orchestration model MUST differ from implementation model |
| `AsyncSubAgent` requires SDK 0.5.x | DeepAgents SDK | Pin to `deepagents>=0.5.0a2` for non-blocking subagent execution |

---

## References

### Existing Templates (already built)
- `guardkit/installer/core/templates/langchain-deepagents/` — Base template with ALL TRF-12 universal fixes
- `guardkit/installer/core/templates/langchain-deepagents-weighted-evaluation/` — Adversarial patterns (IntensityRouter, HITL, weighted Coach, sprint contracts)

### Exemplar Sources
- `appmilla_github/deepagents/examples/nvidia_deep_agent/` — Multi-model, subagent delegation, context_schema
- `appmilla_github/deepagents/examples/deep_research/` — Orchestrator with reflection
- `appmilla_github/deepagents/examples/content-builder-agent/` — Config-driven, AGENTS.md, skills, subagents.yaml
- `appmilla_github/deepagents-player-coach-exemplar/` — Player-Coach adversarial, provider switching
- `appmilla_github/deepagents/libs/deepagents/deepagents/middleware/async_subagents.py` — AsyncSubAgent middleware (SDK 0.5.0a2)

### Evidence
- `TASK-REV-TRF12-review-report.md` — Bug taxonomy: 11 runs, 31 fixes, 84% template-preventable
- `TASK-REV-F5F5-review-report.md` — Process documentation: 43 tasks, 3 human decisions, 93% defaults accepted
- `TASK-REV-7549-review-report.md` — Lessons learned: 180+ reviews, stochastic development problem
- `TASK-REV-CFE0-review-report.md` — AutoBuild validation: 100% success post-Graphiti
- `FEAT-deepagents-exemplar-build.md` — Original exemplar creation methodology (9 decisions)
- `TASK-REV-deepagents-exemplar-validation.md` — Original exemplar validation checklist

### External Research
- Block AI Research: "Adversarial Cooperation in Code Synthesis" (December 2025) — https://block.xyz/documents/adversarial-cooperation-in-code-synthesis.pdf
- Anthropic Engineering: "Harness Design for Long-Running Application Development" (March 2026) — https://www.anthropic.com/engineering/harness-design-long-running-apps
- DeepAgents SDK: https://docs.langchain.com/oss/python/deepagents/overview
- DeepAgents GitHub: https://github.com/langchain-ai/deepagents

### Related Documents
- `pipeline-orchestrator-conversation-starter.md` — For `/system-arch` + `/system-design` session
- `pipeline-orchestrator-consolidated-build-plan.md` — Full build plan (Phase 0-5)
- `pipeline-orchestrator-motivation.md` — The observation that started everything

---

*Prepared: March 2026 | Updated: March 2026*
*This template will be created in Phase 5 after the Pipeline Orchestrator is proven in production.*
*Use as context for `/template-create` command when the orchestrator is working.*
