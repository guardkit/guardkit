---
id: TASK-769D
title: Implement AI agent invocation for template-create and fix fallback
status: in_review
created: 2025-11-12T17:02:19Z
updated: 2025-11-12T18:30:00Z
completed_at: 2025-11-12T18:30:00Z
priority: critical
tags: [bugfix, template-create, ai-native, architecture]
complexity: 2
test_results:
  status: passed
  total_tests: 30
  passed: 30
  failed: 0
  coverage_line: 83.58
  coverage_branch: 75
  last_run: 2025-11-12T18:25:00Z
code_review:
  score: 9.0
  status: approved
  issues_critical: 0
  issues_major: 0
  issues_minor: 2
architectural_review:
  score: 95
  status: approved
previous_state: in_progress
state_transition_reason: "All quality gates passed - 30/30 tests (100%), coverage 83.58%, code review 9.0/10 (APPROVED)"
workflow_completed: true
---

# Implement AI Agent Invocation for Template-Create and Fix Fallback

## Problem Statement

`/template-create` generates 0 template files because the AI agent invocation is **NOT IMPLEMENTED** - it's just a placeholder that always falls back to heuristics, which then fail for non-Python projects.

**Root Cause Analysis**:

**PRIMARY ISSUE** (Root Cause):
- [agent_invoker.py:129](installer/global/lib/codebase_analyzer/agent_invoker.py#L129) - Agent invocation always raises "not yet implemented"
- AI agent (`architectural-reviewer`) is never actually invoked
- System immediately falls back to heuristics

**SECONDARY ISSUE** (Fallback Weakness):
- Heuristic fallback discards already-collected file samples
- Tries to re-scan with hardcoded Python-only logic
- Returns empty example_files for C#, TypeScript, Go, Rust, etc.

**Impact**: All template creation fails to generate templates when using `/template-create`

## Solution Overview

This task implements BOTH fixes for robust, AI-powered, technology-agnostic template creation:

### 1. PRIMARY FIX: Implement Real AI Agent Invocation
Use Claude Code's Task tool to invoke the `architectural-reviewer` agent with the collected codebase samples and analysis prompt.

### 2. SECONDARY FIX: Technology-Agnostic Fallback
When AI is unavailable, use already-collected file samples instead of re-scanning with hardcoded logic.

## Acceptance Criteria

### Primary Fix (AI Agent Invocation)
1. ✅ `AgentInvoker.invoke_agent()` uses Task tool to invoke architectural-reviewer agent
2. ✅ Agent receives file samples and analysis prompt
3. ✅ Agent returns structured JSON with technology/architecture/quality/example_files
4. ✅ Response is parsed into CodebaseAnalysis model
5. ✅ AI-native analysis completes successfully for C#, TypeScript, Python, Go, Rust projects
6. ✅ `/template-create` generates 10-20 template files using AI analysis

### Secondary Fix (Fallback Robustness)
7. ✅ When AI unavailable, heuristics receive already-collected file_samples
8. ✅ HeuristicAnalyzer converts file_samples to example_files (no language detection)
9. ✅ Fallback generates template files using collected samples
10. ✅ NO hardcoded language-specific logic added

### Quality Gates
11. ✅ All existing unit tests pass
12. ✅ Integration test: `/template-create` on C# project generates templates
13. ✅ Integration test: `/template-create` on TypeScript project generates templates
14. ✅ Coverage: ≥80% line, ≥75% branch
15. ✅ Solution remains 100% technology-agnostic

## Implementation Plan

### Part 1: Implement AI Agent Invocation (PRIMARY)

**Strategy**: Reuse the existing `AgentBridgeInvoker` pattern (already working in Phase 5/TASK-51B2-C)

**Reference Implementation**: [installer/global/lib/agent_bridge/invoker.py](installer/global/lib/agent_bridge/invoker.py#L85-L159)

**File 1**: [installer/global/lib/codebase_analyzer/ai_analyzer.py](installer/global/lib/codebase_analyzer/ai_analyzer.py#L94-L125)

Modify `CodebaseAnalyzer.__init__()` to accept optional `agent_invoker`:
```python
class CodebaseAnalyzer:
    def __init__(
        self,
        max_files: int = 10,
        use_agent: bool = True,
        use_stratified_sampling: bool = True,
        agent_invoker: Optional[Any] = None  # NEW: Accept bridge invoker
    ):
        self.max_files = max_files
        self.use_agent = use_agent
        self.use_stratified_sampling = use_stratified_sampling

        # Use provided invoker or create default (backward compatibility)
        if agent_invoker:
            self.agent_invoker_bridge = agent_invoker  # Bridge invoker
        else:
            # Fallback to old agent_invoker (for backward compatibility)
            _agent_invoker_module = importlib.import_module('installer.global.lib.codebase_analyzer.agent_invoker')
            AgentInvoker = _agent_invoker_module.AgentInvoker
            self.agent_invoker_bridge = None
            self.agent_invoker = AgentInvoker()  # Old implementation
```

**File 2**: [installer/global/lib/codebase_analyzer/ai_analyzer.py](installer/global/lib/codebase_analyzer/ai_analyzer.py#L171-L178)

Modify agent invocation to use bridge if available:
```python
if self.use_agent:
    logger.info("Invoking architectural-reviewer agent...")
    try:
        # Use bridge invoker if provided (checkpoint-resume pattern)
        if self.agent_invoker_bridge:
            response = self.agent_invoker_bridge.invoke(
                agent_name="architectural-reviewer",
                prompt=prompt
            )
        else:
            # Fallback to old invoker (backward compatibility)
            response = self.agent_invoker.invoke_agent(
                prompt=prompt,
                agent_name="architectural-reviewer"
            )
```

**File 3**: [installer/global/commands/lib/template_create_orchestrator.py](installer/global/commands/lib/template_create_orchestrator.py#L338-L372)

Pass bridge invoker to `CodebaseAnalyzer` (same pattern as Phase 5):
```python
def _phase1_ai_analysis(self, codebase_path: Path) -> Optional[Any]:
    self._print_phase_header("Phase 1: AI Codebase Analysis")

    try:
        # Create analyzer with bridge invoker for checkpoint-resume
        analyzer = CodebaseAnalyzer(
            max_files=30,
            agent_invoker=self.agent_invoker  # ← Pass AgentBridgeInvoker
        )

        # This may exit with code 42 if agent invocation needed
        analysis = analyzer.analyze_codebase(
            codebase_path=codebase_path,
            template_context=None,
            save_results=False
        )
```

**Key Points**:
- Reuse proven `AgentBridgeInvoker` (checkpoint-resume with exit code 42)
- Same pattern already working in Phase 5 (TASK-51B2-C)
- Maintains backward compatibility with existing tests
- Agent does ALL analysis (technology detection, architecture, example file selection)
- NO Python code tries to detect languages or patterns

### Part 2: Fix Heuristic Fallback (SECONDARY)

**File 1**: [installer/global/lib/codebase_analyzer/agent_invoker.py](installer/global/lib/codebase_analyzer/agent_invoker.py#L193-L268)

Modify `HeuristicAnalyzer`:
```python
class HeuristicAnalyzer:
    def __init__(self, codebase_path: Path, file_samples: Optional[List[Dict]] = None):
        self.codebase_path = codebase_path
        self.file_samples = file_samples  # Use provided samples if available

    def analyze(self) -> dict:
        # ... detect language, frameworks, etc ...

        return {
            "technology": { ... },
            "architecture": { ... },
            "quality": { ... },
            "example_files": self._get_example_files(),  # NEW METHOD
            "agent_used": False,
            "fallback_reason": "Agent not available - using heuristic analysis"
        }

    def _get_example_files(self) -> list:
        """Get example files from provided samples or empty list."""
        if not self.file_samples:
            return []

        # Convert file_samples to example_files format (technology-agnostic)
        return [{
            "path": sample.get("path", ""),
            "purpose": "Code file from codebase",
            "layer": None,  # Let AI determine
            "patterns_used": [],  # Let AI determine
            "key_concepts": []  # Let AI determine
        } for sample in self.file_samples[:20]]  # Limit to 20 files
```

**File 2**: [installer/global/lib/codebase_analyzer/ai_analyzer.py](installer/global/lib/codebase_analyzer/ai_analyzer.py#L226-L253)

Modify `_fallback_analysis()`:
```python
def _fallback_analysis(
    self,
    codebase_path: Path,
    template_context: Optional[Dict[str, str]],
    file_samples: Optional[List[Dict]] = None  # NEW PARAMETER
) -> CodebaseAnalysis:
    """Perform fallback heuristic analysis when agent is unavailable."""
    # Pass file_samples to heuristic analyzer
    heuristic_analyzer = HeuristicAnalyzer(codebase_path, file_samples=file_samples)
    heuristic_data = heuristic_analyzer.analyze()

    # Convert to CodebaseAnalysis
    fallback_builder = FallbackResponseBuilder()
    analysis = fallback_builder.build_from_heuristics(
        heuristic_data=heuristic_data,
        codebase_path=str(codebase_path),
        template_context=template_context
    )

    return analysis
```

And update the call site:
```python
# Fallback to heuristic analysis if needed
if analysis is None:
    logger.info("Performing heuristic analysis...")
    analysis = self._fallback_analysis(
        codebase_path=codebase_path,
        template_context=template_context,
        file_samples=file_samples  # Pass collected samples
    )
```

**CRITICAL**: Remove or comment out the hardcoded Python-only `_find_example_files()` method - it should never be called.

## Technology-Agnostic Principles

### ✅ CORRECT APPROACH (AI-Powered):
- Collect file samples (stratified sampler handles all languages)
- Pass samples to AI agent
- AI agent analyzes and returns example_files
- AI determines language, framework, architecture, patterns
- Python code does ZERO language detection

### ❌ WRONG APPROACH (Hardcoded):
- Python code detects file extensions
- Python code matches framework patterns
- Python code knows about specific languages
- Different code paths for Python vs C# vs TypeScript

## Testing Requirements

### Unit Tests
1. `test_agent_invocation_success` - AI agent returns valid analysis
2. `test_agent_invocation_fallback` - Graceful fallback when AI unavailable
3. `test_heuristic_with_samples` - Heuristics use provided file_samples
4. `test_heuristic_without_samples` - Backward compatibility (empty list)

### Integration Tests
5. `/template-create` on C# project → generates 10-20 templates
6. `/template-create` on TypeScript project → generates 10-20 templates
7. `/template-create` on Python project → generates 10-20 templates
8. Verify templates contain correct placeholders and structure

### Coverage
- Line coverage: ≥80%
- Branch coverage: ≥75%

## Success Metrics

### Primary Success (AI Agent Working):
- ✅ `/template-create` invokes architectural-reviewer agent
- ✅ Agent returns structured analysis with example_files
- ✅ Template generator creates 10-20 .template files
- ✅ Works for C#, TypeScript, Python, Go, Rust, Ruby, PHP (technology-agnostic)
- ✅ No "fell back to heuristics" message

### Secondary Success (Robust Fallback):
- ✅ When AI unavailable, heuristics use collected samples
- ✅ Fallback generates templates using collected files
- ✅ No empty example_files when samples were collected
- ✅ Graceful degradation with clear logging

### Quality Validation:
- ✅ Zero hardcoded language detection in Python code
- ✅ Zero file extension pattern matching
- ✅ Zero framework-specific code paths
- ✅ Solution works identically for all programming languages

## Related Tasks

- **TASK-51B2-E**: Fixed agent scanner invocation (completed, in_review)
- **TASK-51B2-C**: Fixed AI agent generation in Phase 5 using AgentBridgeInvoker (in_review)
- **TASK-2B67**: Heuristic-only fix (superseded by this comprehensive fix)

**Relationship with TASK-51B2-C**:
- TASK-51B2-C: Phase 5 (Agent Generation) - Uses AgentBridgeInvoker ✅
- TASK-769D: Phase 1 (Codebase Analysis) - Will use same AgentBridgeInvoker pattern
- Both tasks are complementary and use the same proven checkpoint-resume mechanism
- No conflicts - they fix different phases using the same architecture

## Implementation Notes

This is the proper fix that addresses BOTH the root cause (missing AI invocation) and provides robust fallback for when AI is unavailable. The solution maintains the core principle: **AI does the analysis, Python code just orchestrates**.

### Why Both Fixes Matter:
- **AI Invocation**: Primary path, best quality, full AI-powered analysis
- **Robust Fallback**: Backup path when AI unavailable, uses collected data instead of failing

The template creation system should be:
1. **AI-first**: Always try to use AI agent for analysis
2. **Robust**: Gracefully degrade to heuristics if AI unavailable
3. **Technology-agnostic**: Works for any programming language without code changes
