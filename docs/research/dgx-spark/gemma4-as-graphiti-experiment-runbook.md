# Gemma 4 as Graphiti Backend — Experiment Runbook

> **Date drafted:** 2026-05-30. **Author of context:** Claude session that
> ran the workhorse-consolidation attempts §9.5–§9.7 of
> [`AUTOBUILD-ON-LLAMA-SWAP-findings.md`](AUTOBUILD-ON-LLAMA-SWAP-findings.md).
> Self-contained — read this once and you can execute the experiment without
> re-reading the full findings history. Pointers back are inline where needed.

---

## 1. Hypothesis

**Use `gemma4-tutor`'s GGUF (Gemma 4 26B-A4B, already on disk and proven
working under llama-swap) as the backend for a NEW `gemma4-graphiti` model
entry, with Graphiti-tuned args, to replace `qwen-graphiti` and free
~7 GB net on the GB10.**

This is the §9.7 candidate path (c). It's **decoupled** from the failed
workhorse-consolidation path (§9.5–§9.7) — Gemma 4 is a pure transformer
(no mamba/SSM/GatedDeltaNet), so the `-np N`-under-llama-swap failure that
blocked workhorse should not apply to it. And Gemma was **not** on the
TASK-REV-DGX1 eliminated list (see `docs/reference/graphiti-llm-selection.md`).

## 2. Why it's worth trying

| Property | Status |
|---|---|
| Model already on disk | ✓ `/opt/llama-swap/models/gemma4-tutor/gemma-4-26b-a4b-it.Q4_K_M.gguf` |
| Already proven under llama-swap | ✓ `gemma4-tutor` runs at `-np 1` daily |
| Pure attention arch (no mamba/SSM) | ✓ — the workhorse `-np N` failure shouldn't apply |
| No thinking mode by default | ✓ pure instruct — clean structured JSON |
| Not on the TASK-REV-DGX1 eliminate-list | ✓ — Qwen3-family was; Gemma 4 wasn't tested then |
| Quality for Graphiti extraction | ❓ — unknown, this experiment's main question |

Cost ledger:

| Change | Memory impact |
|---|---|
| Drop `qwen-graphiti` from preload | **−28 GB** |
| Add `gemma4-graphiti` (`-np 4 / ctx 65K`, mirrors qwen-graphiti) | **+~21 GB** (weights 16 + KV ~5) |
| **Net save** | **~+7 GB headroom** |

Not the original 28 GB dream, but a real win and the most plausible path
left after §9.5–§9.7.

## 3. Pre-flight checks (run these first)

```bash
# Stack versions (should be llama-swap v219 + llama.cpp b9430)
/usr/local/bin/llama-swap --version
pgrep -af "[l]lama-server" | head -1 | grep -oE "/home/[^ ]+/llama-server"

# Baseline state
systemctl --user is-active llama-swap.service        # expect: active
systemctl is-active llama-swap-keepalive.timer       # expect: active
free -g | head -2                                     # expect: ~80 GB used / ~40 GB free
ps -eo args --no-headers | grep "[l]lama-server" | grep -oE "\-\-alias [a-z0-9-]+" | sort -u
# expect 4 aliases: gemma4-tutor, nomic-embed, qwen36-workhorse, qwen-graphiti

# Confirm Graphiti baseline still works (qwen-graphiti at ~9s/call per call)
curl -sS --max-time 10 http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-graphiti","max_tokens":4,"messages":[{"role":"user","content":"hi"}]}' \
  -w "  qwen-graphiti  HTTP %{http_code} in %{time_total}s\n" -o /dev/null
# expect: HTTP 200 in <1s warm
```

If anything fails, stop and read [`AUTOBUILD-ON-LLAMA-SWAP-findings.md`](AUTOBUILD-ON-LLAMA-SWAP-findings.md) §9.4–§9.7 for context.

## 4. The experiment — 6 stages

> Each stage is reversible until stage 6. The standalone smoke (stage 1) is
> the riskiest unknown; if it fails, **the path is blocked** and you can
> stop without touching the live config.

### Stage 1 — Standalone smoke (does Gemma load with `-np 4`?)

Run a fresh `llama-server` on a side port with the **exact args** we'd give
the new model entry. This proves the model loads at the Graphiti-tuned slot
shape **before** touching live config. If it fails the way workhorse `-np 2`
did, the path is dead and there's nothing else to test.

```bash
# Side-port 5897, ~120s budget for cold load
cd /tmp && rm -f /tmp/gemma4-graphiti-smoke.log
(timeout 120 /home/richardwoollcott/llama.cpp-new/build/bin/llama-server \
  --port 5897 --host 0.0.0.0 \
  --model /opt/llama-swap/models/gemma4-tutor/gemma-4-26b-a4b-it.Q4_K_M.gguf \
  --alias gemma4-graphiti-smoke \
  --ctx-size 65536 \
  --batch-size 2048 --ubatch-size 2048 \
  --threads 16 -ngl 999 --no-mmap --flash-attn on --jinja \
  --temp 0.0 \
  -np 4 \
  > /tmp/gemma4-graphiti-smoke.log 2>&1; echo "EXIT=$?" >> /tmp/gemma4-graphiti-smoke.log) &
DIRECT_PID=$!
echo "smoke pid $DIRECT_PID; watching for 'server is listening' up to 120s..."
SECONDS=0
until grep -q "server is listening" /tmp/gemma4-graphiti-smoke.log 2>/dev/null || [ $SECONDS -gt 115 ]; do sleep 4; done
echo "--- result at ${SECONDS}s ---"
grep -E "server is listening|EXIT=|error|abort|cuda" /tmp/gemma4-graphiti-smoke.log | head
```

**PASS criteria:**
- Log contains `server is listening on http://0.0.0.0:5897` within ~60 s.
- No `EXIT=` line (or only after we Ctrl-C / kill at the end).
- No `error`/`abort`/`cuda` failures.

If PASS: quick functional test, then kill.

```bash
# Quick text chat to confirm it serves
curl -sS --max-time 10 http://127.0.0.1:5897/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma4-graphiti-smoke","max_tokens":12,"messages":[{"role":"user","content":"reply: ok"}]}' | head -c 300

# Then the structured-JSON test (the real bar — mirrors what we did for workhorse §9.5)
curl -sS --max-time 30 http://127.0.0.1:5897/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model":"gemma4-graphiti-smoke",
    "max_tokens":500,"temperature":0,
    "response_format":{"type":"json_schema","json_schema":{"name":"entity_extraction","schema":{"type":"object","properties":{"entities":{"type":"array","items":{"type":"object","properties":{"name":{"type":"string"},"entity_type":{"type":"string"}},"required":["name","entity_type"]}}},"required":["entities"]}}},
    "messages":[
      {"role":"system","content":"Extract every named entity (person, organization, place, product) from the user text. Return ONLY JSON matching the schema."},
      {"role":"user","content":"Apple Inc. is a technology company based in Cupertino, California. Tim Cook is its CEO. The company makes iPhones and MacBooks."}
    ]
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); m=d['choices'][0]['message']['content']; print('reply:',m[:400]); import json as j; p=j.loads(m); print('parsed:',p); print('finish:',d['choices'][0]['finish_reason']); print('usage:',d.get('usage'))"

# Cleanup (use ss to find the pid by port, kill it; don't pgrep on a pattern that matches the very command)
for pid in $(ss -tnlp 2>/dev/null | grep ":5897 " | grep -oE 'pid=[0-9]+' | cut -d= -f2); do kill -9 $pid; done
ss -tnl | grep ":5897" || echo "(cleaned)"
```

**Bar to proceed to stage 2:**
- HTTP 200 on both requests.
- JSON parses; entities returned (~5+ for the Apple/Cupertino/Tim Cook prompt).
- `finish: stop`.
- No thinking-token bloat (`<think>` blocks).
- Generation looks roughly reasonable speed (a few seconds for 100–500 tokens at temp 0).

If the load itself fails fast (echo of the workhorse `-np 2` symptom),
**stop here** — record the exit reason and add a section to findings §9.8.

### Stage 2 — Add `gemma4-graphiti` to llama-swap config (additive, on-demand)

Edit `/opt/llama-swap/config/config.yaml`. Insert a new model entry — anywhere
in `models:` is fine; near `gemma4-tutor` is logical. **Do NOT add it to
`hooks.on_startup.preload` yet** — keep this on-demand for the test, with
`ttl: 1800` (auto-release after 30 min idle).

```yaml
  # 2026-05-30 experiment: Gemma 4 as Graphiti backend (§9.7 candidate (c))
  # Same GGUF as gemma4-tutor (no second download), but Graphiti-tuned args:
  # no Socratic template, temp 0 (Graphiti also overrides per-request), -np 4
  # to absorb chunk_extraction_concurrency:4 in graphiti.yaml.
  "gemma4-graphiti":
    cmd: >
      /home/richardwoollcott/llama.cpp-new/build/bin/llama-server
      --port ${PORT}
      --host 0.0.0.0
      --model /opt/llama-swap/models/gemma4-tutor/gemma-4-26b-a4b-it.Q4_K_M.gguf
      --alias gemma4-graphiti
      --ctx-size 65536
      --batch-size 2048
      --ubatch-size 2048
      --threads 16
      -ngl 999
      --no-mmap
      --flash-attn on
      --jinja
      --temp 0.0
      -np 4
    checkEndpoint: /health
    ttl: 1800                # on-demand: auto-unload after 30 min idle
    concurrencyLimit: 6      # ~1.5× -np buffer (mirrors qwen-graphiti)
    aliases:
      - "graphiti-llm-test"
```

llama-swap watches the config file (`-watch-config`, 2 s poll). It should hot-
reload automatically — no restart needed. Verify:

```bash
sleep 4
curl -s --max-time 5 http://localhost:9000/v1/models | python3 -c "import sys,json; ids=[m['id'] for m in json.load(sys.stdin).get('data',[])]; print('gemma4-graphiti listed:', 'gemma4-graphiti' in ids)"
# expect: True
```

### Stage 3 — Route-via-llama-swap smoke (the moment of truth)

If this passes, we've cleared the `-np N`-under-llama-swap risk that
blocked workhorse.

```bash
# This triggers the load AND tests the chat path. Cold-load may take ~30-60s
# (this is its FIRST invocation under llama-swap).
time curl -sS --max-time 240 http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"graphiti-llm-test","max_tokens":12,"messages":[{"role":"user","content":"hi"}]}' \
  -o /tmp/gemma4-graphiti-route.json -w "HTTP %{http_code} in %{time_total}s\n"

head -c 400 /tmp/gemma4-graphiti-route.json
```

**PASS:** HTTP 200 (first call may take 30–60 s cold; subsequent warm calls
< 1 s). The reply body has a `choices[0].message.content`.

**FAIL signatures (means path is dead):**
- `HTTP 502 ... upstream command exited prematurely` in ~5 s → same family as the workhorse failure → file upstream.
- `HTTP 500 ... connection refused` → llama-swap fast-fail mode.

If it fails, jump straight to the **Revert procedure** in §6.

If it passes, check the llama-swap log to make sure it's not flapping:

```bash
grep -i "gemma4-graphiti" /opt/llama-swap/logs/llama-swap.log | tail -10
# expect: Health check passed; no ExitError; no "exited prematurely"
```

### Stage 4 — Swap `graphiti.yaml` to the new model

Back it up first (we've been disciplined about this — keep the streak):

```bash
cp /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml \
   /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml.bak-2026-05-30-gemma4-test
```

Edit `/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml` — two lines:

```yaml
# Was: chunk_extraction_concurrency: 8
chunk_extraction_concurrency: 4    # match gemma4-graphiti -np 4

# Was: llm_model: qwen-graphiti
llm_model: graphiti-llm-test       # routes to gemma4-graphiti
```

No restart needed — guardkit re-reads `graphiti.yaml` per CLI invocation.

### Stage 5 — Real Graphiti ingestion test

Use the same synthetic test doc from §9.5/§9.6 (or create a fresh one with
a clear test marker so you can clean it out of the graph later).

```bash
cat > /tmp/graphiti-gemma4-test.md <<'EOF'
# TEST: Gemma 4 as Graphiti Backend (2026-05-30)

Synthetic test document for evaluating Gemma 4 26B-A4B as a replacement for
Qwen2.5-14B (qwen-graphiti) on the GB10's llama-swap stack.

## Background

The dark factory at AppMilla runs on a DGX Spark GB10 with 121 GB unified
memory. The platform uses llama-swap as the model multiplexer on port 9000.
The GuardKit project orchestrates autobuild flows where a Player model writes
code and a Coach model reviews it.

## Models in scope

- `qwen-graphiti` (Qwen2.5-14B-Instruct-FP8) — current Graphiti extractor.
- `gemma4-graphiti` (Gemma 4 26B-A4B Q4_K_M) — candidate replacement.

## Decision

If Gemma 4 can serve Graphiti without quality regression, qwen-graphiti can be
dropped, freeing ~7 GB net on the GB10. Owner: Richard Woollcott.
EOF

# Run the real ingestion (this is the bar — it'll fire Graphiti's full
# multi-call pipeline: entity-extract, edge-extract, dedup, summarise).
# qwen-graphiti baseline: ~30-60s for this size; failure mode = OpenAI SDK
# retry storm + "Rate limit exceeded" (§9.5).
time guardkit graphiti add-context /tmp/graphiti-gemma4-test.md --type full_doc 2>&1 | tee /tmp/gemma4-graphiti-ingest.log | tail -30
```

**PASS criteria:**
- `Added 1 file, ≥1 episode(s)` in the summary
- `Failed: 0 episode`
- Wall time **< 90 s** (allows some headroom vs qwen-graphiti baseline)
- No `Retrying request to /chat/completions` repeated dozens of times
- No `Rate limit exceeded` or `Episode creation returned None`

If PASS, sanity-check the graph actually has entities:

```bash
guardkit graphiti search "AppMilla GB10 dark factory" --limit 5
# expect: matches mentioning AppMilla / GB10 / etc.
```

### Stage 6 — Commit (only if stage 5 passed cleanly)

This is the irreversible step (well, easily revertable but more invasive
than the test). **Skip if anything was even slightly off.** If you want
more confidence, run a second ingestion test against a different document
first.

Two changes:

1. **In `/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml`:** rename the alias from `graphiti-llm-test` to `graphiti-llm` (cleaner). Update the comment to indicate this is now the production setting.

2. **In `/opt/llama-swap/config/config.yaml`:**
   - In the `gemma4-graphiti` entry's `aliases:`, add `"graphiti-llm"` (or rename `graphiti-llm-test` → `graphiti-llm`).
   - **Drop `qwen-graphiti` from `hooks.on_startup.preload`.**
   - **Add `gemma4-graphiti` to `hooks.on_startup.preload`.**
   - Optionally bump `ttl: 1800` → `ttl: 0` (always on, like qwen-graphiti was).
   - Optionally consider removing the `qwen-graphiti` model entry entirely (frees disk via `rm /opt/llama-swap/models/qwen2.5-14b/*` if you want — but keep the entry as a fallback alias for a while).

3. **Update the keepalive allowlist** (`scripts/llama-swap-keepalive.sh` then re-deploy with sudo — see [`llama-swap-keepalive-start-stop.md`](llama-swap-keepalive-start-stop.md) for the procedure). `MODEL_PROBE_KIND` should now have `gemma4-graphiti` instead of `qwen-graphiti`. If you leave the qwen-graphiti entry in the config, also remove it from the allowlist (the keepalive must equal the preload set — see findings §9.4).

4. **Restart llama-swap:** `systemctl --user restart llama-swap.service`. Verify:

   ```bash
   sleep 30  # preload settles
   ps -eo args --no-headers | grep "[l]lama-server" | grep -oE "\-\-alias [a-z0-9-]+" | sort -u
   # expect 4 core aliases including gemma4-graphiti (not qwen-graphiti)
   free -g | head -2
   # expect ~73 GB used (was ~80) — net ~7 GB freed
   ```

## 5. Documentation

Whichever way it lands (PASS or FAIL), add a `### 9.8 …` section to
[`AUTOBUILD-ON-LLAMA-SWAP-findings.md`](AUTOBUILD-ON-LLAMA-SWAP-findings.md)
mirroring the §9.5–§9.7 style:

- Trigger (this runbook)
- What was tested (the 5-stage flow)
- Outcome with numbers
- Net memory delta if committed
- Updated guidance: what `graphiti-llm-selection.md` should say about Gemma 4
  for Graphiti (we'd want to amend that doc too)

## 6. Revert procedure

If stage 1, 3, or 5 fails — or you just want to back out:

```bash
# 1. Restore graphiti.yaml (only needed if you got past stage 4)
cp /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml.bak-2026-05-30-gemma4-test \
   /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml

# 2. Remove the gemma4-graphiti entry from /opt/llama-swap/config/config.yaml
#    (delete the YAML block you added in stage 2; leave preload as-is —
#    qwen-graphiti was never removed yet).

# 3. The hot-reload picks it up (2s poll). Verify:
sleep 4
curl -s --max-time 5 http://localhost:9000/v1/models | python3 -c "import sys,json; ids=[m['id'] for m in json.load(sys.stdin).get('data',[])]; print('gemma4-graphiti gone:', 'gemma4-graphiti' not in ids)"

# 4. Confirm qwen-graphiti still serves
curl -sS --max-time 10 http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-graphiti","max_tokens":4,"messages":[{"role":"user","content":"hi"}]}' \
  -w "HTTP %{http_code} in %{time_total}s\n" -o /dev/null
```

Box returns to the post-§9.7 stable baseline. No keepalive change needed
(we never added gemma4-graphiti to the allowlist during the test).

## 7. Risks and gotchas

| Risk | Likelihood | Mitigation |
|---|---|---|
| Gemma 4 fails the standalone `-np 4` load (echoes workhorse failure) | Medium-low — different arch, but llama-swap launch env is the wildcard | Stage 1 catches before any live change; revert = nothing to undo |
| Stage 3 fails (loads standalone but not via llama-swap) | Low — gemma4-tutor at `-np 1` already works; `-np 4` on same model should too | Revert via §6 |
| Gemma 4 produces poor structured JSON for Graphiti's schema | Medium — the central unknown | Stage 5 catches; revert via §6 |
| Gemma 4 is *slower* per call than Qwen2.5-14B, eats the time win | Medium | Stage 5 timing comparison; if marginal, may still be worth it for the 7 GB |
| chat-template-vs-system-prompt interaction (no Socratic template now) | Low — Gemma's default jinja is fine | The test exercises this |
| Memory spike during preload of new entry | Very low — we're on-demand+ttl until commit | Don't preload until stage 6 |
| Reverting after stage 6 is more invasive | N/A — same change in reverse + restart | Keep the graphiti.yaml backup; the qwen-graphiti model entry stays defined |

## 8. Quick reference — what changed when

Everything done in this experiment is fully reversible. Files touched:

- `/opt/llama-swap/config/config.yaml` — added `gemma4-graphiti` entry (and at stage 6, changed preload list)
- `/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml` — `llm_model` + `chunk_extraction_concurrency`
- (stage 6 only) `scripts/llama-swap-keepalive.sh` — `MODEL_PROBE_KIND` allowlist

Backups created:

- `.guardkit/graphiti.yaml.bak-2026-05-30-gemma4-test`
- (stage 6 only) `/opt/llama-swap/config/config.yaml.bak-2026-05-30-pre-gemma4-graphiti`
- (stage 6 only) `/usr/local/bin/llama-swap-keepalive.sh.bak-pre-gemma4`

## 9. Pointers (for context if needed)

- [`AUTOBUILD-ON-LLAMA-SWAP-findings.md`](AUTOBUILD-ON-LLAMA-SWAP-findings.md) §9.4 = freeze incident + keepalive fix; §9.5–§9.7 = workhorse-for-Graphiti attempts that failed (why we're trying Gemma instead)
- [`graphiti-llm-selection.md`](../../reference/graphiti-llm-selection.md) — original model selection (TASK-REV-DGX1); note Gemma 4 was **not** evaluated then
- [`llama-swap-keepalive-start-stop.md`](llama-swap-keepalive-start-stop.md) — keepalive procedure (only needed at stage 6)
- Current versions: llama.cpp **b9430** (`/home/richardwoollcott/llama.cpp-new/build/bin/llama-server`), llama-swap **v219** (deployed at `/usr/local/bin/llama-swap`, old v208 backed up at `.v208.bak`)
