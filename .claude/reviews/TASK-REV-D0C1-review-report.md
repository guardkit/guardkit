# Review Report: TASK-REV-D0C1

**Title**: Register dotnet-railway-fastendpoints as builtin template
**Mode**: Architectural review (registration readiness)
**Depth**: Standard
**Completed**: 2026-04-11

## Executive Summary

The `dotnet-railway-fastendpoints` template at `~/.agentecflow/templates/dotnet-railway-fastendpoints/` is **structurally ready** for builtin registration with **four blocking issues** to fix before copy, and **three minor polish items** that can be deferred.

- **Readiness score**: 82/100
- **Decision**: **REFACTOR THEN REGISTER** — fix blockers, copy, update 2 registration points, defer agent enhancement as follow-up
- **Registration is simpler than the task description implies**: the CLI auto-discovers templates from `installer/core/templates/`, so only 2 hardcoded lists must be updated (not 4+).

### Critical Findings

| # | Finding | Severity | File |
|---|---------|----------|------|
| 1 | Manifest `requires: agent:dotnet-domain-specialist` references an agent that doesn't exist in GuardKit | **BLOCKER** | [manifest.json](../../../../.agentecflow/templates/dotnet-railway-fastendpoints/manifest.json) |
| 2 | `settings.json` layer_mappings hardcode "Exemplar" in directory paths (e.g. `src/Exemplar.Customers/Domain`) | **BLOCKER** | [settings.json](../../../../.agentecflow/templates/dotnet-railway-fastendpoints/settings.json) |
| 3 | Manifest `author: "Richard Woollcott"` should be `null` to match conventions | **BLOCKER** | [manifest.json](../../../../.agentecflow/templates/dotnet-railway-fastendpoints/manifest.json) |
| 4 | `CreateCustomer.cs.template` hardcodes role `"admin"`; should use placeholder | **MINOR** | `templates/Endpoints/CreateCustomer.cs.template` |
| 5 | No root `README.md` (other builtins have one) | **MINOR** | — |
| 6 | `source_project` field leaks absolute path `/Users/richardwoollcott/.../dotnet-functional-fastendpoints-exemplar` | **MINOR** | [manifest.json](../../../../.agentecflow/templates/dotnet-railway-fastendpoints/manifest.json) |
| 7 | Complexity rated 10/10 — consider splitting (task Decision Point 4) | **DISCUSSION** | — |

## Review Details

- **Agents used**: architectural-reviewer (self), Explore subagent (2x)
- **Clarification**: Skipped (complexity 0, explicit scope in task)
- **Knowledge graph context**: Not loaded (out of scope for standalone template registration)

---

## Findings

### 1. Template Structure: Conforms to Convention ✅

The template layout matches existing builtins (`python-library`, `langchain-deepagents`) exactly:

```
dotnet-railway-fastendpoints/
├── .claude/
│   ├── CLAUDE.md              # 1.4 KB — template overview
│   └── rules/                 # 22 files with path frontmatter
│       ├── code-style.md      # paths: **/*.cs ✅
│       ├── testing.md         # paths: **/*Test.*, **/*Spec.* ✅
│       ├── patterns/          # 13 pattern rules
│       └── guidance/          # 7 agent quick-references
├── agents/                    # 14 files (7 base + 7 -ext)
├── templates/                 # 20 scaffold templates across 8 layers
├── manifest.json              # 5.2 KB
└── settings.json              # 3.4 KB
```

**Verified**: Path frontmatter exists on rule files (contradicting my initial exploration — I verified directly with `head`):
- `code-style.md`: `paths: **/*.cs`
- `testing.md`: `paths: **/*.test.*, **/tests/**, **/*_test.*, **/*Test.*, **/*Spec.*`

This matches the [python-library convention](../../installer/core/templates/python-library/.claude/rules/code-style.md).

### 2. Manifest Metadata: 3 Issues

**From [manifest.json](../../../../.agentecflow/templates/dotnet-railway-fastendpoints/manifest.json):**

```json
{
  "name": "dotnet-railway-fastendpoints",
  "display_name": "C# Modular Monolith With Bounded Context Isolation",
  "author": "Richard Woollcott",                        // ⚠️ should be null
  "language": "C#",
  "language_version": "net10.0",
  "complexity": 10,
  "confidence_score": 94.67,
  "requires": ["agent:dotnet-domain-specialist"],       // ⚠️ phantom dep
  "source_project": "/Users/richardwoollcott/..."       // ⚠️ author-local path
}
```

- **Issue 2a (BLOCKER)**: `requires: agent:dotnet-domain-specialist` — this agent does **not** exist in `installer/core/agents/`. The only references I found are:
  - `installer/core/commands/task-work.md` (as a hypothetical example)
  - `installer/core/lib/template_creation/manifest_generator.py` (as a generator sample)
  - No actual agent file. Publishing a builtin with a phantom `requires` entry will fail any downstream dependency resolution. **Either add the agent or remove the requires entry.** The 7 template-scoped agents cover the domain modeling concerns anyway.

- **Issue 2b (BLOCKER)**: `author: "Richard Woollcott"` — existing builtins use `author: null` (verified in [python-library manifest.json:7](../../installer/core/templates/python-library/manifest.json#L7)).

- **Issue 2c (MINOR)**: `source_project` field contains an absolute user-local path. Either remove the field entirely or scrub the path. It has no functional purpose in a builtin.

- **Issue 2d (INFO)**: `display_name` is verbose ("C# Modular Monolith With Bounded Context Isolation") — compare with python-library's ("Python Library"). Consider shortening to `"C# Railway-Oriented Monolith"` or similar.

- **Issue 2e (INFO)**: `placeholders` are well-defined — `ProjectName` (required), `Namespace` (required), `Author` (optional). Placeholder structure conforms to convention.

### 3. settings.json: Hardcoded "Exemplar" in Layer Paths (BLOCKER)

The `layer_mappings` section references the source exemplar project name in directory paths:

```json
"layer_mappings": {
  "Customers.Domain": { "directory": "src/Exemplar.Customers/Domain", ... }
}
```

Namespaces correctly use `{{ProjectName}}` but directories are frozen as `Exemplar.*`. When scaffolded, every layer will be placed in `src/Exemplar.*/` regardless of the user's ProjectName. **Fix**: replace `Exemplar` with `{{ProjectName}}` in all 7 layer directory paths.

### 4. Scaffold Templates: Mostly Clean ✅ with 1 Minor Issue

Spot-checked 5 of 20 scaffolds:
- **Program.cs.template**: Parametric connection strings via `builder.Configuration.GetConnectionString(...)`. Keycloak authority from config. ✅
- **CustomerRepository.cs.template**: Connection string injected via constructor. No hardcoded DB credentials. ✅
- **FleetDiscoveryService.cs.template**: `INatsConnection` injected via DI; subjects are generic (`fleet.register`, `fleet.heartbeat.>`). No cluster names. ✅
- **ExemplarApiFactory.cs.template**: Accepts `connectionString, keycloakAuthority` as constructor parameters — Testcontainers can supply values at runtime. ✅
- **CreateCustomer.cs.template**: ⚠️ Hardcodes role string `"admin"` with a `// {{TEMPLATE: PolicyNames}}` comment. The comment acknowledges it needs attention but the value wasn't replaced with a placeholder. **Fix**: replace with `{{DefaultRole}}` placeholder or document in CLAUDE.md that users must edit this.

**Verdict on task review scope item "Confirm NATS fleet integration and Keycloak auth/observability patterns are generic"**: ✅ confirmed — no hardcoded cluster/realm/URL anywhere.

### 5. Agent Definitions: Already Enhanced ✅

All 7 agents use the standard base + `-ext.md` progressive disclosure pattern (same as `langchain-deepagents`). **`/agent-enhance` has already been run** on all 7 agents — confirmed by:
- All 7 have substantial `-ext.md` extended files (121-177 lines each; 1,799 lines total across 14 files)
- Extended files contain the post-enhancement structure: "Related Templates", "Code Examples" with multiple numbered examples, template file cross-references, and inline code blocks
- Spot-checked `railway-result-pipeline-specialist-ext.md`: contains explicit references to `templates/cross-cutting core/functional/ResultExtensions.cs.template` and canonical `BindAsync` combinator examples — clearly the output of a hybrid enhancement pass that inspected the scaffold files

Frontmatter includes `capabilities`, `description`, `keywords`, `phase`, `stack`, `technologies`. No hardcoded paths or credentials.

**Recommendation**: No further agent work needed. The agents are registration-ready as-is.

### 6. Registration Points: Simpler Than Expected

The task description lists many registration points, but the reality (verified via Explore) is:

| Location | Action | Why |
|----------|--------|-----|
| [CLAUDE.md:223](../../CLAUDE.md#L223) | **EDIT** — add to pipe list | Hardcoded templates line |
| [guardkit/cli/init.py:1719](../../guardkit/cli/init.py#L1719) | **EDIT** — add to docstring | Hardcoded help text |
| `guardkit/cli/init.py` template discovery | **NO CHANGE** | Auto-discovers from filesystem (verified: [init.py:462-510](../../guardkit/cli/init.py#L462)) |
| `guardkit/knowledge/seed_templates.py` | **NO CHANGE** | Auto-discovers via `_discover_templates()` ([seed_templates.py:40](../../guardkit/knowledge/seed_templates.py#L40)) |
| [installer/scripts/install.sh:557](../../installer/scripts/install.sh#L557) | **OPTIONAL** — legacy installer | Already stale (missing 5 existing templates) |
| [installer/scripts/install.sh:834](../../installer/scripts/install.sh#L834) | **OPTIONAL** — legacy stack-agents mkdir | Already stale |
| [installer/scripts/install.sh:865-870](../../installer/scripts/install.sh#L865) | **OPTIONAL** — legacy help text | Already stale |
| [tests/knowledge/test_seed_enrichment.py:36-44](../../tests/knowledge/test_seed_enrichment.py#L36) | **NO CHANGE** (separate concern) | `EXPECTED_TEMPLATES` set already excludes python-library, nats-asyncio-service, and all langchain variants. Test is stale; fixing it is out of scope for this task. |
| [README.md](../../README.md) | **OPTIONAL** — comparison table | Only shows 5 templates as examples, not comprehensive |

**Net minimum**: 2 files to edit. Everything else is either auto-discovered or out of scope.

### 7. Task Decision Points — Recommendations

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | Template inheritance | **Standalone** | No existing .NET base to extend. Matches task's own hypothesis. |
| 2 | Manifest polish | **Fix 3 blockers now; defer minor polish** | Blockers (phantom `requires`, author, Exemplar paths) affect functional correctness. Verbose display_name can wait. |
| 3 | Agent enhancement | **Already completed — no action needed** | All 7 agents have enhanced `-ext.md` files (verified: 121-177 lines each with code examples and template references). `/agent-enhance` was run before the review. |
| 4 | Complexity 10/10 — split? | **Keep as single template** | Splitting adds maintenance overhead; users who want a subset can delete layers. A `dotnet-minimal` variant can be added later from a stripped project. |
| 5 | Fleet/NATS/Keycloak coupling | **Keep as-is (optional layers)** | Spot-check confirmed these are DI-wired, not hardcoded. Users can omit Fleet/NATS by removing `.AddFleetIntegration()` from Program.cs. Document this in CLAUDE.md. |

---

## Recommendations (Prioritized)

### Wave 1 — Prerequisites (must finish before copy)

1. **Strip phantom `requires: agent:dotnet-domain-specialist`** from `manifest.json` at the source location.
2. **Replace `"Exemplar"` with `"{{ProjectName}}"`** in all `layer_mappings` directory paths in `settings.json`.
3. **Set `author` to `null`** in `manifest.json`.
4. **Remove or scrub `source_project`** field from `manifest.json`.
5. **Parameterize `"admin"` role** in `CreateCustomer.cs.template` (or add a `CLAUDE.md` note).

### Wave 2 — Copy and Register (after Wave 1 lands)

6. **Copy** `~/.agentecflow/templates/dotnet-railway-fastendpoints/` → `installer/core/templates/dotnet-railway-fastendpoints/`.
7. **Edit [CLAUDE.md:223](../../CLAUDE.md#L223)** to append `dotnet-railway-fastendpoints` to the template pipe list.
8. **Edit [guardkit/cli/init.py:1719](../../guardkit/cli/init.py#L1719)** to append `dotnet-railway-fastendpoints` to the docstring help text.
9. **Add a root `README.md`** to the copied template with a quick-start (~30 lines).

### Wave 3 — Verify (after Wave 2 lands)

10. **Run `/template-validate installer/core/templates/dotnet-railway-fastendpoints`** and address findings.
11. **Smoke test**: `cd /tmp/test && guardkit init dotnet-railway-fastendpoints` → verify scaffold works and no `Exemplar.` paths leak.
12. **Verify `guardkit init --help`** lists the new template.

### Wave 4 — Follow-ups (separate tasks, not blocking registration)

13. Consider whether `tests/knowledge/test_seed_enrichment.py` `EXPECTED_TEMPLATES` should be fixed comprehensively (currently stale for 5+ templates).
14. Evaluate a `dotnet-minimal` variant if complexity 10/10 proves a barrier for new users.

---

## Decision Matrix

| Option | Effort | Risk | Recommendation |
|--------|--------|------|----------------|
| **A. Register as-is (no fixes)** | Low | High — phantom `requires` may break, Exemplar paths ship broken scaffold | ❌ |
| **B. Fix blockers → register (this plan)** | Medium (~1h manifest + 1h registration + 30m verify) | Low | ✅ **Recommended** |
| **C. Full polish → register** | High (~half-day incl. agent enhancement) | Very low | Overkill; defer agent enhancement to Wave 4 |
| **D. Split into minimal + full templates first** | Very High | Medium — design work needed | ❌ Not needed for initial registration |

## Appendix

### Files Referenced

- Task file: [tasks/in_progress/TASK-REV-D0C1-...](../../tasks/in_progress/TASK-REV-D0C1-register-dotnet-railway-fastendpoints-template.md)
- Source template: `~/.agentecflow/templates/dotnet-railway-fastendpoints/`
- Reference templates: [python-library](../../installer/core/templates/python-library/), [langchain-deepagents](../../installer/core/templates/langchain-deepagents/)
- CLI init: [guardkit/cli/init.py](../../guardkit/cli/init.py)
- Install script: [installer/scripts/install.sh](../../installer/scripts/install.sh)
- Root docs: [CLAUDE.md](../../CLAUDE.md)

### Corrections to Initial Exploration

- My first Explore pass reported that rule files likely lacked path frontmatter. **I verified this was wrong** — `code-style.md` and `testing.md` both have correct frontmatter. Report updated.
- Initial exploration flagged `requires: agent:dotnet-domain-specialist` as "unusual"; targeted grep confirmed the agent does not exist anywhere in `installer/core/`. Upgraded to BLOCKER.
- **Initial review implied `/agent-enhance` had not been run and should be a follow-up.** This was wrong — user confirmed, and verification of `-ext.md` file contents (1,799 lines total, with numbered code examples and template cross-references) shows all 7 agents have already been hybrid-enhanced. Section 5 and Decision Point 3 updated. Wave 4 follow-up list de-scoped.
