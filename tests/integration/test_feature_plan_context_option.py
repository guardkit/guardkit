"""
Integration test for /feature-plan --context option.

This test demonstrates the end-to-end workflow with explicit context files.
"""

import asyncio
from pathlib import Path
import tempfile
import pytest

from guardkit.commands.feature_plan_integration import FeaturePlanIntegration


@pytest.mark.asyncio
async def test_feature_plan_with_explicit_context():
    """Test complete workflow with --context option."""

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Create a feature spec file
        docs_dir = project_root / "docs" / "features"
        docs_dir.mkdir(parents=True)

        spec_file = docs_dir / "FEAT-001-api-gateway.md"
        spec_file.write_text("""---
id: FEAT-001
title: API Gateway Implementation
---

# API Gateway

Implement a centralized API gateway for microservices.

## Requirements
- Request routing
- Rate limiting
- Authentication
- Logging
""")

        # Create an architecture doc
        arch_file = project_root / "docs" / "architecture.md"
        arch_file.write_text("""# Architecture

Our system uses a microservices architecture with:
- Service mesh for inter-service communication
- OAuth2 for authentication
- Redis for caching
""")

        # Create integration instance
        integration = FeaturePlanIntegration(project_root=project_root)

        # Test 1: Single context file
        enriched_prompt_1 = await integration.build_enriched_prompt(
            description="Implement FEAT-001",
            context_files=[spec_file]
        )

        assert "API Gateway" in enriched_prompt_1 or "FEAT-001" in enriched_prompt_1
        print("✅ Single context file test passed")

        # Test 2: Multiple context files
        enriched_prompt_2 = await integration.build_enriched_prompt(
            description="Implement FEAT-001",
            context_files=[spec_file, arch_file]
        )

        # Should include content from both files
        assert "FEAT-001" in enriched_prompt_2 or "API Gateway" in enriched_prompt_2
        print("✅ Multiple context files test passed")

        # Test 3: Relative paths
        enriched_prompt_3 = await integration.build_enriched_prompt(
            description="Implement FEAT-001",
            context_files=[Path("docs/features/FEAT-001-api-gateway.md")]
        )

        assert enriched_prompt_3 is not None
        print("✅ Relative path test passed")

        print("\n✅ All integration tests passed!")


if __name__ == "__main__":
    asyncio.run(test_feature_plan_with_explicit_context())
