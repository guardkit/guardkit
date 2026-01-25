# Context-Sensitive Coach: Design Proposal

**Status**: Research/Proposal
**Created**: 2026-01-23
**Related**: TASK-REV-FB22, TASK-REV-FB21
**Author**: AI-assisted design exploration

## Executive Summary

This document proposes a context-sensitive Coach validator that adapts quality gate thresholds based on what was actually implemented, rather than applying fixed thresholds based solely on task_type. The goal is to eliminate false positives where simple, legitimate implementations fail strict quality gates designed for complex features.

## Problem Statement

The current quality gate system is binary:

```python
TaskType.FEATURE: QualityGateProfile(
    arch_review_required=True,
    arch_review_threshold=60,
    coverage_required=True,
    coverage_threshold=80.0,
    tests_required=True,
)
```

This means a 20-line FastAPI app initialization (`main.py`) faces the same validation as a 500-line authentication system. Real-world observations show:

- Simple configuration classes (Pydantic Settings) fail arch review
- App initialization code can't achieve 80% coverage (nothing to test)
- Declarative code has no meaningful unit tests to write

### Evidence from TASK-REV-FB22

| Task | Complexity | LOC | Pattern | Failed Gate |
|------|------------|-----|---------|-------------|
| FHA-002 | 3 | ~30 | Declarative config | Arch review (score 0 < 60) |
| FHA-003 | 2 | ~20 | App initialization | Arch review + coverage |

## Proposed Solution: Context-Sensitive Coach

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│               Context-Sensitive CoachValidator              │
├─────────────────────────────────────────────────────────────┤
│ Inputs (existing):                                          │
│   - task_id, task metadata, task_work_results.json          │
│                                                             │
│ NEW Inputs (context gathering):                             │
│   - Git diff analysis (what changed)                        │
│   - Code metrics (LOC, cyclomatic complexity, etc.)         │
│   - Pattern detection (declarative, wiring, logic)          │
│   - Dependency analysis (isolated vs interconnected)        │
│                                                             │
│ Decision Logic:                                             │
│   1. Gather implementation context                          │
│   2. Classify implementation scope                          │
│   3. Select appropriate validation profile                  │
│   4. Evaluate gates with adjusted expectations              │
│   5. Provide contextual rationale                           │
│                                                             │
│ Output: approve | feedback (with reasoning)                 │
└─────────────────────────────────────────────────────────────┘
```

### Phase 1: Context Gathering

Coach gathers context about what was actually implemented:

```python
@dataclass
class ImplementationContext:
    """Context about what Player actually implemented."""

    # Code volume metrics
    total_lines_added: int
    total_lines_modified: int
    files_created: int
    files_modified: int

    # Code complexity metrics
    max_cyclomatic_complexity: int
    avg_cyclomatic_complexity: float
    has_branching_logic: bool
    has_error_handling: bool

    # Pattern classification
    code_patterns: List[str]  # e.g., ["declarative", "configuration", "wiring"]
    dominant_pattern: str     # e.g., "declarative" or "business_logic"

    # Dependency analysis
    external_dependencies: int
    internal_imports: int
    is_isolated: bool  # No dependencies on other project code

    # Test context
    test_files_created: int
    test_lines_added: int
    testable_lines: int  # Lines that could meaningfully be tested
```

#### Context Gatherer Implementation

```python
class ContextGatherer:
    """Gathers implementation context from git diff and static analysis."""

    def gather(self, worktree_path: Path, task_id: str) -> ImplementationContext:
        # 1. Git diff analysis
        diff_stats = self._analyze_git_diff(worktree_path)

        # 2. Static code analysis (using AST or simple parsing)
        code_metrics = self._analyze_code_metrics(worktree_path, diff_stats.changed_files)

        # 3. Pattern detection
        patterns = self._detect_patterns(worktree_path, diff_stats.changed_files)

        # 4. Dependency analysis
        deps = self._analyze_dependencies(worktree_path, diff_stats.changed_files)

        return ImplementationContext(
            total_lines_added=diff_stats.lines_added,
            total_lines_modified=diff_stats.lines_modified,
            files_created=diff_stats.files_created,
            files_modified=diff_stats.files_modified,
            max_cyclomatic_complexity=code_metrics.max_complexity,
            avg_cyclomatic_complexity=code_metrics.avg_complexity,
            has_branching_logic=code_metrics.has_branching,
            has_error_handling=code_metrics.has_try_except,
            code_patterns=patterns.detected,
            dominant_pattern=patterns.dominant,
            external_dependencies=deps.external_count,
            internal_imports=deps.internal_count,
            is_isolated=deps.is_isolated,
            test_files_created=diff_stats.test_files,
            test_lines_added=diff_stats.test_lines,
            testable_lines=code_metrics.testable_lines,
        )
```

### Phase 2: Implementation Scope Classification

Based on gathered context, classify the implementation:

```python
class ScopeClassifier:
    """Classifies implementation scope for appropriate validation."""

    @dataclass
    class ScopeClassification:
        category: str  # "trivial", "simple", "moderate", "complex", "critical"
        confidence: float
        rationale: str
        recommended_profile: str

    def classify(self, context: ImplementationContext, task_metadata: dict) -> ScopeClassification:
        # Score different dimensions
        volume_score = self._score_volume(context)
        complexity_score = self._score_complexity(context)
        pattern_score = self._score_patterns(context)
        risk_score = self._score_risk(context, task_metadata)

        # Weighted combination
        overall_score = (
            volume_score * 0.2 +
            complexity_score * 0.35 +
            pattern_score * 0.25 +
            risk_score * 0.2
        )

        # Classify based on score
        if overall_score < 20:
            return ScopeClassification(
                category="trivial",
                confidence=0.9,
                rationale=self._build_rationale(context, "trivial"),
                recommended_profile="minimal",
            )
        elif overall_score < 40:
            return ScopeClassification(
                category="simple",
                confidence=0.85,
                rationale=self._build_rationale(context, "simple"),
                recommended_profile="light",
            )
        elif overall_score < 60:
            return ScopeClassification(
                category="moderate",
                confidence=0.8,
                rationale=self._build_rationale(context, "moderate"),
                recommended_profile="standard",
            )
        elif overall_score < 80:
            return ScopeClassification(
                category="complex",
                confidence=0.8,
                rationale=self._build_rationale(context, "complex"),
                recommended_profile="strict",
            )
        else:
            return ScopeClassification(
                category="critical",
                confidence=0.85,
                rationale=self._build_rationale(context, "critical"),
                recommended_profile="maximum",
            )
```

#### Scoring Functions

```python
def _score_volume(self, ctx: ImplementationContext) -> float:
    """Score based on code volume (0-100)."""
    if ctx.total_lines_added < 30:
        return 10  # Trivial
    elif ctx.total_lines_added < 100:
        return 30  # Small
    elif ctx.total_lines_added < 300:
        return 50  # Moderate
    elif ctx.total_lines_added < 500:
        return 70  # Large
    else:
        return 90  # Very large

def _score_complexity(self, ctx: ImplementationContext) -> float:
    """Score based on code complexity (0-100)."""
    score = 0

    # Cyclomatic complexity
    if ctx.max_cyclomatic_complexity > 10:
        score += 40
    elif ctx.max_cyclomatic_complexity > 5:
        score += 20

    # Branching logic
    if ctx.has_branching_logic:
        score += 25

    # Error handling (indicates complexity)
    if ctx.has_error_handling:
        score += 15

    # Multiple files (architectural scope)
    if ctx.files_created > 3:
        score += 20

    return min(score, 100)

def _score_patterns(self, ctx: ImplementationContext) -> float:
    """Score based on code patterns (0-100)."""
    low_complexity_patterns = ["declarative", "configuration", "wiring", "boilerplate"]
    high_complexity_patterns = ["business_logic", "algorithm", "state_machine", "async_flow"]

    if ctx.dominant_pattern in low_complexity_patterns:
        return 15
    elif ctx.dominant_pattern in high_complexity_patterns:
        return 75
    else:
        return 45  # Neutral

def _score_risk(self, ctx: ImplementationContext, task_metadata: dict) -> float:
    """Score based on risk factors (0-100)."""
    score = 0

    # Tags indicating risk
    risky_tags = ["security", "authentication", "payment", "database", "migration"]
    task_tags = task_metadata.get("tags", [])
    if any(tag in risky_tags for tag in task_tags):
        score += 40

    # External dependencies (attack surface)
    if ctx.external_dependencies > 5:
        score += 30

    # Not isolated (could affect other code)
    if not ctx.is_isolated:
        score += 20

    return min(score, 100)
```

### Phase 3: Dynamic Profile Selection

Instead of static profiles per task_type, select based on classification:

```python
@dataclass
class DynamicProfile:
    """Quality gate profile with contextual adjustments."""

    arch_review_required: bool
    arch_review_threshold: int
    coverage_required: bool
    coverage_threshold: float
    min_testable_coverage: float  # Only count testable lines
    tests_required: bool
    integration_tests_acceptable: bool  # Can pass with integration tests only
    plan_audit_required: bool

    rationale: str  # Why these thresholds were chosen

DYNAMIC_PROFILES = {
    "minimal": DynamicProfile(
        arch_review_required=False,
        arch_review_threshold=0,
        coverage_required=False,
        coverage_threshold=0,
        min_testable_coverage=0,
        tests_required=False,
        integration_tests_acceptable=True,
        plan_audit_required=True,
        rationale="Trivial implementation - minimal validation sufficient",
    ),
    "light": DynamicProfile(
        arch_review_required=False,
        arch_review_threshold=0,
        coverage_required=True,
        coverage_threshold=50.0,
        min_testable_coverage=70.0,
        tests_required=True,
        integration_tests_acceptable=True,
        plan_audit_required=True,
        rationale="Simple implementation - light validation appropriate",
    ),
    "standard": DynamicProfile(
        arch_review_required=True,
        arch_review_threshold=50,
        coverage_required=True,
        coverage_threshold=70.0,
        min_testable_coverage=80.0,
        tests_required=True,
        integration_tests_acceptable=False,
        plan_audit_required=True,
        rationale="Moderate implementation - standard validation",
    ),
    "strict": DynamicProfile(
        arch_review_required=True,
        arch_review_threshold=60,
        coverage_required=True,
        coverage_threshold=80.0,
        min_testable_coverage=85.0,
        tests_required=True,
        integration_tests_acceptable=False,
        plan_audit_required=True,
        rationale="Complex implementation - strict validation required",
    ),
    "maximum": DynamicProfile(
        arch_review_required=True,
        arch_review_threshold=70,
        coverage_required=True,
        coverage_threshold=85.0,
        min_testable_coverage=90.0,
        tests_required=True,
        integration_tests_acceptable=False,
        plan_audit_required=True,
        rationale="Critical implementation - maximum validation required",
    ),
}
```

### Phase 4: Contextual Coverage Evaluation

Evaluate **testable code**, not total code:

```python
class ContextualCoverageEvaluator:
    """Evaluates coverage in context of what's actually testable."""

    def evaluate(
        self,
        context: ImplementationContext,
        profile: DynamicProfile,
        reported_coverage: float,
    ) -> CoverageResult:

        # If no testable lines, coverage gate is meaningless
        if context.testable_lines == 0:
            return CoverageResult(
                passed=True,
                actual_coverage=reported_coverage,
                required_coverage=0,
                rationale="No testable lines detected (declarative/configuration code)",
                adjusted=True,
            )

        # Calculate coverage of testable code only
        if context.testable_lines < context.total_lines_added:
            testable_ratio = context.testable_lines / context.total_lines_added
            adjusted_threshold = profile.coverage_threshold * testable_ratio

            return CoverageResult(
                passed=reported_coverage >= adjusted_threshold,
                actual_coverage=reported_coverage,
                required_coverage=adjusted_threshold,
                rationale=f"Adjusted threshold from {profile.coverage_threshold}% to {adjusted_threshold:.1f}% "
                         f"({context.testable_lines}/{context.total_lines_added} lines are testable)",
                adjusted=True,
            )

        # Standard evaluation
        return CoverageResult(
            passed=reported_coverage >= profile.coverage_threshold,
            actual_coverage=reported_coverage,
            required_coverage=profile.coverage_threshold,
            rationale="Standard coverage evaluation",
            adjusted=False,
        )
```

### Phase 5: Pattern Detection for Testability

Detect what's actually testable:

```python
class TestabilityAnalyzer:
    """Analyzes code to determine what's meaningfully testable."""

    # Patterns that are NOT meaningfully unit-testable
    NON_TESTABLE_PATTERNS = [
        "pydantic_model",      # Declarative models
        "dataclass",           # Data containers
        "enum_definition",     # Enumerations
        "constant_definition", # Constants
        "import_statement",    # Imports
        "type_alias",          # Type definitions
        "app_initialization",  # FastAPI/Flask app = X()
        "router_inclusion",    # app.include_router()
        "middleware_config",   # app.add_middleware()
    ]

    # Patterns that ARE meaningfully testable
    TESTABLE_PATTERNS = [
        "function_with_logic",    # Functions with branching
        "method_with_logic",      # Methods with branching
        "error_handling",         # try/except blocks
        "validation_logic",       # if/else validation
        "transformation",         # Data transformation functions
        "api_endpoint_logic",     # Route handlers with logic
        "database_query",         # Query construction
        "external_api_call",      # HTTP clients
    ]

    def analyze(self, file_path: Path) -> TestabilityReport:
        """Analyze a file for testability."""
        tree = ast.parse(file_path.read_text())

        testable_lines = 0
        non_testable_lines = 0
        patterns_found = []

        for node in ast.walk(tree):
            pattern = self._classify_node(node)
            if pattern:
                patterns_found.append(pattern)
                if pattern in self.TESTABLE_PATTERNS:
                    testable_lines += self._count_lines(node)
                elif pattern in self.NON_TESTABLE_PATTERNS:
                    non_testable_lines += self._count_lines(node)

        return TestabilityReport(
            testable_lines=testable_lines,
            non_testable_lines=non_testable_lines,
            patterns=patterns_found,
            testability_ratio=testable_lines / (testable_lines + non_testable_lines)
                if (testable_lines + non_testable_lines) > 0 else 0,
        )
```

### Complete Context-Sensitive Coach

```python
class ContextSensitiveCoachValidator:
    """Coach that adapts validation to implementation context."""

    def __init__(self, worktree_path: str):
        self.worktree_path = Path(worktree_path)
        self.context_gatherer = ContextGatherer()
        self.scope_classifier = ScopeClassifier()
        self.testability_analyzer = TestabilityAnalyzer()
        self.coverage_evaluator = ContextualCoverageEvaluator()

    def validate(
        self,
        task_id: str,
        turn: int,
        task: Dict[str, Any],
    ) -> CoachValidationResult:

        # 1. Gather implementation context
        context = self.context_gatherer.gather(self.worktree_path, task_id)
        logger.info(f"Implementation context: {context.total_lines_added} LOC, "
                   f"pattern={context.dominant_pattern}, "
                   f"complexity={context.max_cyclomatic_complexity}")

        # 2. Classify implementation scope
        classification = self.scope_classifier.classify(context, task)
        logger.info(f"Scope classification: {classification.category} "
                   f"(confidence={classification.confidence:.0%})")
        logger.info(f"Rationale: {classification.rationale}")

        # 3. Select appropriate profile
        profile = DYNAMIC_PROFILES[classification.recommended_profile]
        logger.info(f"Selected profile: {classification.recommended_profile}")
        logger.info(f"Profile rationale: {profile.rationale}")

        # 4. Read task-work results
        task_work_results = self.read_quality_gate_results(task_id)

        # 5. Evaluate gates with context
        gates_status = self._evaluate_gates_contextually(
            task_work_results,
            profile,
            context,
        )

        # 6. Make decision with full context
        if gates_status.all_gates_passed:
            return self._approve_with_context(task_id, turn, gates_status, classification)
        else:
            return self._feedback_with_context(task_id, turn, gates_status, classification, context)

    def _evaluate_gates_contextually(
        self,
        results: Dict[str, Any],
        profile: DynamicProfile,
        context: ImplementationContext,
    ) -> ContextualGateStatus:

        issues = []

        # Architectural review (context-aware)
        if profile.arch_review_required:
            arch_score = results.get("code_review", {}).get("score", 0)
            arch_passed = arch_score >= profile.arch_review_threshold
            if not arch_passed:
                issues.append(f"Arch review: {arch_score} < {profile.arch_review_threshold}")
        else:
            arch_passed = True
            logger.info(f"Arch review skipped: {profile.rationale}")

        # Coverage (context-aware)
        if profile.coverage_required:
            reported_coverage = results.get("quality_gates", {}).get("coverage", 0)
            coverage_result = self.coverage_evaluator.evaluate(
                context, profile, reported_coverage
            )
            coverage_passed = coverage_result.passed
            if coverage_result.adjusted:
                logger.info(f"Coverage adjusted: {coverage_result.rationale}")
            if not coverage_passed:
                issues.append(f"Coverage: {coverage_result.actual_coverage:.1f}% < "
                            f"{coverage_result.required_coverage:.1f}%")
        else:
            coverage_passed = True
            logger.info("Coverage skipped: not required for this scope")

        # Tests (context-aware)
        if profile.tests_required:
            tests_passed = results.get("quality_gates", {}).get("all_passed", False)

            # If integration tests are acceptable, check for those
            if not tests_passed and profile.integration_tests_acceptable:
                integration_tests_exist = self._check_integration_tests(context)
                if integration_tests_exist:
                    tests_passed = True
                    logger.info("Unit tests missing but integration tests found (acceptable)")
        else:
            tests_passed = True

        return ContextualGateStatus(
            arch_review_passed=arch_passed,
            coverage_passed=coverage_passed,
            tests_passed=tests_passed,
            plan_audit_passed=True,
            all_gates_passed=all([arch_passed, coverage_passed, tests_passed]),
            profile_used=profile,
            adjustments_made=issues,
        )
```

## Example: How This Would Handle TASK-FHA-002

```
Task: Implement core configuration
task_type: feature
complexity: 3

--- Context Gathering ---
total_lines_added: 28
files_created: 2 (config.py, .env.example)
max_cyclomatic_complexity: 1
has_branching_logic: False
has_error_handling: False
code_patterns: ["pydantic_model", "configuration", "constant_definition"]
dominant_pattern: "declarative"
testable_lines: 0 (Pydantic model is declarative)

--- Scope Classification ---
volume_score: 10 (< 30 lines)
complexity_score: 0 (no branching, no error handling)
pattern_score: 15 (declarative dominant)
risk_score: 0 (no risky tags, isolated)
overall_score: 6.25

Classification: "trivial"
Recommended profile: "minimal"

--- Profile Selection ---
arch_review_required: False
coverage_required: False
tests_required: False
rationale: "Trivial implementation - minimal validation sufficient"

--- Gate Evaluation ---
Arch review: SKIPPED (not required for trivial scope)
Coverage: SKIPPED (no testable lines detected)
Tests: SKIPPED (not required for trivial scope)

--- Decision ---
APPROVED

Rationale: "Implementation classified as trivial (28 LOC declarative configuration
code). Architectural review, coverage, and unit tests skipped as inappropriate
for this scope. Plan audit passed."
```

## Trade-offs and Considerations

### Pros

- Adapts to actual implementation, not just task metadata
- Eliminates false positives (simple code failing strict gates)
- Provides transparent reasoning for decisions
- Still enforces strict gates for complex/risky code

### Cons

- More complex implementation
- Requires code analysis (AST parsing, git diff)
- Pattern detection can be imperfect
- Adds latency to validation

### Mitigation Strategies

- Cache analysis results per task
- Use fast parsing (tree-sitter) instead of full AST
- Allow override via task frontmatter (`force_strict_validation: true`)
- Log all decisions for auditability

## Implementation Phases

| Phase | Scope | Effort | Value |
|-------|-------|--------|-------|
| 1 | Basic context gathering (LOC, file count) | Low | Medium |
| 2 | Scope classification (volume + complexity) | Medium | High |
| 3 | Dynamic profile selection | Low | High |
| 4 | Pattern detection (declarative vs logic) | Medium | Medium |
| 5 | Testability analysis | High | Medium |
| 6 | Full contextual coverage evaluation | Medium | Medium |

## Language-Agnostic Architecture

The initial design examples use Python AST, but GuardKit is explicitly technology-agnostic. This section describes how to make the context-sensitive Coach work across all supported languages.

### Tiered Analysis Strategy

The context gathering system uses a three-tier approach:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Tier 1: Universal Analysis (All Languages)                          │
│   - Git diff statistics (lines added/modified/deleted)              │
│   - File counts and extensions                                      │
│   - Line counting (wc -l equivalent)                                │
│   - Directory structure analysis                                    │
│   - Dependency file parsing (package.json, requirements.txt, etc.)  │
│   ► Always available, ~50ms total                                   │
├─────────────────────────────────────────────────────────────────────┤
│ Tier 2: Tree-sitter Analysis (40+ Languages)                        │
│   - AST-based pattern detection                                     │
│   - Function/class/method counting                                  │
│   - Cyclomatic complexity approximation                             │
│   - Import/dependency analysis                                      │
│   ► Available for: Python, JS/TS, Go, Rust, C#, Java, etc.         │
│   ► ~100-200ms per file                                             │
├─────────────────────────────────────────────────────────────────────┤
│ Tier 3: Language-Specific Plugins (Optional)                        │
│   - Deep pattern recognition                                        │
│   - Framework-specific detection                                    │
│   - Testability heuristics                                          │
│   ► Python: FastAPI, Pydantic, Django patterns                     │
│   ► TypeScript: React, Next.js, NestJS patterns                    │
│   ► C#: ASP.NET, Entity Framework patterns                         │
│   ► ~200-500ms when invoked                                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Tier 1: Universal Analysis (Always Available)

These metrics work for ANY language and provide the foundation:

```python
@dataclass
class UniversalContext:
    """Language-agnostic context from git and file system."""

    # Git diff statistics (git diff --stat --numstat)
    lines_added: int
    lines_deleted: int
    lines_modified: int
    files_created: int
    files_modified: int
    files_deleted: int

    # File type breakdown
    file_extensions: Dict[str, int]  # e.g., {".py": 3, ".json": 1}
    source_files: int
    test_files: int  # Detected via naming convention (*_test.*, *.test.*, etc.)
    config_files: int

    # Dependency indicators
    has_dependency_changes: bool  # package.json, requirements.txt, etc.
    new_external_dependencies: int

class UniversalContextGatherer:
    """Gathers context using only language-agnostic tools."""

    def gather(self, worktree_path: Path) -> UniversalContext:
        # Git diff is universal
        diff_stats = self._run_git_diff_stat(worktree_path)

        # File extension analysis is universal
        extensions = self._categorize_files(diff_stats.changed_files)

        # Test file detection via naming conventions
        test_patterns = [
            "*_test.*", "*.test.*", "test_*.*",  # Common patterns
            "*_spec.*", "*.spec.*",              # JS/Ruby conventions
            "*Tests.*", "*Test.*",               # C#/Java conventions
        ]
        test_files = self._match_patterns(diff_stats.changed_files, test_patterns)

        # Dependency file detection
        dep_files = ["package.json", "requirements.txt", "go.mod",
                     "Cargo.toml", "*.csproj", "pom.xml", "build.gradle"]
        has_dep_changes = any(f in diff_stats.changed_files for f in dep_files)

        return UniversalContext(
            lines_added=diff_stats.lines_added,
            lines_deleted=diff_stats.lines_deleted,
            lines_modified=diff_stats.lines_modified,
            files_created=diff_stats.files_created,
            files_modified=diff_stats.files_modified,
            files_deleted=diff_stats.files_deleted,
            file_extensions=extensions,
            source_files=len([f for f in extensions if f not in [".json", ".yaml", ".md"]]),
            test_files=len(test_files),
            config_files=len([f for f in diff_stats.changed_files if self._is_config(f)]),
            has_dependency_changes=has_dep_changes,
            new_external_dependencies=self._count_new_deps(worktree_path),
        )
```

### Tier 2: Tree-sitter Analysis (Multi-Language AST)

[Tree-sitter](https://tree-sitter.github.io/tree-sitter/) provides fast, incremental parsing for 40+ languages with a unified API:

```python
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_go as tsgo
import tree_sitter_rust as tsrust
from tree_sitter import Language, Parser

class TreeSitterAnalyzer:
    """Language-agnostic AST analysis using tree-sitter."""

    LANGUAGE_MAP = {
        ".py": tspython.language(),
        ".js": tsjavascript.language(),
        ".ts": tsjavascript.language(),  # TS parser handles both
        ".go": tsgo.language(),
        ".rs": tsrust.language(),
        ".cs": None,  # Add when tree-sitter-c-sharp available
        ".java": None,  # Add when tree-sitter-java available
    }

    # Universal node types that exist across languages
    FUNCTION_NODES = ["function_definition", "function_declaration",
                      "method_definition", "arrow_function"]
    CLASS_NODES = ["class_definition", "class_declaration", "struct_item"]
    BRANCH_NODES = ["if_statement", "match_expression", "switch_statement",
                    "conditional_expression", "ternary_expression"]
    LOOP_NODES = ["for_statement", "while_statement", "for_in_statement"]

    def analyze(self, file_path: Path) -> Optional[ASTMetrics]:
        ext = file_path.suffix
        language = self.LANGUAGE_MAP.get(ext)

        if language is None:
            return None  # Fall back to Tier 1 only

        parser = Parser(language)
        source = file_path.read_bytes()
        tree = parser.parse(source)

        return ASTMetrics(
            function_count=self._count_nodes(tree, self.FUNCTION_NODES),
            class_count=self._count_nodes(tree, self.CLASS_NODES),
            branch_count=self._count_nodes(tree, self.BRANCH_NODES),
            loop_count=self._count_nodes(tree, self.LOOP_NODES),
            max_nesting_depth=self._calculate_max_nesting(tree),
            cyclomatic_complexity=self._estimate_cyclomatic(tree),
        )

    def _estimate_cyclomatic(self, tree) -> int:
        """Estimate cyclomatic complexity from AST.

        CC = 1 + branches + loops + boolean operators
        This is an approximation but works across languages.
        """
        branches = self._count_nodes(tree, self.BRANCH_NODES)
        loops = self._count_nodes(tree, self.LOOP_NODES)
        # Boolean operators add decision points
        bool_ops = self._count_nodes(tree, ["and", "or", "&&", "||"])
        return 1 + branches + loops + bool_ops
```

### Tier 3: Language-Specific Plugins

For deep pattern recognition, language plugins provide framework-aware analysis:

```python
class LanguagePlugin(Protocol):
    """Protocol for language-specific analysis plugins."""

    def detect_patterns(self, file_path: Path, ast: Any) -> List[str]:
        """Detect language/framework-specific patterns."""
        ...

    def estimate_testability(self, file_path: Path, ast: Any) -> float:
        """Estimate what percentage of code is meaningfully testable."""
        ...

    def get_non_testable_patterns(self) -> List[str]:
        """Return patterns that are not meaningfully unit-testable."""
        ...

class PythonPlugin(LanguagePlugin):
    """Python-specific pattern detection."""

    NON_TESTABLE = [
        "pydantic_model",       # BaseModel subclasses
        "dataclass",            # @dataclass decorators
        "fastapi_app_init",     # app = FastAPI()
        "django_model",         # models.Model subclasses
        "enum_class",           # Enum subclasses
    ]

    def detect_patterns(self, file_path: Path, ast) -> List[str]:
        patterns = []

        # Detect Pydantic models
        if self._has_basemodel_import(ast) and self._has_class_inheriting(ast, "BaseModel"):
            patterns.append("pydantic_model")

        # Detect FastAPI app initialization
        if "app = FastAPI(" in file_path.read_text():
            patterns.append("fastapi_app_init")

        # Detect dataclasses
        if self._has_dataclass_decorator(ast):
            patterns.append("dataclass")

        return patterns

class TypeScriptPlugin(LanguagePlugin):
    """TypeScript/JavaScript-specific pattern detection."""

    NON_TESTABLE = [
        "react_component_jsx",   # Pure JSX without logic
        "nextjs_page_config",    # export const config = {}
        "type_definition",       # interface/type declarations
        "tailwind_classes",      # className strings
        "graphql_schema",        # GraphQL type definitions
    ]

    def detect_patterns(self, file_path: Path, ast) -> List[str]:
        patterns = []

        # Detect pure JSX components (no hooks, no logic)
        if self._is_pure_jsx_component(ast):
            patterns.append("react_component_jsx")

        # Detect type-only files
        if self._is_type_only_file(ast):
            patterns.append("type_definition")

        return patterns

class CSharpPlugin(LanguagePlugin):
    """C#-specific pattern detection."""

    NON_TESTABLE = [
        "dto_record",            # record Dto { ... }
        "entity_class",          # EF Core entities
        "aspnet_startup",        # Program.cs/Startup.cs
        "automapper_profile",    # AutoMapper profiles
        "ef_migration",          # EF migrations
    ]
```

### Plugin Registry and Fallback

```python
class PluginRegistry:
    """Manages language plugins with graceful fallback."""

    PLUGINS = {
        ".py": PythonPlugin,
        ".ts": TypeScriptPlugin,
        ".tsx": TypeScriptPlugin,
        ".js": TypeScriptPlugin,  # Same patterns mostly
        ".cs": CSharpPlugin,
        ".go": GoPlugin,
        ".rs": RustPlugin,
        ".java": JavaPlugin,
    }

    def get_plugin(self, extension: str) -> Optional[LanguagePlugin]:
        plugin_class = self.PLUGINS.get(extension)
        if plugin_class:
            return plugin_class()
        return None

    def analyze_with_fallback(
        self,
        file_path: Path,
        universal_context: UniversalContext,
    ) -> ImplementationContext:
        """Analyze file, falling back to universal context if needed."""

        ext = file_path.suffix

        # Always have Tier 1
        context = ImplementationContext.from_universal(universal_context)

        # Try Tier 2 (tree-sitter)
        ast_metrics = self.tree_sitter.analyze(file_path)
        if ast_metrics:
            context = context.with_ast_metrics(ast_metrics)

        # Try Tier 3 (language plugin)
        plugin = self.get_plugin(ext)
        if plugin and ast_metrics:
            patterns = plugin.detect_patterns(file_path, ast_metrics.tree)
            testability = plugin.estimate_testability(file_path, ast_metrics.tree)
            context = context.with_language_analysis(patterns, testability)

        return context
```

### Scope Classification Without Language-Specific Analysis

When language-specific analysis isn't available, the classifier still works using Tier 1 metrics:

```python
def classify_from_universal_only(self, ctx: UniversalContext) -> ScopeClassification:
    """Classify scope using only universal (Tier 1) metrics.

    This is the fallback when tree-sitter or language plugins aren't available.
    """

    # Volume-based scoring (same as before)
    volume_score = self._score_volume_universal(ctx)

    # Heuristic complexity from file counts and test presence
    complexity_score = 0
    if ctx.source_files > 5:
        complexity_score += 30
    if ctx.test_files == 0 and ctx.source_files > 1:
        complexity_score += 20  # Missing tests for non-trivial change
    if ctx.has_dependency_changes:
        complexity_score += 15

    # Pattern heuristics from file naming
    pattern_score = 50  # Neutral baseline
    config_ratio = ctx.config_files / max(ctx.source_files, 1)
    if config_ratio > 0.5:
        pattern_score = 20  # Likely configuration-heavy

    # Risk from dependencies
    risk_score = min(ctx.new_external_dependencies * 10, 40)

    overall = (
        volume_score * 0.3 +      # Weight volume more
        complexity_score * 0.25 +
        pattern_score * 0.25 +
        risk_score * 0.2
    )

    # Use conservative classification when uncertain
    confidence = 0.7  # Lower confidence without AST analysis
    return self._classify_with_confidence(overall, confidence)
```

---

## Performance Analysis & Optimization

### Latency Budget

The Coach validates after each Player turn. Current validation takes ~2-5 seconds. Adding context gathering must not significantly impact this.

**Target Latency Budget**:
- Tier 1 (Universal): < 100ms
- Tier 2 (Tree-sitter): < 500ms total
- Tier 3 (Language plugins): < 300ms total
- **Total context gathering**: < 1 second

### Baseline Measurements

| Operation | Typical Latency | Notes |
|-----------|-----------------|-------|
| `git diff --stat` | 10-50ms | Depends on diff size |
| `git diff --numstat` | 10-50ms | Parallel with above |
| File extension categorization | 5ms | In-memory |
| Tree-sitter parse (per file) | 20-100ms | Depends on file size |
| Pattern detection (per file) | 50-150ms | Depends on plugin |
| **Total (10 files)** | **300-800ms** | Acceptable |

### Caching Strategy

Context gathering happens once per turn, but the same task may have 3-5 turns. Caching reduces redundant work:

```python
@dataclass
class CachedAnalysis:
    """Cached analysis results for a file."""
    file_path: str
    file_hash: str  # SHA of file contents
    ast_metrics: Optional[ASTMetrics]
    patterns: List[str]
    testability: float
    timestamp: datetime

class ContextCache:
    """Caches analysis results between turns."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_file = cache_dir / "context_cache.json"
        self._cache: Dict[str, CachedAnalysis] = {}

    def get_or_analyze(
        self,
        file_path: Path,
        analyzer: Callable[[Path], CachedAnalysis]
    ) -> CachedAnalysis:
        """Return cached analysis or compute and cache."""

        file_hash = self._compute_hash(file_path)
        cache_key = str(file_path)

        # Check cache validity
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if cached.file_hash == file_hash:
                return cached  # Cache hit

        # Cache miss - analyze and store
        result = analyzer(file_path)
        result.file_hash = file_hash
        self._cache[cache_key] = result

        return result

    def invalidate_changed_files(self, changed_files: List[str]) -> None:
        """Invalidate cache entries for changed files."""
        for f in changed_files:
            self._cache.pop(f, None)
```

### Incremental Analysis

Only analyze files that changed since last turn:

```python
class IncrementalContextGatherer:
    """Gathers context incrementally, only analyzing changed files."""

    def __init__(self, cache: ContextCache):
        self.cache = cache
        self.previous_commit: Optional[str] = None

    def gather_incremental(
        self,
        worktree_path: Path,
        task_id: str,
        turn: int,
    ) -> ImplementationContext:

        if turn == 1:
            # First turn: full analysis
            return self._full_analysis(worktree_path, task_id)

        # Subsequent turns: incremental
        current_commit = self._get_head_commit(worktree_path)

        if self.previous_commit:
            # Get files changed since last turn
            changed_files = self._get_changed_since(
                worktree_path,
                self.previous_commit,
                current_commit
            )

            # Only re-analyze changed files
            self.cache.invalidate_changed_files(changed_files)

        self.previous_commit = current_commit
        return self._cached_analysis(worktree_path, task_id)

    def _get_changed_since(
        self,
        worktree: Path,
        from_commit: str,
        to_commit: str
    ) -> List[str]:
        """Get files changed between commits."""
        result = subprocess.run(
            ["git", "diff", "--name-only", from_commit, to_commit],
            cwd=worktree,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip().split("\n")
```

### Lazy Evaluation Strategy

Don't compute expensive metrics unless needed:

```python
class LazyContextGatherer:
    """Gathers context lazily, only computing what's needed."""

    def gather_for_classification(
        self,
        worktree_path: Path
    ) -> MinimalContext:
        """Fast path: gather just enough for initial classification."""

        # Tier 1 only - always fast
        universal = self._gather_universal(worktree_path)

        # Quick classification using universal metrics
        if self._is_obviously_trivial(universal):
            # < 30 LOC, 1-2 files, no deps → skip deeper analysis
            return MinimalContext(
                classification="trivial",
                confidence=0.85,
                universal=universal,
                # Skip Tier 2 and 3 entirely
            )

        if self._is_obviously_complex(universal):
            # > 500 LOC, > 10 files, many deps → strict profile
            # But still gather full context for rationale
            pass

        # Middle ground: need deeper analysis
        return self._gather_full_context(worktree_path, universal)

    def _is_obviously_trivial(self, ctx: UniversalContext) -> bool:
        """Detect trivially simple changes without AST analysis."""
        return (
            ctx.lines_added < 30 and
            ctx.files_created + ctx.files_modified <= 2 and
            ctx.new_external_dependencies == 0 and
            ctx.test_files >= 0  # Any test files are bonus
        )

    def _is_obviously_complex(self, ctx: UniversalContext) -> bool:
        """Detect obviously complex changes without AST analysis."""
        return (
            ctx.lines_added > 500 or
            ctx.files_created + ctx.files_modified > 10 or
            ctx.new_external_dependencies > 5
        )
```

### Performance Summary

| Scenario | Context Gathering Time | Strategy Used |
|----------|------------------------|---------------|
| Turn 1, trivial (< 30 LOC) | ~50ms | Tier 1 only, skip deeper |
| Turn 1, small (30-100 LOC) | ~300ms | Tier 1 + Tier 2 |
| Turn 1, medium (100-300 LOC) | ~600ms | Full analysis |
| Turn 1, large (> 300 LOC) | ~1000ms | Full analysis |
| Turn 2+, no changes | ~10ms | Full cache hit |
| Turn 2+, few changes | ~100ms | Incremental |

**Worst case**: First turn of a large change (> 500 LOC, 20 files) = ~2 seconds
**Best case**: Subsequent turn with no changes = ~10ms
**Typical case**: First turn of medium change = ~500ms

---

## Open Questions (Remaining)

1. ~~**Language agnostic**: Current design assumes Python AST - how to handle other languages?~~ **Addressed above.**
2. ~~**Performance**: How much latency does context gathering add per turn?~~ **Addressed above.**
3. ~~**Caching**: Can we cache context between turns (only re-analyze changed files)?~~ **Addressed above.**
4. **Override mechanism**: How should users force strict validation when needed?
5. **Integration**: How does this interact with existing task_type system?

## Next Steps

1. ~~Address language-agnostic design~~ **Done**
2. ~~Analyze performance implications~~ **Done**
3. Prototype Phase 1-3 for validation (Tier 1 universal + scope classification)
4. Gather feedback on classification thresholds
5. Implement tree-sitter integration for Tier 2
6. Create language plugins for Python, TypeScript, C#
