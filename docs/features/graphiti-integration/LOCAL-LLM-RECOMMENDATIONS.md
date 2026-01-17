# Local LLM Recommendations for M2 Max 96GB

## Your Hardware

| Component | Specification | LLM Relevance |
|-----------|---------------|---------------|
| **Chip** | Apple M2 Max | Excellent for local LLM inference |
| **Memory** | 96GB Unified | Can run 70B+ models comfortably |
| **GPU Cores** | 38 | Hardware acceleration for inference |
| **Memory Bandwidth** | ~400 GB/s | Key bottleneck for token generation |

### Why Apple Silicon is Great for LLMs

Apple's unified memory architecture means:
- **No VRAM limit** - The GPU shares all 96GB with CPU
- **No memory copying** - Data doesn't move between CPU/GPU RAM
- **High bandwidth** - 400 GB/s (M2 Max) is excellent for LLM inference

**Reference from user with same setup**:
> "With my M2 Max, I get approx. 60 token/s for llama-2 7B (Q4 quantized). And because I also have 96GB RAM for my GPU, I also get approx. 8 token/s for llama-2 70B (Q4) inference."

---

## Critical Requirement: Structured Output

Graphiti requires reliable **structured JSON output** for:
- Entity extraction
- Fact extraction  
- Relationship extraction
- Deduplication

**From Graphiti docs**:
> "Graphiti works best with LLM services that support Structured Output (such as OpenAI and Gemini). Using other services may result in incorrect output schemas and ingestion failures. This is particularly problematic when using smaller models."

**This means**: We need models that reliably follow JSON schemas, not just any fast model.

---

## Recommended Models for Your Setup

### Tier 1: Best Choice - Qwen2.5 72B (Structured Output Champion)

**Why Qwen2.5**:
> "Significant advancements in instruction following... understanding structured data (e.g., tables), and **generating structured outputs, especially in JSON format**."

| Model | Size | Memory (Q4) | Speed Est. | Structured Output |
|-------|------|-------------|------------|-------------------|
| `qwen2.5:72b-instruct-q4_K_M` | 72B | ~45GB | ~8-10 tok/s | ⭐⭐⭐⭐⭐ Excellent |

```bash
# Install
ollama pull qwen2.5:72b-instruct-q4_K_M

# Test structured output
ollama run qwen2.5:72b-instruct-q4_K_M "Extract entities from this text as JSON: 'John works at Acme Corp in London'"
```

**Memory usage**: ~45-50GB leaves plenty of headroom for context and other apps.

### Tier 2: Faster Alternative - Qwen2.5 32B

If 72B is too slow for your workflow:

| Model | Size | Memory (Q4) | Speed Est. | Structured Output |
|-------|------|-------------|------------|-------------------|
| `qwen2.5:32b-instruct-q4_K_M` | 32B | ~20GB | ~20-25 tok/s | ⭐⭐⭐⭐ Very Good |

```bash
ollama pull qwen2.5:32b-instruct-q4_K_M
```

**Trade-off**: Faster but slightly less capable at complex reasoning.

### Tier 3: Speed King - Qwen2.5 14B

For development/testing where speed matters more:

| Model | Size | Memory (Q4) | Speed Est. | Structured Output |
|-------|------|-------------|------------|-------------------|
| `qwen2.5:14b-instruct-q4_K_M` | 14B | ~10GB | ~40-50 tok/s | ⭐⭐⭐ Good |

```bash
ollama pull qwen2.5:14b-instruct
```

### Alternative: Llama 3.3 70B

Meta's latest, comparable to Qwen:

| Model | Size | Memory (Q4) | Speed Est. | Structured Output |
|-------|------|-------------|------------|-------------------|
| `llama3.3:70b-instruct-q4_K_M` | 70B | ~43GB | ~8-10 tok/s | ⭐⭐⭐⭐ Very Good |

```bash
ollama pull llama3.3:70b-instruct-q4_K_M
```

### NOT Recommended

| Model | Why Not |
|-------|---------|
| Models < 14B | Unreliable structured output for Graphiti |
| DeepSeek-R1 | Great for reasoning, overkill for entity extraction |
| Code-specific models | Optimized for code, not JSON extraction |

---

## Memory Planning

With 96GB unified memory:

```
┌─────────────────────────────────────────────────────────────┐
│                     96GB Unified Memory                      │
├─────────────────────────────────────────────────────────────┤
│ macOS + Apps           │ ~10-15GB                           │
│ Qwen2.5 72B (Q4)       │ ~45GB                              │
│ KV Cache (8K context)  │ ~5-8GB                             │
│ Sentence Transformers  │ ~1GB                               │
│ FalkorDB + Graphiti    │ ~2-4GB                             │
│ Headroom               │ ~20-25GB                           │
└─────────────────────────────────────────────────────────────┘
```

**You can comfortably run 72B models** with room to spare.

---

## Performance Expectations

Based on M2 Max 96GB reports:

| Model Size | Quantization | Expected Speed | Notes |
|------------|--------------|----------------|-------|
| 7B | Q4_K_M | ~60 tok/s | Very fast |
| 14B | Q4_K_M | ~40-50 tok/s | Fast |
| 32B | Q4_K_M | ~20-25 tok/s | Good |
| 70B | Q4_K_M | ~8-10 tok/s | Acceptable for batch |

**For Graphiti**: Speed is less critical than reliability. Graphiti processes episodes in batch, so 8-10 tok/s is fine.

---

## Recommended Setup

### For Development (Best Balance)

```yaml
# Graphiti config.yaml
llm:
  provider: "openai"
  model: "qwen2.5:32b-instruct"
  api_base: "http://localhost:11434/v1"
  api_key: "ollama"

embedder:
  provider: "sentence_transformers"
  model: "all-MiniLM-L6-v2"
```

### For Production Quality (Maximum Capability)

```yaml
# Graphiti config.yaml
llm:
  provider: "openai"
  model: "qwen2.5:72b-instruct-q4_K_M"
  api_base: "http://localhost:11434/v1"
  api_key: "ollama"

embedder:
  provider: "sentence_transformers"
  model: "all-MiniLM-L6-v2"
```

---

## Quick Setup Commands

```bash
# 1. Install Ollama (if not already)
brew install ollama

# 2. Start Ollama service
ollama serve

# 3. Pull recommended model (in another terminal)
ollama pull qwen2.5:72b-instruct-q4_K_M

# 4. Pull smaller model for testing
ollama pull qwen2.5:14b-instruct

# 5. Test structured output
ollama run qwen2.5:72b-instruct-q4_K_M << 'EOF'
Extract all entities and relationships from this text as valid JSON:

"Alice is the CEO of TechCorp. She reports to the board of directors. 
TechCorp is headquartered in San Francisco and was founded in 2015."

Return ONLY valid JSON with "entities" and "relationships" arrays.
EOF
```

---

## Comparison: Local vs API

| Aspect | Ollama Local | Anthropic API |
|--------|--------------|---------------|
| **Cost** | Free (electricity only) | Per-token pricing |
| **Speed** | ~8-10 tok/s (70B) | ~50-100 tok/s |
| **Privacy** | 100% local | Data sent to cloud |
| **Reliability** | Depends on model | Very reliable |
| **Quality** | Very good (72B) | Excellent (Claude) |
| **Setup** | Requires hardware | Just API key |

**Recommendation**: 
- **Development**: Use Ollama local for cost savings and privacy
- **Production/Quality-critical**: Consider Anthropic API for reliability

---

## Summary

**Your M2 Max 96GB can run**:
- ✅ Qwen2.5 72B (Q4) - **Recommended for structured output**
- ✅ Llama 3.3 70B (Q4) - Good alternative
- ✅ Any model up to ~70B parameters

**Best choice for Graphiti**: `qwen2.5:72b-instruct-q4_K_M`
- Explicitly designed for structured JSON output
- 72B has excellent reasoning capability
- Fits comfortably in your 96GB

**Fully local setup** (no API keys needed):
- LLM: Qwen2.5 72B via Ollama
- Embeddings: Sentence Transformers (all-MiniLM-L6-v2)
- Database: FalkorDB in Docker

This gives you complete data sovereignty with no external API dependencies.
