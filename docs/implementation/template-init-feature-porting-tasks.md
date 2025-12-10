# Template-Init Feature Porting: 11 Implementation Tasks

**Parent Review**: TASK-5E55
**Decision**: Option B - Port Features (Approved)
**Timeline**: 5 weeks, 60 hours
**Status**: Ready for implementation

---

## Quick Reference

| Task | Title | Week | Hours | Priority | Dependencies |
|------|-------|------|-------|----------|--------------|
| TASK-INIT-001 | Port boundary sections | 1 | 8 | HIGH | None |
| TASK-INIT-002 | Port agent enhancement tasks | 1 | 6 | HIGH | TASK-INIT-001 |
| TASK-INIT-003 | Port Level 1 validation | 2 | 4 | MEDIUM | None |
| TASK-INIT-004 | Port Level 2 validation | 2 | 4 | MEDIUM | TASK-INIT-003 |
| TASK-INIT-005 | Integrate Level 3 audit | 2 | 4 | MEDIUM | TASK-INIT-004 |
| TASK-INIT-006 | Port quality scoring | 3 | 6 | MEDIUM | TASK-INIT-003-005 |
| TASK-INIT-007 | Port two-location output | 3 | 4 | HIGH | None |
| TASK-INIT-008 | Port discovery metadata | 4 | 4 | MEDIUM | TASK-INIT-001 |
| TASK-INIT-009 | Port exit codes | 4 | 2 | LOW | TASK-INIT-006 |
| TASK-INIT-010 | Update documentation | 5 | 4 | HIGH | All tasks 1-9 |
| TASK-INIT-011 | Comprehensive testing | 5 | 4 | HIGH | All tasks 1-10 |

**Total**: 60 hours across 5 weeks

---

## TASK-INIT-001: Port Boundary Sections ✅ CREATED

**File**: `tasks/backlog/TASK-INIT-001-boundary-sections.md`

See detailed specification above.

---

## TASK-INIT-002: Port Agent Enhancement Task Creation

### Problem Statement
`/template-init` generates agents but doesn't create enhancement tasks, missing the user guidance that `/template-create` provides (TASK-UX-3A8D).

### Implementation Summary
- Add Phase 5 after template save
- Create one JSON task per generated agent
- Display enhancement options (A: `--hybrid`, B: `/task-work`)
- Show boundary sections information
- Support `--no-create-agent-tasks` flag

### Key Code Changes
```python
def _create_agent_enhancement_tasks(self, template_name, agent_files):
    """Create enhancement tasks for generated agents."""
    task_ids = []
    for agent_file in agent_files:
        task_id = f"TASK-AGENT-{datetime.now().strftime('%H%M')}"
        task_data = {
            "id": task_id,
            "title": f"Enhance {agent_file.stem} with boundary sections",
            "metadata": {
                "agent_file": str(agent_file),
                "template_name": template_name
            }
        }
        # Save to tasks/backlog/
        task_ids.append(task_id)
    return task_ids
```

### Acceptance Criteria
- [ ] Phase 5 creates one task per agent
- [ ] Tasks saved to `tasks/backlog/`
- [ ] Enhancement options displayed (A/B)
- [ ] Boundary section info shown
- [ ] Can skip with `--no-create-agent-tasks`

---

## TASK-INIT-003: Port Level 1 Automatic Validation

### Problem Statement
`/template-init` lacks automatic validation (CRUD completeness, layer symmetry) that `/template-create` performs.

### Implementation Summary
- Add validation phase after template generation, before save
- Check CRUD coverage (60% threshold)
- Validate layer symmetry
- Provide auto-fix recommendations
- Display results (warnings don't block)

### Key Code Changes
```python
def _validate_template_completeness(self, template_data):
    """Level 1 automatic validation."""
    # CRUD completeness check
    crud_operations = {'create', 'read', 'update', 'delete'}
    # Check agent capabilities for coverage
    crud_coverage = calculate_coverage(template_data['agents'])

    # Layer symmetry validation
    layers = template_data.get('layers', [])
    # Check for common patterns

    return is_valid, {
        'errors': [],
        'warnings': [],
        'auto_fixes': [],
        'crud_coverage': crud_coverage
    }
```

### Acceptance Criteria
- [ ] CRUD completeness check (60% threshold)
- [ ] Layer symmetry validation
- [ ] Auto-fix recommendations shown
- [ ] Warnings displayed but don't block
- [ ] Validation runs automatically

---

## TASK-INIT-004: Port Level 2 Extended Validation

### Problem Statement
`/template-init` lacks optional extended validation with `--validate` flag and quality reports.

### Implementation Summary
- Add `--validate` flag to constructor
- Run extended checks when flag present
- Generate `validation-report.md`
- Calculate 0-10 score with grade (A-F)
- Check placeholder consistency, pattern fidelity

### Key Code Changes
```python
def __init__(self, validate=False):
    """Initialize with optional validation."""
    self.validate = validate

def _run_level2_validation(self, template_path):
    """Level 2 extended validation."""
    results = {
        'placeholder_consistency': {'score': 0, 'issues': []},
        'pattern_fidelity': {'score': 0, 'issues': []},
        'overall_score': 0,
        'grade': 'F'
    }
    # Check placeholder format consistency
    # Validate architecture pattern match
    # Generate validation-report.md
    return results
```

### Acceptance Criteria
- [ ] `--validate` flag triggers extended validation
- [ ] Report saved as `validation-report.md`
- [ ] Overall score (0-10) calculated
- [ ] Grade assigned (A-F)
- [ ] No impact when flag not used

---

## TASK-INIT-005: Integrate Level 3 Comprehensive Audit

### Problem Statement
`/template-init` templates can't use `/template-validate` command for comprehensive audits.

### Implementation Summary
- Ensure template structure matches `/template-validate` requirements
- Add required manifest fields
- Create `.validation-compatible` marker
- Display `/template-validate` usage guidance

### Key Code Changes
```python
def _ensure_validation_compatibility(self, template_path):
    """Ensure template works with /template-validate."""
    # Ensure required directories
    (template_path / "templates").mkdir(exist_ok=True)
    (template_path / "agents").mkdir(exist_ok=True)

    # Add required manifest fields
    manifest['schema_version'] = '1.0.0'
    manifest['complexity'] = 5
    manifest['confidence_score'] = 75

    # Create compatibility marker
    (template_path / ".validation-compatible").write_text("1.0.0")
```

### Acceptance Criteria
- [ ] Generated templates have required structure
- [ ] Manifest includes validation fields
- [ ] `/template-validate` works with templates
- [ ] Validation guidance displayed
- [ ] Compatibility marker created

---

## TASK-INIT-006: Port Quality Scoring and Reports

### Problem Statement
`/template-init` doesn't generate quality scores or reports, missing the 0-10 scoring system.

### Implementation Summary
- Add `QualityScorer` class
- Calculate scores from Q&A answers (not code analysis)
- Score: architecture, testing, error handling, docs, agents, patterns
- Generate `quality-report.md`
- Display summary after creation

### Key Code Changes
```python
class QualityScorer:
    """Calculate template quality score."""

    def calculate_score(self, template_data):
        """Calculate 0-10 quality score."""
        scores = {
            'architecture_clarity': score_from_pattern(template_data),
            'testing_coverage': score_from_test_types(template_data),
            'error_handling': score_from_strategy(template_data),
            # ... more components
        }
        overall = sum(scores.values()) / len(scores)
        return {
            'overall_score': overall,
            'grade': calculate_grade(overall),
            'production_ready': overall >= 7
        }
```

### Acceptance Criteria
- [ ] Quality score calculated (0-10)
- [ ] Letter grade assigned (A+ to F)
- [ ] Production readiness assessment
- [ ] `quality-report.md` generated
- [ ] Score summary displayed

---

## TASK-INIT-007: Port Two-Location Output Support

### Problem Statement
`/template-init` only saves to one location vs. `/template-create`'s two locations (personal/repo).

### Implementation Summary
- Add `--output-location global|repo` flag
- Default to `global` (~/.agentecflow/templates/)
- Support `repo` (installer/core/templates/)
- Display location-specific guidance

### Key Code Changes
```python
def __init__(self, output_location='global'):
    """Initialize with output location."""
    self.output_location = output_location

def _get_template_path(self, template_name):
    """Get path based on location setting."""
    if self.output_location == 'repo':
        return Path('installer/core/templates') / template_name
    else:
        return Path.home() / '.agentecflow' / 'templates' / template_name
```

### Acceptance Criteria
- [ ] `--output-location` flag accepts global|repo
- [ ] Default is global
- [ ] repo saves to installer/core/templates/
- [ ] Location-specific guidance displayed
- [ ] Backward compatible

---

## TASK-INIT-008: Port Discovery Metadata to Agents

### Problem Statement
`/template-init` generates agents without discovery metadata (stack, phase, capabilities, keywords).

### Implementation Summary
- Add frontmatter to generated agents
- Include stack, phase, capabilities, keywords
- Map from Q&A answers to metadata
- Technology-specific metadata

### Key Code Changes
```python
def _generate_agent_metadata(self, agent_type):
    """Generate discovery metadata for agent."""
    metadata = {
        'stack': [],  # From language/framework Q&A
        'phase': 'implementation',
        'capabilities': [],  # Agent-type specific
        'keywords': []
    }
    # Map Q&A answers to metadata
    return metadata

def _format_agent_with_metadata(self, agent_content, metadata):
    """Add frontmatter to agent markdown."""
    frontmatter = [
        "---",
        f"stack: {metadata['stack']}",
        f"phase: {metadata['phase']}",
        # ... more fields
        "---"
    ]
    return "\n".join(frontmatter) + agent_content
```

### Acceptance Criteria
- [ ] Agents include frontmatter
- [ ] Metadata has stack/phase/capabilities/keywords
- [ ] Derived from Q&A answers
- [ ] Matches template-create format
- [ ] Agents still valid markdown

---

## TASK-INIT-009: Port Exit Codes

### Problem Statement
`/template-init` doesn't return quality-based exit codes for CI/CD integration.

### Implementation Summary
- Modify `run()` to return (answers, exit_code)
- Exit codes: 0 (≥8), 1 (6-7.9), 2 (<6), 3+ (errors)
- Add main() entry point
- Display exit code meaning

### Key Code Changes
```python
def run(self):
    """Run Q&A and return answers with exit code."""
    # ... existing logic ...

    # Calculate exit code from quality score
    if scores['overall_score'] >= 8:
        exit_code = 0
    elif scores['overall_score'] >= 6:
        exit_code = 1
    else:
        exit_code = 2

    return self.answers, exit_code

def main():
    """Entry point with exit code handling."""
    session = TemplateInitQASession()
    answers, exit_code = session.run()
    sys.exit(exit_code)
```

### Acceptance Criteria
- [ ] Exit code 0 for high quality (≥8)
- [ ] Exit code 1 for medium (6-7.9)
- [ ] Exit code 2 for low (<6)
- [ ] Exit code meaning displayed
- [ ] CI/CD can use for quality gates

---

## TASK-INIT-010: Update Documentation

### Problem Statement
Documentation doesn't reflect new features, leaving users unaware of capabilities.

### Implementation Summary
- Update command options section
- Document all 13 ported features
- Add examples for new flags
- Update workflow phases
- Document exit codes

### Key Changes
```markdown
## Command Options

--output-location LOC    Where to save template
--validate               Run extended validation
--no-create-agent-tasks  Skip task creation

## Features (NEW)

### Boundary Sections
All agents include ALWAYS/NEVER/ASK sections...

### Quality Scoring
Automatic 0-10 scoring...

### Validation Levels
Level 1, 2, 3 available...

## Exit Codes

0 - High quality (≥8/10)
1 - Medium quality (6-7.9/10)
2 - Low quality (<6/10)
```

### Acceptance Criteria
- [ ] All ported features documented
- [ ] Command options complete
- [ ] Exit codes documented
- [ ] Workflow phases updated
- [ ] Examples work as documented

---

## TASK-INIT-011: Comprehensive Testing

### Problem Statement
Ported features need comprehensive testing to ensure correctness and prevent regressions.

### Implementation Summary
- Create `tests/test_template_init/test_enhancements.py`
- Unit tests for each feature
- Integration tests for feature interaction
- Regression tests for existing functionality
- Achieve 80%+ coverage

### Test Coverage
```python
class TestBoundarySections:
    def test_generate_boundary_sections_testing_agent()
    def test_validate_boundary_sections_valid()
    def test_validate_boundary_sections_invalid_count()

class TestAgentEnhancementTasks:
    def test_create_agent_enhancement_tasks()

class TestValidation:
    def test_level1_validation_crud_coverage()
    def test_level2_validation_with_flag()

class TestQualityScoring:
    def test_quality_score_calculation()
    def test_quality_report_generation()

class TestOutputLocations:
    def test_global_output_location()
    def test_repo_output_location()

class TestDiscoveryMetadata:
    def test_generate_agent_metadata_python()

class TestExitCodes:
    def test_exit_code_high_quality()
    def test_exit_code_low_quality()

class TestRegression:
    def test_existing_qa_workflow_unchanged()
    def test_backward_compatibility_no_flags()
```

### Acceptance Criteria
- [ ] All ported features have tests
- [ ] Test coverage ≥80% for new code
- [ ] All regression tests pass
- [ ] Tests use mocks/temp directories
- [ ] CI/CD can run tests

---

## Implementation Strategy

### Week-by-Week Approach

**Week 1** (14 hours): Critical features that users see immediately
- TASK-INIT-001: Boundary sections (most visible improvement)
- TASK-INIT-002: Agent tasks (immediate next steps)

**Week 2** (12 hours): Quality infrastructure
- TASK-INIT-003: Level 1 validation (automatic)
- TASK-INIT-004: Level 2 validation (optional)
- TASK-INIT-005: Level 3 integration (compatibility)

**Week 3** (10 hours): Quality and distribution
- TASK-INIT-006: Quality scoring (metrics)
- TASK-INIT-007: Two locations (team distribution)

**Week 4** (6 hours): Advanced features
- TASK-INIT-008: Discovery metadata (agent matching)
- TASK-INIT-009: Exit codes (CI/CD)

**Week 5** (8 hours): Polish
- TASK-INIT-010: Documentation (user awareness)
- TASK-INIT-011: Testing (quality assurance)

### Parallel Execution Opportunities

Can run in parallel:
- Week 2: All 3 validation tasks (independent)
- Week 3: Both tasks (independent)
- Week 4: Both tasks (independent after TASK-INIT-001, TASK-INIT-006)

### Quality Gates

After each week:
- All tests pass
- No regressions in existing Q&A
- Feature demo/review
- Decision: Continue or pause

---

## Success Metrics

### Overall Goals
- [ ] 100% feature parity with /template-create
- [ ] 0 breaking changes to existing Q&A
- [ ] <5% performance impact
- [ ] 90%+ test coverage
- [ ] All 11 tasks completed

### User Impact
- [ ] Generated templates score ≥8/10
- [ ] Boundary sections in all agents
- [ ] Enhancement tasks provide clear guidance
- [ ] Validation catches quality issues
- [ ] Teams can distribute templates easily

---

## Risk Management

### Overall Mitigation Strategy
1. **Phased rollout**: Can pause after any week
2. **Feature flags**: Can toggle features if issues arise
3. **Backward compatibility**: Old workflows keep working
4. **Comprehensive testing**: Each phase tested thoroughly
5. **Clear scope**: Minimal changes to prevent regressions

### Emergency Rollback
If critical issues:
1. Revert last commit
2. Disable new features via flags
3. Fix forward instead of rollback
4. Document lessons learned

---

## References

- **Parent Review**: TASK-5E55
- **Decision Document**: docs/decisions/template-init-vs-template-create-analysis.md
- **Source Command**: installer/core/commands/template-create.md
- **Target Files**: installer/core/commands/lib/greenfield_qa_session.py (984 lines)
