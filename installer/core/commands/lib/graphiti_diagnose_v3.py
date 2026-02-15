#!/usr/bin/env python3
"""Diagnostic v3: discover actual FalkorDB schema and data per graph."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

import redis

host = "whitestocks"
port = 6379
r = redis.Redis(host=host, port=port, decode_responses=True)

graphs = r.execute_command("GRAPH.LIST")

# Check a few graphs that we KNOW have data (graphiti-core found results)
target_graphs = [
    "product_knowledge", "technology_stack", "feature_build_architecture",
    "patterns", "command_workflows", "guardkit", "default_db",
    "guardkit__product_knowledge",
]

print("=== SCHEMA DISCOVERY ===")
for graph_name in target_graphs:
    if graph_name not in graphs:
        continue
    print(f"\n--- {graph_name} ---")
    
    # Get all node labels
    try:
        result = r.execute_command(
            "GRAPH.QUERY", graph_name,
            "MATCH (n) RETURN DISTINCT labels(n) AS lbls, count(n) AS cnt"
        )
        if result and result[0]:
            for row in result[0]:
                print(f"  Labels: {row[0]}, Count: {row[1]}")
        else:
            print("  (no nodes)")
    except Exception as e:
        print(f"  Labels error: {e}")
    
    # Get all relationship types
    try:
        result = r.execute_command(
            "GRAPH.QUERY", graph_name,
            "MATCH ()-[r]->() RETURN DISTINCT type(r) AS t, count(r) AS cnt"
        )
        if result and result[0]:
            for row in result[0]:
                print(f"  Rel type: {row[0]}, Count: {row[1]}")
        else:
            print("  (no relationships)")
    except Exception as e:
        print(f"  Rels error: {e}")
    
    # Get total node count with any match
    try:
        result = r.execute_command(
            "GRAPH.QUERY", graph_name,
            "MATCH (n) RETURN count(n) AS total"
        )
        total = result[0][0][0] if result and result[0] else 0
        print(f"  Total nodes: {total}")
    except Exception as e:
        print(f"  Count error: {e}")
    
    # Get sample node properties
    try:
        result = r.execute_command(
            "GRAPH.QUERY", graph_name,
            "MATCH (n) RETURN n LIMIT 2"
        )
        if result and result[0]:
            for row in result[0]:
                node = row[0]
                # FalkorDB returns node as a dict-like structure
                print(f"  Sample node: {str(node)[:200]}")
    except Exception as e:
        print(f"  Sample error: {e}")

# Now test: run the actual seed for one category and watch what happens
print("\n\n=== SEED TEST: command_workflows ===")
print("Testing if seed_command_workflows actually writes data...")

import asyncio

async def test_seed():
    from guardkit.knowledge.config import load_graphiti_config
    from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig
    
    settings = load_graphiti_config()
    config = GraphitiConfig(
        enabled=settings.enabled,
        graph_store=settings.graph_store,
        falkordb_host=settings.falkordb_host,
        falkordb_port=settings.falkordb_port,
        project_id=getattr(settings, 'project_id', None),
    )
    
    client = GraphitiClient(config)
    success = await client.initialize()
    print(f"  Client initialized: {success}, enabled: {client.enabled}")
    
    if not client.enabled:
        print("  ABORT: client not enabled")
        return
    
    # Test writing a single episode to command_workflows
    print("  Writing test episode to command_workflows...")
    try:
        result = await client.add_episode(
            name="test_episode_diag",
            episode_body='{"test": true, "purpose": "diagnostic"}',
            group_id="command_workflows",
            source="diagnostic",
            entity_type="test",
        )
        print(f"  Result: {result}")
    except Exception as e:
        print(f"  ERROR writing episode: {e}")
        import traceback
        traceback.print_exc()
    
    # Now search for it
    print("  Searching command_workflows for test data...")
    try:
        results = await client.search(
            "test diagnostic",
            group_ids=["command_workflows"],
            num_results=3
        )
        print(f"  Search results: {len(results)}")
        for r_item in results:
            print(f"    -> {r_item}")
    except Exception as e:
        print(f"  ERROR searching: {e}")
        import traceback
        traceback.print_exc()
    
    # Check what prefix was applied
    print(f"\n  Group prefix check:")
    print(f"    command_workflows -> {client._apply_group_prefix('command_workflows')}")
    print(f"    is_project_group('command_workflows') = {client.is_project_group('command_workflows')}")
    
    await client.close()

asyncio.run(test_seed())

r.close()
