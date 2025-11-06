## AI Agent Generator

Generates project-specific AI agents based on codebase analysis, filling capability gaps identified by comparing needed capabilities with existing agents.

**Key Principle**: AI creates tailored agents from actual code examples (not generic templates)

## Overview

The AI Agent Generator analyzes your codebase to identify needed agent capabilities, compares them with existing agents from the scanner (TASK-003), and generates new agents to fill any gaps using AI.

### Key Features

- ✅ Codebase-driven capability identification
- ✅ Smart gap detection (avoids duplicates)
- ✅ AI-powered agent generation with context
- ✅ Based on actual project code examples
- ✅ Reusability detection and saving
- ✅ Dependency Inversion Principle (DIP) compliant

## Usage

### Basic Generation

```python
from agent_scanner import MultiSourceAgentScanner
from agent_generator import AIAgentGenerator

# Step 1: Scan existing agents
scanner = MultiSourceAgentScanner()
inventory = scanner.scan()

# Step 2: Generate agents for gaps
generator = AIAgentGenerator(inventory=inventory)
generated = generator.generate(analysis)

# Output:
# 🤖 Determining agent needs...
#   ✓ Identified 5 capability needs
#   ✓ architectural-reviewer: Using existing (global)
#   ❌ maui-appshell-navigator: MISSING (will create)
#   ✓ Found 1 gap to fill
#
# 💡 Creating project-specific agents...
#   → Generating: maui-appshell-navigator
#     ✓ Created: maui-appshell-navigator (confidence: 85%)
```

### With Custom AI Invoker

```python
from agent_generator import AIAgentGenerator, AgentInvoker

class MyAgentInvoker:
    """Custom AI invoker implementation"""

    def invoke(self, agent_name: str, prompt: str) -> str:
        # Your AI invocation logic here
        return ai_response

generator = AIAgentGenerator(
    inventory=inventory,
    ai_invoker=MyAgentInvoker()
)

generated = generator.generate(analysis)
```

### Saving Agents for Reuse

```python
# Generated agents with reuse_recommended=True
for agent in generated:
    if agent.reuse_recommended:
        # Save to .claude/agents/ for future projects
        saved_path = generator.save_agent_to_custom(agent)
        print(f"Saved to {saved_path}")
```

## Data Structures

### CapabilityNeed

Represents an identified capability need from codebase analysis:

```python
@dataclass
class CapabilityNeed:
    name: str                  # e.g., "maui-appshell-navigator"
    description: str           # What capability is needed
    reason: str                # Why it's needed
    technologies: List[str]    # Technologies involved
    example_files: List[Path]  # Code examples to learn from
    priority: int              # 1-10 (10=critical)
```

### GeneratedAgent

Represents an AI-generated agent:

```python
@dataclass
class GeneratedAgent:
    name: str
    description: str
    tools: List[str]
    tags: List[str]
    full_definition: str       # Complete markdown
    confidence: int            # 0-100 (AI's confidence)
    based_on_files: List[Path] # Source files used
    reuse_recommended: bool    # Reusable across projects?
```

### AgentInvoker Protocol

Protocol for AI agent invocation (Dependency Inversion):

```python
class AgentInvoker(Protocol):
    def invoke(self, agent_name: str, prompt: str) -> str:
        """Invoke an AI agent with a prompt"""
        ...
```

## Generation Process

The generator follows a 4-phase process:

### Phase 1: Identify Capability Needs

Analyzes codebase to determine what agents are needed:

- Architecture patterns (MVVM, Clean Architecture, etc.)
- Navigation patterns (AppShell, NavigationPage, etc.)
- Error handling patterns (ErrorOr, Result, etc.)
- Domain operations
- Testing frameworks

### Phase 2: Find Gaps

Compares needs with existing agents:

```python
needs = generator._identify_capability_needs(analysis)
gaps = generator._find_capability_gaps(needs)
```

### Phase 3: Generate Agents

Uses AI to create project-specific agents:

```python
for gap in gaps:
    agent = generator._generate_agent(gap, analysis)
```

### Phase 4: Offer Save for Reuse

Prompts user to save reusable agents:

```python
generator._offer_save_for_reuse(generated)
```

## Capability Detection

The generator identifies capabilities based on:

### MVVM Architecture

```python
if analysis.architecture_pattern == "MVVM":
    # Creates mvvm-viewmodel-specialist
    # Priority: 9/10
    # Based on: Files containing "ViewModel"
```

### Navigation Patterns

```python
if "navigation" in layer.patterns or "appshell" in layer:
    # Creates navigation-specialist
    # Priority: 8/10
    # Based on: Navigation-related files
```

### Error Handling

```python
if "ErrorOr" in quality_assessment or "Result" in quality_assessment:
    # Creates error-pattern-specialist
    # Priority: 7/10
    # Based on: Files using ErrorOr/Result patterns
```

### Domain Operations

```python
if layer.name == "domain":
    # Creates domain-operations-specialist
    # Priority: 8/10
    # Based on: Domain layer files
```

### Testing Frameworks

```python
if analysis.testing_framework:
    # Creates {framework}-specialist (e.g., xunit-specialist)
    # Priority: 7/10
    # Based on: Test files
```

## Agent Generation Prompt

The generator creates context-rich prompts:

```markdown
Create an AI agent definition for this project.

**Agent Name**: maui-appshell-navigator
**Purpose**: MAUI AppShell navigation patterns
**Why Needed**: Project uses AppShell for navigation

**Project Context**:
- Language: C#
- Architecture: MVVM
- Frameworks: .NET MAUI
- Technologies: C#, AppShell, MAUI

**Code Examples from This Project**:
File: src/App.xaml.cs
```
[Actual code from your project]
```

[Additional examples...]

**Output Format**:
[Complete markdown template with frontmatter]
```

## Reusability Detection

Agents are marked as reusable if they handle general patterns:

**Reusable Patterns:**
- MVVM
- Clean Architecture
- Hexagonal Architecture
- Testing
- Error Handling
- Domain Operations

**Not Reusable:**
- Project-specific APIs
- Company-specific patterns
- Custom implementations

## Testing

Comprehensive test suite with 20 tests:

```bash
python -m pytest tests/unit/test_ai_agent_generator.py -v
```

**Test Coverage**: 76% (close to 80% target)

### Test Categories

- Data class creation
- Capability need identification
- Gap finding logic
- AI generation with mocks
- Prompt building
- Agent parsing
- Reusability detection
- Save functionality
- Full workflow integration

## Integration

Works seamlessly with:

- **TASK-002**: Codebase Analysis (provides analysis input)
- **TASK-003**: Multi-Source Scanner (provides existing agents)
- **TASK-009**: Agent Orchestration (uses generated agents)
- **TASK-010**: Template Create Command (generates project agents)

## Example: MAUI Project

```python
# After codebase analysis
analysis = CodebaseAnalysis(
    language="C#",
    architecture_pattern="MVVM",
    frameworks=[".NET MAUI"],
    testing_framework="xUnit",
    quality_assessment="Uses ErrorOr pattern",
    layers=[
        Layer(name="domain", patterns=["DDD", "Value Objects"]),
        Layer(name="ui", patterns=["AppShell", "MVVM"])
    ],
    example_files=[...]
)

# Scan existing agents
scanner = MultiSourceAgentScanner()
inventory = scanner.scan()

# Generate agents
generator = AIAgentGenerator(inventory=inventory, ai_invoker=my_invoker)
generated = generator.generate(analysis)

# Results:
# - mvvm-viewmodel-specialist (from ViewModels)
# - navigation-specialist (from AppShell)
# - error-pattern-specialist (from ErrorOr)
# - domain-operations-specialist (from Domain)
# - xunit-specialist (from tests)
```

## Architecture

```
AIAgentGenerator
├── generate() - Main entry point
├── _identify_capability_needs() - Phase 1
├── _find_capability_gaps() - Phase 2
├── _generate_agent() - Phase 3
│   ├── _build_generation_prompt()
│   └── _parse_generated_agent()
├── _offer_save_for_reuse() - Phase 4
├── save_agent_to_custom() - Save agent
├── _capability_covered() - Coverage check
└── _is_reusable() - Reusability check
```

## Dependencies

- `python-frontmatter` - Markdown frontmatter parsing
- Agent Scanner (TASK-003) - Existing agent inventory
- Codebase Analysis (TASK-002) - Project analysis

## License

MIT

## Author

Taskwright Team
