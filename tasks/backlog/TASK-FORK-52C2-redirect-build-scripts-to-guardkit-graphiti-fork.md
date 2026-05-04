---
id: TASK-FORK-52C2
title: Redirect graphiti build/setup scripts to guardkit/graphiti fork
status: backlog
created: 2026-05-03T00:00:00Z
updated: 2026-05-03T00:00:00Z
priority: high
task_type: infrastructure
complexity: 4
estimated_minutes: 90
execution_location: promaxgb10-41b1
tags: [graphiti, fork, infra, mcp, scripts]
depends_on: [TASK-FORK-PATCH]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Redirect graphiti build/setup scripts to guardkit/graphiti fork

**PRIORITY**: high
**TASK_TYPE**: infrastructure
**COMPLEXITY**: 4
**ESTIMATED_MINUTES**: 90 (script edits + GB10 image rebuild + smoke probes)
**TAGS**: graphiti, fork, infra, mcp, scripts
**EXECUTION_LOCATION**: promaxgb10-41b1 (the rebuild step needs to run on the GB10 because `graphiti-mcp-build.sh` builds the standalone image with the GB10's local Docker daemon — see [graphiti-gb10-deployment.md §One-time GB10 setup](../../docs/guides/graphiti-gb10-deployment.md))
**DEPENDS ON**: `TASK-FORK-PATCH` in [`appmilla_github/graphiti/tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md`](../../../graphiti/tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md) — that task lands the patches and cuts a tag (e.g. `v0.29.5-appmilla.1`); this task pins to that tag.

---

## Why

The local upstream-tracking clone of `getzep/graphiti` has been renamed from `~/Projects/appmilla_github/graphiti` to `~/Projects/appmilla_github/graphiti-original`, and a new fork at `https://github.com/guardkit/graphiti` now occupies the original path. The MCP-build pipeline still defaults to cloning `getzep/graphiti.git` directly, which means:

1. The MCP container is rebuilt against unpatched upstream graphiti, so the seven-bug punchlist tracked in TASK-FORK-PATCH (RediSearch dash-escape, openai_generic factory, decorator group_id `>=1` fix, edge-search O(n×m), sanitize gaps, etc.) keeps being baked back in on every rebuild.
2. The newly-renamed `graphiti-original` directory is dead code from the build pipeline's perspective — nothing references it. The fork at the original path *would* be picked up by `GRAPHITI_REPO_DIR`'s default if the directory weren't blown away during the next `--no-cache` rebuild.

This task switches every live build/setup script reference from `getzep/graphiti` (upstream) to `guardkit/graphiti` (the fork), pinned to a specific fork tag for reproducibility, and verifies the rebuilt MCP image carries the patches.

This is the GuardKit-side execution of **AC-FORK-07** in TASK-FORK-PATCH; it cannot be merged before TASK-FORK-PATCH cuts its tagged release.

## Files to update — live (non-archived) references

Identified by `grep -rn "getzep/graphiti" --include="*.sh" --include="*.py"` in the guardkit repo, filtering out task-history/docs-archive directories. Each entry below has the line context that needs editing.

### Scripts (mechanical, must change)

| File | Line(s) | Current | After |
|------|---------|---------|-------|
| [`scripts/graphiti-mcp-build.sh`](../../scripts/graphiti-mcp-build.sh) | 5 (comment) | "It clones getzep/graphiti (read-only..." | "It clones guardkit/graphiti (the appmilla fork, see TASK-FORK-PATCH for what's patched relative to upstream getzep/graphiti)..." |
| [`scripts/graphiti-mcp-build.sh`](../../scripts/graphiti-mcp-build.sh) | 23 | `GRAPHITI_REPO_DIR="${GRAPHITI_REPO_DIR:-$HOME/Projects/appmilla_github/graphiti}"` | Keep value (`graphiti` now == fork); add a comment line above clarifying that this directory is the fork checkout, NOT the upstream tracker (which is now at `graphiti-original`). |
| [`scripts/graphiti-mcp-build.sh`](../../scripts/graphiti-mcp-build.sh) | 24 | `GRAPHITI_REPO_URL="${GRAPHITI_REPO_URL:-https://github.com/getzep/graphiti.git}"` | `GRAPHITI_REPO_URL="${GRAPHITI_REPO_URL:-https://github.com/guardkit/graphiti.git}"` |
| [`scripts/graphiti-mcp-build.sh`](../../scripts/graphiti-mcp-build.sh) | (new line near 24) | (none) | Add `GRAPHITI_REPO_REF="${GRAPHITI_REPO_REF:-v0.29.5-appmilla.1}"` (or whichever tag TASK-FORK-PATCH cuts; replace literal once known) |
| [`scripts/graphiti-mcp-build.sh`](../../scripts/graphiti-mcp-build.sh) | 47 | `git clone --depth 1 "$GRAPHITI_REPO_URL" "$GRAPHITI_REPO_DIR"` | `git clone --depth 1 --branch "$GRAPHITI_REPO_REF" "$GRAPHITI_REPO_URL" "$GRAPHITI_REPO_DIR"` |
| [`scripts/graphiti-validation/setup_graphiti.sh`](../../scripts/graphiti-validation/setup_graphiti.sh) | 19 | `COMPOSE_URL="https://raw.githubusercontent.com/getzep/graphiti/main/mcp_server/docker/docker-compose.yml"` | `COMPOSE_URL="https://raw.githubusercontent.com/guardkit/graphiti/main/mcp_server/docker/docker-compose.yml"` (or tag-pinned: `.../guardkit/graphiti/v0.29.5-appmilla.1/...`) |
| [`scripts/graphiti-validation/setup_graphiti_local.sh`](../../scripts/graphiti-validation/setup_graphiti_local.sh) | 22 | (same shape as above) | Same change as above |

### Tests (verify, may need update)

| File | Line | Notes |
|------|------|-------|
| [`tests/integration/conftest.py`](../../tests/integration/conftest.py) | 250 | `"graphiti-core": "/getzep/graphiti"` — appears to be a string mapping in test setup; read surrounding context to determine whether it's a documentation string (leave) or an actual path/URL used at runtime (update to `"/guardkit/graphiti"`). |

### Docs (judgment call — separate doc-update pass acceptable)

| File | Line | Disposition |
|------|------|-------------|
| [`docs/features/graphiti-integration/INSTALL-AND-VALIDATE.md`](../../docs/features/graphiti-integration/INSTALL-AND-VALIDATE.md) | 84 | `curl -O https://raw.githubusercontent.com/getzep/graphiti/main/mcp_server/docker/docker-compose.yml` — update to fork URL OR strike the section if `setup_graphiti*.sh` already covers the same flow. |
| [`docs/features/graphiti-integration/FEAT-GI-001-core-infrastructure.md`](../../docs/features/graphiti-integration/FEAT-GI-001-core-infrastructure.md) | 63 | `image: getzep/graphiti:latest` — docker-image example. Live deployment uses locally-built `graphiti-mcp-standalone:local` (per [graphiti-mcp.sh](../../scripts/graphiti-mcp.sh)), so this docs snippet is illustrative only. Update for accuracy or annotate as historical. |

**Out of scope for this task**: GitHub URL references in completed tasks, ADRs, blog posts, and `.claude/reviews/` (`tasks/completed/`, `docs/research/`, `docs/blog/`, `docs/reviews/`, `docs/adr/`, `tasks/in_review/TASK-GC-72AF…`, `tasks/in_review/TASK-FKDB-32D9…`). These reference upstream issues/PRs that legitimately live on `getzep/graphiti` (PR #1170, issue #1272, etc.) and should keep pointing at upstream. Do not bulk-rewrite them.

## Path-rename clarification

The user note "repo renamed to graphiti-original" describes a sibling-directory move that has already happened on disk. The new layout under `~/Projects/appmilla_github/`:

| Path | Remote | Role |
|------|--------|------|
| `graphiti/` | `https://github.com/guardkit/graphiti.git` (fork) | Source for `graphiti-mcp-build.sh` clone target — what we want to build from after this task |
| `graphiti-original/` (or `graphiti-official/` — verify the actual name on the GB10 with `ls ~/Projects/appmilla_github/ \| grep graph` before starting work) | `https://github.com/getzep/graphiti.git` (upstream) | Read-only upstream tracker, used for diffing and pulling upstream into the fork; not referenced by any build script |

The build script's `GRAPHITI_REPO_DIR` default already points at `~/Projects/appmilla_github/graphiti`, which is now the fork — so no path-default change is needed once the URL flips. But the `--depth 1` clone at line 47 will *blow away the existing fork checkout if it's there*; verify with the implementer that this is desired (likely yes — the build wants a fresh shallow clone of the tag), and add a comment so this isn't a future surprise.

## Acceptance Criteria

- [ ] **AC-FORK-52C2-01** — TASK-FORK-PATCH has cut a tagged release on the `guardkit/graphiti` fork (e.g. `v0.29.5-appmilla.1` per AC-FORK-04 of that task). Capture the chosen tag below before starting work:
  - **Fork tag pinned by this task**: `_TBD — fill in once TASK-FORK-PATCH ships_`
- [ ] **AC-FORK-52C2-02** — `scripts/graphiti-mcp-build.sh` updated: URL default flipped to `https://github.com/guardkit/graphiti.git`; new `GRAPHITI_REPO_REF` env var added with the tag from AC-01 as the default; `git clone` line uses `--branch "$GRAPHITI_REPO_REF"`. Comment block at the top updated to reflect "clones the fork, not upstream".
- [ ] **AC-FORK-52C2-03** — `scripts/graphiti-validation/setup_graphiti.sh` and `scripts/graphiti-validation/setup_graphiti_local.sh` updated: `COMPOSE_URL` flipped from `getzep` to `guardkit` raw URL, ideally tag-pinned to match AC-01. Both scripts smoke-tested by re-running them locally to confirm the docker-compose.yml fetch still succeeds.
- [ ] **AC-FORK-52C2-04** — `tests/integration/conftest.py:250` reviewed in surrounding context. If the string is a runtime path/URL, update to `/guardkit/graphiti`. If documentation-only, leave with an inline comment noting the upstream provenance. Capture the decision in the commit message.
- [ ] **AC-FORK-52C2-05** — Doc updates in [`INSTALL-AND-VALIDATE.md:84`](../../docs/features/graphiti-integration/INSTALL-AND-VALIDATE.md) and [`FEAT-GI-001-core-infrastructure.md:63`](../../docs/features/graphiti-integration/FEAT-GI-001-core-infrastructure.md) applied — either flipped to fork URL/image or annotated as historical.
- [ ] **AC-FORK-52C2-06** — On the GB10 (executed via `ssh promaxgb10-41b1` or `mosh`):
  ```bash
  cd ~/Projects/appmilla_github/guardkit
  ./scripts/graphiti-mcp-build.sh --no-cache
  ```
  completes successfully and produces `graphiti-mcp-standalone:local` with the fork's commit at the pinned tag. Verify via `docker run --rm graphiti-mcp-standalone:local cat /app/graphiti/.git/HEAD` (or equivalent) — expect the tag SHA, not upstream main's SHA.
- [ ] **AC-FORK-52C2-07** — Restart the MCP stack: `./scripts/graphiti-stack-up.sh`. Confirm `docker logs graphiti-mcp` shows `INFO Using OpenAIGenericClient for non-OpenAI endpoint: http://localhost:9000/v1` on first LLM call (proves the factory fix from TASK-FORK-PATCH punchlist #2 is now live in the rebuilt image). Confirm via `mcp__graphiti__add_memory` smoke probe that an episode round-trips successfully.
- [ ] **AC-FORK-52C2-08** — Confirm `~/Projects/appmilla_github/graphiti-original/` (the renamed upstream tracker, if it exists on the GB10) is NOT touched by the rebuild — `git status` inside that directory after the rebuild should show whatever staged changes were already there (the `factories.py` in-flight patch that informed TASK-FORK-PATCH; see that task's "In-flight patch already drafted" section).
- [ ] **AC-FORK-52C2-09** — `grep -rn "github.com/getzep/graphiti.git\|getzep/graphiti/main/mcp_server" scripts/ tests/integration/conftest.py` returns zero hits (mechanical-references sweep). Hits in docs are acceptable per "Out of scope" above.
- [ ] **AC-FORK-52C2-10** — Update the parent task: when this lands, mark **AC-FORK-07** in [`appmilla_github/graphiti/tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md`](../../../graphiti/tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md) as complete, with a backlink to this task ID.

## Order of operations

1. Wait for TASK-FORK-PATCH to ship its tag (AC-FORK-04 there). Without that, this task pins to nothing.
2. Edit the three scripts (`graphiti-mcp-build.sh`, `setup_graphiti.sh`, `setup_graphiti_local.sh`) on the Mac dev machine — these are `sh` files with no host-specific dependencies, so editing here is fine; they execute on the GB10 later.
3. Edit `tests/integration/conftest.py` and the two doc files.
4. Push the guardkit changes.
5. SSH into the GB10, pull guardkit, run `./scripts/graphiti-mcp-build.sh --no-cache`, verify image SHA, restart stack, run smoke probes.
6. Once green, close out AC-FORK-07 in TASK-FORK-PATCH.

## Rollback

If the rebuilt image fails the smoke probe (factories.py logs no `OpenAIGenericClient` line, or MCP probe doesn't round-trip an episode):

```bash
# On GB10 — revert to the previously-baked image (untagged-but-cached upstream build)
docker tag graphiti-mcp-standalone:local-pre-fork graphiti-mcp-standalone:local  # if pre-fork tag was preserved before --no-cache
./scripts/graphiti-stack-up.sh
```

(Tag the existing image as `:local-pre-fork` BEFORE starting AC-06 so this rollback is available — add as a tip to the rebuild step at execution time.)

Revert the script edits with `git revert` on guardkit. Investigate fork-tag fetch issue (auth? tag missing? CI on the fork repo broken?) before retrying.

## Cross-references

- **TASK-FORK-PATCH** ([`appmilla_github/graphiti/tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md`](../../../graphiti/tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md)) — parent task that lands the bug fixes in the fork and cuts the tag this task pins to. AC-FORK-07 there is the specific outcome this task delivers.
- **TASK-INF-5054** ([`tasks/backlog/TASK-INF-5054-graphiti-mcp-llm-endpoint-misrouting.md`](TASK-INF-5054-graphiti-mcp-llm-endpoint-misrouting.md)) — original symptom that motivated the in-flight `factories.py` patch now incorporated into the fork. Closes when AC-07 of this task verifies the `OpenAIGenericClient` log line appears.
- **graphiti-gb10-deployment.md** ([`docs/guides/graphiti-gb10-deployment.md`](../../docs/guides/graphiti-gb10-deployment.md)) — runbook for the build/start/stop scripts touched by this task. NOTE: this guide is itself stale (still describes the retired vLLM `:8000`/`:8001` topology) and has a separate refresh task pending — do not roll that into this task.
- **TASK-graphiti-yaml-endpoint-migration** ([`docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md`](../../docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md)) — orthogonal task tracking the consumer-side `.guardkit/graphiti.yaml` endpoint migration. Independent of this fork-redirection task.
