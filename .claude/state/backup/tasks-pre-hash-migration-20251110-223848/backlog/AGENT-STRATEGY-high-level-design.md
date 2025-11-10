# Agent Strategy: High-Level Design
## AI-First Creation with Complementary Discovery

**Date**: 2025-11-01
**Status**: ✅ **APPROVED** - Ready for implementation
**Context**: Template creation automation (EPIC-001)
**Decisions Confirmed**: 2025-11-01 (all 4 design decisions approved)

---

## Executive Summary

**Core Principle**: Claude Code should **create appropriate agents** based on codebase analysis, not just discover existing ones. External discovery is **complementary**, providing suggestions that users can optionally adopt.

**Agent Hierarchy** (priority order):
1. **User's Custom Agents** (`.claude/agents/`) - Highest priority
2. **Template-Specific Agents** (from template being used/generated)
3. **Global Built-in Agents** (`installer/global/agents/`)
4. **AI-Generated Agents** (Claude creates on-the-fly)
5. **External Community Agents** (optional suggestions)

**Key Insight**: Don't just find agents - **create the right agents** for each project.

---

## Problem Statement

### Current Thinking (Too Narrow)
```
Discover agents from:
- Local agents (installer/global/agents/)
- External sources (subagents.cc, GitHub)
→ Present list to user
→ User selects
```

**Issues**:
- Assumes agents exist somewhere
- Misses Claude Code's ability to create agents
- Doesn't check user's existing agents
- May duplicate agents in templates

### Better Thinking (AI-First)
```
1. Check what agents user already has
2. Check what agents template already has
3. Analyze codebase to understand needs
4. CREATE appropriate agents that don't exist
5. Optionally suggest community agents as supplements
```

**Benefits**:
- Leverages Claude Code's core capability
- Avoids duplication
- Context-aware (project-specific)
- External discovery is bonus, not requirement

---

## Agent Discovery & Creation Flow

### Phase 1: Inventory (What Exists)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Scan User's Custom Agents                                │
│    Location: .claude/agents/*.md                            │
│    Priority: HIGHEST (user's own creations)                 │
│    Example: mycompany-react-specialist.md                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Check Template Agents (if using existing template)       │
│    Location: installer/local/templates/mytemplate/agents/   │
│    Priority: HIGH (template-specific)                       │
│    Example: maui-appshell-specialist.md                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Scan Global Built-in Agents                              │
│    Location: installer/global/agents/*.md                   │
│    Priority: MEDIUM (general-purpose)                       │
│    Example: architectural-reviewer.md                       │
└─────────────────────────────────────────────────────────────┘
```

**Output**: Complete inventory of existing agents

### Phase 2: Analysis (What's Needed)

```
┌─────────────────────────────────────────────────────────────┐
│ AI Analyzes Codebase (TASK-002)                             │
│                                                              │
│ Extracts:                                                    │
│ - Language: C# / .NET MAUI                                   │
│ - Architecture: MVVM + AppShell                              │
│ - Patterns: Domain operations, ErrorOr<T>, CQRS             │
│ - Testing: xUnit + FluentAssertions                          │
│ - Layers: Domain, Application, Infrastructure, Presentation │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ AI Determines Agent Needs                                    │
│                                                              │
│ "This project needs:                                         │
│  1. MAUI XAML specialist (Views, Styles, Resources)         │
│  2. MVVM ViewModel specialist (INotifyPropertyChanged)       │
│  3. Domain operations specialist (Verb-based operations)     │
│  4. ErrorOr pattern specialist (Railway-oriented)            │
│  5. xUnit testing specialist (Arrange-Act-Assert)            │
└─────────────────────────────────────────────────────────────┘
```

**Output**: List of needed agent capabilities

### Phase 3: Gap Analysis (What's Missing)

```
┌─────────────────────────────────────────────────────────────┐
│ Compare: What Exists vs What's Needed                       │
│                                                              │
│ Needed Agents:                         Status:               │
│ ✅ architectural-reviewer          → Exists (global)         │
│ ✅ code-reviewer                   → Exists (global)         │
│ ⚠️  maui-xaml-specialist           → User has custom version │
│ ❌ maui-appshell-navigator         → MISSING (create)        │
│ ❌ errror-pattern-specialist       → MISSING (create)        │
│ ❓ maui-testing-specialist         → Found on subagents.cc   │
└─────────────────────────────────────────────────────────────┘
```

**Output**:
- ✅ Agents to use (already exist)
- ⚠️ Agents to prefer (user's custom over generic)
- ❌ Agents to create (missing capabilities)
- ❓ Agents to suggest (external options)

### Phase 4: Creation (Fill Gaps)

```
┌─────────────────────────────────────────────────────────────┐
│ AI Creates Missing Agents                                    │
│                                                              │
│ For: maui-appshell-navigator                                 │
│                                                              │
│ Claude analyzes:                                             │
│ - How AppShell navigation is used in this project           │
│ - Naming conventions for page registration                  │
│ - Route patterns                                             │
│ - Good example files from codebase                           │
│                                                              │
│ Generates:                                                   │
│ ---                                                          │
│ name: maui-appshell-navigator                                │
│ description: Specialist in .NET MAUI AppShell navigation     │
│ tools: [Read, Write, Edit, Grep]                             │
│ ---                                                          │
│                                                              │
│ # MAUI AppShell Navigation Specialist                        │
│                                                              │
│ Expert in .NET MAUI AppShell-based navigation patterns...    │
│                                                              │
│ ## Capabilities                                              │
│ - Route registration and naming conventions                  │
│ - Deep linking and query parameters                          │
│ - Navigation best practices for this architecture            │
│ ...                                                          │
└─────────────────────────────────────────────────────────────┘
```

**Output**: Generated agent definitions tailored to project

### Phase 5: Suggestions (Optional Discovery)

```
┌─────────────────────────────────────────────────────────────┐
│ External Agent Suggestions (Complementary)                   │
│                                                              │
│ "I've created the agents you need. Additionally, I found:    │
│                                                              │
│ 📦 From subagents.cc:                                        │
│    - maui-testing-specialist (98 downloads)                  │
│      Similar to what we created, but includes Appium         │
│      [Preview] [Use Instead] [Ignore]                        │
│                                                              │
│ 📦 From wshobson/agents:                                     │
│    - xaml-performance-analyzer                               │
│      Not currently needed, but might be useful later         │
│      [Add to Project] [Ignore]                               │
│                                                              │
│ 💡 You already have: mycompany-maui-specialist               │
│    in .claude/agents/ - I'm using that instead of generic.   │
└─────────────────────────────────────────────────────────────┘
```

**Output**: Optional suggestions user can review

---

## Agent Priority Hierarchy

### 1. User's Custom Agents (`.claude/agents/`)

**Priority**: HIGHEST ⭐⭐⭐

**Why**: User-created, project-specific, company standards

**Example**:
```
.claude/agents/
├── mycompany-react-specialist.md     # Company React patterns
├── mycompany-security-reviewer.md    # Company security standards
└── mycompany-logging-specialist.md   # Company logging library
```

**Behavior**:
- Always use user's custom agents over generic equivalents
- Notify user: "Using your custom mycompany-react-specialist"
- Never suggest external agent if user has custom version

### 2. Template-Specific Agents

**Priority**: HIGH ⭐⭐

**Why**: Designed for specific template architecture

**Example**:
```
installer/local/templates/maui-appshell/agents/
├── maui-appshell-specialist.md       # AppShell-specific patterns
├── maui-viewmodel-generator.md       # MVVM patterns for this template
└── maui-domain-operations.md         # Domain layer for this template
```

**Behavior**:
- Include all template agents when using/generating template
- These agents understand template conventions
- Can be customized by user (copied to .claude/agents/)

### 3. Global Built-in Agents

**Priority**: MEDIUM ⭐

**Why**: General-purpose, well-tested, always available

**Example**:
```
installer/global/agents/
├── architectural-reviewer.md
├── code-reviewer.md
├── test-verifier.md
├── security-specialist.md
└── devops-specialist.md
```

**Behavior**:
- Use for general capabilities (review, testing, security)
- Foundation that works across all projects
- Can be specialized via creation if needed

### 4. AI-Generated Agents

**Priority**: MEDIUM ⭐ (context-specific)

**Why**: Tailored to specific project needs, created on-demand

**Example**:
```
Generated for MAUI project:
├── maui-appshell-navigator.md        # Created based on codebase analysis
├── errror-pattern-specialist.md      # Created for ErrorOr<T> usage
└── cqrs-command-handler.md           # Created for CQRS pattern
```

**Behavior**:
- Created when gap identified (needed but doesn't exist)
- Tailored to project's specific patterns and conventions
- Can be saved to template or .claude/agents/ for reuse

### 5. External Community Agents

**Priority**: LOW ⭐ (suggestions only)

**Why**: May not match project conventions, complementary

**Example**:
```
Suggested from subagents.cc:
- react-state-specialist (generic)
- maui-testing-specialist (community best practices)
```

**Behavior**:
- Suggested as optional additions
- User reviews and decides
- Preview before adding
- Lower priority than custom/generated agents

---

## Duplication Prevention Strategy

### Check Before Recommending

```python
def should_recommend_agent(candidate_agent: Agent) -> Decision:
    """Determine if agent should be recommended"""

    # 1. Check user's custom agents first
    user_agent = find_in_user_agents(candidate_agent.name)
    if user_agent:
        return Decision.skip(
            reason=f"You already have custom {candidate_agent.name}",
            action="Using your version"
        )

    # 2. Check template agents
    template_agent = find_in_template_agents(candidate_agent.name)
    if template_agent:
        return Decision.skip(
            reason=f"Template includes {candidate_agent.name}",
            action="Using template version"
        )

    # 3. Check for similar agents (semantic similarity)
    similar = find_similar_agents(candidate_agent.description)
    if similar:
        return Decision.ask_user(
            reason=f"Similar to existing {similar.name}",
            question="Use existing or add this one?",
            options=["Use existing", "Add both", "Preview difference"]
        )

    # 4. Check if capability already covered
    if capability_covered(candidate_agent.capabilities):
        return Decision.optional(
            reason="Capability already covered by existing agents",
            action="Available as optional addition"
        )

    # 5. Recommend
    return Decision.recommend(
        reason="Adds new capability",
        action="Include in template"
    )
```

### Deduplication Rules

| Scenario | Action |
|----------|--------|
| **Exact match (same name)** | Skip, use existing |
| **User's custom vs generic** | Use user's custom, notify |
| **Template vs global** | Use template version |
| **Similar but different** | Ask user, show comparison |
| **Capability overlap** | Mark as optional |
| **Unique capability** | Recommend |

---

## AI-Generated Agent Creation Process

### Input: Codebase Analysis

```json
{
  "language": "C#",
  "frameworks": [".NET MAUI 8.0"],
  "architecture": "MVVM + AppShell",
  "patterns": {
    "navigation": "AppShell routing with deep links",
    "error_handling": "ErrorOr<T> pattern",
    "domain_operations": "Verb-based (GetProducts, CreateOrder)",
    "dependency_injection": "Microsoft.Extensions.DependencyInjection"
  },
  "layers": ["Domain", "Application", "Infrastructure", "Presentation"],
  "testing": "xUnit + FluentAssertions",
  "example_files": [
    "src/Domain/Products/GetProducts.cs",
    "src/Presentation/Views/ProductListPage.xaml",
    "src/Presentation/ViewModels/ProductListViewModel.cs"
  ]
}
```

### Process: AI Agent Generation

```
┌──────────────────────────────────────────────────────────────┐
│ AI Prompt: Create Agent Definition                           │
│                                                               │
│ "Based on this MAUI project analysis:                         │
│  - AppShell navigation with custom routes                     │
│  - Naming convention: {Verb}{Entity}Page for views           │
│  - Good examples: ProductListPage.xaml, SettingsPage.xaml    │
│                                                               │
│ Create a 'maui-appshell-navigator' agent that:               │
│ 1. Understands this project's navigation patterns            │
│ 2. Can register new routes following conventions             │
│ 3. Handles deep linking and query parameters                 │
│ 4. Uses the patterns from example files                      │
│                                                               │
│ Return as complete agent markdown definition."               │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│ AI Generates Agent Definition                                 │
│                                                               │
│ ---                                                           │
│ name: maui-appshell-navigator                                 │
│ description: Specialist in .NET MAUI AppShell navigation      │
│ tools: [Read, Write, Edit, Grep]                              │
│ tags: [maui, navigation, appshell, xaml]                      │
│ ---                                                           │
│                                                               │
│ # MAUI AppShell Navigation Specialist                         │
│                                                               │
│ Expert in .NET MAUI AppShell-based navigation for this        │
│ project architecture. Understands routing conventions,        │
│ deep linking, and navigation patterns used in this codebase.  │
│                                                               │
│ ## Navigation Conventions in This Project                     │
│                                                               │
│ ### Page Naming                                               │
│ - Pattern: `{Verb}{Entity}Page` (ProductListPage)            │
│ - Location: `Presentation/Views/`                             │
│ - XAML + code-behind pattern                                  │
│                                                               │
│ ### Route Registration                                        │
│ ```csharp                                                     │
│ Routing.RegisterRoute("products/list", typeof(ProductListPage)); │
│ ```                                                           │
│ ...                                                           │
└──────────────────────────────────────────────────────────────┘
```

### Output: Tailored Agent Definition

**Key Characteristics**:
- ✅ Project-specific (knows this project's conventions)
- ✅ Example-based (learned from actual code)
- ✅ Context-aware (understands architecture)
- ✅ Reusable (can be saved to template)

---

## User Experience Flows

### Flow 1: Template Creation (Brownfield)

```bash
$ /template-create "mycompany-maui"

[Q&A Session - 8 questions...]

🔍 Analyzing codebase...
✓ Language: C# / .NET MAUI 8.0
✓ Architecture: MVVM + AppShell
✓ Patterns: ErrorOr, CQRS, Verb-based domain operations

📦 Checking existing agents...
✓ Found 3 custom agents in .claude/agents/
✓ Found 15 global agents in installer/global/agents/

🤖 Determining agent needs...
✓ Need: MAUI AppShell navigation specialist
✓ Need: ErrorOr pattern specialist
✓ Need: MVVM ViewModel generator
✓ Need: Domain operation specialist

💡 Creating project-specific agents...
  ✓ Created: maui-appshell-navigator
  ✓ Created: errror-pattern-specialist
  ✓ Created: maui-viewmodel-generator
  ✓ Created: domain-operation-specialist

✅ Agent Setup Complete:
  • Using your custom: mycompany-logging-specialist
  • Using global: architectural-reviewer, code-reviewer, test-verifier
  • Created for this project: 4 specialized agents

🌐 Optional: Discover community agents? [Y/n] y

📡 Searching external sources...
  ✓ Found 12 agents from subagents.cc
  ✓ Found 8 agents from wshobson/agents

📋 Suggestions (optional):
  1. maui-testing-specialist (subagents.cc)
     Similar to test-verifier but includes Appium patterns
     [Preview] [Add] [Skip]

  2. xaml-performance-analyzer (wshobson/agents)
     Performance profiling for XAML layouts
     [Preview] [Add] [Skip]

[User reviews suggestions...]

✅ Template created: mycompany-maui
  Location: installer/local/templates/mycompany-maui/
  Agents: 8 total (3 custom, 15 global, 4 generated, 0 external)
```

### Flow 2: Template Usage (Using Existing Template)

```bash
$ agentic-init mycompany-maui

📦 Loading template: mycompany-maui
  ✓ Manifest loaded
  ✓ Settings loaded
  ✓ CLAUDE.md loaded

🤖 Setting up agents...
  ✓ Template agents: 4 specialized agents
  ✓ Global agents: 15 built-in agents

💡 Checking for updates...
  ℹ️  Your custom agents in .claude/agents/ take precedence
  ✓ Using: mycompany-logging-specialist (custom)
  ✓ Using: maui-appshell-navigator (template)

✅ Project initialized with 19 agents
```

### Flow 3: Greenfield Template Creation

```bash
$ /template-init

[Q&A Session - 9 sections, ~40 questions...]

Technology Stack: .NET MAUI
Architecture: MVVM
Navigation: AppShell
Error Handling: ErrorOr<T>
Testing: xUnit

🤖 Generating agents for this configuration...
  ✓ Created: maui-mvvm-specialist
  ✓ Created: maui-appshell-navigator
  ✓ Created: errror-pattern-specialist
  ✓ Created: xunit-testing-specialist

💡 Including standard agents...
  ✓ architectural-reviewer
  ✓ code-reviewer
  ✓ test-verifier

🌐 Suggest community agents? [Y/n] n

✅ Template created: mycompany-new-template
  Agents: 7 total (4 generated, 3 global)
```

---

## Implementation Breakdown

### TASK-003: Multi-Source Agent Scanner (Revised)

**Scan 3 locations** (not just global):

```python
def scan_all_agent_sources() -> AgentInventory:
    """Scan all agent sources in priority order"""

    inventory = AgentInventory()

    # 1. User's custom agents (highest priority)
    user_agents = scan_directory(Path(".claude/agents/"))
    inventory.add(user_agents, priority=Priority.HIGHEST, source="custom")

    # 2. Template agents (if using template)
    if current_template:
        template_agents = scan_directory(
            Path(f"installer/local/templates/{current_template}/agents/")
        )
        inventory.add(template_agents, priority=Priority.HIGH, source="template")

    # 3. Global built-in agents
    global_agents = scan_directory(Path("installer/global/agents/"))
    inventory.add(global_agents, priority=Priority.MEDIUM, source="global")

    return inventory
```

**Estimated**: 6 hours → 8 hours (3 sources instead of 1)

### TASK-004A: AI Agent Generator (NEW)

**Create agents based on codebase analysis**:

```python
def generate_needed_agents(
    analysis: CodebaseAnalysis,
    existing_agents: AgentInventory
) -> List[GeneratedAgent]:
    """Generate agents to fill capability gaps"""

    # Determine what agents are needed
    needed_capabilities = identify_needed_capabilities(analysis)

    # Check what already exists
    gaps = find_capability_gaps(needed_capabilities, existing_agents)

    # Generate agents for gaps
    generated = []
    for gap in gaps:
        agent = ai_generate_agent(
            capability=gap,
            project_context=analysis,
            examples=analysis.example_files
        )
        generated.append(agent)

    return generated
```

**Estimated**: 8 hours, Complexity 6/10

### TASK-004B: External Agent Discovery (Optional)

**Complementary suggestions** (your redesigned TASK-004):

```python
def suggest_external_agents(
    analysis: CodebaseAnalysis,
    existing_agents: AgentInventory,
    generated_agents: List[GeneratedAgent]
) -> List[AgentSuggestion]:
    """Suggest external agents as complementary options"""

    # Discover external agents
    external = discover_external_agents(sources=enabled_sources)

    # Filter out duplicates
    unique = filter_duplicates(external, existing_agents, generated_agents)

    # Rank by relevance
    suggestions = rank_by_relevance(unique, analysis)

    # Mark as optional
    for suggestion in suggestions:
        suggestion.optional = True
        suggestion.preview_available = True

    return suggestions
```

**Estimated**: 6 hours, Complexity 5/10

### TASK-009: AI-Powered Agent Recommendation (Revised)

**Orchestrate the full flow**:

```python
def recommend_agents_for_template(analysis: CodebaseAnalysis) -> AgentRecommendation:
    """Complete agent recommendation flow"""

    # Phase 1: Inventory
    existing = scan_all_agent_sources()

    # Phase 2: Gap Analysis
    gaps = identify_capability_gaps(analysis, existing)

    # Phase 3: Generation
    generated = generate_needed_agents(gaps, analysis)

    # Phase 4: External Suggestions (optional)
    if user_wants_external_suggestions:
        suggestions = suggest_external_agents(analysis, existing, generated)
    else:
        suggestions = []

    # Phase 5: Deduplication
    final = deduplicate_and_prioritize(existing, generated, suggestions)

    return AgentRecommendation(
        use_existing=final.existing,
        newly_generated=final.generated,
        optional_suggestions=final.suggestions
    )
```

**Estimated**: 4 hours → 6 hours (orchestration more complex)

---

## Revised Epic Timeline

### Wave 0: Foundation

| Task | Hours | Change |
|------|-------|--------|
| TASK-001 | 8h | +2h (shared infra) |
| TASK-001B | 8h | NEW (greenfield Q&A) |
| TASK-002 | 11h | +3h (error handling) |
| TASK-003 | 8h | +2h (3 sources) |
| **Total** | **35h** | was 21h |

### Wave 1: Agent & Template Generation

| Task | Hours | Change |
|------|-------|--------|
| TASK-004A | 8h | NEW (AI agent generator) |
| TASK-004B | 6h | OPTIONAL (external discovery) |
| TASK-005 | 4h | no change |
| TASK-006 | 3h | no change |
| TASK-007 | 4h | no change |
| TASK-008 | 7h | no change |
| TASK-009 | 6h | +2h (orchestration) |
| **Total** | **38h** | was 26h (without TASK-004A) |

### Total Impact

**Without Optional External Discovery**:
- Original: 85h
- Revised: 85h - 3h (old TASK-004) + 17h (pre-work) + 10h (additions) = 109h
- **Timeline**: 5.5 weeks @ 20h/week

**With Optional External Discovery**:
- Add: 6h (TASK-004B)
- **Timeline**: 5.75 weeks @ 20h/week

**Parallel Execution** (Conductor):
- ~60 hours actual time
- **Timeline**: 3 weeks @ 20h/week

---

## Design Decisions (Confirmed)

### Decision 1: Agent Priority Order ✅

**CONFIRMED**: User Custom > Template > Global > AI-Generated > External

```
Priority Order:
1. Check user's custom agents (.claude/agents/) ⭐⭐⭐ HIGHEST
2. Check template agents (template/agents/) ⭐⭐ HIGH
3. Check global agents (installer/global/) ⭐ MEDIUM
4. CREATE needed agents (AI-generated) ⭐ MEDIUM (context-specific)
5. Suggest external agents (optional) ⭐ LOW (suggestions only)
```

**Rationale**: User's custom agents always take precedence. AI generates what's missing. External discovery is complementary.

### Decision 2: External Discovery Opt-In ✅

**CONFIRMED**: Opt-in (default OFF)

```bash
🌐 Discover community agents? [y/N] _
```

**Implementation**:
- Default: External discovery disabled
- User must explicitly request: `y` or `--discover-external`
- Skips external discovery entirely if user says `N`
- Fast path: No network calls unless requested

**Rationale**: Doesn't slow down default flow. Users who want external agents can opt-in.

### Decision 3: Generated Agent Reuse ✅

**CONFIRMED**: Ask user ("Save for future projects?")

```bash
💡 Created: maui-appshell-navigator

   This agent is tailored to your project's patterns.
   Save to .claude/agents/ for reuse in future projects? [y/N] _
```

**Implementation**:
- Default: Agents stay in template (project-specific)
- User can save to `.claude/agents/` for reuse
- Saved agents become "custom" (highest priority)
- Future projects auto-detect and use saved agents

**Rationale**: User control. Some agents are project-specific, others are reusable.

### Decision 4: Deduplication Strategy ✅

**CONFIRMED**: Auto-skip external (user's custom takes precedence)

```bash
📦 Checking existing agents...
✓ Found mycompany-react-specialist in .claude/agents/

🌐 Discover community agents? [y/N] y

📡 Searching external sources...
  ℹ️  Skipping react-specialist (you have custom version)
  ℹ️  Skipping react-state-manager (capability covered)
  ✓ Found react-testing-specialist (new capability)
```

**Implementation**:
- Exact name match: Auto-skip, use user's version
- Similar capability: Auto-skip, notify user
- Unique capability: Suggest as optional
- No interactive prompts for duplicates (clean UX)

**Rationale**: Respect user's custom agents. Don't clutter with duplicates.

---

## Implementation Roadmap (Confirmed)

### Phase 1: MVP (Core Capability) ✅ APPROVED

**Scope**:
- ✅ Multi-source scanning (user, template, global) - TASK-003
- ✅ AI-powered agent generation - TASK-004A
- ✅ Smart deduplication logic
- ✅ Agent reuse prompts (save to .claude/agents/)
- ❌ External discovery disabled by default

**Tasks**:
- TASK-003: Multi-Source Agent Scanner (8h)
- TASK-004A: AI Agent Generator (8h)
- TASK-009: Agent Orchestration (6h)

**Estimated**: 22 hours (agent system only)
**Priority**: HIGH (blocking template creation)

**Benefits**:
- ✅ Leverages proven Claude Code agent creation
- ✅ Fast (no network calls unless requested)
- ✅ Respects user's custom agents
- ✅ Context-aware (project-specific generation)
- ✅ No external dependencies

### Phase 2: Enhancement (Optional) ✅ APPROVED

**Scope**:
- ✅ External agent discovery (opt-in) - TASK-004B
- ✅ WebFetch + AI extraction
- ✅ Configurable sources (agent-sources.json)
- ✅ 24-hour caching
- ✅ Graceful degradation

**Tasks**:
- TASK-004B: External Agent Discovery (6h)

**Estimated**: 6 hours
**Priority**: MEDIUM (optional enhancement, Phase 2)

**Benefits**:
- ✅ Access to community agents
- ✅ AI-powered extraction (not brittle scraping)
- ✅ User-controlled (opt-in)
- ✅ Doesn't slow down default flow

### Timeline

**Phase 1 (Include in EPIC-001)**:
- Wave 0: TASK-003 (8h)
- Wave 1: TASK-004A (8h), TASK-009 (6h)
- **Total**: 22 hours
- **Milestone**: Template creation works with AI-generated agents

**Phase 2 (Post-EPIC-001 or optional)**:
- TASK-004B (6h)
- **Total**: 6 hours
- **Milestone**: External agent discovery available

**Rationale**:
- ✅ Claude Code creates excellent agents (proven capability)
- ✅ External discovery is nice-to-have, not requirement
- ✅ Simpler implementation path (no external dependencies)
- ✅ Can add external discovery after MVP validation
- ✅ User feedback confirmed this approach

---

## Summary (Final Design)

### Core Flow (5 Phases)

1. ✅ **Inventory**: Check user's custom agents (`.claude/agents/`)
2. ✅ **Inventory**: Check template agents (template-specific)
3. ✅ **Inventory**: Check global agents (built-in)
4. ✅ **Generation**: AI creates needed agents (primary capability)
5. ⭐ **Discovery**: External agents optional (complementary, opt-in)

### Key Principles (Confirmed)

- ✅ **AI creates agents**, doesn't just discover (primary capability)
- ✅ **User's agents highest priority** (always preferred)
- ✅ **Smart deduplication** (auto-skip duplicates)
- ✅ **External discovery opt-in** (doesn't slow default flow)
- ✅ **User control on reuse** (ask before saving to .claude/agents/)

### Implementation (Approved)

**Phase 1 - MVP** (Include in EPIC-001):
- TASK-003: Multi-Source Agent Scanner (8h)
- TASK-004A: AI Agent Generator (8h)
- TASK-009: Agent Orchestration (6h)
- **Total**: 22 hours

**Phase 2 - Enhancement** (Post-EPIC-001):
- TASK-004B: External Agent Discovery (6h, optional)

### Benefits

✅ Leverages Claude Code's proven agent creation capability
✅ Fast (no network calls by default)
✅ Respects user's custom work
✅ Context-aware (project-specific)
✅ No external dependencies (Phase 1)
✅ Extensible (Phase 2 adds external discovery)

---

## Status

**Design**: ✅ APPROVED (2025-11-01)
**Decisions**: ✅ ALL CONFIRMED (4/4)
**Implementation**: 🚀 READY TO PROCEED

**Next Steps**:
1. ✅ Create TASK-003 specification (Multi-Source Scanner)
2. ✅ Create TASK-004A specification (AI Agent Generator)
3. ✅ Update TASK-009 specification (Orchestration)
4. ✅ Update EPIC-001 timeline with revised estimates
5. 🚀 Begin implementation (Phase 1 - MVP)
