# Template Create Review Report: TASK-REV-TC01

## Executive Summary

The `/template-create` command run on the kartlog repository **was working before the progressive disclosure changes** but now fails due to a **bug introduced in the split output implementation**. The core issue is a mismatch between the `TemplateSplitOutput` model's attribute names and how they're accessed in the orchestrator. This is a **regression** from the Phase 5.6 progressive disclosure work.

**Key Insight**: The template-create command is **AI-powered and technology-agnostic**. It observes patterns in source code and creates appropriate subagents. The review should NOT recommend "adding Svelte/JS patterns" as that defeats the entire purpose of AI-based codebase analysis.

**Overall Assessment**: The progressive disclosure infrastructure (Phase 5.6) has a critical bug that must be fixed.

---

## Review Context

| Attribute | Value |
|-----------|-------|
| **Source Repo** | https://github.com/ColinEberhardt/kartlog |
| **Tech Stack** | Svelte 5.35.5, Vite, Firebase/Firestore, OpenAI GPT-4, SMUI, AlaSQL, PWA |
| **Progressive Disclosure Phase** | Phase 5.6 (TASK-PD-005/006/007) |
| **Affected Code** | `template_create_orchestrator.py`, `models.py` |

---

## Critical Bug: TemplateSplitOutput Attribute Mismatch

### Root Cause

The `TemplateSplitOutput` model ([models.py:356-379](installer/global/lib/template_generator/models.py#L356-L379)) defines:
```python
class TemplateSplitOutput(BaseModel):
    core_content: str       # ← Correct name
    patterns_content: str   # ← Correct name
    reference_content: str  # ← Correct name
```

But the orchestrator ([template_create_orchestrator.py:1556-1568](installer/global/commands/lib/template_create_orchestrator.py#L1556-L1568)) accesses:
```python
split_output.core        # ← AttributeError
split_output.patterns    # ← AttributeError
split_output.reference   # ← AttributeError
```

### Impact

- **CLAUDE.md generation completely fails**
- **Template is incomplete** without the core documentation file
- **Progressive disclosure does not work** as intended

### Fix Required

Change in `_write_claude_md_split()` method:
```python
# Line 1556
split_output.core → split_output.core_content

# Line 1562
split_output.patterns → split_output.patterns_content

# Line 1568
split_output.reference → split_output.reference_content
```

---

## Corrected Analysis of Template-Create Output

### Understanding the Core Philosophy

**Template-create is AI-powered**: It analyzes ANY codebase and learns its patterns. It does NOT have hardcoded technology patterns. This is the correct design.

The generated output shows the system **correctly identified**:
- Svelte 5 components with runes
- Firebase/Firestore CRUD patterns
- OpenAI function calling patterns
- SMUI component usage
- AlaSQL in-memory database patterns
- PWA configuration
- Complex form validation

**The 7 agents created are appropriate for this codebase.**

### What the AI Correctly Detected

| Detected Pattern | Source Evidence | Agent Created |
|------------------|-----------------|---------------|
| Svelte 5 runes (`$state`, `$derived`) | Component files | svelte5-component-specialist |
| Firestore CRUD with security rules | sessions.js, firestore.rules | firebase-firestore-crud-specialist |
| OpenAI function calling | chat.js with 5 custom functions | openai-function-calling-specialist |
| SMUI components | DataTable, Card, Button imports | smui-material-ui-specialist |
| AlaSQL database | query.js with SQL operations | alasql-in-memory-database-specialist |
| PWA with Workbox | vite.config.js, manifest | pwa-vite-specialist |
| Multi-section forms | Session forms with 6 sections | complex-form-validation-specialist |

**This is exactly what template-create should do**: observe patterns and create specialized agents.

### Agent Quality Assessment (Revised)

The agents are **stub agents** as expected at this stage. They:
- ✅ Have correct frontmatter with name, description, technologies
- ✅ Accurately reflect the patterns found in kartlog
- ✅ Are ready for enhancement via `/agent-enhance`

**Missing items are expected** - boundary sections, code examples, and best practices are added during the **enhancement phase**, not initial creation.

### Template Quality Assessment (Revised)

The templates correctly extracted:
- Full source files as templates
- Testing files (run_chat.js)
- Infrastructure files (databaseListeners.js)

The "80% fallback classification" is **not a bug** - it reflects that:
1. The kartlog codebase doesn't follow a traditional layered architecture
2. Most files are utility/library files without clear layer assignment
3. The system correctly placed them in `other/` when no pattern matched

**This is correct behavior** - the AI shouldn't force files into layers they don't belong to.

---

## Progressive Disclosure Status

### Phase 5.6 Work Status

| Task | Expected Output | Actual Status |
|------|-----------------|---------------|
| TASK-PD-005 | `TemplateSplitOutput` model | ✅ Model created correctly |
| TASK-PD-006 | Orchestrator uses split output | ❌ Attribute name mismatch |
| TASK-PD-007 | Split metadata generation | ✅ `generate_metadata()` works |

### The Disconnect

The model was created with `core_content`, `patterns_content`, `reference_content`, but when TASK-PD-006 integrated this into the orchestrator, the wrong attribute names were used (`.core`, `.patterns`, `.reference`).

This suggests either:
1. The integration was done without testing the full flow
2. The attribute names were changed in the model but not updated in the orchestrator
3. Code review missed this mismatch

---

## Recommendations

### Immediate (P0 - Blocking)

1. **Fix attribute name mismatch** in `template_create_orchestrator.py:1556-1568`
   - This is a simple 3-line fix
   - Should restore template-create functionality
   - **Create**: TASK-FIX-PD-001

### Validation Required

2. **Re-run template-create on kartlog** after fix to verify:
   - CLAUDE.md generates correctly
   - Split files are created in `docs/patterns/` and `docs/reference/`
   - Progressive disclosure reduction achieved (target: ≥55%)

### DO NOT Implement

The original review incorrectly recommended:
- ~~Add Svelte/JS layer classification patterns~~ - **Wrong**: Template-create is AI-powered
- ~~Generate boundary sections during creation~~ - **Wrong**: Done during `/agent-enhance`
- ~~Fix template naming (.j.template)~~ - **Minor**: Not blocking

---

## Decision Checkpoint

Based on this revised review:

| Option | Description |
|--------|-------------|
| **[I]mplement** | Create TASK-FIX-PD-001 to fix the 3-line attribute mismatch |

**Recommended**: **[I]mplement** - This is a simple regression fix that will restore template-create functionality.

---

## Appendix: Correct Understanding of Template-Create

### What Template-Create Does

1. **Analyzes source code** using AI (or heuristic fallback)
2. **Identifies patterns** specific to the codebase
3. **Creates specialized agents** based on observed patterns
4. **Generates CLAUDE.md** with project-specific guidance
5. **Produces templates** from actual source files

### What It Does NOT Do

- ❌ Use hardcoded technology patterns
- ❌ Require manual layer configuration
- ❌ Generate complete agents (that's `/agent-enhance`)
- ❌ Force files into layers they don't match

### Progressive Disclosure Goal

The goal is to reduce context window usage by 55-60% by:
- Splitting CLAUDE.md into core + docs/patterns/ + docs/reference/
- Splitting agents into core + -ext.md files
- Loading extended content only when needed

**The kartlog test demonstrates this is the right approach** - it just has a bug in the implementation.

---

*Review revised: 2025-12-07T11:00:00Z*
*Reviewer: Claude Opus 4.5 (with corrected understanding)*
