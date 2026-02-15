#!/usr/bin/env python3
"""Diagnostic: dump all group_ids and episode counts from FalkorDB."""

import asyncio
import sys
from pathlib import Path

# Ensure guardkit importable
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

async def diagnose():
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
    
    print(f"Config: graph_store={config.graph_store}, host={config.falkordb_host}:{config.falkordb_port}")
    print(f"Config: project_id={config.project_id}")
    print()
    
    client = GraphitiClient(config)
    success = await client.initialize()
    
    if not success:
        print("ERROR: Failed to initialize client")
        return
    
    print(f"Client enabled: {client.enabled}")
    print(f"Client project_id: {client._project_id}")
    print()
    
    # Query distinct group_ids from Episodes
    driver = getattr(client._graphiti, 'driver', None)
    if not driver:
        print("ERROR: No driver available")
        return
    
    # Get all episode group_ids and counts
    print("=== EPISODES BY GROUP_ID ===")
    try:
        result = await driver.execute_query(
            "MATCH (e:Episode) RETURN e.group_id AS group_id, count(e) AS cnt ORDER BY cnt DESC"
        )
        if result:
            records, _, _ = result
            if records:
                for r in records:
                    print(f"  {r['group_id']}: {r['cnt']} episodes")
            else:
                print("  (no episodes found)")
        else:
            print("  (null result)")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    # Get all node group_ids and counts
    print()
    print("=== NODES BY GROUP_ID ===")
    try:
        result = await driver.execute_query(
            "MATCH (n:Entity) RETURN n.group_id AS group_id, count(n) AS cnt ORDER BY cnt DESC"
        )
        if result:
            records, _, _ = result
            if records:
                for r in records:
                    print(f"  {r['group_id']}: {r['cnt']} nodes")
            else:
                print("  (no nodes found)")
        else:
            print("  (null result)")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    # Get all edge/fact group_ids
    print()
    print("=== FACTS/EDGES BY GROUP_ID ===")
    try:
        result = await driver.execute_query(
            "MATCH ()-[r:RELATES_TO]->() RETURN r.group_id AS group_id, count(r) AS cnt ORDER BY cnt DESC"
        )
        if result:
            records, _, _ = result
            if records:
                for r in records:
                    print(f"  {r['group_id']}: {r['cnt']} edges")
            else:
                print("  (no edges found)")
        else:
            print("  (null result)")
    except Exception as e:
        print(f"  ERROR querying RELATES_TO: {e}")
        # Try alternate edge label
        try:
            result = await driver.execute_query(
                "MATCH ()-[r]->() WHERE r.group_id IS NOT NULL RETURN r.group_id AS group_id, count(r) AS cnt ORDER BY cnt DESC LIMIT 30"
            )
            if result:
                records, _, _ = result
                if records:
                    for r in records:
                        print(f"  {r['group_id']}: {r['cnt']} edges")
        except Exception as e2:
            print(f"  ERROR querying all edges: {e2}")
    
    # Check total graph size
    print()
    print("=== GRAPH STATISTICS ===")
    try:
        result = await driver.execute_query("MATCH (n) RETURN count(n) AS total_nodes")
        if result:
            records, _, _ = result
            print(f"  Total nodes: {records[0]['total_nodes'] if records else 0}")
        
        result = await driver.execute_query("MATCH ()-[r]->() RETURN count(r) AS total_edges")
        if result:
            records, _, _ = result
            print(f"  Total edges: {records[0]['total_edges'] if records else 0}")
        
        # Show distinct labels
        result = await driver.execute_query("MATCH (n) RETURN DISTINCT labels(n) AS labels LIMIT 20")
        if result:
            records, _, _ = result
            labels = [str(r['labels']) for r in records] if records else []
            print(f"  Node labels: {labels}")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    # Test the group_id prefix mapping
    print()
    print("=== GROUP_ID PREFIX MAPPING ===")
    test_groups = [
        "product_knowledge", "command_workflows", "quality_gate_phases",
        "technology_stack", "feature_build_architecture", "architecture_decisions",
        "failure_patterns", "component_status", "integration_points",
        "templates", "agents", "patterns", "rules",
        "project_overview", "project_architecture", "guardkit",
    ]
    for g in test_groups:
        try:
            prefixed = client._apply_group_prefix(g)
            is_proj = client.is_project_group(g)
            print(f"  {g:35s} -> {prefixed:45s} (project={is_proj})")
        except Exception as e:
            print(f"  {g:35s} -> ERROR: {e}")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(diagnose())
