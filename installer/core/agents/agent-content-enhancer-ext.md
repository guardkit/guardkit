# agent-content-enhancer - Extended Reference

This file contains detailed documentation for the `agent-content-enhancer` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/agent-content-enhancer-ext.md
```


## GitHub Best Practices (Industry Standards)

### Evidence Base
Based on analysis of 2,500+ repositories (GitHub Research, 2024).
**Full analysis**: [docs/analysis/github-agent-best-practices-analysis.md](../../../docs/analysis/github-agent-best-practices-analysis.md)

**IMPORTANT**: This agent MUST generate content conforming to all GitHub best practices, especially:
- **Boundary Sections** (Critical Gap #4 in analysis) - ALWAYS/NEVER/ASK framework required
- **Early Command Placement** (Critical Gap #2) - Commands in first 50 lines
- **Code Examples First** (Critical Gap #3) - Examples before line 50, 40-50% density target

### Quality Thresholds (Automated Enforcement)

When enhancing agents, the following standards MUST be met:

#### 1. Time to First Example (CRITICAL)
- **Target**: <50 lines from file start
- **Current GuardKit Average**: 150-280 lines
- **Enforcement**: REQUIRED (FAIL if exceeded)
- **Calculation**: Count lines from YAML frontmatter end to first ```code block

**Why**: Users abandon agents if they can't find examples quickly. GitHub data shows 80% of users only read first 50 lines.

#### 2. Example Density (CRITICAL)
- **Target**: 40-50% of content should be executable code examples
- **Current GuardKit Average**: 20-30%
- **Enforcement**: REQUIRED (FAIL if <30%, WARN if <40%)
- **Calculation**: (Lines inside ```code blocks / Total lines excluding frontmatter) × 100
- **Format Preference**: ✅ DO / ❌ DON'T comparison style

**Why**: "One real code snippet beats three paragraphs describing it" (GitHub Research)

#### 3. Boundary Sections (REQUIRED)
**Enforcement**: REQUIRED by JSON schema - all responses MUST include `boundaries` field

**How to Derive Boundaries from Templates**:
1. **ALWAYS rules**: Extract patterns that appear consistently across templates (e.g., validation, error handling, async/await)
2. **NEVER rules**: Identify anti-patterns or violations found in template comments/docs (e.g., "never use sync I/O")
3. **ASK scenarios**: Find configuration decisions or tradeoffs mentioned in templates (e.g., cache strategy, pagination size)

**Structural Requirements** (enforced by schema):
- ALWAYS: 5-7 rules with ✅ emoji prefix
- NEVER: 5-7 rules with ❌ emoji prefix
- ASK: 3-5 scenarios with ⚠️ emoji prefix
- Format: "[emoji] [action] ([brief rationale])"
- Minimum 500 characters total
- See JSON schema in prompt for full validation rules

🚨 **EMOJI PREFIXES ARE MANDATORY** (TASK-FIX-PD07):
Every boundary rule MUST include the correct emoji prefix in exactly this format:
- ALWAYS: `- ✅ ` (dash, space, checkmark emoji, space, then action text)
- NEVER: `- ❌ ` (dash, space, cross emoji, space, then action text)
- ASK: `- ⚠️ ` (dash, space, warning emoji, space, then scenario text)

Rules WITHOUT emoji prefixes will FAIL validation and trigger regeneration.
This was identified as a common issue in TASK-REV-TC03 review.

**Why**: Explicit boundaries prevent costly mistakes and reduce human intervention by 40%.

#### 4. Specificity Score (MAINTAINED)
- **Target**: ≥8/10 (GuardKit already strong at 8.5/10)
- **Bad**: "Helpful assistant for code quality"
- **Good**: "Code review specialist for React components with TypeScript"
- **Enforcement**: REQUIRED (FAIL if <8/10)
- **Measurement**: Check role statement against rubric:
  - 10/10: Mentions tech stack + domain + standards (e.g., "React 18 + TypeScript 5.x performance optimizer using Core Web Vitals metrics")
  - 8/10: Mentions tech stack + domain (e.g., "React TypeScript code reviewer")
  - 6/10: Mentions tech stack only (e.g., "React helper")
  - 4/10: Generic (e.g., "Web development assistant")

**Why**: Specific roles set clear expectations and improve task completion by 60%.

#### 5. Commands-First Structure (CRITICAL)
- **Target**: Working command example in first 50 lines
- **Format**: Full command with flags/options + expected output
- **Enforcement**: REQUIRED (FAIL if >50 lines)

**Example**:
```markdown

## Quick Start

### Basic Usage
```bash
/agent-enhance my-template/my-agent --strategy=hybrid
```

### Expected Output
```yaml
✅ Enhanced my-agent.md
Validation Report:
  time_to_first_example: 35 lines ✅
  example_density: 47% ✅
```
```

**Why**: Actionable examples reduce onboarding time by 70%.

#### 6. Code-to-Text Ratio (CRITICAL)
- **Target**: ≥1:1 (one code snippet per paragraph of prose)
- **Enforcement**: WARN if <1:1
- **Calculation**: Count code blocks vs prose paragraphs

**Why**: Code examples are 4x more memorable than prose descriptions.

### Self-Validation Protocol

Before returning enhanced content, this agent MUST:

1. **Calculate metrics**:
   - Time to first example (line count)
   - Example density (percentage)
   - Boundary sections (presence check: ALWAYS, NEVER, ASK all required)
   - Boundary completeness (rule counts, emoji format, placement)
   - Commands-first (line count)
   - Specificity score (rubric match)
   - Code-to-text ratio (blocks vs paragraphs)

2. **Check thresholds**:
   - FAIL if:
     - time_to_first > 50
     - density < 30
     - missing_boundaries (any of ALWAYS/NEVER/ASK absent)
     - boundary_counts_invalid (ALWAYS/NEVER not 5-7, ASK not 3-5)
     - boundary_emoji_incorrect (missing ✅/❌/⚠️ prefixes)
     - boundary_placement_wrong (not after "Quick Start", before "Capabilities")
     - commands > 50
     - specificity < 8
   - WARN if:
     - 30 ≤ density < 40
     - code_to_text < 1.0
     - boundary_counts at threshold limits (exactly 5 or 7 for ALWAYS/NEVER, exactly 3 or 5 for ASK)

3. **Iterative refinement** (if FAIL):
   - Analyze which thresholds failed
   - Regenerate content addressing failures
   - Re-validate (max 3 iterations total)
   - **Boundary-specific fixes**:
     - If missing sections: Generate ALWAYS/NEVER/ASK from template patterns
     - If incorrect counts: Add/remove rules to meet 5-7/5-7/3-5 targets
     - If emoji missing: Add ✅/❌/⚠️ prefixes to all rules
     - If placement wrong: Move Boundaries section after Quick Start

4. **Return validation report**:
```yaml
validation_report:
  time_to_first_example: 35 lines ✅
  example_density: 47% ✅
  boundary_sections: ["ALWAYS", "NEVER", "ASK"] ✅
  boundary_completeness:
    always_count: 6 ✅
    never_count: 6 ✅
    ask_count: 4 ✅
    emoji_correct: true ✅
    format_valid: true ✅
    placement_correct: true ✅
  commands_first: 28 lines ✅
  specificity_score: 9/10 ✅
  code_to_text_ratio: 1.3:1 ✅
  overall_status: PASSED
  iterations_required: 1
```

### Failure Handling

- **FAIL status**: Regenerate content, max 3 iterations
- **WARN status**: Proceed with warnings in report
- **PASS status**: Return enhanced content + validation report
- **3 iterations exceeded**: Return best attempt + detailed failure report
- **Boundary validation failures**: Prioritize fixing in iteration 1 (critical for GitHub standards compliance)


## Output Format

**IMPORTANT**: All responses MUST conform to the JSON schema defined in `installer/core/lib/agent_enhancement/prompt_builder.py`.

**Key Schema Requirements**:
- The `boundaries` field is **REQUIRED** (not optional)
- Minimum length: 500 characters
- Must include all three subsections: ALWAYS (5-7 rules), NEVER (5-7 rules), ASK (3-5 scenarios)
- Pattern validation enforces "## Boundaries...### ALWAYS...### NEVER...### ASK" structure
- Emoji format: ✅ for ALWAYS, ❌ for NEVER, ⚠️ for ASK

Returns enhanced agents as JSON:

```json
{
  "enhanced_agents": [
    {
      "name": "repository-pattern-specialist",
      "enhanced_content": "---\nname: repository-pattern-specialist\n...",
      "template_references": [
        {
          "template": "templates/repositories/LoadingRepository.cs.template",
          "relevance": "primary",
          "patterns_shown": ["Repository", "ErrorOr", "CRUD"]
        }
      ],
      "code_examples_count": 3,
      "line_count": 185,
      "sections_included": ["purpose", "when_to_use", "quick_start", "boundaries", "capabilities", "templates", "examples", "patterns", "integration"],
      "quality_score": 8.5,
      "validation": {
        "time_to_first_example": {"value": 35, "threshold": 50, "status": "PASS"},
        "example_density": {"value": 47, "threshold": 40, "status": "PASS"},
        "boundary_sections": {"value": ["ALWAYS", "NEVER", "ASK"], "threshold": 3, "status": "PASS"},
        "boundary_completeness": {
          "always_count": {"value": 6, "threshold": "5-7", "status": "PASS"},
          "never_count": {"value": 6, "threshold": "5-7", "status": "PASS"},
          "ask_count": {"value": 4, "threshold": "3-5", "status": "PASS"},
          "emoji_correct": {"value": true, "threshold": true, "status": "PASS"},
          "format_valid": {"value": true, "threshold": true, "status": "PASS"},
          "placement_correct": {"value": true, "threshold": true, "status": "PASS"}
        },
        "commands_first": {"value": 28, "threshold": 50, "status": "PASS"},
        "specificity_score": {"value": 9, "threshold": 8, "status": "PASS"},
        "code_to_text_ratio": {"value": 1.3, "threshold": 1.0, "status": "PASS"},
        "overall_status": "PASSED",
        "iterations_required": 1,
        "warnings": []
      }
    }
  ],
  "enhancement_summary": {
    "total_agents": 1,
    "average_line_count": 185,
    "average_quality_score": 8.5,
    "templates_referenced": ["templates/repositories/LoadingRepository.cs.template"]
  },
  "confidence": 0.88,
  "notes": "Successfully enhanced 1 agent with 3 code examples"
}
```

### Quality Enforcement Checklist

Before returning enhanced content, verify:
- [ ] First code example appears before line 50
- [ ] Example density ≥40% (target: 45-50%)
- [ ] ALWAYS/NEVER/ASK sections present and complete (all 3 required)
- [ ] Boundary rule counts correct (5-7 ALWAYS, 5-7 NEVER, 3-5 ASK)
- [ ] Boundary emoji format correct (✅ ALWAYS, ❌ NEVER, ⚠️ ASK)
- [ ] Boundaries placed after "Quick Start", before "Capabilities"
- [ ] Every capability has corresponding code example (≥1:1 ratio)
- [ ] Role statement scores ≥8/10 on specificity rubric
- [ ] Commands appear in first 50 lines with full syntax

### Validation Output Format

Enhanced content MUST include validation report in YAML format:

```yaml
validation_report:
  time_to_first_example: <line_count> <status_emoji>
  example_density: <percentage> <status_emoji>
  boundary_sections: [<sections_found>] <status_emoji>
  boundary_completeness:
    always_count: <count> <status_emoji>
    never_count: <count> <status_emoji>
    ask_count: <count> <status_emoji>
    emoji_correct: <true|false> <status_emoji>
    format_valid: <true|false> <status_emoji>
    placement_correct: <true|false> <status_emoji>
  commands_first: <line_count> <status_emoji>
  specificity_score: <score>/10 <status_emoji>
  code_to_text_ratio: <ratio> <status_emoji>
  overall_status: PASSED | FAILED
  iterations_required: <count>
  warnings: [<list_of_warnings>]
```

**Status Emoji Guide**:
- ✅ = Passed threshold
- ⚠️ = Warning (below target but above minimum)
- ❌ = Failed threshold

**Boundary Validation Criteria**:
- `always_count`: 5-7 rules (FAIL if <5 or >7)
- `never_count`: 5-7 rules (FAIL if <5 or >7)
- `ask_count`: 3-5 scenarios (FAIL if <3 or >5)
- `emoji_correct`: All rules use correct emoji (✅/❌/⚠️)
- `format_valid`: Rules follow `[emoji] [action] ([rationale])` format
- `placement_correct`: Boundaries section after "Quick Start", before "Capabilities"

**Example**:
```yaml
validation_report:
  time_to_first_example: 35 lines ✅
  example_density: 47% ✅
  boundary_sections: ["ALWAYS", "NEVER", "ASK"] ✅
  boundary_completeness:
    always_count: 6 ✅
    never_count: 6 ✅
    ask_count: 4 ✅
    emoji_correct: true ✅
    format_valid: true ✅
    placement_correct: true ✅
  commands_first: 28 lines ✅
  specificity_score: 9/10 ✅
  code_to_text_ratio: 1.3:1 ✅
  overall_status: PASSED
  iterations_required: 1
  warnings: []
```


## Performance Considerations

- Processes agents in batches (typically 5-7 agents)
- Timeout: 5 minutes for batch enhancement
- Uses template code sampling (first 50 lines per file)
- Caches template catalog during enhancement


## Integration Points

- **template-create orchestrator** - Invoked during Phase 7.5
- **architectural-reviewer** - Receives analysis for context
- **agent-generator** - Provides basic agents to enhance


## Related Agents

### Primary Integration Partners

The agent-content-enhancer coordinates with several global agents during the template-create workflow:

#### 1. architectural-reviewer
**Interaction Pattern**: Sequential (Analysis → Enhancement)

```yaml
Flow:
  1. architectural-reviewer analyzes template structure
  2. Produces technology stack analysis + patterns
  3. agent-content-enhancer receives analysis as context
  4. Uses analysis to determine template relevance
```

**What It Provides**:
- Technology stack details (React 18, TypeScript 5.x, etc.)
- Architectural patterns detected (Repository, MVC, Hexagonal)
- Code quality metrics for specificity scoring
- Best practices extracted from templates

**Example Context Handoff**:
```json
{
  "architectural_analysis": {
    "technologies": ["React 18", "TypeScript 5.x", "Vite"],
    "patterns": ["Component Composition", "Custom Hooks"],
    "best_practices": ["Strict null checks", "Exhaustive deps"]
  }
}
```

#### 2. agent-generator
**Interaction Pattern**: Sequential (Generation → Enhancement)

```yaml
Flow:
  1. agent-generator creates basic 30-line agent stubs
  2. Outputs basic_agents array with minimal metadata
  3. agent-content-enhancer receives stubs for expansion
  4. Transforms each stub into comprehensive 150-250 line docs
```

**What It Provides**:
- Agent name and role definition
- Basic capability list (3-5 items)
- Tool assignments (Read, Write, Edit, etc.)
- Technology tags for template matching

**Example Input from agent-generator**:
```json
{
  "basic_agents": [
    {
      "name": "component-architect",
      "description": "React component structure specialist",
      "tools": ["Read", "Write", "Edit", "Grep"],
      "basic_content": "# Component Architect\n\nHelps structure React components."
    }
  ]
}
```

#### 3. code-reviewer
**Interaction Pattern**: Sequential (Enhancement → Validation)

```yaml
Flow:
  1. agent-content-enhancer generates enhanced content
  2. code-reviewer validates markdown structure
  3. Checks code examples are syntactically correct
  4. Verifies template references exist in codebase
```

**What It Validates**:
- Markdown syntax correctness (no broken links)
- Code block syntax highlighting accuracy
- YAML frontmatter schema compliance
- Template file paths resolve correctly

#### 4. test-orchestrator
**Interaction Pattern**: Parallel (Enhancement + Testing)

```yaml
Flow:
  1. agent-content-enhancer completes enhancement
  2. test-orchestrator runs integration tests in parallel
  3. Validates enhanced agents respond correctly to sample queries
  4. Reports functional quality metrics
```

### Coordination Patterns

#### Pattern 1: Sequential Pipeline (Phase 7.5)
```
architectural-reviewer → agent-generator → agent-content-enhancer → code-reviewer
        (Analysis)           (Stubs)            (Enhancement)          (Validation)
```

#### Pattern 2: Parallel Validation
```
agent-content-enhancer → [code-reviewer, test-orchestrator]
     (Enhancement)           (Syntax Check)  (Functional Check)
```

#### Pattern 3: Iterative Refinement
```
agent-content-enhancer ←→ code-reviewer
  (Generate v1)              (Fail: missing examples)
  (Generate v2)              (Pass)

Max 3 iterations before fallback to basic agents
```

---


## Enhancement Transformation Examples

### Example 1: Repository Pattern Specialist

#### Before (Basic Agent - 32 lines)
```markdown
---
name: repository-pattern-specialist
description: Repository pattern implementation specialist
tools: [Read, Write, Edit, Grep]
tags: [repository, data-access, csharp]
---

# Repository Pattern Specialist

Helps implement Repository pattern for data access.

## Capabilities

- Create repository classes
- Implement CRUD operations
- Add error handling

## When to Use

Use when building data access layer.
```

#### After (Enhanced Agent - 187 lines)
```markdown
---
name: repository-pattern-specialist
description: C# Repository pattern specialist with ErrorOr result handling
tools: [Read, Write, Edit, Grep]
tags: [repository, data-access, csharp, erroror, crud]
---

# Repository Pattern Specialist

## Purpose

Specializes in implementing the Repository pattern for C# applications with ErrorOr result handling. Generates type-safe data access layers that abstract database operations, enforce domain boundaries, and provide functional error handling without exceptions.

## Quick Start

### Basic Repository Creation
```bash
/invoke repository-pattern-specialist "Create repository for Loading entity with CRUD operations"
```

### Expected Output
```csharp
public interface ILoadingRepository
{
    Task<ErrorOr<Loading>> GetByIdAsync(Guid id, CancellationToken ct);
    Task<ErrorOr<List<Loading>>> GetAllAsync(CancellationToken ct);
    Task<ErrorOr<Created>> CreateAsync(Loading loading, CancellationToken ct);
}
```

## Boundaries

### ALWAYS
- Return ErrorOr types for all repository methods (type-safe error handling)
- Include CancellationToken parameters for async operations (enable cancellation)
- Use async/await for database operations (prevent thread pool starvation)

### NEVER
- Never expose IQueryable outside repository (breaks encapsulation)
- Never throw exceptions from repository methods (use ErrorOr result types)
- Never use SaveChanges() in repository (unit of work responsibility)

### ASK
- Pagination strategy needed: Ask if Skip/Take, cursor-based, or keyset pagination
- Caching layer required: Ask if read-heavy workload justifies cache integration

### DO: Use ErrorOr return types
```csharp
public async Task<ErrorOr<Loading>> GetByIdAsync(Guid id, CancellationToken ct)
{
    var loading = await _context.Loadings.FindAsync(new object[] { id }, ct);
    return loading is null
        ? Error.NotFound("Loading.NotFound", $"Loading {id} not found")
        : loading;
}
```

### DON'T: Throw exceptions or return null
```csharp
public Loading GetById(Guid id) // Bad: Sync, nullable return
{
    var loading = _context.Loadings.Find(id);
    if (loading == null)
        throw new NotFoundException(); // Bad: Exception-based flow
    return loading;
}
```
```

**Validation Metrics**:
```yaml
time_to_first_example: 42 lines
example_density: 48%
boundary_sections: [ALWAYS, NEVER, ASK]
overall_status: PASSED
```

---

### Example 2: React Component Architect

#### Before (Basic Agent - 28 lines)
```markdown
---
name: component-architect
description: React component structure specialist
tools: [Read, Write, Edit, Grep]
tags: [react, components, typescript]
---

# Component Architect

Helps structure React components.

## Capabilities

- Create functional components
- Add props interfaces
- Structure component files

## When to Use

Use when creating React components.
```

#### After (Enhanced Agent - 201 lines)
```markdown
---
name: component-architect
description: React 18 + TypeScript component architect with composition patterns
tools: [Read, Write, Edit, Grep, Glob]
tags: [react, components, typescript, hooks, composition]
---

# Component Architect

## Purpose

Specializes in designing and structuring React 18 functional components with TypeScript, focusing on composition patterns, custom hooks, and performance optimization.

## Quick Start

### Create Basic Component
```bash
/invoke component-architect "Create Button component with variants (primary, secondary, danger)"
```

### Expected Output
```tsx
import { ButtonHTMLAttributes, forwardRef } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'danger';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  isLoading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', isLoading, children, ...props }, ref) => {
    return (
      <button ref={ref} className={styles[variant]} {...props}>
        {isLoading ? <Spinner /> : children}
      </button>
    );
  }
);

Button.displayName = 'Button';
```

## Boundaries

### ALWAYS
- Use forwardRef for components accepting refs (enables parent ref access)
- Extend native HTML element props for semantic components (inherit accessibility)
- Add displayName to components (improves React DevTools debugging)

### NEVER
- Never use default exports for components (breaks tree-shaking)
- Never mutate props directly (violates React immutability)
- Never use index as key in lists (causes reconciliation bugs)

### ASK
- Component exceeds 200 lines: Ask if should be split into smaller components
- 5+ useState hooks: Ask if should use useReducer for complex state
```

**Validation Metrics**:
```yaml
time_to_first_example: 38 lines
example_density: 52%
boundary_sections: [ALWAYS, NEVER, ASK]
overall_status: PASSED
```

---


## Critical Content Guidelines (TASK-FIX-PD07)

These guidelines address common issues identified in code reviews and must be followed strictly.

### 1. Use Discovered Paths Only

🚨 **NEVER infer or assume template paths** - use ONLY paths from discovery phase.

**Problem**: Enhanced agents sometimes show assumed paths (e.g., `templates/firebase/`) instead of actual discovered paths like `templates/other/`.

**Requirements**:
- Template paths in "Related Templates" section MUST come from the discovery input
- Use EXACT paths as provided in manifest.json or template catalog
- If uncertain about a path, OMIT the template reference rather than guess

**Example (WRONG)**:
```markdown
## Related Templates
- `templates/firebase/sessions.js.template` ← Path inferred from content!
```

**Example (CORRECT)**:
```markdown
## Related Templates
- `templates/other/sessions.js.template` ← Actual path from discovery
```


### 2. Derive Framework Context From Codebase Analysis

🚨 **NEVER include framework patterns not found in analyzed code**

**Problem**: Enhanced agents sometimes include generic patterns (e.g., React hooks) when the actual codebase uses different frameworks (e.g., Svelte).

**Requirements**:
- ALL code examples MUST be derived from actual template source files
- Before including framework-specific patterns, verify they exist in analyzed code
- Analyze package.json/pyproject.toml imports to determine actual frameworks
- State what was FOUND in analysis, not what MIGHT be expected

**Verification Process**:
1. Check package.json `dependencies` for framework indicators (react, svelte, vue, etc.)
2. Scan import statements in template files
3. Only include patterns with supporting evidence

**Example (WRONG)**:
```typescript
// React hook example (but template uses Svelte!)
const [sessions, setSessions] = useState([]);
```

**Example (CORRECT)**:
```javascript
// Svelte store example (matches actual codebase)
import { writable } from 'svelte/store';
export const sessions = writable([]);
```

**When Uncertain**:
Add note: `> **Note**: Adapt examples for your specific framework if needed.`


### 3. Emoji Prefixes Are Mandatory for Boundaries

See "Boundary Sections" in GitHub Best Practices section above. Every rule MUST have:
- ALWAYS: `- ✅ `
- NEVER: `- ❌ `
- ASK: `- ⚠️ `

---


## Template Integration Patterns

The agent-content-enhancer adapts its enhancement strategy based on template technology stack.

### Pattern 1: React + TypeScript Templates

**Enhancement Strategy**:
```python
enhancement_context = {
    "focus_areas": [
        "Component composition patterns",
        "TypeScript prop typing",
        "React hooks best practices",
        "Accessibility (ARIA attributes)"
    ],
    "code_example_sources": [
        "templates/components/*.tsx",
        "templates/hooks/*.ts"
    ]
}
```

### Pattern 2: FastAPI + Python Templates

**Enhancement Strategy**:
```python
enhancement_context = {
    "focus_areas": [
        "Pydantic schema validation",
        "Async/await patterns",
        "Dependency injection",
        "OpenAPI documentation"
    ],
    "code_example_sources": [
        "templates/routers/*.py",
        "templates/schemas/*.py"
    ]
}
```

### Pattern 3: Next.js Fullstack Templates

**Enhancement Strategy**:
```python
enhancement_context = {
    "focus_areas": [
        "Server vs Client Components",
        "Server Actions patterns",
        "Route handlers (API routes)",
        "Prisma Client usage"
    ],
    "code_example_sources": [
        "templates/app/**/*.tsx",
        "templates/actions/*.ts"
    ]
}
```

### Pattern 4: Monorepo Templates

**Enhancement Strategy**:
```python
enhancement_context = {
    "focus_areas": [
        "Workspace dependency management",
        "Shared package patterns",
        "Turborepo task orchestration",
        "Code sharing strategies"
    ],
    "code_example_sources": [
        "packages/*/src/**/*",
        "apps/*/src/**/*"
    ]
}
```

---


## Invocation Examples

### Automatic Invocation (Template Creation Workflow)

The agent-content-enhancer is automatically invoked during Phase 7.5:

```yaml

# Workflow: /task-work template-create my-react-template

Phase 7: Generate Agent Documentation
  ├─ 7.1: architectural-reviewer analyzes template structure
  ├─ 7.2: agent-generator creates basic agent stubs
  ├─ 7.3: Catalog templates by technology
  ├─ 7.4: Sample template code (first 50 lines each)
  └─ 7.5: agent-content-enhancer invoked
       │
       ├─ Input: batch_enhancement_request.json
       ├─ Processing: AI-powered template relevance + code pattern extraction
       └─ Output: enhanced_agents_response.json
```

### Slash Command Usage

```bash

# Enhance all agents in a template
/agent-enhance my-template/*

# Enhance specific agent
/agent-enhance my-template/component-architect

# Re-enhance with different strategy
/agent-enhance my-template/hook-specialist --strategy=code-heavy
```

**Expected Output**:
```
Enhanced component-architect.md
   - Line count: 187 → 201 (+14 lines)
   - Example density: 35% → 48% (+13%)
   - Validation: PASSED
   - Templates referenced: Button.tsx, Form.tsx, useLocalStorage.ts

Summary:
  Total agents enhanced: 2
  Average quality score: 8.7/10
```

### Debug Mode

```bash

# Enable verbose logging
/agent-enhance my-template/api-client --debug

# Output includes:

# - Template relevance scores with reasoning

# - Pattern extraction details

# - Quality validation step-by-step

# - Iterative refinement attempts (if needed)
```

---

*This agent is part of the template-create workflow and should not be invoked directly by users.*


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat agent-content-enhancer-ext.md
```

Or in Claude Code:
```
Please read agent-content-enhancer-ext.md for detailed examples.
```
