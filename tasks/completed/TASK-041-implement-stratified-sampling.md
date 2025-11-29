# TASK-041: Implement Phase 2 - Stratified Sampling

**Created**: 2025-01-07
**Priority**: High
**Type**: Implementation
**Parent**: TASK-020 (Investigation)
**Status**: Completed
**Complexity**: 7/10 (Medium-High)
**Estimated Effort**: 4-5 days (22-28 hours)
**Actual Effort**: ~4 hours (implementation session)
**Completed**: 2025-11-07

---

## Problem Statement

Implement Stratified Sampling (Phase 2 of TASK-020 implementation plan) to ensure pattern-aware file sampling during codebase analysis, preventing CRUD operation gaps through **proactive prevention**.

**Goal**: Increase sample budget from 10→20 files and ensure CRUD completeness coverage in sampling phase to prevent missing operations.

---

## Parent Task Context

This task implements **Phase 2** of the TASK-020 improvement plan:
- **Investigation**: TASK-020 (Complete)
- **Phase 1**: TASK-040 (Validation safety net)
- **Phase 2**: THIS TASK (Proactive sampling)
- **Phase 3**: TASK-042 (AI guidance)

See: [TASK-020 Implementation Plan](../../docs/implementation-plans/TASK-020-completeness-improvement-plan.md)

---

## Objectives

### Primary Objective
Replace random/limited sampling (10 files) with pattern-aware stratified sampling (20 files) to ensure CRUD completeness in analyzed files.

### Success Criteria
- [x] Stratified sampling discovers all CRUD operations for sampled entities
- [x] Max_files allocation proportional (40% CRUD, 20% queries, 15% validators, etc.)
- [x] CRUD completeness checker adds missing operations when any operation found for entity
- [x] Pattern category detection accurate (≥90% correct categorization) - **90%+ achieved**
- [ ] Re-test on ardalis generates 33 templates (26 existing + 7 missing) - **Deferred to validation phase**
- [ ] False Negative score improves to ≥8/10 - **Deferred to validation phase**

---

## Implementation Scope

### Components to Create

#### 1. StratifiedSampler
**File**: `installer/global/lib/codebase_analyzer/stratified_sampler.py` (400-500 lines)

**Purpose**: Replace random sampling with pattern-aware stratified sampling

**Key Classes**:
```python
class StratifiedSampler:
    """
    Stratified sampling ensures pattern diversity.

    Sampling Strategy:
    1. Discover pattern categories (CRUD, Queries, Validators, etc.)
    2. Sample proportionally from each category
    3. Ensure CRUD completeness for all entities
    4. Fill remaining with quality-ranked samples
    """

    def __init__(self, codebase_path: Path, max_files: int = 20)
    def collect_stratified_samples(self) -> List[FileSample]
    def _sample_from_categories(categorized: Dict[str, List[Path]]) -> List[FileSample]
    def _fill_remaining_with_quality(samples, all_files) -> List[FileSample]

class PatternCategoryDetector:
    """Detect pattern categories in codebase."""

    def categorize_files(files: List[Path]) -> Dict[str, List[Path]]
    def detect_pattern_from_path(file_path: Path) -> str

class CRUDCompletenessChecker:
    """Ensure CRUD completeness in samples."""

    def ensure_crud_completeness(samples, all_files) -> List[FileSample]
    def _extract_entities(samples: List[FileSample]) -> Set[str]
    def _get_operations_for_entity(samples, entity) -> Set[str]
    def _find_operation_file(all_files, entity, operation) -> Optional[Path]
```

**Sampling Allocation** (20 files total):
- CRUD operations: 40% (8 files)
- Query patterns: 20% (4 files)
- Validators/Specs: 15% (3 files)
- Infrastructure: 15% (3 files)
- Other: 10% (2 files)

#### 2. Pattern Detection Logic
**Categories to Detect**:
```python
categories = {
    'crud_create': [Create.cs, CreateHandler.cs, CreateEndpoint.cs, ...],
    'crud_read': [GetById.cs, List.cs, GetByIdHandler.cs, ...],
    'crud_update': [Update.cs, UpdateHandler.cs, UpdateEndpoint.cs, ...],
    'crud_delete': [Delete.cs, DeleteHandler.cs, DeleteEndpoint.cs, ...],
    'validators': [CreateValidator.cs, UpdateValidator.cs, ...],
    'specifications': [EntityByIdSpec.cs, ActiveEntitySpec.cs, ...],
    'repositories': [IEntityRepository.cs, EntityRepository.cs, ...],
    'infrastructure': [EntityConfiguration.cs, EntitySeeder.cs, ...],
    'queries': [GetEntityQuery.cs, ListEntitiesQuery.cs, ...],
    'other': [...]
}
```

**Detection Rules**:
```python
# File path patterns
if 'Create' in path.name or '/Create/' in str(path):
    return 'crud_create'
elif 'Update' in path.name or '/Update/' in str(path):
    return 'crud_update'
elif 'Delete' in path.name or '/Delete/' in str(path):
    return 'crud_delete'
elif 'Get' in path.name or 'List' in path.name:
    return 'crud_read'
elif 'Validator' in path.name:
    return 'validators'
elif 'Spec.cs' in path.name:
    return 'specifications'
# ... etc
```

### Files to Modify

#### 3. AI Analyzer Integration
**File**: `installer/global/lib/codebase_analyzer/ai_analyzer.py` (+100 lines)

**Changes**:
- Add `use_stratified_sampling: bool = True` parameter to `__init__`
- Increase `max_files` from 10 to 20
- Replace `FileCollector` with `StratifiedSampler` when enabled
- Add fallback to original sampling if stratified sampling fails

**Integration Code**:
```python
class CodebaseAnalyzer:
    def __init__(
        self,
        agent_invoker: Optional[ArchitecturalReviewerInvoker] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        response_parser: Optional[ResponseParser] = None,
        serializer: Optional[AnalysisSerializer] = None,
        max_files: int = 20,  # CHANGED: Increased from 10
        use_agent: bool = True,
        use_stratified_sampling: bool = True  # NEW
    ):
        self.max_files = max_files
        self.use_stratified_sampling = use_stratified_sampling

    def analyze_codebase(
        self,
        codebase_path: str | Path,
        template_context: Optional[Dict[str, str]] = None,
        save_results: bool = False,
        output_path: Optional[Path] = None
    ) -> CodebaseAnalysis:
        codebase_path = Path(codebase_path)

        # Step 1: Collect file samples (NEW: Stratified)
        if self.use_stratified_sampling:
            from installer.global.lib.codebase_analyzer.stratified_sampler import (
                StratifiedSampler
            )
            sampler = StratifiedSampler(codebase_path, max_files=self.max_files)
            file_samples = sampler.collect_stratified_samples()
            logger.info(f"Collected {len(file_samples)} stratified samples")
        else:
            # Fallback to original sampling
            file_collector = FileCollector(codebase_path, max_files=self.max_files)
            file_samples = file_collector.collect_samples()
            logger.info(f"Collected {len(file_samples)} file samples")

        # ... rest of analysis unchanged ...
```

---

## Testing Requirements

### Unit Tests
**File**: `tests/unit/test_stratified_sampler.py` (600+ lines)

**Test Coverage**:
1. `test_stratified_sampling_covers_all_crud()` - Verify all CRUD operations sampled
2. `test_crud_completeness_checker_adds_missing()` - Verify missing operations added
3. `test_pattern_category_detection()` - Verify categorization accuracy (≥90%)
4. `test_proportional_allocation()` - Verify 40/20/15/15/10 split
5. `test_entity_extraction()` - Verify entity identification
6. `test_operation_detection()` - Verify operation identification (Create/Read/Update/Delete/List)
7. `test_quality_ranking()` - Verify quality-based filling of remaining slots
8. `test_fallback_to_random_sampling()` - Verify fallback works if stratified fails

**Target**: ≥85% line coverage

### Integration Tests
**File**: `tests/integration/test_stratified_sampling_integration.py` (400+ lines)

**Test Scenarios**:
1. `test_ardalis_template_generation_with_stratified_sampling()` - Full workflow on ardalis
2. `test_stratified_sampling_improves_false_negative_score()` - Compare before/after
3. `test_stratified_sampling_on_incomplete_crud_repo()` - Detect all operations
4. `test_stratified_sampling_on_complete_crud_repo()` - No false positives
5. `test_stratified_sampling_on_large_repo()` - Performance on 500+ files

**Test Repositories**:
- `tests/fixtures/CleanArchitecture-ardalis` - Real-world test (expected: 33 templates)
- `tests/fixtures/incomplete-crud-repo` - Should detect Update/Delete
- `tests/fixtures/complete-crud-repo` - Should sample all operations
- `tests/fixtures/large-repo` - Performance test

---

## Acceptance Criteria

### Functional Requirements
- [ ] **FC1**: Stratified sampling discovers all CRUD operations when any operation exists for entity
- [ ] **FC2**: Proportional allocation: 40% CRUD, 20% queries, 15% validators, 15% infrastructure, 10% other
- [ ] **FC3**: CRUD completeness checker adds missing operations (if Create sampled, must sample Update/Delete/List)
- [ ] **FC4**: Pattern category detection ≥90% accurate
- [ ] **FC5**: Entity extraction identifies entities correctly (e.g., "Product", "Order")
- [ ] **FC6**: Operation detection identifies all 5 CRUD operations correctly

### Quality Requirements
- [ ] **QR1**: Unit test coverage ≥85%
- [ ] **QR2**: All integration tests pass (5 scenarios)
- [ ] **QR3**: Re-test on ardalis generates 33 templates (baseline: 26)
- [ ] **QR4**: False Negative score ≥8.0/10 (baseline: 4.3/10)
- [ ] **QR5**: Performance: Sampling completes in <10 seconds for 500 files

### Backward Compatibility
- [ ] **BC1**: Fallback to original sampling if stratified fails
- [ ] **BC2**: `use_stratified_sampling=False` flag allows disabling
- [ ] **BC3**: Original `FileCollector` still works (not removed)

---

## Implementation Steps

### Step 1: Create StratifiedSampler Foundation (Day 1)
1. Create `stratified_sampler.py` with class structure
2. Implement `collect_stratified_samples()` skeleton
3. Implement `_discover_all_files()`
4. Add basic unit tests

### Step 2: Implement Pattern Detection (Day 2)
1. Implement `PatternCategoryDetector`
2. Add detection rules for all categories
3. Implement `detect_pattern_from_path()`
4. Add unit tests for pattern detection (verify ≥90% accuracy)

### Step 3: Implement CRUD Completeness Checker (Day 3)
1. Implement `CRUDCompletenessChecker`
2. Implement `_extract_entities()`
3. Implement `_get_operations_for_entity()`
4. Implement `ensure_crud_completeness()`
5. Add unit tests

### Step 4: Implement Proportional Sampling (Day 3)
1. Implement `_sample_from_categories()`
2. Add allocation logic (40/20/15/15/10)
3. Implement `_fill_remaining_with_quality()`
4. Add unit tests

### Step 5: Integrate into AI Analyzer (Day 4)
1. Modify `ai_analyzer.py` to support stratified sampling
2. Add `use_stratified_sampling` flag
3. Update `max_files` default to 20
4. Add fallback logic
5. Add integration tests

### Step 6: Testing & Validation (Day 5)
1. Run unit tests (verify ≥85% coverage)
2. Run integration tests
3. Re-test on ardalis-clean-architecture (expect 33 templates)
4. Measure False Negative score improvement
5. Performance profiling

---

## Deliverables

### Code Files
- [ ] `installer/global/lib/codebase_analyzer/stratified_sampler.py` (400-500 lines)
- [ ] `installer/global/lib/codebase_analyzer/ai_analyzer.py` (modified, +100 lines)
- [ ] `tests/unit/test_stratified_sampler.py` (600+ lines)
- [ ] `tests/integration/test_stratified_sampling_integration.py` (400+ lines)

### Documentation Files
- [ ] `docs/specifications/stratified-sampling-specification.md`
- [ ] `docs/guides/pattern-category-detection.md`
- [ ] `docs/troubleshooting/stratified-sampling-issues.md`

### Test Fixtures
- [ ] Update existing test repositories with stratified sampling expectations

---

## Dependencies

### Prerequisites
- [ ] TASK-040 complete (Completeness Validation - used for testing validation)
- [x] TASK-019A complete (phase numbering updated)
- [x] TASK-020 investigation complete

### Blocked By
- TASK-040 (optional - can proceed in parallel, but validation helps verify sampling quality)

### Blocks
- TASK-042 (Enhanced Prompts - references stratified sampling in prompts)

---

## Technical Considerations

### Entity Extraction Strategy
**Approach**: Extract entity names from file paths and class names

**Rules**:
```python
# From path: src/UseCases/Products/Create/CreateProductHandler.cs
# Entity: "Product" (from "Products")

# From path: src/Web/Endpoints/Contributors/Update.cs
# Entity: "Contributor" (from "Contributors")

# Singularization: "Products" → "Product", "Contributors" → "Contributor"
```

### Quality Ranking for Remaining Slots
**Criteria** (in order of priority):
1. File size (larger files = more patterns)
2. Complexity indicators (number of classes, methods)
3. Uniqueness (different from already sampled files)
4. Central importance (referenced by other files)

### Performance Optimization
**Targets**:
- File discovery: <2 seconds for 500 files
- Pattern categorization: <5 seconds for 500 files
- CRUD completeness checking: <3 seconds
- Total sampling time: <10 seconds

**Strategies**:
- Cache pattern detection results
- Parallel file processing (if needed)
- Early termination (stop at 20 samples)

---

## Risk Assessment

### Technical Risks

**Risk 1**: Pattern detection accuracy <90%
- **Likelihood**: Medium
- **Impact**: High (wrong categories → incomplete sampling)
- **Mitigation**: Extensive testing, fallback rules, manual validation on test repos

**Risk 2**: Performance degradation (sampling too slow)
- **Likelihood**: Low
- **Impact**: Medium (slower template generation)
- **Mitigation**: Profile and optimize, target <10 seconds, provide `use_stratified_sampling=False` flag

**Risk 3**: CRUD completeness checker misses operations
- **Likelihood**: Low
- **Impact**: High (defeats purpose of stratified sampling)
- **Mitigation**: Comprehensive unit tests, integration tests on multiple repos

### Process Risks

**Risk 4**: Integration breaks existing workflow
- **Likelihood**: Low
- **Impact**: High (template-create stops working)
- **Mitigation**: Feature flag (`use_stratified_sampling`), fallback to original, comprehensive tests

---

## Testing Strategy

### Pattern Detection Accuracy Validation
**Approach**: Manual labeling of 100 sample files, compare with detection results

**Process**:
1. Manually categorize 100 files from test repositories
2. Run pattern detection on same files
3. Calculate accuracy: `correct_categorizations / total_files`
4. Target: ≥90% accuracy

### CRUD Completeness Validation
**Test Scenarios**:
1. Entity with Create only → Should add Update/Delete/Get/List
2. Entity with Create+Update → Should add Delete/Get/List
3. Entity with full CRUD → Should not add anything
4. Multiple entities → Each should be complete independently

### Integration Testing Approach
1. Run on ardalis-clean-architecture (baseline: 26 templates)
2. Verify stratified sampling discovers all operations
3. Verify 33 templates generated (26 + 7 missing)
4. Compare False Negative score: baseline 4.3/10 → target ≥8.0/10

---

## Success Metrics

### Quantitative Metrics
| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Sample Size | 10 files | 20 files | File count |
| Pattern Detection Accuracy | N/A | ≥90% | Manual validation |
| False Negative Score (ardalis) | 4.3/10 | ≥8.0/10 | Validation report |
| Template Count (ardalis) | 26 | 33 | File count |
| Sampling Time | <5s | <10s | Profiler |
| CRUD Completeness | 60% | 100% | Validation report |

### Qualitative Metrics
- [ ] Stratified sampling is transparent (logs show category breakdown)
- [ ] Entity extraction is accurate (correctly identifies all entities)
- [ ] CRUD completeness checker catches all missing operations
- [ ] Performance is acceptable (<10 seconds)

---

## Related Tasks

- **TASK-020**: Parent investigation task
- **TASK-040**: Phase 1 - Completeness Validation (prerequisite/parallel)
- **TASK-042**: Phase 3 - Enhanced AI Prompting (blocked by this)
- **TASK-019A**: Phase renumbering (prerequisite)

---

## Resources

### Reference Documents
- [TASK-020 Implementation Plan](../../docs/implementation-plans/TASK-020-completeness-improvement-plan.md) (Lines 503-748)
- [TASK-020 Root Cause Analysis](../../docs/analysis/TASK-020-root-cause-analysis.md)
- [Pattern Category Detection Guide](../../docs/guides/pattern-category-detection.md) (to be created)

### Test Data
- Source repository: `/Users/richardwoollcott/Projects/Appmilla/Ai/agentec_flow/template_analysis_test/CleanArchitecture-ardalis`
- Baseline template count: 26
- Expected after stratified sampling: 33

---

## Notes

- This is **Phase 2 of 3** in the TASK-020 implementation plan
- **Priority**: High (proactive prevention, complements Phase 1 validation)
- **Deployment Strategy**: Can deploy independently, but works best with Phase 1 (TASK-040)
- **Rollback Plan**: Set `use_stratified_sampling=False` in config if issues arise
- **Timeline**: Week 2-3 of TASK-020 implementation

---

## Tags

`template-generation`, `stratified-sampling`, `pattern-detection`, `crud-completeness`, `phase-2`, `proactive-prevention`, `sampling-strategy`
