#!/usr/bin/env python3
"""Test the fulltext query underscore escaping fix."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

async def test():
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

    groups = ['product_knowledge', 'command_workflows', 'technology_stack', 'patterns']
    for g in groups:
        results = await client.search('guardkit quality gate workflow', group_ids=[g], num_results=3)
        print(f'{g}: {len(results)} results')
        for r in results[:2]:
            print(f'  -> {r["fact"][:100]}')

    # Also test prefixed project groups
    prefixed = ['guardkit__project_overview', 'guardkit__project_architecture']
    for g in prefixed:
        results = await client.search('guardkit architecture', group_ids=[g], num_results=3)
        print(f'{g}: {len(results)} results')
        for r in results[:2]:
            print(f'  -> {r["fact"][:100]}')

    await client.close()
    print("\nDone - no RediSearch errors = fix working!")

if __name__ == "__main__":
    asyncio.run(test())
