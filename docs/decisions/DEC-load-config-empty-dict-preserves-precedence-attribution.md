# DEC — `_load_config` returns `{}` (not `_DEFAULT_CONFIG`) so precedence attribution stays authoritative

**Status:** ACCEPTED (implemented) · **Date:** 2026-04-18 · **Task:** TASK-LCL-006 · **Commit:** `dbc47bc51`

## Context

The langchain-deepagents-orchestrator template hard-codes its fallback model
identifiers in `_DEFAULT_CONFIG` (`anthropic:claude-sonnet-4-6`,
`anthropic:claude-haiku-4-5`). TASK-LCL-006 (FEAT-LTL1 Wave 2, from the
TASK-REV-LES1 review) added an env-var override layer with the LES1 §3 PMEV
precedence chain **env > yaml > hardcoded default** (`AGENT_MODELS__REASONING_MODEL`,
`AGENT_MODELS__IMPLEMENTATION_MODEL`), and required an INFO log
`Resolved X=Y (source=env|yaml|default)` so an operator can see which layer won.

Before the change, `_load_config` backfilled defaults on any failure path — every
missing-file / `YAMLError` / `OSError` / malformed-structure branch returned
`dict(_DEFAULT_CONFIG)`, and the success path merged
`{**_DEFAULT_CONFIG["orchestrator"], **orch}`. With defaults already merged into the
config dict, the downstream resolver could no longer tell a *yaml-provided* value
apart from a *fell-through-to-default* value: both arrived as a populated
`config["orchestrator"]` entry, so the required `source=yaml` log would fire for
both — mis-attributing the winning layer whenever yaml was absent or malformed.

## Decision

Refactor `_load_config` to return `{}` on every degraded input (missing file,
`yaml.YAMLError`/`OSError`, non-dict top level, non-mapping `orchestrator` key)
instead of `dict(_DEFAULT_CONFIG)`, and drop the success-path
`_DEFAULT_CONFIG`-merge. All defaulting moves into the `_resolve_model` helper,
which is the single authoritative site for the three-layer
`env > yaml > default` precedence and its INFO log.

Additionally, resolve the env layer with a **falsy check** on
`os.environ.get(env_var)` (`if env_val:`) rather than a sentinel default — so an
explicitly-emptied variable (`AGENT_MODELS__REASONING_MODEL=`) is treated as
"unset" and falls through to yaml rather than clobbering it. This is the
empty-string edge case called out in the task acceptance criteria.

## Rationale

Pushing defaulting down into `_resolve_model` makes the precedence attribution
correct: with `_load_config` returning `{}` when yaml is missing/malformed,
`config.get("orchestrator")` yields an empty mapping, `_resolve_model` sees a falsy
yaml value, and it logs `source=default` — which is the truth. Had `_load_config`
kept backfilling defaults, the resolver would have seen a populated yaml value and
logged the misleading `source=yaml`. The alternative (leave the backfill in
`_load_config` and try to re-derive provenance in `_resolve_model`) would split the
precedence logic across two functions and require `_resolve_model` to know which
of its inputs were synthetic — reintroducing exactly the ambiguity the change
removes.

The falsy env check (over `os.environ.get(env_var, default)`) is deliberate for
the same attribution reason: an empty string is operator intent to defer, not a
model identifier, so it must fall through rather than win as `source=env`.

## Consequences / Implementation

In `installer/core/templates/langchain-deepagents-orchestrator/templates/other/other/agent.py.template`:

- **`_load_config`** (`:60`) — returns `{}` at every degraded branch
  (`FileNotFoundError` `:85`, `yaml.YAMLError`/`OSError` `:92`, non-dict top level
  `:99`), and strips a non-mapping `orchestrator` key rather than merging defaults.
  Its docstring (`:66-68`) states the rationale: returning `{}` keeps "yaml
  provided" and "fell through to hardcoded default" distinguishable in the INFO log.
- **`_resolve_model`** (`:138`) — the authoritative precedence + attribution site:
  `env_val = os.environ.get(env_var)` then `if env_val:` (`:162-163`) logs
  `source=env`; `if yaml_value:` (`:166`) logs `source=yaml`; the fall-through
  (`:169`) logs `source=default`. Falsy values at env/yaml fall through.
- **`_build_agent`** (`:173`) — resolves both `reasoning_model` and
  `implementation_model` through `_resolve_model` (`:194`, `:200`), passing
  `_DEFAULT_CONFIG["orchestrator"]` values as the last-resort `default_value` — so
  the sole `_DEFAULT_CONFIG` consumption is now the explicit default argument, not a
  `.get()` backfill.
- The `orchestrator-config.yaml.template` header (`:9-20`) documents the precedence,
  names the env vars, and describes the empty-string fall-through contract.

## References

- **Task:** `tasks/completed/TASK-LCL-006/TASK-LCL-006.md`
- **Commit:** `dbc47bc5157392496ccf0ee55961bad19032f0f3` — "Apply lessons learned
  from the specialist agent to the templates" (added the task file and the template
  refactor together)
- **Review:** `.claude/reviews/TASK-REV-LES1-review-report.md` (§HIGH-3, §LOW-2 —
  the PMEV/CRMV provider-resolution finding this task closed)
