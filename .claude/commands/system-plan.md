# /system-plan - Interactive Architecture Planning Command

Establishes and maintains system-level architecture context in Graphiti. This is the third specialization in GuardKit's command hierarchy: `/task-review` (code level), `/feature-plan` (feature level), and `/system-plan` (system/architecture level).

## Command Syntax

```bash
/system-plan "description" [--mode=MODE] [--focus=FOCUS] [--no-questions] [--defaults] [--context path/to/file.md]
```

## Available Flags

| Flag | Description |
|------|-------------|
| `--mode=MODE` | Override auto-detected mode: `setup`, `refine`, `review` |
| `--focus=FOCUS` | Narrow session scope: `domains`, `services`, `decisions`, `crosscutting`, `all` |
| `--no-questions` | Skip all interactive clarification |
| `--defaults` | Use clarification defaults without prompting |
| `--context path/to/file.md` | Include additional context files (can be used multiple times) |

## Mode Auto-Detection

The command automatically detects the appropriate mode based on existing architecture context in Graphiti:

| Graphiti State | Detected Mode | Purpose |
|----------------|---------------|---------|
| No architecture context | `setup` | First-time architecture planning |
| Architecture exists | `refine` | Update existing architecture |
| `--mode=review` override | `review` | Evaluate proposed change against architecture |

**Transparent Display**: The command always shows which mode was selected and why.

**Graceful Degradation**: If Graphiti is unavailable, defaults to `setup` mode without persistence.

## Execution Flow

### Phase 0: Context Loading (All Modes)

**Load existing architecture context from Graphiti:**

```python
from guardkit.planning.graphiti_arch import SystemPlanGraphiti
from guardkit.knowledge.graphiti_service import get_graphiti

# Initialize Graphiti client
client = get_graphiti()  # Returns None if Graphiti unavailable

# Auto-detect mode
if client:
    sp = SystemPlanGraphiti(client, project_id="current_project")
    has_arch = sp.has_architecture_context()  # Sync wrapper for async call
    detected_mode = "refine" if has_arch else "setup"
else:
    detected_mode = "setup"
    print("⚠️ Graphiti unavailable - running without persistence")

# User override
mode = flags.get("mode", detected_mode)

# Display mode selection
if mode == "setup":
    print("🏗️ Mode: setup (no existing architecture context found)")
elif mode == "refine":
    print("🔄 Mode: refine (updating existing architecture)")
elif mode == "review":
    print("🔍 Mode: review (evaluating change against existing architecture)")
```

### Phase 1: Interactive Session (Mode-Specific)

#### Setup Mode Flow

**Ask structured questions across 6 categories:**

1. **Domain & Methodology Discovery**
2. **System Structure** (adapts to methodology)
3. **Service/Module Relationships**
4. **Technology Decisions**
5. **Cross-Cutting Concerns**
6. **Constraints and NFRs**

**After each category:**
- Display what was captured
- Show checkpoint: `[C]ontinue / [R]evise / [S]kip / [A]DR?`
- If `[A]DR?`: Capture ADR inline before continuing
- Upsert entities to Graphiti immediately (not batched)

**Question Adaptation:**

```python
from guardkit.planning.question_adapter import SetupQuestionAdapter

adapter = SetupQuestionAdapter()

# Category 1: Always ask methodology selection
print("Category 1: Domain & Methodology Discovery")
print("Q5. What architectural methodology best fits this project?")
print("    [M]odular — Components/modules with clear responsibilities")
print("    [L]ayered — Traditional layered architecture")
print("    [D]omain-Driven Design — Bounded contexts, aggregates, domain events")
print("    [E]vent-Driven — Event-based communication")
print("    [N]ot sure — Let questions guide the choice")
methodology = input("Your choice [M/L/D/E/N]: ").lower()

# Store in answers
answers["q5_methodology"] = methodology

# Category 2: Adapt questions based on methodology
if adapter.should_ask_ddd_questions(answers):
    # Ask DDD-specific questions (bounded contexts, aggregates, domain events)
    pass
else:
    # Ask generic component/module questions
    pass
```

**Checkpoint Example:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Category 2: System Structure
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Captured 3 components:
  • CLI Parser — command routing, argument validation
  • Planning Engine — question flow, markdown generation
  • Graphiti Integration — persist architecture context

Communication:
  • CLI Parser → Planning Engine (invokes sessions)
  • Planning Engine → Graphiti Integration (persists)

[C]ontinue to next category | [R]evise this category | [S]kip remaining | [A]DR?

Your choice [C/R/S/A]:
```

**ADR Capture (if user chooses [A]):**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 ARCHITECTURE DECISION RECORD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Title: [Ask user for title]
Context: [Ask user for context]
Decision: [Ask user for decision]
Consequences: [Ask user - can list multiple]
Status: [A]ccepted / [P]roposed / [D]eprecated / [S]uperseded

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ ADR-001 captured. Continuing to next category...
```

**Graphiti Persistence (after each category checkpoint):**

```python
from guardkit.knowledge.entities.architecture import (
    ComponentDef, SystemContextDef, CrosscuttingConcernDef, ArchitectureDecision
)

# After Category 1 (Domain & Methodology)
system_context = SystemContextDef(
    name=project_name,
    purpose=answers.get("q1_purpose"),
    users=answers.get("q2_users"),
    methodology=answers.get("q5_methodology"),
)
sp.upsert_system_context(system_context)  # Upserts immediately

# After Category 2 (System Structure)
for component in captured_components:
    comp_def = ComponentDef(
        name=component.name,
        description=component.description,
        responsibilities=component.responsibilities,
        dependencies=component.dependencies,
    )
    sp.upsert_component(comp_def)  # Upserts each component

# After Category 5 (Cross-Cutting Concerns)
for concern in captured_concerns:
    concern_def = CrosscuttingConcernDef(
        name=concern.name,
        category=concern.category,
        description=concern.description,
        affected_components=concern.affected_components,
    )
    sp.upsert_crosscutting(concern_def)

# If ADR captured at any checkpoint
adr = ArchitectureDecision(
    number=next_adr_number,
    title=adr_title,
    context=adr_context,
    decision=adr_decision,
    consequences=adr_consequences,
    status=adr_status,
)
sp.upsert_adr(adr)
```

#### Refine Mode Flow

**Show current architecture state:**

```
🔄 Mode: refine (existing architecture found)

Current architecture summary:
  • Methodology: DDD
  • 4 bounded contexts (Attorney Mgmt, Doc Gen, Financial, Compliance)
  • 7 ADRs (3 accepted, 2 superseded, 2 proposed)
  • 3 external integrations (Moneyhub, OPG, GOV.UK Verify)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 REFINEMENT SCOPE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

What would you like to refine?

[C]omponents — Add, modify, or remove components/contexts
[S]ervice relationships — Update communication patterns
[D]ecisions — Add new ADR or supersede existing
[T]echnology — Update stack or infrastructure decisions
[X]rosscutting — Modify shared concerns (auth, logging, etc.)
[A]ll — Full review of all categories

Your choice:
```

**Targeted refinement:**
- Show current state for selected area
- Ask what's changed conversationally (not full questionnaire)
- Update Graphiti entities
- Regenerate affected markdown files

#### Review Mode Flow

**Evaluate proposed change against existing architecture:**

```
🔍 Mode: review (evaluating against existing architecture)

Analyzing "add real-time notifications" against:
  • 4 bounded contexts (DDD methodology)
  • 7 ADRs
  • 12 BDD scenarios

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 IMPACT ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Affected components:
  ⚠️ Attorney Management — notification triggers for status changes
  ⚠️ Financial Oversight — alerts for transaction anomalies
  ℹ️ Compliance — audit logging of notifications sent

Conflicts with existing ADRs:
  ⚠️ ADR-003: "Use synchronous HTTP for all inter-service communication"
      → Real-time notifications require async/WebSocket

Architectural implications:
  • Need new shared concern: Notification Service
  • Cross-cutting: WebSocket connection management
  • Domain events: StatusChanged, TransactionFlagged

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 DECISION CHECKPOINT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Options:
  [A]ccept — Approve change and update architecture
  [R]eject — Change conflicts too heavily with current design
  [M]odify — Suggest alternative approach
  [F]eature-plan — Chain to /feature-plan for task decomposition
  [C]ancel — Discard analysis

Your choice:
```

**Integration with /feature-plan:**

```
Your choice: F

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 CHAINING TO FEATURE PLANNING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Architecture context will be passed to /feature-plan:
  • Impact analysis from this review
  • Affected components and dependencies
  • Relevant ADRs and constraints

Launching /feature-plan...

[Execute /feature-plan "add real-time notifications" with architecture context]
```

### Phase 2: Output Generation

**Generate markdown artefacts using ArchitectureWriter:**

```python
from guardkit.planning.architecture_writer import ArchitectureWriter

writer = ArchitectureWriter()

# Collect all captured data
system = {
    "name": project_name,
    "purpose": system_purpose,
    "methodology": methodology,
    "users": users,
}

components = [
    {"name": c.name, "description": c.description, "responsibilities": c.responsibilities}
    for c in captured_components
]

concerns = [
    {"name": cc.name, "category": cc.category, "description": cc.description}
    for cc in captured_concerns
]

decisions = [
    {"number": adr.number, "title": adr.title, "status": adr.status}
    for adr in captured_adrs
]

# Write all artefacts
output_dir = "docs/architecture"
writer.write_all(
    output_dir=output_dir,
    system=system,
    components=components,
    concerns=concerns,
    decisions=decisions,
)

# Display what was created
print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ARCHITECTURE DOCUMENTATION CREATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Created: {output_dir}/
  ├── ARCHITECTURE.md (index)
  ├── system-context.md
  ├── components.md (or bounded-contexts.md for DDD)
  ├── crosscutting-concerns.md
  └── decisions/
      ├── ADR-001-{slug}.md
      ├── ADR-002-{slug}.md
      └── ...

Graphiti context:
  ✓ {len(components)} components persisted
  ✓ {len(concerns)} cross-cutting concerns persisted
  ✓ {len(decisions)} ADRs persisted
  ✓ 1 system context persisted

Next steps:
  1. Review: {output_dir}/ARCHITECTURE.md
  2. Plan features: /feature-plan "feature description"
  3. Refine architecture: /system-plan "{project_name}"
""")
```

### Phase 3: Graphiti Final Persistence

**If not already done per-category, upsert all entities:**

Note: In setup mode, entities are upserted after each category checkpoint. This phase is a safety check to ensure all entities are persisted.

```python
# Verify all entities were persisted
if client:
    sp = SystemPlanGraphiti(client, project_id)

    # Double-check system context
    if system_context:
        sp.upsert_system_context(system_context)

    # Double-check components
    for comp in components:
        sp.upsert_component(comp)

    # Double-check concerns
    for concern in concerns:
        sp.upsert_crosscutting(concern)

    # Double-check ADRs
    for adr in decisions:
        sp.upsert_adr(adr)

    print("✓ All architecture entities synchronized to Graphiti")
```

## Methodology-Specific Question Gating

The setup flow adapts questions based on the selected methodology:

| Methodology | Questions Asked |
|-------------|-----------------|
| **Modular** | Components, modules, responsibilities, dependencies |
| **Layered** | Layers, presentation/service/data, cross-layer communication |
| **DDD** | Bounded contexts, aggregates, domain events, shared kernels, ACLs |
| **Event-Driven** | Events, event streams, event handlers, eventual consistency |

**DDD-Specific Questions (only when methodology = DDD):**

- Q6d. How do these map to bounded contexts?
- Q7d. What are the aggregate roots in each context?
- Q8d. Are there shared kernels or anti-corruption layers needed?
- Q9d. What domain events flow between contexts?

**Implementation:**

```python
class SetupQuestionAdapter:
    def should_ask_ddd_questions(self, answers: dict) -> bool:
        return answers.get("q5_methodology") == "ddd"

    def should_ask_event_questions(self, answers: dict) -> bool:
        methodology = answers.get("q5_methodology")
        return methodology in ("event_driven", "ddd")

    def get_questions_for_category(self, category: str, answers: dict) -> list:
        base_questions = CATEGORY_QUESTIONS[category]

        if category == "system_structure":
            if self.should_ask_ddd_questions(answers):
                base_questions += DDD_SPECIFIC_QUESTIONS

        if category == "service_relationships":
            if self.should_ask_event_questions(answers):
                base_questions += EVENT_DRIVEN_QUESTIONS

        return base_questions
```

## Flag Handling

### --no-questions

Skip all interactive clarification:

```python
if flags.get("no_questions"):
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("⚠️ --no-questions flag: Skipping interactive session")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Use defaults or fail gracefully
    print("ERROR: /system-plan requires interactive input")
    print("       --no-questions not supported for architecture planning")
    exit(1)
```

### --defaults

Use clarification defaults:

```python
if flags.get("defaults"):
    # Use default methodology
    answers["q5_methodology"] = "modular"

    # Use default deployment
    answers["q9_deployment"] = "monolith"

    # Auto-continue at checkpoints
    checkpoint_choice = "c"  # Always continue
```

### --context

Include additional context files:

```python
context_files = flags.get("context", [])
for context_file in context_files:
    with open(context_file) as f:
        additional_context = f.read()
    print(f"✓ Loaded context from {context_file}")
```

## Error Handling

### Graphiti Unavailable

```python
if not client:
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("⚠️ WARNING: Graphiti unavailable")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("")
    print("Architecture planning will continue WITHOUT persistence.")
    print("Markdown files will be generated, but context won't be")
    print("queryable by /feature-plan or AutoBuild coach.")
    print("")
    print("To enable Graphiti:")
    print("  1. Install: pip install guardkit-py[graphiti]")
    print("  2. Configure: Add Graphiti settings to .env")
    print("")

    choice = input("Continue without persistence? [Y/n]: ")
    if choice.lower() == "n":
        print("Cancelled.")
        exit(0)
```

### Empty Answers

```python
answer = input("Q1. What does this system do? ")
if not answer or answer.strip() == "":
    print("⚠️ Empty answer - using placeholder")
    answer = "[To be defined]"
```

### Cancelled Session

```python
checkpoint_choice = input("Your choice [C/R/S/A]: ")

if checkpoint_choice.lower() == "s":
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("⚠️ Session cancelled (remaining categories skipped)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("")
    print("Partial architecture captured:")
    print(f"  • Completed: {completed_categories} categories")
    print(f"  • Skipped: {remaining_categories} categories")
    print("")
    print("Generated files reflect partial architecture only.")
    print("Run /system-plan again to complete.")
    break
```

## Examples

### Example 1: Simple Modular Project (Setup)

```bash
/system-plan "CLI task workflow tool"

🏗️ Mode: setup (no existing architecture context found)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 SYSTEM PLANNING: CLI task workflow tool
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Category 1: Domain & Methodology Discovery
  Q1. What does this system do?
      > A CLI tool that helps developers manage tasks with built-in quality gates

  Q2. Who are the primary users?
      > Software developers, AI agents

  Q5. What architectural methodology best fits this project?
      [M]odular (DEFAULT) | [L]ayered | [D]DD | [E]vent-Driven | [N]ot sure
      > M

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Category 1: Domain & Methodology Discovery
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Captured:
  • Purpose: CLI tool for task management with quality gates
  • Users: Developers, AI agents
  • Methodology: Modular

[C]ontinue | [R]evise | [S]kip | [A]DR?
> C

[Continue through remaining categories...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ARCHITECTURE DOCUMENTATION CREATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Created: docs/architecture/
  ├── ARCHITECTURE.md
  ├── system-context.md
  ├── components.md
  ├── crosscutting-concerns.md
  └── decisions/
      └── ADR-001-use-click-for-cli.md

Graphiti context:
  ✓ 5 components persisted
  ✓ 2 cross-cutting concerns persisted
  ✓ 1 ADR persisted
```

### Example 2: Complex DDD Project (Setup)

```bash
/system-plan "Power of Attorney platform"

🏗️ Mode: setup (no existing architecture context found)

Category 1: Domain & Methodology Discovery
  Q5. What architectural methodology best fits this project?
      > D (DDD)

Category 2: System Structure
  Q6. What are the major components?
      > Attorney Management, Document Generation, Financial Oversight, Compliance

  Q6d. How do these map to bounded contexts? (DDD-specific)
       > Each is a bounded context with its own domain model

  Q7d. What are the aggregate roots? (DDD-specific)
       > Donor (Attorney Mgmt), LPADocument (Doc Gen), Account (Financial)

  Q9d. What domain events flow between contexts? (DDD-specific)
       > DonorCreated, LPAFiled, TransactionFlagged

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Category 2: System Structure
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Captured 4 bounded contexts:
  • Attorney Management — donor, attorney, aggregate: Donor
  • Document Generation — LPA forms, aggregate: LPADocument
  • Financial Oversight — accounts, transactions, aggregate: Account
  • Compliance — OPG registration, identity verification

Domain events: DonorCreated, LPAFiled, TransactionFlagged

[C]ontinue | [R]evise | [S]kip | [A]DR?
> A

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 ARCHITECTURE DECISION RECORD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Title: Use anti-corruption layer for Moneyhub integration
[... capture ADR ...]

✓ ADR-001 captured. Continuing to Category 3...

[Continue through remaining categories...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ARCHITECTURE DOCUMENTATION CREATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Created: docs/architecture/
  ├── ARCHITECTURE.md
  ├── system-context.md
  ├── bounded-contexts.md (DDD variant)
  ├── crosscutting-concerns.md
  └── decisions/
      ├── ADR-001-moneyhub-acl.md
      ├── ADR-002-event-sourcing.md
      └── ADR-003-cqrs-pattern.md
```

### Example 3: Review Mode

```bash
/system-plan "add real-time notifications" --mode=review

🔍 Mode: review (evaluating against existing architecture)

Analyzing against:
  • 4 bounded contexts
  • 7 existing ADRs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 IMPACT ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Affected components:
  ⚠️ Attorney Management — triggers on status changes
  ⚠️ Financial Oversight — alerts on anomalies

Conflicts:
  ⚠️ ADR-003: "Synchronous HTTP only"
      → Notifications need async/WebSocket

Options:
  [A]ccept | [R]eject | [M]odify | [F]eature-plan | [C]ancel

> F

Launching /feature-plan with architecture context...

[Executes /feature-plan "add real-time notifications"]
```

---

## CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE

**IMPORTANT: YOU MUST FOLLOW THESE STEPS EXACTLY. THIS IS AN INTERACTIVE ORCHESTRATION COMMAND.**

When the user runs `/system-plan "description"`, you MUST execute these steps in order:

### Step 1: Parse Arguments

```python
import sys

# Extract description and flags
description = args[0]  # Required
mode = flags.get("mode", None)  # Auto-detect if not specified
focus = flags.get("focus", "all")
no_questions = flags.get("no_questions", False)
defaults = flags.get("defaults", False)
context_files = flags.get("context", [])
```

### Step 2: Initialize Graphiti

```python
from guardkit.knowledge.graphiti_service import get_graphiti
from guardkit.planning.graphiti_arch import SystemPlanGraphiti

# Get Graphiti client (returns None if unavailable)
client = get_graphiti()

if client:
    project_id = "current_project"  # Or extract from .guardkit/config
    sp = SystemPlanGraphiti(client, project_id)
else:
    print("⚠️ WARNING: Graphiti unavailable")
    print("Architecture planning will continue WITHOUT persistence.")
    # Ask user if they want to continue
    choice = input("Continue without persistence? [Y/n]: ")
    if choice.lower() == "n":
        exit(0)
    sp = None
```

### Step 3: Auto-Detect Mode (if not specified)

```python
if not mode:
    if sp and sp.has_architecture_context():
        mode = "refine"
    else:
        mode = "setup"

# Display mode
if mode == "setup":
    print("🏗️ Mode: setup (no existing architecture context found)")
elif mode == "refine":
    print("🔄 Mode: refine (updating existing architecture)")
elif mode == "review":
    print("🔍 Mode: review (evaluating change against existing architecture)")
```

### Step 4: Execute Mode-Specific Flow

#### If mode == "setup":

```python
from guardkit.planning.question_adapter import SetupQuestionAdapter
from guardkit.knowledge.entities.architecture import (
    ComponentDef, SystemContextDef, CrosscuttingConcernDef, ArchitectureDecision
)

adapter = SetupQuestionAdapter()
answers = {}
captured_components = []
captured_concerns = []
captured_adrs = []

# Category 1: Domain & Methodology
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("📋 SYSTEM PLANNING:", description)
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print()
print("Category 1: Domain & Methodology Discovery")

# Ask Q1-Q5 (including methodology selection)
# ... collect answers ...

# Checkpoint after Category 1
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("✓ Category 1: Domain & Methodology Discovery")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print()
print("Captured:")
print(f"  • Purpose: {answers['q1_purpose']}")
print(f"  • Users: {answers['q2_users']}")
print(f"  • Methodology: {answers['q5_methodology']}")
print()
checkpoint = input("[C]ontinue | [R]evise | [S]kip | [A]DR? ")

if checkpoint.lower() == "a":
    # Capture ADR inline
    adr = capture_adr_inline()
    captured_adrs.append(adr)
    if sp:
        sp.upsert_adr(adr)

if checkpoint.lower() == "s":
    print("Session cancelled")
    break

# Upsert system context to Graphiti after Category 1
system_context = SystemContextDef(
    name=description,
    purpose=answers["q1_purpose"],
    users=answers["q2_users"],
    methodology=answers["q5_methodology"],
)
if sp:
    sp.upsert_system_context(system_context)

# Category 2: System Structure (adapts to methodology)
questions = adapter.get_questions_for_category("system_structure", answers)
# ... ask adapted questions ...
# ... capture components ...
# ... checkpoint ...
# ... upsert components to Graphiti ...

for comp in captured_components:
    if sp:
        sp.upsert_component(comp)

# Continue for Categories 3-6
# ... each with checkpoint and Graphiti upsert ...
```

#### If mode == "refine":

```python
# Show current architecture
if sp:
    summary = sp.get_architecture_summary()
    print("Current architecture summary:")
    print(f"  • Methodology: {summary.get('methodology')}")
    print(f"  • {len(summary.get('components', []))} components")
    print(f"  • {len(summary.get('decisions', []))} ADRs")

# Ask what to refine
print("What would you like to refine?")
print("[C]omponents | [S]ervices | [D]ecisions | [T]echnology | [X]rosscutting | [A]ll")
choice = input("Your choice: ")

# Show current state for selected area
# Ask what changed (conversational, not full questionnaire)
# Update Graphiti entities
# Regenerate affected markdown
```

#### If mode == "review":

```python
# Load architecture context
if sp:
    relevant_context = sp.get_relevant_context_for_topic(description)

    print(f"Analyzing '{description}' against:")
    print(f"  • {len(relevant_context.get('components', []))} components")
    print(f"  • {len(relevant_context.get('decisions', []))} ADRs")

    # Perform impact analysis
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📊 IMPACT ANALYSIS")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Analyze affected components
    # Identify conflicting ADRs
    # Suggest architectural implications

    # Decision checkpoint
    print("Options:")
    print("  [A]ccept | [R]eject | [M]odify | [F]eature-plan | [C]ancel")
    decision = input("Your choice: ")

    if decision.lower() == "f":
        # Chain to /feature-plan
        print("Launching /feature-plan with architecture context...")
        # Execute /feature-plan with enriched context
```

### Step 5: Generate Markdown Artefacts

```python
from guardkit.planning.architecture_writer import ArchitectureWriter

writer = ArchitectureWriter()

# Prepare data
system = {
    "name": description,
    "purpose": answers.get("q1_purpose"),
    "methodology": answers.get("q5_methodology"),
}

components = [
    {"name": c.name, "description": c.description}
    for c in captured_components
]

concerns = [
    {"name": cc.name, "category": cc.category}
    for cc in captured_concerns
]

decisions = [
    {"number": adr.number, "title": adr.title}
    for adr in captured_adrs
]

# Write all artefacts
output_dir = "docs/architecture"
writer.write_all(output_dir, system, components, concerns, decisions)

# Display summary
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("✅ ARCHITECTURE DOCUMENTATION CREATED")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print()
print(f"Created: {output_dir}/")
print("  ├── ARCHITECTURE.md")
print("  ├── system-context.md")
print("  ├── components.md")
print("  ├── crosscutting-concerns.md")
print("  └── decisions/")
print(f"      └── ... {len(decisions)} ADRs")
```

### Step 6: Verify Graphiti Persistence

```python
if sp:
    # Final verification that all entities were persisted
    print()
    print("Graphiti context:")
    print(f"  ✓ {len(captured_components)} components persisted")
    print(f"  ✓ {len(captured_concerns)} cross-cutting concerns persisted")
    print(f"  ✓ {len(captured_adrs)} ADRs persisted")
    print(f"  ✓ 1 system context persisted")
```

### What NOT to Do

DO NOT:
- Skip the interactive question flow (this is an interactive command)
- Batch all Graphiti upserts at the end (upsert after each category)
- Skip checkpoints (user must review each category)
- Proceed without user confirmation at decision points
- Generate code implementations (this is a planning command)
- Skip mode auto-detection (always detect unless overridden)
- Ignore Graphiti unavailability (warn user, offer to continue)

### Error Handling

```python
# If Graphiti unavailable
if not client:
    print("⚠️ Graphiti unavailable - continuing without persistence")

# If empty answer
if not answer.strip():
    answer = "[To be defined]"
    print("⚠️ Empty answer - using placeholder")

# If session cancelled
if checkpoint == "s":
    print("⚠️ Session cancelled - partial architecture captured")
    # Generate what we have so far
    break
```

### Example Execution Trace

```
User: /system-plan "CLI tool for developers"

Claude executes:
  1. Initialize Graphiti → client = get_graphiti()
  2. Auto-detect mode → "setup" (no architecture exists)
  3. Display: "🏗️ Mode: setup"
  4. Ask Category 1 questions (including methodology)
  5. Checkpoint after Category 1
  6. Upsert system_context to Graphiti
  7. Ask Category 2 questions (adapted to methodology)
  8. Checkpoint after Category 2
  9. Upsert components to Graphiti
  10. ... continue for Categories 3-6 ...
  11. Generate markdown files via ArchitectureWriter
  12. Display summary with file locations
```

Remember: This is an **interactive planning command**. You MUST present questions, wait for user input, show checkpoints, and allow the user to guide the session. DO NOT try to answer the questions yourself or auto-complete the flow.
