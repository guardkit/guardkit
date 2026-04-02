# Review Report: TASK-REV-TI25

## Executive Summary

**Goal**: Register the `langchain-deepagents-orchestrator` template (created from the `deepagents-orchestrator-exemplar` repo via `/template-create`) as a builtin template in the GuardKit installer, so that `guardkit init langchain-deepagents-orchestrator` works out of the box.

The template at `~/.agentecflow/templates/langchain-deepagents-orchestrator/` is a solid foundation (44 files, 7 specialist agents, 8 patterns) for the Pipeline Orchestrator pattern. It requires **essential manifest cleanup before registration** — the `/template-create` output has generic metadata (display_name: "Python Standard Structure"), hardcoded paths, and author defaults that need updating. Missing configuration templates (langgraph.json, config YAML, domain directory) are desirable but deferrable.

**Overall Assessment: 62/100** — Template content is good; metadata and registration points need updating.

**Recommendation: Register as standalone template (no `extends`)** with essential manifest fixes applied first. Display name: "LangChain DeepAgents Orchestrator".

## Review Details

- **Mode**: Architectural Review
- **Depth**: Standard
- **Focus**: All aspects
- **Trade-off Priority**: Balanced
- **Complexity**: 5/10

---

## Findings

### Area 1: Template Installation (Manifest Quality)

| # | Finding | Severity | Evidence |
|---|---------|----------|----------|
| F1 | `display_name` is generic "Python Standard Structure" | HIGH | `manifest.json` — should be "LangChain DeepAgents Orchestrator" |
| F2 | `description` is generic "Python template using Standard Structure architecture" | HIGH | Doesn't mention DeepAgents, orchestrator, or two-model architecture |
| F3 | `source_project` contains hardcoded absolute path | HIGH | `/Users/richardwoollcott/Projects/appmilla_github/deepagents-orchestrator-exemplar` |
| F4 | `Author` placeholder default is "Richard Woollcott" | MEDIUM | Should be `null` for a builtin template |
| F5 | `frameworks` only lists pytest | MEDIUM | Base template lists DeepAgents, LangChain, LangChain-Core, LangGraph, LangChain-Community |
| F6 | `tags` are generic Standard Structure tags | LOW | Missing: deepagents, langchain, langgraph, orchestrator, pipeline, two-model |
| F7 | `category` is "general" | LOW | Should be "agent" to match the langchain-deepagents family |
| F8 | `requires` references "python-domain-specialist" | LOW | This agent doesn't exist in GuardKit — should reference actual template agents |

### Area 2: Missing Configuration Templates

| # | Finding | Severity | Evidence |
|---|---------|----------|----------|
| F9 | No `langgraph.json.template` | MEDIUM | Base template provides this; `agent.py.template` expects it |
| F10 | No `orchestrator-config.yaml` template | MEDIUM | `agent.py.template` loads this via `yaml.safe_load` with fallback |
| F11 | No domain directory template | MEDIUM | Code references `domains/{domain}/DOMAIN.md`; base has `example-domain/DOMAIN.md.template` |
| F12 | No `.env.example.template` | LOW | Base template provides this for model configuration |

### Area 3: Code Quality Issues

| # | Finding | Severity | Evidence |
|---|---------|----------|----------|
| F13 | `CompiledStateGraph` import path unresolved | HIGH | `agents.py.template` line 21: `from {{ProjectName}}.graph.state import CompiledStateGraph` — no module provided |
| F14 | `.claude/CLAUDE.md` says "using None" | MEDIUM | Generic auto-generated content, not orchestrator-specific |
| F15 | Pattern rules are generic Standard Structure | LOW | `.claude/rules/patterns/` has builder.md, factory.md etc. — not DeepAgents-specific |

### Area 4: Installer Registration

| # | Finding | Severity | Evidence |
|---|---------|----------|----------|
| F16 | Help text in `init.py` is hardcoded | INFO | Line 1631 — must be manually updated to include new template |
| F17 | Template discovery is directory-based | INFO | Placing template in `installer/core/templates/` is sufficient for runtime discovery |
| F18 | No existing `fastmcp-python` or `mcp-typescript` in help text either | INFO | These templates exist on disk but aren't in the help string — precedent for gap |

### Area 5: Documentation

| # | Finding | Severity | Evidence |
|---|---------|----------|----------|
| F19 | Root `CLAUDE.md` lists 7 templates — needs 8th | LOW | Line 223 |
| F20 | `docs/templates.md` doesn't include this template | LOW | Lists 7 templates |
| F21 | Dark Factory README already references pending registration | INFO | Correct and up to date |

---

## Architectural Strengths

1. **Progressive Disclosure**: Core + extended (-ext.md) agent documentation — excellent pattern, consistent with base template
2. **Defensive Error Handling**: All @tool functions wrap in try/except with logger.exception fallback
3. **Domain-Agnostic Prompts**: {date} and {domain_prompt} runtime injection pattern
4. **Two-Phase Prompt Construction**: Handles JSON braces in evaluator prompt elegantly
5. **Safe Argument Parsing**: `parse_known_args()` instead of `parse_args()` for LangGraph server compatibility
6. **Configuration Fallbacks**: Graceful defaults when config/domain files missing
7. **Agent Quality**: 7 specialist agents at 85% confidence with clear ALWAYS/NEVER/ASK boundaries

---

## Decision Point Analysis

### D1: Should this template `extend` langchain-deepagents?

| Factor | Extend | Standalone |
|--------|--------|------------|
| Agent overlap | 0/7 agents shared — completely different specialist sets | No inheritance needed |
| Architecture | Orchestrator pattern ≠ Adversarial Player-Coach | Architecturally distinct |
| Rules overlap | code-style.md and testing.md are similar | Can maintain independently |
| Template files | Different (orchestrator vs player/coach) | No reuse opportunity |
| lib/ modules | Base has 9 runtime libs (factory_guards, etc.) | Orchestrator doesn't use them |
| Precedent | weighted-evaluation extends base (same architecture) | This is a different architecture |

**Recommendation: Standalone** — The orchestrator pattern is architecturally distinct from the adversarial Player-Coach pattern. Extending would inherit agents, rules, and lib/ modules that don't apply. If shared patterns emerge later, extract to `common/`.

### D2: How much manifest cleanup before registration?

**Recommendation: Essential fixes before, polish after.**

**MUST FIX before registration (blocking):**
- F1: `display_name` → "LangChain DeepAgents Orchestrator"
- F2: `description` → pipeline-orchestrator-specific
- F3: Remove or relativize `source_project`
- F4: `Author` default → `null`
- F5: Add DeepAgents/LangChain/LangGraph to `frameworks`
- F13: Fix CompiledStateGraph import (use `from langgraph.graph import CompiledStateGraph` or `TYPE_CHECKING`)

**CAN DEFER to follow-up task:**
- F6/F7/F8: Tags, category, requires cleanup
- F9-F12: Add missing config templates
- F14-F15: Improve CLAUDE.md and pattern files
- Agent enhancement via `/agent-enhance --hybrid`

### D3: Agent enhancement before or after registration?

**Recommendation: After** — Agents are already at 85% confidence with good ALWAYS/NEVER/ASK structure. Enhancement is a polish task, not a blocker.

---

## Recommendations

| # | Recommendation | Priority | Effort |
|---|---------------|----------|--------|
| R1 | Fix manifest.json metadata (F1-F5) | **Critical** | 15 min |
| R2 | Fix CompiledStateGraph import (F13) | **Critical** | 10 min |
| R3 | Copy template to `installer/core/templates/` | **High** | 5 min |
| R4 | Update `init.py` help text (F16) | **High** | 5 min |
| R5 | Update CLAUDE.md and docs/templates.md (F19-F20) | **Medium** | 10 min |
| R6 | Add langgraph.json + config templates (F9-F11) | **Medium** | 30 min |
| R7 | Update .claude/CLAUDE.md content (F14) | **Low** | 10 min |
| R8 | Enhance agents with `/agent-enhance --hybrid` | **Low** | Separate task |
| R9 | Add DeepAgents-specific pattern rules (F15) | **Low** | Separate task |

**Total effort for registration (R1-R5): ~45 minutes**
**Total effort including polish (R1-R7): ~1.5 hours**

---

## Appendix: File Inventory

| Category | Count | Notes |
|----------|-------|-------|
| Agent specialists (.md) | 14 | 7 core + 7 extended |
| Pattern rules (.md) | 8 | Generic Standard Structure |
| Code templates (.py.template) | 8 | Agents, tools, prompts, init |
| Configuration templates | 0 | **MISSING** — langgraph.json, config YAML |
| Rules/guidance files | 11 | code-style, testing, 7 guidance |
| **Total files** | **44** | |

### Comparison with Existing Templates

| Metric | Base (langchain-deepagents) | Weighted-Eval | Orchestrator |
|--------|---------------------------|---------------|-------------|
| Confidence | 96.67% | 95.0% | 68.33% |
| Agents | 7 | 0 (inherits) | 7 |
| Extends | — | langchain-deepagents | **Standalone** |
| Config templates | Yes | Yes (Jinja2) | **Missing** |
| Runtime lib/ | 9 modules | Inherits | None |
| Complexity | 10 | 10 | 7 |
