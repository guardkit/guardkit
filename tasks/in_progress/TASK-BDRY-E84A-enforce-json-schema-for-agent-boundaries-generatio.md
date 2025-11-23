---
id: TASK-BDRY-E84A
title: Enforce JSON Schema for Agent Boundaries Generation
status: in_review
created: 2025-11-23T22:26:53.775286
updated: 2025-11-23T23:15:00.000000
priority: high
tags: [ai-enhancement, json-schema, boundaries, quality-improvement]
complexity: 0
test_results:
  status: passed
  coverage: 86
  last_run: 2025-11-23T23:15:00.000000
---

# Task: Enforce JSON Schema for Agent Boundaries Generation

## Description

Fix agent-content-enhancer to reliably generate boundaries using JSON schema enforcement. Root cause: No machine-readable schema makes boundaries optional. Solution: Add JSON schema to prompt_builder.py (lines 83-106), simplify agent-content-enhancer.md (lines 64-95), update parser.py comment (lines 156-164). Preserve enhancer.py and boundary_utils.py workarounds as defense-in-depth. Out of scope: applier.py, boundary_utils.py core logic. Success: Reduce AI omission from ~30-40% to <5%.

See docs/tasks/TASK-BDRY-SCHEMA-spec.md for full specification.

## Acceptance Criteria

### AC1: Add JSON Schema to Prompt Builder ✅
- [ ] File: `installer/global/lib/agent_enhancement/prompt_builder.py`
- [ ] Lines: 83-106 (replace existing output format section)
- [ ] Add `required: ["sections", "related_templates", "examples", "boundaries"]`
- [ ] Add pattern validation: `"pattern": "## Boundaries.*### ALWAYS.*### NEVER.*### ASK"`
- [ ] Add minLength: 500 (ensures substantive content)
- [ ] Include example valid response

### AC2: Simplify Agent Instructions ✅
- [ ] File: `installer/global/agents/agent-content-enhancer.md`
- [ ] Lines: 64-95 (Boundary Sections section)
- [ ] Reduce from 32 lines to ~14 lines
- [ ] Remove redundant examples (schema is source of truth)
- [ ] Focus on "how to derive" boundaries from templates
- [ ] Reference schema for structural requirements

### AC3: Update Parser Validation Comment ✅
- [ ] File: `installer/global/lib/agent_enhancement/parser.py`
- [ ] Lines: 156-164
- [ ] Change from "RECOMMENDED" to "REQUIRED by JSON schema"
- [ ] Update error message to hint at schema violation
- [ ] NO functional logic changes (only comment update)

### AC4: Preserve Workarounds ✅
- [ ] DO NOT MODIFY: `installer/global/lib/agent_enhancement/enhancer.py` (_ensure_boundaries)
- [ ] DO NOT MODIFY: `installer/global/lib/agent_enhancement/boundary_utils.py` (generate_generic_boundaries)
- [ ] Verify workarounds still functional after changes
- [ ] These provide defense-in-depth safety net

### AC5: Update Agent Documentation ✅
- [ ] File: `installer/global/agents/agent-content-enhancer.md`
- [ ] Lines: 248-300 (Output Format section)
- [ ] Add schema reference to output format documentation
- [ ] Highlight that `boundaries` field is REQUIRED by schema
- [ ] Note minimum length and subsection requirements

## Out of Scope

**WILL NOT CHANGE**:
- ❌ `applier.py` - Boundaries placement logic (working correctly)
- ❌ `boundary_utils.py` core logic - Shared utilities (working correctly)
- ❌ `enhancer.py` _ensure_boundaries() - Keep as defense-in-depth
- ❌ Static boundary generation - Keep as ultimate fallback
- ❌ Parser._validate_boundaries() logic - Only comment update

## Verification Steps

1. **Unit Test**: Valid boundaries pass, missing boundaries fail parser
2. **Integration Test**: /agent-enhance produces boundaries
3. **Regression Test**: Workarounds still functional
4. **Metrics**: Monitor _ensure_boundaries trigger rate (expect <5%, down from ~30-40%)

## Success Metrics

- **BEFORE**: AI omits boundaries ~30-40% of responses
- **AFTER**: AI omits boundaries <5% (schema enforcement)
- **IDEAL**: Workarounds rarely trigger but remain functional

## Implementation Notes

- Schema is primary fix, workarounds are safety net (defense-in-depth)
- Use lenient regex patterns to avoid false rejections
- Test with minimal valid boundaries to ensure minLength correct
- Schema validation happens BEFORE _ensure_boundaries fallback
- Keep all existing workarounds functional

## Related Documentation

- Full specification: `docs/tasks/TASK-BDRY-SCHEMA-spec.md`
- Plan agent output: Detailed before/after code snippets
- Regression analysis: Potential issues and mitigations
- Testing strategy: Comprehensive verification approach
