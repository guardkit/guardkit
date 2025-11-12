---
id: TASK-TMPL-4E89
title: Replace Hard-Coded Agent Detection with AI-Powered Analysis
status: completed
created: 2025-11-11T14:00:00Z
updated: 2025-01-11T00:00:00Z
completed: 2025-01-11T16:00:00Z
priority: high
tags: [template-creation, agent-generation, ai, core-limitation, enhancement]
complexity: 8
affected_files:
  - installer/global/lib/agent_generator/agent_generator.py
  - installer/global/commands/lib/template_create_orchestrator.py
test_results:
  status: passed
  total_tests: 29
  passed: 29
  failed: 0
  pass_rate: 100
  line_coverage: 86
  branch_coverage: 79
  last_run: "2025-01-11T00:00:00Z"
previous_state: in_review
state_transition_reason: "Task completed successfully: 100% tests passing, 86% line coverage, 79% branch coverage, code quality 8.5/10, all acceptance criteria met"
completed_location: tasks/completed/TASK-TMPL-4E89/
organized_files: ["TASK-TMPL-4E89.md"]
design:
  status: approved
  approved_at: "2025-01-11T00:00:00Z"
  approved_by: "human"
  implementation_plan_version: "v1"
  architectural_review_score: 78
  complexity_score: 8
  design_session_id: "design-TASK-TMPL-4E89-20250111000000"
  design_notes: "Design approved via --design-only workflow. Architectural review: 78/100 (approved with recommendations). Complexity: 8/10 (complex). Estimated: 8 hours, 505 LOC, 3 files."
  recommendations:
    - "Remove Retry pattern (YAGNI violation) - saves 100 lines"
    - "Simplify Strategy pattern to if/else - saves 120 lines"
    - "Verify Either pattern need - may save 130 lines"
implementation:
  status: completed
  code_review_score: 8.5
  approved_by: "code-reviewer"
  actual_loc: 470
  actual_files: 1
completion_metrics:
  total_duration_hours: 8
  implementation_time_hours: 6.5
  testing_time_hours: 1
  review_time_hours: 0.5
  test_iterations: 1
  final_line_coverage: 86
  final_branch_coverage: 79
  final_test_count: 29
  final_test_passing: 29
  requirements_met: "6/6 acceptance criteria groups"
  critical_constraint_met: true
---

# Task: Replace Hard-Coded Agent Detection with AI-Powered Analysis

## Problem Statement

**CORE SYSTEM LIMITATION**: The `/template-create` command uses **hard-coded pattern detection** for agent identification, severely limiting its usefulness for real-world complex codebases.

### Current Implementation (Lines 120-235 in agent_generator.py)

The `_identify_capability_needs()` method has **5 hard-coded IF statements** that only detect:

1. **MVVM** - Only if `architecture_pattern == "MVVM"` (exact string match)
2. **Navigation** - Only if `"navigation"` in layer patterns
3. **ErrorOr** - Only if `"ErrorOr"` in quality assessment string
4. **Domain** - Only if `layer_name == "domain"` (exact match)
5. **Testing** - Only if `testing_framework` attribute exists

**This cannot detect**:
- Repository, Service, Engine patterns
- Database-specific patterns (Realm, EF Core, MongoDB)
- CQRS, Event Sourcing, Mediator patterns
- Clean Architecture validators
- Framework-specific specialists (MAUI XAML, React Query, FastAPI)
- Domain-specific validators (MVVM compliance, ISP patterns)
- ANY pattern not explicitly coded

### Real-World Impact

**Example: .NET MAUI App with Clean Architecture**
- **Expected**: 7-9 specialized agents (Repository, Engine, Service, MAUI ViewModel, MAUI XAML, Realm, ErrorOr)
- **Actual**: 1 agent generated (erroror-pattern-specialist)
- **Coverage**: ~14% (1 out of 7 needed agents)

**Example: React + FastAPI Monorepo**
- **Expected**: 6-8 agents (React Query, Form Validation, Feature Architecture, FastAPI, Database, Testing)
- **Actual**: 2-3 agents (generic React, FastAPI, testing if lucky)
- **Coverage**: ~30%

**Example: Custom Enterprise Architecture**
- **Expected**: 8-12 agents (domain-specific patterns)
- **Actual**: 0-2 agents (if patterns happen to match hard-coded rules)
- **Coverage**: <20%

### Why This Is a Core Limitation

1. **Maintenance Burden**: Every new pattern requires code changes to agent_generator.py
2. **Scalability**: Cannot handle emerging patterns or technologies
3. **Customization**: Cannot adapt to project-specific architectures
4. **User Experience**: Users get incomplete templates with missing agents
5. **Template Quality**: Generated templates lack necessary domain specialists

### Inconsistency with Template Generation

**Phase 5 (Template Generation)** uses AI to:
- ✅ Analyze code patterns
- ✅ Extract placeholders intelligently
- ✅ Generate comprehensive templates
- ✅ Adapt to any architecture

**Phase 6 (Agent Generation)** uses hard-coded rules to:
- ❌ Check 5 exact string matches
- ❌ Miss 90% of patterns
- ❌ Generate incomplete agent sets
- ❌ Fail for custom architectures

**This inconsistency undermines the entire value proposition of `/template-create`.**

## Solution: AI-Powered Agent Generation

Replace hard-coded pattern detection with **AI-driven analysis** that:
1. Analyzes the complete codebase analysis object
2. Identifies ALL architectural patterns, layers, and frameworks
3. Generates a comprehensive list of needed agents
4. Creates project-specific agents based on actual code examples
5. Eliminates maintenance burden of hard-coded detection rules

### Evidence from Code Review

**File**: [agent_generator.py:120-235](installer/global/lib/agent_generator/agent_generator.py#L120-L235)

```python
def _identify_capability_needs(self, analysis: Any) -> List[CapabilityNeed]:
    needs = []

    # Only 5 hard-coded checks:
    if architecture_pattern == "MVVM":        # Line 141 - exact match only
        needs.append(...)

    if "navigation" in layer_patterns:        # Line 156 - substring match
        needs.append(...)

    if "ErrorOr" in quality_assessment:       # Line 178 - substring match
        needs.append(...)

    if layer_name == "domain":                # Line 201 - exact match only
        needs.append(...)

    if testing_framework:                     # Line 221 - generic
        needs.append(...)

    return sorted(needs, key=lambda n: n.priority, reverse=True)
```

**AI IS already used** in Phase 5 (template generation) and Phase 7 (CLAUDE.md generation) successfully. This task extends that same AI capability to Phase 6 (agent detection).

### Why This Should Be High Priority

1. **User Impact**: Every user of `/template-create` on a complex codebase gets incomplete templates
2. **Value Proposition**: AI-powered template creation is a key differentiator for Taskwright
3. **Quick Win**: AI infrastructure already exists, just need to use it for agent detection
4. **Prevents Manual Work**: Users must manually create 5-10 missing agents after template generation
5. **Quality Consistency**: Phase 5 uses AI (works great), Phase 6 uses hard-coded rules (broken)

### Consistency with System Design Philosophy

From [CLAUDE.md](CLAUDE.md):
> "AI does heavy lifting, humans make decisions"

Currently:
- ❌ Phase 6 has **NO AI** - pure hard-coded rules
- ✅ Phase 5, 2, 7 **use AI** - adaptive and comprehensive

This task restores design consistency.

## Description

Refactor the `AIAgentGenerator` class to use AI for comprehensive agent identification instead of hard-coded pattern matching. The AI should analyze the codebase analysis and generate a complete list of all specialized agents needed for the template.

## Acceptance Criteria

### 1. AI-Powered Agent Identification
- [ ] Create new method `_ai_identify_all_agents(analysis)` that uses AI to analyze codebase
- [ ] AI analyzes: architecture patterns, layers, frameworks, patterns list, and code examples
- [ ] AI returns comprehensive JSON array of all needed agents (not just 5 hard-coded ones)
- [ ] Each agent includes: name, description, reason, technologies, priority

### 2. JSON Response Parsing
- [ ] AI prompt specifies exact JSON format for agent needs
- [ ] Response parser handles JSON array of agent specifications
- [ ] Invalid JSON responses are caught and reported with clear errors
- [ ] Fallback to partial results if some agents fail to parse

### 3. Integration with Existing Workflow
- [ ] Replace `_identify_capability_needs()` with new AI-powered method
- [ ] Maintain backward compatibility with existing gap analysis (`_find_capability_gaps`)
- [ ] Preserve existing agent generation logic (`_generate_agent`)
- [ ] No breaking changes to [template_create_orchestrator.py](installer/global/commands/lib/template_create_orchestrator.py) integration

### 4. AI Prompt Engineering
- [ ] Prompt includes: architecture pattern, patterns list, layers with descriptions, frameworks
- [ ] Prompt explicitly requests agents for EACH pattern, layer, and framework
- [ ] Prompt requests priority scoring (1-10) for each agent
- [ ] Output format is strict JSON array (no markdown wrappers)

### 5. Comprehensive Agent Coverage
- [ ] For complex templates: Generate minimum 7+ agents covering all patterns/layers
- [ ] For MVVM projects: Generate viewmodel, view, and navigation specialists
- [ ] For Clean Architecture: Generate layer-specific specialists (domain, application, infrastructure)
- [ ] For database patterns: Generate database-specific specialists (Realm, EF Core, etc.)

### 6. Quality and Testing
- [ ] Unit tests for `_ai_identify_all_agents()` with mock AI responses
- [ ] Integration test with real codebase analysis from complex project
- [ ] Verify all expected agents are generated for test cases
- [ ] Test handles AI failures gracefully (fallback to hard-coded detection if needed)

## Implementation Notes

### Current Code Location
```
File: installer/global/lib/agent_generator/agent_generator.py
Method: _identify_capability_needs (lines 120-235)
Issue: Hard-coded pattern detection with only 5 agent types
```

### Proposed AI Prompt Structure
```python
def _ai_identify_all_agents(self, analysis: Any) -> List[CapabilityNeed]:
    """
    Use AI to analyze codebase and identify ALL agent needs.
    This eliminates hard-coded pattern detection entirely.
    """

    # Extract data from analysis
    architecture = getattr(analysis, 'architecture_pattern', 'Unknown')
    patterns = getattr(analysis, 'patterns', [])
    layers = getattr(analysis, 'layers', [])
    frameworks = getattr(analysis, 'frameworks', [])
    language = getattr(analysis, 'language', 'Unknown')

    # Build comprehensive prompt
    prompt = f"""
Analyze this codebase and identify ALL specialized AI agents needed for template creation.

**Project Context:**
- Language: {language}
- Architecture: {architecture}
- Patterns: {', '.join(patterns)}
- Layers: {', '.join([f"{l.name} ({', '.join(l.directories)})" for l in layers])}
- Frameworks: {', '.join(frameworks)}

**Requirements:**
1. Generate an agent for EACH architectural pattern listed
2. Generate an agent for EACH layer (Domain, Application, Infrastructure, etc.)
3. Generate an agent for EACH major framework (MAUI, Entity Framework, etc.)
4. Generate specialist agents for key patterns (Repository, Engine, Service, etc.)
5. Include validation agents (architecture validators, compliance checkers)

**Output Format (strict JSON array):**
[
  {{
    "name": "repository-pattern-specialist",
    "description": "Repository pattern with ErrorOr and thread-safety",
    "reason": "Project uses Repository pattern in Infrastructure layer",
    "technologies": ["C#", "Repository Pattern", "ErrorOr", "Realm"],
    "priority": 9
  }},
  {{
    "name": "engine-pattern-specialist",
    "description": "Business logic engines with orchestration",
    "reason": "Project has Application layer with Engines subdirectory",
    "technologies": ["C#", "Engine Pattern"],
    "priority": 9
  }},
  ...
]

Return comprehensive JSON array of ALL agents this project needs. Include minimum 1 agent per pattern/layer/framework.
"""

    # Invoke AI
    response = self.ai_invoker.invoke("architectural-reviewer", prompt)

    # Parse JSON response
    agents_data = json.loads(response)

    # Convert to CapabilityNeed objects
    needs = []
    for agent_spec in agents_data:
        needs.append(CapabilityNeed(
            name=agent_spec['name'],
            description=agent_spec['description'],
            reason=agent_spec['reason'],
            technologies=agent_spec['technologies'],
            example_files=[],  # Will be populated from analysis
            priority=agent_spec.get('priority', 7)
        ))

    return sorted(needs, key=lambda n: n.priority, reverse=True)
```

### Testing Strategy

1. **Unit Tests**: Mock AI responses with known agent lists
2. **Integration Test**: Run against actual complex codebase analysis
3. **Regression Test**: Ensure existing templates still generate correctly
4. **Quality Gate**: Complex templates must generate ≥7 agents

### Backward Compatibility

- Keep `_identify_capability_needs()` as fallback if AI fails
- Add configuration flag: `use_ai_agent_detection=True`
- Graceful degradation: AI fails → fallback to hard-coded → log warning

### Performance Considerations

- Single AI call (not one per agent)
- JSON parsing is fast (no complex markdown parsing)
- Cache AI responses for same codebase analysis (avoid repeated calls)

## Test Requirements

### Unit Tests
- [ ] Test `_ai_identify_all_agents` with mock AI responses
- [ ] Test JSON parsing with valid responses
- [ ] Test JSON parsing with invalid responses (error handling)
- [ ] Test fallback to hard-coded detection on AI failure

### Integration Tests
- [ ] Run against complex codebase analysis
- [ ] Verify ≥7 agents generated for complex projects
- [ ] Verify agent metadata is correct (name, description, technologies)
- [ ] Verify agents are saved to correct directory (.claude/agents/)

### Regression Tests
- [ ] Existing templates still generate correctly
- [ ] Hard-coded fallback works when AI is unavailable
- [ ] Template creation workflow is not broken

## Implementation Checklist

- [ ] Create `_ai_identify_all_agents()` method
- [ ] Design comprehensive AI prompt with JSON output format
- [ ] Implement JSON response parser with error handling
- [ ] Add fallback to hard-coded detection on AI failure
- [ ] Update `generate()` method to use new AI-powered detection
- [ ] Write unit tests for AI method
- [ ] Write integration test with complex codebase analysis
- [ ] Run regression tests on existing templates
- [ ] Update documentation in [agent_generator.py](installer/global/lib/agent_generator/agent_generator.py)
- [ ] Test end-to-end: `/template-create` → verify 7+ agents generated

## Definition of Done

- [ ] Complex template generation creates ≥7 agents (not just 1-2)
- [ ] All patterns in codebase analysis have corresponding generated agents
- [ ] Unit tests pass with 80%+ coverage
- [ ] Integration test passes with real complex codebase analysis
- [ ] No regression in existing template generation
- [ ] Documentation updated in [agent_generator.py](installer/global/lib/agent_generator/agent_generator.py)
- [ ] Code reviewed and approved
- [ ] Changes committed and pushed

## Related Files

- [agent_generator.py](installer/global/lib/agent_generator/agent_generator.py) (primary file)
- [template_create_orchestrator.py](installer/global/commands/lib/template_create_orchestrator.py) (orchestrator)
- `.claude/agents/` (output directory for generated agents)

## Estimated Effort

**Complexity Score**: 8/10 (Complex - AI integration, JSON parsing, backward compatibility)
**Estimated Time**: 6-8 hours
**Risk Level**: Medium (AI reliability, backward compatibility)

## Dependencies

- `architectural-reviewer` agent (for AI invocation)
- `ai_invoker` interface in `AIAgentGenerator`
- JSON parsing library (Python stdlib)
- Existing `CapabilityNeed` and `GeneratedAgent` data classes

## Success Metrics

### Quantitative Improvements

**Current State (Hard-Coded Detection)**:
- Simple projects (MVVM): 2-3 agents (60% coverage)
- Medium projects (Clean Architecture): 1-2 agents (20-30% coverage)
- Complex projects (Multi-pattern): 1 agent (10-15% coverage)
- Detection accuracy: ~30% of needed agents found

**Target State (AI-Powered Detection)**:
- Simple projects: 3-5 agents (90%+ coverage)
- Medium projects: 5-7 agents (85%+ coverage)
- Complex projects: 7-12 agents (95%+ coverage)
- Detection accuracy: 95%+ of needed agents found

### Validation Criteria

**Test Case 1: .NET MAUI Clean Architecture**
- Patterns: MVVM, Repository, Service, Engine, ErrorOr, Realm, XAML
- Current: 1 agent (ErrorOr only)
- Target: 7-8 agents (all patterns covered)

**Test Case 2: React + FastAPI Monorepo**
- Patterns: React Query, Feature-Sliced, FastAPI, SQLAlchemy, Pydantic, Testing
- Current: 2-3 agents
- Target: 6-8 agents

**Test Case 3: Enterprise Custom Architecture**
- Patterns: Domain-specific (varies)
- Current: 0-2 agents (if lucky)
- Target: Comprehensive coverage of all detected patterns

### Quality Measures

- **AI Reliability**: 95%+ success rate in JSON parsing and agent generation
- **Pattern Coverage**: 90%+ of patterns in analysis have corresponding agents
- **Fallback Reliability**: Hard-coded detection works if AI fails
- **No Regressions**: Existing templates (react-typescript, fastapi-python) still generate correctly

## Impact Assessment

### This Is NOT a MyDrive-Specific Issue

While this limitation was discovered during MyDrive template creation, **it affects ALL complex codebases**:

1. **Any Clean Architecture project** - Will miss layer-specific specialists
2. **Any repository pattern** - Won't detect repository agents
3. **Any CQRS/Event Sourcing** - Won't detect command/query/event handlers
4. **Any custom architecture** - Won't detect domain-specific patterns
5. **Any modern framework** - Won't detect framework-specific specialists

The hard-coded rules in [agent_generator.py:120-235](installer/global/lib/agent_generator/agent_generator.py#L120-L235) are **not extensible** without code changes to the core library.

### User Experience Impact

**Without this fix**:
1. User runs `/template-create` on their complex codebase
2. AI analysis correctly identifies 10+ patterns (Phase 2 works)
3. Template files are generated correctly (Phase 5 works)
4. Only 1-2 agents are created (Phase 6 fails - hard-coded detection)
5. User opens `.claude/agents/` and finds it mostly empty
6. User must manually create 5-10 missing agents
7. **User concludes**: "AI template generation doesn't work for complex projects"

**With this fix**:
1. User runs `/template-create` on their complex codebase
2. AI analysis correctly identifies 10+ patterns (Phase 2 works)
3. Template files are generated correctly (Phase 5 works)
4. **7-10 agents are created** (Phase 6 now uses AI - works!)
5. User opens `.claude/agents/` and finds comprehensive agent set
6. User immediately starts using template with full AI assistance
7. **User concludes**: "AI template generation is amazing!"

### Business Value

- **Increases adoption**: Users can create templates from ANY architecture
- **Reduces support burden**: Users don't need help creating missing agents
- **Competitive advantage**: Most template systems don't have AI agent generation at all
- **Scalability**: System adapts to new patterns without code changes
- **Quality perception**: Complete templates = professional tool
