# Implementation Guide: Improve Low-Confidence Templates and Installer Display

## Feature: FEAT-ILCT
## Parent Review: TASK-REV-81AA

## Execution Strategy

### Wave 1: Template Metadata and Content (Parallel)

Four independent tasks that can run in parallel:

| Task | Title | Complexity | Method |
|------|-------|-----------|--------|
| TASK-ILCT-001 | Enrich nats-asyncio-service manifest and settings | 3 | task-work |
| TASK-ILCT-002 | Enrich langchain-deepagents-orchestrator manifest and settings | 3 | task-work |
| TASK-ILCT-003 | Populate nats-asyncio-service pattern rule files | 4 | task-work |
| TASK-ILCT-004 | Add mcp-typescript confidence_score to manifest | 1 | direct |

**TASK-ILCT-001** and **TASK-ILCT-002** are parallel manifest/settings enrichment — same type of work on different templates.

**TASK-ILCT-003** is the most involved: 10 pattern rule files need real code examples extracted from the nats-asyncio-service-exemplar agent -ext files.

**TASK-ILCT-004** is trivial: add one field to mcp-typescript/manifest.json.

### Wave 2: Installer and Settings Polish (Parallel)

| Task | Title | Complexity | Method |
|------|-------|-----------|--------|
| TASK-ILCT-005 | Standardise installer template display | 3 | task-work |
| TASK-ILCT-006 | Extend settings.json code_style for both templates | 2 | direct |

**TASK-ILCT-005** modifies install.sh: filter `common`, add scores to fastmcp-python and mcp-typescript lines, add `(confidence: X/10)` format, add score label, add source comment.

**TASK-ILCT-006** adds missing code_style fields (quote_style, async_preferred, type_hints, docstrings, linter, formatter) to both templates' settings.json.

### Wave 3: Verification (Sequential)

| Task | Title | Complexity | Method |
|------|-------|-----------|--------|
| TASK-ILCT-007 | Verify confidence scores improved | 2 | direct |

Re-run template analysis on both templates and verify scores are 80+.

## Dependency Graph

```
TASK-ILCT-001 (Wave 1) ──┐
TASK-ILCT-002 (Wave 1) ──┤
TASK-ILCT-003 (Wave 1) ──┼──> TASK-ILCT-005 (Wave 2) ──┐
TASK-ILCT-004 (Wave 1) ──┘    TASK-ILCT-006 (Wave 2) ──┼──> TASK-ILCT-007 (Wave 3)
                               (independent)           ──┘
```

## Key Risks

1. **Pattern file population quality** — Extracting examples from agent -ext files requires understanding the exemplar codebase. If the -ext files lack concrete code, examples may need to be written from scratch.
2. **Confidence scoring algorithm** — The exact formula is opaque. Adding quality_scores and flags should help but the magnitude of improvement is estimated.
3. **install.sh common filtering** — Need to ensure `common` template isn't accidentally excluded from internal use (it's used by the installer itself for shared files).

## Quick Start

```bash
# Wave 1 (parallel — use Conductor for maximum speed)
/task-work TASK-ILCT-001
/task-work TASK-ILCT-002
/task-work TASK-ILCT-003
# TASK-ILCT-004 is direct (manual edit)

# Wave 2 (after Wave 1 complete)
/task-work TASK-ILCT-005
# TASK-ILCT-006 is direct

# Wave 3 (after Wave 2 complete)
# TASK-ILCT-007 is direct verification
```
