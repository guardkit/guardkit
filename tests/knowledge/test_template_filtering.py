"""
Tests for template filtering in seeding (TASK-a912).

Covers:
- seed_all_system_context passes template_filter to template-specific categories
- seed_all_system_context does not pass template_filter to non-template categories
- seed_templates filters discovered templates by template_filter
- seed_agents skips templates not in template_filter
- seed_rules skips templates not in template_filter
- Backward compatibility: None template_filter seeds all templates

Coverage Target: >=85%
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


class TestSeedAllSystemContextTemplateFilter:
    """Test that seed_all_system_context passes template_filter correctly."""

    @pytest.mark.asyncio
    async def test_template_filter_passed_to_template_categories(self):
        """When template is provided, template-specific seeders receive template_filter."""
        from guardkit.knowledge.seeding import seed_all_system_context

        client = AsyncMock()
        client.enabled = True
        client.reset_circuit_breaker = MagicMock()

        # Track calls to each seeder
        call_tracker = {}

        async def mock_seeder(client_arg, **kwargs):
            # Get function name from the stack
            return (1, 0)

        # Patch all seeders and track their kwargs
        seeders_called_with_filter = []
        seeders_called_without_filter = []

        original_seed_fn_calls = []

        async def tracking_seed_fn(client_arg, **kwargs):
            original_seed_fn_calls.append(kwargs)
            return (1, 0)

        # Patch is_seeded to return False so seeding runs
        with (
            patch("guardkit.knowledge.seeding.is_seeded", return_value=False),
            patch("guardkit.knowledge.seeding.mark_seeded"),
        ):
            # We need to patch the module-level functions that getattr() looks up.
            # The seed_all_system_context uses sys.modules[__name__] + getattr.
            import guardkit.knowledge.seeding as seeding_mod

            # Create mock seeders that record whether template_filter was passed
            calls_with_filter = {}
            original_fns = {}

            template_categories = {"templates", "agents", "rules"}
            all_categories = [
                "seed_product_knowledge", "seed_command_workflows",
                "seed_quality_gate_phases", "seed_technology_stack",
                "seed_feature_build_architecture", "seed_architecture_decisions",
                "seed_failure_patterns", "seed_component_status",
                "seed_integration_points", "seed_templates", "seed_agents",
                "seed_patterns", "seed_rules", "seed_project_overview",
                "seed_project_architecture", "seed_failed_approaches_wrapper",
                "seed_pattern_examples_wrapper",
            ]

            for fn_name in all_categories:
                original_fns[fn_name] = getattr(seeding_mod, fn_name, None)

                async def make_mock(name=fn_name):
                    async def mock_fn(c, **kwargs):
                        calls_with_filter[name] = kwargs
                        return (1, 0)
                    return mock_fn

                mock = AsyncMock(side_effect=lambda c, _name=fn_name, **kwargs: calls_with_filter.update({_name: kwargs}) or (1, 0))
                setattr(seeding_mod, fn_name, mock)

            try:
                result = await seed_all_system_context(
                    client, force=True, template="fastapi-python"
                )

                # Verify template-specific categories received template_filter
                for cat_name in ["seed_templates", "seed_agents", "seed_rules"]:
                    mock_fn = getattr(seeding_mod, cat_name)
                    assert mock_fn.called, f"{cat_name} was not called"
                    # Check that template_filter kwarg was passed
                    call_kwargs = mock_fn.call_args
                    assert "template_filter" in call_kwargs.kwargs, (
                        f"{cat_name} was not called with template_filter"
                    )
                    assert call_kwargs.kwargs["template_filter"] == {"fastapi-python", "default"}

                # Verify non-template categories did NOT receive template_filter
                for cat_name in ["seed_product_knowledge", "seed_command_workflows",
                                 "seed_quality_gate_phases"]:
                    mock_fn = getattr(seeding_mod, cat_name)
                    assert mock_fn.called, f"{cat_name} was not called"
                    call_kwargs = mock_fn.call_args
                    assert "template_filter" not in call_kwargs.kwargs, (
                        f"{cat_name} should not receive template_filter"
                    )
            finally:
                # Restore original functions
                for fn_name, orig in original_fns.items():
                    if orig is not None:
                        setattr(seeding_mod, fn_name, orig)

    @pytest.mark.asyncio
    async def test_no_template_filter_when_template_is_none(self):
        """When template is None, no seeders receive template_filter."""
        from guardkit.knowledge.seeding import seed_all_system_context
        import guardkit.knowledge.seeding as seeding_mod

        client = AsyncMock()
        client.enabled = True
        client.reset_circuit_breaker = MagicMock()

        all_categories = [
            "seed_product_knowledge", "seed_command_workflows",
            "seed_quality_gate_phases", "seed_technology_stack",
            "seed_feature_build_architecture", "seed_architecture_decisions",
            "seed_failure_patterns", "seed_component_status",
            "seed_integration_points", "seed_templates", "seed_agents",
            "seed_patterns", "seed_rules", "seed_project_overview",
            "seed_project_architecture", "seed_failed_approaches_wrapper",
            "seed_pattern_examples_wrapper",
        ]

        original_fns = {}
        for fn_name in all_categories:
            original_fns[fn_name] = getattr(seeding_mod, fn_name, None)
            mock = AsyncMock(return_value=(1, 0))
            setattr(seeding_mod, fn_name, mock)

        try:
            with (
                patch("guardkit.knowledge.seeding.is_seeded", return_value=False),
                patch("guardkit.knowledge.seeding.mark_seeded"),
            ):
                await seed_all_system_context(client, force=True, template=None)

            # No category should have received template_filter
            for cat_name in all_categories:
                mock_fn = getattr(seeding_mod, cat_name)
                if mock_fn.called:
                    call_kwargs = mock_fn.call_args
                    assert "template_filter" not in call_kwargs.kwargs, (
                        f"{cat_name} should not receive template_filter when template=None"
                    )
        finally:
            for fn_name, orig in original_fns.items():
                if orig is not None:
                    setattr(seeding_mod, fn_name, orig)


class TestSeedTemplatesFilter:
    """Test seed_templates with template_filter."""

    @pytest.mark.asyncio
    async def test_filters_discovered_templates(self, tmp_path):
        """Only templates in template_filter are seeded."""
        from guardkit.knowledge.seed_templates import seed_templates

        client = AsyncMock()
        client.enabled = True

        # Create 3 template dirs with manifests
        for tpl in ["default", "fastapi-python", "react-typescript"]:
            tpl_dir = tmp_path / tpl
            tpl_dir.mkdir()
            (tpl_dir / "manifest.json").write_text(
                f'{{"name": "{tpl}", "display_name": "{tpl}"}}'
            )

        with (
            patch(
                "guardkit.knowledge.seed_templates._get_templates_dir",
                return_value=tmp_path,
            ),
            patch(
                "guardkit.knowledge.seed_templates._add_episodes",
                new_callable=AsyncMock,
                return_value=(2, 0),
            ) as mock_add,
        ):
            await seed_templates(client, template_filter={"fastapi-python", "default"})

        # Should have 2 episodes (default + fastapi-python), not 3
        assert mock_add.called
        episodes = mock_add.call_args.args[1]
        template_ids = [ep[1]["id"] for ep in episodes]
        assert "default" in template_ids
        assert "fastapi-python" in template_ids
        assert "react-typescript" not in template_ids

    @pytest.mark.asyncio
    async def test_no_filter_seeds_all(self, tmp_path):
        """Without template_filter, all templates are seeded."""
        from guardkit.knowledge.seed_templates import seed_templates

        client = AsyncMock()
        client.enabled = True

        for tpl in ["default", "fastapi-python", "react-typescript"]:
            tpl_dir = tmp_path / tpl
            tpl_dir.mkdir()
            (tpl_dir / "manifest.json").write_text(
                f'{{"name": "{tpl}", "display_name": "{tpl}"}}'
            )

        with (
            patch(
                "guardkit.knowledge.seed_templates._get_templates_dir",
                return_value=tmp_path,
            ),
            patch(
                "guardkit.knowledge.seed_templates._add_episodes",
                new_callable=AsyncMock,
                return_value=(3, 0),
            ) as mock_add,
        ):
            await seed_templates(client, template_filter=None)

        episodes = mock_add.call_args.args[1]
        assert len(episodes) == 3


class TestSeedAgentsFilter:
    """Test seed_agents with template_filter."""

    @pytest.mark.asyncio
    async def test_skips_templates_not_in_filter(self, tmp_path):
        """Templates not in template_filter are skipped."""
        from guardkit.knowledge.seed_agents import seed_agents

        client = AsyncMock()
        client.enabled = True

        # Create agents in two templates
        for tpl in ["default", "react-typescript"]:
            agents_dir = tmp_path / tpl / "agents"
            agents_dir.mkdir(parents=True)
            (agents_dir / "specialist.md").write_text("# Specialist\nContent")

        with (
            patch(
                "guardkit.knowledge.seed_agents._get_templates_dir",
                return_value=tmp_path,
            ),
            patch(
                "guardkit.knowledge.seed_agents._add_episodes",
                new_callable=AsyncMock,
                return_value=(1, 0),
            ) as mock_add,
        ):
            await seed_agents(client, template_filter={"default"})

        # Only default template's agents should be seeded
        episodes = mock_add.call_args.args[1]
        template_ids = {ep[1]["template_id"] for ep in episodes}
        assert "default" in template_ids
        assert "react-typescript" not in template_ids

    @pytest.mark.asyncio
    async def test_no_filter_seeds_all_agents(self, tmp_path):
        """Without template_filter, agents from all templates are seeded."""
        from guardkit.knowledge.seed_agents import seed_agents

        client = AsyncMock()
        client.enabled = True

        for tpl in ["default", "react-typescript"]:
            agents_dir = tmp_path / tpl / "agents"
            agents_dir.mkdir(parents=True)
            (agents_dir / "specialist.md").write_text("# Specialist\nContent")

        with (
            patch(
                "guardkit.knowledge.seed_agents._get_templates_dir",
                return_value=tmp_path,
            ),
            patch(
                "guardkit.knowledge.seed_agents._add_episodes",
                new_callable=AsyncMock,
                return_value=(2, 0),
            ) as mock_add,
        ):
            await seed_agents(client, template_filter=None)

        episodes = mock_add.call_args.args[1]
        template_ids = {ep[1]["template_id"] for ep in episodes}
        assert len(template_ids) == 2


class TestSeedRulesFilter:
    """Test seed_rules with template_filter."""

    @pytest.mark.asyncio
    async def test_skips_templates_not_in_filter(self, tmp_path):
        """Templates not in template_filter are skipped."""
        from guardkit.knowledge.seed_rules import seed_rules

        client = AsyncMock()
        client.enabled = True
        client.reset_circuit_breaker = MagicMock()

        # Create rules in 3 templates
        for tpl in ["default", "fastapi-python", "react-typescript"]:
            rules_dir = tmp_path / tpl / ".claude" / "rules"
            rules_dir.mkdir(parents=True)
            (rules_dir / "rule.md").write_text("# Rule\nContent")

        with (
            patch(
                "guardkit.knowledge.seed_rules._get_templates_dir",
                return_value=tmp_path,
            ),
            patch(
                "guardkit.knowledge.seed_rules._add_episodes",
                new_callable=AsyncMock,
                return_value=(1, 0),
            ) as mock_add,
        ):
            result = await seed_rules(
                client, template_filter={"fastapi-python", "default"}
            )

        # Should be called for 2 templates (default + fastapi-python), not 3
        assert mock_add.call_count == 2
        call_group_ids = [
            c.args[2] for c in mock_add.call_args_list
        ]
        assert "rules_default" in call_group_ids
        assert "rules_fastapi-python" in call_group_ids
        assert "rules_react-typescript" not in call_group_ids
        assert result == (2, 0)

    @pytest.mark.asyncio
    async def test_no_filter_seeds_all_rules(self, tmp_path):
        """Without template_filter, rules from all templates are seeded."""
        from guardkit.knowledge.seed_rules import seed_rules

        client = AsyncMock()
        client.enabled = True
        client.reset_circuit_breaker = MagicMock()

        for tpl in ["default", "fastapi-python", "react-typescript"]:
            rules_dir = tmp_path / tpl / ".claude" / "rules"
            rules_dir.mkdir(parents=True)
            (rules_dir / "rule.md").write_text("# Rule\nContent")

        with (
            patch(
                "guardkit.knowledge.seed_rules._get_templates_dir",
                return_value=tmp_path,
            ),
            patch(
                "guardkit.knowledge.seed_rules._add_episodes",
                new_callable=AsyncMock,
                return_value=(1, 0),
            ) as mock_add,
        ):
            result = await seed_rules(client, template_filter=None)

        assert mock_add.call_count == 3
        assert result == (3, 0)
