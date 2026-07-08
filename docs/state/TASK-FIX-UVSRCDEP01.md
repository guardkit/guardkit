# TASK-FIX-UVSRCDEP01 — provenance record

**Status:** completed (fleet task; tracking file not originally committed to this repo)

This is a provenance record for a fleet task whose *code* landed in this
repository but whose task-tracking file was never committed here. It exists so
the orchestrator's hardcoded references to `TASK-FIX-UVSRCDEP01` resolve under
the `tests/rules/test_no_dead_task_id_references.py` linter (the references are
real provenance, not a dead/typo'd ID).

## What it was

Made `[tool.uv.sources]` editable-sibling redirects survive the autobuild
environment-bootstrap per-dependency install path, closing the FEAT-HARV
`nats-core` PyPI namespace collision (landed in commit `ff4b63ce`, 2026-06-25).

## Where it is referenced

- [`guardkit/orchestrator/environment_bootstrap.py:349`](../../guardkit/orchestrator/environment_bootstrap.py#L349)
- [`guardkit/orchestrator/environment_bootstrap.py:710`](../../guardkit/orchestrator/environment_bootstrap.py#L710)

## Cross-references

- Design rule: [`.claude/rules/uv-sources-must-survive-every-install-path.md`](../../.claude/rules/uv-sources-must-survive-every-install-path.md)
- Design rule: [`.claude/rules/namespace-hygiene.md`](../../.claude/rules/namespace-hygiene.md)
- Retro: [`docs/retro/autobuild-retro-xref-2026-07-04.md`](../retro/autobuild-retro-xref-2026-07-04.md)
