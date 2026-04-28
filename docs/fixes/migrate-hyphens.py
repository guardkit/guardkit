#!/usr/bin/env python3
"""
Migrate FalkorDB graphs from hyphenated to underscored project IDs.

Converts graph names like 'specialist-agent__project_decisions'
to 'specialist_agent__project_decisions' and updates group_id
properties on all nodes and edges inside each graph.

Run inside the graphiti-mcp container:
    docker exec graphiti-mcp uv run --no-sync python /app/mcp/migrate-hyphens.py --dry-run
    docker exec graphiti-mcp uv run --no-sync python /app/mcp/migrate-hyphens.py

The script is idempotent — running it twice is safe.
"""

import argparse
import re
import sys

import redis


def get_hyphenated_graphs(r: redis.Redis) -> list[str]:
    """Return all graph names containing hyphens."""
    graphs = r.execute_command("GRAPH.LIST")
    return sorted(g.decode() for g in graphs if b"-" in g)


def graph_stats(r: redis.Redis, graph: str) -> tuple[int, int]:
    """Return (node_count, edge_count) for a graph."""
    try:
        nodes = r.execute_command("GRAPH.QUERY", graph, "MATCH (n) RETURN count(n)")
        edges = r.execute_command(
            "GRAPH.QUERY", graph, "MATCH ()-[e]->() RETURN count(e)"
        )
        nc = nodes[1][0][0] if nodes[1] else 0
        ec = edges[1][0][0] if edges[1] else 0
        return (nc, ec)
    except Exception as e:
        print(f"  ERROR reading {graph}: {e}")
        return (0, 0)


def new_name(old: str) -> str:
    """Replace hyphens with underscores in the project-id portion.

    Graph names follow the pattern: project-id__suffix
    or standalone names like 'appmilla-fleet'.

    We replace ALL hyphens since underscores are safe everywhere
    in FalkorDB/RediSearch.
    """
    return old.replace("-", "_")


def migrate_graph(r: redis.Redis, old: str, dry_run: bool) -> bool:
    """Migrate a single graph. Returns True if work was done."""
    new = new_name(old)
    nc, ec = graph_stats(r, old)

    # Skip if target already exists
    if r.exists(new):
        print(f"  SKIP {old} -> {new} (target already exists)")
        return False

    if nc == 0 and ec == 0:
        # Empty graph — just delete it
        if dry_run:
            print(f"  DRY-RUN: would DELETE empty graph '{old}'")
        else:
            r.execute_command("GRAPH.DELETE", old)
            print(f"  DELETED empty graph '{old}'")
        return True

    # Non-empty graph — rename the Redis key, then update group_id properties
    old_group_id = old  # the graph name IS the group_id in FalkorDB
    new_group_id = new

    if dry_run:
        print(f"  DRY-RUN: would RENAME '{old}' -> '{new}' ({nc} nodes, {ec} edges)")
        print(f"           would UPDATE group_id '{old_group_id}' -> '{new_group_id}'")
        return True

    # Step 1: Rename the Redis key (atomic, preserves everything)
    r.rename(old, new)
    print(f"  RENAMED '{old}' -> '{new}'")

    # Step 2: Update group_id on all nodes
    # Use CYPHER parameter syntax for FalkorDB
    if nc > 0:
        query = (
            f"CYPHER old='{old_group_id}' new='{new_group_id}' "
            f"MATCH (n) WHERE n.group_id = $old SET n.group_id = $new RETURN count(n)"
        )
        result = r.execute_command("GRAPH.QUERY", new, query)
        updated = result[1][0][0] if result[1] else 0
        print(f"  UPDATED {updated} node group_ids")

    # Step 3: Update group_id on all edges
    if ec > 0:
        query = (
            f"CYPHER old='{old_group_id}' new='{new_group_id}' "
            f"MATCH ()-[e]->() WHERE e.group_id = $old SET e.group_id = $new RETURN count(e)"
        )
        result = r.execute_command("GRAPH.QUERY", new, query)
        updated = result[1][0][0] if result[1] else 0
        print(f"  UPDATED {updated} edge group_ids")

    return True


def main():
    parser = argparse.ArgumentParser(description="Migrate hyphenated FalkorDB graph names")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--host", default="whitestocks", help="FalkorDB host (default: whitestocks)"
    )
    parser.add_argument(
        "--port", type=int, default=6379, help="FalkorDB port (default: 6379)"
    )
    args = parser.parse_args()

    r = redis.Redis(host=args.host, port=args.port)

    # Verify connection
    try:
        r.ping()
    except redis.ConnectionError as e:
        print(f"Cannot connect to FalkorDB at {args.host}:{args.port}: {e}")
        sys.exit(1)

    graphs = get_hyphenated_graphs(r)
    print(f"Found {len(graphs)} hyphenated graphs")
    if args.dry_run:
        print("DRY RUN — no changes will be made\n")
    else:
        print()

    migrated = 0
    errors = 0

    for g in graphs:
        try:
            if migrate_graph(r, g, args.dry_run):
                migrated += 1
        except Exception as e:
            print(f"  ERROR migrating {g}: {e}")
            errors += 1

    print(f"\nDone: {migrated} graphs processed, {errors} errors")
    if args.dry_run:
        print("Re-run without --dry-run to apply changes")
    else:
        print("\nNext steps:")
        print("  1. Update project_id in each repo's .guardkit/graphiti.yaml")
        print("     (replace hyphens with underscores)")
        print("  2. Update group_id references in .claude/rules/graphiti-knowledge-graph.md")
        print("  3. Restart the graphiti-mcp container:")
        print("     ./scripts/graphiti-mcp.sh")


if __name__ == "__main__":
    main()
