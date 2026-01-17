# Graphiti MCP Validation Scripts

Scripts to set up and validate Graphiti MCP server with local LLMs (no API keys required).

## Quick Start (Local Setup - Recommended)

```bash
# 1. Make scripts executable
chmod +x setup_graphiti_local.sh

# 2. Run setup (auto-detects best model for your RAM)
./setup_graphiti_local.sh

# 3. Install Python test dependency
pip install httpx

# 4. Run validation tests
python test_graphiti_connection.py
```

## Files

| File | Description |
|------|-------------|
| `setup_graphiti_local.sh` | Sets up Ollama + FalkorDB + Graphiti MCP (no API keys) |
| `test_graphiti_connection.py` | Python tests to verify everything works |

## What the Setup Does

1. Checks Ollama is installed and running
2. Recommends a model based on your RAM:
   - 96GB+ → `qwen2.5:72b-instruct-q4_K_M`
   - 64GB+ → `qwen2.5:32b-instruct`
   - 32GB+ → `qwen2.5:14b-instruct`
   - 16GB+ → `qwen2.5:7b-instruct`
3. Pulls the model if not present
4. Downloads docker-compose.yml
5. Creates config.yaml for local LLM
6. Starts FalkorDB + Graphiti MCP containers

## What the Tests Validate

1. **Ollama** - Local LLM server is running with models
2. **MCP Health** - Graphiti MCP server is healthy
3. **MCP Tools** - All required tools are available
4. **Add Episode** - Can add knowledge (tests LLM entity extraction)
5. **Search Nodes** - Can search for entities
6. **Search Facts** - Can search for relationships

## Expected Output

```
============================================================
Graphiti MCP Validation - Local Setup
============================================================

🔍 Test 1: Ollama Connection
   ✅ Ollama running with 2 model(s)
   ℹ️ Model: qwen2.5:72b-instruct-q4_K_M

🔍 Test 2: MCP Server Health
   ✅ MCP server healthy: {'status': 'ok'}

🔍 Test 3: MCP Tools Available
   ✅ Found 6 tools
   ✅ All required tools available

🔍 Test 4: Add Episode (LLM Entity Extraction)
   ⏳ This may take 30-120 seconds with local LLM...
   ✅ Episode added successfully (45.2s)

🔍 Test 5: Search Nodes
   ✅ Search completed successfully
   ✅ Found 3 result(s)

🔍 Test 6: Search Facts
   ✅ Facts search completed

============================================================
Test Results Summary
============================================================
   ✅ Ollama
   ✅ MCP Health
   ✅ MCP Tools
   ✅ Add Episode
   ✅ Search Nodes
   ✅ Search Facts

Total: 6 passed, 0 failed

🎉 All tests passed!
Graphiti MCP is ready for GuardKit integration.
```

## Troubleshooting

### "Cannot connect to Ollama"

```bash
# Check if running
pgrep ollama

# Start if not
ollama serve
```

### "Cannot connect to MCP server"

```bash
cd ~/graphiti-mcp
docker compose ps      # Check status
docker compose logs    # View logs
docker compose up -d   # Start if not running
```

### "Timeout" during Add Episode

Local LLMs are slower than API calls. The 72B model takes 30-60 seconds per episode.

Options:
1. Wait longer (timeout is 3 minutes)
2. Use a smaller/faster model:
   ```bash
   ollama pull qwen2.5:14b-instruct
   # Edit ~/graphiti-mcp/config.yaml to use this model
   docker compose restart
   ```

### Memory Issues

If your Mac becomes unresponsive:
1. Use a smaller model
2. Close other applications
3. Check Activity Monitor for memory pressure

## Configuration Files

After setup, these files are in `~/graphiti-mcp/`:

- `.env` - Environment variables
- `config.yaml` - Graphiti configuration
- `docker-compose.yml` - Container configuration

## Start/Stop Commands

```bash
# Start everything
ollama serve &
cd ~/graphiti-mcp && docker compose up -d

# Stop everything
cd ~/graphiti-mcp && docker compose down
pkill ollama

# View logs
docker compose logs -f

# Restart after config change
docker compose down && docker compose up -d
```

## Alternative Setups

The main guide (`INSTALL-AND-VALIDATE.md`) covers:
- Anthropic API setup
- OpenAI API setup
- Amazon Bedrock via LiteLLM
- Cloud deployment for teams
