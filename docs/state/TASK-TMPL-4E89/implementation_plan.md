# Implementation Plan: TASK-TMPL-4E89

**Task**: Replace Hard-Coded Agent Detection with AI-Powered Analysis
**Complexity**: 8/10 (Complex)
**Priority**: High
**Estimated Duration**: 6-8 hours
**Stack**: Python (guardkit-python orchestrator pattern)

---

## Executive Summary

Replace the hard-coded pattern detection in `agent_generator.py` (5 IF statements, 14-30% coverage) with AI-powered comprehensive analysis that identifies ALL needed agents from complete codebase analysis. This enhancement will dramatically improve template generation effectiveness for complex codebases.

**Key Improvement**: Complex .NET MAUI app currently detects 1 agent (14%) → will detect 7-9 agents (78-100%)

---

## Architecture Overview

### Current Architecture (Problems)
```
CodebaseAnalyzer → Analysis Object
                      ↓
         AgentGenerator._identify_capability_needs()
                      ↓
              [5 Hard-Coded Checks]
                      ↓
         Returns: 0-2 CapabilityNeeds (poor coverage)
```

**Issues**:
- Only detects MVVM, Navigation, ErrorOr, Domain, Testing (5 patterns)
- Cannot detect: Repository, Service, Engine, CQRS, Event Sourcing, database patterns, framework specialists
- Maintenance burden (add IF for each new pattern)
- Limited by developer imagination

### Proposed Architecture (Solution)
```
CodebaseAnalyzer → Analysis Object (comprehensive)
                      ↓
         AgentGenerator._ai_identify_all_agents()
                      ↓
         [Single AI Call with Full Context]
                      ↓
         JSON Array of Agent Specifications
                      ↓
         Parse & Validate → CapabilityNeed Objects
                      ↓
         Fallback to hard-coded if AI fails
                      ↓
         Returns: 7-15+ CapabilityNeeds (comprehensive coverage)
```

**Benefits**:
- Single AI call analyzes complete codebase context
- Identifies ALL needed agents comprehensively
- Zero maintenance (no code changes for new patterns)
- Self-improving (learns from codebase patterns)

---

## Implementation Design

### Phase 1: AI Integration Method

**File**: `installer/core/lib/agent_generator/agent_generator.py`

**New Method**: `_ai_identify_all_agents(analysis)`

```python
def _ai_identify_all_agents(self, analysis: Any) -> List[CapabilityNeed]:
    """
    Use AI to comprehensively identify ALL needed agents

    Single AI call analyzes complete codebase analysis and returns
    structured JSON array of agent specifications.

    Args:
        analysis: Complete CodebaseAnalysis object

    Returns:
        List of CapabilityNeed objects (7-15+ for complex codebases)

    Raises:
        AIAnalysisError: If AI call fails (caught internally)
    """
```

**Design Decisions**:

1. **Single AI Call** (not one-per-agent)
   - Performance: 1 call vs 10+ calls
   - Context: AI sees complete picture, not fragments
   - Token budget: 3000-5000 tokens (within Phase 5 budget)

2. **Structured JSON Response**
   ```json
   [
     {
       "name": "mvvm-viewmodel-specialist",
       "description": "MVVM ViewModel patterns with INotifyPropertyChanged",
       "reason": "Project has 8 ViewModels following MVVM pattern",
       "technologies": ["C#", "MVVM", ".NET MAUI"],
       "example_files": ["ViewModels/HomeViewModel.cs", "ViewModels/UserViewModel.cs"],
       "priority": 9
     },
     {
       "name": "repository-pattern-specialist",
       "description": "Repository pattern for data access abstraction",
       "reason": "Project uses repository pattern in 5 data access layers",
       "technologies": ["C#", "Repository Pattern", "Entity Framework"],
       "example_files": ["Repositories/UserRepository.cs"],
       "priority": 8
     }
   ]
   ```

3. **Error Handling Strategy**
   - Try AI analysis first (preferred)
   - Catch JSON parsing errors gracefully
   - Fallback to hard-coded detection if AI fails
   - Log fallback usage for monitoring
   - Never block template creation

4. **Backward Compatibility**
   - Existing `_identify_capability_needs()` becomes fallback
   - No breaking changes to orchestrator integration
   - Existing unit tests continue to pass
   - New tests added for AI path

---

### Phase 2: AI Prompt Engineering

**Prompt Structure** (3000-4000 tokens):

```python
def _build_ai_analysis_prompt(self, analysis: Any) -> str:
    """Build comprehensive AI prompt with complete context"""

    # Extract ALL analysis data (not just example_files)
    language = getattr(analysis, 'language', 'Unknown')
    architecture_pattern = getattr(analysis, 'architecture_pattern', None)
    frameworks = getattr(analysis, 'frameworks', [])
    layers = getattr(analysis, 'layers', [])
    patterns = getattr(analysis, 'patterns', [])
    testing_framework = getattr(analysis, 'testing_framework', None)
    database_tech = getattr(analysis, 'database_tech', None)

    # Include quality assessment for error handling patterns
    quality_assessment = getattr(analysis, 'quality_assessment', '')

    # Include example files (up to 10 for context)
    example_files = getattr(analysis, 'example_files', [])[:10]
```

**Prompt Template**:
```
You are analyzing a codebase to identify ALL specialized AI agents needed
for template generation. Your goal is comprehensive coverage.

CODEBASE ANALYSIS:
- Language: {language}
- Architecture: {architecture_pattern}
- Frameworks: {frameworks}
- Layers: {layers}
- Patterns: {patterns}
- Testing: {testing_framework}
- Database: {database_tech}

EXAMPLE FILES (showing implementation patterns):
{formatted_example_files_with_snippets}

TASK: Identify ALL specialized agents needed for this codebase.

Consider these agent categories:
1. Architecture Specialists: MVVM, MVC, Clean Architecture, Hexagonal, CQRS, Event Sourcing
2. Layer Specialists: Domain, Application, Infrastructure, Presentation
3. Pattern Specialists: Repository, Service, Factory, Strategy, Observer
4. Technology Specialists: Database (EF, Dapper), ORM, API (REST, GraphQL)
5. Framework Specialists: React, FastAPI, .NET MAUI, Next.js
6. Quality Specialists: Testing framework, Error handling, Logging
7. Platform Specialists: Mobile (iOS, Android), Web, Desktop

OUTPUT FORMAT (JSON array):
[
  {
    "name": "agent-name-kebab-case",
    "description": "Brief description of agent capability",
    "reason": "Why this agent is needed (specific to this codebase)",
    "technologies": ["Tech1", "Tech2"],
    "example_files": ["file1.cs", "file2.cs"],
    "priority": 1-10
  }
]

REQUIREMENTS:
- Return ONLY valid JSON (no markdown, no commentary)
- Include minimum 5 agents (comprehensive analysis)
- Prioritize agents by importance (10=critical, 1=optional)
- Base agents on ACTUAL codebase evidence (not assumptions)
- Include example_files from the analysis provided
```

**Key Principles**:
- Comprehensive category guidance (7 categories)
- Evidence-based (requires codebase justification)
- Structured output (JSON only, parseable)
- Quality over quantity (but minimum 5)
- Priority-based (helps with gap analysis)

---

### Phase 3: JSON Parsing & Validation

**Implementation**:

```python
def _parse_ai_agent_response(self, response: str, analysis: Any) -> List[CapabilityNeed]:
    """
    Parse AI JSON response into CapabilityNeed objects

    Args:
        response: JSON string from AI
        analysis: Analysis object for fallback data

    Returns:
        List of CapabilityNeed objects
    """
    try:
        # Parse JSON
        agents_data = json.loads(response)

        # Validate structure
        if not isinstance(agents_data, list):
            raise ValueError("Response must be JSON array")

        if len(agents_data) < 3:
            print(f"  ⚠️  AI returned only {len(agents_data)} agents (expected 5+)")

        # Convert to CapabilityNeed objects
        needs = []
        for agent_spec in agents_data:
            need = self._create_capability_need_from_spec(agent_spec, analysis)
            if need:
                needs.append(need)

        return sorted(needs, key=lambda n: n.priority, reverse=True)

    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON parsing failed: {e}")
        return self._fallback_to_hardcoded(analysis)

    except Exception as e:
        print(f"  ⚠️  AI analysis failed: {e}")
        return self._fallback_to_hardcoded(analysis)
```

**Validation Rules**:
1. Must be valid JSON array
2. Each object must have: name, description, reason, technologies, priority
3. Priority must be 1-10 integer
4. Technologies must be non-empty array
5. Name must be kebab-case string
6. Minimum 3 agents (warn if <5)

**Error Recovery**:
- JSON parsing error → fallback
- Missing required fields → skip agent, continue parsing
- Invalid priority → default to 5
- Empty array → fallback
- Any exception → fallback with logging

---

### Phase 4: Integration with Existing Workflow

**Orchestrator Integration**:

File: `installer/core/orchestrators/template_create_orchestrator.py`

```python
# Phase 5: Generate agents
print("\n" + "="*55)
print("🤖 PHASE 5: AGENT GENERATION")
print("="*55)

agent_generator = AIAgentGenerator(
    inventory=agent_inventory,
    ai_invoker=self.ai_invoker  # Already exists in orchestrator
)

generated_agents = agent_generator.generate(codebase_analysis)
```

**No changes needed to orchestrator** - `ai_invoker` already exists and is passed to `AIAgentGenerator`.

**Method Modification**:

```python
def _identify_capability_needs(self, analysis: Any) -> List[CapabilityNeed]:
    """
    Identify needed agent capabilities

    Strategy:
    1. Try AI-powered comprehensive analysis (preferred)
    2. Fallback to hard-coded detection if AI fails
    3. Always return some result (never block workflow)
    """
    try:
        # Try AI analysis first
        ai_needs = self._ai_identify_all_agents(analysis)

        if ai_needs and len(ai_needs) >= 3:
            print(f"  ✓ AI identified {len(ai_needs)} agents")
            return ai_needs
        else:
            print(f"  ⚠️  AI analysis incomplete ({len(ai_needs)} agents)")
            raise ValueError("Insufficient AI results")

    except Exception as e:
        print(f"  ⚠️  Falling back to hard-coded detection: {e}")
        return self._fallback_to_hardcoded(analysis)
```

**Fallback Method**:

```python
def _fallback_to_hardcoded(self, analysis: Any) -> List[CapabilityNeed]:
    """
    Fallback to original hard-coded detection

    This is the existing _identify_capability_needs() logic,
    preserved for reliability.
    """
    # Original 5 IF statements (lines 141-233 currently)
    needs = []

    # MVVM check
    if architecture_pattern == "MVVM":
        needs.append(CapabilityNeed(...))

    # Navigation check
    # ErrorOr check
    # Domain check
    # Testing check

    return sorted(needs, key=lambda n: n.priority, reverse=True)
```

---

### Phase 5: Testing Strategy

**Unit Tests** (80%+ coverage target):

File: `tests/unit/lib/agent_generator/test_ai_agent_generator.py`

```python
class TestAIAgentGeneration:
    """Test AI-powered agent generation"""

    def test_ai_identifies_multiple_agents(self):
        """AI should identify 7+ agents for complex codebase"""
        # Given: Complex .NET MAUI analysis
        analysis = create_complex_maui_analysis()

        # When: AI analysis runs
        generator = AIAgentGenerator(inventory, mock_ai_invoker)
        needs = generator._ai_identify_all_agents(analysis)

        # Then: Should identify 7+ agents
        assert len(needs) >= 7
        assert any("mvvm" in n.name for n in needs)
        assert any("repository" in n.name for n in needs)

    def test_ai_returns_valid_json(self):
        """AI response should parse as valid JSON"""
        # Test JSON parsing with valid response

    def test_fallback_on_invalid_json(self):
        """Should fallback to hard-coded if JSON invalid"""
        # Mock AI returning invalid JSON
        # Verify fallback method called
        # Verify template creation continues

    def test_fallback_on_ai_failure(self):
        """Should fallback to hard-coded if AI fails"""
        # Mock AI throwing exception
        # Verify fallback gracefully

    def test_agent_priority_sorting(self):
        """Agents should be sorted by priority (high first)"""

    def test_backward_compatibility(self):
        """Existing hard-coded detection still works"""
        # Test original 5 patterns still detected
```

**Integration Tests**:

File: `tests/integration/lib/test_agent_generator_integration.py`

```python
class TestAgentGeneratorIntegration:
    """Test full agent generation workflow"""

    def test_end_to_end_complex_codebase(self):
        """Test complete workflow with real codebase analysis"""
        # Given: Real codebase analysis
        analysis = analyze_real_codebase("samples/dotnet-maui")

        # When: Generate agents
        generator = AIAgentGenerator(inventory, real_ai_invoker)
        generated = generator.generate(analysis)

        # Then: Should generate 7+ agents
        assert len(generated) >= 7

        # Should save to .claude/agents/
        for agent in generated:
            agent_file = Path(f".claude/agents/{agent.name}.md")
            assert agent_file.exists()

    def test_orchestrator_integration(self):
        """Test integration with template_create_orchestrator"""
        # Verify orchestrator can call generator
        # Verify agents created successfully
        # Verify no breaking changes
```

**Test Coverage Targets**:
- Unit tests: 85%+ coverage
- Integration tests: Key workflows covered
- Error paths: All exception handlers tested
- Fallback: Hard-coded detection tested
- JSON parsing: Valid, invalid, edge cases

---

## Files to Modify

### 1. Core Implementation
**File**: `installer/core/lib/agent_generator/agent_generator.py` (Lines 120-235)

**Changes**:
- Add `_ai_identify_all_agents()` method (new, ~80 lines)
- Add `_build_ai_analysis_prompt()` method (new, ~60 lines)
- Add `_parse_ai_agent_response()` method (new, ~40 lines)
- Add `_create_capability_need_from_spec()` method (new, ~30 lines)
- Rename existing `_identify_capability_needs()` to `_fallback_to_hardcoded()` (~100 lines)
- Rewrite `_identify_capability_needs()` as AI-first dispatcher (~30 lines)

**Total LOC**: ~340 lines (current: 115 lines) = +225 lines

### 2. Unit Tests
**File**: `tests/unit/lib/agent_generator/test_ai_agent_generator.py` (new)

**Contents**:
- 8-10 test methods
- Mock AI invoker fixtures
- Sample analysis fixtures
- ~200 lines

### 3. Integration Tests
**File**: `tests/integration/lib/test_agent_generator_integration.py` (existing, extend)

**Changes**:
- Add 2-3 integration test methods
- ~80 lines additional

---

## Dependencies & Technologies

**Existing Dependencies** (no new packages):
- `json` (stdlib) - JSON parsing
- `dataclasses` (stdlib) - CapabilityNeed structure
- `typing` (stdlib) - Type hints
- `pathlib` (stdlib) - File handling
- AI invoker (already exists in orchestrator)

**AI Infrastructure** (already exists):
- `AgentInvoker` protocol (existing, DIP compliance)
- AI client integration (used in Phases 5 & 7)
- Token budget management (3000-5000 tokens, within budget)

**No New Dependencies Required** ✅

---

## Risk Assessment & Mitigation

### Risk 1: AI Returns Invalid JSON (Medium)
**Impact**: Agent generation fails
**Probability**: 15-20% (based on Phase 5/7 experience)
**Mitigation**:
- Robust JSON parsing with try/catch
- Fallback to hard-coded detection
- Template creation continues (no blocking)
- Log failures for monitoring

### Risk 2: AI Returns Insufficient Agents (Low)
**Impact**: Reduced coverage (but still better than current 14-30%)
**Probability**: 10%
**Mitigation**:
- Minimum threshold check (warn if <5 agents)
- Combine AI + hard-coded results if needed
- Monitor average agent count over time

### Risk 3: Performance Degradation (Low)
**Impact**: Template creation slower
**Probability**: 5%
**Mitigation**:
- Single AI call (not per-agent)
- Token budget: 3000-5000 tokens (~15-20 seconds)
- Async execution (if needed)
- Cache results for repeated analysis

### Risk 4: Backward Compatibility Break (Low)
**Impact**: Existing workflows fail
**Probability**: 5%
**Mitigation**:
- Preserve existing hard-coded method as fallback
- No changes to orchestrator integration
- Existing unit tests must pass
- Gradual rollout with monitoring

---

## Acceptance Criteria Verification

✅ **AC1**: New `_ai_identify_all_agents(analysis)` method created
- Implementation: Phase 1 & 2
- Returns: List[CapabilityNeed]
- Token budget: 3000-5000 tokens

✅ **AC2**: AI returns structured JSON array
- Format: Array of agent specifications
- Fields: name, description, reason, technologies, example_files, priority
- Validation: JSON schema check

✅ **AC3**: JSON parsing with error handling
- Try/catch around json.loads()
- Fallback on parse failure
- Validation of required fields

✅ **AC4**: Integration maintains backward compatibility
- Existing method becomes fallback
- No orchestrator changes required
- Existing tests continue to pass

✅ **AC5**: Complex templates generate 7+ agents
- Target: 78-100% coverage (vs current 14-30%)
- Evidence-based (codebase patterns)
- Priority-sorted

✅ **AC6**: Unit and integration tests with 80%+ coverage
- Unit tests: ~200 lines (8-10 methods)
- Integration tests: ~80 lines (2-3 methods)
- Error path coverage: 100%

---

## Success Metrics

**Before (Current State)**:
- Agent detection: Hard-coded (5 IF statements)
- Coverage: 14-30% for complex codebases
- Example: .NET MAUI detects 1 agent (14%)
- Maintenance: Add code for each new pattern

**After (Target State)**:
- Agent detection: AI-powered comprehensive analysis
- Coverage: 78-100% for complex codebases
- Example: .NET MAUI detects 7-9 agents (78-100%)
- Maintenance: Zero (self-improving)

**Improvement**:
- Coverage increase: 5-7x improvement
- Agent count: 7-9 agents vs 1 agent
- Maintenance reduction: 100% (no code changes)
- Adaptability: Works with any language/pattern

---

## Implementation Timeline

**Phase 1: Core AI Integration** (2 hours)
- Implement `_ai_identify_all_agents()` method
- Build comprehensive AI prompt
- Token budget: 3000-5000 tokens

**Phase 2: JSON Parsing & Validation** (1 hour)
- Implement `_parse_ai_agent_response()`
- Field validation
- Error handling

**Phase 3: Workflow Integration** (1 hour)
- Refactor `_identify_capability_needs()` as dispatcher
- Rename existing to `_fallback_to_hardcoded()`
- Maintain backward compatibility

**Phase 4: Unit Testing** (2 hours)
- 8-10 test methods
- Mock AI responses
- Error path coverage

**Phase 5: Integration Testing** (1.5 hours)
- End-to-end tests
- Orchestrator integration verification
- Real codebase testing

**Phase 6: Documentation & Review** (0.5 hours)
- Update docstrings
- Add inline comments
- Review against acceptance criteria

**Total**: 8 hours (within 6-8 hour estimate)

---

## Architecture Decision Records

### ADR-001: Single AI Call vs Per-Agent Calls

**Decision**: Use single AI call for all agents

**Context**:
- Could call AI once per agent category (7 calls)
- Could call AI once for all agents (1 call)

**Rationale**:
- Performance: 1 call vs 7+ calls (~85% faster)
- Context: AI sees complete picture, better recommendations
- Token efficiency: 4000 tokens vs 7000+ tokens
- Simplicity: Single response parsing

**Trade-offs**:
- Pro: Faster, cheaper, better context
- Con: Single point of failure (mitigated by fallback)

---

### ADR-002: Fallback Strategy

**Decision**: Preserve hard-coded detection as fallback

**Context**:
- AI may fail or return invalid JSON
- Template creation must not be blocked

**Rationale**:
- Reliability: Always returns some result
- Backward compatible: Existing logic preserved
- Gradual rollout: Monitor AI performance
- User experience: No blocking errors

**Trade-offs**:
- Pro: Zero disruption, safe rollout
- Con: Increased code complexity (manageable)

---

### ADR-003: JSON Response Format

**Decision**: Structured JSON array with validation

**Context**:
- Could use natural language parsing
- Could use structured JSON
- Could use markdown format

**Rationale**:
- Parseability: json.loads() reliable
- Validation: Schema checking straightforward
- Error handling: Clear failure modes
- Integration: Easy to convert to CapabilityNeed

**Trade-offs**:
- Pro: Robust, testable, maintainable
- Con: Requires AI prompt engineering (acceptable)

---

## Testing Plan Summary

**Unit Tests** (85%+ coverage):
- AI method logic
- JSON parsing (valid, invalid, edge cases)
- Fallback mechanism
- CapabilityNeed conversion
- Error handling paths

**Integration Tests**:
- End-to-end workflow
- Orchestrator integration
- Real codebase analysis
- File system operations

**Manual Testing**:
- Complex .NET MAUI template (target: 7+ agents)
- React TypeScript template (target: 5+ agents)
- FastAPI Python template (target: 6+ agents)
- Fallback scenario (invalid AI response)

---

## Monitoring & Observability

**Metrics to Track**:
```python
metrics = {
    "ai_success_rate": "% of times AI analysis succeeds",
    "fallback_rate": "% of times fallback used",
    "avg_agents_generated": "Average agent count per template",
    "avg_execution_time": "Time for agent generation",
    "json_parse_failures": "Count of JSON errors",
    "agent_coverage": "% of patterns detected"
}
```

**Logging**:
- AI analysis attempts
- Fallback usage (with reason)
- Agent count per template
- Execution time per phase
- JSON parsing errors

---

## Future Enhancements (Out of Scope)

These are explicitly NOT included in this task:

1. **Agent Quality Scoring**: AI evaluates agent quality (separate task)
2. **Agent Deduplication**: Merge similar agents (separate task)
3. **Agent Customization**: User modifies AI suggestions (separate task)
4. **Multi-Model Support**: Try GPT-4 if Claude fails (separate task)
5. **Caching**: Cache analysis results (separate task)

---

## Conclusion

This implementation replaces hard-coded pattern detection (5 IF statements, 14-30% coverage) with AI-powered comprehensive analysis (single call, 78-100% coverage).

**Key Benefits**:
- 5-7x improvement in agent detection coverage
- Zero maintenance burden (self-improving)
- Backward compatible (fallback preserved)
- Production-ready (robust error handling)
- Well-tested (80%+ coverage)

**Complexity Justification** (8/10):
- File changes: 3 files (1 core, 2 tests)
- New methods: 5 methods (~340 lines)
- AI integration: Comprehensive prompt engineering
- Testing: 10-13 test methods
- Risk management: Multiple mitigation strategies

**Next Steps**:
1. Human approval of implementation plan
2. Execute Phase 1-6 (8 hours)
3. Run test suite (target: 80%+ coverage)
4. Manual testing with 3+ template types
5. Monitor metrics for 1 week
6. Iterate based on results

---

**Plan Status**: Ready for Review
**Documentation Level**: Standard (brief architecture notes + key decisions)
**Review Required**: Yes (complexity 8/10)
