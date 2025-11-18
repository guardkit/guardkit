# TASK-PHASE-1-CHECKPOINT: Enable AI Analysis in Phase 1

**Task ID**: TASK-PHASE-1-CHECKPOINT
**Title**: Implement Checkpoint-Resume for Phase 1 AI Codebase Analysis
**Status**: BACKLOG
**Priority**: HIGH
**Complexity**: 5/10 (Medium)
**Estimated Hours**: 2-3
**Phase**: 3 of 8 (Template-Create Redesign)

---

## Problem Statement

### Current Issue

Phase 1 codebase analysis falls back to heuristics instead of using AI, resulting in 68% confidence instead of 90%+.

```
Agent invocation failed: Agent invocation not yet implemented.
Using fallback heuristics.
Confidence: 68%
```

### Impact

- Lower confidence scores (68% vs 90%+)
- Less accurate technology detection
- Incomplete pattern recognition
- Downstream phases receive poor input

---

## Solution Design

### Approach

Implement checkpoint-resume pattern in Phase 1:
1. Save checkpoint before agent invocation
2. Write agent request file
3. Exit with code 42
4. On resume, parse agent response
5. Continue workflow with AI analysis results

### Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `installer/global/commands/lib/template_create_orchestrator.py` | MODIFY | Add checkpoint logic to Phase 1 |

---

## Implementation Details

### Phase 1 with Checkpoint-Resume

```python
# In template_create_orchestrator.py

from installer.global.lib.agent_bridge.invoker import (
    AgentBridgeInvoker,
    CheckpointRequested
)
from installer.global.lib.agent_bridge.state_manager import (
    StateManager,
    TemplateCreateState
)
from installer.global.lib.template_creation.prompts import (
    PHASE_1_ANALYSIS_PROMPT,
    PHASE_1_CONFIDENCE_THRESHOLD
)


class TemplateCreateOrchestrator:
    def __init__(self, ...):
        # ... existing init ...
        self.state_manager = StateManager()
        self.agent_invoker = AgentBridgeInvoker(phase=1, phase_name="codebase_analysis")

    def _phase1_ai_analysis(
        self,
        samples: List[FileSample],
        output_path: Path
    ) -> CodebaseAnalysis:
        """
        Phase 1: AI Codebase Analysis with checkpoint-resume.

        Args:
            samples: Stratified file samples
            output_path: Template output directory

        Returns:
            CodebaseAnalysis result

        Raises:
            CheckpointRequested: If external agent invocation needed
        """
        self._print_phase_header("Phase 1: AI Codebase Analysis")

        # Check if resuming with response
        if self.agent_invoker.has_response():
            self._print_info("  Resuming from checkpoint...")
            return self._complete_phase_1_from_response(samples)

        # Check if we have a direct invoker
        if self.agent_invoker and hasattr(self.agent_invoker, 'invoke_directly'):
            return self._phase1_direct_invocation(samples)

        # Need external invocation - save checkpoint
        self._print_info("  Requesting architectural-reviewer for analysis...")

        # Build prompt
        prompt = PHASE_1_ANALYSIS_PROMPT.format(
            file_samples=self._serialize_samples(samples)
        )

        # Create agent request
        request = {
            "request_id": str(uuid.uuid4()),
            "version": "1.0",
            "phase": 1,
            "phase_name": "codebase_analysis",
            "agent_name": "architectural-reviewer",
            "prompt": prompt,
            "context": {
                "project_path": str(self.project_path),
                "output_path": str(output_path),
                "template_name": self.template_name
            },
            "timeout_seconds": 120,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }

        # Save checkpoint using existing StateManager API
        self.state_manager.save_state(
            checkpoint="before_ai_analysis",
            phase=1,
            config={
                "codebase_path": str(self.project_path),
                "output_location": self.output_location,
                "template_name": self.template_name,
                "output_path": str(output_path)
            },
            phase_data={
                "samples": self._serialize_samples(samples)
            },
            agent_request_pending={
                "agent_name": "architectural-reviewer",
                "request_id": request["request_id"]
            }
        )

        # Write request file for agent bridge
        Path(".agent-request.json").write_text(
            json.dumps(request, indent=2),
            encoding="utf-8"
        )

        self._print_info("  📝 Request written to: .agent-request.json")
        self._print_info("  🔄 Checkpoint: Resume after agent responds")

        # Exit for external invocation
        raise CheckpointRequested(
            agent_name="architectural-reviewer",
            phase=1,
            phase_name="codebase_analysis"
        )

    def _complete_phase_1_from_response(
        self,
        samples: List[FileSample]
    ) -> CodebaseAnalysis:
        """
        Complete Phase 1 using agent response from checkpoint.

        Args:
            samples: Original file samples

        Returns:
            CodebaseAnalysis from AI response
        """
        response = self.checkpoint_manager.load_agent_response()

        if not response:
            self._print_warning("  ⚠️  No agent response found, using fallback")
            return self._fallback_to_heuristics(samples)

        if response.get("status") != "success":
            error_msg = response.get("error_message", "Unknown error")
            self._print_warning(f"  ⚠️  Agent failed: {error_msg}")
            return self._fallback_to_heuristics(samples)

        try:
            # Parse AI response
            analysis_data = json.loads(response.get("response", "{}"))

            # Check confidence
            confidence = analysis_data.get("overall_confidence", 0)
            if confidence < PHASE_1_CONFIDENCE_THRESHOLD:
                self._print_warning(
                    f"  ⚠️  Low AI confidence ({confidence:.0%}), using fallback"
                )
                return self._fallback_to_heuristics(samples)

            # Build CodebaseAnalysis from response
            analysis = CodebaseAnalysis.from_ai_response(analysis_data)

            self._print_info(f"  ✓ AI analysis complete (confidence: {confidence:.0%})")
            self._print_info(f"  ✓ Language: {analysis.primary_language}")
            self._print_info(f"  ✓ Framework: {analysis.framework}")
            self._print_info(f"  ✓ Patterns: {len(analysis.patterns)} detected")

            return analysis

        except json.JSONDecodeError as e:
            self._print_warning(f"  ⚠️  Failed to parse response: {e}")
            return self._fallback_to_heuristics(samples)

    def _run_from_phase_1(self) -> OrchestrationResult:
        """
        Resume orchestration from Phase 1 checkpoint.

        Called when orchestrator detects a Phase 1 checkpoint and agent response.
        """
        self._print_info("Resuming from Phase 1 checkpoint...")

        # Load state
        state = self.checkpoint_manager.load_checkpoint()
        if not state:
            raise OrchestrationError("Failed to load checkpoint state")

        output_path = Path(state.output_path)

        # Deserialize samples
        samples = self._deserialize_samples(state.phase_data.get("samples", []))

        # Complete Phase 1 with response
        analysis = self._complete_phase_1_from_response(samples)

        # Continue with remaining phases
        return self._continue_from_phase_2(analysis, output_path)

    def _serialize_samples(self, samples: List[FileSample]) -> List[Dict]:
        """Serialize file samples for checkpoint."""
        return [
            {
                "path": str(s.path),
                "content": s.content,
                "extension": s.extension,
                "size": s.size
            }
            for s in samples
        ]

    def _deserialize_samples(self, data: List[Dict]) -> List[FileSample]:
        """Deserialize file samples from checkpoint."""
        return [
            FileSample(
                path=Path(d["path"]),
                content=d["content"],
                extension=d["extension"],
                size=d["size"]
            )
            for d in data
        ]

    def run(self) -> OrchestrationResult:
        """Main orchestration entry point."""
        # Check if resuming from checkpoint
        if self.checkpoint_manager.is_resuming():
            state = self.checkpoint_manager.load_checkpoint()
            if state:
                if state.phase == 1 and self.checkpoint_manager.has_agent_response():
                    return self._run_from_phase_1()
                # ... other phase resume routing ...

        # Normal flow - start from beginning
        return self._run_full_workflow()
```

### CodebaseAnalysis.from_ai_response()

```python
# In codebase_analyzer/models.py

@dataclass
class CodebaseAnalysis:
    """Result of codebase analysis."""
    primary_language: str
    secondary_languages: List[str]
    framework: str
    framework_version: Optional[str]
    architecture_pattern: str
    layers: List[str]
    patterns: List[PatternDetection]
    testing_framework: str
    confidence: float

    @classmethod
    def from_ai_response(cls, data: Dict[str, Any]) -> "CodebaseAnalysis":
        """Create CodebaseAnalysis from AI response JSON."""
        tech = data.get("technology_stack", {})
        arch = data.get("architecture", {})
        testing = data.get("testing", {})

        patterns = [
            PatternDetection(
                name=p["name"],
                category=p.get("category", "other"),
                confidence=p["confidence"],
                example_files=p.get("example_files", []),
                usage_frequency=p.get("usage_frequency", "common")
            )
            for p in data.get("patterns", [])
        ]

        # Get primary framework
        frameworks = tech.get("frameworks", [])
        framework = frameworks[0]["name"] if frameworks else "Unknown"
        framework_version = frameworks[0].get("version") if frameworks else None

        return cls(
            primary_language=tech.get("primary_language", "Unknown"),
            secondary_languages=tech.get("secondary_languages", []),
            framework=framework,
            framework_version=framework_version,
            architecture_pattern=arch.get("pattern", "Unknown"),
            layers=arch.get("layers", []),
            patterns=patterns,
            testing_framework=testing.get("framework", "Unknown"),
            confidence=data.get("overall_confidence", 0.0)
        )
```

---

## Acceptance Criteria

### Functional

- [ ] Phase 1 saves checkpoint before agent invocation
- [ ] Agent request file (.agent-request.json) written correctly
- [ ] Exit code 42 signals checkpoint
- [ ] Resume parses agent response correctly
- [ ] Confidence threshold (0.70) triggers fallback
- [ ] 90%+ confidence on reference projects

### Quality

- [ ] Test coverage >= 90%
- [ ] Handles malformed response gracefully
- [ ] Cleanup on success

---

## Test Specifications

### Integration Tests

```python
# tests/integration/test_phase_1_checkpoint.py

class TestPhase1Checkpoint:
    """Integration tests for Phase 1 checkpoint-resume."""

    def test_checkpoint_saved_before_invocation(self, tmp_path, monkeypatch):
        """Test that checkpoint is saved before agent invocation."""
        orchestrator = TemplateCreateOrchestrator(
            project_path=tmp_path,
            template_name="test"
        )

        # Should raise CheckpointRequested
        with pytest.raises(CheckpointRequested) as exc_info:
            orchestrator._phase1_ai_analysis(
                samples=[...],
                output_path=tmp_path / "output"
            )

        assert exc_info.value.agent_name == "architectural-reviewer"
        assert exc_info.value.phase == 1

        # Verify files created
        assert (tmp_path / ".template-create-state.json").exists()
        assert (tmp_path / ".agent-request.json").exists()

    def test_resume_with_successful_response(self, tmp_path):
        """Test resuming with successful agent response."""
        # Setup checkpoint
        manager = CheckpointManager(...)
        state = TemplateCreateState(phase=1, ...)
        manager.save_checkpoint(state)

        # Write response
        response = {
            "status": "success",
            "response": json.dumps({
                "technology_stack": {"primary_language": "Python"},
                "overall_confidence": 0.92
            })
        }
        (tmp_path / ".agent-response.json").write_text(json.dumps(response))

        # Resume
        orchestrator = TemplateCreateOrchestrator(...)
        result = orchestrator._run_from_phase_1()

        assert result.analysis.primary_language == "Python"
        assert result.analysis.confidence >= 0.85

    def test_fallback_on_low_confidence(self, tmp_path):
        """Test fallback to heuristics when confidence is low."""
        # Setup with low confidence response
        response = {
            "status": "success",
            "response": json.dumps({
                "technology_stack": {"primary_language": "Unknown"},
                "overall_confidence": 0.45  # Below threshold
            })
        }

        # Should fall back to heuristics
        # ... test implementation
```

---

## Dependencies

### Depends On
- TASK-ARTIFACT-FILTER (Phase 1) - needs filtered samples
- TASK-AGENT-BRIDGE-COMPLETE (Phase 2) - needs checkpoint manager

### Blocks
- TASK-PHASE-5-CHECKPOINT (Phase 4) - needs analysis results

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Confidence score | 90%+ | manifest.json |
| Resume success rate | 100% | Integration tests |
| Language accuracy | 95%+ | Test on 4 projects |

---

## AI Integration Details

### Agent Used
`architectural-reviewer`

### Prompt Reference
See `AI-PROMPTS-SPECIFICATION.md`, Phase 1 section

### Confidence Threshold
- 0.70 minimum for auto-proceed
- Below 0.70 triggers fallback to heuristics

### Fallback Behavior
If AI fails or confidence too low:
1. Log warning
2. Use existing `_heuristic_analysis()` method
3. Continue workflow with lower confidence

---

**Created**: 2025-11-18
**Phase**: 3 of 8 (Template-Create Redesign)
**Related**: AI-PROMPTS-SPECIFICATION.md, AGENT-BRIDGE-SCHEMAS.md
