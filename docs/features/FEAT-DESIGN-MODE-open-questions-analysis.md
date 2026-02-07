# Design Mode Open Questions — Research & Recommendations

**For**: FEAT-DESIGN-MODE-spec.md  
**Date**: 2025-02-07  
**Status**: Ready for review — decisions needed before `/feature-plan`

---

## Question 1: Browser Verification Tooling

**Context**: The Coach needs to render generated components in a browser, capture screenshots, and verify visual fidelity against the design reference. Two main options exist.

### agent-browser (Vercel Labs, Dec 2025)

**Architecture**: Rust CLI for fast command parsing + Node.js daemon managing persistent Playwright instances under the hood. CLI-first — works with any agent that can execute bash.

**Strengths**:
- **5.7× more token-efficient** than Playwright MCP. Six tests consumed ~5.5K characters vs ~31K with Playwright MCP (~1,400 tokens vs ~7,800). Independently verified by Pulumi blog and paddo.dev.
- **Element refs** (@e1, @e2) from accessibility tree snapshots — no CSS selectors, no DOM structure coupling. A button is just `@e9` regardless of class names or DOM restructuring.
- **93% less context overhead**. Compact snapshots fit in hundreds of tokens instead of thousands per page.
- **Zero MCP configuration overhead**. No tool schema definitions taxing the context window when idle. Vercel's own research showed removing 80% of an agent's tools made it 3.5× faster with 100% success rate.
- **Claude Code skill file** available — drop-in integration: `curl -o .claude/skills/agent-browser.md ...`
- Community-built **MCP wrapper** exists (`agent-browser-mcp`) if MCP integration is later needed.

**Weaknesses**:
- **Early stage** — documentation is thin, requires reading source for edge cases.
- **No advanced features** — no network interception, no multi-tab handling, no PDF generation, no sophisticated wait/sync logic.
- **Chromium-only desktop** — no native iOS Simulator or Android Emulator support. Windows has known issues (needs WSL).
- **No mobile testing** path without Appium + Playwright underneath anyway.

### Playwright MCP

**Strengths**:
- **Battle-tested**. Microsoft-backed, extensive documentation, large community, 26+ tools covering full browser automation surface.
- **Advanced capabilities** — network interception, multi-tab, PDF generation, sophisticated synchronisation, video recording.
- **Mobile testing** via Appium integration — iOS Simulator and Android Emulator. Critical for the MAUI pipeline.
- **WebKit support** — can test Safari rendering behaviour, relevant for iOS.

**Weaknesses**:
- **Verbose output drains context**. GitHub issue #889 documented a 6× token increase between versions. Single screenshots consuming 15,000+ tokens. Users exhausted 5-hour token allocations in a few automation steps.
- **CSS selector brittleness** — selectors break when class names or DOM structure change. Generated code is particularly prone to this.
- **Schema overhead** — 26+ tool definitions consume context even when idle.
- **MCP server config complexity** — adds to the already-present Figma/Zeplin MCP setup.

### Analysis for GuardKit

The critical factor is the **Player-Coach adversarial loop**. Each Coach verification cycle costs tokens. With Playwright MCP at ~7,800 tokens/cycle, a 3-cycle verification costs ~23,400 tokens just for browser interaction. With agent-browser, the same loop costs ~4,200 tokens — freeing ~19,200 tokens for the Coach's actual reasoning about design fidelity.

However, the **MAUI pipeline** requires iOS Simulator and Android Emulator testing. agent-browser can't do this. For MAUI platform targets, Playwright + Appium remains the only viable path.

### ✅ Recommendation: agent-browser primary, Playwright fallback for mobile

```
Browser Verification Strategy:
├── React/TypeScript targets → agent-browser (CLI)
│   Token-efficient, sufficient for web component verification
│
├── MAUI web preview → agent-browser
│   Desktop browser preview of MAUI components
│
└── MAUI platform targets → Playwright + Appium (fallback)
    iOS Simulator / Android Emulator verification
    Accept higher token cost for platform-specific testing
```

**Implementation approach**:
- Define a `BrowserVerifier` abstraction: `open(url)`, `screenshot(selector?)`, `getAccessibilityTree()`, `close()`
- Task metadata's target stack determines which implementation is selected
- agent-browser is the default for all web targets
- Playwright activates only for platform-specific testing (MAUI iOS/Android)
- Follows the existing delegation pattern — orchestrator selects the right tool, downstream agents don't need to know which browser tool is being used

**Why not "start with Playwright, migrate later"**: Token efficiency isn't a nice-to-have in the adversarial loop — it directly determines how many verification cycles the Coach can run before context exhaustion. Starting efficient and falling back when necessary is the better architecture.

---

## Question 2: Visual Comparison Method

**Context**: The Coach needs to compare a rendered screenshot against the design reference and produce a fidelity score. The spec requires ≥95% visual fidelity for approval.

### Option A: Pixel-by-Pixel Diff (pixelmatch, odiff)

| Factor | Assessment |
|--------|------------|
| Speed | Milliseconds. Zero LLM token cost. |
| Accuracy | Catches every single pixel difference. |
| False positives | **Very high**. Anti-aliasing, font rendering, sub-pixel rendering, browser/OS variations all trigger failures. A 1px border-radius rendering difference fails the test even when the component looks identical to a human. |
| Best for | Regression testing (same rendering engine comparing against itself). |
| **Fatal flaw** | Design-to-code compares a Figma rendering engine against a browser rendering engine. They will *always* have pixel-level differences even when the component is correct. This makes pixel-diff fundamentally unsuitable as the primary comparison method. |

### Option B: Perceptual Hash (pHash, dHash, aHash)

| Factor | Assessment |
|--------|------------|
| Speed | Sub-millisecond hash comparison. Zero LLM token cost. |
| False positives | Low — tolerant of rendering engine differences. |
| False negatives | **Very high for design fidelity**. Reduces images to 64-256 bit fingerprints. Two images with similar overall structure but different spacing, typography, or colour tokens produce similar hashes. Wrong font-size + wrong padding could score as "matching." |
| Best for | Duplicate detection, near-duplicate finding, content moderation. |
| **Fatal flaw** | Precision far too coarse. Can't distinguish "correct Tailwind spacing" from "close enough." Not designed for fidelity measurement — optimised for "same or different", not "how similar." No spatial information about *where* differences occur. |

### Option C: SSIM — Structural Similarity Index

| Factor | Assessment |
|--------|------------|
| Speed | Fast — milliseconds for typical screenshots via ssim.js. Zero LLM token cost. |
| How it works | Compares luminance, contrast, and structure between images using a sliding window. Returns 0.0–1.0 score. Produces a spatial quality map showing *where* differences occur. |
| Accuracy | Excellent correlation with human perception. Emmy Award (2015), IEEE Best Paper Award (2009), 50,000+ academic citations. |
| False positives | Low-to-moderate. Tolerant of rendering engine differences — anti-aliasing and font smoothing cause only minor score drops. |
| Threshold | Well-studied. SSIM ≥ 0.95 maps directly to the spec's ≥95% visual fidelity requirement. |
| Industry adoption | jest-image-snapshot supports SSIM as comparison method (`comparisonMethod: 'ssim'`). Default SSIM implementation is 'bezkrovny' — optimised for speed with negligible accuracy loss via downsampling. Recommended over pixelmatch for reduced false positives and higher sensitivity to actual changes. |
| Spatial awareness | Produces per-region quality map — valuable for Coach reporting ("differences concentrated in the header area"). |
| Best for | Comparing structurally similar images from different rendering engines — exactly the design-to-code scenario. |

### Option D: AI/VLM-Based Comparison (Claude Vision)

| Factor | Assessment |
|--------|------------|
| Speed | Slowest. API call latency + inference time per comparison. |
| Token cost | **High**. Two images + prompt + response per comparison. Compounds rapidly in iterative verification loops. |
| Accuracy | Potentially highest — can understand semantic intent, detect layout issues, reason about design tokens in context. |
| Determinism | **Non-deterministic**. Same images may get different scores across runs. Conflicts with GuardKit's principle that quality gates must execute deterministically. |
| Best for | Qualitative assessment — catching semantic mismatches that metrics would miss. |
| **Concern** | Too expensive and non-deterministic for a quality gate in an adversarial loop. But extremely valuable for *reasoning* about borderline cases. |

### Analysis for GuardKit

Design-to-code comparison is fundamentally different from regression testing. Pixel-diff is too noisy, perceptual hash too coarse, and AI/VLM too expensive/non-deterministic for a quality gate. SSIM maps directly to the requirement and is the industry standard for structural similarity assessment.

But there's genuine value in AI vision for borderline cases — when SSIM says 0.91, is that because of acceptable rendering engine differences, or because the spacing is actually wrong? That's where the Coach's LLM reasoning adds genuine value.

### ✅ Recommendation: SSIM primary + AI-assisted escalation for borderline cases

```
Visual Comparison Pipeline:
│
├── Tier 1: SSIM Score (deterministic, zero token cost)
│   ├── SSIM ≥ 0.95 → PASS → Coach approves
│   ├── SSIM 0.85–0.94 → ESCALATE to Tier 2
│   └── SSIM < 0.85 → FAIL → Coach rejects, Player must retry
│
└── Tier 2: AI Vision Review (borderline cases only)
    ├── Send both images + SSIM spatial map to Coach's LLM
    ├── Coach reasons about whether differences are acceptable
    │   (rendering engine artefacts vs actual design violations)
    └── Coach makes final determination with explanation
```

**Why tiered**:
- Most comparisons will be clearly pass or clearly fail — SSIM handles these at zero token cost
- The grey zone (0.85–0.94) is where rendering engine differences might cause acceptable SSIM drops — this is where AI judgment adds genuine value
- AI vision is used surgically, not as the default — preserving token budget
- The SSIM spatial map gives the Coach targeted context about *where* differences are, rather than analysing entire images blindly

**Implementation**:
```javascript
// Using jest-image-snapshot patterns
const ssim = require('ssim.js');

// Fast bezkrovny variant (recommended by jest-image-snapshot)
const { mssim, performance_data } = ssim.compare(designRef, rendered, {
  ssim: 'bezkrovny'  // Optimised for speed, negligible accuracy loss
});

if (mssim >= 0.95) {
  return { pass: true, score: mssim, method: 'ssim' };
} else if (mssim >= 0.85) {
  // Borderline — escalate to Coach's AI vision
  const aiReview = await coachVisionReview(designRef, rendered, ssimMap);
  return { pass: aiReview.pass, score: mssim, feedback: aiReview.feedback };
} else {
  return { pass: false, score: mssim, feedback: 'Visual fidelity below threshold' };
}
```

**Important distinction**: Design token validation (correct hex colour, correct spacing value) is handled separately from visual comparison — those are structural checks in the prohibition checklist, not image comparison tasks.

---

## Question 3: Design Iteration Handling

**Context**: If the Figma/Zeplin design changes while a task is in progress or after completion, what happens? The spec currently uses 1-hour cache TTL for MCP extractions.

### Option A: Cache Invalidation + Re-extract (Same Task)

| Factor | Assessment |
|--------|------------|
| UX | Seamless — task continues, adapts to new design. |
| Complexity | **High**. Need change detection, old-vs-new diffing, decide whether code can be patched or must be regenerated, rollback if re-extraction fails mid-task. |
| Risk | Scope creep in disguise. A "design change" could be anything from a colour tweak to a complete restructure. Auto-handling both the same way is dangerous. |
| Change detection | Figma Webhooks V2 support file/project-level events including `DEV_MODE_STATUS_UPDATE`. But requires webhook server infrastructure — over-engineered for a CLI tool. |
| Alignment | **Partial**. GuardKit's task model assumes stable requirements — frozen acceptance criteria at creation. Changing the design mid-task effectively changes the acceptance criteria. |

### Option B: New Task Per Design Iteration

| Factor | Assessment |
|--------|------------|
| UX | More manual — user creates a new task. |
| Complexity | **Low**. No change detection, no diffing, no rollback. |
| Risk | Wasted work if original task hasn't completed yet. |
| Alignment | **Strong**. Consistent with task model — frozen scope, changes are new tasks, clear audit trail. |
| Traceability | Excellent. Each design version has its own task. |

### Option C: State-Aware Hybrid

The right approach depends on where the task is in its lifecycle.

### ✅ Recommendation: State-aware hybrid with human checkpoints

```
Design Change Detection:
│
├── Task in BACKLOG (not yet started)
│   → Silent cache refresh on next task-work
│   → No user action needed — design was never extracted
│
├── Task IN_PROGRESS (Player-Coach loop active)
│   → Pause after current cycle completes
│   → Notify: "Design has changed since extraction"
│   → User decides: continue with current design, or restart
│   → If restart: invalidate cache, re-extract, reset Coach baseline
│
├── Task IN_REVIEW (awaiting human review)
│   → Flag in review notes: "Design updated since implementation"
│   → Reviewer decides: accept, or create follow-up task
│
└── Task COMPLETED
    → New task required
    → Reference original: "Update login form per revised design (supersedes TASK-123)"
    → New extraction reflects current design state
```

**Change detection mechanism** — lightweight, no webhook infrastructure:

```yaml
# In task frontmatter
design_metadata:
  file_key: abc123
  node_id: "2:2"
  extracted_at: "2025-02-07T10:30:00Z"
  extraction_hash: "sha256:abcdef..."  # Hash of extracted design data
```

On each `task-work` invocation:
1. If `extracted_at` older than cache TTL (1 hour), re-query MCP for the node
2. Hash the new extraction
3. If `extraction_hash` differs → design has changed → apply state-aware handling

**Why this fits GuardKit**:
- Respects human-in-the-loop principle at critical decision points
- Doesn't auto-handle ambiguous situations
- Keeps task model clean — completed tasks stay completed
- "Walk before running" — start with notification and human decision, automate later when patterns are clear

**What NOT to build yet**:
- Figma webhook integration (requires server infrastructure)
- Automatic design diffing (which specific elements changed)
- Smart patching (applying only changed design tokens to existing code)

---

## Summary of Decisions

| Question | Decision | Key Rationale |
|----------|----------|---------------|
| **Browser tool** | agent-browser primary, Playwright for mobile | 5.7× token efficiency enables more Coach verification cycles. `BrowserVerifier` abstraction hides implementation. Playwright only for MAUI platform testing. |
| **Visual comparison** | SSIM primary + AI escalation for borderline | Deterministic, zero token cost, maps to ≥95% gate. AI vision reserved for 0.85–0.94 grey zone. Industry standard (jest-image-snapshot). |
| **Design iteration** | State-aware hybrid with human checkpoints | Detection via extraction hash. Backlog → silent refresh. In-progress → pause & notify. Completed → new task. No webhook infrastructure needed. |

## Spec Update Actions

Once approved, these changes to FEAT-DESIGN-MODE-spec.md:

1. **Replace Open Questions section** with Decisions section referencing this analysis
2. **Dependencies** — change "Browser verification tool (agent-browser or Playwright MCP)" to "agent-browser CLI (primary), Playwright MCP (MAUI platform fallback)"
3. **Add to Technical Requirements** — `BrowserVerifier` abstraction interface
4. **Add to Coach Integration** — SSIM tiered pipeline with threshold definitions
5. **Add to Task Frontmatter** — `design_metadata` block with `extraction_hash`
6. **Add to Acceptance Criteria** — state-aware change detection behaviour per task state

Then run `/feature-plan` to decompose into implementation tasks.
