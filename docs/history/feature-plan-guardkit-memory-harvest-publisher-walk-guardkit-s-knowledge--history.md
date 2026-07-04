# /feature-plan — guardkit-memory-harvest-publisher-walk-guardkit-s-knowledge- — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /feature-plan guardkit-memory-harvest-publisher-walk-guardkit-s-knowledge- — 2026-06-25T14:24:10Z

### Prompt

```
/feature-plan "Guardkit memory harvest publisher: walk guardkit's knowledge artifacts and publish each
as a canonical MemoryEpisodeV1 onto the NATS MEMORY stream via nats_core.NATSClient.publish_episode().
project_id='guardkit'; episode_type per source (adr / feature_outcome / review_report / document);
content_format markdown|text for prose docs (the relay chunks + embeds them), json for structured
payloads. episode_id is a DETERMINISTIC hash of the artifact's natural key so re-harvest is idempotent
(JetStream dedupes on Nats-Msg-Id=episode_id). Connect as the dedicated 'guardkit' NATS user (already
provisioned; password in nats-infrastructure/.env GUARDKIT_NATS_PASSWORD) which has publish rights on
memory.episode.> (the fleet-memory user is consumer-only and cannot publish). Idempotent + resumable:
safe to run repeatedly. Tests: subject resolves to
memory.episode.guardkit.{episode_type}; episode_id stable across runs; >900KB body rejected with an
actionable error; dry-run mode lists what would publish without connecting." --context docs/design/specs/memory-publisher/P4-harvest-publisher-feature-brief.md
```

### Assistant response

I'll start by reading the context brief and checking for any existing related tasks/features, since the recent git history shows substantial memory-publisher work already.

Brief is comprehensive and no prior feature/tasks exist. Before planning, I need to ground the plan in guardkit's actual structure (the feature-plan classification guide warns hard against invented paths). Let me explore the real doc taxonomy, CLI structure, and the sibling-repo references.

Key findings: guardkit has a Click/argparse CLI in `guardkit/cli/` (subcommands registered via `main.py`), and **`nats_core` is NOT installed in guardkit's env — it's sibling repo `../nats-core`**. That dependency wiring is a real planning concern. Let me verify the CLI registration pattern and the actual `nats_core` contract (the brief is human-written and could drift from code).

Contract confirmed against real code. Let me look at the reference publisher impl and the `publish_episode` body (the 900KB guard + subject resolution) so the plan mirrors what exists.

Let me check how guardkit is expected to pull in `nats-core` (there's a comment near line 105) — the dependency wiring is the main integration risk.

I now have solid grounding. Key facts confirmed against real code:
- **CLI**: Click-based, subcommands in `guardkit/cli/` registered in `main.py` via `cli.add_command()`.
- **`nats_core` contract** (verified): `NATSConfig(url, user, password: SecretStr, name)` → `connect()` / `publish_episode(episode)` / `disconnect()`; `publish_episode` resolves `memory.episode.{project_id}.{episode_type}`, sets `Nats-Msg-Id` header, raises `ValueError` if >900KB.
- **Idempotency pattern to mirror**: `fleet-memory`'s `_derive_episode_id` = `f"ep-{sha256(natural_key).hex()[:16]}"`.
- **Dependency wiring**: `nats-core` is **not installed** — it's sibling `../nats-core` (pkg `nats-core` v0.4.0); guardkit pulls siblings via `[tool.uv.sources]` editable paths (the guardkitfactory pattern).
- **Doc taxonomy is large** (50+ `docs/*` dirs) — the brief itself says "confirm against the real doc taxonomy."

A few genuine scoping decisions will materially change the plan. Let me confirm them before generating tasks.

All four answered with the recommended options: curated config-driven scope, new `guardkit memory` group, skip+report for oversized, and an `operator_handoff` task for the live GB10 run.

Let me check the generation tooling and existing file conventions so the artifacts I produce match this repo.

The bin script accepts `--feature-id` (so I can fix IDs upfront) and the repo's task frontmatter uses `depends_on:` + `parent_review`/`feature_id`/`wave`. Let me do one final grounding check — confirm the curated harvest dirs actually contain content — then build the plan.

Critical confirmation: **oversized docs exist today** — 8+ docs over 880KB (two `reseed_guardkit_*.md` files exceed 2MB). So the skip+report path fires on the very first run; it's a real, testable case, not hypothetical. 456 curated docs total (331 in `docs/reviews`).

I have everything needed. Let me build the feature plan. Setting up tracking and creating the folder:

Now creating the task files (7 tasks + a planning record):

Now the 7 task files:

Now the IMPLEMENTATION-GUIDE.md (with the mandatory Mermaid diagrams + §4 Integration Contracts) and README.md:

All 10 artifacts created. Now generating the structured `FEAT-HARV.yaml` for AutoBuild (`--discover` resolves task file paths from disk):

The YAML generated cleanly (AC-quality review: 0 unverifiable). The script's dependency-derived waves put TASK-HARV-006 and 007 both in Wave 4 (both depend only on 005). But logically the live GB10 run (007) should follow the acceptance suite (006) being green — let me make that an explicit edge so the wave ordering is correct, then regenerate.

Feature validates: `✓ Feature FEAT-HARV is valid`. Let me confirm the final wave structure and task_type frontmatter are all correct:

Final structure is correct and the feature validates. Waves: `1:[001,002] → 2:[003,004] → 3:[005] → 4:[006] → 5:[007]`, all `task_type`s set.

One real pre-build risk I want to harden against: `nats_core` is currently **not importable** in the active env, and a Player that merely edits `pyproject.toml` won't materialise the editable install — so Wave 2's `import nats_core` could fail at test collection. Let me make that install step explicit in TASK-HARV-001:
