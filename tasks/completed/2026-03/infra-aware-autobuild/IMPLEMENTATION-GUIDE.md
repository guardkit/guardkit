# Implementation Guide: FEAT-INFRA

## Wave 1 (Parallel)

### TASK-INFR-6D4F: requires_infrastructure field and propagation
- Add `requires_infrastructure: List[str]` to `FeatureTask` model
- Load from task frontmatter in `autobuild.py:738-742`
- Pass through `_loop_phase` → `_execute_turn` → `task` dict at `autobuild.py:3564`
- Propagate from feature YAML to task frontmatter in `feature_orchestrator.py`
- **Method**: `/task-work TASK-INFR-6D4F`

### TASK-INFR-1670: Tiered classification patterns
- Split `_INFRA_FAILURE_PATTERNS` into `_INFRA_HIGH_CONFIDENCE` + `_INFRA_AMBIGUOUS`
- Change `_classify_test_failure()` return type to `Tuple[str, str]`
- Update all callers for new return type
- Update existing tests, add edge case tests
- **Method**: `/task-work TASK-INFR-1670`

## Wave 2 (Parallel, after Wave 1)

### TASK-INFR-5922: Docker test fixtures (PRIMARY)
- Add infrastructure setup section to `autobuild_execution_protocol.md`
- Add Docker availability check to `CoachValidator`
- Add container lifecycle (start/stop) to `CoachValidator.run_independent_tests()`
- Set environment variables (DATABASE_URL etc.) for tests
- **Method**: `/task-work TASK-INFR-5922`

### TASK-INFR-24DB: Conditional approval fallback
- Add `approved_without_independent_tests` flag to `CoachValidationResult`
- Modify decision path in `coach_validator.py:575-616`
- Only approve when: high-confidence classification + declared deps + Docker unavailable + all other gates pass
- Display distinctly in AutoBuild summary
- **Method**: `/task-work TASK-INFR-24DB`

## Verification

After all 4 tasks complete, re-run the failing scenario:
```bash
guardkit autobuild feature FEAT-BA28 --verbose --max-turns 5
```

Expected: TASK-DB-003 either runs against a Docker PostgreSQL (primary) or gets conditionally approved (fallback), instead of stalling.
