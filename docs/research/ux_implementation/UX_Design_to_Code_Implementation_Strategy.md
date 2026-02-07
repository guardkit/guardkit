# UX Design-to-Code Implementation Strategy

## Modernising Frontend Implementation with Design MCPs, Player-Coach Verification, and Mobile Testing

> **Author**: Rich Woollcott / Appmilla  
> **Date**: 7 February 2026  
> **Status**: Strategy Document  
> **Scope**: GuardKit / AutoBuild Integration

---

## Executive Summary

This document defines the strategy for modernising UX frontend implementation workflows within GuardKit, integrating Figma and Zeplin MCPs with AutoBuild's player-coach adversarial verification loop. The approach replaces manual design-to-code translation with an automated pipeline: extract design specifications via MCP, generate components through stack-specific UI specialists, and verify visual fidelity using AI-optimised browser automation.

Three critical findings shape this strategy:

1. **Vercel agent-browser is 5.7x more token-efficient than Playwright** for verification loops, making it the recommended tool for Player-Coach cycles where context window budget is at a premium.

2. **Figma MCP token limits are a real constraint** — responses can exceed 350K tokens against a 25K limit. Node-specific queries, caching, and the `MAX_MCP_OUTPUT_TOKENS` environment variable are essential mitigations.

3. **Mobile testing via iOS Simulator and Android Emulator is practical today** through agent-browser's Appium integration and tools like Arbigent, enabling cross-platform verification for React Native and .NET MAUI projects.

---

## 1. Current State Assessment

### What Exists

GuardKit already has foundational infrastructure for design-to-code workflows:

**Orchestrators** (`tasks/backlog/design-url-integration/`):
The `figma-react-orchestrator.md` implements a 6-phase Saga pattern covering MCP verification, design extraction, boundary documentation, component generation, visual testing, and constraint validation. A parallel `zeplin-maui-orchestrator.md` handles .NET MAUI with XAML generation.

**Constraint System**: A 12-category prohibition checklist enforces zero scope creep. Loading states, error states, API integrations, and extra props for flexibility are prohibited by default — only what's visible in the design gets implemented.

**Backlog Tasks**: TASK-UX-7F1E (add `design:URL` parameter to task-create) and TASK-UX-2A61 (refactor figma-react-orchestrator to be technology-agnostic) are defined and ready for implementation.

### What's Missing

The current orchestrators are stack-specific (React, MAUI) rather than technology-agnostic. There's no integration with AutoBuild's player-coach pattern for independent verification. Browser-based visual testing relies on Playwright, which is verbose and fragile. Mobile testing has no established workflow.

---

## 2. Design Extraction Strategy

### Figma MCP Integration

The Figma Dev Mode MCP provides direct access to design specifications, code suggestions, and design tokens. However, token management is the primary technical challenge.

**The Token Problem**: A full file extraction can return 351,378 tokens against a typical 25,000 token MCP response limit. This isn't a theoretical concern — it's been encountered in practice.

**Mitigations**:

Set the `MAX_MCP_OUTPUT_TOKENS` environment variable to increase the limit. Use node-specific queries rather than full file extractions — the `nodeId` parameter targets individual components. Cache MCP responses with a 1-hour TTL to avoid redundant API calls, and implement retry logic with exponential backoff for 429 rate limit errors.

**Node ID Format Conversion**: This is the primary cause of MCP failures in previous implementations. Figma URLs use hyphen format (`node-id=2-2`) while the MCP API requires colon format (`"2:2"`). The conversion must happen before any MCP call.

**Extraction Pattern**:
```
1. Verify MCP tools available (Phase 0)
2. Convert node ID: "2-2" → "2:2"
3. Extract code suggestion: get_code(nodeId, clientFrameworks)
4. Extract design tokens: get_variable_defs(nodeId)
5. Capture visual reference: get_image(nodeId, format: "png", scale: 2)
```

### Zeplin MCP Integration

Zeplin's MCP is more straightforward — colours, text styles, and screen data can be extracted in parallel MCP calls. The Zeplin API is less prone to token overflow since it returns structured design token data rather than full file representations.

**Extraction Pattern**:
```
Parallel fetch: colours + text styles + screen data
→ Merge into unified DesignContext
→ Pass to stack-specific UI specialist
```

---

## 3. Browser Verification: agent-browser vs Playwright

### Why agent-browser Wins

Vercel's agent-browser, released December 2025, was purpose-built for AI agent workflows. The comparison with Playwright is decisive for the Player-Coach use case.

**Token efficiency**: For equivalent test coverage (6 test scenarios), agent-browser produces ~5.5K characters of output versus Playwright's ~31K characters — a 5.7x improvement. In a Player-Coach loop where each turn consumes context window budget, this is the difference between 3-4 verification cycles and potentially only 1.

**Element stability**: agent-browser uses element references (`@e1`, `@e2`) derived from accessibility tree snapshots rather than CSS selectors. When a design changes, CSS selectors break; element refs based on semantic role and content are more resilient.

**Compact snapshots**: The `snapshot -i` command returns only interactive elements with their refs, producing a minimal representation that fits comfortably in agent context.

### Workflow

```bash
# Desktop verification
agent-browser open http://localhost:3000/component
agent-browser snapshot -i --json    # Get interactive elements with refs
agent-browser screenshot actual.png  # Capture rendered output
agent-browser click @e1             # Test interaction
agent-browser fill @e2 "test"       # Test form input

# iOS Simulator verification
agent-browser -p ios --device "iPhone 16 Pro" open http://localhost:3000
agent-browser -p ios snapshot -i
agent-browser -p ios tap @e1
agent-browser -p ios screenshot ios-actual.png
```

### When to Use Playwright

Playwright remains appropriate for complex E2E scenarios requiring network interception, multi-tab orchestration, or advanced browser features. The recommendation is a hybrid approach: agent-browser for the Player-Coach verification loop, Playwright for comprehensive E2E test suites that run outside the agentic flow.

---

## 4. AutoBuild Player-Coach Integration

### Why Player-Coach for Design Verification

The AutoBuild pattern uses adversarial cooperation: a Player agent implements while a Coach agent validates independently. Fresh LLM instances on each turn prevent context pollution. Critically, only the Coach can approve completion — this prevents the "false completion" problem where an implementing agent declares its own work done.

This maps perfectly to design-to-code verification. A Player generating a component from a Figma design has inherent bias toward declaring fidelity — it made the implementation decisions. An independent Coach with fresh context, looking at the design spec alongside the rendered output, provides the objective verification that visual fidelity actually meets the threshold.

### Architecture

**Player Node** (Implementation):
1. Receives DesignContext from orchestrator (elements, constraints, metadata)
2. Delegates to stack-specific UI specialist (react-ui, react-native-ui, maui-ux, flutter-ux)
3. Runs agent-browser to capture screenshots of rendered component
4. Reports output (but does NOT self-validate)

**Coach Node** (Validation):
1. Reads original design requirements independently
2. Reviews generated code against constraint checklist
3. Runs agent-browser independently to capture screenshots
4. Compares actual rendering against design reference image
5. Calculates visual fidelity score
6. Makes decision: APPROVE (≥95% fidelity, zero constraint violations) or FEEDBACK

**LangGraph State Machine**:
```
START → player_node → coach_node → {APPROVE → END, FEEDBACK → player_node}
                                     (max 5 turns)
```

### Quality Gates

Quality gates execute deterministically — they are not left to AI discretion:

- **Visual fidelity**: ≥95% similarity between rendered component and design reference. Below threshold → automatic FEEDBACK.
- **Constraint violations**: Zero tolerance. Any prohibited element (loading states, error states, API integrations, extra props) → automatic FEEDBACK.
- **Turn limit**: Maximum 5 Player-Coach cycles. If not approved by turn 5 → escalate to human review.

### Constraint Enforcement

The prohibition checklist covers 12 categories. By default, the following are prohibited unless explicitly shown in the design:

- Loading states and spinners
- Error states and error boundaries  
- API integrations and data fetching
- Extra props "for flexibility"
- Navigation logic
- State management beyond local component state
- Authentication/authorisation logic
- Analytics tracking
- Accessibility features beyond semantic HTML
- Internationalisation
- Animation (unless in design)
- Responsive breakpoints (unless in design)

---

## 5. Mobile Testing Strategy

### iOS Simulator Testing

iOS Simulator testing is practical today through multiple approaches.

**agent-browser with Appium** is the recommended path. It controls real Mobile Safari in the iOS Simulator, requiring macOS with Xcode. First launch takes 30-60 seconds; subsequent commands are fast. It also supports real iOS devices via USB for production validation.

**InditexTech MCP Server** provides enterprise-scale simulator management using Facebook's IDB (iOS Development Bridge). It can create, configure, and launch simulators programmatically through natural language — useful for testing across multiple device configurations.

### Android Emulator Testing

**Arbigent** is the leading option for AI-driven Android testing. It uses annotated screenshots rather than accessibility trees, making it independent of accessibility service availability. It supports Android, iOS, Web, and even TV interfaces with D-pad navigation.

**AskUI** offers cross-platform natural language testing ("Click the Login button") with visual matching that's less fragile across app updates.

### .NET MAUI Cross-Platform Strategy

MAUI apps require platform-specific testing since they render natively on each platform:

| Platform | Tool | Approach |
|----------|------|----------|
| iOS | agent-browser + iOS Simulator | Mobile Safari for web views, native for XAML |
| Android | Arbigent + Android Emulator | Screenshot-based verification |
| Windows | agent-browser (desktop mode) | Standard browser automation |
| macOS | agent-browser (desktop mode) | Standard browser automation |

**Recommendation**: Start with simulators/emulators for development cycles. Add real device testing only for production validation — the overhead isn't justified during iterative Player-Coach loops.

---

## 6. Technology-Agnostic Orchestrator Design

### Current Problem

The existing orchestrators are hard-coded to specific stacks: `figma-react-orchestrator` generates React components, `zeplin-maui-orchestrator` generates XAML. Adding a new stack (Next.js, Flutter, React Native) would require duplicating the entire orchestrator.

### Refactored Design

The orchestrator becomes stack-agnostic by delegating component generation to parameterised UI specialists:

```
figma-orchestrator (technology-agnostic)
  ├── Phase 0: MCP Verification
  ├── Phase 1: Design Extraction (Figma MCP)
  ├── Phase 2: Boundary Documentation (prohibition checklist)
  ├── Phase 3: Component Generation → delegates to {stack}-ui-specialist
  ├── Phase 4: Visual Verification → agent-browser (Coach validates)
  └── Phase 5: Constraint Validation (orchestrator validates)
```

**Delegation Interface**:

The orchestrator passes a `DesignContext` to the UI specialist containing extracted design elements, the prohibition checklist, and metadata (source, nodeId, fileKey, visual reference). The specialist returns generated files, a visual fidelity score, and any constraint violations.

This separation means adding Flutter support, for example, only requires creating a `flutter-ux-specialist` — the orchestrator, verification loop, and constraint system remain unchanged.

### Supported Specialists

| Specialist | Stack | Output |
|-----------|-------|--------|
| react-ui-specialist | React + Tailwind | TSX + CSS |
| react-native-ui-specialist | React Native | TSX + StyleSheet |
| maui-ux-specialist | .NET MAUI | XAML + C# code-behind |
| flutter-ux-specialist | Flutter | Dart widgets |
| nextjs-ui-specialist | Next.js | TSX + App Router |

---

## 7. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

**Install and validate agent-browser**:
- `npm install -g agent-browser && agent-browser install`
- Test with a simple React component from an existing Figma design
- Measure token usage and compare against Playwright baseline
- Validate iOS Simulator support on Rich's MacBook Pro M2 Max

**Implement TASK-UX-7F1E**: Add `design:URL` parameter to task-create
- Parse Figma/Zeplin/Sketch URLs from command input
- Store in task frontmatter: `design_url`, `design_source`, `design_metadata`
- Auto-detect source and extract file_key/node_id
- Convert node IDs from hyphen to colon format

### Phase 2: Orchestrator Refactoring (Weeks 3-4)

**Implement TASK-UX-2A61**: Refactor to technology-agnostic orchestrators
- Rename `figma-react-orchestrator` → `figma-orchestrator`
- Parameterise delegation to `{stack}-ui-specialist`
- Update the DesignContext interface
- Create equivalent `zeplin-orchestrator`

**Both tasks can run in parallel using Conductor + git worktrees.**

### Phase 3: Player-Coach Integration (Weeks 5-6)

**Wire orchestrators into AutoBuild's LangGraph state machine**:
- Player node: orchestrator + UI specialist + agent-browser screenshot
- Coach node: independent agent-browser verification + fidelity comparison
- Quality gates: ≥95% visual fidelity, zero constraint violations
- Turn limit: 5 cycles maximum

### Phase 4: Mobile Testing (Weeks 7-8)

**Add mobile verification paths**:
- iOS Simulator via agent-browser Appium integration
- Android Emulator via Arbigent
- Cross-platform test matrix for MAUI projects
- Document workflows for each platform

---

## 8. Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Figma MCP token overflow | Blocks extraction | High | Node-specific queries, MAX_MCP_OUTPUT_TOKENS, caching |
| Figma API rate limits | Slows development | Medium | 1-hour cache TTL, retry with backoff, Pro/Enterprise tier |
| agent-browser instability (new tool) | Verification failures | Medium | Hybrid approach with Playwright fallback |
| Visual fidelity comparison accuracy | False positives/negatives | Medium | Tune 95% threshold based on real-world testing |
| iOS Simulator first-launch latency | Slow Player-Coach cycles | Low | Keep simulator running between cycles |
| Node ID format conversion missed | Silent MCP failures | High | Validation in orchestrator Phase 0 |

---

## 9. Key References

### Internal
- `tasks/backlog/design-url-integration/figma-react-orchestrator.md`
- `tasks/backlog/design-url-integration/zeplin-maui-orchestrator.md`
- `tasks/backlog/design-url-integration/TASK-UX-7F1E-add-design-url-parameter.md`
- `tasks/backlog/design-url-integration/TASK-UX-2A61-refactor-figma-react-orchestrator.md`
- `docs/research/ux_implementation/Figma_to_code_px_skill.md`
- `docs/research/autobuild/AutoBuild_Product_Specification.md`

### External
- [Vercel agent-browser](https://github.com/vercel-labs/agent-browser) — AI-optimised browser automation
- [Figma MCP Server](https://developers.figma.com/docs/figma-mcp-server/) — Official Figma Dev Mode MCP
- [Arbigent](https://github.com/takahirom/arbigent) — AI agent for multi-platform mobile testing
- [Firebase App Testing Agent](https://firebase.blog/posts/2025/04/app-testing-agent/) — Gemini-powered mobile test generation
- [InditexTech iOS Simulator MCP](https://github.com/nicklama/mcp-server-simulator) — Enterprise simulator management
