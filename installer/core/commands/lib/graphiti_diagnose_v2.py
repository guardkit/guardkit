#!/usr/bin/env python3
"""Diagnostic v2: check FalkorDB multi-graph structure directly."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

async def diagnose():
    import redis
    
    host = "whitestocks"
    port = 6379
    
    r = redis.Redis(host=host, port=port, decode_responses=True)
    print(f"Connected to FalkorDB at {host}:{port}")
    print(f"Redis PING: {r.ping()}")
    print()
    
    # List all FalkorDB graphs
    print("=== ALL FALKORDB GRAPHS ===")
    try:
        graphs = r.execute_command("GRAPH.LIST")
        print(f"  Found {len(graphs)} graphs:")
        for g in sorted(graphs):
            print(f"    - {g}")
    except Exception as e:
        print(f"  ERROR listing graphs: {e}")
        # Fallback: scan for graph keys
        print("  Trying key scan fallback...")
        for key in r.scan_iter("*"):
            key_type = r.type(key)
            print(f"    {key} (type={key_type})")
    
    print()
    
    # For each graph, count nodes and episodes
    print("=== GRAPH CONTENTS ===")
    if graphs:
        for graph_name in sorted(graphs):
            try:
                # Count episodes
                result = r.execute_command(
                    "GRAPH.QUERY", graph_name,
                    "MATCH (e:Episodic) RETURN count(e) AS cnt"
                )
                ep_count = _extract_count(result)
                
                # Count entity nodes
                result2 = r.execute_command(
                    "GRAPH.QUERY", graph_name,
                    "MATCH (n:Entity) RETURN count(n) AS cnt"
                )
                node_count = _extract_count(result2)
                
                # Count edges
                result3 = r.execute_command(
                    "GRAPH.QUERY", graph_name,
                    "MATCH ()-[r]->() RETURN count(r) AS cnt"
                )
                edge_count = _extract_count(result3)
                
                print(f"  {graph_name:40s}: {ep_count:3d} episodes, {node_count:3d} nodes, {edge_count:3d} edges")
                
                # If it has episodes, show a sample
                if ep_count > 0:
                    try:
                        sample = r.execute_command(
                            "GRAPH.QUERY", graph_name,
                            "MATCH (e:Episodic) RETURN e.name AS name, e.group_id AS gid LIMIT 3"
                        )
                        rows = _extract_rows(sample)
                        for row in rows:
                            print(f"    -> ep: name={row[0]}, group_id={row[1]}")
                    except:
                        pass
                
                if node_count > 0:
                    try:
                        sample = r.execute_command(
                            "GRAPH.QUERY", graph_name,
                            "MATCH (n:Entity) RETURN n.name AS name, n.group_id AS gid LIMIT 3"
                        )
                        rows = _extract_rows(sample)
                        for row in rows:
                            print(f"    -> node: name={row[0]}, group_id={row[1]}")
                    except:
                        pass
                        
            except Exception as e:
                print(f"  {graph_name:40s}: ERROR - {e}")
    
    # Also check what the graphiti-core search finds
    print()
    print("=== GRAPHITI-CORE SEARCH TEST ===")
    try:
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
        await client.initialize()
        
        if client.enabled:
            # Search without group_ids (should search default graph)
            results = await client.search("guardkit quality gate", num_results=3)
            print(f"  Search (no group filter): {len(results)} results")
            for r_item in results:
                print(f"    -> {r_item.get('name', 'N/A')[:60]}")
            
            # Search with specific group_ids
            results2 = await client.search(
                "guardkit quality gate",
                group_ids=["product_knowledge"],
                num_results=3
            )
            print(f"  Search (product_knowledge): {len(results2)} results")
            for r_item in results2:
                print(f"    -> {r_item.get('name', 'N/A')[:60]}")
            
            # Search with technology_stack
            results3 = await client.search(
                "claude code python",
                group_ids=["technology_stack"],
                num_results=3
            )
            print(f"  Search (technology_stack): {len(results3)} results")
            for r_item in results3:
                print(f"    -> {r_item.get('name', 'N/A')[:60]}")
            
            await client.close()
        else:
            print("  Client not enabled after init")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    r.close()


def _extract_count(result):
    """Extract count from FalkorDB GRAPH.QUERY result."""
    try:
        if result and len(result) > 0:
            rows = result[0]  # First element is result rows
            if rows and len(rows) > 0:
                return int(rows[0][0])
    except:
        pass
    return 0


def _extract_rows(result):
    """Extract rows from FalkorDB GRAPH.QUERY result."""
    try:
        if result and len(result) > 0:
            return result[0]  # First element is result rows
    except:
        pass
    return []


if __name__ == "__main__":
    asyncio.run(diagnose())
