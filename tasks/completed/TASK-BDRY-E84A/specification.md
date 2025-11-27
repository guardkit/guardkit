# TASK SPECIFICATION: Enforce JSON Schema for Agent Boundaries Generation

## Summary

Fix the `agent-content-enhancer` AI agent to reliably generate boundaries sections by implementing JSON schema enforcement. This addresses the root cause (no machine-readable schema) rather than relying on workarounds.

## Quick Reference

- **Priority**: HIGH
- **Estimated Effort**: 4-6 hours
- **Files Modified**: 3 (prompt_builder.py, agent-content-enhancer.md, parser.py)
- **Files Preserved**: 2 (enhancer.py, boundary_utils.py - defense-in-depth)
- **Expected Impact**: Reduce AI omission rate from ~30-40% to <5%

## Problem Statement

The `agent-content-enhancer` AI agent is not reliably generating boundaries sections despite detailed natural language instructions. Current workarounds prevent failures but mask the root cause.

**Root Cause**: No machine-readable JSON schema → AI treats boundaries as optional

**Solution**: Implement JSON schema enforcement making boundaries structurally required

**Strategy**: Defense-in-depth (schema enforcement + keep existing workarounds)

## Acceptance Criteria

### AC1: Add JSON Schema to Prompt Builder ✅

**File**: `installer/global/lib/agent_enhancement/prompt_builder.py`
**Lines**: 83-106

**Change**: Replace natural language "Output Format" with formal JSON schema

**Key Requirements**:
- Add `required: ["sections", "related_templates", "examples", "boundaries"]`
- Add pattern validation: `"pattern": "## Boundaries.*### ALWAYS.*### NEVER.*### ASK"`
- Add minLength: 500 (ensures substantive content)
- Include example valid response

**See**: Full specification in Plan agent output above

### AC2: Simplify Agent Instructions ✅

**File**: `installer/global/agents/agent-content-enhancer.md`
**Lines**: 64-95

**Change**: Reduce from 32 lines to ~14 lines

**Approach**:
- Remove redundant examples (schema is source of truth)
- Focus on "how to derive" boundaries from templates
- Reference schema for structural requirements
- Keep derivation strategy

### AC3: Update Parser Comment ✅

**File**: `installer/global/lib/agent_enhancement/parser.py`
**Lines**: 156-164

**Change**: Update comment to reflect schema enforcement

**Details**:
- Change from "RECOMMENDED" to "REQUIRED by JSON schema"
- Update error message to hint at schema violation
- NO functional logic changes

### AC4: Preserve Workarounds ✅

**Files**:
- `installer/global/lib/agent_enhancement/enhancer.py` (_ensure_boundaries)
- `installer/global/lib/agent_enhancement/boundary_utils.py` (generate_generic_boundaries)

**Action**: **DO NOT MODIFY** - defense-in-depth safety net

### AC5: Update Agent Documentation ✅

**File**: `installer/global/agents/agent-content-enhancer.md`
**Lines**: 248-300

**Change**: Add schema reference to output format section

## Out of Scope

**WILL NOT CHANGE**:
- `applier.py` - Boundaries placement (working)
- `boundary_utils.py` core logic - Utilities (working)
- `enhancer.py` _ensure_boundaries - Workaround (keep as safety net)
- Static boundary generation - Fallback (keep as ultimate safety net)
- Parser validation logic - Only comment update

## Verification Steps

1. **Unit Test**: Valid boundaries pass, missing boundaries fail parser
2. **Integration Test**: /agent-enhance produces boundaries
3. **Regression Test**: Workarounds still functional
4. **Metrics**: Monitor _ensure_boundaries trigger rate

## Success Metrics

- **BEFORE**: AI omits boundaries ~30-40%
- **AFTER**: AI omits boundaries <5%
- **IDEAL**: Workarounds rarely trigger but remain functional

## Use This For /task-create

```
Title: Enforce JSON Schema for Agent Boundaries Generation
Priority: high

Description:
Fix agent-content-enhancer to reliably generate boundaries by implementing JSON schema enforcement. Changes: (1) Add schema to prompt_builder.py lines 83-106, (2) Simplify agent-content-enhancer.md lines 64-95, (3) Update parser.py comment lines 156-164. Preserve enhancer.py and boundary_utils.py workarounds as defense-in-depth. Expected: Reduce AI omission from ~30-40% to <5%.
```

## Full Implementation Details

See Plan agent output above for:
- Exact before/after code snippets
- Detailed regex patterns for schema
- Regression point analysis
- Complete testing strategy
- Rollback plan
