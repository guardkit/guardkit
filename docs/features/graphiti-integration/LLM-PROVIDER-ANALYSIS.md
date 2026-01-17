# Graphiti LLM Provider Deep Dive Analysis

## ⚠️ Critical Clarification: Claude Code ≠ Graphiti

**Claude Code** (the CLI tool) and **Graphiti** (the knowledge graph library) are **separate systems**:

| System | What It Is | API Usage |
|--------|------------|----------|
| **Claude Code** | Anthropic's CLI development tool | Uses your **Claude Max subscription** (no API key) |
| **Graphiti** | Zep's knowledge graph library | Makes its **own API calls** (needs API keys OR local LLMs) |

**Your Claude Max subscription does NOT cover Graphiti's API calls.**

Graphiti makes many LLM calls per episode (entity extraction, fact extraction, deduplication, etc.) - these would incur separate API costs if using Anthropic/OpenAI APIs.

### The Solution: Fully Local Setup

With your M2 Max 96GB, you can run Graphiti **entirely locally** with:
- **LLM**: Qwen2.5 72B via Ollama (no API key)
- **Embeddings**: Sentence Transformers (no API key)
- **Database**: FalkorDB in Docker

**Result**: Zero external API dependencies, complete data sovereignty.

See [Local LLM Recommendations](./LOCAL-LLM-RECOMMENDATIONS.md) for detailed hardware-specific guidance.

---

## Executive Summary

**Question**: Does Graphiti support all of our planned LLM deployment scenarios?

| Scenario | Current Support | Status | Notes |
|----------|-----------------|--------|-------|
| **Fully Local (Ollama)** | ✅ Via OpenAI-compatible API | **Recommended** | No API keys needed |
| Anthropic Claude (direct API) | ✅ Native | Ready | Requires separate API key (not Claude Max) |
| OpenAI (for embeddings) | ✅ Native | Ready | Default provider |
| Amazon Bedrock | ⚠️ PR Open (#1107) | In Progress | Use LiteLLM workaround |

**Bottom Line for M2 Max 96GB**: 
- ✅ **Fully local with Qwen2.5 72B + Sentence Transformers**: Best choice - no API costs
- ✅ **Anthropic Claude API**: Works but costs money (separate from Claude Max subscription)
- ⚠️ **Amazon Bedrock**: Not native yet, but achievable via LiteLLM proxy

---

## Current Provider Support

### 1. Anthropic Claude (Direct) ✅

**Status**: Fully supported natively

```bash
pip install graphiti-core[anthropic]
```

```python
from graphiti_core import Graphiti
from graphiti_core.llm_client import AnthropicClient
from graphiti_core.llm_client.config import LLMConfig

# Configure Anthropic client
llm_client = AnthropicClient(
    config=LLMConfig(
        model="claude-sonnet-4-20250514",
        small_model="claude-3-5-haiku-20241022"
    )
)

# Still need OpenAI for embeddings
graphiti = Graphiti(
    uri="redis://localhost:6379",
    llm_client=llm_client,
    # embedder still uses OpenAI by default
)
```

**Important caveat**: Even with Anthropic for LLM, you still need OpenAI API key for:
- Embeddings (text-embedding-3-small)
- Reranking

**MCP Server config.yaml**:
```yaml
llm:
  provider: "anthropic"
  model: "claude-sonnet-4-20250514"

# Still needs OpenAI for embeddings
embedder:
  provider: "openai"  # Default
```

### 2. OpenAI ✅

**Status**: Default provider, fully supported

```python
from graphiti_core import Graphiti

# Default - uses OpenAI for everything
graphiti = Graphiti(
    uri="redis://localhost:6379"
)
```

Required env vars:
```bash
OPENAI_API_KEY=your-key
```

### 3. Ollama (Local LLMs) ✅

**Status**: Fully supported via OpenAI-compatible API

```python
from graphiti_core import Graphiti
from graphiti_core.llm_client import OpenAIGenericClient  # NOT OpenAIClient!
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.embedder import SentenceTransformerEmbedder

# Use OpenAIGenericClient for Ollama
llm_client = OpenAIGenericClient(
    config=LLMConfig(
        model="llama3.1:70b",  # Your Ollama model
        api_base="http://localhost:11434/v1",
        api_key="ollama"  # Dummy key required
    )
)

# Use local embeddings too
embedder = SentenceTransformerEmbedder(
    model="all-MiniLM-L6-v2"
)

graphiti = Graphiti(
    uri="redis://localhost:6379",
    llm_client=llm_client,
    embedder=embedder
)
```

**MCP Server config.yaml**:
```yaml
llm:
  provider: "openai"  # Use openai provider with custom base
  model: "llama3.1:70b"
  api_base: "http://localhost:11434/v1"
  api_key: "ollama"

embedder:
  provider: "sentence_transformers"
  model: "all-MiniLM-L6-v2"
```

**Critical Warning from docs**:
> Graphiti works best with LLM services that support Structured Output (such as OpenAI and Gemini). Using other services may result in incorrect output schemas and ingestion failures. This is particularly problematic when using smaller models.

**Recommendation**: Use larger Ollama models (70B+) for reliable structured output.

### 4. Amazon Bedrock ⚠️

**Status**: PR #1107 open, not yet merged (as of Dec 16, 2025)

The PR title: "feat: Add Amazon Bedrock integration for LLM, embeddings, and reranking"

**When merged**, it would look like:
```python
from graphiti_core.llm_client import BedrockClient  # Future

llm_client = BedrockClient(
    model="anthropic.claude-3-5-sonnet-20241022-v2:0",
    region="us-east-1"
)
```

**Current workaround**: Use LiteLLM as proxy (see below)

---

## LiteLLM Proxy: The Universal Solution

LiteLLM provides an OpenAI-compatible API that can route to ANY provider including Bedrock. This is the **recommended workaround** for Bedrock until native support lands.

### Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │      │                 │
│  Graphiti MCP   │─────▶│  LiteLLM Proxy  │─────▶│  AWS Bedrock    │
│  Server         │      │  (OpenAI API)   │      │  (Claude)       │
│                 │      │                 │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                              │
                              ▼
                         Also routes to:
                         - Anthropic Direct
                         - OpenAI
                         - Ollama
                         - Azure OpenAI
                         - Google Gemini
```

### LiteLLM Setup for Bedrock

```yaml
# litellm_config.yaml
model_list:
  # Bedrock Claude
  - model_name: claude-bedrock
    litellm_params:
      model: bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0
      aws_access_key_id: os.environ/AWS_ACCESS_KEY_ID
      aws_secret_access_key: os.environ/AWS_SECRET_ACCESS_KEY
      aws_region_name: us-east-1

  # Bedrock Embeddings
  - model_name: bedrock-embeddings
    litellm_params:
      model: bedrock/amazon.titan-embed-text-v2:0
      aws_access_key_id: os.environ/AWS_ACCESS_KEY_ID
      aws_secret_access_key: os.environ/AWS_SECRET_ACCESS_KEY
      aws_region_name: us-east-1
```

```bash
# Start LiteLLM proxy
pip install 'litellm[proxy]'
litellm --config litellm_config.yaml --port 4000
```

### Graphiti with LiteLLM Proxy

```python
from graphiti_core import Graphiti
from graphiti_core.llm_client import OpenAIGenericClient
from graphiti_core.llm_client.config import LLMConfig

# Point Graphiti at LiteLLM proxy
llm_client = OpenAIGenericClient(
    config=LLMConfig(
        model="claude-bedrock",  # Model name from LiteLLM config
        api_base="http://localhost:4000/v1",
        api_key="sk-anything"  # LiteLLM master key
    )
)

graphiti = Graphiti(
    uri="redis://localhost:6379",
    llm_client=llm_client,
    # Can also use LiteLLM for embeddings
)
```

**MCP Server config.yaml**:
```yaml
llm:
  provider: "openai"
  model: "claude-bedrock"
  api_base: "http://localhost:4000/v1"
  api_key: "${LITELLM_MASTER_KEY}"

embedder:
  provider: "openai"
  model: "bedrock-embeddings"
  api_base: "http://localhost:4000/v1"
  api_key: "${LITELLM_MASTER_KEY}"
```

---

## Embedding Provider Options

Graphiti requires embeddings for semantic search. Options:

| Provider | Support | Model | Notes |
|----------|---------|-------|-------|
| OpenAI | ✅ Default | text-embedding-3-small | Requires API key |
| Sentence Transformers | ✅ Local | all-MiniLM-L6-v2 | No API key, runs locally |
| Voyage AI | ✅ Native | voyage-3 | Requires API key |
| Google Gemini | ✅ Native | embedding-001 | Requires API key |
| Bedrock Titan | ⚠️ Via LiteLLM | amazon.titan-embed-text-v2 | Needs LiteLLM proxy |

**For fully local/private setup**:
```yaml
embedder:
  provider: "sentence_transformers"
  model: "all-MiniLM-L6-v2"  # Runs locally, no API calls
```

---

## Deployment Scenarios

### Scenario 1: Claude Code GuardKit (Current)

**Goal**: Use Anthropic Claude for LLM, need embeddings

```yaml
# .env
ANTHROPIC_API_KEY=your-key
OPENAI_API_KEY=your-key  # For embeddings only

# config.yaml
llm:
  provider: "anthropic"
  model: "claude-sonnet-4-20250514"
embedder:
  provider: "openai"
```

**Assessment**: ✅ Fully supported today

### Scenario 2: Deep Agents GuardKit with Local LLMs

**Goal**: Run completely locally with Ollama, no external API calls

```yaml
# config.yaml
llm:
  provider: "openai"
  model: "llama3.1:70b"
  api_base: "http://localhost:11434/v1"
  api_key: "ollama"
embedder:
  provider: "sentence_transformers"
  model: "all-MiniLM-L6-v2"
```

**Assessment**: ✅ Fully supported today (with capable models)

### Scenario 3: Enterprise with Amazon Bedrock

**Goal**: Use Claude on Bedrock for data sovereignty

**Option A**: Wait for native support (PR #1107)
- Pros: Cleaner, native integration
- Cons: Timeline unknown, PR still in progress

**Option B**: Use LiteLLM proxy now
- Pros: Works today, proven pattern
- Cons: Additional service to manage

```yaml
# LiteLLM config
model_list:
  - model_name: claude-bedrock
    litellm_params:
      model: bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0
      aws_access_key_id: os.environ/AWS_ACCESS_KEY_ID
      aws_secret_access_key: os.environ/AWS_SECRET_ACCESS_KEY
      aws_region_name: eu-west-2  # UK region for data residency

# Graphiti config
llm:
  provider: "openai"
  api_base: "http://litellm:4000/v1"
  model: "claude-bedrock"
```

**Assessment**: ⚠️ Achievable via LiteLLM, native support pending

---

## Recommendations

### For Claude Code GuardKit (Now)

1. **Use Anthropic native** for LLM (`pip install graphiti-core[anthropic]`)
2. **Use OpenAI** for embeddings (simplest, well-tested)
3. **Configuration**:
   ```yaml
   llm:
     provider: "anthropic"
     model: "claude-sonnet-4-20250514"
   embedder:
     provider: "openai"
   ```

### For Deep Agents GuardKit (Future)

1. **Start with same config** as above (LangGraph doesn't affect Graphiti config)
2. **Plan for flexibility**:
   - Abstract Graphiti client behind interface
   - Config-driven provider selection
   - Test with Ollama early to validate structured output requirements

### For Enterprise/Bedrock Deployment

1. **Use LiteLLM proxy pattern** from day one if Bedrock is a requirement
2. **Watch PR #1107** for native support
3. **Architecture**:
   ```
   GuardKit → Graphiti MCP → LiteLLM Proxy → Bedrock
   ```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Bedrock PR not merged | Medium | Medium | LiteLLM workaround exists |
| Ollama structured output issues | Medium | High | Use 70B+ models, test early |
| OpenAI dependency for embeddings | Low | Low | Sentence Transformers alternative exists |
| LiteLLM adds complexity | Low | Low | Well-documented, widely used |

---

## Conclusion

**Graphiti fully supports our planned deployment scenarios**:

1. ✅ **Anthropic Claude (direct)**: Native support, ready now
2. ✅ **Local LLMs (Ollama)**: Supported via OpenAI-compatible API
3. ⚠️ **Amazon Bedrock**: Not native yet, but LiteLLM provides proven workaround

**Our design is not blocked**. We should:
1. Proceed with Anthropic native for initial Claude Code GuardKit
2. Plan LiteLLM integration layer for maximum flexibility
3. Monitor PR #1107 for native Bedrock support

---

## References

- [Graphiti LLM Configuration](https://help.getzep.com/graphiti/configuration/llm-configuration)
- [Graphiti GitHub - PR #1107 (Bedrock)](https://github.com/getzep/graphiti/pull/1107)
- [LiteLLM Bedrock Docs](https://docs.litellm.ai/docs/providers/bedrock)
- [LiteLLM Anthropic Docs](https://docs.litellm.ai/docs/providers/anthropic)
