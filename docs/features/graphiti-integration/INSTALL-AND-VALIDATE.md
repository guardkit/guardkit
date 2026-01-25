# Graphiti MCP Installation and Validation Guide

## Overview

This guide covers:
1. **Local-first setup** (recommended) - Ollama + Sentence Transformers, no API keys
2. Alternative: Anthropic API setup (if needed later)
3. Alternative: OpenAI API setup (if needed later)
4. Cloud deployment considerations for team sharing
5. Validation tests

**LLM Provider Strategy**: See [LLM Provider Analysis](./LLM-PROVIDER-ANALYSIS.md) and [Local LLM Recommendations](./LOCAL-LLM-RECOMMENDATIONS.md) for detailed analysis.

> **Important**: Graphiti makes its own LLM/embedding API calls - it does NOT use your Claude Max subscription. The local setup below avoids all external API costs.

---

## Part 1: Local Setup (Recommended)

This setup runs entirely on your machine with **no external API dependencies**.

### Prerequisites

- Docker and Docker Compose
- ~50GB free disk space (for models + containers)
- macOS with Apple Silicon (M1/M2/M3) or Linux with NVIDIA GPU

**For M2 Max 96GB**: You can run 70B+ models comfortably.

### Step 1: Install Ollama

```bash
# macOS
brew install ollama

# Or direct download
curl -fsSL https://ollama.com/install.sh | sh
```

### Step 2: Start Ollama and Pull Model

```bash
# Start Ollama service (runs in background)
ollama serve

# In another terminal, pull the recommended model
# Choose based on your RAM:

# For 96GB RAM (recommended for structured output quality)
ollama pull qwen2.5:72b-instruct-q4_K_M

# For 64GB RAM
ollama pull qwen2.5:32b-instruct

# For 32GB RAM  
ollama pull qwen2.5:14b-instruct

# For 16GB RAM (minimum for reliable structured output)
ollama pull qwen2.5:7b-instruct
```

### Step 3: Test Ollama Structured Output

```bash
# Test that your model can produce reliable JSON
ollama run qwen2.5:72b-instruct-q4_K_M << 'EOF'
Extract entities from this text and return ONLY valid JSON:

"Alice is the CEO of TechCorp. TechCorp is headquartered in London."

Return format: {"entities": [{"name": "...", "type": "..."}], "relationships": [...]}
EOF
```

Expected output should be valid JSON. If it's not reliable, try a larger model.

### Step 4: Set Up FalkorDB + Graphiti MCP

```bash
# Create directory
mkdir -p ~/graphiti-mcp && cd ~/graphiti-mcp

# Download docker-compose
curl -O https://raw.githubusercontent.com/getzep/graphiti/main/mcp_server/docker/docker-compose.yml

# Create .env file for LOCAL setup (no external API keys!)
cat > .env << 'EOF'
# ===========================================
# LOCAL SETUP - No external API dependencies
# ===========================================

# Graphiti Configuration
GRAPHITI_GROUP_ID=guardkit
GRAPHITI_TELEMETRY_ENABLED=false

# LLM Configuration - Point to local Ollama
# Note: We'll override this in config.yaml
OPENAI_API_KEY=not-used-for-local

# FalkorDB Configuration  
FALKORDB_PASSWORD=
EOF
```

### Step 5: Create Local Configuration

```bash
# Create config.yaml for fully local operation
cat > config.yaml << 'EOF'
# ===========================================
# Graphiti MCP - Fully Local Configuration
# ===========================================
# No external API calls - runs entirely on your machine

server:
  transport: "http"
  host: "0.0.0.0"
  port: 8000

# LLM - Use local Ollama
llm:
  provider: "openai"  # Ollama provides OpenAI-compatible API
  model: "qwen2.5:72b-instruct-q4_K_M"  # Adjust to your model
  api_base: "http://host.docker.internal:11434/v1"
  api_key: "ollama"  # Dummy key, Ollama doesn't check

# Embeddings - Use local Sentence Transformers
embedder:
  provider: "sentence_transformers"
  model: "all-MiniLM-L6-v2"  # Downloads automatically, runs locally

# Database
database:
  provider: "falkordb"
EOF
```

### Step 6: Start Services

```bash
# Make sure Ollama is running
ollama serve &

# Start FalkorDB + Graphiti MCP
cd ~/graphiti-mcp
docker compose up -d
```

### Step 7: Verify Everything Works

```bash
# Check containers
docker compose ps

# Check health
curl http://localhost:8000/health

# Check Ollama
curl http://localhost:11434/api/tags
```

### Services Running

| Service | Port | URL |
|---------|------|-----|
| FalkorDB (Redis protocol) | 6379 | `redis://localhost:6379` |
| FalkorDB Browser UI | 3000 | http://localhost:3000 |
| MCP Server HTTP endpoint | 8000 | http://localhost:8000/mcp/ |
| Ollama API | 11434 | http://localhost:11434 |

---

## Part 2: Alternative - Anthropic API Setup

Use this if you need higher quality/speed than local models, and are willing to pay API costs.

> **Note**: This requires separate API keys - your Claude Max subscription does NOT cover Graphiti's API calls.

### Prerequisites

- Anthropic API key (from console.anthropic.com)
- OpenAI API key (for embeddings - Anthropic doesn't provide embeddings)

### Configuration

```bash
cd ~/graphiti-mcp

# Create .env file
cat > .env << 'EOF'
# ===========================================
# ANTHROPIC API SETUP
# ===========================================

# LLM - Anthropic Claude (REQUIRES PAID API KEY)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Embeddings - OpenAI (REQUIRES PAID API KEY)
# Note: Still needed even with Anthropic LLM
OPENAI_API_KEY=sk-your-openai-key-here

# Graphiti Configuration
GRAPHITI_GROUP_ID=guardkit
GRAPHITI_TELEMETRY_ENABLED=false

# FalkorDB
FALKORDB_PASSWORD=
EOF

# Create config.yaml
cat > config.yaml << 'EOF'
server:
  transport: "http"
  host: "0.0.0.0"
  port: 8000

llm:
  provider: "anthropic"
  model: "claude-sonnet-4-20250514"
  small_model: "claude-3-5-haiku-20241022"

embedder:
  provider: "openai"
  model: "text-embedding-3-small"

database:
  provider: "falkordb"
EOF
```

### Cost Considerations

Graphiti makes many LLM calls per episode:
- Entity extraction
- Fact extraction
- Deduplication
- Relationship extraction

**Estimate**: Processing 100 episodes could cost $5-20+ depending on content length.

---

## Part 3: Alternative - OpenAI API Setup

Simpler setup using only OpenAI for both LLM and embeddings.

### Configuration

```bash
cd ~/graphiti-mcp

cat > .env << 'EOF'
# ===========================================
# OPENAI API SETUP
# ===========================================

OPENAI_API_KEY=sk-your-openai-key-here

GRAPHITI_GROUP_ID=guardkit
GRAPHITI_TELEMETRY_ENABLED=false
FALKORDB_PASSWORD=
EOF

cat > config.yaml << 'EOF'
server:
  transport: "http"
  host: "0.0.0.0"
  port: 8000

llm:
  provider: "openai"
  model: "gpt-4o"
  small_model: "gpt-4o-mini"

embedder:
  provider: "openai"
  model: "text-embedding-3-small"

database:
  provider: "falkordb"
EOF
```

---

## Part 4: Alternative - Amazon Bedrock (via LiteLLM)

For enterprise deployments with data sovereignty requirements.

> **Note**: Native Bedrock support is pending (PR #1107). This uses LiteLLM as a proxy.

### Architecture

```
Graphiti MCP → LiteLLM Proxy → AWS Bedrock (Claude)
```

### Setup LiteLLM Proxy

```bash
# Install LiteLLM
pip install 'litellm[proxy]'

# Create LiteLLM config
cat > litellm_config.yaml << 'EOF'
model_list:
  # Bedrock Claude for LLM
  - model_name: claude-bedrock
    litellm_params:
      model: bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0
      aws_access_key_id: ${AWS_ACCESS_KEY_ID}
      aws_secret_access_key: ${AWS_SECRET_ACCESS_KEY}
      aws_region_name: eu-west-2  # UK region for data residency

  # Bedrock Titan for embeddings
  - model_name: bedrock-embeddings
    litellm_params:
      model: bedrock/amazon.titan-embed-text-v2:0
      aws_access_key_id: ${AWS_ACCESS_KEY_ID}
      aws_secret_access_key: ${AWS_SECRET_ACCESS_KEY}
      aws_region_name: eu-west-2
EOF

# Start LiteLLM proxy
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
litellm --config litellm_config.yaml --port 4000
```

### Graphiti Configuration for LiteLLM

```yaml
# config.yaml
server:
  transport: "http"
  host: "0.0.0.0"
  port: 8000

llm:
  provider: "openai"
  model: "claude-bedrock"
  api_base: "http://localhost:4000/v1"
  api_key: "not-used"

embedder:
  provider: "openai"
  model: "bedrock-embeddings"
  api_base: "http://localhost:4000/v1"
  api_key: "not-used"

database:
  provider: "falkordb"
```

---

## Part 5: Cloud Deployment for Team Sharing

### Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Cloud (AWS/Azure/GCP)                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              FalkorDB (Managed or Self-Hosted)           │   │
│  │                    redis://...:6379                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
              │                    │                    │
              ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Dev Machine 1  │  │  Dev Machine 2  │  │  Dev Machine 3  │
│                 │  │                 │  │                 │
│  Ollama (local) │  │  Ollama (local) │  │  Ollama (local) │
│  MCP Server     │  │  MCP Server     │  │  MCP Server     │
│  Claude Code    │  │  Claude Code    │  │  Claude Code    │
└─────────────────┘  └─────────────────┘  └─────────────────┘

All share: Same FalkorDB data via group_ids
Each runs: Own LLM locally (no API costs)
```

### FalkorDB Cloud Options

| Option | Pros | Cons |
|--------|------|------|
| **FalkorDB Cloud** | Managed, multi-region | Monthly cost |
| **Self-hosted VM** | Full control | You manage it |
| **Kubernetes** | HA, scaling | Complexity |

### Multi-Tenancy via group_id

Data is isolated by `group_id`:

```python
# Project A - isolated
await graphiti.add_episode(..., group_id="project_a")

# Project B - completely separate
await graphiti.add_episode(..., group_id="project_b")

# Search only sees its own group
results = await graphiti.search(query="...", group_ids=["project_a"])
```

---

## Part 6: Validation Tests

### Test Script

Save as `~/graphiti-mcp/test_connection.py`:

```python
#!/usr/bin/env python3
"""
Graphiti MCP Connection Validation Tests
Tests local Ollama + Graphiti MCP setup
"""

import asyncio
import json
import sys

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)

MCP_ENDPOINT = "http://localhost:8000/mcp/"
OLLAMA_ENDPOINT = "http://localhost:11434"
TEST_GROUP_ID = "guardkit_validation_test"


async def test_ollama():
    """Test Ollama is running and has models."""
    print("\n🔍 Test 1: Ollama Connection")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{OLLAMA_ENDPOINT}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                print(f"   ✅ Ollama running with {len(models)} models")
                for m in models[:3]:
                    print(f"      - {m['name']}")
                return True
            else:
                print(f"   ❌ Ollama returned {resp.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Cannot connect to Ollama: {e}")
            print("   💡 Run: ollama serve")
            return False


async def test_mcp_health():
    """Test MCP server health."""
    print("\n🔍 Test 2: MCP Server Health")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("http://localhost:8000/health", timeout=5)
            if resp.status_code == 200:
                print(f"   ✅ MCP server healthy: {resp.json()}")
                return True
            else:
                print(f"   ❌ Health check failed: {resp.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Cannot connect to MCP: {e}")
            print("   💡 Run: cd ~/graphiti-mcp && docker compose up -d")
            return False


async def test_mcp_tools():
    """Test MCP tools are available."""
    print("\n🔍 Test 3: MCP Tools Available")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                MCP_ENDPOINT,
                json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                timeout=10
            )
            result = resp.json()
            if "result" in result and "tools" in result["result"]:
                tools = [t["name"] for t in result["result"]["tools"]]
                print(f"   ✅ Found {len(tools)} tools: {', '.join(tools)}")
                return True
            else:
                print(f"   ❌ Unexpected response: {result}")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False


async def test_add_episode():
    """Test adding an episode (requires LLM)."""
    print("\n🔍 Test 4: Add Episode (uses LLM)")
    print("   ⏳ This may take 30-60 seconds with local LLM...")
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                MCP_ENDPOINT,
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "add_episode",
                        "arguments": {
                            "name": "test_episode",
                            "episode_body": "GuardKit is a quality gate system. It enforces review checkpoints.",
                            "source_description": "Validation test",
                            "group_id": TEST_GROUP_ID
                        }
                    },
                    "id": 2
                },
                timeout=120  # Long timeout for local LLM
            )
            result = resp.json()
            if "error" not in result:
                print("   ✅ Episode added successfully")
                return True
            else:
                print(f"   ❌ Error: {result.get('error')}")
                return False
        except httpx.TimeoutException:
            print("   ⚠️ Timeout - LLM may be loading or model too slow")
            return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False


async def test_search():
    """Test searching for nodes."""
    print("\n🔍 Test 5: Search Nodes")
    print("   ⏳ Waiting for processing...")
    await asyncio.sleep(5)
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                MCP_ENDPOINT,
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "search_nodes",
                        "arguments": {
                            "query": "quality gate",
                            "group_ids": [TEST_GROUP_ID],
                            "limit": 5
                        }
                    },
                    "id": 3
                },
                timeout=30
            )
            result = resp.json()
            if "result" in result:
                print("   ✅ Search completed")
                return True
            else:
                print(f"   ❌ Error: {result.get('error')}")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False


async def main():
    print("=" * 60)
    print("Graphiti MCP Validation - Local Setup")
    print("=" * 60)
    
    results = []
    
    results.append(("Ollama", await test_ollama()))
    results.append(("MCP Health", await test_mcp_health()))
    
    if all(r[1] for r in results):
        results.append(("MCP Tools", await test_mcp_tools()))
        results.append(("Add Episode", await test_add_episode()))
        results.append(("Search", await test_search()))
    
    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"   {status} {name}")
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    print(f"\n   Total: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Graphiti is ready for GuardKit.")
    else:
        print("\n⚠️ Some tests failed. Check output above.")


if __name__ == "__main__":
    asyncio.run(main())
```

### Run Tests

```bash
# Install test dependency
pip install httpx

# Run tests
python ~/graphiti-mcp/test_connection.py
```

### Expected Output (Local Setup)

```
============================================================
Graphiti MCP Validation - Local Setup
============================================================

🔍 Test 1: Ollama Connection
   ✅ Ollama running with 2 models
      - qwen2.5:72b-instruct-q4_K_M
      - qwen2.5:14b-instruct

🔍 Test 2: MCP Server Health
   ✅ MCP server healthy: {'status': 'ok'}

🔍 Test 3: MCP Tools Available
   ✅ Found 6 tools: add_episode, search_nodes, search_facts, ...

🔍 Test 4: Add Episode (uses LLM)
   ⏳ This may take 30-60 seconds with local LLM...
   ✅ Episode added successfully

🔍 Test 5: Search Nodes
   ✅ Search completed

============================================================
Results Summary
============================================================
   ✅ Ollama
   ✅ MCP Health
   ✅ MCP Tools
   ✅ Add Episode
   ✅ Search

   Total: 5/5 passed

🎉 All tests passed! Graphiti is ready for GuardKit.
```

---

## Part 7: Troubleshooting

### Ollama Issues

```bash
# Check if running
pgrep ollama

# Start if not running
ollama serve

# Check available models
ollama list

# Pull model if missing
ollama pull qwen2.5:72b-instruct-q4_K_M
```

### Docker/MCP Issues

```bash
# Check containers
cd ~/graphiti-mcp
docker compose ps

# View logs
docker compose logs -f

# Restart
docker compose down
docker compose up -d
```

### Memory Issues (Local LLM)

If running out of memory:
1. Use a smaller model: `qwen2.5:32b-instruct` or `qwen2.5:14b-instruct`
2. Close other applications
3. Check memory usage: `top` or Activity Monitor

### Slow Performance

Local 70B models run at ~8-10 tokens/second. This is normal.
- Episode processing takes 30-60 seconds
- This is acceptable for batch operations
- For faster iteration, use a smaller model during development

---

## Quick Reference

### Start Everything (Local Setup)

```bash
# Terminal 1: Ollama
ollama serve

# Terminal 2: FalkorDB + MCP
cd ~/graphiti-mcp && docker compose up -d

# Verify
curl http://localhost:8000/health
curl http://localhost:11434/api/tags
```

### Stop Everything

```bash
# Stop MCP + FalkorDB
cd ~/graphiti-mcp && docker compose down

# Stop Ollama (optional)
pkill ollama
```

### Switch Configurations

```bash
cd ~/graphiti-mcp

# Edit config.yaml to switch providers
# Then restart:
docker compose down
docker compose up -d
```

---

## Summary: Configuration Comparison

| Setup | API Keys Needed | Cost | Speed | Quality |
|-------|-----------------|------|-------|---------|
| **Local (Ollama)** | None | Free | ~8-10 tok/s | Very Good |
| Anthropic API | ANTHROPIC + OPENAI | $$$ | ~50 tok/s | Excellent |
| OpenAI API | OPENAI | $$ | ~50 tok/s | Excellent |
| Bedrock (LiteLLM) | AWS credentials | $$ | ~50 tok/s | Excellent |

**Recommendation**: Start with Local setup, switch to API if quality issues arise.
