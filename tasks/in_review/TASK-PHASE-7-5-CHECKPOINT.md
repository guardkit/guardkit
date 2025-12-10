# TASK: Add Checkpoint-Resume Support for Phase 7.5 (Agent Enhancement)

**Status**: Backlog  
**Priority**: High  
**Complexity**: 5/10  
**Estimated Time**: 45 minutes  
**Dependencies**: None (all infrastructure exists)

---

## Problem Statement

Phase 7.5 (Agent Enhancement) exists in the template creation orchestrator but **fails silently** because it lacks checkpoint-resume support.

### Current Behavior

```python
# Phase 7: Write agents to disk
agent_paths = self._phase7_write_agents(self.agents, output_path)

# Phase 7.5: Agent Enhancement
enhancement_success = self._phase7_5_enhance_agents(output_path)  # ❌ CRASHES HERE

# Phase 8: CLAUDE.md generation
self.claude_md = self._phase8_claude_md_generation(...)
```

**What Happens:**
1. `_phase7_5_enhance_agents()` calls `AgentEnhancer`
2. `AgentEnhancer` needs to invoke `agent-content-enhancer` agent
3. Agent bridge exits with **code 42** to request external invocation
4. **No checkpoint saved before Phase 7.5** → orchestrator crashes
5. Template completes but agents remain **basic (3/10 quality)** instead of **enhanced (9/10 quality)**

### Evidence

From latest template creation run:
```
Phase 7: Agent Writing
✓ 8 agent files written

# Phase 7.5 never appears in output - silent failure!

Phase 8: CLAUDE.md Generation
✓ Architecture overview
```

Agent files show only basic content (30 lines) instead of enhanced content (150-250 lines).

---

## Root Cause

The checkpoint-resume pattern is **only implemented for Phase 5** (agent generation) but **not for Phase 7.5** (agent enhancement).

**Missing Infrastructure:**
1. No checkpoint saved before Phase 7.5
2. No `_run_from_phase_7()` method to resume after Phase 7.5
3. No agent serialization/deserialization methods
4. Resume routing doesn't handle phase 7.5

---

## Solution: Add Checkpoint-Resume for Phase 7.5

Follow the **exact same pattern** used successfully in Phase 5.

### Implementation Steps

#### 1. Add Agent Serialization Methods

Add to `TemplateCreateOrchestrator` class (around line 900, near other serialization methods):

```python
def _serialize_agents(self, agents: List[Any]) -> Optional[List[dict]]:
    """Serialize agents to list of dicts."""
    if not agents:
        return None
    
    result = []
    for agent in agents:
        agent_dict = {}
        if hasattr(agent, '__dict__'):
            agent_dict = agent.__dict__.copy()
            # Convert Path and datetime objects to strings for JSON serialization
            for key, value in agent_dict.items():
                if isinstance(value, Path):
                    agent_dict[key] = str(value)
                elif isinstance(value, datetime):
                    agent_dict[key] = value.isoformat()
        result.append(agent_dict)
    return result

def _deserialize_agents(self, data: Optional[List[dict]]) -> List[Any]:
    """Deserialize list of dicts back to agent objects."""
    if not data:
        return []
    
    agents = []
    for agent_dict in data:
        agent_obj = type('GeneratedAgent', (), agent_dict)()
        agents.append(agent_obj)
    return agents
```

#### 2. Add Checkpoint Before Phase 7.5

Modify `_complete_workflow()` method (around line 290):

```python
def _complete_workflow(self) -> OrchestrationResult:
    """Complete phases 6-9."""
    
    # ... existing code ...
    
    # Phase 7: Agent Writing
    if self.agents:
        agent_paths = self._phase7_write_agents(self.agents, output_path)
        if not agent_paths:
            self.warnings.append("Agent writing failed")
        else:
            # CRITICAL: Save checkpoint BEFORE Phase 7.5
            self._save_checkpoint("agents_written", phase=7)
            
            # Phase 7.5: Agent Enhancement (may exit with code 42)
            enhancement_success = self._phase7_5_enhance_agents(output_path)
            if not enhancement_success:
                self.warnings.append("Agent enhancement had issues (workflow continuing)")
    
    # Phase 8: CLAUDE.md Generation
    # ... rest of workflow ...
```

#### 3. Update Checkpoint Save to Include Agents

Modify `_save_checkpoint()` method (around line 820) to save agents:

```python
def _save_checkpoint(self, checkpoint: str, phase: int) -> None:
    """Save current state to checkpoint."""
    
    # Serialize phase data
    phase_data = {
        "qa_answers": self.qa_answers,
        "analysis": self._serialize_analysis(self.analysis),
        "manifest": self._serialize_manifest(self.manifest),
        "settings": self._serialize_settings(self.settings),
        "templates": self._serialize_templates(self.templates),
        "agent_inventory": self.agent_inventory,
        "agents": self._serialize_agents(self.agents)  # ← ADD THIS LINE
    }
    
    # ... rest of method ...
```

#### 4. Update Resume to Restore Agents

Modify `_resume_from_checkpoint()` method (around line 740) to restore agents:

```python
def _resume_from_checkpoint(self) -> None:
    """Restore state from checkpoint."""
    
    # ... existing restoration code ...
    
    if "templates" in phase_data and phase_data["templates"]:
        self.templates = self._deserialize_templates(phase_data["templates"])
    
    self.agent_inventory = phase_data.get("agent_inventory")
    
    # ADD THIS BLOCK:
    if "agents" in phase_data and phase_data["agents"]:
        self.agents = self._deserialize_agents(phase_data["agents"])
    
    # ... rest of method ...
```

#### 5. Add Phase 7 Resume Method

Add new method to `TemplateCreateOrchestrator` class (around line 280):

```python
def _run_from_phase_7(self) -> OrchestrationResult:
    """
    Continue from Phase 7.5 after agent invocation.
    
    State has been restored in __init__, now complete agent enhancement.
    
    Returns:
        OrchestrationResult with success status and generated artifacts
    """
    self._print_header()
    print("  (Resuming from checkpoint - Phase 7.5)")
    
    # Determine output path (needed for enhancement)
    if self.config.output_path:
        output_path = self.config.output_path
    elif self.config.output_location == 'repo':
        output_path = Path("installer/core/templates") / self.manifest.name
    else:
        output_path = Path.home() / ".agentecflow" / "templates" / self.manifest.name
    
    # Phase 7.5: Complete agent enhancement with loaded response
    enhancement_success = self._phase7_5_enhance_agents(output_path)
    if not enhancement_success:
        self.warnings.append("Agent enhancement had issues (workflow continuing)")
    
    # Continue with Phase 8-9
    return self._complete_workflow_from_phase_8(output_path)
```

#### 6. Create Phase 8 Resume Helper

Add helper method to complete workflow from Phase 8 onwards:

```python
def _complete_workflow_from_phase_8(self, output_path: Path) -> OrchestrationResult:
    """
    Complete phases 8-9 after resuming from Phase 7.5.
    
    Args:
        output_path: Template output directory
        
    Returns:
        OrchestrationResult with success status and generated artifacts
    """
    # Phase 8: CLAUDE.md Generation
    self.claude_md = self._phase8_claude_md_generation(self.analysis, self.agents, output_path)
    if not self.claude_md:
        return self._create_error_result("CLAUDE.md generation failed")
    
    # Phase 9: Template Package Assembly
    output_path = self._phase9_package_assembly(
        manifest=self.manifest,
        settings=self.settings,
        claude_md=self.claude_md,
        templates=self.templates,
        output_path=output_path
    )
    
    if not output_path:
        return self._create_error_result("Package assembly failed")
    
    # Phase 9.5: Extended Validation (if enabled)
    validation_report_path = None
    exit_code = 0
    if self.config.validate and self.templates:
        validation_report_path, exit_code = self._phase9_5_extended_validation(
            templates=self.templates,
            manifest=self.manifest,
            settings=self.settings,
            claude_md_path=output_path / "CLAUDE.md",
            agents=self.agents,
            output_path=output_path
        )
    
    # Cleanup state on success
    self.state_manager.cleanup()
    
    # Success!
    location_type = "personal" if self.config.output_location == 'global' else "distribution"
    if self.config.output_path:
        location_type = "custom"
    self._print_success(output_path, self.manifest, self.templates, self.agents, location_type, validation_report_path)
    
    return OrchestrationResult(
        success=True,
        template_name=self.manifest.name,
        output_path=output_path,
        manifest_path=output_path / "manifest.json",
        settings_path=output_path / "settings.json",
        claude_md_path=output_path / "CLAUDE.md",
        template_count=len(self.templates.templates) if self.templates else 0,
        agent_count=len(self.agents),
        confidence_score=self.manifest.confidence_score,
        errors=self.errors,
        warnings=self.warnings,
        validation_report_path=validation_report_path,
        exit_code=exit_code
    )
```

#### 7. Update Resume Routing

Modify `run()` method (around line 165) to route to Phase 7 resume:

```python
def run(self) -> OrchestrationResult:
    """Execute complete template creation workflow."""
    
    try:
        # If resuming, route to appropriate phase
        if self.config.resume:
            # Load state to determine which phase to resume from
            state = self.state_manager.load_state()
            
            if state.phase == 4:
                # Resume from Phase 5 (agent generation)
                return self._run_from_phase_5()
            elif state.phase == 7:
                # Resume from Phase 7.5 (agent enhancement)
                return self._run_from_phase_7()
            else:
                self._print_error(f"Unknown resume phase: {state.phase}")
                return self._create_error_result("Invalid checkpoint phase")
        
        # Normal execution: Phases 1-7
        return self._run_all_phases()
    
    except KeyboardInterrupt:
        self._print_info("\n\nTemplate creation interrupted.")
        return self._create_error_result("User interrupted")
    except Exception as e:
        logger.exception("Unexpected error in orchestration")
        return self._create_error_result(f"Unexpected error: {e}")
```

---

## Acceptance Criteria

### Must Have

- [ ] Agent serialization/deserialization methods implemented
- [ ] Checkpoint saved before Phase 7.5 execution
- [ ] `_run_from_phase_7()` method implemented
- [ ] Resume routing handles phase 7.5 correctly
- [ ] Phase 7.5 exits with code 42 when agent invocation needed
- [ ] External command loop resumes orchestrator correctly
- [ ] Template creation completes successfully with enhanced agents

### Validation

- [ ] Run `/template-create --name test-checkpoint --validate`
- [ ] Verify Phase 7.5 appears in output
- [ ] Verify agent files are 150-250 lines (enhanced, not 30 lines basic)
- [ ] Verify validation report shows agent enhancement success
- [ ] Verify checkpoint files created in codebase directory
- [ ] Verify checkpoint files cleaned up on success

### Quality Checks

- [ ] Enhanced agent files contain:
  - Purpose section (50-100 words)
  - When to Use section (3-4 scenarios)
  - Related Templates section (2-3 primary templates)
  - Example Pattern section (code snippet)
  - Best Practices section (3-5 practices)
- [ ] Agent files reference actual template paths (not invented)
- [ ] Overall quality score improves: 7/10 → 9/10

---

## Testing Strategy

### Unit Tests

Create `tests/unit/test_phase_7_5_checkpoint.py`:

```python
def test_serialize_agents():
    """Test agent serialization."""
    # Test with various agent structures
    # Verify all fields serialized correctly
    # Verify Path and datetime conversion

def test_deserialize_agents():
    """Test agent deserialization."""
    # Test roundtrip serialization
    # Verify object reconstruction

def test_checkpoint_save_includes_agents():
    """Test checkpoint saves agent data."""
    # Mock agents with various content
    # Save checkpoint
    # Verify agents in saved state

def test_resume_restores_agents():
    """Test resume restores agent data."""
    # Create checkpoint with agents
    # Resume from checkpoint
    # Verify agents restored correctly
```

### Integration Tests

Create `tests/integration/test_phase_7_5_workflow.py`:

```python
def test_full_enhancement_workflow():
    """Test complete Phase 7.5 checkpoint-resume flow."""
    # Run template-create to Phase 7.5
    # Verify exit code 42
    # Verify checkpoint created
    # Mock agent response
    # Resume orchestrator
    # Verify completion
    # Verify enhanced agents

def test_enhancement_with_actual_codebase():
    """Test enhancement on real codebase."""
    # Use test codebase
    # Run full workflow
    # Verify agent quality
    # Compare before/after enhancement
```

---

## Implementation Notes

### Pattern to Follow

**Phase 5 Implementation** (working reference):
- Line 210: `_run_from_phase_5()` method
- Line 285: Checkpoint save before Phase 5
- Line 570: `_serialize_analysis()` method
- Line 740: `_resume_from_checkpoint()` restoration

**Use the exact same structure** for Phase 7.5.

### Key Differences from Phase 5

1. **Simpler serialization**: Agents are just dicts, not complex Pydantic models
2. **Different resume point**: Continue to Phase 8, not Phase 6-7
3. **Output path handling**: Need to reconstruct output_path in resume method

### Error Handling

Must handle gracefully:
- Agent invocation timeout
- Agent invocation error
- Missing agent files
- Serialization errors
- Checkpoint corruption

**Fallback behavior**: If enhancement fails, continue with basic agents (don't block workflow).

---

## Related Files

**Primary File:**
- `/Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/commands/lib/template_create_orchestrator.py`

**Reference Implementations:**
- Phase 5 checkpoint-resume (lines 210-280)
- Serialization methods (lines 820-920)
- Agent enhancement (lines 500-540)

**Supporting Files:**
- `/Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/lib/template_creation/agent_enhancer.py`
- `/Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/lib/agent_bridge/invoker.py`

---

## Success Metrics

**Before Implementation:**
- Agent files: 30 lines (basic)
- Agent quality: 3/10
- Enhancement phase: Missing from output
- Template quality: 7-8/10

**After Implementation:**
- Agent files: 150-250 lines (enhanced)
- Agent quality: 9/10
- Enhancement phase: Visible in output with success message
- Template quality: 9-10/10

---

## Risks and Mitigations

### Risk: Agent serialization edge cases
**Mitigation**: Use simple dict serialization like Phase 5, test with various agent structures

### Risk: Resume routing complexity
**Mitigation**: Add clear phase number checks, use existing pattern from Phase 5

### Risk: Output path reconstruction
**Mitigation**: Store output_path in checkpoint config, use same logic as Phase 5

### Risk: Breaking existing functionality
**Mitigation**: Extensive testing, fallback to basic agents on error

---

## Documentation Updates

After implementation, update:

1. **template-create.md** - Add Phase 7.5 to workflow documentation
2. **SESSION-SUMMARY-PHASE-7-5-CHECKPOINT.md** - Create implementation summary
3. **Agent enhancement documentation** - Note checkpoint-resume requirement

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Unit tests passing (>90% coverage)
- [ ] Integration tests passing
- [ ] Manual testing with real codebase successful
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] Enhanced agents verified (150-250 lines, proper structure)
- [ ] Template quality score 9+/10 achieved

---

**Priority Justification**: High - This bug blocks a major quality feature (agent enhancement) that transforms basic agent files (3/10) into comprehensive, template-aware agents (9/10). The infrastructure exists but silently fails, making templates less valuable.

**Complexity Justification**: 5/10 - Pattern already exists in Phase 5, just needs adaptation. Main complexity is in ensuring proper serialization and resume routing.
