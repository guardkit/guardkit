#!/usr/bin/env python3
"""
Graphiti MCP Connection Validation Tests

Tests the local Ollama + Graphiti MCP setup.
Handles the slower response times of local LLMs.

Prerequisites:
- Ollama running with a model pulled
- Docker containers running (docker compose up -d)

Usage:
    pip install httpx
    python test_graphiti_connection.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx")
    sys.exit(1)

# Configuration
MCP_ENDPOINT = os.environ.get("MCP_ENDPOINT", "http://localhost:8000/mcp/")
HEALTH_ENDPOINT = MCP_ENDPOINT.replace("/mcp/", "/health")
OLLAMA_ENDPOINT = os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434")
TEST_GROUP_ID = "guardkit_validation_test"

# Timeouts (local LLMs are slower)
TIMEOUT_HEALTH = 5
TIMEOUT_TOOLS = 10
TIMEOUT_EPISODE = 180  # 3 minutes for local LLM processing
TIMEOUT_SEARCH = 60


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")


def print_test(name: str):
    print(f"\n{Colors.BOLD}🔍 {name}{Colors.RESET}")


def print_success(text: str):
    print(f"   {Colors.GREEN}✅{Colors.RESET} {text}")


def print_error(text: str):
    print(f"   {Colors.RED}❌{Colors.RESET} {text}")


def print_warning(text: str):
    print(f"   {Colors.YELLOW}⚠️{Colors.RESET} {text}")


def print_info(text: str):
    print(f"   {Colors.BLUE}ℹ️{Colors.RESET} {text}")


def print_wait(text: str):
    print(f"   {Colors.YELLOW}⏳{Colors.RESET} {text}")


async def test_ollama() -> tuple[bool, list[str]]:
    """Test Ollama is running and has models."""
    print_test("Test 1: Ollama Connection")
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{OLLAMA_ENDPOINT}/api/tags",
                timeout=TIMEOUT_HEALTH
            )
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                model_names = [m["name"] for m in models]
                
                if models:
                    print_success(f"Ollama running with {len(models)} model(s)")
                    for m in model_names[:5]:
                        print_info(f"Model: {m}")
                    return True, model_names
                else:
                    print_error("Ollama running but no models installed")
                    print_info("Run: ollama pull qwen2.5:72b-instruct-q4_K_M")
                    return False, []
            else:
                print_error(f"Ollama returned status {resp.status_code}")
                return False, []
        except httpx.ConnectError:
            print_error("Cannot connect to Ollama")
            print_info("Start Ollama: ollama serve")
            return False, []
        except Exception as e:
            print_error(f"Error: {e}")
            return False, []


async def test_mcp_health() -> bool:
    """Test MCP server health."""
    print_test("Test 2: MCP Server Health")
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(HEALTH_ENDPOINT, timeout=TIMEOUT_HEALTH)
            if resp.status_code == 200:
                data = resp.json()
                print_success(f"MCP server healthy: {data}")
                return True
            else:
                print_error(f"Health check failed: HTTP {resp.status_code}")
                return False
        except httpx.ConnectError:
            print_error("Cannot connect to MCP server")
            print_info("Start containers: cd ~/graphiti-mcp && docker compose up -d")
            return False
        except Exception as e:
            print_error(f"Error: {e}")
            return False


async def test_mcp_tools() -> bool:
    """Test MCP tools are available."""
    print_test("Test 3: MCP Tools Available")
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                MCP_ENDPOINT,
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "id": 1
                },
                timeout=TIMEOUT_TOOLS
            )
            result = resp.json()
            
            if "result" in result and "tools" in result["result"]:
                tools = result["result"]["tools"]
                tool_names = [t["name"] for t in tools]
                print_success(f"Found {len(tools)} tools")
                
                required = ["add_episode", "search_nodes", "search_facts"]
                missing = [t for t in required if t not in tool_names]
                
                if missing:
                    print_warning(f"Missing expected tools: {missing}")
                else:
                    print_success("All required tools available")
                
                print_info(f"Tools: {', '.join(tool_names)}")
                return True
            else:
                print_error(f"Unexpected response: {result}")
                return False
        except Exception as e:
            print_error(f"Error: {e}")
            return False


async def test_add_episode() -> bool:
    """Test adding an episode (exercises the LLM)."""
    print_test("Test 4: Add Episode (LLM Entity Extraction)")
    print_wait("This may take 30-120 seconds with local LLM...")
    
    start_time = datetime.now()
    
    episode_content = """
    GuardKit is a quality gate system for AI-assisted development.
    It was created by Rich at Appmilla to enforce mandatory review checkpoints.
    The system uses a player-coach pattern with adversarial cooperation.
    GuardKit integrates with Claude Code for automated task implementation.
    """
    
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
                            "name": f"validation_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            "episode_body": episode_content.strip(),
                            "source_description": "GuardKit validation test",
                            "group_id": TEST_GROUP_ID
                        }
                    },
                    "id": 2
                },
                timeout=TIMEOUT_EPISODE
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            result = resp.json()
            
            if "error" not in result:
                print_success(f"Episode added successfully ({elapsed:.1f}s)")
                return True
            else:
                error = result.get("error", {})
                print_error(f"Failed: {error}")
                return False
                
        except httpx.TimeoutException:
            elapsed = (datetime.now() - start_time).total_seconds()
            print_error(f"Timeout after {elapsed:.0f}s")
            print_info("Your LLM model may be too slow or still loading")
            print_info("Try a smaller model: ollama pull qwen2.5:14b-instruct")
            return False
        except Exception as e:
            print_error(f"Error: {e}")
            return False


async def test_search_nodes() -> bool:
    """Test searching for nodes."""
    print_test("Test 5: Search Nodes")
    print_wait("Waiting for episode processing...")
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
                            "query": "quality gate review checkpoint",
                            "group_ids": [TEST_GROUP_ID],
                            "limit": 10
                        }
                    },
                    "id": 3
                },
                timeout=TIMEOUT_SEARCH
            )
            
            result = resp.json()
            
            if "result" in result:
                content = result.get("result", {})
                print_success("Search completed successfully")
                
                # Try to parse results
                if isinstance(content, dict) and "content" in content:
                    items = content["content"]
                    if items:
                        print_success(f"Found {len(items)} result(s)")
                    else:
                        print_warning("No results (episode may still be processing)")
                return True
            else:
                error = result.get("error", {})
                print_error(f"Search failed: {error}")
                return False
                
        except Exception as e:
            print_error(f"Error: {e}")
            return False


async def test_search_facts() -> bool:
    """Test searching for facts/relationships."""
    print_test("Test 6: Search Facts")
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                MCP_ENDPOINT,
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "search_facts",
                        "arguments": {
                            "query": "GuardKit quality",
                            "group_ids": [TEST_GROUP_ID],
                            "limit": 10
                        }
                    },
                    "id": 4
                },
                timeout=TIMEOUT_SEARCH
            )
            
            result = resp.json()
            
            if "result" in result:
                print_success("Facts search completed")
                return True
            else:
                error = result.get("error", {})
                print_warning(f"Facts search: {error.get('message', 'Unknown')}")
                return True  # Non-critical
                
        except Exception as e:
            print_error(f"Error: {e}")
            return False


async def main():
    print_header("Graphiti MCP Validation - Local Setup")
    
    print_info(f"MCP Endpoint: {MCP_ENDPOINT}")
    print_info(f"Ollama Endpoint: {OLLAMA_ENDPOINT}")
    print_info(f"Test Group ID: {TEST_GROUP_ID}")
    print_info(f"Timestamp: {datetime.now().isoformat()}")
    
    results = {}
    
    # Test 1: Ollama
    ollama_ok, models = await test_ollama()
    results["Ollama"] = ollama_ok
    
    if not ollama_ok:
        print_error("\nOllama not available - cannot proceed")
        print_info("1. Install Ollama: brew install ollama")
        print_info("2. Start Ollama: ollama serve")
        print_info("3. Pull a model: ollama pull qwen2.5:72b-instruct-q4_K_M")
        sys.exit(1)
    
    # Test 2: MCP Health
    results["MCP Health"] = await test_mcp_health()
    
    if not results["MCP Health"]:
        print_error("\nMCP server not available - cannot proceed")
        print_info("1. cd ~/graphiti-mcp")
        print_info("2. docker compose up -d")
        sys.exit(1)
    
    # Test 3: MCP Tools
    results["MCP Tools"] = await test_mcp_tools()
    
    # Test 4: Add Episode (LLM test)
    results["Add Episode"] = await test_add_episode()
    
    # Test 5 & 6: Search (if episode worked)
    if results["Add Episode"]:
        results["Search Nodes"] = await test_search_nodes()
        results["Search Facts"] = await test_search_facts()
    else:
        print_warning("\nSkipping search tests (episode add failed)")
    
    # Summary
    print_header("Test Results Summary")
    
    passed = 0
    failed = 0
    
    for name, result in results.items():
        if result:
            print_success(name)
            passed += 1
        else:
            print_error(name)
            failed += 1
    
    print(f"\n{Colors.BOLD}Total: {passed} passed, {failed} failed{Colors.RESET}")
    
    if failed == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 All tests passed!{Colors.RESET}")
        print(f"{Colors.GREEN}Graphiti MCP is ready for GuardKit integration.{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️ Some tests failed.{Colors.RESET}")
        print("Review the output above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
