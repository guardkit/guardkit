# /feature-plan — FEAT-MEM-08 — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /feature-plan FEAT-MEM-08 — 2026-06-28T19:58:11Z

### Prompt

```
/feature-plan FEAT-MEM-08 --context docs/design/specs/memory-cutover/FEAT-MEM-08-guardkit-cutover-feature-brief.md
```

### Assistant response

I'll start by reading the feature brief to understand the scope of FEAT-MEM-08.

This is a substantial cutover feature with a comprehensive brief. Before I orchestrate the plan, I must verify the live integration points actually exist in the codebase (the brief lists specific paths, and inventing paths is the #1 `/feature-plan` defect class). Let me map the real surface.

All brief paths exist on disk, and `fleet_memory_client.py` correctly does not yet exist. Now let me map the actual call-site shapes and the fleet-memory contract before designing tasks. I'll fan out parallel exploration.

Both sibling repos exist with the fleet-memory contract present. Now I'll fan out three parallel Explore agents to map the precise call-site shapes — this drives correct task design.

I now have a complete, verified map of both repos. Let me confirm one contract detail that determines a key design fork — whether fleet-memory's typed payloads reject extra fields (this decides how task-outcome's `lessons`/`approach`/`task_id` are carried).

Key contract detail confirmed: fleet-memory's `BasePayload` uses `extra="ignore"` — so extra fields on `build_outcome` (task_id/lessons/approach) are **silently dropped**, not stored or embedded. That makes the typed-payload field gap a real design fork that also determines whether this feature touches the sibling `fleet-memory` repo.

I have a fully verified map of both repos (write call-sites, GROI read call-sites, the fleet-memory MCP/NATS contract, the `query_logger` evidence hook, and the 9 project + 20 system `group_id` definitions in `_group_defs.py`). The brief already settles most decisions; two genuine forks remain that change the task breakdown, so I'll confirm those before generating the plan.

Both forks resolved:
1. **Extend `build_outcome` (cross-repo)** — W1 includes a fleet-memory-repo task adding optional `task_id`/`lessons`/`approach`; the feature declares `fleet-memory` as an `evidence_repos`.
2. **Split code vs. proof** — each wave splits autobuild code+tests from `operator_handoff` live-proof tasks (soak audit, "prove a real run reads", cutover sign-off).

Let me check the planning tooling available on this box before generating the structure.

All tooling is present: `generate-feature-yaml` supports `--feature-id`/`--feature-slug`/`--discover`, `guardkit feature validate` exists, and FEAT-MEM-08 is unfiled with no conflicting tasks. I'll use the real feature ID `FEAT-MEM-08` and slug `memory-cutover`.

The brief is itself the completed decision analysis and the user supplied a fully-specified feature, so I'll record the decision in a review task for provenance and proceed straight to generating the structure (10 tasks, 8 waves, with the two resolved forks baked in). Let me create the review task and the feature folder.

Now the 10 task files. Starting with W1 — the mapping table (the core design driver, produced first) and the adapter + cross-repo payload extension.

W2 — the dual-write repoint (consumes both the adapter and the extended payload) plus the operator-gated soak audit.

W3 — the GROI reads wiring plus the acceptance-gate operator task ("prove a real run reads").

W4 — CLI commands, the config/docs flip, and the final operator cutover sign-off.

All 10 task files are written. Now the IMPLEMENTATION-GUIDE.md with the mandatory Mermaid diagrams (data flow, integration-contract sequence, task-dependency graph) and the §4 Integration Contracts section.

All 10 task files, the guide, and the README are written. Now generate the structured YAML with the real feature ID `FEAT-MEM-08`, slug `memory-cutover`, and `--discover` to resolve `file_path` from the files on disk.

The YAML is generated with 8 waves. Two follow-ups before validation: (1) the AC linter found **0 unverifiable criteria**; (2) the R3 smoke-gate nudge fired — correctly, I will **not** inject smoke gates because the test paths don't exist yet (they're created by this feature), which would violate the path-verification rule. Let me inspect the YAML, then add the cross-repo `evidence_repos` declaration for TASK-MEM08-003.

The YAML is well-formed (`task_type`/`consumer_context` correctly live in the task-file frontmatter, read by FeatureLoader). Before adding the cross-repo `evidence_repos` declaration, let me confirm FeatureLoader actually supports that key — adding an unknown key would fail schema validation.

`evidence_repos` is an officially supported feature-level field. Let me check the exact format used by FEAT-HARV (the harvest feature, same fleet-memory/nats neighborhood) and mirror it.

`evidence_repos` is a plain path list. Since TASK-MEM08-002/004 import `nats_core`/`fleet_memory` in the worktree venv, let me check guardkit's pyproject extras + `[tool.uv.sources]` so I declare `bootstrap_extras` correctly (this is exactly the uv-sources gotcha from [[env-bootstrap-uvsources-gotcha]]).

Critical bootstrap finding: **fleet-memory is NOT in guardkit's pyproject** (no extra, no `[tool.uv.sources]`), but `nats-core` IS (the `memory` extra → editable `../nats-core`). Per the brief, guardkit talks to fleet-memory via `nats_core.publish_episode` (writes) + the MCP tools (reads/writes) — it should **not** `import fleet_memory`. So `bootstrap_extras: [dev, memory]` (gets nats-core) is the right declaration, and I must steer the adapter task away from a direct `fleet_memory` import. Let me wire both into the YAML and harden TASK-MEM08-002.

Now align the guide's wave table with the canonical computed waves (008 lands in Wave 6 alongside the 007 gate since it only depends on 006) and add the no-`fleet_memory`-import note to the risks.

Now run the pre-flight validation on the feature YAML (Step 8.5).

Validation passes (`✓ Feature FEAT-MEM-08 is valid`) — task_types, file paths, dependencies, and intra-wave conflicts all clean. Final inventory check:
