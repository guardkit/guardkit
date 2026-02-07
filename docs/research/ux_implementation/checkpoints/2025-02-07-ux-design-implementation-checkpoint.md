# UX Design-to-Code Implementation Strategy - Research Checkpoint

> **Purpose**: Recovery checkpoint capturing all research from Claude conversation 2026-02-07.
> **Status**: Complete research, ready for final document generation.
> **Created**: 2026-02-07

---

## 1. Existing Infrastructure

### Orchestrators (tasks/backlog/design-url-integration/)

**figma-react-orchestrator.md**: 6-phase Saga pattern
- Phase 0: MCP Verification
- Phase 1: Design Extraction (via Figma MCP)
- Phase 2: Boundary Documentation (prohibition checklist)
- Phase 3: Component Generation (delegates to UI specialist)
- Phase 4: Visual Regression Testing
- Phase 5: Constraint Validation

**zeplin-maui-orchestrator.md**: Similar pattern for .NET MAUI with XAML generation

### Backlog Tasks
- **TASK-UX-7F1E**: Add design URL parameter to task-create command
- **TASK-UX-2A61**: Refactor figma-react-orchestrator to technology-agnostic figma-orchestrator

### Research Article
**docs/research/ux_implementation/Figma_to_code_px_skill.md**:
- Pix skill for Claude Code: Figma MCP → React with autonomous visual comparison loop
- Extracts design tokens (colors, typography, spacing)
- Visual comparison: screenshot rendered component → compare against Figma → auto-fix

---

## 2. Critical Issues

### Figma MCP Token Limits
- MCP responses can exceed context windows (351,378 tokens vs 25,000 limit)
- Solution: Set MAX_MCP_OUTPUT_TOKENS environment variable
- Extract only necessary nodes (use node-id parameter)
- Cache MCP responses (1-hour TTL)
- Implement retry logic with exponential backoff for 429 errors
- Figma API rate limits: 6/month for Starter, higher for Pro/Enterprise

### Node ID Format Conversion (Primary cause of MCP failures)
- Figma URLs use hyphen format: `node-id=2-2`
- MCP API requires colon format: `"2:2"`
- Must convert before MCP calls: `nodeId.replace("-", ":")`

---

## 3. Browser Verification Options

### Option 1: Playwright MCP (Previous Approach)
- Used in uk-probate-agent project
- Pros: Mature, full browser automation
- Cons: Verbose snapshots (~31K chars), CSS selector brittleness

### Option 2: Vercel agent-browser (Recommended)
- Released December 2025, designed for AI agents
- **5.7x more token-efficient** than Playwright (~5.5K vs ~31K chars)
- Element refs (@e1, @e2) instead of CSS selectors (more stable)
- Compact accessibility tree snapshots
- **iOS Simulator support** via Appium
- Core workflow: `agent-browser open`, `snapshot -i`, `click @e1`, `screenshot`
- iOS: `agent-browser -p ios --device "iPhone 16 Pro" open <url>`

### Option 3: Hybrid
agent-browser for verification loop, Playwright for complex E2E scenarios.

---

## 4. Mobile App Testing

### iOS Simulators (Practical: Yes)
- **agent-browser**: Controls real Mobile Safari in iOS Simulator, requires macOS + Xcode
- **InditexTech MCP Server**: Enterprise-scale, uses Facebook's IDB, autonomous management
- **Firebase App Testing Agent**: Gemini-powered, natural language test goals

### Android Emulators (Practical: Yes)
- **Arbigent**: AI agent for Android, iOS, Web, TV testing. Accessibility-independent.
- **AskUI**: Cross-platform natural language test steps

### .NET MAUI Considerations
- Platform-specific testing required (iOS Sim, Android Emu, Windows/macOS desktop)
- agent-browser handles web and iOS Simulator
- Arbigent or similar needed for Android

---

## 5. AutoBuild Player-Coach Integration

### Architecture
- Player implements, Coach validates independently
- Fresh LLM instances each turn prevent context pollution
- Only Coach can approve completion (prevents "false completion")
- LangGraph state machine with turn limits

### Verification Flow
1. Player generates component from design
2. Player captures screenshot via agent-browser
3. Coach independently runs agent-browser tests
4. Coach compares screenshots with design reference
5. Coach validates constraint adherence (12 prohibition categories)
6. Coach decides: APPROVE (≥95% visual fidelity, zero violations) or FEEDBACK

### Constraint Enforcement (Zero Scope Creep)
```typescript
interface ProhibitionChecklist {
  loading_states: boolean;           // Default: prohibited
  error_states: boolean;             // Default: prohibited
  api_integrations: boolean;         // Always prohibited
  extra_props_for_flexibility: boolean; // Always prohibited
  // ... 12 categories total
}
```

---

## 6. Recommended Architecture

### Phase 1: Design Extraction
- Figma: Use node-specific MCP calls with retry logic
- Zeplin: Parallel MCP calls for colors, text styles, screen data
- Always convert node IDs from hyphen to colon format

### Phase 2: Component Generation (Player Agent)
- Delegates to stack-specific UI specialist (react-ui, react-native-ui, maui-ux, flutter-ux)
- Passes DesignContext interface with elements, constraints, metadata

### Phase 3: Verification (Coach Agent)
- agent-browser for screenshots and interaction testing
- Visual fidelity comparison (≥95% threshold)
- Constraint violation check (zero tolerance)

### Phase 4: Coach Validation
- Independent verification (doesn't trust Player's claims)
- Quality gates execute deterministically

---

## 7. Implementation Recommendations

1. **Use agent-browser for verification** - 5.7x token efficiency enables more Player-Coach cycles
2. **Integrate with AutoBuild Player-Coach** - LangGraph state machine
3. **Handle token limits proactively** - node-specific queries, caching, retry logic
4. **Mobile testing strategy** - Start with simulators, add real devices for production
5. **Refactor orchestrators** - Technology-agnostic, parameterized by stack

---

## 8. Action Items

### COMPLETED
- ✅ Figma orchestrator with 6-phase Saga pattern
- ✅ Zeplin orchestrator with platform-specific testing
- ✅ Constraint validation (12 prohibition categories)
- ✅ MCP integration patterns (retry, error handling)

### PENDING
- [ ] Refactor orchestrators to be technology-agnostic (TASK-UX-2A61)
- [ ] Integrate agent-browser for verification (replace Playwright)
- [ ] Implement Player-Coach loop with LangGraph
- [ ] Add visual fidelity comparison (≥95% threshold)
- [ ] Test iOS Simulator integration with agent-browser
- [ ] Test Android Emulator integration (Arbigent or agent-browser)
- [ ] Update task-create for design:URL parameter (TASK-UX-7F1E)
- [ ] Document mobile testing workflows

### NEXT STEPS
1. Install agent-browser: `npm install -g agent-browser`
2. Test with simple React component from Figma design
3. Measure token usage vs. Playwright
4. Prototype Player-Coach loop with agent-browser verification
5. Test iOS Simulator support on macOS

---

## 9. Key References

### Project Files
- `tasks/backlog/design-url-integration/figma-react-orchestrator.md`
- `tasks/backlog/design-url-integration/zeplin-maui-orchestrator.md`
- `docs/research/ux_implementation/Figma_to_code_px_skill.md`
- `docs/research/autobuild/AutoBuild_Product_Specification.md`

### External
- Vercel agent-browser: https://github.com/vercel-labs/agent-browser
- Figma MCP: https://developers.figma.com/docs/figma-mcp-server/
- Arbigent: https://github.com/takahirom/arbigent
- Firebase App Testing Agent: https://firebase.blog/posts/2025/04/app-testing-agent/
- InditexTech iOS Simulator MCP: https://github.com/nicklama/mcp-server-simulator
