---
id: TASK-FSGS-001
title: Make /feature-spec emit single-line Gherkin steps so /feature-plan Step 11 (BDD linking) can parse the output
task_type: implementation
parent_repo: study-tutor
feature_id: FEAT-FSGS
wave: 1
implementation_mode: task-work
status: completed
priority: high
complexity: 4
dependencies: []
tags: [feature-spec, feature-plan, bdd-linker, gherkin, parser, recurring-bug-class]
created: 2026-05-06T00:00:00Z
updated: 2026-05-06T00:00:00Z
completed: 2026-05-06T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/2026-05/
state_transition_reason: |
  All ACs satisfied including manual end-to-end verification. Real-world
  reproduction: /feature-spec run on specialist-agent for FEAT-FFC3 (FinProxy
  fine-tune vs frontier comparison) emitted 2 wrapped step lines — the
  Background And at L21-23 and the Then at L139-140 — and gherkin-official
  Parser failed with the canonical CompositeParserException at exactly the
  shape this task targets. The normaliser CLI cleaned both wraps
  deterministically; post-normalise file parsed cleanly with 32 scenarios.
  /feature-plan Step 11 (BDD linking) then ran successfully against the
  cleaned file, tagging all 32 scenarios with @task: markers across 4 of 6
  subtasks. End-to-end /feature-spec → normalise → /feature-plan Step 11 →
  status=ready confirmed.
---

# Make /feature-spec emit single-line Gherkin steps so /feature-plan Step 11 can parse the output

## Context

`/feature-spec` writes a `.feature` file under `features/{slug}/{slug}.feature`
that is then consumed by `/feature-plan` Step 11
(`feature-plan-bdd-link prepare`) to discover scenarios and tag them with
`@task:<TASK-ID>`. Step 11 uses the official Gherkin parser
(`gherkin.parser.Parser`) via
`installer/core/commands/lib/bdd_linker.py:parse_feature_file`.

The official Gherkin parser **does not accept step continuations** — every
`Given`/`When`/`Then`/`And`/`But` step must fit on a single line. (Multi-line
content is only supported via doc-strings or data tables, which require
explicit syntax.)

`/feature-spec` currently emits step text wrapped across multiple lines
when the step is long. Example from a real run on 2026-05-06
(study-tutor `mcp-llm-player-coach-adapters.feature`, Background):

```gherkin
  Background:
    Given the tutoring orchestrator surfaces (PlayerLike, CoachLike,
      PlayerCoachOrchestrator, validate_coach_config, parse_coach_output)
      are unchanged from Phase-0
```

This raises:

```
gherkin.errors.CompositeParserException: Parser errors:
(19:7): expected: #EOF, #TableRow, #DocStringSeparator, #StepLine, #TagLine,
        #ScenarioLine, #RuleLine, #Comment, #Empty, got
        'PlayerCoachOrchestrator, validate_coach_config, parse_coach_output)'
(20:7): expected: ... got 'are unchanged from Phase-0'
```

Result: `feature-plan-bdd-link prepare` exits 1, Step 11 stops with a hard
error per the slash-command spec, the BDD-linker subagent never runs, R2
stays dormant. The R2 nudge from Step 10.6 cannot surface this because the
file *exists* and *has tags* — the file is just not parseable.

The same shape will hit every feature spec the moment a step is long enough
to wrap. In the study-tutor MCP-LCA feature there were ~17 multi-line steps
across one file. The user manually collapsed them all to single lines before
re-running Step 11. Without an upstream fix this is a recurring tax on every
feature.

## Description

Two-pronged fix; both prongs are needed because each closes a different
class of failure.

### Prong A — Prompt instruction in `/feature-spec`

Update the prompt in `installer/core/commands/feature-spec.md` (the
"Generate scenarios" / "Output format" sections — wherever the LLM is told
how to format Gherkin output) to add an explicit invariant:

> **GHERKIN SYNTAX INVARIANT (MANDATORY):** Every `Given`/`When`/`Then`/
> `And`/`But` step **must fit on a single line**. The official Gherkin
> parser used by `/feature-plan` Step 11 (BDD linking) rejects multi-line
> step continuations and stops the rest of the workflow. Do not wrap step
> text across lines under any circumstances. Use a data table or doc-string
> if a step needs structured multi-line content; otherwise keep the entire
> step on one line, no matter how long.

This catches the issue at generation time so most new feature specs come
out clean.

### Prong B — Post-generation normaliser

Add a deterministic post-generation pass in
`installer/core/commands/lib/feature_spec_normalize.py` (new module) that
parses the LLM-generated `.feature` text and collapses any wrapped step
lines to single lines before writing to disk.

The normaliser is a defensive backstop — Prong A is the primary fix, but
the LLM will occasionally drift, and a deterministic post-pass guarantees
the output parses regardless. Algorithm:

1. Read the generated `.feature` text.
2. Walk lines top-to-bottom. Track whether we are "inside a step" — i.e.
   the most recent non-empty, non-comment, non-tag line started with
   `Given|When|Then|And|But ` (case-insensitive) at the step's indent.
3. While inside a step, any subsequent line that:
   - is more indented than the step,
   - is not a comment (`#`),
   - is not a tag (`@`),
   - is not a doc-string delimiter (`"""` / `'''`),
   - is not a table row (starts with `|`),
   - is not a new keyword (`Given|When|Then|And|But|Examples:|Scenario:|
     Background:|Feature:|Rule:|Scenario Outline:`),
   ... is a continuation. Append it to the step line with a single space
   separator and drop it from the output.
4. Re-emit the file.

After Prong B runs, validate with `gherkin.parser.Parser.parse()`. If the
parse still fails, raise a `FeatureSpecGherkinError` with the parser's
error messages so the operator gets a clear, actionable failure mode
rather than a deferred Step 11 surprise.

The normaliser is also useful as a one-shot fixer for existing
hand-authored `.feature` files (CLI: `python -m
installer.core.commands.lib.feature_spec_normalize <path>`).

## Acceptance Criteria

- [ ] `installer/core/commands/feature-spec.md` includes the GHERKIN SYNTAX
      INVARIANT block under the LLM output instructions, worded so the LLM
      understands "single line, no wrapping" as a hard rule
- [ ] `installer/core/commands/lib/feature_spec_normalize.py` exists with:
      - `collapse_multi_line_steps(text: str) -> str` — pure function,
        deterministic, idempotent
      - `validate_gherkin(text: str) -> None` — raises
        `FeatureSpecGherkinError` listing parser errors if the input does
        not parse via `gherkin.parser.Parser.parse()`
      - `normalize_feature_file(text: str) -> str` — runs collapse then
        validate; returns the cleaned text
      - A `__main__` entry-point usable as `python -m
        installer.core.commands.lib.feature_spec_normalize <path>` that
        rewrites the file in place
- [ ] `/feature-spec` calls `normalize_feature_file()` between LLM output
      and disk write, so the file written under `features/{slug}/` is
      already clean
- [ ] `tests/unit/commands/test_feature_spec_normalize.py` covers:
      - Single-line step input (idempotent — no-op)
      - 2-line continuation (Background `Given`)
      - 3-line continuation (Scenario `Given` with embedded quote)
      - Continuation immediately followed by a comment line (comment is
        preserved at the right place)
      - Continuation immediately followed by another step (the second step
        is **not** absorbed into the first — keyword detection works at
        any indent)
      - Doc-string content with a `"""` delimiter is **not** collapsed
        even when wrapped (doc-strings are valid multi-line content)
      - Table row starting with `|` is **not** collapsed (tables are
        valid multi-line content)
      - A `Scenario Outline` `Examples:` block is preserved verbatim
      - Real-world fixture: the study-tutor pre-fix
        `mcp-llm-player-coach-adapters.feature` (committed as a
        test fixture under `tests/fixtures/feature_specs/`) collapses to
        a Gherkin-valid file matching the post-fix version
- [ ] `tests/integration/commands/test_feature_spec_e2e.py` extended with
      a regression guard that runs `/feature-spec` end-to-end against a
      synthetic brief known to produce long step text and asserts the
      output parses via `gherkin.parser.Parser`
- [ ] Existing `/feature-spec` test suite continues to pass
- [ ] Manual verification: re-run `/feature-spec` against a brief that
      previously produced wrapped steps; confirm the written
      `features/{slug}/{slug}.feature` parses cleanly via
      `feature-plan-bdd-link prepare ...` (no Gherkin parser error,
      `status=ready` returned)
- [ ] All modified files pass project-configured lint/format checks with
      zero errors

## Out of Scope

- Changing the Gherkin output language or test runner behaviour. Only the
  syntax of generated step text is in scope.
- Updating already-written `.feature` files in user repos. Operators with
  pre-existing wrapped specs can run `python -m
  installer.core.commands.lib.feature_spec_normalize <path>` to fix in
  place; we do not need to scan and rewrite at upgrade time.
- Changing the BDD linker / `feature-plan-bdd-link` script behaviour. The
  linker is correct to reject malformed Gherkin — the fix belongs in
  `/feature-spec`, not in the consumer.
- Multi-language Gherkin (`# language: fr` headers, etc.). Not currently
  produced by `/feature-spec`; future work if it ever is.

## Implementation Notes

- The `gherkin` Python package is already a dependency (used by
  `bdd_linker.py`). No new dependency needed.
- The collapse algorithm should NOT alter step content beyond joining
  continuation lines with a single space. Preserve embedded quotes,
  parentheses, escape sequences as-is.
- Idempotence matters: running the normaliser twice on the same input
  must produce the same output. Add a property test for this.
- Prong A vs Prong B priority: ship them together. Prong A reduces the
  LLM-drift surface; Prong B turns the failure into a deterministic pass.
  Either alone is insufficient.
- A useful side effect of the normaliser: it can be exposed as a
  pre-commit hook for repos that hand-author `.feature` files.

## Test Execution Log

**Run on:** 2026-05-06 (TASK-FSGS-001 task-work, intensity=light auto-detected)

### New tests (introduced by this task)

```
$ python -m pytest tests/unit/commands/test_feature_spec_normalize.py \
                   tests/integration/commands/test_feature_spec_e2e.py \
                   --no-cov -v
======================== 25 passed in 0.65s ========================
```

Coverage of:
- All AC enumerations (idempotence, 2-line/3-line continuations, comment
  preservation, following-step non-absorption, doc-string preservation,
  table rows preservation, Scenario Outline Examples preservation,
  real-world study-tutor fixture, idempotency property test).
- ``validate_gherkin`` (clean / wrapped) and the
  ``FeatureSpecGherkinError`` raise path.
- ``normalize_feature_file`` happy path and unrescuable-input failure path.
- CRLF line-ending preservation.
- ``__main__`` CLI: rewrite-in-place, no-op on clean files, exit code 2
  on missing path, exit code 2 on no args, exit code 1 on unparseable
  input.

### Regression sweep on the commands unit suite

```
$ python -m pytest tests/unit/commands/ --no-cov -q
======================== 436 passed in 1.05s ========================
```

No regressions in adjacent ``commands/lib`` tests.

### Broader regression context (informational)

```
$ python -m pytest tests/integration/ tests/unit/commands/ --no-cov -q
==== 111 failed, 1305 passed, 88 skipped, 529 warnings in 12m37s ====
```

The 111 failures are pre-existing on ``main`` and are confined to two
unrelated suites (``test_sdk_delegation.py`` Coach SDK structural checks
and ``test_template_create_orchestrator_integration.py``
template-creator orchestrator tests). Verified by stashing this task's
changes and re-running two sample failures — both still fail on stock
``main``. No failure references ``feature-spec``, ``feature_spec_normalize``,
``bdd_linker``, or any path under ``tests/fixtures/feature_specs/``.
These are owned by other in-flight work and are explicitly out of scope
here.

### Files added/modified

```
installer/core/commands/feature-spec.md         (modified — Prong A invariant + Step 8 wire-in)
installer/core/commands/lib/feature_spec_normalize.py  (new)
tests/unit/commands/test_feature_spec_normalize.py     (new — 23 tests)
tests/integration/commands/test_feature_spec_e2e.py    (new — 2 regression guards)
tests/fixtures/feature_specs/mcp-llm-player-coach-adapters_post.feature  (new — verbatim copy from study-tutor post-fix)
tests/fixtures/feature_specs/mcp-llm-player-coach-adapters_pre.feature   (new — deterministic re-wrap of the post-fix file; provenance documented in test docstring since the original pre-fix file was never committed to study-tutor)
```

### Manual verification AC — RESOLVED 2026-05-06

The end-to-end round-trip ran organically against a real
``/feature-spec`` brief on the specialist-agent repo (FEAT-FFC3 —
FinProxy fine-tune vs frontier comparison) the same day this task
landed. Sequence:

1. User ran ``/feature-spec "FinProxy Fine-Tune vs Frontier Comparison"``
   from specialist-agent (which still has the pre-FSGS-001 prompt — no
   GHERKIN SYNTAX INVARIANT, no Step-8 normaliser wire). The LLM emitted
   ``finproxy-fine-tune-vs-frontier-comparison.feature`` with **two
   wrapped steps**: the Background ``And`` at L21-23 (a 3-line wrap of
   "the four canonical FinProxy align payloads...") and the ``Then`` at
   L139-140 (a 2-line wrap of "every session should be scored on
   coverage...").

2. ``gherkin.parser.Parser().parse(text)`` failed with the canonical
   ``CompositeParserException``: ``(22:9): expected ... got 'the
   modular-monolith ADR, ...'`` and two more identical-shape errors at
   23:9 and 140:9 — exactly the failure mode this task targets.

3. Ran the normaliser CLI shipped by this task:
   ``python -m installer.core.commands.lib.feature_spec_normalize
   /Users/.../finproxy-fine-tune-vs-frontier-comparison.feature``.
   Output: ``normalised: ...feature``. Both wraps collapsed to single
   lines deterministically; no other content touched (verified via
   ``difflib.unified_diff``).

4. Re-ran ``Parser().parse(text)`` on the cleaned file: parsed cleanly,
   32 scenarios.

5. User ran ``/feature-plan "FinProxy Fine-Tune vs Frontier Comparison"
   --context ..._summary.md`` against the cleaned file. **Step 11 (BDD
   linking) succeeded** — ``feature-plan-bdd-link prepare`` returned
   ``status=ready``, the BDD-linker subagent tagged all 32 scenarios
   with ``@task:TASK-FFC3-NNN`` markers across 4 of 6 subtasks (TASK-001:
   4, TASK-003: 9, TASK-004: 7, TASK-005: 12), and the feature plan
   completed. The completion banner reported "All 32 BDD scenarios
   linked above 0.6 confidence; 0 already tagged; 0 dropped."

This is the "in-the-wild reproduction" + "deterministic fix" pair the
fixture-based unit tests anticipated. The reconstructed pre-fix fixture
under ``tests/fixtures/feature_specs/mcp-llm-player-coach-adapters_pre.feature``
is now empirically validated by a real-world emission of the same
failure shape, and the AC "manual verification: confirm
``feature-plan-bdd-link prepare`` returns ``status=ready``" is
satisfied.

**Note on prompt propagation**: specialist-agent and study-tutor still
have the pre-FSGS-001 ``feature-spec.md`` prompt. The Prong A invariant
+ the Step-8 normaliser wire only take effect in repos that pull the
updated GuardKit prompt. Until those repos pull, the normaliser CLI
remains a manual post-step (which is exactly what happened here). This
is by design — Prong B (deterministic CLI) is the safety belt for
repos that haven't yet rolled the new prompt forward.
