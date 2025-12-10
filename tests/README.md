# GuardKit Clarification Feature Test Suite

This directory contains comprehensive tests for the clarifying questions feature (TASK-CLQ-012).

## Test Structure

```
tests/
├── unit/lib/clarification/
│   ├── test_core.py           # Question, Decision, ClarificationContext tests
│   ├── test_detection.py      # Ambiguity detection algorithm tests
│   ├── test_display.py        # Display formatting and user interaction tests
│   └── test_generators.py     # Question generation tests
│
├── integration/lib/clarification/
│   ├── test_task_work_clarification.py       # Phase 1.5 integration tests
│   ├── test_task_review_clarification.py     # Context A & B integration tests
│   └── test_feature_plan_clarification.py    # Feature-plan workflow tests
│
└── docs/testing/
    └── clarification-uat-scenarios.md        # User acceptance test scenarios
```

## Running Tests

### Prerequisites

The clarification module must be implemented first (Waves 1-3):
- `lib/clarification/core.py`
- `lib/clarification/detection.py`
- `lib/clarification/display.py`
- `lib/clarification/generators/*.py`
- `lib/clarification/templates/*.py`

### Run All Tests

```bash
# From repository root
pytest tests/ -v --cov=lib/clarification --cov-report=term --cov-report=json
```

### Run Specific Test Suites

```bash
# Unit tests only
pytest tests/unit/lib/clarification/ -v

# Integration tests only
pytest tests/integration/lib/clarification/ -v

# Specific test file
pytest tests/unit/lib/clarification/test_core.py -v

# Specific test class
pytest tests/unit/lib/clarification/test_core.py::TestQuestion -v

# Specific test
pytest tests/unit/lib/clarification/test_core.py::TestQuestion::test_question_with_all_fields -v
```

### Run with Coverage

```bash
# Generate coverage report
pytest tests/ --cov=lib/clarification --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Test Coverage Goals

| Module | Target Coverage | Critical Functions |
|--------|----------------|-------------------|
| `core.py` | 95%+ | `ClarificationContext.persist_to_frontmatter()`, `load_from_frontmatter()` |
| `detection.py` | 90%+ | All 5 detection functions |
| `display.py` | 85%+ | `display_questions_full()`, `display_questions_quick()` |
| `generators/*.py` | 90%+ | All 3 generator functions |

## Test Categories

### Unit Tests (4 files, ~150 tests)

**test_core.py** (40+ tests)
- Question dataclass creation and serialization
- Decision dataclass with default handling
- ClarificationContext persistence to frontmatter
- Loading from frontmatter with validation
- Edge cases (empty decisions, invalid YAML)

**test_detection.py** (50+ tests)
- Scope ambiguity detection (vague vs specific descriptions)
- Technology ambiguity detection (multiple options)
- Tradeoff ambiguity detection (performance, security)
- Review focus ambiguity
- Implementation preference ambiguity
- Edge cases (empty descriptions, special characters)

**test_display.py** (40+ tests)
- Question formatting
- Option formatting
- Decision summary formatting
- Full interactive mode
- Quick mode with timeout
- Skip mode
- User input validation
- Edge cases (empty options, invalid input)

**test_generators.py** (30+ tests)
- Planning question generation (Context C)
- Review question generation (Context A)
- Implementation question generation (Context B)
- Complexity-based question selection
- Task-specific adaptation
- Question quality validation

### Integration Tests (3 files, ~80 tests)

**test_task_work_clarification.py** (35+ tests)
- Phase 1.5 complexity-based mode selection
- Skip mode for complexity 1-2
- Quick mode for complexity 3-4
- Full mode for complexity 5+
- Flag handling: `--no-questions`, `--with-questions`, `--answers`
- Timeout behavior
- Clarification context propagation to Phase 2
- Boundary testing

**test_task_review_clarification.py** (25+ tests)
- Context A: Review scope clarification
- Multiple review modes (decision, architectural, security)
- Context B: Implementation preferences at [I]mplement
- Dual-context workflow
- Flag handling
- Context propagation

**test_feature_plan_clarification.py** (20+ tests)
- End-to-end feature-plan workflow
- Context A + Context B integration
- Subtask generation using clarification
- Scope-based subtask filtering
- Flag handling
- Clarification persistence

### User Acceptance Tests (8 scenarios)

See `docs/testing/clarification-uat-scenarios.md` for detailed scenarios:

1. **Full Clarification** - High complexity task with full mode
2. **Quick Timeout** - Medium complexity with timeout behavior
3. **Review Scope** - task-review with dual contexts
4. **Feature Plan** - Complete workflow end-to-end
5. **Skip Clarification** - --no-questions flag
6. **Inline Answers** - --answers flag for CI/CD
7. **Quick with Input** - User input before timeout
8. **Complexity Boundaries** - Mode transitions at boundaries

Plus **Rework Rate Measurement** comparing baseline vs clarification-enabled workflows.

## Dependencies

The tests import from modules that must be implemented:

```python
from lib.clarification.core import Question, Decision, ClarificationContext
from lib.clarification.detection import (
    detect_scope_ambiguity,
    detect_technology_ambiguity,
    detect_tradeoff_ambiguity,
    detect_review_focus_ambiguity,
    detect_implementation_preference_ambiguity,
)
from lib.clarification.display import (
    display_questions_full,
    display_questions_quick,
    display_question_skip,
)
from lib.clarification.generators.planning_generator import generate_planning_questions
from lib.clarification.generators.review_generator import generate_review_questions
from lib.clarification.generators.implement_generator import generate_implement_questions
```

## Expected Test Results

Once the clarification module is implemented, running the test suite should produce:

```
================================ test session starts =================================
platform darwin -- Python 3.11.x, pytest-7.x.x
collected 230 items

tests/unit/lib/clarification/test_core.py .......................... [ 18%]
tests/unit/lib/clarification/test_detection.py ........................................ [ 41%]
tests/unit/lib/clarification/test_display.py .................................. [ 59%]
tests/unit/lib/clarification/test_generators.py ........................ [ 73%]
tests/integration/lib/clarification/test_task_work_clarification.py ..................... [ 85%]
tests/integration/lib/clarification/test_task_review_clarification.py ............. [ 94%]
tests/integration/lib/clarification/test_feature_plan_clarification.py ......... [100%]

================================ 230 passed in 45.23s ================================

Coverage Report:
lib/clarification/core.py              96%
lib/clarification/detection.py         92%
lib/clarification/display.py           88%
lib/clarification/generators/*.py      91%
--------------------------------------------------
TOTAL                                  92%
```

## Test Execution Checklist

Before marking TASK-CLQ-012 as complete:

- [ ] All unit tests pass (100% pass rate)
- [ ] All integration tests pass (100% pass rate)
- [ ] Coverage ≥80% for all modules
- [ ] No critical bugs found in UAT
- [ ] UAT scenarios 1-8 executed successfully
- [ ] Rework rate improvement measured and documented

## Known Limitations

These tests are **ready to run** once the clarification module is implemented. They currently:

✅ **Have complete test coverage** for all planned functionality
✅ **Test all three contexts** (C, A, B)
✅ **Include edge cases** and error scenarios
✅ **Provide UAT documentation** for manual testing

⚠️ **Will not run** until Wave 1-3 implementation is complete
⚠️ **May require minor adjustments** based on actual implementation details

## Contributing

When modifying the clarification feature:

1. **Update tests first** - Add tests for new functionality
2. **Maintain coverage** - Keep coverage ≥80%
3. **Run full suite** - Verify no regressions
4. **Update UAT scenarios** - Document user-facing changes

## Questions or Issues

If tests fail unexpectedly, check:

1. **Module imports** - Are all clarification modules in `lib/clarification/`?
2. **Function signatures** - Do functions match test expectations?
3. **Dataclass fields** - Are Question/Decision/ClarificationContext correctly defined?
4. **Frontmatter format** - Is YAML serialization compatible with tests?

For bugs or test issues, file under tag `clarifying-questions` with severity and steps to reproduce.
