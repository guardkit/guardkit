# vllm-embed.sh — Fix: Switch Default from Nemotron to Nomic

**Date:** 2026-02-23
**Script:** `scripts/vllm-embed.sh`
**Container:** `nvcr.io/nvidia/vllm:26.01-py3` (vLLM 0.13.0)

---

## What Was Wrong

Running `./vllm-embed.sh` (the default nemotron preset) started a container that immediately crashed with two distinct errors.

### Error 1 — Wrong flag for nomic (`--task embed`)

When switching to the `nomic` preset as a workaround, the server failed with:

```
vllm: error: unrecognized arguments: --task embed
```

`--task embed` is not a valid flag in vLLM 0.13.0. The correct flag for serving pooling/embedding models is `--runner pooling`.

### Error 2 — Nemotron requires transformers 5.x (root cause)

The nemotron model (`nvidia/llama-nemotron-embed-1b-v2`) uses a custom bidirectional Llama encoder architecture (`llama_bidirectional_model.py`). vLLM has no native implementation for this, so it falls back to the Transformers backend. The Transformers backend requires `transformers>=5.0.0.dev0` for encoder model support, but the 26.01 container ships `transformers==4.57.1`:

```
WARNING: TransformersEmbeddingModel has no vLLM implementation,
         falling back to Transformers implementation.
...
ImportError: Transformers modeling backend requires transformers>=5.0.0.dev0
             for encoder models support, but got 4.57.1
RuntimeError: Engine core initialization failed.
```

The server process died before binding to port 8001, which is why `curl` returned `Connection reset by peer` / `Couldn't connect to server`.

---

## Changes Made

### 1. Default preset changed from `nemotron` → `nomic`

`nomic-ai/nomic-embed-text-v1.5` (137M, NomicBertModel) has a native vLLM implementation and does not depend on the Transformers backend. It works correctly with the 26.01 container.

### 2. Nomic args corrected: `--task embed` → `--runner pooling --trust-remote-code`

`--runner pooling` is the correct vLLM 0.13.0 flag for embedding/pooling models. `--trust-remote-code` is required by the nomic model's custom tokenizer.

### 3. Nemotron preset retained with a warning

The `nemotron` preset still exists but now prints a warning before starting:

```
WARNING: Requires transformers>=5.0.0.dev0; container 26.01 has 4.57.1 — likely to fail.
```

### 4. `custom` preset default args updated

The `custom` preset fallback still references `--task embed` via `VLLM_EMBED_EXTRA_ARGS` — this is intentional as the user is expected to override it for their specific model.

---

## Working Configuration (nomic)

| Property | Value |
|---|---|
| Model | `nomic-ai/nomic-embed-text-v1.5` |
| Architecture | `NomicBertModel` (native vLLM support) |
| Dimensions | 768 |
| Max context | 2048 tokens (note: nomic context extension disabled by default) |
| vLLM flags | `--runner pooling --trust-remote-code` |
| Port | 8001 |
| GPU util | 0.15 |

### Verified test

```bash
curl http://localhost:8001/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model": "nomic-ai/nomic-embed-text-v1.5", "input": "Hello world"}'
# Returns: 768-dim embedding vector
```

---

## When Nemotron Will Work Again

The nemotron model will work once NVIDIA releases a vLLM container that bundles `transformers>=5.0.0.dev0`. Check for new container versions at:

```bash
docker pull nvcr.io/nvidia/vllm:26.02-py3   # not yet available as of 2026-02-23
```

To verify the transformers version in a future container:

```bash
docker run --rm nvcr.io/nvidia/vllm:XX.XX-py3 python3 -c "import transformers; print(transformers.__version__)"
```

Once the version is `>=5.0.0.dev0`, the nemotron preset can be tested and the warning removed.
