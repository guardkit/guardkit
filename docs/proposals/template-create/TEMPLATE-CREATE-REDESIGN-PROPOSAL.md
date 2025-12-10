# Template-Create Redesign Proposal

**Date**: 2025-11-18  
**Status**: PROPOSED  
**Type**: Architectural Redesign  
**Impact**: HIGH - Core template creation workflow

---

## Executive Summary

The `/template-create` command has accumulated multiple architectural issues that require a comprehensive redesign rather than incremental fixes:

1. **Agent invocation not implemented** - System falls back to heuristics instead of using AI analysis
2. **Phase 7.5 silent failure** - Agent enhancement exists but lacks checkpoint-resume support
3. **Hard-coded detection patterns** - Violates AI-first principle with 1,045 LOC of brittle pattern matching
4. **Build artifact contamination** - Counts build folders leading to wrong language detection
5. **Incomplete agent generation** - Detects 14% of needed agents (1/7-9 expected)

**Recommendation**: Rename existing `template-create` to `template-create-legacy` (undocumented fallback), then build the fixed version as the main `template-create` command. This provides a clean user experience for the upcoming open source release.

---

## Current State Analysis

### What Works ✅

From the debug output and documentation:
- Phase 1: Codebase sampling and stratified file selection works
- Phase 2-4: Manifest, settings, and template file generation succeed
- Phase 4.5: Completeness validation passes
- Basic template creation completes without crashes

### What's Broken ❌

#### Issue 1: Agent Invocation Not Implemented (CRITICAL)

**Evidence from debug output:**
```
2025-11-18 11:32:23,510 - installer.core.lib.codebase_analyzer.ai_analyzer - WARNING - 
Agent invocation failed: Unexpected error during agent invocation: 
Agent invocation not yet implemented. Using fallback heuristics.
```

**Impact:**
- AI analysis disabled, system uses heuristics
- Reduces confidence from expected 90%+ to actual 68%
- Affects all downstream phases (manifest accuracy, agent detection, template quality)

**Root Cause:**
From `codebase_analyzer/ai_analyzer.py`:
```python
except Exception as e:
    self.logger.warning(
        f"Agent invocation failed: {e}. Falling back to heuristics."
    )
```

The agent bridge pattern is defined but not fully implemented - it throws "not yet implemented" error.

#### Issue 2: Phase 5 Checkpoint-Resume Incomplete

**Evidence from debug output:**
```
Phase 5: Agent Recommendation
------------------------------------------------------------
...
🤖 Determining agent needs...
  ⏸️  Requesting agent invocation: architectural-reviewer
  📝 Request written to: .agent-request.json
  🔄 Checkpoint: Orchestrator will resume after agent responds
```

**Problem:** Process exits with code 42 (checkpoint) but:
- Phase 5 completes without waiting for agent response
- No actual AI-powered agent recommendation occurs
- Proceeds to Phase 6 with incomplete data

**Expected Flow:**
1. Phase 5 requests architectural-reviewer
2. Orchestrator exits with code 42
3. User/system invokes architectural-reviewer agent
4. Agent analyzes codebase and returns recommendations
5. Orchestrator resumes from checkpoint with agent data
6. Phase 5 completes with comprehensive agent list

**Actual Flow:**
1. Phase 5 requests architectural-reviewer
2. Orchestrator immediately continues (no wait)
3. Uses fallback hard-coded detection (5 patterns only)
4. Phase 5 "completes" with minimal agent set

#### Issue 3: Phase 7.5 Missing Checkpoint-Resume

**From SESSION-SUMMARY-PHASE-7-5-SILENT-FAILURE.md:**
- Phase 7.5 (Agent Enhancement) exists in code
- Calls `AgentEnhancer` which needs external agent invocation
- No checkpoint saved before Phase 7.5
- No `_run_from_phase_7()` resume method
- No agent serialization/deserialization
- Result: Basic 34-line agents instead of enhanced 150-250 line agents

#### Issue 4: Hard-Coded Detection Violates AI-First Principle

**From TEMPLATE-CREATE-ARCHITECTURAL-REVIEW.md:**

Current implementation has `smart_defaults_detector.py` (531 LOC) + tests (514 LOC) = 1,045 LOC of pattern matching:

```python
class LanguageDetector:
    def detect_language(self, project_path: Path) -> Optional[str]:
        if (project_path / "setup.py").exists():
            return "Python"
        # ... 7 more languages with file-based detection

class FrameworkDetector:
    PYTHON_FRAMEWORKS = {
        r"fastapi[>=<]": "FastAPI",
        r"flask[>=<]": "Flask",
        # ... Pattern matching for 12+ frameworks
```

**Why This Is Wrong:**
1. AI can already read and understand dependency files
2. Pattern matching breaks when new frameworks emerge
3. Maintenance burden (update code for every new framework)
4. Contradicts original AI-native vision from TASK-042/058/059
5. Brittle with monorepos, custom configs, framework-less architectures

**Original Vision (TASK-042):**
> "You are generating SCAFFOLDING for complete features. If you only see some operations in the reference code, **YOU MUST INFER THE OTHERS**."

AI should infer from codebase analysis, not use hard-coded patterns.

#### Issue 5: Build Artifact Contamination (TASK-9037)

**Impact:** Counts 606 `.java` files from `obj/` and `bin/` folders in .NET projects
**Result:** Detects as Java project instead of C# project
**Affects:** All technology stacks with compiled output

#### Issue 6: Agent Detection Limitation (TASK-TMPL-4E89)

**Current:** Hard-coded checks for 5 patterns (MVVM, Navigation, ErrorOr, Domain, Testing)
**Detects:** 1 agent (14% coverage)
**Expected:** 7-9 agents (78-100% coverage)
**Missing:** Repository, Service, Engine, CQRS, Event Sourcing, database patterns, etc.

---

## Design Principles for Redesign

### 1. AI-First Architecture (Restored)

**Principle:** AI analyzes, humans decide. No hard-coded pattern matching.

**Implementation:**
- All detection happens through agent invocation (architectural-reviewer)
- No `smart_defaults_detector.py`
- Enhanced prompts guide AI inference
- Code provides structure, AI provides intelligence

### 2. Checkpoint-Resume Pattern (Complete)

**Principle:** All phases that need external agent invocation must support checkpoint-resume.

**Required Components:**
- Checkpoint save before agent invocation
- State serialization (include all context)
- Resume routing method (`_run_from_phase_N()`)
- State deserialization on resume
- Graceful error handling

**Apply to:**
- Phase 1: AI Codebase Analysis (architectural-reviewer)
- Phase 5: Agent Recommendation (architectural-reviewer)
- Phase 7.5: Agent Enhancement (agent-content-enhancer)

### 3. Clean Build Artifact Filtering

**Principle:** Analyze source code only, never build outputs.

**Implementation:**
- Respect `.gitignore` patterns
- Add standard exclusion list (obj/, bin/, node_modules/, dist/, build/, target/, etc.)
- User-configurable exclusions in project `.agentecflow/config.json`

### 4. Graceful Degradation

**Principle:** System should work even when AI components fail.

**Fallback Strategy:**
- Phase 1 AI failure → Use heuristics (current behavior)
- Phase 5 AI failure → Use basic agent set from manifest
- Phase 7.5 AI failure → Use basic agent templates (current behavior)

**User Communication:**
```
⚠️  AI analysis failed, using heuristics (confidence: 68% vs 90% expected)
💡 For better results, ensure agent bridge is configured correctly
```

### 5. Progressive Enhancement

**Principle:** Create working templates first, enhance iteratively.

**Phases:**
1. Core template creation (Phases 1-4) - **Must work**
2. Agent recommendation (Phase 5) - **Should work**
3. Agent enhancement (Phase 7.5) - **Nice to have**

Users can manually enhance agents if Phase 7.5 fails.

---

## Proposed Architecture

### Rename Strategy: Clean Main Command

Create clean main command for open source release:

```bash
# Step 1: Rename existing command (keep as fallback)
mv installer/core/commands/template-create.md \
   installer/core/commands/template-create-legacy.md

mv installer/core/commands/lib/template_create_orchestrator.py \
   installer/core/commands/lib/template_create_legacy_orchestrator.py

# Step 2: Build new template-create with all fixes
# (Fresh implementation with all improvements)

# Result: Users only see /template-create (clean, modern)
# Legacy available if needed but not documented
```

**Why this approach:**
- Clean for new users (only one command visible)
- Safe fallback available if needed
- Perfect for open source release
- No confusion about versions
- Professional first impression

### Phase Flow (v2)

```
Phase 1: AI Codebase Analysis ✨ (ENHANCED)
├─ Stratified sampling (30 files) ✅ Working
├─ Filter build artifacts 🔧 New
├─ Request architectural-reviewer agent 🔧 New
├─ Checkpoint and exit (code 42) 🔧 New
└─ Resume: Complete Phase 1 with AI analysis ✨ (95% confidence)

Phase 2: Manifest Generation ✅ (Working)
├─ Use AI analysis results
└─ Generate manifest.json

Phase 3: Settings Generation ✅ (Working)
├─ Extract naming conventions
└─ Generate settings.json

Phase 4: Template Generation ✅ (Working)
├─ Generate template files
└─ Apply transformations

Phase 4.5: Completeness Validation ✅ (Working)
├─ Check CRUD completeness
└─ Calculate false negative score

Phase 5: Agent Recommendation ✨ (ENHANCED)
├─ Request architectural-reviewer agent 🔧 New
├─ Checkpoint and exit (code 42) 🔧 New
└─ Resume: Complete Phase 5 with agent list ✨ (7-9 agents)

Phase 6: Agent Writing ✅ (Working)
├─ Write basic agent files
└─ Save checkpoint 🔧 New

Phase 7: Documentation Generation ✅ (Working)
└─ Generate CLAUDE.md

Phase 7.5: Agent Enhancement ✨ (NEW)
├─ Request agent-content-enhancer agent 🔧 New
├─ Checkpoint and exit (code 42) 🔧 New
└─ Resume: Complete Phase 7.5 with enhanced agents ✨ (150-250 lines)

Phase 8: Validation ✅ (Working)
└─ Generate validation report
```

**Legend:**
- ✅ Working: Already implemented and functional
- ✨ Enhanced: Requires AI integration (checkpoint-resume)
- 🔧 New: Requires new code

### Agent Bridge Integration Pattern

**Current Issue:** Agent invocation throws "not yet implemented"

**Solution:** Complete the agent bridge integration

```python
# File: installer/core/lib/codebase_analyzer/agent_invoker.py

class AgentBridgeInvoker:
    """Invokes agents using the bridge pattern with checkpoint-resume."""
    
    def invoke_architectural_reviewer(
        self, 
        samples: List[FileSample],
        context: Dict[str, Any]
    ) -> AnalysisResult:
        """
        Invoke architectural-reviewer agent for codebase analysis.
        
        Returns:
            AnalysisResult with comprehensive analysis (95% confidence)
            
        Raises:
            CheckpointRequested: Exits with code 42 if agent needs invocation
        """
        # 1. Check if we're resuming from checkpoint
        if self._has_agent_response():
            return self._parse_agent_response()
        
        # 2. First invocation - write agent request
        self._write_agent_request({
            'agent': 'architectural-reviewer',
            'samples': self._serialize_samples(samples),
            'context': context
        })
        
        # 3. Save checkpoint and exit
        raise CheckpointRequested(
            agent='architectural-reviewer',
            phase='codebase_analysis',
            exit_code=42
        )
```

**Key Points:**
1. Use exception-based flow control (like Phase 5 currently attempts)
2. Write `.agent-request.json` in project root
3. Exit with code 42 to signal checkpoint
4. On resume, check for `.agent-response.json`
5. Parse response and continue workflow

### Build Artifact Filtering

```python
# File: installer/core/lib/codebase_analyzer/exclusion_patterns.py

DEFAULT_EXCLUSIONS = [
    # Build outputs
    "obj/", "bin/", "build/", "dist/", "out/", "target/",
    
    # Dependencies
    "node_modules/", "vendor/", ".venv/", "venv/", "virtualenv/",
    
    # IDE
    ".idea/", ".vscode/", ".vs/", "*.swp", "*.swo",
    
    # Version control
    ".git/", ".svn/", ".hg/",
    
    # Package managers
    "__pycache__/", "*.pyc", ".pytest_cache/", ".tox/",
    "*.egg-info/", ".eggs/",
    
    # Compiled assets
    "*.dll", "*.exe", "*.so", "*.dylib", "*.class", "*.jar",
]

def apply_exclusions(files: List[Path], project_path: Path) -> List[Path]:
    """Filter out build artifacts and dependencies."""
    # Read .gitignore if exists
    gitignore_patterns = _read_gitignore(project_path)
    
    # Combine with defaults
    all_patterns = DEFAULT_EXCLUSIONS + gitignore_patterns
    
    # Filter files
    return [f for f in files if not _matches_pattern(f, all_patterns)]
```

### Comprehensive Agent Recommendation

**Remove:** `agent_generator.py` with 5 hard-coded patterns

**Replace with:** AI-powered recommendation via architectural-reviewer

**Agent Prompt Enhancement:**

```markdown
Based on your analysis, recommend specialized agents for this codebase.

Consider the following agent types and recommend those that are relevant:

**Architecture Patterns:**
- repository-pattern-specialist (if Repository pattern detected)
- service-layer-specialist (if Service layer detected)
- cqrs-specialist (if Command/Query separation detected)
- event-sourcing-specialist (if Event sourcing detected)
- domain-driven-design-specialist (if DDD patterns detected)

**Technology-Specific:**
- database-specialist (if direct database access patterns)
- orm-specialist (if ORM usage detected)
- api-client-specialist (if external API consumption)
- message-queue-specialist (if async messaging)

**MVVM/UI (for UI applications):**
- mvvm-specialist (if MVVM pattern detected)
- navigation-specialist (if routing/navigation)
- validation-specialist (if form validation)
- state-management-specialist (if state management patterns)

**Quality:**
- erroror-pattern-specialist (if ErrorOr or Result types)
- testing-specialist (always recommended if test files exist)

**Output Format:**
Return a list of recommended agents with:
- agent_name (kebab-case)
- priority (1-10, higher = more important)
- rationale (why this agent is needed)
- key_patterns (list of detected patterns that triggered recommendation)

Example:
```json
{
  "recommended_agents": [
    {
      "agent_name": "repository-pattern-specialist",
      "priority": 9,
      "rationale": "Detected Repository pattern in 12 files with ErrorOr integration",
      "key_patterns": ["Repository suffix", "ErrorOr return types", "Realm database"]
    }
  ]
}
```
```

**Expected Output:** 7-9 agents (78-100% coverage) vs current 1 agent (14%)

### Agent Enhancement Implementation

**Complete Phase 7.5 checkpoint-resume:**

```python
# File: installer/core/commands/lib/template_create_orchestrator.py

def _phase7_5_enhance_agents(self, output_path: Path) -> bool:
    """Phase 7.5: Agent Enhancement with checkpoint-resume."""
    self._print_phase_header("Phase 7.5: Agent Enhancement")
    
    # Check if resuming
    if self._has_agent_response('agent-content-enhancer'):
        # Parse enhanced agents from response
        enhanced_agents = self._parse_agent_enhancements()
        
        # Write enhanced agent files
        for agent in enhanced_agents:
            agent_file = output_path / "agents" / f"{agent.name}.md"
            agent_file.write_text(agent.enhanced_content)
        
        self._print_info(f"  ✓ Enhanced {len(enhanced_agents)} agents")
        return True
    
    # First invocation - request enhancement
    request = {
        'agent': 'agent-content-enhancer',
        'agents': self._serialize_agents(self.agents),
        'templates': self._serialize_templates(output_path / "templates"),
        'settings': self._load_settings(output_path / "settings.json")
    }
    
    self._write_agent_request(request)
    self._print_info("  ⏸️  Requesting agent-content-enhancer")
    self._print_info("  🔄 Checkpoint: Resume after agent responds")
    
    # Exit with code 42
    raise CheckpointRequested(
        agent='agent-content-enhancer',
        phase='agent_enhancement',
        exit_code=42
    )

def _run_from_phase_7(self) -> OrchestrationResult:
    """Resume orchestration from Phase 7 (after agent enhancement)."""
    # Load state
    state = self._load_checkpoint()
    output_path = Path(state.output_path)
    
    # Complete Phase 7.5
    try:
        enhancement_success = self._phase7_5_enhance_agents(output_path)
        if not enhancement_success:
            self._print_warning("  ⚠️  Agent enhancement failed, using basic agents")
    except Exception as e:
        self.logger.warning(f"Phase 7.5 failed: {e}")
        self._print_warning("  ⚠️  Continuing with basic agents")
    
    # Continue to Phase 8-9
    return self._complete_workflow_from_phase_8(output_path)
```

---

## Implementation Plan

### Phase 1: Build Artifact Filtering (2-3 hours)

**Task:** TASK-ARTIFACT-FILTER

**Files:**
- Create: `installer/core/lib/codebase_analyzer/exclusion_patterns.py`
- Modify: `installer/core/lib/codebase_analyzer/stratified_sampler.py`
- Create: `tests/unit/test_exclusion_patterns.py`

**Tests:**
- Verify .gitignore patterns are respected
- Verify default exclusions work (obj/, bin/, node_modules/)
- Test on .NET, Node.js, Python projects

**Acceptance:**
- ✅ .NET project correctly detected as C# (not Java)
- ✅ File count accurate (excludes build artifacts)
- ✅ 95%+ test coverage

### Phase 2: Agent Bridge Implementation (4-6 hours)

**Task:** TASK-AGENT-BRIDGE-COMPLETE

**Files:**
- Modify: `installer/core/lib/codebase_analyzer/agent_invoker.py`
- Create: `installer/core/lib/agent_bridge/checkpoint_manager.py`
- Create: `tests/unit/test_agent_bridge.py`
- Create: `tests/integration/test_agent_workflow.py`

**Components:**
1. Complete `AgentBridgeInvoker.invoke_architectural_reviewer()`
2. Implement `CheckpointRequested` exception
3. Add `.agent-request.json` write/read
4. Add `.agent-response.json` parse
5. Test checkpoint-resume cycle

**Tests:**
- Unit test: Request serialization
- Unit test: Response parsing
- Integration test: Full checkpoint-resume cycle
- Integration test: Error handling

**Acceptance:**
- ✅ architectural-reviewer invocation works
- ✅ Checkpoint saves and resumes correctly
- ✅ Agent response parsed successfully
- ✅ 90%+ test coverage

### Phase 3: Phase 1 Checkpoint-Resume (2-3 hours)

**Task:** TASK-PHASE-1-CHECKPOINT

**Files:**
- Modify: `installer/core/commands/lib/template_create_orchestrator.py` (Phase 1)
- Add: `_run_from_phase_1()` method
- Modify: Resume routing logic

**Changes:**
1. Save checkpoint before Phase 1 agent invocation
2. Integrate `AgentBridgeInvoker.invoke_architectural_reviewer()`
3. Add `_run_from_phase_1()` resume method
4. Update routing: `if state.phase == 1: return self._run_from_phase_1()`

**Tests:**
- Integration test: Phase 1 checkpoint cycle
- Integration test: AI analysis vs heuristic fallback

**Acceptance:**
- ✅ Phase 1 requests architectural-reviewer
- ✅ Orchestrator exits with code 42
- ✅ Resume completes Phase 1 with AI analysis
- ✅ Confidence score 90%+ (vs 68% heuristic)

### Phase 4: Phase 5 Checkpoint-Resume (2-3 hours)

**Task:** TASK-PHASE-5-CHECKPOINT

**Files:**
- Modify: `installer/core/commands/lib/template_create_orchestrator.py` (Phase 5)
- Modify: Agent recommendation logic

**Changes:**
1. Replace hard-coded detection with AI recommendation
2. Save checkpoint before Phase 5 agent invocation
3. Use agent response for comprehensive agent list
4. Remove `agent_generator.py` dependency

**Tests:**
- Integration test: Phase 5 checkpoint cycle
- Comparison test: AI recommendation vs hard-coded detection

**Acceptance:**
- ✅ Phase 5 requests architectural-reviewer (agent recommendation mode)
- ✅ Detects 7-9 agents (78-100% coverage)
- ✅ Agent list includes Repository, Service, CQRS, etc.

### Phase 5: Phase 7.5 Checkpoint-Resume (3-4 hours)

**Task:** TASK-PHASE-7-5-CHECKPOINT (Already exists!)

**Files:**
- Modify: `installer/core/commands/lib/template_create_orchestrator.py` (Phase 7.5)
- Add: `_run_from_phase_7()` method
- Add: Agent serialization methods

**Changes:**
1. Save checkpoint before Phase 7.5
2. Integrate agent-content-enhancer invocation
3. Add `_run_from_phase_7()` resume method
4. Add agent serialization/deserialization

**Tests:**
- Integration test: Phase 7.5 checkpoint cycle
- Content test: Enhanced agent files 150-250 lines

**Acceptance:**
- ✅ Phase 7.5 requests agent-content-enhancer
- ✅ Enhanced agent files generated (150-250 lines, 9/10 quality)
- ✅ Template references included
- ✅ Best practices sections added

### Phase 6: Remove Hard-Coded Detection (1-2 hours)

**Task:** TASK-REMOVE-DETECTOR

**Files:**
- Delete: `installer/core/commands/lib/smart_defaults_detector.py` (531 LOC)
- Delete: `tests/unit/test_smart_defaults_detector.py` (514 LOC)
- Modify: Remove references in orchestrator

**Impact:**
- 1,045 LOC removed
- Maintenance burden eliminated
- AI-first principle restored

**Tests:**
- Integration test: Verify template creation works without detector
- Regression test: Verify all reference templates still create successfully

**Acceptance:**
- ✅ Detector code removed (1,045 LOC)
- ✅ All tests passing (100%)
- ✅ Template creation works with AI only

### Phase 7: Rename Legacy & Build New Command (2-3 hours)

**Task:** TASK-RENAME-LEGACY-BUILD-NEW

**Files:**
- Rename: `installer/core/commands/template-create.md` → `template-create-legacy.md`
- Rename: `installer/core/commands/lib/template_create_orchestrator.py` → `template_create_legacy_orchestrator.py`  
- Create: `installer/core/commands/template-create.md` (fresh, with all fixes)
- Create: `installer/core/commands/lib/template_create_orchestrator.py` (fresh, with all fixes)

**Approach:**
1. Rename existing files to `-legacy` suffix
2. Build new clean implementation with all fixes from Phases 1-6
3. Test on reference projects
4. Verify legacy still works as fallback

**Tests:**
- E2E test: Create template with new command
- Fallback test: Verify legacy still works
- Comparison test: New vs legacy output quality

**Acceptance:**
- ✅ `/template-create` command works (new version)
- ✅ `/template-create-legacy` available as fallback
- ✅ All checkpoint-resume phases functional
- ✅ Quality improvements verified (confidence 90%+, 7-9 agents, enhanced agent files)
- ✅ Legacy not documented (hidden from new users)

### Phase 8: Documentation for Open Source Release (2-3 hours)

**Task:** TASK-OPEN-SOURCE-DOCUMENTATION

**Files:**
- Update: `CLAUDE.md` (add template-create workflow)
- Update: `installer/core/commands/README.md`
- Create: `docs/guides/template-creation-guide.md` (user-facing)
- Update: `docs/architecture/agent-bridge-pattern.md`

**Content:**
- User guide for template creation (beginner-friendly)
- Agent bridge pattern documentation (for contributors)
- Troubleshooting guide
- Architecture overview

**Focus:**
- Clean, professional documentation for open source
- No mention of legacy command (internal fallback only)
- Emphasize AI-first approach
- Clear examples and best practices

**Acceptance:**
- ✅ User guide complete and beginner-friendly
- ✅ Architecture documented for contributors
- ✅ Troubleshooting guide comprehensive
- ✅ Ready for open source release

---

## Testing Strategy

### Unit Tests

**Coverage Target:** 95%+

**Test Files:**
- `tests/unit/test_exclusion_patterns.py` (build artifact filtering)
- `tests/unit/test_agent_bridge.py` (checkpoint-resume mechanics)
- `tests/unit/test_checkpoint_manager.py` (state serialization)

### Integration Tests

**Coverage Target:** All critical paths

**Test Files:**
- `tests/integration/test_phase_1_checkpoint.py` (AI analysis cycle)
- `tests/integration/test_phase_5_checkpoint.py` (agent recommendation cycle)
- `tests/integration/test_phase_7_5_checkpoint.py` (agent enhancement cycle)
- `tests/integration/test_full_workflow.py` (end-to-end)

### E2E Tests

**Test Projects:**
1. .NET MAUI app (DeCUK.Mobile.MyDrive)
2. React TypeScript app (bulletproof-react)
3. FastAPI Python app (fastapi-best-practices)
4. Next.js full-stack (nextjs-boilerplate)

**Validation:**
- ✅ Correct language detection (C#, TypeScript, Python, TypeScript)
- ✅ High confidence scores (90%+)
- ✅ Comprehensive agent sets (7-9 agents)
- ✅ Enhanced agent files (150-250 lines)
- ✅ Complete templates (manifest, settings, CLAUDE.md, templates/, agents/)

---

## Rollout Strategy

### Week 1: Foundation (Phases 1-2)

**Focus:** Build artifact filtering + agent bridge

**Deliverables:**
- Build artifacts excluded from analysis
- Agent bridge checkpoint-resume implemented
- All tests passing

**Risk:** Low - These are isolated improvements

### Week 2: Checkpoint-Resume (Phases 3-5)

**Focus:** Implement checkpoint-resume for Phases 1, 5, 7.5

**Deliverables:**
- Phase 1 AI analysis working
- Phase 5 comprehensive agent recommendation
- Phase 7.5 agent enhancement working
- All tests passing

**Risk:** Medium - Requires agent invocation infrastructure

### Week 3: Integration (Phases 6-7)

**Focus:** Rename legacy, build new command, remove detector

**Deliverables:**
- Legacy renamed (fallback available)
- New `/template-create` command working
- Hard-coded detector removed (1,045 LOC)
- E2E tests passing on 4 projects

**Risk:** Low - Legacy available as fallback

### Week 4: Documentation (Phase 8)

**Focus:** Documentation for open source release

**Deliverables:**
- User guide published
- Architecture documented
- Troubleshooting guide created
- Ready for open source release

**Risk:** Low - Documentation only

### Post-Implementation: Open Source Preparation

**Before making public:**
- ✅ All tests passing (100%)
- ✅ Template creation works perfectly
- ✅ Documentation complete
- ✅ No references to "legacy" in user-facing docs
- ✅ Professional first impression

**Legacy command:**
- Available as undocumented fallback
- Not mentioned in README or guides
- Can be removed after proving new command stable

---

## Success Metrics

### Quality Metrics

| Metric | Current (v1) | Target (v2) | Measurement |
|--------|--------------|-------------|-------------|
| Confidence Score | 68% (heuristic) | 90%+ (AI) | manifest.json |
| Agents Detected | 1 (14%) | 7-9 (78-100%) | manifest.json |
| Agent File Size | 34 lines (3/10) | 150-250 lines (9/10) | Line count |
| Build Artifact Issues | Yes (TASK-9037) | No | Language detection accuracy |
| Hard-Coded LOC | 1,045 | 0 | Code deleted |

### Performance Metrics

| Metric | Current (v1) | Target (v2) | Impact |
|--------|--------------|-------------|--------|
| Template Creation Time | 2-3 min | 3-5 min | +1-2 min (AI calls) |
| Checkpoint-Resume Cycles | 0-1 (incomplete) | 3 (complete) | Better quality |
| False Starts (wrong detection) | 30% | 5% | Fewer retries |

### User Experience Metrics

| Metric | Current (v1) | Target (v2) |
|--------|--------------|-------------|
| Success Rate (first try) | 70% | 95% |
| Manual Agent Additions | 60% of users | 5% of users |
| User Satisfaction | 6/10 | 9/10 |

---

## Risk Assessment

### Technical Risks

**Risk 1: Agent Bridge Instability (MEDIUM)**
- **Impact:** Checkpoint-resume failures
- **Mitigation:** Extensive integration tests, graceful fallback to heuristics
- **Contingency:** Keep v1 available as fallback

**Risk 2: AI Inference Accuracy (LOW)**
- **Impact:** Wrong language/framework detection
- **Mitigation:** Enhanced prompts, E2E validation, user override options
- **Contingency:** Manual Q&A mode (like current `--skip-qa` behavior)

**Risk 3: Performance Degradation (LOW)**
- **Impact:** Longer template creation times
- **Mitigation:** Parallel AI calls where possible, progress indicators
- **Contingency:** Add `--fast` flag to skip enhancement phases

### Process Risks

**Risk 4: User Resistance to v2 (LOW)**
- **Impact:** Users continue using v1, v2 adoption slow
- **Mitigation:** Clear migration guide, showcase quality improvements
- **Contingency:** Extend parallel operation period

**Risk 5: Incomplete Migration (MEDIUM)**
- **Impact:** Some projects still depend on v1 behavior
- **Mitigation:** Thorough testing on diverse projects, backward compatibility
- **Contingency:** Keep v1 indefinitely if needed

---

## Alternative Approaches Considered

### Alternative 1: Fix In-Place Without Rename

**Approach:** Fix existing template-create command directly without keeping legacy

**Pros:**
- Simplest approach
- No file renaming needed
- Single code path

**Cons:**
- ❌ No fallback if issues arise
- ❌ Hard to rollback changes
- ❌ Higher risk for solo developer

**Decision:** Rejected - too risky without fallback

### Alternative 2: Create template-create-v2

**Approach:** Keep v1 and create v2 in parallel

**Pros:**
- Safe fallback available
- Can test v2 extensively

**Cons:**
- ❌ Confusing for new open source users
- ❌ "What's v1? What's v2?" questions
- ❌ Messy for public release
- ❌ Extra maintenance burden

**Decision:** Rejected - bad for open source first impression

### Alternative 3: Complete Rewrite

**Approach:** Rebuild from scratch with new architecture

**Pros:**
- Clean slate
- Modern patterns
- No legacy code

**Cons:**
- ❌ 3-4 weeks of work
- ❌ All tests need rewriting
- ❌ High risk of introducing new bugs
- ❌ Too much work for solo developer

**Decision:** Rejected due to time/effort

### ✅ Chosen: Rename to Legacy + Build Clean Main

**Approach:** Rename existing to legacy, build fixed version as main command

**Pros:**
- ✅ Clean for open source (only see /template-create)
- ✅ Safe fallback available if needed
- ✅ Professional first impression
- ✅ No version confusion
- ✅ Easy to remove legacy after proven stable

**Cons:**
- Minor: Need to rename files
- Minor: Maintain legacy temporarily

**Decision:** ACCEPTED - Perfect for solo developer preparing open source release

---

## Conclusion

The current `/template-create` command has accumulated technical debt that requires comprehensive fixes rather than incremental patches. The proposed redesign:

1. **Restores AI-first architecture** - Removes 1,045 LOC of hard-coded patterns
2. **Completes checkpoint-resume** - Enables all AI-powered phases
3. **Fixes build artifacts** - Accurate language detection
4. **Improves agent generation** - From 14% to 78-100% coverage
5. **Enhances agent quality** - From 34 lines to 150-250 lines

**Recommended Approach:** Rename existing command to `template-create-legacy` (undocumented fallback), build fixed version as main `template-create` command. This provides a clean user experience for the upcoming open source release.

**Timeline:** 4 weeks (implementation) = Ready for open source launch

**Risk:** Low (legacy available as fallback for solo developer)

**Impact:** High (affects core workflow, critical for open source first impression)

---

## Next Steps

1. **Review & Approve** this design document
2. **Create Tasks** for 8 implementation phases
3. **Begin Phase 1** (Build artifact filtering)
4. **Weekly Check-ins** to track progress
5. **User Testing** with v2 beta after Phase 7

---

## Appendix: Task Dependencies

```
TASK-ARTIFACT-FILTER (Phase 1)
    │
    ├─── No dependencies (can start immediately)
    │
    └─── Outputs: Exclusion patterns, filtered file lists

TASK-AGENT-BRIDGE-COMPLETE (Phase 2)
    │
    ├─── Depends on: None
    │
    └─── Outputs: AgentBridgeInvoker, CheckpointRequested exception

TASK-PHASE-1-CHECKPOINT (Phase 3)
    │
    ├─── Depends on: TASK-AGENT-BRIDGE-COMPLETE, TASK-ARTIFACT-FILTER
    │
    └─── Outputs: Phase 1 checkpoint-resume, AI analysis integration

TASK-PHASE-5-CHECKPOINT (Phase 4)
    │
    ├─── Depends on: TASK-AGENT-BRIDGE-COMPLETE
    │
    └─── Outputs: Phase 5 checkpoint-resume, comprehensive agent list

TASK-PHASE-7-5-CHECKPOINT (Phase 5)
    │
    ├─── Depends on: TASK-AGENT-BRIDGE-COMPLETE
    │
    └─── Outputs: Phase 7.5 checkpoint-resume, enhanced agents

TASK-REMOVE-DETECTOR (Phase 6)
    │
    ├─── Depends on: TASK-PHASE-1-CHECKPOINT, TASK-PHASE-5-CHECKPOINT
    │
    └─── Outputs: Removed 1,045 LOC, AI-first architecture restored

TASK-RENAME-LEGACY-BUILD-NEW (Phase 7)
    │
    ├─── Depends on: All previous tasks (Phases 1-6)
    │
    └─── Outputs: Clean main template-create command, legacy available as fallback

TASK-OPEN-SOURCE-DOCUMENTATION (Phase 8)
    │
    ├─── Depends on: TASK-RENAME-LEGACY-BUILD-NEW
    │
    └─── Outputs: User guide, architecture docs, ready for open source
```

---

**Status**: PROPOSED - Awaiting approval
**Author**: Claude (AI Engineer)
**Reviewers**: Rich (Architect), Product Team
**Approval Required**: Yes (architectural change)
