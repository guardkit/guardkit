# P4 — Guardkit Harvest Publisher (feature brief)

**Date:** 2026-06-25
**Status:** Ready for `/feature-plan` (run from this repo, guardkit). Pass this file via `--context`.
**Repo:** guardkit (owns the harvest — the *first* real publisher onto the memory write path).
**Part of:** the post-Graphiti memory write path. Authoritative spec:
`nats-infrastructure/docs/design/specs/memory-relay/memory-write-path-v2-post-graphiti.md`.
Upstream: P1 publisher helper (`nats-core`), P2 stream (`nats-infrastructure`), P3 relay (`fleet-memory`)
— all built, **live on the GB10, and verified end-to-end** (RLY-007 G1/G3/G4 all green, 2026-06-25).

## Why this is next

The relay (FEAT-MEM-04, consumer) is live and **waiting for messages** on `memory.episode.>`, but nothing
publishes real episodes yet. P4 is "run the harvest on the GB10": collect guardkit's knowledge artifacts
(ADRs, feature outcomes, review reports, design docs) and publish each as a `MemoryEpisodeV1` via the
`nats_core` publisher helper. Once this lands, episodes flow straight through to the live NAS Postgres
store, unblocking FEAT-MEM-07 (re-index) → FEAT-MEM-05 (parity eval vs the Graphiti baseline) → cutover.

## `/feature-plan` input

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

## Scope

- **Harvest walker** — enumerate guardkit's knowledge artifacts and map each to an `episode_type`
  (suggested mapping below; `/feature-plan` should confirm against the real doc taxonomy).
- **Publish via the canonical helper** — `nats_core.NATSClient.publish_episode(MemoryEpisodeV1(...))`.
  Do **not** hand-roll NATS publishing; the helper owns subject resolution, the `Nats-Msg-Id` header,
  and the 900 KB guard. (A working reference for building + publishing the envelope is
  `fleet-memory/src/fleet_memory/reindex/publisher.py`, which publishes `content_format="json"` payloads.)
- **Deterministic episode_id** — hash the artifact's natural key (e.g. `sha256(repo:path:kind)` →
  `ep-…`), exactly as the re-index publisher does, so re-running the harvest overwrites in place rather
  than duplicating (idempotency layer at the publish boundary + the relay's content-hash/uuid5 layers).
- **Dry-run / resumable** — a `--dry-run` that reports the episodes it would publish (counts per type)
  without connecting; safe to re-run after partial failures.
- **CLI/command** — a guardkit command/entry point to run the harvest (and wire it into whatever
  scheduler/runbook "run the harvest on the GB10" implies).

## The publisher contract (verified live, 2026-06-25)

From `nats-core` (`src/nats_core/client.py`, `events/_memory.py`, `config.py`):

```python
from nats_core import NATSClient
from nats_core.config import NATSConfig
from nats_core.events import MemoryEpisodeV1
from pydantic import SecretStr

cfg = NATSConfig(url="nats://127.0.0.1:4222", user="<publisher-user>",
                 password=SecretStr("<pw>"), name="guardkit-harvest")
client = NATSClient(cfg, source_id="guardkit-harvest")
await client.connect()                 # uses cfg; connect() takes NO url arg
await client.publish_episode(episode)  # one MemoryEpisodeV1
await client.disconnect()              # NOT .close()
```

- **Subject:** `memory.episode.{project_id}.{episode_type}` (resolved by the helper).
- **Header:** `Nats-Msg-Id = episode_id` → JetStream server-side dedupe.
- **Body:** raw `MemoryEpisodeV1` JSON (the helper bypasses `MessageEnvelope`). **Rejected if > 900 KB**
  (`MAX_EPISODE_BODY_BYTES = 900*1024`) — large docs must be split upstream or chunked into multiple
  episodes.

### `MemoryEpisodeV1` fields

- **Required:** `episode_id`, `project_id`, `episode_type` (NATS-safe id, pattern
  `^[a-zA-Z0-9][a-zA-Z0-9\-_]*$`), `content_format` (`json|markdown|text`), `body`.
- **Optional:** `payload_type` (registry key, json path only), `source_ref` (e.g. commit SHA / path),
  `name`, `source`, `occurred_at`, `published_at`, `ingest_hints`.
  The relay now **captures + persists** `episode_type` and all of these (fixed 2026-06-25), so populate
  `name`/`source`/`source_ref`/`occurred_at` — they survive to Postgres and aid the parity eval.

## Suggested episode_type → source mapping (confirm in planning)

| `episode_type`    | guardkit source (examples)                                   | `content_format` |
|-------------------|--------------------------------------------------------------|------------------|
| `adr`             | `docs/adr/`, `docs/adrs/`, `docs/decisions/`                 | `markdown`       |
| `review_report`   | `docs/reviews/`, `docs/code-review/`                         | `markdown`       |
| `feature_outcome` | `docs/completion-reports/`, FEAT-* outcomes, `docs/retro/`   | `markdown`       |
| `document`        | general prose: `docs/guides/`, `docs/reference/`, `docs/design/`, … (catch-all) | `markdown`/`text` |

Prose (`markdown`/`text`) routes through the relay's heading-aware chunker → embed → store. Use `json`
+ `payload_type` only for structured records that match a `fleet_memory` payload-registry type.

## Publisher NATS identity — DONE (provisioned + verified live, 2026-06-25)

The dedicated **`guardkit`** APPMILLA user is provisioned (`nats-infrastructure` commit `5c3b8df`) and
live on the GB10 broker. The harvest just connects as it — no further infra change needed.

- **Identity:** user `guardkit`, password in `nats-infrastructure/.env` as `GUARDKIT_NATS_PASSWORD`
  (gitignored, GB10-local). Connect: `NATSConfig(url="nats://127.0.0.1:4222", user="guardkit",
  password=SecretStr(<GUARDKIT_NATS_PASSWORD>), name="guardkit-harvest")`.
- **Least privilege (publisher):** `publish memory.episode.>` + `subscribe _INBOX.>` (for PubAcks).
  Deliberately **no `$JS.>`** (no JetStream admin — cannot create/purge streams or consumers) and
  **no subscribe on `memory.episode.>`** (it does not consume — that is the relay's job).
- **Verified end-to-end:** publishing via `nats_core.publish_episode` as `guardkit` lands a row in the
  live Postgres store (G1) and a hyphenated `project_id` correctly parks on `memory.dlq.*` (G3).

> The harvest's only remaining job re: identity is to **read `GUARDKIT_NATS_PASSWORD`** (from the
> nats-infrastructure `.env`, an injected secret, or wherever guardkit keeps its NATS creds) and build the
> `NATSConfig` above. `/feature-plan` should NOT re-plan the broker user — it exists.

## Hard constraints (the relay enforces these — getting them wrong = poison/DLQ)

- **`project_id` must be a valid namespace identifier — underscores, NOT hyphens.** The relay validates
  the storage namespace and **terminates + DLQs** anything hyphenated (this is exactly the G3 poison
  case: `project_id="bad-proj"` → `memory.dlq.bad-proj`). `project_id="guardkit"` is fine.
- **`episode_type` must match** `^[a-zA-Z0-9][a-zA-Z0-9\-_]*$` (it's a NATS subject segment).
- **Empty/whitespace `body`** is acked with zero chunks (the G4 case) — harmless, but filter empties to
  avoid noise.
- **Idempotency** holds only if `episode_id` is deterministic; a random id per run re-stores everything.

## Live environment (already running on the GB10, 2026-06-25)

- Broker `ships-computer-nats` (healthy), `MEMORY` stream (`memory.episode.>` + `memory.dlq.>`, limits,
  365d). Relay `fleet-memory-relay` container (`restart: unless-stopped`, `deploy/relay/` in fleet-memory)
  bound to durable pull consumer `fleet-memory-relay`.
- Postgres+pgvector at `whitestocks.tailebf801.ts.net:5433/fleet_memory` (creds in
  `fleet-memory/deploy/nas/.env.deploy`). Embed service at `http://promaxgb10-41b1:9000`.

### Verify a harvest run (G1-style)

After publishing, confirm rows landed:
```sql
select value->>'episode_type', value->>'episode_id', left(value->>'content',60)
from store where prefix like 'fleet_memory.guardkit%' order by updated_at desc limit 20;
```
and that embeddings were written (`store_vectors` join). Poison/DLQ shows up under
`nats stream subjects MEMORY 'memory.dlq.>'`.

## Downstream chain (after the harvest publishes)

**P4 (this) → FEAT-MEM-07** re-index into the live NAS Postgres → **FEAT-MEM-05** probe-set parity eval
vs the Graphiti baseline → go/no-go → **FEAT-MEM-08** cutover → **FEAT-MEM-09** Graphiti decommission.

## References

- Publisher helper + schema: `nats-core/src/nats_core/{client.py,config.py,events/_memory.py}`;
  brief `nats-core/docs/design/specs/memory-publisher/P1-memory-publisher-feature-brief.md`.
- Reference publisher impl: `fleet-memory/src/fleet_memory/reindex/publisher.py`.
- Relay contract: `fleet-memory/docs/decisions/MEM-04-relay-jetstream-contract.md`;
  authoritative design `nats-infrastructure/docs/design/specs/memory-relay/memory-write-path-v2-post-graphiti.md`.
- Deploy state + the original handoff: `fleet-memory/docs/handoffs/HANDOFF-2026-06-25-memory-write-path-gb10.md`.
- NATS user pattern to mirror: `nats-infrastructure/config/accounts/accounts.conf.template` (the
  `fleet-memory` / `forge` users).
