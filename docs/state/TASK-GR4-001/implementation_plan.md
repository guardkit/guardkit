# Implementation Plan: TASK-GR4-001

## Task: Implement KnowledgeGapAnalyzer

### Overview
Create the `KnowledgeGapAnalyzer` class that analyzes existing knowledge in Graphiti to identify gaps and generates targeted questions to fill them.

### Files to Create/Modify

1. **guardkit/knowledge/gap_analyzer.py** (CREATE)
   - `KnowledgeCategory` enum with all categories
   - `KnowledgeGap` dataclass
   - `KnowledgeGapAnalyzer` class with `analyze_gaps()` method

2. **tests/knowledge/test_gap_analyzer.py** (CREATE)
   - Unit tests for KnowledgeGapAnalyzer
   - Tests for analyze_gaps with various focus options
   - Tests for importance sorting
   - Tests for max_questions limit

3. **guardkit/knowledge/__init__.py** (MODIFY)
   - Export new classes: `KnowledgeCategory`, `KnowledgeGap`, `KnowledgeGapAnalyzer`

### Acceptance Criteria
- [ ] `analyze_gaps(focus, max_questions)` returns `List[KnowledgeGap]`
- [ ] Queries Graphiti for existing knowledge
- [ ] Compares against question templates to find gaps
- [ ] Supports focus filtering by category
- [ ] Sorts by importance (high/medium/low)
- [ ] Includes AutoBuild categories (role_customization, quality_gates, workflow_preferences)

### Knowledge Categories
- `project_overview`, `architecture`, `domain`, `constraints`, `decisions`, `goals`
- `role_customization` (NEW - from TASK-REV-1505)
- `quality_gates` (NEW - from TASK-REV-1505)
- `workflow_preferences` (NEW - from TASK-REV-1505)

### Dependencies
- guardkit.knowledge.graphiti_client (get_graphiti)

### Estimated Effort
- Duration: 3 hours
- Lines of Code: ~300

### TDD Phases
1. RED: Write failing tests for KnowledgeGapAnalyzer
2. GREEN: Implement minimum code to pass tests
3. REFACTOR: Clean up and optimize

### Design Approved
- Approved at: 2026-02-01
- Approved by: system (from design_approved state)
