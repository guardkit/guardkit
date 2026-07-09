<!-- qa-format: runbook format_version: 1.0 -->
# Runbook: LPA Platform POC — Foundation Infrastructure

WS2-B10 exemplar (F11). Derived from
`lpa-platform-poc/docs/runbooks/RUNBOOK-foundation-infrastructure.md`, formalized
to the F11 conventions: a Facts header, typed phases, and an executable
`**Pass:**` check on every phase (a runbook step without a pass check is a wish).

## Facts

- **Docker Desktop 24+ / Compose v2+ present** — verified 2026-07-05 — `docker --version && docker compose version`
- **GB10 reachable for LLM inference** — verified 2026-07-05 — `curl -sf http://gb10:9000/health`
- **Scope doc committed** — verified 2026-07-05 — `git log --oneline -1 docs/poc/SCOPE.md`

## Phase 0: Pre-flight — type: preflight

Confirm the host has Docker, free ports (5432 / 8180 / 8000), and a clean tree.

```bash
docker compose version
ss -ltn | grep -E ':5432|:8180|:8000' || echo "ports free"
```

**Pass:** `docker compose version` prints v2+, the three ports are free, and `git status` shows a clean or known working tree.

## Phase 1: Docker Compose skeleton — type: change

Create `docker-compose.poc.yml` + `Dockerfile.poc` and bring the stack up.

```bash
docker compose -f docker-compose.poc.yml up -d --build
```

**Pass:** `docker compose ps` shows postgres, keycloak, and api all `Up (healthy)`.

## Phase 2: Keycloak realm — type: change

Import the finproxy realm export and create the test users.

**Pass:** a direct-access-grant token request for a test user returns a JWT with the expected realm roles.

## Phase 3: Backup before schema change — type: backup

Snapshot the Postgres volume before running Alembic.

```bash
docker compose exec postgres pg_dump -U poc finproxy > backups/pre-alembic.sql
```

**Pass:** `backups/pre-alembic.sql` exists and is non-empty.

## Phase 4: Verify — type: verify

Run the phase-6 leak sweep against the deployed app.

**Pass:** the sweep reports zero mock identities in donor/attorney scopes and writes evidence shots.

## Phase 5: Rollback — type: rollback

If any phase fails, restore the pre-Alembic snapshot and re-import the realm.

**Pass:** `docker compose ps` returns all services healthy on the restored snapshot.
