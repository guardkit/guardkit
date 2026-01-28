#!/usr/bin/env python3
"""
Test suite for TASK-FMT-008: Validate fastmcp-python template

Tests all acceptance criteria:
- Template validation passes with 0 errors
- Quality score 8+/10
- All critical components present
"""

import json
import unittest
from pathlib import Path


class TestFastMCPTemplateValidation(unittest.TestCase):
    """Test fastmcp-python template validation"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.template_path = Path("installer/core/templates/fastmcp-python")
        cls.assertTrue(cls.template_path.exists(), f"Template not found: {cls.template_path}")

    def test_manifest_json_valid(self):
        """AC: manifest.json valid"""
        manifest_path = self.template_path / "manifest.json"
        self.assertTrue(manifest_path.exists(), "manifest.json not found")

        with open(manifest_path) as f:
            manifest = json.load(f)

        # Check required fields
        required_fields = ["name", "version", "description"]
        for field in required_fields:
            self.assertIn(field, manifest, f"manifest.json missing field: {field}")

        self.assertEqual(manifest["name"], "fastmcp-python")

    def test_settings_json_valid(self):
        """AC: settings.json valid"""
        settings_path = self.template_path / "settings.json"
        self.assertTrue(settings_path.exists(), "settings.json not found")

        with open(settings_path) as f:
            settings = json.load(f)

        # Settings should not be empty
        self.assertGreater(len(settings), 0, "settings.json is empty")

    def test_at_least_2_agents(self):
        """AC: At least 2 agents"""
        agents_dir = self.template_path / ".claude" / "agents"
        self.assertTrue(agents_dir.exists(), ".claude/agents directory not found")

        agent_files = list(agents_dir.glob("*.md"))
        # Count core agents (not -ext files)
        core_agents = [f for f in agent_files if not f.name.endswith("-ext.md")]

        self.assertGreaterEqual(len(core_agents), 2,
                                f"Expected at least 2 agents, found {len(core_agents)}")

    def test_at_least_6_templates(self):
        """AC: At least 6 template files"""
        templates_dir = self.template_path / "templates"
        self.assertTrue(templates_dir.exists(), "templates directory not found")

        template_files = [f for f in templates_dir.rglob("*") if f.is_file()]
        self.assertGreaterEqual(len(template_files), 6,
                                f"Expected at least 6 template files, found {len(template_files)}")

    def test_at_least_3_rules(self):
        """AC: At least 3 rules"""
        rules_dir = self.template_path / ".claude" / "rules"
        self.assertTrue(rules_dir.exists(), ".claude/rules directory not found")

        rule_files = list(rules_dir.glob("*.md"))
        self.assertGreaterEqual(len(rule_files), 3,
                                f"Expected at least 3 rules, found {len(rule_files)}")

    def test_claude_md_present(self):
        """AC: CLAUDE.md files present"""
        # Check for CLAUDE.md in root or .claude/
        claude_md_paths = [
            self.template_path / "CLAUDE.md",
            self.template_path / ".claude" / "CLAUDE.md"
        ]

        found = any(p.exists() for p in claude_md_paths)
        self.assertTrue(found, "CLAUDE.md not found in template root or .claude/")

    def test_readme_md_present(self):
        """AC: README.md present"""
        readme_path = self.template_path / "README.md"
        self.assertTrue(readme_path.exists(), "README.md not found")

        # Verify README has content
        with open(readme_path) as f:
            content = f.read()
        self.assertGreater(len(content), 100, "README.md appears to be empty or too short")

    def test_quality_score_above_8(self):
        """AC: Quality score 8+/10"""
        # This test verifies the overall quality based on component counts
        results = {
            "manifest": self._check_manifest(),
            "settings": self._check_settings(),
            "agents": self._count_agents(),
            "templates": self._count_templates(),
            "rules": self._count_rules(),
            "documentation": self._check_documentation()
        }

        score = self._calculate_quality_score(results)
        self.assertGreaterEqual(score, 8.0,
                                f"Quality score {score:.1f}/10 is below 8.0")

    def test_no_validation_errors(self):
        """AC: Template passes with 0 errors"""
        errors = []

        # Check all critical components
        if not (self.template_path / "manifest.json").exists():
            errors.append("manifest.json not found")

        if not (self.template_path / "settings.json").exists():
            errors.append("settings.json not found")

        agents_dir = self.template_path / ".claude" / "agents"
        if not agents_dir.exists():
            errors.append(".claude/agents directory not found")
        elif len(list(agents_dir.glob("*.md"))) < 2:
            errors.append("Less than 2 agents found")

        templates_dir = self.template_path / "templates"
        if not templates_dir.exists():
            errors.append("templates directory not found")

        rules_dir = self.template_path / ".claude" / "rules"
        if not rules_dir.exists():
            errors.append(".claude/rules directory not found")

        self.assertEqual(len(errors), 0,
                        f"Validation found {len(errors)} error(s): {', '.join(errors)}")

    # Helper methods
    def _check_manifest(self) -> bool:
        """Check if manifest.json is valid"""
        manifest_path = self.template_path / "manifest.json"
        if not manifest_path.exists():
            return False
        try:
            with open(manifest_path) as f:
                json.load(f)
            return True
        except:
            return False

    def _check_settings(self) -> bool:
        """Check if settings.json is valid"""
        settings_path = self.template_path / "settings.json"
        if not settings_path.exists():
            return False
        try:
            with open(settings_path) as f:
                json.load(f)
            return True
        except:
            return False

    def _count_agents(self) -> int:
        """Count agent files"""
        agents_dir = self.template_path / ".claude" / "agents"
        if not agents_dir.exists():
            return 0
        # Count core agents only
        core_agents = [f for f in agents_dir.glob("*.md") if not f.name.endswith("-ext.md")]
        return len(core_agents)

    def _count_templates(self) -> int:
        """Count template files"""
        templates_dir = self.template_path / "templates"
        if not templates_dir.exists():
            return 0
        return len([f for f in templates_dir.rglob("*") if f.is_file()])

    def _count_rules(self) -> int:
        """Count rule files"""
        rules_dir = self.template_path / ".claude" / "rules"
        if not rules_dir.exists():
            return 0
        return len(list(rules_dir.glob("*.md")))

    def _check_documentation(self) -> bool:
        """Check if documentation exists"""
        claude_md_exists = (self.template_path / "CLAUDE.md").exists() or \
                          (self.template_path / ".claude" / "CLAUDE.md").exists()
        readme_exists = (self.template_path / "README.md").exists()
        return claude_md_exists and readme_exists

    def _calculate_quality_score(self, results: dict) -> float:
        """Calculate quality score based on validation results"""
        weights = {
            "manifest": 15,
            "settings": 15,
            "agents": 25,
            "templates": 20,
            "rules": 15,
            "documentation": 10
        }

        score = 0.0

        if results["manifest"]:
            score += weights["manifest"]

        if results["settings"]:
            score += weights["settings"]

        # Agents (target: 2+)
        agent_count = results["agents"]
        if agent_count >= 2:
            agent_score = min(10, agent_count / 0.2)  # 2 agents = 10 points
            score += (agent_score / 10) * weights["agents"]

        # Templates (target: 6+)
        template_count = results["templates"]
        if template_count >= 6:
            template_score = min(10, template_count / 0.6)  # 6 templates = 10 points
            score += (template_score / 10) * weights["templates"]

        # Rules (target: 3+)
        rule_count = results["rules"]
        if rule_count >= 3:
            rule_score = min(10, rule_count / 0.3)  # 3 rules = 10 points
            score += (rule_score / 10) * weights["rules"]

        if results["documentation"]:
            score += weights["documentation"]

        return score / 10  # Convert to 0-10 scale


if __name__ == "__main__":
    unittest.main()
