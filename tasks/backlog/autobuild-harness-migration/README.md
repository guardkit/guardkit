# Feature: AutoBuild Harness Migration (Claude SDK → LangGraph/DeepAgents)

> **Feature ID**: FEAT-HMIG
> **Parent review**: [TASK-REV-HMIG](../../review_complete/TASK-REV-HMIG-prepare-autobuild-harness-migration-claude-sdk-to-langgraph.md)
> **Review report**: [`.claude/reviews/TASK-REV-HMIG-review-report.md`](../../../.claude/reviews/TASK-REV-HMIG-review-report.md) (with Revision 1 + Revision 2 in §14)
> **Deadline**: 2026-06-15 (Anthropic enforces API-key validation)
> **Cutover target**: 2026-06-10 (5-day validation margin)
> **Repos involved**: this repo (`guardkit`) + sibling repo (`guardkitfactory`)

## Problem statement

On **2026-06-15**, Anthropic enforces API-key validation on its endpoints. The
`ANTHROPIC_BASE_URL` redirect pattern AutoBuild relies on to route inference at local
vLLM (gb10:9000) breaks. AutoBuild stops working on local models, in direct violation of
DECISION-DF-001 (no cloud API on critical path).

The cross-repo evidence is strong: fleet agents on LangGraph/DeepAgents
(forge/jarvis/study-tutor/specialist-agent) show ~80-90% first-pass-success;
SDK-based GuardKit AutoBuild shows ~60-70% with ~30% non-recoverable failures
(per [TASK-REV-HMIG review §5.10](../../../.claude/reviews/TASK-REV-HMIG-review-report.md#510-comparative-analysis-cross-repo-failure-rate-asymmetry)).
The migration is both forced (deadline) and earned (failure-rate evidence).

## Solution approach

Replace the Claude Agents SDK boundary with a `HarnessAdapter` interface that has
two implementations:

- `ClaudeSDKHarness` (legacy, in `guardkit`, deprecated 2026-06-15)
- `LangGraphHarness` (new, in **`guardkitfactory`**, the new sibling repo)

`guardkit/orchestrator/agent_invoker.py` dispatches through the interface
based on `GUARDKIT_HARNESS=sdk|langgraph` env var. Cutover (D-7 = 2026-06-08)
flips the default; SDK path retained as a revert fallback through 2026-06-15.

The `LangGraphHarness` lives in a separate repo (`guardkitfactory`) initialised
from the `langchain-deepagents` template (per Revision 2 / D-01). DeepAgents'
built-in `ls / read_file / write_file / edit_file / glob / grep / execute` tools
are used directly via `LocalShellBackend` + `FilesystemPermission` (per Revision 1 / D-03).

## Cross-repo coordination

This feature folder is the **migration's home base** in `guardkit`. A mirror
feature folder lives at `guardkitfactory/tasks/backlog/autobuild-harness-migration/`
with the tasks that touch source code in that repo. Each task file declares the
cross-repo work in its acceptance criteria.

| In `guardkit` (this folder) | In `guardkitfactory` |
|---|---|
| TASK-HMIG-001A (HarnessAdapter ABC) | TASK-HMIG-000R (complete source scaffold) |
| TASK-HMIG-006 (agent_invoker dispatch refactor) | TASK-HMIG-001B (LangGraphHarness skeleton) |
| **TASK-HMIG-008R** (LLM Coach primary + evidence-supplier refactor — Revision 3) | TASK-HMIG-002R (LocalShellBackend + permissions) |
| TASK-HMIG-009 (canary validation) | TASK-HMIG-007 (BDD plugin interface + PytestBDDPlugin) |
| TASK-HMIG-010 (full feature autobuild) | — |

## Task summary

| ID | Title | Wave | Effort | Status |
|---|---|---|---|---|
| TASK-HMIG-001A | Define HarnessAdapter interface (guardkit-side) | 1 | 2h | backlog |
| TASK-HMIG-006 | Refactor agent_invoker._invoke_with_role to dispatch through HarnessAdapter | 2 | 10h | backlog |
| **TASK-HMIG-008R** *(Revision 3)* | **Restore LLM Coach as primary + refactor CoachValidator into CoachEvidenceBundle supplier** | **2** | **12h** | **backlog** |
| TASK-HMIG-009 | Canary validation under GUARDKIT_HARNESS=langgraph | 3 | 4h | backlog |
| TASK-HMIG-010 | Full feature autobuild end-to-end validation | 3 | 8h | backlog |

Total in `guardkit`: **5 tasks, ~36h** *(Revision 3: was ~28h; TASK-HMIG-008 expanded from 4h to 12h)*. See `guardkitfactory/tasks/backlog/autobuild-harness-migration/README.md` for the additional ~20h there.

## Next steps

1. Read [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) for wave-by-wave execution.
2. Start Wave 1: TASK-HMIG-001A (here) and TASK-HMIG-000R / TASK-HMIG-001B / TASK-HMIG-002R in `guardkitfactory` (can run in parallel as they touch different repos).
3. Wave 2 starts when Wave 1 falsifiers pass in both repos.
4. Wave 3 (canary + feature validation) gates Wave 4 cutover.

## Forward-compatibility (post-cutover phases — not in scope here)

A second-opinion review (Claude Desktop, 2026-05-19) flagged that the operator
intends to add NATS JetStream + A2A + Google ADK + AG-UI in subsequent phases.
The current migration is deliberately scoped to substrate replacement and
**does not block any of those**. The layered architecture below holds:

| Layer | Protocol / library | Migration phase | Lives where |
|---|---|---|---|
| Tool access | MCP | Already in use (Graphiti MCP, etc.) | n/a |
| **Agent orchestration** | **LangGraph + DeepAgents** | **This migration** | **`guardkitfactory`** |
| Agent coordination (cross-boundary) | A2A over NATS (internal) + HTTP (external) | Post-cutover (decision D-04 defers) | Jarvis-side bridge; harness untouched |
| Cloud-facing agents | Google ADK (where appropriate) | Post-cutover | Separate deployment; A2A bridges to local LangGraph |
| Human oversight | AG-UI (CopilotKit + LangGraph integration) | Subsequent phase | Frontend; consumes LangGraph interrupts |

Why nothing in this feature blocks the future phases:

- The `LangGraphHarness` in `guardkitfactory` is a pure execution engine. It
  knows nothing about NATS, A2A, ADK, or AG-UI. The `HarnessAdapter` interface
  in `guardkit` doesn't leak any of those concerns either.
- NATS publishing already happens at the orchestrator level in `guardkit`
  (independent of substrate). A2A wraps the agent endpoint *above* the
  harness — it doesn't require changes inside `LangGraphHarness`.
- AG-UI's human-in-the-loop events ride LangGraph's native `interrupt`
  primitive (DeepAgents exposes this via `interrupt_on` per tool). The
  current plan does not foreclose that — interrupts can be added later
  without re-architecting.
- ADK and LangGraph coexist via A2A; ADK is the right choice for *cloud*
  deployments where Google ecosystem is preferred, LangGraph is the right
  choice for the *local fleet*. Both protocols speak A2A at the boundary.

The four-layer stack ("MCP for tools, orchestration in code, A2A for
coordination, AG-UI for humans") is the implicit target architecture. This
migration delivers the orchestration layer. The other three plug in above.

## See also

- Review report: [`.claude/reviews/TASK-REV-HMIG-review-report.md`](../../../.claude/reviews/TASK-REV-HMIG-review-report.md)
- Original implementation guide: [`.claude/reviews/TASK-REV-HMIG-implementation-guide.md`](../../../.claude/reviews/TASK-REV-HMIG-implementation-guide.md)
- Sibling feature folder: `~/Projects/appmilla_github/guardkitfactory/tasks/backlog/autobuild-harness-migration/`
- Falsifier: at end of Wave 3 (D-7 = 2026-06-08), measured first-pass-success on the canary task set must be ≥75% (see review report §11)
- Future-phase context (out of scope here but referenced for trajectory):
  - `~/Projects/YouTube Channel/insights/Six Agent Protocols - MCP A2A AGUI and the Emerging Agentic Stack.md`
  - `~/Projects/YouTube Channel/transcripts/Six Agent Protocols - MCP A2A AGUI and the Emerging Agentic Stack.md`
  - LangChain Deep Agents deploy-coding-agent example: <https://github.com/langchain-ai/deepagents/tree/main/examples/deploy-coding-agent>
  - Decisions D-04 (A2A defer), D-10 (role expansion via Skills), D-11 (sandbox backend swap) in the parent review
