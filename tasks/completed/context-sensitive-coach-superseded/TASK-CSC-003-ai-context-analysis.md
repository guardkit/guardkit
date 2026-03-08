---
id: TASK-CSC-003
title: Implement AI context analysis
status: backlog
created: 2026-01-23T11:30:00Z
priority: high
tags: [context-sensitive-coach, ai-analysis, testability, quality-gates]
task_type: feature
complexity: 5
parent_review: TASK-REV-CSC1
feature_id: FEAT-CSC
wave: 2
implementation_mode: task-work
conductor_workspace: csc-wave2-analyzer
dependencies:
  - TASK-CSC-001
---

# Task: Implement AI Context Analysis

## Description

Implement the AI-based context analysis that determines code testability and patterns. This is invoked only for "uncertain" cases (30-300 LOC) that need deeper analysis.

## Acceptance Criteria

- [ ] `AIContextAnalyzer` class with `analyze()` method
- [ ] Well-defined analysis prompt that works across languages
- [ ] Response parsing with validation
- [ ] Testability score extraction (0-100)
- [ ] Pattern detection (declarative, logic, wiring, etc.)
- [ ] Fallback to standard profile on AI errors
- [ ] Unit tests with mock AI responses

## Implementation Notes

### Location

Create in: `guardkit/orchestrator/quality_gates/context_analysis/ai_analyzer.py`

### Analysis Prompt

```python
CONTEXT_ANALYSIS_PROMPT = """
Analyze this code implementation for quality gate validation.

CHANGED FILES:
{diff_summary}

FILE CONTENTS (relevant excerpts):
{file_contents}

Answer these questions as JSON:
1. "testability_score": What percentage of this code is meaningfully unit-testable? (0-100)
   - 0: Pure configuration/declarative (DTOs, records, enums)
   - 30-50: Mostly wiring/initialization with some logic
   - 60-80: Mixed logic and configuration
   - 90-100: Pure business logic with branching

2. "patterns": What code patterns are present?
   - "declarative_config": Data classes, DTOs, records
   - "app_initialization": Framework setup, DI registration
   - "business_logic": Methods with if/else, loops, calculations
   - "data_access": Database queries, API calls
   - "wiring": Import/export, routing, middleware

3. "is_declarative": Is this primarily declarative/configuration code? (true/false)

4. "arch_review_recommended": Should architectural review be applied? (true/false)
   - Yes for: Complex logic, multi-file changes, design patterns
   - No for: Simple config, single-purpose utilities, tests

5. "rationale": Brief explanation of assessment (1-2 sentences)

Respond ONLY with valid JSON, no markdown.
"""
```

### AIContextAnalyzer Interface

```python
@dataclass
class AIAnalysisResult:
    testability_score: int  # 0-100
    patterns: List[str]
    is_declarative: bool
    arch_review_recommended: bool
    rationale: str
    raw_response: str

class AIContextAnalyzer:
    async def analyze(
        self,
        context: UniversalContext,
        diff_summary: str,
        file_contents: str,
    ) -> AIAnalysisResult:
        """Analyze implementation using AI."""
        ...

    def _prepare_file_contents(self, context: UniversalContext, max_chars: int = 8000) -> str:
        """Extract relevant file contents for analysis."""
        ...

    def _parse_response(self, response: str) -> AIAnalysisResult:
        """Parse and validate AI response."""
        ...
```

### AI Invocation

Use existing agent infrastructure. Prefer fast model (Haiku) for lower latency:

```python
# Use Task tool internally or direct API call
response = await self._invoke_ai(
    prompt=formatted_prompt,
    model="haiku",  # Fast model for context analysis
    max_tokens=500,
)
```

### Error Handling

```python
try:
    result = await self.analyze(context, diff, contents)
except AIAnalysisError:
    # Fallback to standard profile on any AI error
    return AIAnalysisResult(
        testability_score=50,  # Neutral
        patterns=["unknown"],
        is_declarative=False,
        arch_review_recommended=True,  # Conservative
        rationale="AI analysis failed, using conservative defaults",
    )
```

## Testing Strategy

- Test prompt formatting with various diff sizes
- Test response parsing with valid/invalid JSON
- Test error handling and fallback behavior
- Mock AI responses for deterministic tests
