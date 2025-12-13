---
paths: "**/*orchestrator.py", "**/*_orchestrator.py"
---

# Orchestrator Patterns

Multi-step workflow orchestration patterns extracted from GuardKit's actual orchestrators.

## Pipeline Step Execution Pattern

Execute multiple steps in sequence with clear progress reporting:

```python
class ImplementOrchestrator:
    """
    Orchestrates multi-step implementation workflow.

    Each step has:
    - Clear naming (Step N/Total)
    - Progress reporting
    - Success confirmation
    - Error handling
    """

    def run(self) -> None:
        """Execute complete workflow."""
        print("\n" + "="*80)
        print("🔄 Enhanced [I]mplement Flow - Auto-Detection Pipeline")
        print("="*80 + "\n")

        # Step 1: Extract feature info
        print("Step 1/10: Extracting feature slug...")
        self.extract_feature_info()
        print(f"   ✓ Feature slug: {self.feature_slug}")

        # Step 2: Parse subtasks
        print("\nStep 2/10: Parsing subtasks from review recommendations...")
        self.parse_subtasks()
        print(f"   ✓ Found {len(self.subtasks)} subtasks")

        # Step 3: Assign modes
        print("\nStep 3/10: Assigning implementation modes...")
        self.assign_modes()
        print(f"   ✓ Modes assigned")

        # ... continue with remaining steps ...
```

**When to use:**
- Multi-step workflows with >3 steps
- Need clear progress visibility
- Sequential dependency between steps
- User needs to understand what's happening

## Checkpoint-Resume Pattern

Save state and resume from checkpoints for long-running or AI-dependent workflows:

```python
from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Optional

@dataclass
class OrchestrationState:
    """Minimal state for checkpoint-resume."""
    agent_file: str
    template_dir: str
    strategy: str
    dry_run: bool
    verbose: bool
    timestamp: str

class AgentEnhanceOrchestrator:
    """
    Orchestrator with checkpoint-resume capability.

    Workflow:
    1. First invocation: Save state, run phase (may exit 42 for AI)
    2. Second invocation: Detect existing response, load and continue
    3. Success: Clean up state
    """

    def __init__(self, enhancer, resume: bool = False):
        self.enhancer = enhancer
        self.resume = resume
        self.state_file = Path(".agent-enhance-state.json")

    def run(self, agent_file: Path, template_dir: Path):
        """Execute with checkpoint-resume."""
        if self.resume:
            return self._run_with_resume(agent_file, template_dir)
        else:
            return self._run_initial(agent_file, template_dir)

    def _run_initial(self, agent_file: Path, template_dir: Path):
        """Save state and run (may exit 42 for AI)."""
        # Save state before potential exit
        self._save_state(agent_file, template_dir)

        try:
            result = self.enhancer.enhance(agent_file, template_dir)
            # Success - clean up state
            self._cleanup_state()
            return result
        except SystemExit as e:
            if e.code == 42:
                # Agent invocation needed - state remains for resume
                raise
            else:
                # Unexpected exit - clean up and re-raise
                self._cleanup_state()
                raise

    def _run_with_resume(self, agent_file: Path, template_dir: Path):
        """Load state and resume."""
        state = self._load_state()
        # Resume with loaded state
        result = self.enhancer.resume_enhancement(state)
        # Clean up on success
        self._cleanup_state()
        return result

    def _save_state(self, agent_file: Path, template_dir: Path) -> None:
        """Save state to JSON checkpoint."""
        state = OrchestrationState(
            agent_file=str(agent_file),
            template_dir=str(template_dir),
            strategy=self.enhancer.strategy,
            dry_run=self.enhancer.dry_run,
            verbose=self.enhancer.verbose,
            timestamp=datetime.now().isoformat()
        )
        self.state_file.write_text(json.dumps(asdict(state), indent=2))

    def _load_state(self) -> OrchestrationState:
        """Load state from checkpoint."""
        data = json.loads(self.state_file.read_text())
        return OrchestrationState(**data)

    def _cleanup_state(self) -> None:
        """Remove checkpoint file."""
        if self.state_file.exists():
            self.state_file.unlink()
```

**When to use:**
- Workflow requires AI interaction (exit code 42)
- Long-running operations that may fail
- Need to resume after interruption
- Multi-phase workflows with dependencies

## Validation Chain Pattern

Execute sequential validation phases with early exit on failure:

```python
class TemplateQAOrchestrator:
    """
    Orchestrator with validation chain.

    Each phase validates and may fail early:
    - Phase 1: Check for existing config
    - Phase 2: Run Q&A session
    - Phase 3: Save configuration

    Returns early on any failure.
    """

    def run(self) -> QAOrchestrationResult:
        """Execute Q&A orchestration with validation chain."""
        try:
            self._print_header()

            # Phase 1: Check for existing config (if --resume)
            if self.config.resume:
                if not self._handle_resume():
                    return QAOrchestrationResult(
                        success=False,
                        error="Config file not found or invalid"
                    )

            # Phase 2: Run Q&A session
            self.answers = self._run_qa_session()
            if not self.answers:
                return QAOrchestrationResult(
                    success=False,
                    error="Q&A session cancelled or failed"
                )

            # Phase 3: Save configuration
            config_file = self._save_configuration()
            if not config_file:
                return QAOrchestrationResult(
                    success=False,
                    error="Failed to save configuration"
                )

            # All phases succeeded
            self._print_success(config_file)
            return QAOrchestrationResult(
                success=True,
                config_file=config_file,
                template_name=self.answers.template_name
            )

        except KeyboardInterrupt:
            return QAOrchestrationResult(
                success=False,
                error="User interrupted"
            )
```

**When to use:**
- Sequential validation steps
- Each step depends on previous success
- Need structured error handling
- Early exit on failure preferred

## State Management Pattern

Use dataclasses for orchestration state with JSON serialization:

```python
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict
import json
from pathlib import Path

@dataclass
class ImplementOrchestrationState:
    """
    Complete state for implement orchestration.

    Includes all context needed to resume workflow.
    """
    review_task: Dict
    review_report_path: str
    feature_slug: Optional[str] = None
    feature_name: Optional[str] = None
    subtasks: List[Dict] = field(default_factory=list)
    subfolder_path: Optional[str] = None
    current_step: int = 0

    def to_json(self, path: Path) -> None:
        """Serialize to JSON file."""
        path.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def from_json(cls, path: Path):
        """Deserialize from JSON file."""
        data = json.loads(path.read_text())
        return cls(**data)
```

**When to use:**
- Need to save/load orchestration state
- Multiple fields to track
- JSON serialization required
- Type safety with dataclasses preferred

## Error Recovery Pattern

Handle errors gracefully with cleanup and user-friendly messages:

```python
class ImplementOrchestrator:
    """Orchestrator with error recovery."""

    def parse_subtasks(self) -> None:
        """
        Parse subtasks with error recovery.

        Handles multiple error scenarios:
        - File not found
        - Parse errors
        - Empty results
        """
        try:
            self.subtasks = extract_subtasks_from_review(
                self.review_report_path,
                self.feature_slug
            )
        except FileNotFoundError as e:
            print(f"❌ Error: Review report not found: {self.review_report_path}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error parsing review report: {e}")
            sys.exit(1)

        if not self.subtasks:
            print("⚠️  Warning: No subtasks found in review report.")
            print("    The review report may not contain a recommendations section.")
            sys.exit(1)
```

**When to use:**
- Multiple failure scenarios possible
- Need specific error messages per scenario
- User-friendly error output required
- Cleanup needed on failure

## Progress Reporting Pattern

Provide visual feedback during long-running operations:

```python
class ImplementOrchestrator:
    """Orchestrator with progress reporting."""

    def display_detection_summary(self) -> None:
        """Display auto-detected values before proceeding."""
        waves = set(s.get("parallel_group") for s in self.subtasks if s.get("parallel_group"))
        wave_count = len(waves)

        print("\n" + "="*80)
        print("✅ Auto-detected Configuration:")
        print("="*80)
        print(f"   Feature slug: {self.feature_slug}")
        print(f"   Feature name: {self.feature_name}")
        print(f"   Subtasks: {len(self.subtasks)} (from review recommendations)")
        print(f"   Parallel groups: {wave_count} waves")
        print("="*80 + "\n")

    def display_summary(self) -> None:
        """Display final summary and next steps."""
        print("\n" + "="*80)
        print("✅ Feature Implementation Structure Created")
        print("="*80)
        print(f"\nCreated: {self.subfolder_path}/")
        print("  ├── README.md")
        print("  ├── IMPLEMENTATION-GUIDE.md")
        # ... detailed file tree ...

        print("\n" + "="*80)
        print("🚀 Next Steps:")
        print("="*80)
        print(f"1. Review: {self.subfolder_path}/IMPLEMENTATION-GUIDE.md")
        print(f"2. Start with Wave 1 tasks")
        print("="*80 + "\n")
```

**When to use:**
- Multi-step workflow with progress
- User needs to see what's happening
- Summary needed at completion
- Next steps should be clear

## Strategy Routing Pattern

Route to different execution strategies based on configuration:

```python
class AgentEnhanceOrchestrator:
    """Orchestrator with strategy routing."""

    def __init__(self, strategy: str = "hybrid"):
        """
        Initialize with strategy.

        Args:
            strategy: ai | static | hybrid
        """
        self.strategy = strategy

    def enhance(self, agent_file: Path, template_dir: Path):
        """Route to appropriate strategy."""
        if self.strategy == "ai":
            return self._enhance_with_ai(agent_file, template_dir)
        elif self.strategy == "static":
            return self._enhance_with_static(agent_file, template_dir)
        else:  # hybrid
            try:
                return self._enhance_with_ai(agent_file, template_dir)
            except Exception:
                # Fallback to static on AI failure
                return self._enhance_with_static(agent_file, template_dir)
```

**When to use:**
- Multiple execution strategies available
- Need fallback behavior
- User selects strategy via config
- AI/static hybrid patterns
