---
id: TASK-DM-006
title: "Implement SSIM comparison pipeline"
status: backlog
created: 2026-02-07T10:00:00Z
updated: 2026-02-07T10:00:00Z
priority: high
task_type: feature
parent_review: TASK-REV-D3E0
feature_id: FEAT-D4CE
wave: 3
implementation_mode: task-work
complexity: 5
dependencies:
  - TASK-DM-005
tags: [design-mode, ssim, visual-comparison, quality-gate]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Implement SSIM Comparison Pipeline

## Description

Implement the tiered visual comparison pipeline using SSIM (Structural Similarity Index) as the deterministic primary comparison method, with AI vision escalation for borderline cases. This is the quality gate for visual fidelity in design mode.

## Requirements

1. Create `guardkit/orchestrator/visual_comparator.py`:
   ```python
   class VisualComparator:
       async def compare(self, reference: bytes, rendered: bytes) -> ComparisonResult
   ```

2. Tiered comparison pipeline:
   ```
   Tier 1: SSIM Score (deterministic, zero token cost)
   ├── SSIM >= 0.95 → PASS (Coach approves)
   ├── SSIM 0.85-0.94 → ESCALATE to Tier 2
   └── SSIM < 0.85 → FAIL (Coach rejects, Player retries)

   Tier 2: AI Vision Review (borderline cases only)
   ├── Send both images + SSIM spatial map to Coach's LLM
   ├── Coach reasons about rendering artefacts vs actual violations
   └── Coach makes final determination with explanation
   ```

3. Use `ssim.js` with `bezkrovny` variant (recommended by jest-image-snapshot):
   - Fast computation, negligible accuracy loss
   - Produces spatial quality map showing WHERE differences occur
   - Spatial map passed to Tier 2 for targeted AI reasoning

4. `ComparisonResult` dataclass:
   ```python
   @dataclass
   class ComparisonResult:
       passed: bool
       ssim_score: float          # 0.0-1.0
       method: str                # "ssim" | "ssim+ai_vision"
       tier: int                  # 1 or 2
       feedback: Optional[str]    # Explanation if failed or escalated
       spatial_map: Optional[bytes]  # SSIM spatial diff map
   ```

5. Design token validation (hex colours, spacing values) is separate from visual comparison — handled by prohibition checklist, not this pipeline.

## Acceptance Criteria

- [ ] SSIM comparison using bezkrovny variant via ssim.js
- [ ] Tier 1: >= 0.95 auto-PASS, < 0.85 auto-FAIL
- [ ] Tier 2: 0.85-0.94 escalates to AI vision with spatial map
- [ ] AI vision receives both images + SSIM spatial map for targeted reasoning
- [ ] `ComparisonResult` includes score, method, tier, feedback
- [ ] Spatial map generated for Tier 2 escalation cases
- [ ] Zero token cost for Tier 1 (deterministic computation)
- [ ] Unit tests with synthetic image pairs at each threshold

## Technical Notes

- See FEAT-DESIGN-MODE-spec.md §6 (Visual Comparison Pipeline)
- See open questions analysis §2 for detailed SSIM rationale
- SSIM >= 0.95 maps directly to the >=95% fidelity requirement in the spec
- ssim.js may need Node.js subprocess call from Python — consider sharp/pillow alternatives if pure Python preferred
