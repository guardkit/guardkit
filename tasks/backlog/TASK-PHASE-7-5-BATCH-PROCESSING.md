---
id: TASK-PHASE-7-5-BATCH-PROCESSING
title: "Phase 7.5: Implement Batch Processing for Agent Enhancement"
status: backlog
priority: high
created: 2025-01-16
dependencies:
  - TASK-PHASE-7-5-FIX-FOUNDATION
tags:
  - agent-enhancement
  - batch-processing
  - architecture
  - phase-7-5
estimated_effort: 8 hours
---

# Phase 7.5: Implement Batch Processing for Agent Enhancement

## Context

**Prerequisite**: This task REQUIRES completion of TASK-PHASE-7-5-FIX-FOUNDATION first.

Phase 7.5 (Agent Enhancement) currently uses a loop-based approach that is fundamentally incompatible with the checkpoint-resume pattern used for agent bridge invocations. The loop processes agents one-by-one, invoking the agent bridge for each agent, but loop state is not preserved across resume cycles. This results in only 1/10 agents being enhanced.

**Current Architecture Problem**:
```python
# BROKEN: Loop + Checkpoint-Resume Pattern
for agent_file in agent_files:  # 10 agents
    enhance_agent_file(agent_file, templates)
        └─> find_relevant_templates()
            └─> bridge.invoke()  # EXIT CODE 42 - workflow exits
# On resume: Loop restarts from beginning, no state tracking
# Result: Only agent #1 gets enhanced, 9 agents skipped
```

**Architectural Analysis Score**: Batch Processing solution scored **92/100** vs Stateful Loop at 78/100.

**Reference**: See `docs/research/phase-7-5-agent-enhancement-architecture-analysis.md` for complete analysis.

## Problem Statement

**Current Behavior**:
- Agent files remain at 31-33 lines (basic template)
- Only 1/10 agents enhanced per run
- Missing template references, best practices, code examples
- Output shows: "Found 10 agents and 15 templates" but enhancement doesn't happen

**Expected Behavior**:
- All 10 agents enhanced to 150-250 lines
- Single agent-content-enhancer invocation processes all agents
- Rich content with template references, examples, constraints
- Output shows: "Enhanced 10 agents with 15 templates"

## Acceptance Criteria

### Functional Requirements

1. **Batch Enhancement Implementation**
   - [ ] Replace loop-based enhancement with single batch invocation
   - [ ] Single call to agent-content-enhancer processes all 10 agents
   - [ ] All agents enhanced in one workflow execution (no resume cycles needed)
   - [ ] Enhanced agent files are 150-250 lines each

2. **Batch Prompt Design**
   - [ ] Structured batch request format (agent metadata + template catalog)
   - [ ] Clear separation between agents in response
   - [ ] Consistent enhancement quality across all agents
   - [ ] Template discovery included in batch prompt

3. **Response Parsing**
   - [ ] Parse batch response into individual agent enhancements
   - [ ] Robust error handling for malformed responses
   - [ ] Partial success handling (some agents enhanced, others failed)
   - [ ] Clear logging of enhancement results per agent

4. **Token Budget Optimization**
   - [ ] Total token usage ≤ 25,000 tokens (input + output)
   - [ ] Input: ~8,000-10,000 tokens (10 agents + 15 templates)
   - [ ] Output: ~15,000-18,000 tokens (10 enhanced agents)
   - [ ] Efficient template representation in batch prompt

5. **Quality Assurance**
   - [ ] All 10 agents enhanced with relevant template references
   - [ ] Each agent includes: best practices, code examples, constraints
   - [ ] Enhancement consistent with template-specific patterns
   - [ ] No scope creep (agents don't recommend features not in templates)

### Non-Functional Requirements

1. **Performance**
   - [ ] Single invocation reduces total workflow time by ~60 seconds
   - [ ] No checkpoint-resume cycles for Phase 7.5
   - [ ] Batch processing completes in <30 seconds

2. **Maintainability**
   - [ ] Clear separation of concerns (batch request vs enhancement logic)
   - [ ] Reusable batch prompt builder
   - [ ] Testable components (mocked AI responses)

3. **Robustness**
   - [ ] Graceful degradation if batch enhancement fails (fallback to basic agents)
   - [ ] Clear error messages for debugging
   - [ ] Comprehensive logging at DEBUG level

## Implementation Plan

### Phase 1: Batch Request Builder (2 hours)

**File**: `installer/global/lib/template_creation/agent_enhancer.py`

1. **Create Batch Request Structure**
   ```python
   def _build_batch_enhancement_request(
       self,
       agent_files: List[Path],
       templates: TemplateSet
   ) -> Dict[str, Any]:
       """Build structured batch request for all agents."""
       return {
           'agents': [
               {
                   'name': agent.stem,
                   'path': str(agent),
                   'metadata': self._extract_agent_metadata(agent),
                   'current_content': agent.read_text()
               }
               for agent in agent_files
           ],
           'template_catalog': self._build_template_catalog(templates),
           'enhancement_instructions': self._get_enhancement_instructions()
       }
   ```

2. **Template Catalog Builder**
   ```python
   def _build_template_catalog(self, templates: TemplateSet) -> List[Dict[str, Any]]:
       """Build compact template catalog for batch prompt."""
       catalog = []
       for category in ['components', 'pages', 'services', 'utilities', 'other']:
           category_templates = getattr(templates, category, [])
           for template in category_templates:
               catalog.append({
                   'name': template.name,
                   'category': category,
                   'path': template.relative_path,
                   'purpose': template.metadata.get('purpose', ''),
                   'technologies': template.metadata.get('technologies', [])
               })
       return catalog
   ```

3. **Enhancement Instructions**
   ```python
   def _get_enhancement_instructions(self) -> str:
       """Return standardized enhancement instructions."""
       return """
       For each agent:
       1. Find 3-5 most relevant templates based on agent's technologies
       2. Add "Template References" section with template paths and purposes
       3. Add "Best Practices" section with template-specific patterns
       4. Add "Code Examples" section with realistic examples from templates
       5. Add "Constraints" section with what agent should NOT do
       6. Target: 150-250 lines per agent
       7. Preserve original agent metadata (frontmatter)
       """
   ```

### Phase 2: Batch Invocation (2 hours)

**File**: `installer/global/lib/template_creation/agent_enhancer.py`

1. **Replace Loop with Batch Call**
   ```python
   def enhance_all_agents(self, output_path: Path) -> Dict[str, Any]:
       """Enhance all agent files using batch processing."""
       agent_files = self._get_agent_files(output_path)
       all_templates = self._load_all_templates(output_path)

       print(f"\n{'='*60}")
       print("Agent Enhancement (Batch Processing)")
       print(f"{'='*60}")
       print(f"Found {len(agent_files)} agents and {all_templates.total_count} templates")

       if not all_templates or all_templates.total_count == 0:
           logger.warning("No templates available for agent enhancement")
           return self._create_skip_result(agent_files, all_templates)

       # BATCH PROCESSING - Single invocation for all agents
       batch_result = self._batch_enhance_agents(agent_files, all_templates, output_path)

       return batch_result
   ```

2. **Batch Enhancement Method**
   ```python
   def _batch_enhance_agents(
       self,
       agent_files: List[Path],
       templates: TemplateSet,
       output_path: Path
   ) -> Dict[str, Any]:
       """Process all agents in a single batch invocation."""

       if self.bridge_invoker is None:
           logger.warning("No bridge invoker available - skipping enhancement")
           return self._create_skip_result(agent_files, templates)

       # Build batch request
       batch_request = self._build_batch_enhancement_request(agent_files, templates)

       # Single bridge invocation for all agents
       logger.info(f"Invoking agent-content-enhancer for {len(agent_files)} agents")
       batch_response = self.bridge_invoker.invoke(
           agent_name='agent-content-enhancer',
           input_data=batch_request,
           context={
               'mode': 'batch',
               'agent_count': len(agent_files),
               'template_count': templates.total_count,
               'output_path': str(output_path)
           }
       )

       # Parse and apply batch response
       return self._apply_batch_enhancements(agent_files, batch_response, output_path)
   ```

### Phase 3: Response Parsing (2 hours)

**File**: `installer/global/lib/template_creation/agent_enhancer.py`

1. **Parse Batch Response**
   ```python
   def _apply_batch_enhancements(
       self,
       agent_files: List[Path],
       batch_response: Dict[str, Any],
       output_path: Path
   ) -> Dict[str, Any]:
       """Parse batch response and apply enhancements to agent files."""

       enhanced_count = 0
       failed_count = 0
       errors = []

       # Extract enhancements from response
       enhancements = batch_response.get('enhancements', [])

       if not enhancements:
           logger.error("Batch response contains no enhancements")
           return self._create_error_result("No enhancements in batch response")

       # Map enhancements to agent files
       enhancement_map = {e['agent_name']: e for e in enhancements}

       for agent_file in agent_files:
           agent_name = agent_file.stem
           enhancement = enhancement_map.get(agent_name)

           if not enhancement:
               logger.warning(f"No enhancement found for {agent_name}")
               failed_count += 1
               errors.append(f"Missing enhancement for {agent_name}")
               continue

           try:
               success = self._apply_single_enhancement(agent_file, enhancement)
               if success:
                   enhanced_count += 1
                   print(f"  ✓ Enhanced {agent_name}")
               else:
                   failed_count += 1
                   errors.append(f"Failed to apply enhancement for {agent_name}")
           except Exception as e:
               logger.error(f"Error enhancing {agent_name}: {e}")
               failed_count += 1
               errors.append(f"{agent_name}: {str(e)}")

       return self._create_batch_result(enhanced_count, failed_count, errors)
   ```

2. **Apply Single Enhancement**
   ```python
   def _apply_single_enhancement(
       self,
       agent_file: Path,
       enhancement: Dict[str, Any]
   ) -> bool:
       """Apply enhancement content to single agent file."""

       try:
           enhanced_content = enhancement.get('enhanced_content', '')

           if not enhanced_content:
               logger.warning(f"No enhanced content for {agent_file.name}")
               return False

           # Validate enhancement quality
           if not self._validate_enhancement(enhanced_content):
               logger.warning(f"Enhancement validation failed for {agent_file.name}")
               return False

           # Write enhanced content
           agent_file.write_text(enhanced_content)

           logger.info(f"Enhanced {agent_file.name} ({len(enhanced_content)} chars)")
           return True

       except Exception as e:
           logger.error(f"Failed to apply enhancement: {e}")
           return False
   ```

3. **Enhancement Validation**
   ```python
   def _validate_enhancement(self, content: str) -> bool:
       """Validate enhanced agent content meets quality standards."""

       lines = content.split('\n')

       # Minimum length check
       if len(lines) < 150:
           logger.warning(f"Enhancement too short: {len(lines)} lines")
           return False

       # Required sections check
       required_sections = [
           'Template References',
           'Best Practices',
           'Code Examples',
           'Constraints'
       ]

       for section in required_sections:
           if section not in content:
               logger.warning(f"Missing required section: {section}")
               return False

       return True
   ```

### Phase 4: Result Handling (1 hour)

**File**: `installer/global/lib/template_creation/agent_enhancer.py`

1. **Create Result Objects**
   ```python
   def _create_batch_result(
       self,
       enhanced_count: int,
       failed_count: int,
       errors: List[str]
   ) -> Dict[str, Any]:
       """Create structured batch enhancement result."""

       total = enhanced_count + failed_count
       success_rate = (enhanced_count / total * 100) if total > 0 else 0

       result = {
           'status': 'success' if enhanced_count > 0 else 'failed',
           'enhanced_count': enhanced_count,
           'failed_count': failed_count,
           'total_count': total,
           'success_rate': success_rate,
           'errors': errors
       }

       # Log summary
       print(f"\nEnhancement Summary:")
       print(f"  Enhanced: {enhanced_count}/{total} agents ({success_rate:.1f}%)")
       if errors:
           print(f"  Errors: {len(errors)}")
           for error in errors[:3]:  # Show first 3 errors
               print(f"    - {error}")

       return result
   ```

2. **Fallback Handling**
   ```python
   def _create_skip_result(
       self,
       agent_files: List[Path],
       templates: TemplateSet
   ) -> Dict[str, Any]:
       """Create result when enhancement is skipped."""

       logger.info("Agent enhancement skipped - agents remain in basic form")

       return {
           'status': 'skipped',
           'enhanced_count': 0,
           'failed_count': 0,
           'total_count': len(agent_files),
           'success_rate': 0,
           'errors': [],
           'reason': 'No templates or bridge invoker available'
       }
   ```

### Phase 5: Integration & Testing (1 hour)

**File**: `tests/unit/lib/template_creation/test_agent_enhancer_batch.py`

1. **Test Batch Enhancement Success**
   ```python
   def test_batch_enhancement_all_agents_enhanced(mock_bridge, mock_templates):
       """Test successful batch enhancement of all agents."""

       # Setup: 10 agent files, 15 templates
       agent_files = create_mock_agent_files(10)
       templates = create_mock_template_set(15)

       # Mock batch response with all enhancements
       batch_response = {
           'enhancements': [
               {
                   'agent_name': f'agent-{i}',
                   'enhanced_content': create_enhanced_content(i)
               }
               for i in range(10)
           ]
       }
       mock_bridge.invoke.return_value = batch_response

       # Execute
       enhancer = AgentEnhancer(bridge_invoker=mock_bridge)
       result = enhancer.enhance_all_agents(output_path)

       # Verify
       assert result['status'] == 'success'
       assert result['enhanced_count'] == 10
       assert result['failed_count'] == 0
       assert result['success_rate'] == 100.0

       # Verify single bridge invocation
       assert mock_bridge.invoke.call_count == 1

       # Verify batch request structure
       call_args = mock_bridge.invoke.call_args
       assert call_args[1]['agent_name'] == 'agent-content-enhancer'
       assert len(call_args[1]['input_data']['agents']) == 10
       assert len(call_args[1]['input_data']['template_catalog']) == 15
   ```

2. **Test Partial Enhancement**
   ```python
   def test_batch_enhancement_partial_success(mock_bridge):
       """Test batch enhancement with some failures."""

       # Setup: 10 agents, but only 7 enhancements returned
       agent_files = create_mock_agent_files(10)

       batch_response = {
           'enhancements': [
               {'agent_name': f'agent-{i}', 'enhanced_content': create_enhanced_content(i)}
               for i in range(7)  # Only 7 of 10
           ]
       }
       mock_bridge.invoke.return_value = batch_response

       # Execute
       enhancer = AgentEnhancer(bridge_invoker=mock_bridge)
       result = enhancer.enhance_all_agents(output_path)

       # Verify partial success
       assert result['status'] == 'success'  # Still success if any enhanced
       assert result['enhanced_count'] == 7
       assert result['failed_count'] == 3
       assert result['success_rate'] == 70.0
       assert len(result['errors']) == 3
   ```

3. **Test Token Budget**
   ```python
   def test_batch_request_token_budget():
       """Test batch request stays within token budget."""

       # Setup: Maximum size scenario
       agent_files = create_mock_agent_files(10)  # ~100 lines each
       templates = create_mock_template_set(15)    # ~50 lines each

       enhancer = AgentEnhancer(bridge_invoker=None)
       batch_request = enhancer._build_batch_enhancement_request(
           agent_files, templates
       )

       # Estimate tokens (rough: 4 chars = 1 token)
       request_json = json.dumps(batch_request)
       estimated_tokens = len(request_json) / 4

       # Verify within budget
       assert estimated_tokens < 10000, f"Request too large: {estimated_tokens} tokens"
   ```

4. **Test Enhancement Validation**
   ```python
   def test_enhancement_validation_rejects_insufficient_content():
       """Test validation rejects content that doesn't meet standards."""

       enhancer = AgentEnhancer(bridge_invoker=None)

       # Too short
       short_content = "# Agent\n\n" + "line\n" * 50
       assert not enhancer._validate_enhancement(short_content)

       # Missing required sections
       incomplete_content = "# Agent\n\n" + "line\n" * 200
       assert not enhancer._validate_enhancement(incomplete_content)

       # Valid content
       valid_content = create_enhanced_content_with_all_sections()
       assert enhancer._validate_enhancement(valid_content)
   ```

## Technical Specifications

### Token Budget Analysis

**Input Tokens** (~8,000-10,000):
- 10 agents × 30 lines × 50 chars = ~15,000 chars = ~3,750 tokens
- 15 templates × 50 lines × 50 chars = ~37,500 chars = ~9,375 tokens
- Enhancement instructions: ~500 tokens
- **Total Input**: ~13,625 tokens (conservative estimate)

**Output Tokens** (~15,000-18,000):
- 10 enhanced agents × 200 lines × 50 chars = ~100,000 chars = ~25,000 tokens
- **Total Output**: ~25,000 tokens (conservative estimate)

**Optimization Strategy**:
- Use template catalog instead of full template content (reduce by ~80%)
- Include only essential agent metadata (name, technologies, purpose)
- Structured JSON response instead of markdown (reduce by ~20%)
- **Optimized Total**: ~10,000 input + ~18,000 output = ~28,000 tokens

**Acceptable**: Well within Claude's 200K context window and reasonable for batch operation.

### Batch Prompt Structure

```json
{
  "agents": [
    {
      "name": "api-specialist",
      "technologies": ["TypeScript", "REST API", "Express"],
      "current_content": "...",
      "metadata": {...}
    }
  ],
  "template_catalog": [
    {
      "name": "api-route-handler",
      "category": "services",
      "path": "services/api/route-handler.template",
      "purpose": "RESTful API endpoint with validation",
      "technologies": ["TypeScript", "Express", "Zod"]
    }
  ],
  "enhancement_instructions": "..."
}
```

### Expected Response Structure

```json
{
  "enhancements": [
    {
      "agent_name": "api-specialist",
      "enhanced_content": "---\nname: api-specialist\n...\n## Template References\n...",
      "templates_referenced": ["api-route-handler", "error-handler"],
      "line_count": 187,
      "quality_score": 9
    }
  ],
  "summary": {
    "total_agents": 10,
    "enhanced": 10,
    "average_quality": 8.7
  }
}
```

## Testing Strategy

### Unit Tests (8 tests)

1. `test_batch_enhancement_all_agents_enhanced()` - Success case
2. `test_batch_enhancement_partial_success()` - Partial enhancement
3. `test_batch_enhancement_no_templates()` - Graceful skip
4. `test_batch_enhancement_bridge_failure()` - Error handling
5. `test_batch_request_structure()` - Request format validation
6. `test_batch_response_parsing()` - Response parsing
7. `test_enhancement_validation()` - Quality validation
8. `test_token_budget_compliance()` - Token usage verification

### Integration Tests (3 tests)

1. **End-to-End Batch Enhancement**
   ```bash
   /template-create --name test-batch --verbose
   # Verify:
   # - Single agent-content-enhancer invocation
   # - All 10 agents enhanced
   # - Agent files 150-250 lines
   # - No checkpoint-resume cycles in Phase 7.5
   ```

2. **Agent Quality Validation**
   ```bash
   # Check enhanced agent content
   wc -l ~/.agentecflow/templates/test-batch/agents/*.md
   grep "Template References" ~/.agentecflow/templates/test-batch/agents/*.md
   grep "Best Practices" ~/.agentecflow/templates/test-batch/agents/*.md
   grep "Code Examples" ~/.agentecflow/templates/test-batch/agents/*.md
   ```

3. **Performance Measurement**
   ```bash
   # Compare workflow duration before/after
   # Expected improvement: -60 seconds (no resume cycles)
   ```

### Test Coverage Goals

- Line Coverage: ≥85%
- Branch Coverage: ≥80%
- Critical Path Coverage: 100%

## Success Metrics

### Functional Success

- ✅ All 10 agents enhanced in single workflow execution
- ✅ Single agent-content-enhancer invocation (not 10)
- ✅ Enhanced agents are 150-250 lines each
- ✅ All agents include required sections (Template References, Best Practices, Code Examples, Constraints)
- ✅ No checkpoint-resume cycles during Phase 7.5

### Quality Success

- ✅ Architectural review score: ≥92/100 (target from analysis)
- ✅ Enhancement consistency across all agents
- ✅ Template references are accurate and relevant
- ✅ Code examples are realistic and stack-appropriate
- ✅ No scope creep in agent recommendations

### Performance Success

- ✅ Workflow time reduction: ≥60 seconds (eliminate 9 resume cycles)
- ✅ Token usage: ≤28,000 tokens total (input + output)
- ✅ Phase 7.5 completion: <30 seconds
- ✅ No degradation in other phases

### Maintainability Success

- ✅ Code complexity reduction (eliminate loop state management)
- ✅ Clear error messages for debugging
- ✅ Comprehensive logging at DEBUG level
- ✅ All tests passing with ≥85% coverage

## Risk Assessment

### High Risk

**Risk**: Batch response parsing failures
- **Mitigation**: Robust error handling with partial success support
- **Fallback**: Skip enhancement gracefully (agents remain in basic form)
- **Test Coverage**: Dedicated tests for malformed responses

**Risk**: Token budget exceeded for large codebases
- **Mitigation**: Template catalog instead of full content (80% reduction)
- **Monitoring**: Log token usage estimates
- **Fallback**: Reduce template details if needed

### Medium Risk

**Risk**: Enhancement quality degradation in batch mode
- **Mitigation**: Validation checks for required sections
- **Quality Gates**: Reject enhancements <150 lines or missing sections
- **Test Coverage**: Quality validation tests

**Risk**: Agent-content-enhancer changes breaking integration
- **Mitigation**: Version batch request format
- **Compatibility**: Support both batch and single-agent modes during transition
- **Test Coverage**: Integration tests with real agent invocations

### Low Risk

**Risk**: Template catalog incompleteness
- **Mitigation**: Comprehensive template metadata extraction
- **Validation**: Verify all templates included in catalog
- **Test Coverage**: Catalog building tests

## Dependencies

### Required Completion

- **TASK-PHASE-7-5-FIX-FOUNDATION**: MUST be completed first
  - Provides WorkflowPhase constants
  - Fixes resume routing for Phase 7.5
  - Ensures templates written to disk before Phase 7.5
  - Foundation must score ≥82/100 before batch implementation

### External Dependencies

- **AgentBridgeInvoker**: File-based IPC for agent invocation (existing)
- **TemplateSet**: Template container structure (existing)
- **agent-content-enhancer**: AI agent for content generation (existing)

## Rollback Plan

If batch processing encounters issues in production:

1. **Immediate Rollback**: Keep loop-based code as `_loop_enhance_agents()` method
2. **Feature Flag**: Add `use_batch_enhancement` flag in config
3. **Gradual Migration**: Test batch mode on small codebases first
4. **Fallback Logic**:
   ```python
   if config.use_batch_enhancement and len(agent_files) <= 10:
       return self._batch_enhance_agents(agent_files, templates, output_path)
   else:
       return self._loop_enhance_agents(agent_files, templates, output_path)
   ```

## Definition of Done

- [ ] All acceptance criteria met
- [ ] All unit tests passing (8 tests)
- [ ] All integration tests passing (3 tests)
- [ ] Test coverage ≥85% line, ≥80% branch
- [ ] Code review approved (architectural-reviewer + code-reviewer)
- [ ] Architectural score ≥92/100
- [ ] Documentation updated (architecture analysis marked as implemented)
- [ ] Performance benchmarks met (≥60s improvement)
- [ ] No regressions in other phases
- [ ] Successfully tested on 3 different codebases (small, medium, large)

## Notes

### Implementation Sequence

This task MUST be implemented AFTER TASK-PHASE-7-5-FIX-FOUNDATION because:

1. **Foundation provides critical infrastructure**:
   - WorkflowPhase constants for phase numbers
   - Fixed resume routing that won't skip Phase 7.5
   - Template pre-writing that batch processing depends on
   - Enhanced serialization for batch response handling

2. **Quality baseline requirement**:
   - Foundation fixes bring quality from 72/100 → 82/100
   - Batch processing builds on stable foundation to reach 92/100
   - Without foundation fixes, batch processing may encounter edge cases

3. **Risk management**:
   - Foundation fixes are lower risk, higher impact
   - Batch processing is higher complexity, requires stable base
   - Incremental improvement approach (fix foundation, then optimize)

### Expected Outcome

After completion:
- `/template-create` runs Phase 7.5 with single agent invocation
- All 10 agents enhanced to 150-250 lines
- Total workflow time reduced by ~60 seconds
- Output shows: "Enhanced 10 agents with 15 templates (100% success)"
- Architectural quality score: 92/100

### Reference Implementation

See `docs/research/phase-7-5-agent-enhancement-architecture-analysis.md` Section 4.1 for detailed batch processing design rationale and comparison with alternative approaches.
