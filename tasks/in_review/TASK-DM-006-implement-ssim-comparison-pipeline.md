---
complexity: 5
created: 2026-02-07 10:00:00+00:00
dependencies:
- TASK-DM-005
feature_id: FEAT-D4CE
id: TASK-DM-006
implementation_mode: task-work
parent_review: TASK-REV-D3E0
priority: high
status: in_review
tags:
- design-mode
- ssim
- visual-comparison
- quality-gate
task_type: feature
test_results:
  coverage: 83
  last_run: 2026-02-08T12:30:00+00:00
  status: passed
  tests_passed: 60
  tests_total: 60
title: Implement SSIM comparison pipeline
updated: 2026-02-07 10:00:00+00:00
wave: 3
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

- [x] SSIM comparison using bezkrovny variant via scikit-image (Python equivalent)
- [x] Tier 1: >= 0.95 auto-PASS, < 0.85 auto-FAIL
- [x] Tier 2: 0.85-0.94 escalates to AI vision with spatial map
- [x] AI vision receives both images + SSIM spatial map for targeted reasoning
- [x] `ComparisonResult` includes score, method, tier, feedback
- [x] Spatial map generated for Tier 2 escalation cases
- [x] Zero token cost for Tier 1 (deterministic computation)
- [x] Unit tests with synthetic image pairs at each threshold (60 tests, 83% coverage)

## Technical Notes

- See FEAT-DESIGN-MODE-spec.md §6 (Visual Comparison Pipeline)
- See open questions analysis §2 for detailed SSIM rationale
- SSIM >= 0.95 maps directly to the >=95% fidelity requirement in the spec
- ssim.js may need Node.js subprocess call from Python — consider sharp/pillow alternatives if pure Python preferred