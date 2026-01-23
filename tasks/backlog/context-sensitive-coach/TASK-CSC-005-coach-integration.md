---
id: TASK-CSC-005
title: Integrate with existing CoachValidator
status: backlog
created: 2026-01-23T11:30:00Z
priority: high
tags: [context-sensitive-coach, integration, coach-validator, quality-gates]
task_type: feature
complexity: 5
parent_review: TASK-REV-CSC1
feature_id: FEAT-CSC
wave: 3
implementation_mode: task-work
conductor_workspace: csc-wave3-integration
dependencies:
  - TASK-CSC-003
  - TASK-CSC-004
---

# Task: Integrate with Existing CoachValidator

## Description

Create the `ContextSensitiveCoachValidator` class that orchestrates all components (universal context, fast classifier, AI analyzer, cache) and integrate it with the existing `CoachValidator`.

## Acceptance Criteria

- [ ] `ContextSensitiveCoachValidator` class that orchestrates all components
- [ ] Dynamic profile selection based on context analysis
- [ ] Feature flag for gradual rollout (`GUARDKIT_CONTEXT_SENSITIVE_COACH`)
- [ ] Backward compatibility preserved (existing behavior unchanged when flag off)
- [ ] Logging for profile selection rationale
- [ ] Integration tests with existing CoachValidator

## Implementation Notes

### Location

Create in: `guardkit/orchestrator/quality_gates/context_sensitive_coach.py`

### Dynamic Profiles

```python
DYNAMIC_PROFILES = {
    "minimal": QualityGateProfile(
        arch_review_required=False,
        arch_review_threshold=0,
        coverage_required=False,
        coverage_threshold=0,
        tests_required=False,
        plan_audit_required=True,
    ),
    "light": QualityGateProfile(
        arch_review_required=False,
        arch_review_threshold=0,
        coverage_required=True,
        coverage_threshold=50.0,
        tests_required=True,
        plan_audit_required=True,
    ),
    "standard": QualityGateProfile(
        arch_review_required=True,
        arch_review_threshold=50,
        coverage_required=True,
        coverage_threshold=70.0,
        tests_required=True,
        plan_audit_required=True,
    ),
    "strict": QualityGateProfile(
        arch_review_required=True,
        arch_review_threshold=60,
        coverage_required=True,
        coverage_threshold=80.0,
        tests_required=True,
        plan_audit_required=True,
    ),
}
```

### Profile Selection Logic

```python
def _select_profile(
    self,
    classification: ClassificationResult,
    ai_analysis: Optional[AIAnalysisResult],
) -> Tuple[QualityGateProfile, str]:
    """Select profile based on classification and AI analysis."""

    # Fast path: classification already determined profile
    if not classification.needs_ai_analysis:
        return DYNAMIC_PROFILES[classification.recommended_profile], classification.rationale

    # AI analysis path
    if ai_analysis.testability_score < 20 and ai_analysis.is_declarative:
        return DYNAMIC_PROFILES["minimal"], f"Declarative code ({ai_analysis.testability_score}% testable)"

    if ai_analysis.testability_score < 50:
        return DYNAMIC_PROFILES["light"], f"Low testability ({ai_analysis.testability_score}%)"

    if ai_analysis.arch_review_recommended:
        return DYNAMIC_PROFILES["strict"], f"Complex code requiring arch review"

    return DYNAMIC_PROFILES["standard"], f"Standard code ({ai_analysis.testability_score}% testable)"
```

### ContextSensitiveCoachValidator Interface

```python
class ContextSensitiveCoachValidator:
    """Coach that uses AI-based context analysis for dynamic profile selection."""

    def __init__(
        self,
        worktree_path: str,
        test_command: Optional[str] = None,
        test_timeout: int = 300,
    ):
        self.worktree_path = Path(worktree_path)
        self.context_gatherer = UniversalContextGatherer(worktree_path)
        self.classifier = FastClassifier()
        self.ai_analyzer = AIContextAnalyzer()
        self.cache = ContextCache(worktree_path / ".guardkit", "context")

        # Delegate to base CoachValidator for actual validation
        self._base_validator = CoachValidator(worktree_path, test_command, test_timeout)

    async def validate(
        self,
        task_id: str,
        turn: int,
        task: Dict[str, Any],
    ) -> CoachValidationResult:
        """Validate with context-sensitive profile selection."""

        # 1. Gather universal context
        context = self.context_gatherer.gather()
        logger.info(f"Context: {context.lines_added} LOC, {context.files_created + context.files_modified} files")

        # 2. Fast classification
        classification = self.classifier.classify(context)
        logger.info(f"Classification: {classification.category.value} ({classification.confidence:.0%})")

        # 3. AI analysis if needed
        if classification.needs_ai_analysis:
            cache_key = self.cache.compute_key(context)
            ai_analysis = self.cache.get(cache_key)

            if ai_analysis is None:
                ai_analysis = await self.ai_analyzer.analyze(context, ...)
                self.cache.set(cache_key, ai_analysis, turn)
        else:
            ai_analysis = None

        # 4. Select profile
        profile, rationale = self._select_profile(classification, ai_analysis)
        logger.info(f"Selected profile: {profile.__class__.__name__} - {rationale}")

        # 5. Validate with selected profile (delegate to base)
        # Override the profile in the base validator
        return self._base_validator.validate_with_profile(task_id, turn, task, profile)
```

### Feature Flag Integration

```python
def get_coach_validator(worktree_path: str, ...) -> Union[CoachValidator, ContextSensitiveCoachValidator]:
    """Factory function to get appropriate validator based on feature flag."""
    if os.environ.get("GUARDKIT_CONTEXT_SENSITIVE_COACH", "").lower() == "true":
        return ContextSensitiveCoachValidator(worktree_path, ...)
    return CoachValidator(worktree_path, ...)
```

### Integration with AutoBuild

Update `autobuild.py` to use the factory function:

```python
# In _run_coach_turn
validator = get_coach_validator(self.worktree_path, test_command, test_timeout)
result = await validator.validate(task_id, turn, task)
```

## Testing Strategy

- Unit test profile selection logic with various scenarios
- Integration test with mock components
- Test feature flag behavior (on/off)
- Test backward compatibility (flag off = existing behavior)
- Test logging output for auditability
