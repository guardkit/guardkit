---
id: TASK-GK-FORK-PIN
title: Pin graphiti-core to guardkit/graphiti fork (pyproject + MCP build script + container rebuild)
status: backlog
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T00:00:00Z
priority: high
task_type: feature
complexity: 3
estimated_minutes: 45
execution_location: promaxgb10-41b1
tags: [graphiti, fork, pyproject, mcp, container]
parent_task: graphiti/TASK-FORK-PATCH (cross-repo follow-up)
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Pin graphiti-core to the guardkit/graphiti fork

**WHY**: TASK-FORK-PATCH landed all six bug-fix patches in the [`guardkit/graphiti`](https://github.com/guardkit/graphiti) fork at tag `v0.29.5-guardkit.1`, but guardkit (the consumer) still pulls graphiti-core from PyPI. This task switches the pin to the fork tag so the patches actually exercise in deployed code.

This task is a **prerequisite** for graphiti-side TASK-FPA-009 (end-to-end verification) which is currently in `tasks/blocked/` waiting for cross-repo work to land.

## What needs to change

### 1. `pyproject.toml` — five graphiti-core references

All five lines pin to PyPI; replace with the fork tag. **Note**: the fork's `pyproject.toml` is at the repo root (the package name `graphiti-core` is declared there directly), so no `#subdirectory=` qualifier is needed.

| Line | Current | Replacement |
|------|---------|-------------|
| 34 (main deps) | `"graphiti-core>=0.5.0"` | `"graphiti-core @ git+https://github.com/guardkit/graphiti.git@v0.29.5-guardkit.1"` |
| 51 (`falkordb` extra) | `"graphiti-core[falkordb]"` | `"graphiti-core[falkordb] @ git+https://github.com/guardkit/graphiti.git@v0.29.5-guardkit.1"` |
| 56 (`gemini` extra) | `"graphiti-core[google-genai]"` | `"graphiti-core[google-genai] @ git+https://github.com/guardkit/graphiti.git@v0.29.5-guardkit.1"` |
| 72 (`all` extra) | `"graphiti-core[falkordb]"` | `"graphiti-core[falkordb] @ git+https://github.com/guardkit/graphiti.git@v0.29.5-guardkit.1"` |
| 73 (`all` extra) | `"graphiti-core[google-genai]"` | `"graphiti-core[google-genai] @ git+https://github.com/guardkit/graphiti.git@v0.29.5-guardkit.1"` |

### 2. `scripts/graphiti-mcp-build.sh` — fork URL + tag pin

Currently defaults to upstream `getzep/graphiti` and never checks out a specific tag (just uses whatever's in the working tree). Update so the build is reproducible against the fork tag:

```diff
-GRAPHITI_REPO_URL="${GRAPHITI_REPO_URL:-https://github.com/getzep/graphiti.git}"
+GRAPHITI_REPO_URL="${GRAPHITI_REPO_URL:-https://github.com/guardkit/graphiti.git}"
+GRAPHITI_TAG="${GRAPHITI_TAG:-v0.29.5-guardkit.1}"

 if [ ! -d "$GRAPHITI_REPO_DIR/.git" ]; then
-  echo "Cloning graphiti repo → $GRAPHITI_REPO_DIR"
+  echo "Cloning graphiti fork → $GRAPHITI_REPO_DIR (tag: $GRAPHITI_TAG)"
   mkdir -p "$(dirname "$GRAPHITI_REPO_DIR")"
-  git clone --depth 1 "$GRAPHITI_REPO_URL" "$GRAPHITI_REPO_DIR"
-elif [ "$DO_PULL" = "1" ]; then
-  echo "Pulling latest graphiti → $GRAPHITI_REPO_DIR"
-  git -C "$GRAPHITI_REPO_DIR" pull --ff-only
+  git clone --depth 1 --branch "$GRAPHITI_TAG" "$GRAPHITI_REPO_URL" "$GRAPHITI_REPO_DIR"
+else
+  echo "Fetching tags and checking out $GRAPHITI_TAG → $GRAPHITI_REPO_DIR"
+  git -C "$GRAPHITI_REPO_DIR" fetch --tags origin
+  git -C "$GRAPHITI_REPO_DIR" checkout "$GRAPHITI_TAG"
 fi
```

Also update the header comment from "It clones getzep/graphiti" → "It clones guardkit/graphiti at tag $GRAPHITI_TAG".

The `--pull` arg becomes a no-op (or remove it from the arg parser since checkout-tag is now unconditional). Choose: simpler to drop, or preserve for compatibility — your call.

### 3. `scripts/graphiti-mcp.sh` — no change needed

Already exports `-e MCP_SERVER_HOST=0.0.0.0` (line 153), which is what patch 003 needs. ✅

The `bootstrap.py` monkey-patch is **technically retirable** post-fork (patch 003 obviates it) but **leave it in for this task** — retiring the shim is a stretch goal (graphiti-side AC-FORK-14) and out of scope here. File `TASK-GK-RETIRE-BOOTSTRAP-SHIM` if you want to track that separately.

### 4. Container rebuild

After 1+2 are committed:

```bash
cd ~/Projects/appmilla_github/guardkit
./scripts/graphiti-mcp-build.sh --no-cache    # builds from ~/Projects/appmilla_github/graphiti at v0.29.5-guardkit.1
./scripts/graphiti-mcp.sh                     # restarts the MCP container
docker logs graphiti-mcp 2>&1 | head -20      # smoke check on startup
```

Expect the auto-detect log line on first LLM call: `Using OpenAIGenericClient for non-OpenAI endpoint: http://localhost:9000/v1`.

## Acceptance Criteria

- [ ] `pyproject.toml`: all five graphiti-core lines pin to `git+https://github.com/guardkit/graphiti.git@v0.29.5-guardkit.1` (with appropriate extras).
- [ ] `uv sync` (or `pip install -e .[all]`) succeeds and installs graphiti-core from the fork tag. Verify with `python -c "import graphiti_core; print(graphiti_core.__file__)"` — path should reflect the fork checkout, not a PyPI install.
- [ ] `scripts/graphiti-mcp-build.sh`: defaults to fork URL and `v0.29.5-guardkit.1` tag; `--branch` flag passed to `git clone --depth 1`; existing checkouts checked out to the tag explicitly.
- [ ] MCP container rebuilt successfully (`./scripts/graphiti-mcp-build.sh --no-cache` exits 0; image tag `graphiti-mcp-standalone:local` updated).
- [ ] MCP container restarted and reachable: `curl -sf http://promaxgb10-41b1:8004/mcp/ -H 'Accept: text/event-stream'` returns 200 (or 307 — both indicate serving).
- [ ] `docker logs graphiti-mcp` shows the auto-detect log line on first LLM call. Zero references to `api.openai.com` in the startup window.
- [ ] Single commit on guardkit's `main` (or whichever branch is current) with message `pin: graphiti-core → guardkit/graphiti @ v0.29.5-guardkit.1 (fork)`. Squash the pyproject + script changes into one commit if they were drafted separately.

## Cross-references

- Parent (graphiti repo): [TASK-FORK-PATCH](../../graphiti/tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md)
- Blocks: [graphiti TASK-FPA-009](../../graphiti/tasks/blocked/fork-patch-application/TASK-FPA-009-end-to-end-verification.md)
- Sibling cross-repo: jarvis TASK-JAR-FORK-PIN
- Fork tag: [v0.29.5-guardkit.1](https://github.com/guardkit/graphiti/releases/tag/v0.29.5-guardkit.1)

## Notes

- study-tutor was originally listed as a third cross-repo follow-up but is **not** affected: study-tutor's pyproject.toml does not declare a graphiti-core dependency at all. The seed-script (`scripts/seed_student_model.py`) lazy-imports graphiti-core, presumably from a venv that gets graphiti-core from elsewhere (likely a user-managed `pip install graphiti-core` on the Mac). study-tutor's seed-test in graphiti TASK-FPA-009 (AC-FORK-08-1 and AC-FORK-08-2) therefore can't be exercised on the GB10 without separate venv-setup work — track that as a separate concern.
- The `bootstrap.py` shim retirement (graphiti-side AC-FORK-14) is intentionally NOT part of this task. File `TASK-GK-RETIRE-BOOTSTRAP-SHIM` post-verification if desired.
