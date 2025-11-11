# TASK-BRIDGE-002: Integrate Bridge with Template Create Orchestrator

**Status**: in_review
**Priority**: high
**Estimated Duration**: 2-3 hours
**Tags**: #bridge #ai-integration #orchestrator #python

---

## Description

Integrate `AgentBridgeInvoker` and `StateManager` into the template creation orchestrator to enable checkpoint-resume workflow. This allows the orchestrator to request agent invocations and resume execution after Claude responds.

**Part of**: Python↔Claude Agent Invocation Bridge (Critical Feature)
**See**: `docs/proposals/python-claude-bridge-technical-spec.md`

**Depends on**: TASK-BRIDGE-001 (Agent Bridge Infrastructure)

---

## Context

The orchestrator currently instantiates `AIAgentGenerator` without an `ai_invoker`, causing it to use `DefaultAgentInvoker` which raises `NotImplementedError`. This task integrates the bridge so agent generation can request AI analysis via Claude.

---

## Acceptance Criteria

- [ ] `template_create_orchestrator.py` modified to support `--resume` flag
- [ ] Orchestrator creates `AgentBridgeInvoker` instance
- [ ] Orchestrator passes bridge invoker to `AIAgentGenerator`
- [ ] State checkpoint saved before Phase 6 (agent generation)
- [ ] Resume logic implemented to load state and continue from Phase 6
- [ ] State cleanup on successful completion
- [ ] All existing tests still pass
- [ ] New integration tests added and passing

---

## Implementation Plan

### Files to Modify

1. `installer/global/commands/lib/template_create_orchestrator.py` (~100 lines changed)

### Files to Create

1. `tests/integration/lib/test_orchestrator_bridge_integration.py` (~150 lines)

### Implementation Steps

#### Step 1: Add Imports (5 min)
```python
from installer.global.lib.agent_bridge.invoker import AgentBridgeInvoker
from installer.global.lib.agent_bridge.state_manager import StateManager, TemplateCreateState
```

#### Step 2: Modify OrchestrationConfig (10 min)
Add `resume` parameter to config:
```python
@dataclass
class OrchestrationConfig:
    # ... existing fields ...
    resume: bool = False  # NEW: Whether this is a resume run
```

#### Step 3: Modify TemplateCreateOrchestrator.__init__() (15 min)
```python
def __init__(self, config: OrchestrationConfig):
    self.config = config
    self.state_manager = StateManager()
    self.agent_invoker = AgentBridgeInvoker(
        phase=6,
        phase_name="agent_generation"
    )

    # Storage for phase results
    self.qa_answers = None
    self.analysis = None
    self.manifest = None
    self.settings = None
    self.templates = None
    self.agent_inventory = None
    self.agents = None
    self.claude_md = None

    # If resuming, load state
    if self.config.resume:
        self._resume_from_checkpoint()
```

#### Step 4: Implement _resume_from_checkpoint() (30 min)
```python
def _resume_from_checkpoint(self) -> None:
    """Restore state from checkpoint"""
    print("\n🔄 Resuming from checkpoint...")

    state = self.state_manager.load_state()
    print(f"  Checkpoint: {state.checkpoint}")
    print(f"  Phase: {state.phase}")

    # Restore configuration
    for key, value in state.config.items():
        setattr(self.config, key, value)

    # Restore phase data
    phase_data = state.phase_data

    self.qa_answers = phase_data.get("qa_answers")

    # Deserialize analysis (convert dict back to object)
    if "analysis" in phase_data:
        analysis_dict = phase_data["analysis"]
        self.analysis = self._deserialize_analysis(analysis_dict)

    # Restore other phase results
    self.manifest = self._deserialize_manifest(phase_data.get("manifest"))
    self.settings = self._deserialize_settings(phase_data.get("settings"))
    self.templates = [
        self._deserialize_template(t)
        for t in phase_data.get("templates", [])
    ]
    self.agent_inventory = phase_data.get("agent_inventory")

    # Load agent response
    try:
        response = self.agent_invoker.load_response()
        print(f"  ✓ Agent response loaded successfully")
    except Exception as e:
        print(f"  ⚠️  Failed to load agent response: {e}")
        print(f"  → Will fall back to hard-coded detection")
```

#### Step 5: Modify run() Method (20 min)
```python
def run(self) -> OrchestrationResult:
    """Execute orchestration workflow"""

    # If resuming, skip to Phase 6
    if self.config.resume:
        return self._run_from_phase_6()

    # Normal execution: Phases 1-8
    return self._run_all_phases()
```

#### Step 6: Implement _run_all_phases() (30 min)
```python
def _run_all_phases(self) -> OrchestrationResult:
    """Execute phases 1-8 from start"""

    # Phases 1-5 (unchanged from current implementation)
    self.qa_answers = self._phase1_qa_session()
    if not self.qa_answers:
        return self._create_error_result("Q&A cancelled")

    self.analysis = self._phase2_ai_analysis(self.qa_answers)
    if not self.analysis:
        return self._create_error_result("Analysis failed")

    self.manifest = self._phase3_manifest_generation(self.analysis, self.qa_answers)
    if not self.manifest:
        return self._create_error_result("Manifest generation failed")

    self.settings = self._phase4_settings_generation(self.analysis)
    if not self.settings:
        return self._create_error_result("Settings generation failed")

    self.templates = self._phase5_template_generation(self.analysis)
    if not self.templates:
        return self._create_error_result("Template generation failed")

    # IMPORTANT: Save state before Phase 6
    # (Phase 6 may exit with code 42 to request agent invocation)
    self._save_checkpoint("templates_generated", phase=5)

    # Phase 6: Agent generation (may exit with code 42)
    self.agents = self._phase6_agent_recommendation(self.analysis)

    # Phase 7-8: Complete workflow
    self.claude_md = self._phase7_claude_md_generation(self.analysis, self.agents)
    if not self.claude_md:
        return self._create_error_result("CLAUDE.md generation failed")

    result = self._phase8_assembly(...)

    # Cleanup state on success
    self.state_manager.cleanup()

    return result
```

#### Step 7: Implement _run_from_phase_6() (20 min)
```python
def _run_from_phase_6(self) -> OrchestrationResult:
    """Continue from Phase 6 after agent invocation"""

    # Phase 6: Complete agent generation with loaded response
    self.agents = self._phase6_agent_recommendation(self.analysis)

    # Phase 7-8: Complete workflow
    self.claude_md = self._phase7_claude_md_generation(self.analysis, self.agents)
    if not self.claude_md:
        return self._create_error_result("CLAUDE.md generation failed")

    result = self._phase8_assembly(...)

    # Cleanup state on success
    self.state_manager.cleanup()

    return result
```

#### Step 8: Modify _phase6_agent_recommendation() (15 min)
```python
def _phase6_agent_recommendation(self, analysis: Any) -> List[Any]:
    """Phase 6: Agent Recommendation (MODIFIED for bridge integration)"""
    self._print_phase_header("Phase 6: Agent Recommendation")

    try:
        from installer.global.lib.agent_scanner import scan_agents

        inventory = scan_agents()

        # CRITICAL: Pass AgentBridgeInvoker to generator
        generator = AIAgentGenerator(
            inventory,
            ai_invoker=self.agent_invoker  # ← BRIDGE INTEGRATION
        )

        # This may exit with code 42 if agent invocation needed
        agents = generator.generate(analysis)

        if agents:
            self._print_info(f"  Generated {len(agents)} custom agents")
        else:
            self._print_info("  All capabilities covered by existing agents")

        return agents

    except SystemExit as e:
        # Code 42 is expected - re-raise to exit orchestrator
        if e.code == 42:
            raise
        # Other exit codes are errors
        self._print_error(f"Agent generation exited with code {e.code}")
        return []

    except Exception as e:
        self._print_warning(f"Agent generation failed: {e}")
        return []
```

#### Step 9: Implement _save_checkpoint() (20 min)
```python
def _save_checkpoint(self, checkpoint: str, phase: int) -> None:
    """Save current state to checkpoint"""

    # Serialize phase data
    phase_data = {
        "qa_answers": self.qa_answers,
        "analysis": self._serialize_analysis(self.analysis),
        "manifest": self._serialize_manifest(self.manifest),
        "settings": self._serialize_settings(self.settings),
        "templates": [
            self._serialize_template(t) for t in (self.templates or [])
        ],
        "agent_inventory": self.agent_inventory
    }

    # Save state
    self.state_manager.save_state(
        checkpoint=checkpoint,
        phase=phase,
        config=self.config.__dict__,
        phase_data=phase_data
    )

    print(f"  💾 State saved (checkpoint: {checkpoint})")
```

#### Step 10: Implement Serialization Helpers (30 min)
```python
def _serialize_analysis(self, analysis: Any) -> dict:
    """Convert analysis object to dict"""
    if hasattr(analysis, '__dict__'):
        return analysis.__dict__
    return analysis

def _deserialize_analysis(self, data: dict) -> Any:
    """Convert dict back to analysis object"""
    # Recreate the analysis object structure
    # This depends on the CodebaseAnalysis class structure
    from installer.global.lib.codebase_analyzer.models import CodebaseAnalysis
    return CodebaseAnalysis(**data)

# Similar for manifest, settings, templates...
```

#### Step 11: Write Integration Tests (30 min)
```python
# tests/integration/lib/test_orchestrator_bridge_integration.py

def test_orchestrator_saves_state_before_phase_6():
    """Test that orchestrator saves state before agent generation"""
    # Setup mock config
    config = OrchestrationConfig(...)

    orchestrator = TemplateCreateOrchestrator(config)

    # Mock phases 1-5 to complete successfully
    ...

    # Run orchestrator (should exit with code 42)
    with pytest.raises(SystemExit) as exc_info:
        orchestrator.run()

    assert exc_info.value.code == 42
    assert Path(".template-create-state.json").exists()
    assert Path(".agent-request.json").exists()

def test_orchestrator_resumes_from_checkpoint():
    """Test that orchestrator can resume from saved state"""
    # Setup: Run orchestrator, let it save state and exit
    ...

    # Write mock agent response
    mock_response = {...}
    Path(".agent-response.json").write_text(json.dumps(mock_response))

    # Create resume config
    resume_config = OrchestrationConfig(resume=True, ...)
    orchestrator = TemplateCreateOrchestrator(resume_config)

    # Run should complete successfully
    result = orchestrator.run()

    assert result.success
    assert not Path(".template-create-state.json").exists()  # Cleanup
```

---

## Testing

```bash
# Run all orchestrator tests
pytest tests/unit/lib/test_template_create_orchestrator.py -v
pytest tests/integration/lib/test_orchestrator_bridge_integration.py -v

# Expected: All tests pass
```

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Orchestrator integrates bridge invoker
- [ ] Checkpoint-resume logic implemented
- [ ] State serialization/deserialization works
- [ ] All existing tests still pass
- [ ] New integration tests pass
- [ ] Code reviewed for quality

---

## Related Tasks

- TASK-BRIDGE-001: Agent Bridge Infrastructure (PREREQUISITE)
- TASK-BRIDGE-003: Command Integration
- TASK-BRIDGE-004: End-to-End Testing

---

## References

- [Technical Specification](../../docs/proposals/python-claude-bridge-technical-spec.md#component-3-orchestrator-integration)
- [Orchestrator File](../../installer/global/commands/lib/template_create_orchestrator.py)
