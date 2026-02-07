# Implementation Checklist: TASK-GBF-001

**Task:** Unify episode serialization pattern across entities
**Status:** Ready for Implementation
**Estimated Duration:** 2-2.5 hours
**Risk Level:** Low

---

## Pre-Implementation

- [ ] **Review all design documents**
  - [ ] ADR-GBF-001 (architecture decision)
  - [ ] DESIGN-GBF-001 (comprehensive design)
  - [ ] DESIGN-GBF-001-visual-architecture.md (diagrams)
  - [ ] DESIGN-SUMMARY-GBF-001.md (executive summary)

- [ ] **Verify assumptions**
  - [ ] GraphitiClient.add_episode() can accept `source`, `entity_type`, `entity_id` parameters
  - [ ] No external code calls `_add_episodes()` directly
  - [ ] `GraphitiClient._inject_metadata()` implementation reviewed

- [ ] **Set up testing environment**
  - [ ] Test infrastructure ready
  - [ ] Run existing test suite to establish baseline

---

## Phase 1: Entity Serialization Cleanup (40 minutes)

### TaskOutcome Entity
- [ ] File: `guardkit/knowledge/entities/outcome.py`
  - [ ] Change `to_episode_body()` return type from `str` to `dict`
  - [ ] Convert human-readable text to structured dict with all fields:
    - [ ] `id`
    - [ ] `outcome_type` (serialized as `.value`)
    - [ ] `task_id`
    - [ ] `task_title`
    - [ ] `task_requirements`
    - [ ] `success`
    - [ ] `summary`
    - [ ] `approach_used`
    - [ ] `patterns_used`
    - [ ] `problems_encountered`
    - [ ] `lessons_learned`
    - [ ] `tests_written`
    - [ ] `test_coverage`
    - [ ] `review_cycles`
    - [ ] `started_at` (serialized as ISO 8601 string or None)
    - [ ] `completed_at` (serialized as ISO 8601 string or None)
    - [ ] `duration_minutes`
    - [ ] `feature_id`
    - [ ] `related_adr_ids`
  - [ ] NO metadata fields in returned dict
  - [ ] Update docstring
  - [ ] Update type hints

### TurnStateEntity
- [ ] File: `guardkit/knowledge/entities/turn_state.py`
  - [ ] Remove `"entity_type": "turn_state"` from returned dict
  - [ ] Verify all domain fields present
  - [ ] Verify enum serialized as `.value` (e.g., `mode.value` → "fresh_start")
  - [ ] Verify datetime serialized as ISO 8601 string (via `.isoformat()`)
  - [ ] Update docstring
  - [ ] Update type hints

### FailedApproachEpisode
- [ ] File: `guardkit/knowledge/entities/failed_approach.py`
  - [ ] Remove `"entity_type": "failed_approach"` from returned dict
  - [ ] Verify all domain fields present
  - [ ] Verify enum serialized as `.value` (severity.value)
  - [ ] Verify datetime serialized as ISO 8601 string
  - [ ] Update docstring
  - [ ] Update type hints

### FeatureOverviewEntity
- [ ] File: `guardkit/knowledge/entities/feature_overview.py`
  - [ ] Remove `"entity_type": "feature_overview"` from returned dict
  - [ ] Remove `"created_at": ...` from returned dict
  - [ ] Remove `"updated_at": ...` from returned dict
  - [ ] Verify all domain fields present
  - [ ] Update docstring
  - [ ] Update type hints

### QualityGateConfigFact
- [ ] File: `guardkit/knowledge/facts/quality_gate_config.py`
  - [ ] Remove `"entity_type": "quality_gate_config"` from returned dict
  - [ ] Keep `version`, `effective_from`, and `supersedes` (domain fields)
  - [ ] Verify datetime serialized as ISO 8601 string
  - [ ] Update docstring
  - [ ] Update type hints

### RoleConstraintFact
- [ ] File: `guardkit/knowledge/facts/role_constraint.py`
  - [ ] Remove `"entity_type": "role_constraint"` from returned dict
  - [ ] Remove `"created_at": ...` from returned dict (if present)
  - [ ] Keep all constraint fields (domain data)
  - [ ] Update docstring
  - [ ] Update type hints

### Phase 1 Verification
- [ ] Run tests: `pytest tests/unit/test_*.py -v` (baseline)
- [ ] No test failures introduced
- [ ] All entity methods return `dict`
- [ ] No `str` returns from `to_episode_body()`

---

## Phase 2: Seeding Helper Cleanup (20 minutes)

### File: `guardkit/knowledge/seed_helpers.py`

- [ ] **Understand current implementation**
  - [ ] Review `_add_episodes()` function signature
  - [ ] Review manual `_metadata` dict construction
  - [ ] Review double injection problem

- [ ] **Update function signature**
  - [ ] Change episodes parameter format from 2-tuple to 4-tuple
  - [ ] Each episode: `(name, body_dict, entity_type, entity_id)`

- [ ] **Update implementation**
  - [ ] Remove manual `_metadata` dict construction
  - [ ] Remove timestamp generation from function
  - [ ] Remove `source_hash: None` assignment
  - [ ] Pass clean `body_dict` to `json.dumps()`
  - [ ] Add `source`, `entity_type`, `entity_id` parameters to `add_episode()` call

- [ ] **Update docstring**
  - [ ] Document new 4-tuple format
  - [ ] Explain that client handles metadata injection
  - [ ] Update Args section with new parameter format
  - [ ] Add example showing 4-tuple structure

- [ ] **Phase 2 Verification**
  - [ ] Code review of changes
  - [ ] Docstring is clear and accurate
  - [ ] No manual metadata dict construction remains

---

## Phase 3: Update Seeding Call Sites (30 minutes)

### File: `guardkit/knowledge/seed_failed_approaches.py`

- [ ] **Find `_add_episodes()` call**
  - [ ] Locate where episodes list is created
  - [ ] Current format: list of (name, body)

- [ ] **Update episode construction**
  - [ ] Change to 4-tuple: `(failed_approach.id, body_dict, "failed_approach", failed_approach.id)`
  - [ ] Ensure body_dict is clean (from `to_episode_body()`)
  - [ ] Set entity_type to "failed_approach" (string)
  - [ ] Set entity_id to unique identifier (e.g., `failed_approach.id`)

- [ ] **Verify call**
  - [ ] `_add_episodes()` called with correct episode list format
  - [ ] No manual metadata dict construction

### File: `guardkit/knowledge/seed_feature_overviews.py`

- [ ] **Find `_add_episodes()` call**
  - [ ] Locate where episodes list is created

- [ ] **Update episode construction**
  - [ ] Change to 4-tuple: `(overview.id, body_dict, "feature_overview", overview.id)`
  - [ ] Ensure body_dict is clean (from `to_episode_body()`)
  - [ ] Set entity_type to "feature_overview"
  - [ ] Set entity_id to unique identifier

### Other Seed Files (if applicable)

- [ ] **Check for other `_add_episodes()` calls**
  - [ ] Search: `grep -r "_add_episodes" guardkit/knowledge/seed_*.py`
  - [ ] Update any other seed files found
  - [ ] Follow same pattern as above

- [ ] **Verify all seeding files updated**
  - [ ] seed_failed_approaches.py ✓
  - [ ] seed_feature_overviews.py ✓
  - [ ] seed_agents.py (if exists) [ ]
  - [ ] seed_architecture_decisions.py (if exists) [ ]
  - [ ] seed_command_workflows.py (if exists) [ ]
  - [ ] seed_component_status.py (if exists) [ ]
  - [ ] seed_failure_patterns.py (if exists) [ ]
  - [ ] seed_integration_points.py (if exists) [ ]
  - [ ] seed_patterns.py (if exists) [ ]
  - [ ] seed_product_knowledge.py (if exists) [ ]
  - [ ] seed_project_architecture.py (if exists) [ ]
  - [ ] seed_project_overview.py (if exists) [ ]
  - [ ] seed_quality_gate_phases.py (if exists) [ ]
  - [ ] seed_rules.py (if exists) [ ]
  - [ ] seed_technology_stack.py (if exists) [ ]
  - [ ] seed_templates.py (if exists) [ ]

### Phase 3 Verification
- [ ] Run tests: `pytest tests/unit/test_seeding*.py -v`
- [ ] No test failures
- [ ] All seeding call sites updated to 4-tuple format
- [ ] No manual metadata dict construction in seed files

---

## Phase 4: Update Manager Call Sites (20 minutes)

### File: `guardkit/knowledge/failed_approach_manager.py`

- [ ] **Find `add_episode()` calls**
  - [ ] Search for all calls to `client.add_episode()`
  - [ ] Identify current parameters

- [ ] **Add metadata parameters**
  - [ ] Add `source="..."` parameter (e.g., "failed_approach_manager")
  - [ ] Add `entity_type="failed_approach"` parameter
  - [ ] Add `entity_id=...` parameter (unique identifier)

- [ ] **Verify episode body is clean**
  - [ ] Confirm `to_episode_body()` returns dict without metadata
  - [ ] No manual metadata dict construction

### File: `guardkit/knowledge/outcome_manager.py`

- [ ] **Find `add_episode()` calls**
  - [ ] Search for all calls to `client.add_episode()`
  - [ ] Identify current parameters

- [ ] **Handle TaskOutcome dict return**
  - [ ] TaskOutcome now returns dict (not str)
  - [ ] Update code to handle dict: `body_dict = outcome.to_episode_body()`
  - [ ] Call `json.dumps(body_dict)` when passing to `add_episode()`

- [ ] **Add metadata parameters**
  - [ ] Add `source="..."` parameter
  - [ ] Add `entity_type="task_outcome"` parameter
  - [ ] Add `entity_id=...` parameter

### Other Manager Files (if applicable)

- [ ] **Search for other managers**
  - [ ] `grep -r "add_episode" guardkit/knowledge/*_manager.py`
  - [ ] Update any other manager files found
  - [ ] Follow same pattern as above

- [ ] **Verify all managers updated**
  - [ ] failed_approach_manager.py ✓
  - [ ] outcome_manager.py ✓
  - [ ] turn_state_manager.py (if exists) [ ]
  - [ ] feature_overview_manager.py (if exists) [ ]
  - [ ] quality_gate_config_manager.py (if exists) [ ]
  - [ ] role_constraint_manager.py (if exists) [ ]

### Phase 4 Verification
- [ ] Run tests: `pytest tests/unit/test_*_manager.py -v`
- [ ] No test failures
- [ ] All manager `add_episode()` calls have metadata parameters
- [ ] TaskOutcome dict handling correct

---

## Phase 5: Add Consistency Tests (30 minutes)

### Create Test File
- [ ] File: `tests/unit/test_episode_serialization.py` (NEW)

### Test 1: All Entities Return Dict
- [ ] Test name: `test_all_entities_return_dict_from_to_episode_body`
- [ ] Create minimal instances of all entity types
- [ ] Call `to_episode_body()` on each
- [ ] Assert all return `dict` type
- [ ] Assert no return type is `str`
- [ ] Assert dicts are not empty

### Test 2: No Metadata Fields in Bodies
- [ ] Test name: `test_entity_bodies_contain_no_metadata_fields`
- [ ] Define METADATA_FIELDS set:
  - [ ] "entity_type"
  - [ ] "_metadata"
  - [ ] "source"
  - [ ] "version"
  - [ ] "source_hash"
- [ ] For each entity type:
  - [ ] Create instance
  - [ ] Call `to_episode_body()`
  - [ ] Assert no metadata fields in body keys
  - [ ] Provide helpful error message if found

### Test 3: DateTime Serialization
- [ ] Test name: `test_entity_datetime_fields_serialized_to_iso8601`
- [ ] For entities with datetime fields (TaskOutcome, TurnStateEntity, etc):
  - [ ] Create instance with specific datetime
  - [ ] Call `to_episode_body()`
  - [ ] Assert datetime field is string
  - [ ] Assert string is in ISO 8601 format (contains "T")
  - [ ] Assert value matches expected ISO format

### Test 4: Enum Serialization
- [ ] Test name: `test_entity_enum_fields_serialized_to_strings`
- [ ] For entities with enum fields:
  - [ ] OutcomeType: Create TaskOutcome with OutcomeType.TASK_COMPLETED
  - [ ] TurnMode: Create TurnStateEntity with TurnMode.FRESH_START
  - [ ] Severity: Create FailedApproachEpisode with Severity.CRITICAL
  - [ ] Call `to_episode_body()`
  - [ ] Assert enum field is string (e.g., "TASK_COMPLETED")
  - [ ] Assert value matches enum.value

### Test 5: Optional Fields Handling
- [ ] Test name: `test_entity_optional_fields_properly_serialized`
- [ ] For entities with optional fields:
  - [ ] Create instance with optional field as None
  - [ ] Call `to_episode_body()`
  - [ ] Assert optional field in dict
  - [ ] Assert value is None (not omitted)
  - [ ] Create instance with optional field set
  - [ ] Assert value properly serialized

### Phase 5 Verification
- [ ] All tests created
- [ ] Run tests: `pytest tests/unit/test_episode_serialization.py -v`
- [ ] All tests pass
- [ ] Coverage reports reviewed
- [ ] No failures in other tests

---

## Phase 6: Final Verification (20 minutes)

### Full Test Suite
- [ ] Run all tests: `pytest tests/unit/ -v`
- [ ] No test failures
- [ ] No regressions introduced
- [ ] Coverage maintained or improved

### Code Quality
- [ ] Type hints correct
  - [ ] `to_episode_body() -> dict` (all entities)
  - [ ] No `-> str` returns
  - [ ] Type hints in docstrings match implementation

- [ ] Docstrings complete
  - [ ] All modified methods have docstrings
  - [ ] Docstrings explain domain-only return
  - [ ] Docstrings explain metadata injection by client
  - [ ] No docstring mentions manual metadata injection

- [ ] No remaining metadata fields
  - [ ] Search: `grep -r "entity_type" guardkit/knowledge/entities/`
  - [ ] Should find ZERO matches in entity `to_episode_body()` methods
  - [ ] Search: `grep -r "\"_metadata\"" guardkit/knowledge/entities/`
  - [ ] Should find ZERO matches in entity methods

### Documentation Update
- [ ] Update CLAUDE.md if needed (list of patterns)
- [ ] Update README.md if needed (serialization patterns)
- [ ] Update code comments if needed

### Code Review Preparation
- [ ] Gather all changes
- [ ] Create summary of changes
- [ ] List files modified
- [ ] List tests added
- [ ] Prepare code review request

---

## Sign-Off & Completion

### Pre-Review Checks
- [ ] All phases complete
- [ ] All tests passing
- [ ] No regressions
- [ ] Documentation updated
- [ ] Changes aligned with design documents

### Code Review
- [ ] Request review from architecture team
- [ ] Provide links to design documents (ADR + visual architecture)
- [ ] Explain changes to reviewers
- [ ] Address feedback/questions
- [ ] Achieve approval

### Completion
- [ ] All review feedback addressed
- [ ] Final test run passes
- [ ] Task marked as COMPLETED
- [ ] Update task frontmatter:
  - [ ] `status: completed`
  - [ ] `updated: <current ISO timestamp>`
  - [ ] Add completion notes

### Post-Implementation
- [ ] Archive design documents (move to docs/completed-designs/)
- [ ] Update team wiki with new pattern
- [ ] Send completion notification to team
- [ ] Document any lessons learned

---

## Troubleshooting Guide

### Issue: Type Checker Errors

**Problem:** Type checker complains about dict vs str return types

**Solution:**
1. Run `mypy` to find exact location
2. Verify return type annotation is `-> dict`
3. Verify all code paths return dict (not str)
4. Add type ignore comments if necessary (rare)

### Issue: Import Errors

**Problem:** Tests fail with import errors after changes

**Solution:**
1. Verify all import paths are correct
2. Check for circular imports
3. Run `python -m pytest --collect-only` to verify test discovery
4. Clear Python cache: `find . -type d -name __pycache__ -exec rm -r {} +`

### Issue: Graphiti Client Not Found

**Problem:** `GraphitiClient.add_episode()` doesn't accept new parameters

**Solution:**
1. Check current `add_episode()` signature
2. Update signature to accept: `source`, `entity_type`, `entity_id`
3. Implement parameter handling in method
4. Update docstring with new parameters

### Issue: Test Failures After Phase Changes

**Problem:** Tests fail after modifying entities but before updating call sites

**Solution:**
1. Expected behavior during incremental implementation
2. Ensure changes are aligned across phases
3. Verify entity changes are complete before updating call sites
4. Run tests after each phase completion

### Issue: Double Metadata in Graphiti

**Problem:** After changes, episodes still have double metadata

**Solution:**
1. Verify seeding helper changes complete
2. Verify no manual metadata dict construction remains
3. Check GraphitiClient._inject_metadata() is only called once
4. Add debug logging to trace metadata injection

---

## Quick Reference: File Changes Summary

| Phase | Files | Changes |
|-------|-------|---------|
| 1 | 6 entity/fact files | Remove metadata fields from `to_episode_body()` |
| 2 | 1 seeding helper | Remove manual metadata injection |
| 3 | 6 seed_*.py files | Update 4-tuple format in episode construction |
| 4 | 2 manager files | Add entity_type to `add_episode()` calls |
| 5 | 1 test file (NEW) | Add consistency tests |
| **TOTAL** | **15-16 files** | |

---

## Estimated Time Breakdown

| Phase | Task | Estimate |
|-------|------|----------|
| Pre | Review + Setup | 15 min |
| 1 | Entity cleanup | 40 min |
| 2 | Seeding helper | 20 min |
| 3 | Seeding call sites | 30 min |
| 4 | Manager call sites | 20 min |
| 5 | Tests | 30 min |
| 6 | Verification | 20 min |
| **TOTAL** | | **2.5-3 hours** |

---

**Implementation Checklist Complete**

Begin implementation with Phase 1. Mark items as completed as you progress.
Good luck!
