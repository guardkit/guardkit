# Graphiti Cloud LLM Configuration — GPU Contention Fix

**Problem:** GB10 runs Qwen2.5-14B (port 8000) for Graphiti entity extraction + nomic-embed-text-v1.5 (port 8001) for embeddings. This blocks fine-tuning, model hosting, and dataset factory runs.

**Solution:** Move Graphiti's LLM calls to a cloud API. Keep the embedding model local (it's tiny). This frees the GPU for everything else.

**Key insight:** Graphiti only uses the LLM during **ingestion/seeding**, not during queries. Queries use embeddings + graph traversal + BM25 — no LLM calls. So the cloud API is only hit during `guardkit graphiti seed` operations, making costs minimal.

---

## Architecture (All Options)

```
GB10 (freed up)                    Cloud
┌─────────────────────┐           ┌──────────────────┐
│ nomic-embed-text-v1.5│           │ Google Gemini API │
│ (port 8001, ~1GB)   │           │   (primary)       │
│                     │           │ OR Groq / Bedrock │
│ + fine-tuning       │           │   (alternatives)  │
│ + model hosting     │           │                  │
│ + dataset factory   │           │ Entity extraction│
│ + AutoBuild Coach   │           │ Relationship ext.│
└─────────────────────┘           │ Entity resolution│
        ▲                         └──────────────────┘
        │ embeddings (local, fast)         ▲
        └──────────────┬───────────────────┘
                       │ LLM calls (cloud, during seed only)
              ┌────────┴────────┐
              │   Graphiti      │
              │   (FalkorDB)    │
              └─────────────────┘
```

---

## Option A: Google Gemini (Recommended)

### Why Gemini

- **Native `GeminiClient`** in graphiti-core — no adapters or proxies
- **Graphiti docs explicitly recommend Gemini** alongside OpenAI for structured output support
- **Native `GeminiEmbedder` and `GeminiRerankerClient`** — full stack without OpenAI dependency
- **Generous free tier** — 1,000+ requests/day on Flash models, no credit card needed to start
- **No thinking mode contamination** — Flash models don't produce `<think>` blocks
- **Strategic alignment** — Gemini 3.1 Pro already planned for the Forge/GuardKit Factory; one provider for both

### Gemini Models for Graphiti

| Model | Cost (input/output per M) | Context | Notes |
|---|---|---|---|
| `gemini-2.5-flash` | $0.30 / $2.50 | 1M | **Best value for entity extraction** — good structured output, very cheap |
| `gemini-3-flash` | $0.50 / $3.00 | 1M | Newer generation, slightly more capable |
| `gemini-2.5-flash-lite` | $0.10 / $0.40 | 1M | Ultra-cheap for `small_model` tasks |
| `gemini-3.1-pro` | $2.00 / $12.00 | 1M | Overkill for Graphiti; save for the Forge |

**Recommendation:** `gemini-2.5-flash` as `model`, same for `small_model` (or
`gemini-2.5-flash-lite` if you want to shave costs on simpler extraction tasks).

### Estimated Monthly Cost

| Usage Pattern | Tokens/month | Gemini Cost (2.5 Flash) |
|---|---|---|
| Light (2-3 seeds/week) | ~2-4M | **£0.50-3** |
| Moderate (daily seeding) | ~10-15M | **£3-10** |
| Heavy (multiple daily) | ~30-50M | **£10-35** |

### Installation

```bash
# On GB10, in the guardkit venv:
pip install "graphiti-core[google-genai]"
```

### Environment Variables (.env)

```bash
# Google Gemini — entity extraction LLM
GOOGLE_API_KEY=your_google_api_key_here

# No OpenAI key needed — Gemini handles LLM, reranker, and optionally embeddings
# Keep local embeddings on GB10 (unchanged)
OPENAI_API_KEY=not-needed-vllm-local

# Semaphore — Gemini free tier is generous, can start higher than Groq
SEMAPHORE_LIMIT=5
```

### Python Configuration

```python
from graphiti_core import Graphiti
from graphiti_core.llm_client.gemini_client import GeminiClient, LLMConfig
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.gemini_reranker_client import GeminiRerankerClient

# --- LLM: Gemini cloud ---
gemini_llm = GeminiClient(
    config=LLMConfig(
        api_key="<your-google-api-key>",    # or os.environ["GOOGLE_API_KEY"]
        model="gemini-2.5-flash",            # Best value for entity extraction
    )
)

# --- Embeddings: Local vLLM on GB10 (stays running, tiny footprint) ---
local_embedder = OpenAIEmbedder(
    config=OpenAIEmbedderConfig(
        api_key="not-needed-vllm-local",
        embedding_model="nomic-ai/nomic-embed-text-v1.5",
        embedding_dim=768,
        base_url="http://localhost:8001/v1",  # GB10 vLLM embeddings port
    )
)

# --- Cross-encoder: Gemini reranker (no OpenAI key needed) ---
gemini_reranker = GeminiRerankerClient(
    config=LLMConfig(
        api_key="<your-google-api-key>",
        model="gemini-2.5-flash",  # Flash is fine for reranking
    )
)

# --- Assemble Graphiti ---
graphiti = Graphiti(
    "redis://localhost:6379",        # FalkorDB on GB10 (or Synology)
    llm_client=gemini_llm,
    embedder=local_embedder,
    cross_encoder=gemini_reranker,
)
```

### Gemini Rate Limits

Gemini's free tier is significantly more generous than OpenAI or Groq:

```bash
# Free tier:     SEMAPHORE_LIMIT=3-5   (generous RPM, unlikely to hit 429s)
# Paid tier:     SEMAPHORE_LIMIT=8-15  (higher limits, per-project)
SEMAPHORE_LIMIT=5
```

### Fully OpenAI-Free

The Gemini configuration above requires **zero OpenAI dependency**. LLM, reranker,
and optionally embeddings can all run through Gemini. We keep local embeddings only
because they're already working on GB10 and avoid a FalkorDB index rebuild.

## Option B: Groq (Alternative — When Developer Tier Opens)

> **Status (April 2026):** Groq Developer tier upgrades are temporarily
> unavailable due to high demand. Free tier rate limits may be too low for
> Graphiti's concurrent LLM calls during seeding. Revisit when Developer tier
> reopens. The analysis below remains valid for when it becomes available.

- **Native `GroqClient`** in graphiti-core — no proxies or adapters needed
- **Llama 3.3 70B** at $0.59/M input, $0.79/M output — quality comparable to GPT-4o
- **662 tokens/sec** for Qwen3 32B, **394 tokens/sec** for Llama 3.3 70B — faster than local vLLM
- Free tier available (no credit card), Developer tier gives 10× rate limits for 25% token discount
- Graphiti's bursty seeding workload fits Groq perfectly — you're not sustaining high throughput

### Estimated Monthly Cost

A typical `guardkit graphiti seed` session (20-30 documents) consumes roughly 500K-2M tokens across entity extraction, relationship extraction, entity resolution, and fact validation calls.

| Usage Pattern | Tokens/month | Groq Cost (GPT-OSS 120B) |
|---|---|---|
| Light (2-3 seeds/week) | ~2-4M | **£0.50-2** |
| Moderate (daily seeding) | ~10-15M | **£3-6** |
| Heavy (multiple daily) | ~30-50M | **£10-20** |

### Installation

```bash
# On GB10, in the guardkit venv:
pip install "graphiti-core[groq]"
```

### Environment Variables (.env)

```bash
# Groq — entity extraction LLM
GROQ_API_KEY=gsk_your_groq_api_key_here

# Keep local embeddings on GB10 (no OpenAI key needed for embeddings)
# The OPENAI_API_KEY below is ONLY for the cross-encoder/reranker
# If you want to avoid OpenAI entirely, see "Fully OpenAI-Free" section below
OPENAI_API_KEY=not-needed-vllm-local

# Semaphore — Groq free tier is limited, start conservative
SEMAPHORE_LIMIT=3
```

### Python Configuration

```python
from graphiti_core import Graphiti
from graphiti_core.llm_client.groq_client import GroqClient, LLMConfig
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient

# --- LLM: Groq cloud ---
groq_llm = GroqClient(
    config=LLMConfig(
        api_key="<your-groq-api-key>",      # or os.environ["GROQ_API_KEY"]
        model="openai/gpt-oss-120b",         # Best fit: no thinking mode, native structured output
        small_model="openai/gpt-oss-20b",    # Fast, cheap for simpler extraction tasks
    )
)

# --- Embeddings: Local vLLM on GB10 (stays running, tiny footprint) ---
local_embedder = OpenAIEmbedder(
    config=OpenAIEmbedderConfig(
        api_key="not-needed-vllm-local",
        embedding_model="nomic-ai/nomic-embed-text-v1.5",
        embedding_dim=768,
        base_url="http://localhost:8001/v1",  # GB10 vLLM embeddings port
    )
)

# --- Cross-encoder: Also via Groq (avoids needing OpenAI key entirely) ---
# Note: This uses the Groq LLM for reranking. If you prefer OpenAI's
# reranker for quality, swap this for OpenAIRerankerClient with an
# OpenAI API key.
groq_reranker_config = LLMConfig(
    api_key="<your-groq-api-key>",
    model="openai/gpt-oss-20b",  # Small model is fine for reranking
)
cross_encoder = OpenAIRerankerClient(
    client=groq_llm,
    config=groq_reranker_config,
)

# --- Assemble Graphiti ---
graphiti = Graphiti(
    "redis://localhost:6379",        # FalkorDB on GB10 (or Synology)
    llm_client=groq_llm,
    embedder=local_embedder,
    cross_encoder=cross_encoder,
)
```

### Groq Rate Limit Tuning

```bash
# Free tier:     SEMAPHORE_LIMIT=1-2  (avoid 429s)
# Developer tier: SEMAPHORE_LIMIT=5-8  (25% cheaper tokens, 10× limits)
# If you hit rate limits, lower this first before anything else
SEMAPHORE_LIMIT=3
```

### ⚠️ CRITICAL: Thinking Mode Incompatibility

**Learned the hard way (March 2026):** Qwen3 models' thinking mode is
fundamentally incompatible with Graphiti's entity extraction. Qwen3 outputs
`<think>` blocks before JSON — even with `--reasoning-parser qwen3` stripping
them from the response, the model still *generates thousands of thinking
tokens internally*, causing **900+ second timeouts** on Graphiti episodes.

This is why Qwen2.5-14B-Instruct was chosen locally — it's a pure instruct
model with no thinking mode, and `xgrammar` enforces JSON schema at the
token level for guaranteed valid structured output.

**The same risk applies to cloud models.** Any model with a thinking/reasoning
mode that can't be reliably disabled at the API level is dangerous for
Graphiti's structured output pipeline.

### Model Safety Matrix for Groq

| Model | Thinking Mode | Safe? | Cost (in/out per M) | Speed | Notes |
|---|---|---|---|---|---|
| `openai/gpt-oss-120b` | **None** | ✅ **Safe** | $0.15 / $0.60 | 500 t/s | **Recommended.** Native structured output, MoE (~5.1B active), OpenAI-format JSON |
| `openai/gpt-oss-20b` | **None** | ✅ **Safe** | $0.075 / $0.30 | 1000 t/s | Budget option, may struggle with complex entity extraction |
| `meta-llama/llama-3.3-70b-versatile` | **None** | ✅ **Safe** | $0.59 / $0.79 | 394 t/s | Highest quality on Groq, pure instruct |
| `qwen/qwen3-32b` | **YES (toggleable)** | ⚠️ **Risky** | $0.29 / $0.59 | 662 t/s | Same `<think>` block family that caused 900s timeouts locally |
| `meta-llama/llama-3.1-8b-instant` | **None** | ✅ **Safe** | $0.05 / $0.08 | 840 t/s | Too small for main model; fine for `small_model` |

### Why GPT-OSS 120B is the Best Fit

1. **No thinking mode** — zero risk of `<think>` block contamination
2. **Native structured output support** — function calling + JSON mode, exactly what Graphiti's extraction prompts expect
3. **OpenAI-format compatibility** — Graphiti's structured output parsing was designed around OpenAI's response format; GPT-OSS follows the same conventions
4. **MoE efficiency** — only ~5.1B parameters active per token despite "120B" label
5. **Graphiti's own Ollama example uses `gpt-oss:120b`** — it's a tested combination
6. **Cost** — $0.15/M input is cheaper than Llama 3.3 70B ($0.59/M)

**Recommendation:** Use `openai/gpt-oss-120b` as `model` and `openai/gpt-oss-20b` as `small_model`. Avoid `qwen3-32b` — same thinking-mode family that broke Graphiti locally.

---

## Option C: AWS Bedrock

### Why Bedrock

- You already have an AWS account (FinProxy, GCSE Tutor deployment pipeline)
- Access to Claude Haiku, Llama, Mistral models
- Pay-per-token, scales to zero — no idle costs
- Enterprise-grade reliability

### The Catch

Graphiti doesn't have a native Bedrock client. Two practical approaches:

#### Approach B1: Use Anthropic API Directly (Simplest)

Graphiti has a native `AnthropicClient`. Rather than going through Bedrock, use Anthropic's API directly with Claude Haiku. This is the simplest path if you're okay with an Anthropic API key.

**Cost:** Claude 3.5 Haiku is $1.00/M input, $5.00/M output.

| Usage Pattern | Tokens/month | Anthropic Cost (Haiku) |
|---|---|---|
| Light (2-3 seeds/week) | ~2-4M | **£2-8** |
| Moderate (daily seeding) | ~10-15M | **£10-30** |
| Heavy (multiple daily) | ~30-50M | **£30-100** |

More expensive than Groq, but still well under £100/month for typical use.

```bash
pip install "graphiti-core[anthropic]"
```

```python
from graphiti_core import Graphiti
from graphiti_core.llm_client.anthropic_client import AnthropicClient, LLMConfig
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient

# --- LLM: Anthropic Claude (direct API) ---
anthropic_llm = AnthropicClient(
    config=LLMConfig(
        api_key="<your-anthropic-api-key>",
        model="claude-3-5-haiku-20241022",       # Cheap, good at structured output
        small_model="claude-3-5-haiku-20241022",  # Haiku for both (it's already small)
    )
)

# --- Embeddings: Local vLLM on GB10 ---
local_embedder = OpenAIEmbedder(
    config=OpenAIEmbedderConfig(
        api_key="not-needed-vllm-local",
        embedding_model="nomic-ai/nomic-embed-text-v1.5",
        embedding_dim=768,
        base_url="http://localhost:8001/v1",
    )
)

# --- Cross-encoder: Use Anthropic too (avoids OpenAI key) ---
# Note: AnthropicClient doesn't directly slot into OpenAIRerankerClient.
# Simplest: use a small OpenAI model for reranking, or use the Anthropic
# client as the reranker via the generic client pattern.
# For now, using OpenAI's nano model is the path of least resistance:
cross_encoder = OpenAIRerankerClient(
    config=LLMConfig(
        api_key="<your-openai-api-key>",  # Needed just for reranker
        model="gpt-4.1-nano",
    )
)

# --- Assemble ---
graphiti = Graphiti(
    "redis://localhost:6379",
    llm_client=anthropic_llm,
    embedder=local_embedder,
    cross_encoder=cross_encoder,
)
```

**Downside:** Requires both an Anthropic key AND an OpenAI key (for reranker). See "Fully OpenAI-Free" section below to eliminate the OpenAI dependency.

#### Approach B2: AWS Bedrock via LiteLLM Proxy

If you specifically want everything through your AWS account (single billing), run a lightweight LiteLLM proxy on GB10 that translates OpenAI-format requests to Bedrock API calls.

```bash
# Install LiteLLM
pip install litellm[proxy]

# Start the proxy (runs on port 4000, minimal resource usage)
litellm --model bedrock/anthropic.claude-3-5-haiku-20241022-v1:0 \
        --port 4000 \
        --drop_params
```

Then configure Graphiti to point at the local proxy:

```python
from graphiti_core import Graphiti
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient

# --- LLM: Bedrock via LiteLLM proxy ---
bedrock_config = LLMConfig(
    api_key="not-needed-litellm",
    model="bedrock/anthropic.claude-3-5-haiku-20241022-v1:0",
    small_model="bedrock/anthropic.claude-3-5-haiku-20241022-v1:0",
    base_url="http://localhost:4000/v1",
)

bedrock_llm = OpenAIGenericClient(config=bedrock_config)

# --- Embeddings: Local vLLM on GB10 ---
local_embedder = OpenAIEmbedder(
    config=OpenAIEmbedderConfig(
        api_key="not-needed-vllm-local",
        embedding_model="nomic-ai/nomic-embed-text-v1.5",
        embedding_dim=768,
        base_url="http://localhost:8001/v1",
    )
)

# --- Cross-encoder: Also via LiteLLM proxy ---
cross_encoder = OpenAIRerankerClient(
    client=bedrock_llm,
    config=bedrock_config,
)

# --- Assemble ---
graphiti = Graphiti(
    "redis://localhost:6379",
    llm_client=bedrock_llm,
    embedder=local_embedder,
    cross_encoder=cross_encoder,
)
```

**LiteLLM AWS credentials** — set in the environment where litellm runs:

```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION_NAME=eu-west-2  # or your preferred region
```

**Bedrock Model Pricing (Haiku via Bedrock):**

Same as Anthropic direct pricing but billed through AWS. Batch inference gives 50% discount for async workloads.

---

## Fully OpenAI-Free Configuration

Both Groq and Anthropic configs above can avoid any OpenAI dependency by using the same LLM client for the cross-encoder/reranker:

**Groq (fully OpenAI-free):**
```python
# Use GroqClient for reranking too
cross_encoder = OpenAIRerankerClient(
    client=groq_llm,  # Reuse the GroqClient instance
    config=LLMConfig(
        api_key="<your-groq-api-key>",
        model="openai/gpt-oss-20b",
    ),
)
```

This means you need ZERO OpenAI API key. Just `GROQ_API_KEY` + local embeddings.

---

## Switching Between Local and Cloud

For maximum flexibility, create a simple config toggle. In your `.env`:

```bash
# Toggle: "local" | "gemini" | "groq" | "bedrock"
GRAPHITI_LLM_PROVIDER=gemini

# Local (when GPU is free)
GRAPHITI_LOCAL_LLM_URL=http://localhost:8000/v1
GRAPHITI_LOCAL_LLM_MODEL=Qwen/Qwen2.5-14B-Instruct-FP8

# Gemini (primary)
GOOGLE_API_KEY=your_google_api_key_here

# Groq (alternative, when Developer tier available)
GROQ_API_KEY=gsk_your_key_here

# Bedrock (via LiteLLM)
GRAPHITI_BEDROCK_PROXY_URL=http://localhost:4000/v1
```

Then in your guardkit Graphiti initialisation code:

```python
import os

provider = os.environ.get("GRAPHITI_LLM_PROVIDER", "local")

if provider == "gemini":
    from graphiti_core.llm_client.gemini_client import GeminiClient
    llm_client = GeminiClient(config=LLMConfig(
        api_key=os.environ["GOOGLE_API_KEY"],
        model="gemini-2.5-flash",
    ))
elif provider == "groq":
    from graphiti_core.llm_client.groq_client import GroqClient
    llm_client = GroqClient(config=LLMConfig(
        api_key=os.environ["GROQ_API_KEY"],
        model="openai/gpt-oss-120b",
        small_model="openai/gpt-oss-20b",
    ))
elif provider == "bedrock":
    from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
    llm_client = OpenAIGenericClient(config=LLMConfig(
        api_key="not-needed",
        model="bedrock/anthropic.claude-3-5-haiku-20241022-v1:0",
        small_model="bedrock/anthropic.claude-3-5-haiku-20241022-v1:0",
        base_url=os.environ["GRAPHITI_BEDROCK_PROXY_URL"],
    ))
else:  # local
    from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
    llm_client = OpenAIGenericClient(config=LLMConfig(
        api_key="not-needed-vllm-local",
        model=os.environ.get("GRAPHITI_LOCAL_LLM_MODEL", "Qwen/Qwen2.5-14B-Instruct-FP8"),
        small_model=os.environ.get("GRAPHITI_LOCAL_LLM_MODEL", "Qwen/Qwen2.5-14B-Instruct-FP8"),
        base_url=os.environ.get("GRAPHITI_LOCAL_LLM_URL", "http://localhost:8000/v1"),
    ))

# Embeddings always local
embedder = OpenAIEmbedder(config=OpenAIEmbedderConfig(
    api_key="not-needed-vllm-local",
    embedding_model="nomic-ai/nomic-embed-text-v1.5",
    embedding_dim=768,
    base_url="http://localhost:8001/v1",
))
```

---

## Migration Steps

1. **Get a Google API key** — https://aistudio.google.com/apikey (free tier, no credit card)
2. **Install the Gemini extra:** `pip install "graphiti-core[google-genai]"`
3. **Update guardkit:** Add `"gemini"` to `VALID_PROVIDERS` in `guardkit/knowledge/config.py`, add `GeminiClient` factory branch in `graphiti_client.py`, add `graphiti-core[google-genai]` to `pyproject.toml` (same pattern as TASK-REV-C7A3 identified for Groq, just different provider)
4. **Update `.env`** with `GOOGLE_API_KEY` and `GRAPHITI_LLM_PROVIDER=gemini`
5. **Update `.guardkit/graphiti.yaml`** — set `llm_provider: gemini`, `llm_model: gemini-2.5-flash`
6. **Stop the Qwen2.5-14B vLLM instance** on port 8000 (keep port 8001 embeddings running)
7. **Test:** Run a small `guardkit graphiti seed` against one document
8. **Verify:** Check entity extraction quality matches what you had locally
9. **Free the GPU:** Now you can run fine-tuning, host Gemma 4 31B, run dataset factory — all while Graphiti queries still work (they don't need the LLM)

---

## Decision Summary

| Criteria | Gemini (2.5 Flash) | Groq (GPT-OSS 120B) | Bedrock (via LiteLLM) |
|---|---|---|---|
| **Setup complexity** | Trivial (native client) | Trivial (native client) | Moderate (LiteLLM proxy) |
| **Cost (light use)** | ~£0.50-3/mo | ~£0.50-2/mo | ~£2-8/mo |
| **Cost (moderate)** | ~£3-10/mo | ~£3-6/mo | ~£10-30/mo |
| **Needs OpenAI key** | No | No | No |
| **Structured output** | Excellent (Graphiti-recommended) | Excellent (native support) | Excellent (Claude) |
| **Thinking mode risk** | None | None (GPT-OSS) | None (Claude) |
| **Rate limits** | Very generous free tier | Dev tier unavailable (Apr 2026) | AWS-grade |
| **Strategic fit** | Gemini 3.1 Pro also used for Forge | Separate provider | AWS billing consolidation |
| **Billing** | Google account | Groq account | AWS account |

**Recommendation:** Start with **Google Gemini 2.5 Flash**. Native graphiti-core support, excellent structured output (Graphiti explicitly recommends Gemini alongside OpenAI), generous free tier for testing, no thinking mode risk, and strategic alignment with Gemini 3.1 Pro for the Forge. Groq remains a viable alternative when the Developer tier reopens.
