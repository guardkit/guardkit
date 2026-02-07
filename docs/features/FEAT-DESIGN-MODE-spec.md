# Feature Specification: Design Mode for Player-Coach Loops

## Overview

Add a **design mode** to GuardKit's task workflow that enables design-to-code implementation within Player-Coach adversarial loops. When a task includes a design URL (Figma or Zeplin), the system extracts design intent, generates components via the Player agent, and validates visual fidelity via the Coach agent using browser-based verification.

This feature closes the gap between design handoff and code generation by making the design itself the source of truth — not a developer's interpretation of it.

## Problem Statement

Currently, GuardKit's `/task-work` workflow treats all tasks as code-only. When a task involves implementing a UI from a design, the developer must:

1. Manually inspect the design in Figma/Zeplin
2. Mentally translate design tokens (colours, spacing, typography) into code
3. Eyeball the result against the design
4. Iterate manually until it looks right

This is error-prone, slow, and produces inconsistent results. The Player-Coach loop should be able to extract design intent programmatically and validate output visually — the same way it validates code correctness through tests.

## Scope

### In Scope

- Accept design URLs (Figma, Zeplin) on task creation via `design:URL` parameter
- Extract design data via MCP tools (Figma Dev Mode MCP, Zeplin MCP)
- Document design boundaries (what IS and IS NOT in the design)
- Generate components via Player agent with design context
- Validate visual fidelity via Coach agent using browser-based verification
- Enforce a 12-category prohibition checklist to prevent scope creep
- Support multiple target stacks (React/TypeScript, .NET MAUI) through delegation to stack-specific UI specialists
- Platform-specific testing for mobile targets (iOS Simulator, Android Emulator)

### Out of Scope

- Sketch support (no MCP server available)
- Adobe XD support (deprecated by Adobe)
- Full design system generation (this is per-component)
- Automated design file creation or modification
- Real-time design sync / watch mode

## User Journey

### Creating a Design Task

```bash
# Figma design
/task-create "Login form" design:https://figma.com/design/abc?node-id=2-2 priority:high

# Zeplin design
/task-create "User profile card" design:https://app.zeplin.io/project/abc/screen/def

# Feature-level with design
/feature-plan "Settings page redesign" --context docs/designs/settings-figma-urls.md
```

### What Happens During `/task-work`

When `/task-work` detects a `design_url` in the task frontmatter, it activates design mode:

1. **Design Extraction Phase** — Extract design data via MCP before the Player starts
2. **Boundary Documentation** — Document what IS and IS NOT in the design (prohibition checklist)
3. **Player Implementation** — Player receives extracted design context + constraints
4. **Coach Verification** — Coach uses browser-based visual comparison against design reference
5. **Constraint Validation** — Verify zero scope creep against prohibition checklist

## Technical Requirements

### 1. Task Frontmatter Extension

Tasks with design URLs store metadata for the orchestration pipeline:

```yaml
---
id: TASK-001
title: Implement login form
status: backlog
design_url: https://figma.com/design/abc?node-id=2-2
design_source: figma        # Auto-detected: figma | zeplin
design_metadata:
  file_key: abc123
  node_id: "2:2"            # IMPORTANT: Colon format, not hyphen
  extracted_at: null         # Set after MCP extraction
  extraction_hash: null      # SHA-256 of extracted design data (for change detection)
  visual_reference: null     # Path to reference screenshot
---
```

**Design source detection:**
- `figma.com` → `figma`
- `zeplin.io` or `app.zeplin.io` → `zeplin`
- Anything else → error with helpful message

### 2. MCP Integration Layer

A facade that hides MCP complexity from downstream agents. The orchestrator handles MCP calls; the Player and Coach never call MCP tools directly.

#### Figma MCP Tools

| Tool | Purpose | Token Risk |
|------|---------|------------|
| `mcp__figma-dev-mode__get_code` | React component suggestions | High (can exceed 25K limit) |
| `mcp__figma-dev-mode__get_image` | Visual reference for regression | Low |
| `mcp__figma-dev-mode__get_variable_defs` | Design tokens (colours, spacing, typography) | Medium |

#### Zeplin MCP Tools

| Tool | Purpose |
|------|---------|
| `mcp__zeplin__get_project` | Project metadata |
| `mcp__zeplin__get_screen` | Screen design data |
| `mcp__zeplin__get_component` | Component design data |
| `mcp__zeplin__get_styleguide` | Design system tokens |
| `mcp__zeplin__get_colors` | Colour palette |
| `mcp__zeplin__get_text_styles` | Typography scale |

#### Critical: Figma Node ID Conversion

This is the **primary cause of MCP failures** and must be handled by the orchestrator before any MCP call:

```
Figma URL format:  node-id=2-2    (hyphens)
MCP API format:    "2:2"          (colons)
```

The orchestrator must convert on extraction and validate format before every MCP call.

#### Token Budget Management

Figma MCP responses can be enormous (observed: 351,378 tokens vs 25,000 context limit). Mitigations:

- Query specific nodes, not entire files
- Set `MAX_MCP_OUTPUT_TOKENS` limit
- Cache MCP responses (1-hour TTL) to avoid redundant calls during Player-Coach iterations
- Summarise extracted design data before passing to Player/Coach

### 3. Prohibition Checklist (12 Categories)

The design boundary documentation uses a standardised checklist. By default, everything not explicitly shown in the design is **prohibited**:

| # | Category | Default | Override Condition |
|---|----------|---------|-------------------|
| 1 | Loading states | Prohibited | Only if shown in design |
| 2 | Error states | Prohibited | Only if shown in design |
| 3 | Additional form validation | Prohibited | Only if shown in design |
| 4 | Complex state management | Prohibited | Only if shown in design |
| 5 | API integrations | **ALWAYS prohibited** | Never — out of scope |
| 6 | Navigation beyond design | Prohibited | Only if shown in design |
| 7 | Additional buttons/controls | Prohibited | Only if shown in design |
| 8 | Sample data beyond design | **ALWAYS prohibited** | Never |
| 9 | Responsive breakpoints | Prohibited | Only if shown in design |
| 10 | Animations not specified | Prohibited | Only if shown in design |
| 11 | Best practice additions | **ALWAYS prohibited** | Never |
| 12 | Extra props for flexibility | **ALWAYS prohibited** | Never |

Items 5, 8, 11, and 12 are **unconditionally prohibited** — even if someone argues it's "best practice" to add them.

### 4. Design Extraction Phase (Pre-Player)

Before the Player-Coach loop starts, the orchestrator runs a design extraction phase:

**Phase 0 — MCP Verification**: Verify required MCP tools are available. Fail fast if not.

**Phase 1 — Design Data Extraction**: Call MCP tools to extract:
- Component structure and hierarchy
- Design tokens (colours, spacing, typography, border radius)
- Visual reference image (screenshot for regression testing)
- Layout constraints (padding, margins, alignment)

**Phase 2 — Boundary Documentation**: Analyse the extracted design to produce:
- List of elements that ARE in the design (exhaustive)
- Prohibition checklist with decisions for each category
- Design token mapping to target stack format

This extraction output becomes the **design context** passed to both Player and Coach.

### 5. Player Agent: Design-Aware Implementation

When the Player receives a task with design context, it:

1. Reads the extracted design data (NOT raw MCP output)
2. Reads the prohibition checklist
3. Generates component code matching the design exactly
4. Applies design tokens (exact colours, spacing, typography — no approximation)
5. Delegates to the appropriate stack-specific UI specialist:
   - React/TypeScript → `react-component-generator` agent
   - .NET MAUI → `maui-ux-specialist` agent

**The Player never calls MCP tools directly.** It works from the pre-extracted design context.

#### Delegation Interface

The Player passes to UI specialists:

```typescript
interface DesignContext {
  elements: ExtractedElement[];          // What's in the design
  constraints: ProhibitionChecklist;      // What's NOT allowed
  tokens: {
    colors: Record<string, string>;       // name → hex
    spacing: Record<string, string>;      // name → value
    typography: TypographyScale[];        // font families, sizes, weights
    borderRadius: Record<string, string>;
  };
  metadata: {
    source: "figma" | "zeplin";
    nodeId: string;
    visualReference: string;             // Path to reference screenshot
  };
}
```

The Player expects back from UI specialists:

```typescript
interface ComponentResult {
  generatedFiles: string[];
  constraintViolations: string[];       // Should be empty
}
```

### 6. Coach Agent: Visual Verification

The Coach validates the Player's output using browser-based visual comparison. This is the key innovation — rather than just reviewing code, the Coach **renders the component and compares it visually** to the design reference.

#### Browser Verification Tool

**Primary: agent-browser** (Vercel Labs) — 5.7× more token-efficient than Playwright MCP (~1,400 tokens vs ~7,800 per test cycle). Element refs (`@e1`, `@e2`) instead of brittle CSS selectors. Critical for Player-Coach loops where multiple verification cycles consume context budget.

**Fallback: Playwright MCP + Appium** — for MAUI platform-specific targets only (iOS Simulator, Android Emulator). Accept higher token cost for platform-specific testing where agent-browser has no coverage.

#### BrowserVerifier Abstraction

A unified interface that hides the browser tool choice from downstream agents. Task metadata's target stack determines which implementation is selected at runtime.

```typescript
interface BrowserVerifier {
  open(url: string): Promise<void>;
  screenshot(selector?: string): Promise<Buffer>;
  getAccessibilityTree(): Promise<AccessibilityNode[]>;
  close(): Promise<void>;
}

// Implementation selection (orchestrator responsibility)
function selectVerifier(task: TaskMetadata): BrowserVerifier {
  if (task.targetStack === 'maui' && task.platformTarget !== 'web') {
    return new PlaywrightAppiumVerifier(task.platformTarget);
  }
  return new AgentBrowserVerifier();  // Default for all web targets
}
```

#### Visual Comparison Pipeline (SSIM + AI Escalation)

The Coach uses a tiered comparison pipeline. Tier 1 is deterministic and zero-token-cost. Tier 2 activates only for borderline cases.

```
Tier 1: SSIM Score (deterministic, zero token cost)
├── SSIM ≥ 0.95 → PASS → Coach approves
├── SSIM 0.85–0.94 → ESCALATE to Tier 2
└── SSIM < 0.85 → FAIL → Coach rejects, Player must retry

Tier 2: AI Vision Review (borderline cases only)
├── Send both images + SSIM spatial map to Coach's LLM
├── Coach reasons about rendering engine artefacts vs actual violations
└── Coach makes final determination with explanation
```

Implementation uses `ssim.js` with the `bezkrovny` variant (optimised for speed, negligible accuracy loss — recommended default in jest-image-snapshot):

```javascript
const { compare } = require('ssim.js');

const { mssim } = compare(designRef, rendered, { ssim: 'bezkrovny' });

if (mssim >= 0.95) {
  return { pass: true, score: mssim, method: 'ssim' };
} else if (mssim >= 0.85) {
  const aiReview = await coachVisionReview(designRef, rendered, ssimMap);
  return { pass: aiReview.pass, score: mssim, feedback: aiReview.feedback };
} else {
  return { pass: false, score: mssim, feedback: 'Visual fidelity below threshold' };
}
```

**Important**: Design token validation (correct hex colour, correct spacing value) is handled separately from visual comparison — those are structural checks in the prohibition checklist, not image comparison tasks.

#### Coach Verification Steps

1. **Render** the generated component in a browser (or simulator for mobile)
2. **Screenshot** the rendered output
3. **Compare** rendered screenshot against the design reference image
4. **Check** the prohibition checklist — flag any elements present in code but not in design
5. **Report** visual fidelity score and any constraint violations

#### Quality Gates

| Gate | Threshold | Action on Failure |
|------|-----------|-------------------|
| Visual fidelity | ≥95% match | Return to Player with specific differences |
| Constraint violations | Zero | Return to Player with violation list |
| Design tokens applied | 100% | Return to Player with missing tokens |

### 7. Platform-Specific Considerations

#### React/TypeScript
- Tailwind CSS for styling (match design specs exactly)
- TypeScript interfaces for component props
- Visual regression via browser screenshot comparison

#### .NET MAUI (via Zeplin)
- XAML components with platform-specific adaptations
- Design tokens mapped to `ResourceDictionary` format
- 8pt grid system enforcement
- Platform-specific testing targets:

| Platform | Min Touch Target | Corner Radius | Notes |
|----------|-----------------|---------------|-------|
| iOS | 48pt | 8pt | SafeArea constraints |
| Android | 48dp | Material Design ripple | Material You |
| Windows | 48px | 4px (Fluent Design) | Fluent Design |
| macOS | 48pt | — | Translucent toolbar |

- Icon code conversion: After MCP extraction, convert icon codes to XAML format (e.g., `&#xe5d2;` → `&#xE5D2;`)

### 8. Error Handling and Retry Strategy

The orchestration follows a saga pattern with fail-fast and retry:

| Error Type | Strategy |
|------------|----------|
| MCP tools not available | Fail fast in Phase 0 — abort before any work |
| MCP network timeout | Exponential backoff (3 retries) |
| MCP rate limit | Exponential backoff with jitter |
| MCP token limit exceeded | Narrow query to specific node, retry |
| Visual fidelity < 95% | Return to Player (up to max adversarial turns) |
| Constraint violations | Return to Player with specific violations |
| Max turns exceeded | Escalate to human review |

### 9. Caching Strategy

MCP responses should be cached to avoid redundant calls during Player-Coach iterations:

| Data | TTL | Invalidation |
|------|-----|-------------|
| Design tokens | 1 hour | Design URL change |
| Component structure | 1 hour | Design URL change |
| Visual reference image | 1 hour | Design URL change |
| Generated components | Per-turn | Each Player iteration |

Cache location: `.guardkit/cache/design/` keyed by design URL hash.

## Acceptance Criteria

### Task Creation
- [ ] `/task-create` accepts `design:URL` parameter
- [ ] Design URL stored in task frontmatter under `design_url`
- [ ] Design source auto-detected (figma/zeplin)
- [ ] Design metadata (file_key, node_id) extracted from URL
- [ ] Node IDs converted from hyphen to colon format on storage
- [ ] Command works without design URL (backward compatible)

### MCP Integration
- [ ] Figma MCP tools called with correct node ID format (colons)
- [ ] Zeplin MCP tools called with correct project/screen IDs
- [ ] MCP verification fails fast if required tools unavailable
- [ ] Token budget respected (query specific nodes, not entire files)
- [ ] MCP responses cached (1-hour TTL)

### Design Extraction
- [ ] Component structure extracted from design
- [ ] Design tokens extracted (colours, spacing, typography)
- [ ] Visual reference screenshot captured
- [ ] Prohibition checklist populated with decisions per category
- [ ] Extracted data summarised for Player/Coach context windows

### Player Integration
- [ ] Player receives pre-extracted design context (not raw MCP)
- [ ] Player delegates to stack-specific UI specialist
- [ ] Player respects prohibition checklist (no scope creep)
- [ ] Generated component applies exact design tokens

### Coach Integration
- [ ] Coach renders generated component in browser via BrowserVerifier abstraction
- [ ] BrowserVerifier selects agent-browser for web targets, Playwright+Appium for MAUI platform targets
- [ ] Coach captures screenshot of rendered output
- [ ] Coach compares rendered vs design reference using SSIM tiered pipeline
- [ ] SSIM ≥ 0.95 → auto-PASS; SSIM 0.85–0.94 → AI vision escalation; SSIM < 0.85 → auto-FAIL
- [ ] AI vision escalation receives SSIM spatial map + both images for targeted reasoning
- [ ] Coach checks prohibition checklist compliance
- [ ] Coach reports visual fidelity score and comparison method used

### Design Change Detection
- [ ] `extraction_hash` (SHA-256) computed and stored after each MCP extraction
- [ ] On `task-work`, if `extracted_at` exceeds 1-hour TTL, re-query MCP and compare extraction hashes
- [ ] BACKLOG tasks: silent cache refresh on next `task-work`
- [ ] IN_PROGRESS tasks: pause after current cycle, notify user of design change, await user decision (continue or restart)
- [ ] IN_REVIEW tasks: flag design change in review notes for reviewer decision
- [ ] COMPLETED tasks: require new task creation (no automatic re-processing)

### Quality
- [ ] Zero constraint violations in approved output
- [ ] All design tokens applied (exact match, no approximation)
- [ ] Platform-specific adaptations for MAUI targets
- [ ] Retry logic for transient MCP failures

## Dependencies

### Required
- Figma Dev Mode MCP server (`figma-dev-mode`) — for Figma designs
- Zeplin MCP server (`zeplin`) — for Zeplin designs
- agent-browser CLI (Vercel Labs) — primary browser verification tool
- ssim.js — SSIM visual comparison (bezkrovny variant)
- Existing Player-Coach adversarial loop infrastructure

### Optional
- Playwright MCP + Appium — fallback for MAUI platform-specific testing (iOS Simulator, Android Emulator)
- iOS Simulator — for MAUI iOS visual testing (requires Playwright fallback)
- Android Emulator — for MAUI Android visual testing (requires Playwright fallback)

## Prior Art and References

This feature draws from two existing orchestrator agents that contain battle-tested patterns but predate the current Player-Coach architecture:

- `tasks/backlog/design-url-integration/figma-react-orchestrator.md` — 6-phase saga pattern, Figma MCP integration, node ID conversion, token budget management
- `tasks/backlog/design-url-integration/zeplin-maui-orchestrator.md` — Zeplin MCP integration, platform-specific adaptations, icon code conversion, 8pt grid enforcement
- `tasks/backlog/design-url-integration/TASK-UX-7F1E-add-design-url-parameter.md` — Original task-create extension design
- `tasks/backlog/design-url-integration/TASK-UX-2A61-refactor-figma-react-orchestrator.md` — Technology-agnostic delegation pattern

These should be treated as domain knowledge references, not implementation tasks — their architecture assumptions are outdated.

## Decisions

Resolved via research analysis — see `FEAT-DESIGN-MODE-open-questions-analysis.md` for full rationale.

### 1. Browser Verification Tooling → agent-browser primary, Playwright fallback for mobile

agent-browser (Vercel Labs) is **5.7× more token-efficient** than Playwright MCP (~1,400 tokens vs ~7,800 per test cycle). In the adversarial loop where the Coach runs multiple verification cycles, this directly determines how many iterations are possible before context exhaustion.

| Target | Tool | Reason |
|--------|------|--------|
| React/TypeScript | agent-browser (CLI) | Token-efficient, element refs instead of CSS selectors |
| MAUI web preview | agent-browser | Desktop browser preview sufficient |
| MAUI platform targets (iOS/Android) | Playwright + Appium | Only viable path for Simulator/Emulator testing |

Implementation: `BrowserVerifier` abstraction hides the tool choice from downstream agents. Task metadata's target stack determines which implementation is selected. See Coach Agent §6 — BrowserVerifier Abstraction.

### 2. Visual Comparison Method → SSIM primary + AI escalation for borderline cases

SSIM (Structural Similarity Index) is the industry standard for comparing structurally similar images from different rendering engines — exactly the design-to-code scenario. Deterministic, zero token cost, and maps directly to the ≥95% fidelity requirement.

| SSIM Score | Action |
|------------|--------|
| ≥ 0.95 | **PASS** — Coach approves |
| 0.85–0.94 | **ESCALATE** — Coach uses AI vision to reason about whether differences are rendering engine artefacts or actual design violations |
| < 0.85 | **FAIL** — Coach rejects, Player must retry |

Implementation: `ssim.js` with `bezkrovny` variant (same as jest-image-snapshot's recommended default). Design token validation (hex colours, spacing values) handled separately as structural checks in the prohibition checklist. See Coach Agent §6 — Visual Comparison Pipeline.

### 3. Design Iteration Handling → State-aware hybrid with human checkpoints

Behaviour depends on where the task is in its lifecycle when a design change is detected:

| Task State | Behaviour |
|------------|----------|
| BACKLOG | Silent cache refresh on next `task-work` — design was never extracted |
| IN_PROGRESS | Pause after current cycle, notify user: "Design has changed since extraction." User decides: continue or restart |
| IN_REVIEW | Flag in review notes: "Design updated since implementation." Reviewer decides |
| COMPLETED | New task required, referencing original |

Change detection: hash-based comparison of MCP extraction data. On each `task-work`, if `extracted_at` exceeds cache TTL (1 hour), re-query MCP, hash the new extraction, compare against stored `extraction_hash`. No webhook infrastructure required. See Task Frontmatter §1 and Acceptance Criteria.
