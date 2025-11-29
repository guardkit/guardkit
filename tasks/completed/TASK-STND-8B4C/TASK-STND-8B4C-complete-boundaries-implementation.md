# TASK-STND-8B4C: Complete Boundaries Implementation in Agent Enhancement Pipeline

**Created**: 2025-11-22
**Priority**: HIGH
**Estimated Effort**: 12-16 hours
**Task Type**: implementation

## Problem Statement

TASK-STND-773D (commit 814d810) was marked as COMPLETED but only partially implemented the boundaries framework. The task updated documentation (`agent-content-enhancer.md`) but failed to update the code that generates prompts, parses responses, and applies enhancements.

### Evidence

**File**: `installer/global/lib/agent_enhancement/prompt_builder.py`

- **Line 80**: Still requests "Best practices for using this agent with these templates"
- **Line 86**: Still uses `'sections': ['related_templates', 'examples', 'best_practices']`
- **Line 89**: Still uses `'best_practices': '## Best Practices\\n\\n1. Practice 1\\n2. Practice 2\\n...'`

**Result**: When `/agent-enhance` runs, it generates agents with "Best Practices" sections instead of "Boundaries (ALWAYS/NEVER/ASK)" sections, violating GitHub best practices framework.

**Example**: Enhanced agent `maui-mvvm-viewmodel-specialist.md` (894 lines) has:
- Line 401: `## Best Practices` ❌ (should be `## Boundaries`)
- Missing explicit ALWAYS/NEVER/ASK framework

## Motivation

The boundaries framework (from `github-agent-best-practices-analysis.md` - analysis of 2,500+ repositories) provides:

1. **Clarity**: Explicit ALWAYS/NEVER/ASK rules eliminate ambiguity
2. **Safety**: Clear prohibited actions prevent mistakes
3. **Consistency**: Standardized format across all agents
4. **Escalation**: ASK framework guides human intervention

**Current State**: Boundary clarity = 0/10 (no boundaries sections)
**Target State**: Boundary clarity = 9/10 (explicit ALWAYS/NEVER/ASK framework)

## Scope

### In Scope
- Update `prompt_builder.py` to request "boundaries" instead of "best_practices"
- Update `parser.py` to validate boundaries format (ALWAYS/NEVER/ASK)
- Update `applier.py` to place boundaries correctly (after Quick Start, before Capabilities)
- Add comprehensive tests for boundaries generation, parsing, and application
- Support backward compatibility (accept both "boundaries" and "best_practices" during transition)
- Update documentation with examples

### Out of Scope
- Migrating existing enhanced agents (separate task)
- Changing agent-content-enhancer.md (already updated in TASK-STND-773D)
- Adding new boundary rules (specification already complete)

## Acceptance Criteria

### AC-1: Prompt Generation Updates
- [ ] AC-1.1: Line 80 requests "Boundaries (ALWAYS/NEVER/ASK framework)" instead of "Best practices"
- [ ] AC-1.2: Line 86 uses `'sections': ['related_templates', 'examples', 'boundaries']`
- [ ] AC-1.3: Line 89 specifies boundaries format with ALWAYS/NEVER/ASK structure
- [ ] AC-1.4: Prompt includes emoji format (✅ ALWAYS, ❌ NEVER, ⚠️ ASK)
- [ ] AC-1.5: Prompt specifies 5-7 ALWAYS rules, 5-7 NEVER rules, 3-5 ASK scenarios

### AC-2: Response Parsing Updates
- [ ] AC-2.1: Parser validates "boundaries" key exists in JSON response
- [ ] AC-2.2: Parser validates ALWAYS section has 5-7 rules with ✅ prefix
- [ ] AC-2.3: Parser validates NEVER section has 5-7 rules with ❌ prefix
- [ ] AC-2.4: Parser validates ASK section has 3-5 scenarios with ⚠️ prefix
- [ ] AC-2.5: Parser provides clear error messages for invalid boundary formats
- [ ] AC-2.6: Backward compatibility: Parser accepts both "boundaries" and "best_practices" keys

### AC-3: Content Application Updates
- [ ] AC-3.1: Applier places boundaries section after "Quick Start"
- [ ] AC-3.2: Applier places boundaries section before "Capabilities"
- [ ] AC-3.3: Applier preserves existing "Boundaries" sections if present
- [ ] AC-3.4: Applier handles both "boundaries" and "best_practices" content
- [ ] AC-3.5: Applier validates section placement before writing

### AC-4: Testing & Validation
- [ ] AC-4.1: Unit tests for prompt_builder._build_enhancement_prompt() with boundaries format
- [ ] AC-4.2: Unit tests for parser._validate_boundaries() method
- [ ] AC-4.3: Unit tests for applier._merge_content() with boundaries placement
- [ ] AC-4.4: Integration test: `/agent-enhance` generates boundaries section (not best practices)
- [ ] AC-4.5: Integration test: Enhanced agent has ALWAYS/NEVER/ASK structure
- [ ] AC-4.6: Integration test: Backward compatibility with existing best_practices responses

### AC-5: Documentation Updates
- [ ] AC-5.1: Update agent_enhancement/README.md with boundaries format examples
- [ ] AC-5.2: Add inline code comments explaining boundaries validation logic
- [ ] AC-5.3: Update error messages to reference boundaries framework
- [ ] AC-5.4: Document backward compatibility strategy

### AC-6: Edge Cases & Error Handling
- [ ] AC-6.1: Handle missing boundaries section gracefully (fallback to best_practices)
- [ ] AC-6.2: Handle malformed boundaries (missing emoji, wrong count)
- [ ] AC-6.3: Handle mixed formats (some agents with boundaries, some with best_practices)
- [ ] AC-6.4: Provide clear error messages for validation failures

### AC-7: Quality Gates
- [ ] AC-7.1: All tests pass (100% pass rate)
- [ ] AC-7.2: Code coverage ≥80% for modified files
- [ ] AC-7.3: No scope creep (only modify prompt_builder.py, parser.py, applier.py, tests)
- [ ] AC-7.4: Architectural review score ≥60/100

## Implementation Plan

### Phase 1: Prompt Builder Updates (2-3 hours)
1. Update `prompt_builder.py` line 80: Change task description to request boundaries
2. Update `prompt_builder.py` line 86: Change sections array to include "boundaries"
3. Update `prompt_builder.py` line 89: Add boundaries format specification
4. Add boundaries format example in prompt showing ALWAYS/NEVER/ASK structure
5. Test prompt generation locally

### Phase 2: Parser Updates (3-4 hours)
1. Add `_validate_boundaries()` method to `parser.py`
2. Implement ALWAYS section validation (5-7 rules, ✅ prefix)
3. Implement NEVER section validation (5-7 rules, ❌ prefix)
4. Implement ASK section validation (3-5 scenarios, ⚠️ prefix)
5. Add backward compatibility check (accept both "boundaries" and "best_practices")
6. Add clear error messages for validation failures
7. Test parser validation logic

### Phase 3: Applier Updates (2-3 hours)
1. Update `_merge_content()` in `applier.py` to handle "boundaries" key
2. Add placement logic: After "Quick Start", before "Capabilities"
3. Add section preservation logic (don't duplicate existing boundaries)
4. Add backward compatibility (handle both "boundaries" and "best_practices")
5. Test content application logic

### Phase 4: Testing (3-4 hours)
1. Write unit tests for prompt_builder boundaries format
2. Write unit tests for parser boundaries validation
3. Write unit tests for applier boundaries placement
4. Write integration test: Run `/agent-enhance` and verify boundaries section
5. Write integration test: Verify ALWAYS/NEVER/ASK structure in output
6. Write backward compatibility tests
7. Run full test suite and verify ≥80% coverage

### Phase 5: Documentation (1-2 hours)
1. Update agent_enhancement/README.md with boundaries examples
2. Add inline code comments explaining validation logic
3. Update error messages to reference boundaries framework
4. Document backward compatibility strategy

### Phase 6: Validation & Review (1-2 hours)
1. Run `/agent-enhance` on test agent to verify boundaries generation
2. Manual review of generated boundaries section
3. Verify no scope creep (only modified specified files)
4. Run architectural review (target ≥60/100)
5. Address any review findings

## Technical Details

### Files to Modify

1. **installer/global/lib/agent_enhancement/prompt_builder.py**
   - Lines 80, 86, 89: Update to request boundaries instead of best_practices
   - Add boundaries format specification

2. **installer/global/lib/agent_enhancement/parser.py**
   - Add `_validate_boundaries()` method
   - Validate ALWAYS (5-7 rules, ✅), NEVER (5-7 rules, ❌), ASK (3-5 scenarios, ⚠️)
   - Backward compatibility: Accept both "boundaries" and "best_practices"

3. **installer/global/lib/agent_enhancement/applier.py**
   - Update `_merge_content()` to place boundaries after Quick Start, before Capabilities
   - Handle both "boundaries" and "best_practices" keys

4. **Tests** (new files)
   - `tests/unit/agent_enhancement/test_prompt_builder_boundaries.py`
   - `tests/unit/agent_enhancement/test_parser_boundaries.py`
   - `tests/unit/agent_enhancement/test_applier_boundaries.py`
   - `tests/integration/test_agent_enhance_boundaries.py`

### Boundaries Format Specification

```markdown
## Boundaries

### ALWAYS
✅ Rule 1 (rationale)
✅ Rule 2 (rationale)
✅ Rule 3 (rationale)
✅ Rule 4 (rationale)
✅ Rule 5 (rationale)

### NEVER
❌ Rule 1 (rationale)
❌ Rule 2 (rationale)
❌ Rule 3 (rationale)
❌ Rule 4 (rationale)
❌ Rule 5 (rationale)

### ASK
⚠️ Scenario 1 (rationale)
⚠️ Scenario 2 (rationale)
⚠️ Scenario 3 (rationale)
```

### Backward Compatibility Strategy

**Transition Period**: Support both "boundaries" and "best_practices" for 1 release cycle

**Parser Logic**:
```python
if "boundaries" in response:
    validate_boundaries(response["boundaries"])
elif "best_practices" in response:
    # Accept but log warning
    logger.warning("Agent returned best_practices instead of boundaries (deprecated)")
    content = response["best_practices"]
else:
    raise ValueError("Missing boundaries or best_practices section")
```

**Applier Logic**:
```python
if "boundaries" in enhanced_content:
    section_content = enhanced_content["boundaries"]
    section_title = "## Boundaries"
else:
    section_content = enhanced_content.get("best_practices", "")
    section_title = "## Best Practices"
```

## Risk Assessment

### Risk 1: Breaking Existing Enhanced Agents
**Likelihood**: Medium
**Impact**: Low
**Mitigation**: Backward compatibility - accept both "boundaries" and "best_practices"

### Risk 2: Parser Validation Too Strict
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**: Clear error messages, graceful fallback to best_practices

### Risk 3: Agent-Content-Enhancer Doesn't Generate Correct Format
**Likelihood**: Low
**Impact**: High
**Mitigation**: Comprehensive prompt with examples, integration tests to catch issues early

### Risk 4: Placement Logic Breaks Existing Agent Structure
**Likelihood**: Low
**Impact**: High
**Mitigation**: Preserve existing sections, only add boundaries if missing

### Risk 5: Test Coverage Insufficient
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**: Phase 4 dedicated to comprehensive testing (unit + integration)

### Risk 6: Scope Creep
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**: Strict acceptance criteria, only modify specified files

## Testing Strategy

### Unit Tests
1. **test_prompt_builder_boundaries.py**
   - Test boundaries format in prompt generation
   - Test sections array includes "boundaries"
   - Test example format includes ALWAYS/NEVER/ASK

2. **test_parser_boundaries.py**
   - Test _validate_boundaries() with valid input
   - Test validation errors (missing emoji, wrong count)
   - Test backward compatibility (best_practices accepted)

3. **test_applier_boundaries.py**
   - Test boundaries placement (after Quick Start, before Capabilities)
   - Test section preservation (don't duplicate)
   - Test backward compatibility (handle both keys)

### Integration Tests
1. **test_agent_enhance_boundaries.py**
   - Run `/agent-enhance` on test agent
   - Verify output has "## Boundaries" section
   - Verify ALWAYS/NEVER/ASK structure
   - Verify emoji prefixes (✅ ❌ ⚠️)
   - Verify rule counts (5-7 ALWAYS, 5-7 NEVER, 3-5 ASK)

### Manual Testing
1. Run `/agent-enhance maui-mydrive/maui-mvvm-viewmodel-specialist` and verify output
2. Compare generated boundaries section to specification
3. Verify no existing sections were broken

## Success Metrics

1. **Boundary Clarity**: 0/10 → 9/10 (explicit ALWAYS/NEVER/ASK framework)
2. **Test Coverage**: ≥80% for modified files
3. **Test Pass Rate**: 100%
4. **Scope Creep**: 0 violations (only specified files modified)
5. **Architectural Review**: ≥60/100

## Rollback Plan

### Option 1: Git Revert
```bash
git revert <commit-hash>
```

### Option 2: Feature Flag
Add configuration option to switch between "boundaries" and "best_practices" mode

### Option 3: Restore Old Files
Keep backup of original prompt_builder.py, parser.py, applier.py

### Option 4: Gradual Rollout
Deploy to test environment first, validate with sample agents before production

## Related Tasks

- **TASK-STND-773D**: Parent task (documentation updates completed, code updates incomplete)
- **TASK-AI-2B37**: AgentBridgeInvoker implementation (provides foundation for agent enhancement)

## References

1. `installer/global/agents/agent-content-enhancer.md` - Lines 396-442 (boundaries specification)
2. `docs/analysis/github-agent-best-practices-analysis.md` - Boundaries framework source
3. `installer/global/lib/agent_enhancement/prompt_builder.py` - Lines 80, 86, 89 (current state)
4. `/Users/richardwoollcott/.agentecflow/templates/maui-mydrive/agents/maui-mvvm-viewmodel-specialist.md` - Example of current output (has best_practices instead of boundaries)

## Notes

- This task completes the incomplete TASK-STND-773D implementation
- Backward compatibility ensures smooth transition
- Comprehensive testing prevents regression
- Clear acceptance criteria prevent scope creep
- 6-phase plan provides structured approach (12-16 hours total)
