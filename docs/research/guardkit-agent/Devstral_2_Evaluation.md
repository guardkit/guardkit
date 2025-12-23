# Devstral 2 Evaluation for GuardKit AutoBuild

**Date:** December 19, 2025  
**Status:** Evaluation Complete  
**Verdict:** ✅ Recommended for AutoBuild multi-model support

---

## Executive Summary

Devstral 2 is Mistral AI's latest coding model family, released December 9, 2025. It offers **state-of-the-art performance** for open-weight models at **7x lower cost** than Claude Sonnet, making it an excellent candidate for GuardKit AutoBuild's multi-model support.

**Key Stats:**
- **72.2% on SWE-bench Verified** (state-of-the-art for open-weight)
- **$0.40/$2.00 per million tokens** (vs Claude's $3/$15)
- **Currently FREE** during preview period
- **256K context window** - handles entire repositories
- **Apache 2.0 (Small) / Modified MIT (Full)** - open source

---

## Model Family

| Model | Parameters | SWE-bench | Price (in/out per M) | License | Deployment |
|-------|------------|-----------|---------------------|---------|------------|
| **Devstral 2** | 123B | 72.2% | $0.40 / $2.00 | Modified MIT | Cloud (4x H100) |
| **Devstral Small 2** | 24B | 68.0% | $0.10 / $0.30 | Apache 2.0 | Local (RTX 4090) |

### Size Comparison

- Devstral 2 is **5x smaller** than DeepSeek V3.2
- Devstral 2 is **8x smaller** than Kimi K2
- Devstral Small 2 runs on **consumer hardware**

---

## Performance Benchmarks

### SWE-bench Verified (Software Engineering)

| Model | Score | Notes |
|-------|-------|-------|
| Devstral 2 | **72.2%** | State-of-the-art open-weight |
| Devstral Small 2 | 68.0% | Matches models 5x larger |
| Claude Sonnet 4 | ~50% | Current GuardKit default |
| DeepSeek R1 | ~65% | Open weights alternative |

### Human Evaluation (via Cline agent tool)

Mistral evaluated Devstral 2 against other models using Cline-scaffolded tasks:

**Devstral 2 vs DeepSeek V3.2:**
- Win rate: 42.8%
- Loss rate: 28.6%
- **Clear advantage for Devstral 2**

### Cost Efficiency

Mistral claims Devstral 2 is **7x more cost-efficient** than Claude Sonnet for real-world coding tasks.

**Monthly cost estimate for heavy AutoBuild usage:**
| Model | Estimated Monthly Cost |
|-------|----------------------|
| Claude (via Max subscription) | $200/month minimum |
| Devstral 2 (API) | ~$20-50/month |
| Devstral Small 2 (local) | $0/month |

---

## Mistral Vibe CLI

Alongside Devstral 2, Mistral released **Mistral Vibe CLI** - an open-source command-line coding assistant.

### Key Features

- Interactive chat interface in terminal
- File manipulation, code search, version control tools
- Project-aware context (scans file structure, Git status)
- Multi-file orchestration
- MCP (Model Context Protocol) support
- Apache 2.0 license

### Relevance to GuardKit

Vibe CLI is a potential **competitor** but also validates the CLI-first approach GuardKit takes. Key differences:

| Aspect | Vibe CLI | GuardKit AutoBuild |
|--------|----------|-------------------|
| Approach | Single agent, natural language | Adversarial cooperation (coach-player) |
| Task structure | Freeform prompts | Feature plans with subtasks |
| Quality assurance | Self-validation | External coach validation |
| Model support | Devstral-focused | Multi-model (Claude, Devstral, DeepSeek) |

**Opportunity:** GuardKit could integrate Vibe CLI as a player agent option, or use its patterns for Devstral integration.

---

## Integration with GuardKit AutoBuild

### API Integration

```python
# Configuration for Devstral 2 via Mistral API
MODEL_CONFIGS = {
    "claude-sonnet": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "api_key_env": "ANTHROPIC_API_KEY"
    },
    "devstral-2": {
        "provider": "mistral",
        "model": "devstral-2",
        "api_key_env": "MISTRAL_API_KEY",
        "base_url": "https://api.mistral.ai/v1"
    },
    "devstral-small": {
        "provider": "mistral",
        "model": "devstral-small-2",
        "api_key_env": "MISTRAL_API_KEY",
        "base_url": "https://api.mistral.ai/v1"
    }
}
```

### Local Deployment (Devstral Small 2)

For fully local/private deployment:

```bash
# Via vLLM (recommended)
vllm serve mistralai/Devstral-Small-2-24B-Instruct-2512 \
    --tool-call-parser mistral \
    --enable-auto-tool-choice \
    --tensor-parallel-size 1

# Via Ollama (simpler)
ollama pull devstral-small
```

### Command Usage

```bash
# Use default model (Claude)
/autobuild

# Use Devstral 2 for cost savings
/autobuild --model devstral-2

# Use local Devstral Small for privacy
/autobuild --model devstral-small --local
```

---

## Recommendations

### For AutoBuild Phase 2 (Multi-Model Support)

1. **Add Devstral 2 as first alternative to Claude**
   - Currently free, excellent performance
   - Validates multi-model architecture works

2. **Add Devstral Small 2 for local deployment**
   - Appeals to privacy-conscious users
   - $0 running cost story

3. **Create cost comparison content**
   - Benchmark same feature with Claude vs Devstral
   - Publish cost/quality trade-off data

### Model Selection Strategy

| Use Case | Recommended Model |
|----------|-------------------|
| Best quality, cost no object | Claude Sonnet 4 |
| Best value (quality/cost) | Devstral 2 |
| Local/private deployment | Devstral Small 2 |
| Experimental/learning | DeepSeek R1 |

---

## References

- Mistral Announcement: https://mistral.ai/news/devstral-2-vibe-cli
- Vibe CLI Repository: https://github.com/mistralai/mistral-vibe
- Hugging Face Model: https://huggingface.co/mistralai/Devstral-2-123B-Instruct-2512
- API Documentation: https://docs.mistral.ai/

---

## Document History

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-19 | Research session | Initial evaluation based on December 9, 2025 release |
