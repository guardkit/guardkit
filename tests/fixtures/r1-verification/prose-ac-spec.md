# Prose-AC fixture — R1 wiring verification

**Purpose:** Force `criteria_classifier.classify_with_warnings()` to emit
`UnverifiableACWarning` instances so we can observe whether the AC linter
post-step fires when `/feature-plan` is invoked.

**Used by:** TASK-FIX-7B2E (verify R1 wiring into `/feature-plan`).

**Expected classifier behaviour per AC (static, from `_MANUAL_PATTERNS` and
the 0.3-confidence `FILE_CONTENT` fallback at `criteria_classifier.py:197`):**
each AC below is deliberately prose-phrased so it cannot match a
`COMMAND_EXECUTION` or strong `FILE_CONTENT` pattern and must therefore
either land in `MANUAL` or the low-confidence fallback — both of which
trip `UNVERIFIABLE_CONFIDENCE_THRESHOLD = 0.6`.

---

## Feature description (invocation payload)

Build a small internal ingestion tool that accepts uploaded CSV files,
writes them to a staging area, emits schema metadata, and exposes a
read endpoint. The tool should be robust to malformed inputs and should
not regress behaviour for existing callers.

## Expected acceptance criteria (prose, unverifiable)

These are the ACs `/feature-plan` should generate from the description —
each one deliberately targets one of the PEX-014..020 bug classes
surfaced in TASK-REV-4D190:

- [ ] **(PEX-014, schema shape)** The emitted schema metadata is correct
      and reflects the source file structure faithfully.
- [ ] **(PEX-015, stub semantic drift)** The staging-area writer behaves
      semantically the same as the production writer, including for
      edge cases not covered by unit tests.
- [ ] **(PEX-016, path validation)** Uploaded file paths are handled
      safely and sanitised appropriately before being written to disk.
- [ ] **(PEX-017, error handling)** The system should handle malformed
      CSV inputs gracefully and surface meaningful errors to the caller.
- [ ] **(PEX-018, backward compatibility)** Backward-compatible defaults
      ensure no breakage for existing callers of the read endpoint.
- [ ] **(PEX-019/020, performance + observability)** Performance is
      reasonable under typical workloads and the tool is observable in
      a manner appropriate to its criticality.

## Why each AC should warn (static prediction)

| # | AC excerpt | Why it should warn |
|---|---|---|
| 1 | "schema metadata is correct …reflects …faithfully" | No file path, no command — prose claim. Falls to MANUAL or 0.3-confidence fallback. |
| 2 | "behaves semantically the same …including for edge cases" | Pure prose; no observable artifact. Classic MANUAL hit. |
| 3 | "handled safely and sanitised appropriately" | "Appropriately" is a weasel — no assertable predicate. |
| 4 | "should handle …gracefully" | Verbatim example from TASK-AC-53445 AC suite; known to warn. |
| 5 | "backward-compatible defaults ensure no breakage" | Verbatim example from TASK-AC-53445 AC suite; known to warn. |
| 6 | "performance is reasonable" / "observable …appropriately" | No threshold, no metric — inherently non-verifiable. |

Per TASK-REV-4D012 R1 acceptance criterion, ≥3 of 6 should fire for the
linter to be considered working. With this fixture, the static prediction
is **all 6 warn** — a wired linter would emit a summary listing all six
under their owning task IDs, preceded by the header from
`feature-plan.md:2299`:

```
AC-quality review: N unverifiable acceptance criteria detected
(warn-mode, non-blocking).
```

## Invocation

See `.claude/reviews/TASK-FIX-7B2E-r1-wiring-verification.md` §"Dynamic
verification repro" for the exact `/feature-plan` invocation and the
grep string to look for in command output.
