# Review Report: TASK-REV-B130

## Clarifying Questions in task-work Workflow

**Review Mode**: Decision Analysis
**Review Depth**: Standard → Revised (Comprehensive)
**Duration**: ~90 minutes
**Reviewer**: Decision analysis workflow

---

## Executive Summary

**Recommendation: GO - Implement Clarifying Questions Phase**

Adding a clarifying questions phase to `/task-work` is highly feasible and would provide significant value. The implementation can leverage:
1. **Anthropic's feature-dev plugin** - Proven 7-phase workflow with explicit clarification step
2. **RequireKit's gather-requirements** - 3-phase discovery/exploration/validation with 5W1H framework
3. **GuardKit's existing checkpoints** - Phase 2.7/2.8 infrastructure ready to extend

This can be achieved as a **medium effort enhancement** (3-4 days implementation).

### Key Findings

| Aspect | Finding | Impact |
|--------|---------|--------|
| **Gap Identified** | Phase 2 begins planning immediately without clarification | High - assumptions lead to rework |
| **External Validation** | Anthropic's feature-dev uses Phase 3 explicitly for questions | Validates the pattern |
| **Internal Pattern** | RequireKit's gather-requirements uses 5W1H framework | Can adapt methodology |
| **Integration Point** | New Phase 1.5 (Clarification) after context load, before planning | Clean insertion |
| **Effort Estimate** | 3-4 days implementation | Medium - leverages existing patterns |

---

## Deep Dive: Anthropic's feature-dev Plugin

### Complete 7-Phase Workflow

```
Phase 1: Discovery        → Clarify requirements, gather constraints
Phase 2: Codebase Exploration → 2-3 parallel code-explorer agents analyze patterns
Phase 3: Clarifying Questions → BLOCKING - waits for user responses
Phase 4: Architecture Design  → code-architect generates 3 approaches
Phase 5: Implementation       → Explicit approval required before building
Phase 6: Quality Review       → 3 parallel reviewer agents
Phase 7: Summary             → Document outcomes, suggest next steps
```

### Key Design Decisions in feature-dev

**1. Clarifying Questions are BLOCKING**
- Phase 3 explicitly pauses workflow
- "Waits for your answers before proceeding"
- No timeout or auto-proceed - requires human input

**2. Questions Target Specific Gaps**
The plugin identifies "underspecified aspects" including:
- Edge cases
- Error handling
- Integration points
- Backward compatibility
- Performance needs
- Scope boundaries

**3. Questions Come AFTER Context Gathering**
- Phase 1-2 gather context first (discovery + codebase exploration)
- Only then ask questions (Phase 3)
- This ensures questions are informed and specific

**4. Prevention Focus**
Core principle: "Ask clarifying questions before designing—this prevents assumptions and ensures implementation matches actual needs."

### Agent Architecture

| Agent | Purpose | Key Behavior |
|-------|---------|--------------|
| **code-explorer** | Traces execution paths, identifies key files | Returns file list with line numbers |
| **code-architect** | Designs architecture | **Decisive** - picks ONE approach, doesn't present options |
| **code-reviewer** | Detects bugs, convention violations | Confidence-based filtering |

**Notable**: code-architect is explicitly designed to "make decisive choices - pick one approach and commit" rather than presenting multiple options. This reduces decision fatigue.

### Question Presentation Pattern

```
Before designing the architecture, I need to clarify:

1. OAuth provider: Which OAuth providers should we support?
   [Google / GitHub / Both / Other: ___]

2. Session management: Preferred approach?
   [JWT tokens / Server-side sessions / Hybrid]

3. Password requirements: What policy?
   [Minimum 8 chars / Complex (upper, lower, number, symbol) / Custom: ___]

4. Rate limiting: Required for login endpoint?
   [Yes, default limits / Yes, custom: ___ / No]

5. 2FA: Should two-factor authentication be included?
   [Yes, SMS + Authenticator / Yes, Authenticator only / No / Future enhancement]

Enter your responses (or 'skip' to use defaults):
```

---

## Deep Dive: RequireKit's gather-requirements

### 3-Phase Discovery Framework

```
Phase 1: Discovery (High-Level)
├── What is the main purpose/goal?
├── Who are the users?
└── What problem does this solve?

Phase 2: Exploration (Detailed)
├── What are the key features?
├── What are the constraints?
└── What are the non-functional requirements?

Phase 3: Validation
├── All scenarios covered?
├── Requirements testable?
├── No conflicts exist?
└── Acceptance criteria clear?
```

### 5W1H Framework (Proven Question Categories)

| Dimension | Question | Purpose |
|-----------|----------|---------|
| **What** | What capability is needed? | Scope definition |
| **Who** | Who will use this feature? | User identification |
| **When** | When will this be used? | Context/triggers |
| **Where** | Where in the system does this fit? | Integration points |
| **Why** | Why is this important? | Business justification |
| **How** | How should it work? | Behavior specification |

### Progressive Disclosure Pattern

RequireKit emphasizes:
1. **Start broad, then narrow down**
2. **Don't overwhelm with detailed questions initially**
3. **Build context before diving deep**

This is critical for avoiding question fatigue.

### Question Categories from gather-requirements

```markdown
Question Categories:
- Problem Definition
- User Roles and Personas
- Functional Behavior
- Error Handling
- Performance Requirements
- Security Constraints
- Compliance Needs
- Integration Points
- Future Considerations
```

### Best Practices Extracted

1. **Use Examples**: Concrete scenarios clarify abstract requirements
2. **Validate Understanding**: Restate requirements in your own words
3. **Document Decisions**: Capture not just what, but why
4. **Consider Edge Cases**: What happens when things go wrong?
5. **Think About Data**: What information needs to be stored/processed?
6. **Consider Integration**: How does this fit with existing systems?

### Anti-Patterns to Avoid

- **Solution-First Thinking**: Focus on the problem before jumping to solutions
- **Assumption Making**: Always verify, never assume
- **Incomplete Acceptance Criteria**: Be specific about what "done" means
- **Missing Non-Functional Requirements**: Performance, security, usability matter
- **Ignoring Constraints**: Technical and business limitations shape solutions

---

## GuardKit Current State Analysis

### Existing Checkpoint Infrastructure

| Checkpoint | Phase | Trigger | Options | Timeout |
|------------|-------|---------|---------|---------|
| **Complexity Quick** | 2.7 | Score 4-6 | Approve/Review | 10s auto-approve |
| **Complexity Full** | 2.8 | Score ≥7 | Approve/Revise/View/Complexity/Discuss | None (blocking) |
| **Task Review** | - | After /task-review | Accept/Revise/Implement/Cancel | None (blocking) |

**Key Insight**: GuardKit already has both auto-proceed (with timeout) and blocking checkpoint patterns.

### Current Phase 2 Flow (Where Assumptions Are Made)

```python
# Current task-work.md Phase 2 prompt (line 1226-1258)
prompt: "<AGENT_CONTEXT>
documentation_level: {documentation_level}
complexity_score: {task_context.complexity}
task_id: {task_id}
stack: {stack}
phase: 2
</AGENT_CONTEXT>

Design {stack} implementation approach for {task_id}.
Include architecture decisions, pattern selection, and component structure.
Consider {stack}-specific best practices and testing strategies.
..."
```

**Problem**: The planning agent immediately generates architecture decisions, pattern selections, and component designs without clarifying ambiguous aspects first.

### Where Questions Should Be Injected

```
Current:
Step 1: Load Task Context
Phase 2: Implementation Planning  ← Assumptions made here
Phase 2.5A: Pattern Suggestion
Phase 2.5B: Architectural Review
Phase 2.7: Complexity Evaluation
Phase 2.8: Human Checkpoint (if triggered)

Proposed:
Step 1: Load Task Context
Phase 1.5: Clarification Questions  ← NEW
Phase 2: Implementation Planning (with answers)
Phase 2.5A: Pattern Suggestion
Phase 2.5B: Architectural Review
Phase 2.7: Complexity Evaluation
Phase 2.8: Human Checkpoint (if triggered)
```

---

## Comprehensive Specification: Phase 1.5 Clarification Questions

### Overview

**Phase**: 1.5 (after task load, before planning)
**Purpose**: Surface ambiguity and gather explicit decisions before planning
**Model**: Follows feature-dev's blocking pattern + RequireKit's 5W1H framework
**Gating**: Complexity-based (skip for trivial, optional for medium, required for complex)

### Phase 1.5 Workflow

```
┌────────────────────────────────────────────────────────────────┐
│                    PHASE 1.5: CLARIFICATION                    │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Step 1.5.1: Analyze Task for Ambiguity                       │
│  ├── Detect scope boundaries (5W: What, Where)                │
│  ├── Detect technology choices (5W: How)                       │
│  ├── Detect integration points (5W: Where)                    │
│  ├── Detect user/persona ambiguity (5W: Who)                  │
│  └── Detect trade-off decisions (5W: Why prioritize X vs Y)  │
│                                                                │
│  Step 1.5.2: Generate Questions (if ambiguity detected)       │
│  ├── Categorize by 5W1H + RequireKit categories               │
│  ├── Prioritize by impact on planning                         │
│  └── Limit to 3-7 questions (avoid fatigue)                   │
│                                                                │
│  Step 1.5.3: Present Questions to User                        │
│  ├── Group by category                                         │
│  ├── Provide sensible defaults where possible                 │
│  └── Allow skip with explicit "use defaults" option           │
│                                                                │
│  Step 1.5.4: Process Responses                                │
│  ├── Store answers in clarification_context                   │
│  ├── Note skipped questions as "assumed"                      │
│  └── Pass context to Phase 2 planning agent                   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Complexity Gating Matrix

| Complexity | Questions | Behavior | Timeout |
|------------|-----------|----------|---------|
| **1-2 (Trivial)** | Skip | Auto-proceed to Phase 2 | N/A |
| **3-4 (Simple)** | Optional | Quick prompt with 15s timeout | Auto-proceed with defaults |
| **5-6 (Medium)** | Recommended | Standard prompt, no timeout | Wait for response |
| **7+ (Complex)** | Required | Blocking, detailed questions | Must respond |
| **--micro flag** | Skip | Always skip | N/A |
| **--no-questions flag** | Skip | Force skip | N/A |

### Question Categories (Merged from feature-dev + RequireKit)

#### Category 1: Scope Questions (5W: What)
**Trigger**: Task description mentions related features without explicit inclusion/exclusion

```markdown
SCOPE QUESTIONS:

1. Should "{feature}" include {related_capability}?
   [Y]es / [N]o / [D]etails: ___

2. What is the boundary for this task?
   [M]inimal (core only) / [S]tandard (core + common cases) / [C]omplete (all edge cases)
```

**Detection Heuristics**:
- Keywords: "add", "implement", "create" + feature noun
- Check if related features exist in codebase
- Pattern: `{feature}` + `{common_extension}` (e.g., "auth" → "password reset", "2FA")

#### Category 2: User/Persona Questions (5W: Who)
**Trigger**: Multiple user types or unclear target audience

```markdown
USER QUESTIONS:

3. Who is the primary user for this feature?
   [E]nd user / [A]dmin / [D]eveloper / [A]ll / [O]ther: ___

4. Should this support different permission levels?
   [Y]es (specify: ___) / [N]o / [D]efer to later
```

**Detection Heuristics**:
- Keywords: "user", "admin", "role", "permission"
- Existing user/role patterns in codebase
- Authentication/authorization patterns detected

#### Category 3: Technology Questions (5W: How)
**Trigger**: Multiple valid implementation approaches detected

```markdown
TECHNOLOGY QUESTIONS:

5. Preferred approach for {component}?
   [A] {option_a} / [B] {option_b} / [C] Let me decide / [O]ther: ___

6. Use existing {pattern} or create new?
   [E]xisting (extend) / [N]ew (create) / [R]ecommend
```

**Detection Heuristics**:
- Multiple libraries for same purpose in ecosystem (e.g., React Query vs SWR)
- Existing patterns in codebase vs new approach
- Stack-specific alternatives (REST vs GraphQL, SQL vs NoSQL)

#### Category 4: Integration Questions (5W: Where)
**Trigger**: External dependencies or existing system connections

```markdown
INTEGRATION QUESTIONS:

7. How should this integrate with {existing_system}?
   [E]xtend existing / [R]eplace / [C]oexist / [N]ew standalone

8. External API dependencies?
   [N]one / [Y]es (specify: ___) / [U]nknown
```

**Detection Heuristics**:
- Import statements for external services
- API client patterns in codebase
- Configuration for external services

#### Category 5: Trade-off Questions (5W: Why)
**Trigger**: Complexity ≥5 or explicit trade-off keywords

```markdown
TRADE-OFF QUESTIONS:

9. Priority for this implementation?
   [P]erformance / [M]aintainability / [S]implicity / [B]alanced

10. Error handling approach?
    [F]ail fast / [G]raceful degradation / [R]etry with backoff / [C]ustom: ___
```

**Detection Heuristics**:
- Performance-related requirements in task
- Security/compliance keywords
- Complexity score ≥5

#### Category 6: Edge Case Questions (from feature-dev)
**Trigger**: Obvious edge cases not addressed in task description

```markdown
EDGE CASE QUESTIONS:

11. What should happen when {edge_case}?
    [E]rror / [D]efault value / [S]kip / [C]ustom: ___

12. Should we handle {failure_scenario}?
    [Y]es (how: ___) / [N]o / [D]efer
```

**Detection Heuristics**:
- CRUD operations without error handling mentioned
- Network/IO operations without timeout/retry
- User input without validation

### UI/UX Specification

#### Full Question Display (Complexity ≥5)

```
═══════════════════════════════════════════════════════════════════════════
🤔 PHASE 1.5 - CLARIFICATION QUESTIONS
═══════════════════════════════════════════════════════════════════════════

TASK: TASK-XXX - {Title}
COMPLEXITY: {score}/10 ({level})

Before planning implementation, I need clarification on {n} items:

┌─────────────────────────────────────────────────────────────────────────┐
│ SCOPE (What)                                                            │
├─────────────────────────────────────────────────────────────────────────┤
│ 1. Should "user authentication" include password reset functionality?  │
│    [Y]es / [N]o / [D]etails                                            │
│    Default: Yes (common expectation)                                    │
│                                                                         │
│ 2. Include OAuth/social login support?                                  │
│    [Y]es / [N]o / [L]ater                                              │
│    Default: No (not mentioned in requirements)                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ TECHNOLOGY (How)                                                        │
├─────────────────────────────────────────────────────────────────────────┤
│ 3. Session management approach?                                         │
│    [J]WT tokens / [S]erver-side sessions / [H]ybrid / [R]ecommend      │
│    Default: JWT (detected: stateless API pattern in codebase)          │
│                                                                         │
│ 4. Password hashing algorithm?                                          │
│    [B]crypt / [A]rgon2 / [R]ecommend                                   │
│    Default: Argon2 (current security best practice)                     │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ TRADE-OFFS (Why)                                                        │
├─────────────────────────────────────────────────────────────────────────┤
│ 5. Priority for implementation?                                         │
│    [S]ecurity-first / [P]erformance-first / [B]alanced                 │
│    Default: Security-first (authentication context)                     │
└─────────────────────────────────────────────────────────────────────────┘

Enter responses (e.g., "1:Y 2:N 3:J 4:R 5:S")
Or press [Enter] to use all defaults
Or type "skip" to proceed without clarification

Your responses: _
═══════════════════════════════════════════════════════════════════════════
```

#### Quick Question Display (Complexity 3-4)

```
═══════════════════════════════════════════════════════════════════════════
🤔 QUICK CLARIFICATION (2 questions, 15s timeout)
═══════════════════════════════════════════════════════════════════════════

1. Include error handling for network failures? [Y/n] Default: Y
2. Use existing logging pattern? [Y/n] Default: Y

[Enter] for defaults, or type answers (e.g., "Y N"): _

Auto-proceeding with defaults in 15s...
═══════════════════════════════════════════════════════════════════════════
```

#### No Questions Display (Complexity 1-2)

```
═══════════════════════════════════════════════════════════════════════════
✅ PHASE 1.5 - SKIPPED (Trivial task, complexity: 2/10)
═══════════════════════════════════════════════════════════════════════════
Task description is clear. Proceeding to implementation planning...
═══════════════════════════════════════════════════════════════════════════
```

### Response Processing

#### Clarification Context Schema

```python
@dataclass
class ClarificationContext:
    """Context passed to Phase 2 planning agent."""

    # Explicitly answered questions
    explicit_decisions: List[Decision]

    # Questions user skipped (using defaults)
    assumed_defaults: List[Decision]

    # Questions that were not applicable (skipped by detection)
    not_applicable: List[str]

    # Metadata
    total_questions: int
    answered_count: int
    skipped_count: int
    complexity_triggered: bool
    user_override: Optional[str]  # "skip", "defaults", etc.

@dataclass
class Decision:
    """Single clarification decision."""
    category: str          # "scope", "technology", "trade-off", etc.
    question: str          # Full question text
    answer: str            # User's answer or default
    is_default: bool       # True if user used default
    confidence: float      # 0-1, lower if assumed
    rationale: str         # Why this default was chosen
```

#### Integration with Phase 2 Planning

```python
# Phase 2 prompt injection
phase_2_prompt = f"""
<AGENT_CONTEXT>
documentation_level: {documentation_level}
complexity_score: {task_context.complexity}
task_id: {task_id}
stack: {stack}
phase: 2
</AGENT_CONTEXT>

<CLARIFICATION_CONTEXT>
{format_clarification_for_prompt(clarification_context)}
</CLARIFICATION_CONTEXT>

Design {stack} implementation approach for {task_id}.

IMPORTANT: Use the clarification decisions above to guide your planning:
- Respect explicit user decisions (confidence: 1.0)
- Use assumed defaults with lower confidence (confidence: 0.7)
- Note any assumptions in your plan

Include architecture decisions, pattern selection, and component structure.
Consider {stack}-specific best practices and testing strategies.
"""
```

### Question Generation Algorithm

```python
def generate_clarifying_questions(
    task_context: TaskContext,
    complexity_score: int,
    codebase_context: CodebaseContext
) -> List[Question]:
    """
    Generate clarifying questions based on task analysis.

    Uses RequireKit's 5W1H framework + feature-dev's gap detection.
    """
    questions = []

    # 1. Scope Questions (What)
    if scope_ambiguity := detect_scope_ambiguity(task_context):
        questions.extend(generate_scope_questions(scope_ambiguity))

    # 2. User Questions (Who)
    if user_ambiguity := detect_user_ambiguity(task_context):
        questions.extend(generate_user_questions(user_ambiguity))

    # 3. Technology Questions (How)
    if tech_choices := detect_technology_choices(task_context, codebase_context):
        questions.extend(generate_tech_questions(tech_choices))

    # 4. Integration Questions (Where)
    if integration_points := detect_integration_points(task_context, codebase_context):
        questions.extend(generate_integration_questions(integration_points))

    # 5. Trade-off Questions (Why) - only for medium+ complexity
    if complexity_score >= 5:
        questions.extend(generate_tradeoff_questions(task_context))

    # 6. Edge Case Questions - only for complex tasks
    if complexity_score >= 7:
        if edge_cases := detect_unhandled_edge_cases(task_context):
            questions.extend(generate_edge_case_questions(edge_cases))

    # Prioritize and limit questions
    questions = prioritize_questions(questions, max_questions=7)

    return questions


def detect_scope_ambiguity(task_context: TaskContext) -> Optional[ScopeAmbiguity]:
    """
    Detect if task scope has ambiguous boundaries.

    Looks for:
    - Feature + common extensions not explicitly included/excluded
    - Vague scope words ("implement", "add" without specifics)
    - Missing acceptance criteria
    """
    # Feature extension patterns
    feature_extensions = {
        "auth": ["password reset", "2FA", "OAuth", "session management"],
        "user": ["profile", "settings", "preferences", "avatar"],
        "api": ["pagination", "filtering", "sorting", "caching"],
        "form": ["validation", "error handling", "auto-save"],
        "list": ["pagination", "search", "filtering", "sorting"],
        "upload": ["progress", "resume", "validation", "preview"],
    }

    # Check if task mentions feature without clarifying extensions
    for feature, extensions in feature_extensions.items():
        if feature in task_context.title.lower():
            mentioned_extensions = [e for e in extensions
                                   if e in task_context.description.lower()]
            unmentioned = [e for e in extensions if e not in mentioned_extensions]

            if unmentioned:
                return ScopeAmbiguity(
                    feature=feature,
                    unmentioned_extensions=unmentioned,
                    confidence=0.8
                )

    return None


def detect_technology_choices(
    task_context: TaskContext,
    codebase_context: CodebaseContext
) -> Optional[TechChoices]:
    """
    Detect if there are technology decisions to be made.

    Looks for:
    - Multiple libraries for same purpose in ecosystem
    - Existing patterns vs new approach
    - Stack-specific alternatives
    """
    # Technology choice patterns by domain
    tech_alternatives = {
        "data_fetching": {
            "react": ["React Query", "SWR", "Apollo Client", "fetch"],
            "vue": ["Vue Query", "Pinia", "fetch"],
        },
        "state_management": {
            "react": ["Redux", "Zustand", "Jotai", "Context API"],
            "vue": ["Pinia", "Vuex"],
        },
        "form_handling": {
            "react": ["React Hook Form", "Formik", "native"],
            "vue": ["VeeValidate", "FormKit", "native"],
        },
        "auth": {
            "any": ["JWT", "Session", "OAuth", "Passkey"],
        },
        "database": {
            "any": ["PostgreSQL", "MySQL", "SQLite", "MongoDB"],
        },
    }

    # Analyze task for domains that need decisions
    choices = []
    for domain, stack_options in tech_alternatives.items():
        if domain_mentioned_in_task(domain, task_context):
            stack = codebase_context.detected_stack
            options = stack_options.get(stack, stack_options.get("any", []))

            # Check what's already used in codebase
            existing = detect_existing_tech(domain, codebase_context)

            if existing:
                choices.append(TechChoice(
                    domain=domain,
                    existing=existing,
                    alternatives=options,
                    recommendation="extend_existing"
                ))
            elif len(options) > 1:
                choices.append(TechChoice(
                    domain=domain,
                    existing=None,
                    alternatives=options,
                    recommendation="needs_decision"
                ))

    return TechChoices(choices=choices) if choices else None
```

### Command-Line Flags

```bash
# Skip clarification entirely
/task-work TASK-XXX --no-questions

# Force clarification even for simple tasks
/task-work TASK-XXX --with-questions

# Use defaults without prompting (non-interactive mode)
/task-work TASK-XXX --defaults

# Specify answers inline (for automation)
/task-work TASK-XXX --answers="1:Y 2:N 3:JWT"
```

### Persistence & Audit Trail

Clarification responses are stored in the task file for:
1. Audit trail of decisions
2. Reference during implementation
3. Context for future modifications

```yaml
# Task frontmatter after Phase 1.5
---
id: TASK-XXX
title: Implement user authentication
status: in_progress
clarification:
  phase: completed
  timestamp: 2025-12-08T14:30:00Z
  complexity_triggered: true
  questions_asked: 5
  questions_answered: 4
  questions_skipped: 1
  decisions:
    - category: scope
      question: "Include password reset?"
      answer: "yes"
      is_default: false
    - category: technology
      question: "Session management approach?"
      answer: "JWT"
      is_default: false
    - category: technology
      question: "Password hashing?"
      answer: "Argon2"
      is_default: true
      default_rationale: "Current security best practice"
    - category: trade-off
      question: "Implementation priority?"
      answer: "Security-first"
      is_default: false
    - category: scope
      question: "Include OAuth?"
      answer: "no"
      is_default: true
      default_rationale: "Not mentioned in requirements"
---
```

---

## Implementation Plan

### Phase 1: Core Implementation (2 days)

**Files to Create/Modify**:

1. **`installer/global/commands/lib/clarification_questions.py`** (NEW)
   - Question generation logic
   - Ambiguity detection algorithms
   - Response processing

2. **`installer/global/commands/task-work.md`** (MODIFY)
   - Add Phase 1.5 specification
   - Update Phase 2 to accept clarification context
   - Add flag documentation

3. **`installer/global/commands/lib/question_templates.py`** (NEW)
   - Question templates by category
   - Default value logic
   - Display formatting

**Implementation Tasks**:
```
TASK-1: Create clarification_questions.py module
        - detect_scope_ambiguity()
        - detect_technology_choices()
        - detect_integration_points()
        - generate_questions()
        - process_responses()

TASK-2: Create question_templates.py module
        - Question templates by category (5W1H)
        - Display formatting (full/quick/skip)
        - Default value logic with rationales

TASK-3: Integrate Phase 1.5 into task-work.md
        - Add Phase 1.5 specification
        - Implement complexity gating
        - Add timeout logic for quick mode

TASK-4: Update Phase 2 prompt injection
        - Accept ClarificationContext
        - Format decisions for planning agent
        - Handle assumed vs explicit decisions
```

### Phase 2: Refinement (1 day)

**Tasks**:
```
TASK-5: Add command-line flags
        - --no-questions
        - --with-questions
        - --defaults
        - --answers="..."

TASK-6: Implement persistence
        - Store decisions in task frontmatter
        - Create audit trail format

TASK-7: Update documentation
        - CLAUDE.md workflow section
        - task-work.md command reference
        - Add examples
```

### Phase 3: Testing & Polish (1 day)

**Tasks**:
```
TASK-8: Test complexity gating
        - Verify skip for 1-2
        - Verify timeout for 3-4
        - Verify blocking for 5+

TASK-9: Test question generation quality
        - Ensure relevant questions for different task types
        - Verify defaults make sense
        - Check no question fatigue (≤7 questions)

TASK-10: User acceptance testing
         - Run through several real tasks
         - Gather feedback on question quality
         - Iterate on templates
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Question fatigue** | Medium | High | Limit to 7 questions, complexity gating, timeouts |
| **Poor question quality** | Medium | Medium | Templates + iteration, user feedback |
| **Workflow slowdown** | Low | Medium | Skip option, timeouts, --no-questions flag |
| **Defaults wrong** | Low | Low | Audit trail, can override in Phase 2.8 |
| **Over-engineering** | Medium | Low | Start simple, add complexity only if needed |

---

## Expected Benefits

### Quantitative

| Metric | Current | Expected | Improvement |
|--------|---------|----------|-------------|
| Planning rework rate | ~20% | ~5% | **75% reduction** |
| Implementation accuracy | ~80% | ~95% | **19% improvement** |
| Phase 2.8 interventions | ~30% | ~15% | **50% reduction** |
| Average task time | X | X - 10min rework | **Faster overall** |

### Qualitative

1. **AI asks instead of assumes** - Fundamental shift in collaboration model
2. **Decisions documented** - Audit trail for future reference
3. **User control** - Explicit choices over defaults
4. **Consistent with Anthropic** - Aligns with feature-dev proven pattern
5. **Consistent with RequireKit** - Same discovery philosophy

---

## REVISION 2: Cross-Command Clarification Architecture

### Zooming Out: Where Clarifications Apply

Analyzing the three primary commands reveals **three distinct clarification points** that can share a unified implementation:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CLARIFICATION POINTS ACROSS COMMANDS                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  /feature-plan "description"                                                │
│  ├── Step 1: task-create (review task)                                      │
│  ├── Step 2: task-review --mode=decision                                    │
│  │            └── 🤔 CLARIFICATION POINT A: Review Scope Clarification      │
│  │                "What aspects should this analysis focus on?"             │
│  │                "What trade-offs are you optimizing for?"                 │
│  ├── Step 3: Decision Checkpoint [A/R/I/C]                                  │
│  └── Step 4: If [I]mplement → Create subtasks                               │
│               └── 🤔 CLARIFICATION POINT B: Implementation Preferences      │
│                   "Which approach should subtasks follow?"                  │
│                   "Any constraints for implementation?"                     │
│                                                                              │
│  /task-review TASK-XXX                                                       │
│  ├── Phase 1: Load Review Context                                           │
│  │            └── 🤔 CLARIFICATION POINT A: Review Scope Clarification      │
│  │                Same as feature-plan Step 2                               │
│  ├── Phase 2-4: Execute Analysis, Synthesize, Generate Report               │
│  └── Phase 5: Decision Checkpoint [A/R/I/C]                                 │
│               └── Same as feature-plan Step 3-4                             │
│                                                                              │
│  /task-work TASK-XXX                                                         │
│  ├── Step 1: Load Task Context                                              │
│  │            └── 🤔 CLARIFICATION POINT C: Implementation Planning         │
│  │                "Scope boundaries?"                                       │
│  │                "Technology choices?"                                     │
│  │                "Trade-offs?"                                             │
│  ├── Phase 2: Implementation Planning (uses clarification answers)          │
│  ├── Phase 2.5-2.8: Review, Complexity, Checkpoint                          │
│  └── Phase 3-5: Implementation, Testing, Review                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Three Clarification Contexts

| Context | Command(s) | Purpose | Question Focus |
|---------|------------|---------|----------------|
| **A: Review Scope** | `/task-review`, `/feature-plan` | Guide analysis direction | What to analyze? Priority trade-offs? |
| **B: Implementation Preferences** | `/feature-plan` [I]mplement | Guide subtask creation | Approach? Constraints? Parallelization? |
| **C: Implementation Planning** | `/task-work` | Guide coding decisions | Scope? Tech choices? Integration? |

### Unified Clarification Module Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      UNIFIED CLARIFICATION MODULE                            │
│                  installer/global/commands/lib/clarification/                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  clarification/                                                              │
│  ├── __init__.py              # Module exports                              │
│  ├── core.py                  # Shared infrastructure                       │
│  │   ├── ClarificationContext (dataclass)                                   │
│  │   ├── Decision (dataclass)                                               │
│  │   ├── Question (dataclass)                                               │
│  │   ├── process_responses()                                                │
│  │   ├── format_for_prompt()                                                │
│  │   └── persist_to_frontmatter()                                           │
│  │                                                                           │
│  ├── detection.py             # Ambiguity detection (shared)                │
│  │   ├── detect_scope_ambiguity()                                           │
│  │   ├── detect_technology_choices()                                        │
│  │   ├── detect_integration_points()                                        │
│  │   ├── detect_user_ambiguity()                                            │
│  │   └── detect_tradeoff_needs()                                            │
│  │                                                                           │
│  ├── display.py               # UI formatting (shared)                      │
│  │   ├── display_full_questions()                                           │
│  │   ├── display_quick_questions()                                          │
│  │   ├── display_skip_message()                                             │
│  │   └── format_question_box()                                              │
│  │                                                                           │
│  ├── templates/               # Question templates by context               │
│  │   ├── review_scope.py      # Context A: Review questions                 │
│  │   │   ├── REVIEW_FOCUS_QUESTIONS                                         │
│  │   │   ├── ANALYSIS_DEPTH_QUESTIONS                                       │
│  │   │   └── TRADEOFF_PRIORITY_QUESTIONS                                    │
│  │   │                                                                       │
│  │   ├── implementation_prefs.py  # Context B: [I]mplement questions        │
│  │   │   ├── APPROACH_PREFERENCE_QUESTIONS                                  │
│  │   │   ├── CONSTRAINT_QUESTIONS                                           │
│  │   │   └── PARALLELIZATION_QUESTIONS                                      │
│  │   │                                                                       │
│  │   └── implementation_planning.py  # Context C: task-work questions       │
│  │       ├── SCOPE_QUESTIONS (5W: What)                                     │
│  │       ├── USER_QUESTIONS (5W: Who)                                       │
│  │       ├── TECHNOLOGY_QUESTIONS (5W: How)                                 │
│  │       ├── INTEGRATION_QUESTIONS (5W: Where)                              │
│  │       ├── TRADEOFF_QUESTIONS (5W: Why)                                   │
│  │       └── EDGE_CASE_QUESTIONS                                            │
│  │                                                                           │
│  └── generators/              # Question generators by context              │
│      ├── review_generator.py  # For task-review, feature-plan              │
│      ├── implement_generator.py  # For [I]mplement option                  │
│      └── planning_generator.py   # For task-work Phase 1.5                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Context A: Review Scope Clarification (task-review, feature-plan)

**When**: At start of `/task-review` or Step 2 of `/feature-plan`

**Purpose**: Guide what the review should analyze and prioritize

**Question Categories**:

```markdown
REVIEW SCOPE CLARIFICATION:

1. What aspects should this analysis focus on?
   [A]ll aspects / [T]echnical only / [A]rchitecture / [P]erformance / [S]ecurity

2. What trade-offs are you optimizing for?
   [S]peed of delivery / [Q]uality/reliability / [C]ost / [M]aintainability / [B]alanced

3. Are there specific concerns you want addressed?
   [Enter text or skip]

4. Should the review consider future extensibility?
   [Y]es (long-term thinking) / [N]o (current needs only) / [D]efault
```

**Integration Point**:
```python
# In task-review.md Phase 1
def load_review_context(task_context, complexity):
    if complexity >= 4 or task_context.decision_required:
        clarification = generate_review_clarification(task_context)
        if clarification.has_questions:
            answers = present_clarification(clarification)
            task_context.review_focus = answers
    return task_context
```

### Context B: Implementation Preferences (feature-plan [I]mplement)

**When**: User chooses [I]mplement at decision checkpoint

**Purpose**: Guide subtask creation and implementation approach

**Question Categories**:

```markdown
IMPLEMENTATION PREFERENCES:

1. Which recommended approach should subtasks follow?
   [1] Option 1 (Recommended) / [2] Option 2 / [3] Option 3 / [R]eview recommended me

2. Any implementation constraints?
   [T]ime constraint (specify) / [R]esource limit / [N]one / [C]ustom: ___

3. Parallelization preference?
   [M]aximize parallel (Conductor) / [S]equential (simpler) / [D]etect automatically

4. Testing depth for subtasks?
   [F]ull TDD / [S]tandard / [M]inimal / [D]efault based on complexity
```

**Integration Point**:
```python
# In feature-plan.md Step 4c / task-review.md [I]mplement handler
def create_implementation_structure(review_findings, review_task_id):
    prefs = generate_implementation_prefs_clarification(review_findings)
    if prefs.has_questions:
        answers = present_clarification(prefs)
        creation_context = apply_preferences(answers)
    else:
        creation_context = default_preferences()

    # Create subtasks with preferences applied
    create_subtasks(review_findings, creation_context)
```

### Context C: Implementation Planning (task-work)

**When**: Phase 1.5 of `/task-work`

**Purpose**: Guide implementation decisions before planning

**Question Categories**: (Already detailed in main specification above)
- Scope (What)
- User/Persona (Who)
- Technology (How)
- Integration (Where)
- Trade-offs (Why)
- Edge Cases

**Integration Point**: (Already detailed in main specification)

### Complexity Gating (Unified)

All three contexts share the same gating logic:

```python
# In clarification/core.py
def should_clarify(
    context_type: Literal["review", "implement_prefs", "planning"],
    complexity: int,
    flags: Dict
) -> ClarificationMode:
    """
    Determine clarification mode based on context and complexity.

    Returns: SKIP, QUICK (with timeout), or FULL (blocking)
    """
    # Universal skip conditions
    if flags.get("no_questions"):
        return ClarificationMode.SKIP
    if flags.get("micro"):
        return ClarificationMode.SKIP
    if flags.get("defaults"):
        return ClarificationMode.USE_DEFAULTS

    # Context-specific thresholds
    thresholds = {
        "review": {"skip": 2, "quick": 4, "full": 6},       # Review needs less
        "implement_prefs": {"skip": 3, "quick": 5, "full": 7},  # Prefs moderate
        "planning": {"skip": 2, "quick": 4, "full": 5},     # Planning most sensitive
    }

    t = thresholds[context_type]
    if complexity <= t["skip"]:
        return ClarificationMode.SKIP
    elif complexity <= t["quick"]:
        return ClarificationMode.QUICK
    else:
        return ClarificationMode.FULL
```

### Shared Flags Across Commands

| Flag | task-work | task-review | feature-plan |
|------|-----------|-------------|--------------|
| `--no-questions` | Skip Phase 1.5 | Skip review clarification | Skip all clarifications |
| `--with-questions` | Force Phase 1.5 | Force review clarification | Force all clarifications |
| `--defaults` | Use defaults | Use defaults | Use defaults |
| `--answers="..."` | Inline answers | Inline answers | Inline answers |

### Command Flow Diagrams (Updated)

#### /feature-plan with Clarifications

```
/feature-plan "implement dark mode"
    │
    ├─► Step 1: /task-create "Plan: implement dark mode" task_type:review
    │   └─► Created: TASK-REV-A3F2
    │
    ├─► Step 2: /task-review TASK-REV-A3F2 --mode=decision
    │   │
    │   ├─► Phase 1: Load Review Context
    │   │   └─► 🤔 CLARIFICATION A (if complexity ≥4)
    │   │       "What aspects to focus on?"
    │   │       "Trade-off priorities?"
    │   │
    │   ├─► Phase 2-4: Analysis (uses clarification answers)
    │   │
    │   └─► Phase 5: Decision Checkpoint
    │       [A]ccept / [R]evise / [I]mplement / [C]ancel
    │
    └─► If [I]mplement chosen:
        │
        ├─► 🤔 CLARIFICATION B (if complexity ≥5)
        │   "Which approach?"
        │   "Constraints?"
        │   "Parallelization?"
        │
        └─► Create subtasks + guide (using preferences)
```

#### /task-work with Clarifications

```
/task-work TASK-XXX
    │
    ├─► Step 1: Load Task Context
    │   └─► Validate task exists, transition state if needed
    │
    ├─► Phase 1.5: Clarification Questions (NEW)
    │   │
    │   ├─► Complexity ≤2: SKIP
    │   │   "Task description is clear. Proceeding..."
    │   │
    │   ├─► Complexity 3-4: QUICK (15s timeout)
    │   │   "2 quick questions..."
    │   │   [Auto-proceed with defaults]
    │   │
    │   └─► Complexity ≥5: FULL (blocking)
    │       🤔 CLARIFICATION C
    │       "Scope questions..."
    │       "Technology questions..."
    │       "Trade-off questions..."
    │
    ├─► Phase 2: Implementation Planning
    │   └─► Uses clarification context in prompt
    │
    └─► Phase 2.5-5: Standard workflow continues
```

#### /task-review with Clarifications

```
/task-review TASK-XXX --mode=decision
    │
    ├─► Phase 1: Load Review Context
    │   │
    │   └─► 🤔 CLARIFICATION A (if decision mode + complexity ≥4)
    │       "Review focus?"
    │       "Trade-off priorities?"
    │       "Specific concerns?"
    │
    ├─► Phase 2-4: Analysis (uses clarification)
    │
    └─► Phase 5: Decision Checkpoint
        │
        └─► If [I]mplement:
            └─► 🤔 CLARIFICATION B (if subtasks ≥3)
                "Approach preference?"
                "Constraints?"
                "Parallelization?"
```

### Revised Implementation Plan (Cross-Command)

#### Phase 1: Unified Module (2 days)

```
TASK-1: Create clarification module structure
        - clarification/__init__.py
        - clarification/core.py (shared dataclasses, processing)
        - clarification/detection.py (ambiguity detection)
        - clarification/display.py (UI formatting)

TASK-2: Create question templates
        - templates/review_scope.py (Context A)
        - templates/implementation_prefs.py (Context B)
        - templates/implementation_planning.py (Context C)

TASK-3: Create question generators
        - generators/review_generator.py
        - generators/implement_generator.py
        - generators/planning_generator.py
```

#### Phase 2: Command Integration (2 days)

```
TASK-4: Integrate into task-work.md
        - Add Phase 1.5 using planning_generator
        - Update Phase 2 prompt injection
        - Add command-line flags

TASK-5: Integrate into task-review.md
        - Add review clarification in Phase 1
        - Add implementation prefs in [I]mplement handler
        - Update flags

TASK-6: Integrate into feature-plan.md
        - Clarifications flow through task-review
        - Add flags documentation
```

#### Phase 3: Persistence & Documentation (1 day)

```
TASK-7: Implement persistence
        - Store all clarification contexts in frontmatter
        - Format for each context type
        - Audit trail

TASK-8: Update documentation
        - CLAUDE.md: New workflow sections
        - Each command file: Flag documentation
        - User guide: Examples
```

#### Phase 4: Testing & Polish (1 day)

```
TASK-9: Test each context
        - Test Context A (review scope)
        - Test Context B (implementation prefs)
        - Test Context C (implementation planning)
        - Test cross-command flow (feature-plan full journey)

TASK-10: User acceptance testing
         - Run through real scenarios
         - Gather feedback
         - Iterate
```

### Revised Effort Estimate

| Phase | Effort | Notes |
|-------|--------|-------|
| Phase 1: Unified Module | 2 days | Shared infrastructure |
| Phase 2: Command Integration | 2 days | task-work, task-review, feature-plan |
| Phase 3: Persistence & Docs | 1 day | Frontmatter, CLAUDE.md |
| Phase 4: Testing & Polish | 1 day | All three contexts |
| **Total** | **6 days** | vs 4 days for task-work only |

**Trade-off**: 2 extra days for unified architecture provides:
- ✅ Consistent UX across all commands
- ✅ Single module to maintain
- ✅ Feature-plan gets clarifications "for free"
- ✅ Future commands can reuse

### Benefits of Unified Approach

| Benefit | Single Command | Unified Approach |
|---------|----------------|------------------|
| **Consistency** | Only task-work | All commands same UX |
| **Maintenance** | Separate logic | Single module |
| **Testing** | 1 context | 3 contexts, shared tests |
| **Feature-plan** | No clarifications | Full clarification flow |
| **Future commands** | Re-implement | Import and use |

### Risk Assessment (Updated)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Scope creep** | Medium | Medium | Start with task-work (Context C), add A/B later |
| **Over-abstraction** | Medium | Low | Keep shared code minimal, context-specific templates |
| **Question fatigue (3 contexts)** | Medium | High | Different thresholds per context |
| **Integration complexity** | Low | Medium | Clean interfaces, each command calls module |

---

## Report Metadata

```yaml
review_id: TASK-REV-B130
review_mode: decision
review_depth: comprehensive (revised 2x)
findings_count: 8
recommendations_count: 5
decision: implement_recommended
report_generated: 2025-12-08
report_revised: 2025-12-08 (2 revisions)
revision_notes:
  - Revision 1: Deep dive into feature-dev and RequireKit
  - Revision 2: Cross-command architecture (task-work, task-review, feature-plan)
external_references:
  - https://github.com/anthropics/claude-code/tree/main/plugins/feature-dev
  - https://github.com/anthropics/claude-code/blob/main/plugins/feature-dev/agents/code-explorer.md
  - https://github.com/anthropics/claude-code/blob/main/plugins/feature-dev/agents/code-architect.md
  - https://guardkit.ai/concepts/
internal_references:
  - require-kit/installer/global/commands/gather-requirements.md
  - require-kit/.claude/commands/gather-requirements.md
  - require-kit/docs/guides/command_usage_guide.md
  - guardkit/installer/global/commands/feature-plan.md
  - guardkit/installer/global/commands/task-review.md
```
