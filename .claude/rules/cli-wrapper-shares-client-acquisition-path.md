# CLI wrappers must share the client-acquisition path with the wrapped Python API

> **Source**: Seeded by TASK-FIX-CLI7 (2026-04-25, commit `8fb28093`). Paired
> with the Graphiti design-rule node *"CLI wrappers must share client-acquisition
> path with the wrapped Python API"* under `guardkit__project_decisions`. Sibling
> of [`namespace-hygiene.md`](namespace-hygiene.md) and the Graphiti *"runner
> without producer anti-pattern"* node (uuid `184731b0-3cb6-4eb2-a310-883421767dbf`)
> — both members of the broader class *local design decisions touching an
> externally-defined contract*.

## The rule

When a CLI subcommand wraps a Python API that has its own client-acquisition
path (a factory, registry, thread-local store, or dependency-injection
container), the CLI MUST obtain its client through **the same acquisition path
the API uses internally**. If the CLI builds its own client while the wrapped
API resolves a *different* instance through the factory, the two operate on
different instances of the shared resource: the CLI's own initialise / timeout /
config flags are invisible to the wrapped API, and — when the API is written to
degrade gracefully — the CLI reports success while no write actually lands.

## Why this rule exists

**2026-04-25 — `guardkit graphiti capture-outcome` phantom write (TASK-FIX-CLI7).**
The CLI subcommand wraps the Python API
`guardkit.knowledge.outcome_manager.capture_task_outcome`
([`outcome_manager.py:50`](../../guardkit/knowledge/outcome_manager.py#L50)).

The mechanism that made a "successful" run write nothing:

1. `capture_task_outcome` acquires its client through the shared factory —
   today `get_memory_client()`
   ([`outcome_manager.py:143`](../../guardkit/knowledge/outcome_manager.py#L143));
   at the time of the fix it was `get_graphiti()`, which the fleet-memory
   cutover (TASK-MEM08-004) later swapped for `get_memory_client()`. The
   acquisition path — a factory-managed thread-local store — is the invariant,
   not the specific function name.
2. The v1 CLI acquired its client via its own convenience helper
   `_get_client_and_config()`
   ([`cli/graphiti.py:76`](../../guardkit/cli/graphiti.py#L76)), which builds a
   *fresh* client **outside** the factory's thread-local store.
3. So the factory's thread-local was empty when `capture_task_outcome` ran; the
   factory built a **second**, deferred-connection, never-initialised client.
4. `capture_task_outcome` saw `client.enabled` was false and silently
   early-returned the generated `OUT-XXXXXXXX` id
   ([`outcome_manager.py:149-151`](../../guardkit/knowledge/outcome_manager.py#L149))
   — its docstring calls graceful degradation *a feature*: *"Gracefully degrades
   if Graphiti is unavailable — still returns the generated outcome ID."*
   ([`outcome_manager.py:73-74`](../../guardkit/knowledge/outcome_manager.py#L73)).
5. The CLI mistook that synthetic return value for real-write evidence and
   printed "captured". The CLI's `--timeout 300` had been applied to its own
   (unused) client; the factory client used the default. First dogfood produced
   `OUT-E167C0F5`, and a follow-up search of the `task_outcomes` group returned
   zero CLI7-related facts — a phantom write.

**Fix.** Route the CLI through the same factory acquisition the inner API uses,
so both share one initialised thread-local client. The load-bearing decision is
now a comment in the code, immediately above the acquisition
([`cli/graphiti.py:2244-2251`](../../guardkit/cli/graphiti.py#L2244)):

```python
# IMPORTANT: must NOT call _get_client_and_config() here. That helper
# builds a fresh GraphitiClient outside the factory's thread-local
# store. capture_task_outcome() internally calls get_memory_client() which
# always goes through the factory — so the inner write would land on
# a *different* (uninitialised) client instance and silently no-op,
# while this CLI happily prints "captured" because the Python API
# returns the generated outcome_id even when degraded. Sharing the
# factory client closes that gap.
```

After the fix, `OUT-59EF322F` produced `nodes=6, edges=3, invalidated=0` and was
searchable in `task_outcomes`.

## Symptom

- The CLI prints success (an id, "captured", "written") but a follow-up search
  for the supposedly-written content returns zero hits.
- The misleading success value is a *synthetic* id the wrapped API returns even
  when its inner client check fails — the API treats degraded behaviour as a
  contract, not an error.
- The CLI's own `--timeout` / config flags have no observable effect on the
  wrapped write (they were applied to a client the API never used).

## Detection recipe

```bash
# 1. A CLI helper that builds its own client, used near a call into an API that
#    acquires a client through the factory:
rg -n "_get_client_and_config\(\)" guardkit/cli/ -A 3 | rg -B 3 "capture_task_outcome|get_memory_client|get_graphiti"

# 2. The wrapped API's internal acquisition path (the one the CLI must share):
rg -n "get_memory_client\(\)|get_graphiti\(\)" guardkit/knowledge/outcome_manager.py

# 3. The graceful-degradation early-return that manufactures the phantom success:
rg -n "if not client.enabled|client is None" guardkit/knowledge/outcome_manager.py
```

## Remediation

1. Find the API's internal acquisition function (search the API module for the
   factory / registry / thread-local lookup).
2. Use *that same function* in the CLI to obtain the client. Apply the CLI's
   config (timeout, etc.) to that shared instance, not a fresh one.
3. **Test-mock corollary**: unit tests that patch the *CLI's* convenience helper
   will pass while the integration is broken (CLI7 v1 mocked
   `_get_client_and_config` and got 15/15 green). Regression tests must patch the
   API's acquisition function at **every** import site (CLI and API), and pin
   "uses factory-managed client, not a fresh client".

## Grep-able signature (for next agent)

```bash
# Load-bearing decision comment (MUST match; its absence means the fix regressed):
rg -n "must NOT call _get_client_and_config" guardkit/cli/graphiti.py   # -> 2244

# The shared-factory acquisition the CLI now uses (matches the API's own path):
rg -n "client = get_memory_client\(\)" guardkit/cli/graphiti.py guardkit/knowledge/outcome_manager.py

# Sibling-rule lookup:
rg "cli-wrapper-shares-client-acquisition|namespace-hygiene|runner without producer" .claude/rules/
```

## When this rule triggers

- Adding a CLI subcommand that wraps any function calling `get_memory_client()`,
  `get_graphiti()`, `get_factory()`, or any thread-local / factory / DI lookup.
- Phase 2.5 architectural review for any task that adds a CLI surface over an
  existing Python API.
- Diagnostic sessions investigating a "wrote successfully but the search returns
  nothing" symptom.

## What it does NOT cover

- CLIs that *own* their client end-to-end and never delegate to a
  factory-backed API — there is no second instance to diverge from.
- The specific acquisition function name. The invariant is *share the API's
  path*; that path was `get_graphiti()` at CLI7 time and is `get_memory_client()`
  after the fleet-memory cutover. Match whatever the API resolves internally
  today, not a hardcoded name.
- APIs whose degradation is loud (raise / return a falsy sentinel the CLI
  checks). The hazard is specifically a *synthetic success* value returned on
  the degraded path.
