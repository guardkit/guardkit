---
id: TASK-INIT-D4E7
title: Surface pattern-layer file count in guardkit init summary
status: completed
task_type: implementation
created: 2026-04-18T00:00:00Z
updated: 2026-04-18T00:00:00Z
completed: 2026-04-18T00:00:00Z
previous_state: in_review
state_transition_reason: "Task completed — acceptance criteria met, all tests passing"
completed_location: tasks/completed/TASK-INIT-D4E7/
organized_files:
  - TASK-INIT-D4E7.md
priority: high
tags:
  - guardkit-init
  - diagnostic-trail
  - templates
  - pattern-layer
  - follow-up-rev-a925
parent_review: TASK-REV-A925
feature_id: FEAT-A925
implementation_mode: task-work
wave: 1
complexity: 3
---

# Task: Surface pattern-layer file count in `guardkit init` summary

## Description

Add a narrow diagnostic-trail improvement to `guardkit init` output. When
the resolved template has a non-empty `templates/` subdirectory (i.e. ships
a pattern layer), report the count and a pointer so users discover the
two-layer split in the installer's visible surface area, not in a broken
downstream consumer.

This is Recommendation **R2** from
[.claude/reviews/TASK-REV-A925-review-report.md](../../../.claude/reviews/TASK-REV-A925-review-report.md).

## Context

Per the parent review (TASK-REV-A925) F5 finding: `guardkit init` reports
"initialized successfully" without mentioning that the template carries a
pattern-layer with `.template` files that are intentionally not rendered
at init time. This is the root cause of the Forge-init incident the review
investigated — users discover the config/pattern split in the downstream
consumer, with no diagnostic trail at init time.

The architectural decision to keep `init` config-layer-only (TASK-INST-010,
2026-03-02, re-affirmed by TASK-REV-A5F8) is **not** being reversed. This
task adds visibility only.

## Acceptance Criteria

### Functional

- [ ] After the "Applied template" log line and before the "Next steps"
      block in `_cmd_init` summary output, `guardkit init` prints (only
      when the resolved template directory contains a non-empty
      `templates/` subdirectory):
  ```
    Pattern layer: {N} scaffold file(s) present in template (not rendered at init time)
      Tip: these are consumed by AutoBuild / future `guardkit render`;
           see docs/guides/template-two-layer-model.md
  ```
  where `{N}` is `len(list((template_dir / "templates").rglob("*.template")))`
  plus `len(list((template_dir / "templates").rglob("*.j2")))` for the
  weighted-evaluation convention. Count both suffixes.
- [ ] When the template has no `templates/` subdirectory or it is empty,
      NO pattern-layer line is emitted (don't add noise for templates
      without a pattern layer).
- [ ] The line is emitted for the resolved template and any base templates
      in the `extends` chain — count files across the whole chain,
      deduplicated on resolved source path.
- [ ] Docs-guide link in the tip text is the path at
      `docs/guides/template-two-layer-model.md` (produced by TASK-DOC-9F2C).
      If TASK-DOC-9F2C has not yet landed at implementation time, the
      link target may not exist; that is acceptable and expected —
      the tip is forward-referencing.

### Non-Functional

- [ ] Does NOT fail the init command if the `templates/` subdirectory
      is missing or unreadable — this is a best-effort diagnostic, never
      a blocker. Wrap the count computation in a try/except that logs
      at debug level and omits the line on failure.
- [ ] Does NOT change exit codes. `guardkit init` remains exit-0 on
      success regardless of pattern-layer presence.
- [ ] Does NOT render any `.template` files. This is explicitly out of scope.

### Tests

- [ ] Unit test in `tests/unit/cli/test_init.py` (or equivalent) covering:
  - Template with `templates/` subdirectory + `.template` files → line emitted with correct count
  - Template with `templates/` subdirectory + `.j2` files → line emitted with correct count
  - Template with empty `templates/` subdirectory → no line emitted
  - Template with no `templates/` subdirectory → no line emitted
  - Unreadable `templates/` subdirectory → no line emitted, no crash, debug log
- [ ] Existing init tests continue to pass; this change is additive.

## Files

- `guardkit/cli/init.py` (modify `_cmd_init` summary block around line 1592)
- `tests/unit/cli/test_init.py` (add unit tests)

## Implementation Notes

### Pointer to the exact edit location

[guardkit/cli/init.py:1592-1608](../../../guardkit/cli/init.py#L1592) is
the summary block. Insert the pattern-layer line after the graphiti
seeding status (line ~1607) and before `console.print(f"\nNext steps:")`
at line 1608.

### Counting across the extends chain

`apply_template` already resolves the chain via `_resolve_extends_chain`
at line 1070. Expose or re-resolve the chain in `_cmd_init` after
`apply_template` returns, and iterate `_resolve_template_source_dir(name)`
for each link. Dedupe source paths in case two links resolve to the
same cache directory.

### Suggested helper

```python
def _count_pattern_layer_files(template_names: List[str]) -> int:
    """Count .template and .j2 files in each template's `templates/` dir."""
    seen: set[Path] = set()
    count = 0
    for name in template_names:
        tpl_dir = _resolve_template_source_dir(name)
        if tpl_dir is None:
            continue
        patterns_dir = tpl_dir / "templates"
        if not patterns_dir.is_dir():
            continue
        try:
            for suffix in ("*.template", "*.j2"):
                for p in patterns_dir.rglob(suffix):
                    resolved = p.resolve()
                    if resolved not in seen:
                        seen.add(resolved)
                        count += 1
        except OSError as e:
            logger.debug(f"Could not count pattern-layer files in {patterns_dir}: {e}")
    return count
```

## Dependencies

- None at code level.
- Documentation target `docs/guides/template-two-layer-model.md` is
  produced by TASK-DOC-9F2C (Wave 2); forward-reference is acceptable.

## Links

- Parent review: [TASK-REV-A925](../../in_review/TASK-REV-A925-orchestrator-template-scaffold-rendering-gap.md)
- Review report: [.claude/reviews/TASK-REV-A925-review-report.md](../../../.claude/reviews/TASK-REV-A925-review-report.md)
- Recommendation: R2
- Related architectural decision: TASK-INST-010 (config-layer-only init)
- Related review: [TASK-REV-A5F8](../../../.claude/reviews/TASK-REV-A5F8-review-report.md)
