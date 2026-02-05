"""
Seed Graphiti patterns group with concrete code examples.

This module seeds the patterns group with actual Python code examples
from the pattern files, not just relationship data. This is needed to
provide Claude with concrete guidance during task implementation.

Pattern Categories:
- Dataclass patterns: Basic state containers, optional fields, JSON serialization,
  computed properties, field() usage
- Pydantic patterns: Basic model structure, field definitions, nested models,
  serialization, JSON schema
- Orchestrator patterns: Pipeline step execution, checkpoint-resume, validation chain,
  state management, error recovery, progress reporting, strategy routing

Usage:
    from guardkit.knowledge.seed_pattern_examples import seed_pattern_examples
    from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig

    client = GraphitiClient(GraphitiConfig())
    await client.initialize()
    await seed_pattern_examples(client)
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


async def seed_pattern_examples(client, force: bool = False) -> dict:
    """Seed Graphiti patterns group with concrete code examples.

    Args:
        client: GraphitiClient instance
        force: If True, re-seed even if already seeded

    Returns:
        Dict with seeding results:
        - success: bool
        - episodes_created: int
        - patterns_seeded: list of pattern names
        - error: Optional error message
    """
    if not client.enabled:
        logger.warning("Graphiti not enabled, skipping pattern seeding")
        return {
            "success": False,
            "episodes_created": 0,
            "patterns_seeded": [],
            "error": "Graphiti not enabled"
        }

    # Pattern file paths
    patterns_dir = Path(".claude/rules/patterns")
    pattern_files = {
        "dataclasses": patterns_dir / "dataclasses.md",
        "pydantic-models": patterns_dir / "pydantic-models.md",
        "orchestrators": patterns_dir / "orchestrators.md",
    }

    # Verify pattern files exist
    missing_files = [name for name, path in pattern_files.items() if not path.exists()]
    if missing_files:
        error_msg = f"Pattern files not found: {', '.join(missing_files)}"
        logger.error(error_msg)
        return {
            "success": False,
            "episodes_created": 0,
            "patterns_seeded": [],
            "error": error_msg
        }

    episodes_created = 0
    patterns_seeded = []

    # Seed dataclass patterns
    try:
        dataclass_content = pattern_files["dataclasses"].read_text()
        dataclass_episodes = extract_dataclass_patterns(dataclass_content)

        for episode in dataclass_episodes:
            episode_id = await client.add_episode(
                name=episode["name"],
                episode_body=episode["body"],
                group_id="patterns",
                scope="system",
                source="pattern_seeding",
                entity_type="code_pattern"
            )
            if episode_id:
                episodes_created += 1
                logger.info(f"Created episode for pattern: {episode['name']}")

        patterns_seeded.append("dataclasses")
        logger.info(f"Seeded {len(dataclass_episodes)} dataclass patterns")

    except Exception as e:
        logger.error(f"Failed to seed dataclass patterns: {e}")
        return {
            "success": False,
            "episodes_created": episodes_created,
            "patterns_seeded": patterns_seeded,
            "error": f"Failed to seed dataclass patterns: {e}"
        }

    # Seed Pydantic patterns
    try:
        pydantic_content = pattern_files["pydantic-models"].read_text()
        pydantic_episodes = extract_pydantic_patterns(pydantic_content)

        for episode in pydantic_episodes:
            episode_id = await client.add_episode(
                name=episode["name"],
                episode_body=episode["body"],
                group_id="patterns",
                scope="system",
                source="pattern_seeding",
                entity_type="code_pattern"
            )
            if episode_id:
                episodes_created += 1
                logger.info(f"Created episode for pattern: {episode['name']}")

        patterns_seeded.append("pydantic-models")
        logger.info(f"Seeded {len(pydantic_episodes)} Pydantic patterns")

    except Exception as e:
        logger.error(f"Failed to seed Pydantic patterns: {e}")
        return {
            "success": False,
            "episodes_created": episodes_created,
            "patterns_seeded": patterns_seeded,
            "error": f"Failed to seed Pydantic patterns: {e}"
        }

    # Seed orchestrator patterns
    try:
        orchestrator_content = pattern_files["orchestrators"].read_text()
        orchestrator_episodes = extract_orchestrator_patterns(orchestrator_content)

        for episode in orchestrator_episodes:
            episode_id = await client.add_episode(
                name=episode["name"],
                episode_body=episode["body"],
                group_id="patterns",
                scope="system",
                source="pattern_seeding",
                entity_type="code_pattern"
            )
            if episode_id:
                episodes_created += 1
                logger.info(f"Created episode for pattern: {episode['name']}")

        patterns_seeded.append("orchestrators")
        logger.info(f"Seeded {len(orchestrator_episodes)} orchestrator patterns")

    except Exception as e:
        logger.error(f"Failed to seed orchestrator patterns: {e}")
        return {
            "success": False,
            "episodes_created": episodes_created,
            "patterns_seeded": patterns_seeded,
            "error": f"Failed to seed orchestrator patterns: {e}"
        }

    return {
        "success": True,
        "episodes_created": episodes_created,
        "patterns_seeded": patterns_seeded,
        "error": None
    }


def extract_dataclass_patterns(content: str) -> list[dict]:
    """Extract dataclass pattern episodes from markdown content.

    Returns:
        List of episode dicts with 'name' and 'body' keys
    """
    episodes = []

    # Basic State Containers
    episodes.append({
        "name": "Dataclass Pattern: Basic State Containers",
        "body": """Use dataclasses for minimal state objects:

```python
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

@dataclass
class OrchestrationState:
    \"\"\"Minimal state for checkpoint-resume.\"\"\"
    agent_file: str
    template_dir: str
    strategy: str
    dry_run: bool
    verbose: bool
    timestamp: str
```

**When to use:**
- Simple internal state containers
- No validation needed
- Need asdict() for JSON serialization
- Minimal overhead preferred
- State passed between internal functions
"""
    })

    # Optional Fields with Defaults
    episodes.append({
        "name": "Dataclass Pattern: Optional Fields with Defaults",
        "body": """Use optional fields with None defaults for flexibility:

```python
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path

@dataclass
class EnhancementResult:
    \"\"\"Result of agent enhancement operation.\"\"\"
    success: bool
    agent_name: str
    sections: List[str]
    error: Optional[str] = None
    core_file: Optional[Path] = None
    extended_file: Optional[Path] = None
    split_output: bool = False
```

**When to use:**
- Results that may or may not have certain fields
- Optional configuration parameters
- Error handling (error field present only on failure)
"""
    })

    # JSON Serialization
    episodes.append({
        "name": "Dataclass Pattern: JSON Serialization with asdict()",
        "body": """Serialize dataclasses to JSON using asdict():

```python
from dataclasses import dataclass, asdict
import json
from pathlib import Path

@dataclass
class OrchestrationState:
    agent_file: str
    template_dir: str
    timestamp: str

# Serialize to JSON
state = OrchestrationState(
    agent_file="/path/to/agent.md",
    template_dir="/path/to/template",
    timestamp="2025-12-13T15:00:00Z"
)

# Write as JSON
json_str = json.dumps(asdict(state), indent=2)
Path("state.json").write_text(json_str)

# Load from JSON
def _load_state(self) -> OrchestrationState:
    \"\"\"Load state from checkpoint file.\"\"\"
    data = json.loads(self.state_file.read_text())
    return OrchestrationState(**data)
```

**When to use:**
- Need to persist state to disk
- Checkpoint-resume workflows
- State passed between processes
"""
    })

    # Computed Properties
    episodes.append({
        "name": "Dataclass Pattern: Computed Properties",
        "body": """Add computed properties to dataclasses:

```python
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path

@dataclass
class EnhancementResult:
    \"\"\"Result of agent enhancement operation.\"\"\"
    success: bool
    core_file: Optional[Path] = None
    extended_file: Optional[Path] = None

    @property
    def files(self) -> List[Path]:
        \"\"\"Return list of created files.\"\"\"
        if self.core_file is None:
            return []
        if self.extended_file is not None:
            return [self.core_file, self.extended_file]
        return [self.core_file]
```

**When to use:**
- Derived values from existing fields
- API convenience methods
- Complex logic based on multiple fields
"""
    })

    # Using field() for Mutable Defaults
    episodes.append({
        "name": "Dataclass Pattern: Using field() for Mutable Defaults",
        "body": """NEVER use mutable defaults directly, always use field(default_factory):

```python
from dataclasses import dataclass, field
from typing import List
from pathlib import Path

@dataclass
class ProcessedFile:
    \"\"\"Result of file processing.\"\"\"
    source_path: Path
    output_path: Path
    lines_changed: int = 0
    # NEVER use [] as default, use field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
```

**Anti-pattern (WRONG):**
```python
@dataclass
class ProcessedFile:
    warnings: List[str] = []  # ❌ WRONG - shared between instances
```

**Why this matters:**
Mutable defaults like [] are shared between all instances, causing unexpected behavior.
Always use field(default_factory=list) for lists, dicts, and other mutable types.
"""
    })

    return episodes


def extract_pydantic_patterns(content: str) -> list[dict]:
    """Extract Pydantic pattern episodes from markdown content.

    Returns:
        List of episode dicts with 'name' and 'body' keys
    """
    episodes = []

    # Basic Model Structure
    episodes.append({
        "name": "Pydantic Pattern: Basic Model Structure",
        "body": """Define models with Field() for documentation and validation:

```python
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class FrameworkInfo(BaseModel):
    \"\"\"Framework information with version and purpose.\"\"\"
    name: str = Field(description="Framework name (e.g., 'FastAPI', 'React')")
    version: Optional[str] = Field(None, description="Framework version if detected")
    purpose: str = Field(description="Framework purpose: 'testing', 'ui', 'data', 'core'")
```

**When to use:**
- Data comes from external sources (JSON, API)
- Need validation (constraints, patterns)
- Need serialization with configuration
- Need JSON schema generation
"""
    })

    # Field Definitions
    episodes.append({
        "name": "Pydantic Pattern: Field Definitions",
        "body": """Use Field() for required, optional, and collection fields:

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class TemplateManifest(BaseModel):
    # Required fields
    name: str = Field(description="Template identifier (kebab-case)")

    # Optional fields with defaults
    version: str = Field(default="1.0.0", description="Template version (semver)")
    author: Optional[str] = Field(None, description="Template author")

    # Collection fields
    frameworks: List[FrameworkInfo] = Field(default_factory=list, description="Frameworks used")
    placeholders: Dict[str, PlaceholderInfo] = Field(default_factory=dict, description="Template placeholders")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")

    # Constrained fields
    complexity: int = Field(ge=1, le=10, description="Complexity score (1-10)")
    confidence_score: float = Field(ge=0.0, le=100.0, description="AI analysis confidence score")
```

**When to use:**
- Need input validation
- Want clear API documentation
- Need constraints (min/max, patterns)
"""
    })

    # Nested Models
    episodes.append({
        "name": "Pydantic Pattern: Nested Models",
        "body": """Compose complex models from nested models:

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class PlaceholderInfo(BaseModel):
    \"\"\"Intelligent placeholder information.\"\"\"
    name: str = Field(description="Placeholder name in {{...}} format")
    description: str = Field(description="Human-readable description")
    default_value: Optional[str] = Field(None, description="Default value if not provided")
    pattern: Optional[str] = Field(None, description="Regex pattern for validation")
    required: bool = Field(default=True, description="Whether placeholder must be provided")


class TemplateManifest(BaseModel):
    \"\"\"Template manifest with nested models.\"\"\"
    schema_version: str = Field(default="1.0.0")
    frameworks: List[FrameworkInfo] = Field(default_factory=list)
    placeholders: Dict[str, PlaceholderInfo] = Field(default_factory=dict)
```

**When to use:**
- Complex data structures
- API responses with nested objects
- Configuration schemas
"""
    })

    # Model Serialization
    episodes.append({
        "name": "Pydantic Pattern: Model Serialization",
        "body": """Convert models to dictionaries with model_dump():

```python
from pydantic import BaseModel, Field
import json

class TemplateManifest(BaseModel):
    name: str
    version: str = Field(default="1.0.0")

    def to_dict(self) -> dict:
        \"\"\"Convert to dictionary for JSON serialization.\"\"\"
        return self.model_dump(exclude_none=False, by_alias=True)

# Usage
manifest = TemplateManifest(name="my-template")
data = manifest.to_dict()
json_str = json.dumps(data, indent=2)
```

**Options:**
- `exclude_none=True` - Skip None values
- `by_alias=True` - Use field aliases
- `exclude={'field_name'}` - Exclude specific fields
- `include={'field_name'}` - Include only specific fields
"""
    })

    # JSON Schema Examples
    episodes.append({
        "name": "Pydantic Pattern: JSON Schema Examples",
        "body": """Provide examples for documentation using json_schema_extra:

```python
from pydantic import BaseModel, Field

class TemplateManifest(BaseModel):
    schema_version: str = Field(default="1.0.0")
    name: str
    complexity: int = Field(ge=1, le=10)

    class Config:
        json_schema_extra = {
            "example": {
                "schema_version": "1.0.0",
                "name": "python-clean-architecture",
                "display_name": "Python Clean Architecture",
                "language": "python",
                "frameworks": [
                    {"name": "FastAPI", "version": "0.104.0", "purpose": "core"},
                    {"name": "pytest", "version": "7.4.0", "purpose": "testing"}
                ],
                "complexity": 6,
                "confidence_score": 85.5
            }
        }
```

**When to use:**
- API documentation generation
- OpenAPI/Swagger schemas
- User documentation with examples
"""
    })

    return episodes


def extract_orchestrator_patterns(content: str) -> list[dict]:
    """Extract orchestrator pattern episodes from markdown content.

    Returns:
        List of episode dicts with 'name' and 'body' keys
    """
    episodes = []

    # Pipeline Step Execution
    episodes.append({
        "name": "Orchestrator Pattern: Pipeline Step Execution",
        "body": """Execute multiple steps in sequence with clear progress reporting:

```python
class ImplementOrchestrator:
    \"\"\"
    Orchestrates multi-step implementation workflow.

    Each step has:
    - Clear naming (Step N/Total)
    - Progress reporting
    - Success confirmation
    - Error handling
    \"\"\"

    def run(self) -> None:
        \"\"\"Execute complete workflow.\"\"\"
        print("\\n" + "="*80)
        print("🔄 Enhanced [I]mplement Flow - Auto-Detection Pipeline")
        print("="*80 + "\\n")

        # Step 1: Extract feature info
        print("Step 1/10: Extracting feature slug...")
        self.extract_feature_info()
        print(f"   ✓ Feature slug: {self.feature_slug}")

        # Step 2: Parse subtasks
        print("\\nStep 2/10: Parsing subtasks from review recommendations...")
        self.parse_subtasks()
        print(f"   ✓ Found {len(self.subtasks)} subtasks")

        # ... continue with remaining steps ...
```

**When to use:**
- Multi-step workflows with >3 steps
- Need clear progress visibility
- Sequential dependency between steps
- User needs to understand what's happening
"""
    })

    # Checkpoint-Resume
    episodes.append({
        "name": "Orchestrator Pattern: Checkpoint-Resume",
        "body": """Save state and resume from checkpoints for long-running workflows:

```python
from dataclasses import dataclass, asdict
import json
from pathlib import Path

@dataclass
class OrchestrationState:
    \"\"\"Minimal state for checkpoint-resume.\"\"\"
    agent_file: str
    template_dir: str
    strategy: str
    dry_run: bool
    verbose: bool
    timestamp: str

class AgentEnhanceOrchestrator:
    def __init__(self, enhancer, resume: bool = False):
        self.enhancer = enhancer
        self.resume = resume
        self.state_file = Path(".agent-enhance-state.json")

    def run(self, agent_file: Path, template_dir: Path):
        \"\"\"Execute with checkpoint-resume.\"\"\"
        if self.resume:
            return self._run_with_resume(agent_file, template_dir)
        else:
            return self._run_initial(agent_file, template_dir)

    def _run_initial(self, agent_file: Path, template_dir: Path):
        \"\"\"Save state and run (may exit 42 for AI).\"\"\"
        self._save_state(agent_file, template_dir)
        try:
            result = self.enhancer.enhance(agent_file, template_dir)
            self._cleanup_state()
            return result
        except SystemExit as e:
            if e.code == 42:
                # Agent invocation needed - state remains for resume
                raise
            else:
                self._cleanup_state()
                raise

    def _save_state(self, agent_file: Path, template_dir: Path) -> None:
        \"\"\"Save state to JSON checkpoint.\"\"\"
        state = OrchestrationState(
            agent_file=str(agent_file),
            template_dir=str(template_dir),
            strategy=self.enhancer.strategy,
            dry_run=self.enhancer.dry_run,
            verbose=self.enhancer.verbose,
            timestamp=datetime.now().isoformat()
        )
        self.state_file.write_text(json.dumps(asdict(state), indent=2))
```

**When to use:**
- Workflow requires AI interaction (exit code 42)
- Long-running operations that may fail
- Need to resume after interruption
- Multi-phase workflows with dependencies
"""
    })

    # Validation Chain
    episodes.append({
        "name": "Orchestrator Pattern: Validation Chain",
        "body": """Execute sequential validation phases with early exit on failure:

```python
class TemplateQAOrchestrator:
    \"\"\"Orchestrator with validation chain.\"\"\"

    def run(self) -> QAOrchestrationResult:
        \"\"\"Execute Q&A orchestration with validation chain.\"\"\"
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
"""
    })

    # State Management
    episodes.append({
        "name": "Orchestrator Pattern: State Management",
        "body": """Use dataclasses for orchestration state with JSON serialization:

```python
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict
import json
from pathlib import Path

@dataclass
class ImplementOrchestrationState:
    \"\"\"Complete state for implement orchestration.\"\"\"
    review_task: Dict
    review_report_path: str
    feature_slug: Optional[str] = None
    feature_name: Optional[str] = None
    subtasks: List[Dict] = field(default_factory=list)
    subfolder_path: Optional[str] = None
    current_step: int = 0

    def to_json(self, path: Path) -> None:
        \"\"\"Serialize to JSON file.\"\"\"
        path.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def from_json(cls, path: Path):
        \"\"\"Deserialize from JSON file.\"\"\"
        data = json.loads(path.read_text())
        return cls(**data)
```

**When to use:**
- Need to save/load orchestration state
- Multiple fields to track
- JSON serialization required
- Type safety with dataclasses preferred
"""
    })

    # Error Recovery
    episodes.append({
        "name": "Orchestrator Pattern: Error Recovery",
        "body": """Handle errors gracefully with cleanup and user-friendly messages:

```python
class ImplementOrchestrator:
    \"\"\"Orchestrator with error recovery.\"\"\"

    def parse_subtasks(self) -> None:
        \"\"\"Parse subtasks with error recovery.\"\"\"
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
"""
    })

    # Progress Reporting
    episodes.append({
        "name": "Orchestrator Pattern: Progress Reporting",
        "body": """Provide visual feedback during long-running operations:

```python
class ImplementOrchestrator:
    \"\"\"Orchestrator with progress reporting.\"\"\"

    def display_detection_summary(self) -> None:
        \"\"\"Display auto-detected values before proceeding.\"\"\"
        waves = set(s.get("parallel_group") for s in self.subtasks if s.get("parallel_group"))
        wave_count = len(waves)

        print("\\n" + "="*80)
        print("✅ Auto-detected Configuration:")
        print("="*80)
        print(f"   Feature slug: {self.feature_slug}")
        print(f"   Feature name: {self.feature_name}")
        print(f"   Subtasks: {len(self.subtasks)} (from review recommendations)")
        print(f"   Parallel groups: {wave_count} waves")
        print("="*80 + "\\n")

    def display_summary(self) -> None:
        \"\"\"Display final summary and next steps.\"\"\"
        print("\\n" + "="*80)
        print("✅ Feature Implementation Structure Created")
        print("="*80)
        print(f"\\nCreated: {self.subfolder_path}/")
        print("  ├── README.md")
        print("  ├── IMPLEMENTATION-GUIDE.md")
        # ... detailed file tree ...

        print("\\n" + "="*80)
        print("🚀 Next Steps:")
        print("="*80)
        print(f"1. Review: {self.subfolder_path}/IMPLEMENTATION-GUIDE.md")
        print(f"2. Start with Wave 1 tasks")
        print("="*80 + "\\n")
```

**When to use:**
- Multi-step workflow with progress
- User needs to see what's happening
- Summary needed at completion
- Next steps should be clear
"""
    })

    # Strategy Routing
    episodes.append({
        "name": "Orchestrator Pattern: Strategy Routing",
        "body": """Route to different execution strategies based on configuration:

```python
class AgentEnhanceOrchestrator:
    \"\"\"Orchestrator with strategy routing.\"\"\"

    def __init__(self, strategy: str = "hybrid"):
        \"\"\"
        Initialize with strategy.

        Args:
            strategy: ai | static | hybrid
        \"\"\"
        self.strategy = strategy

    def enhance(self, agent_file: Path, template_dir: Path):
        \"\"\"Route to appropriate strategy.\"\"\"
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
"""
    })

    return episodes
