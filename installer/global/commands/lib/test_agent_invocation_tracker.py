"""
Tests for Agent Invocation Tracker.

Task Reference: TASK-ENF2
"""

import unittest
from datetime import datetime
from agent_invocation_tracker import (
    AgentInvocationTracker,
    add_pending_phases
)


class TestAgentInvocationTracker(unittest.TestCase):
    """Test cases for AgentInvocationTracker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.tracker = AgentInvocationTracker()

    def test_initialization(self):
        """Test tracker initializes with empty invocations."""
        self.assertEqual(len(self.tracker.invocations), 0)
        self.assertEqual(self.tracker.get_completed_count(), 0)

    def test_record_invocation(self):
        """Test recording an agent invocation."""
        self.tracker.record_invocation(
            phase="2",
            agent_name="python-api-specialist",
            phase_description="Planning",
            agent_source="local"
        )

        self.assertEqual(len(self.tracker.invocations), 1)
        inv = self.tracker.invocations[0]
        self.assertEqual(inv["phase"], "2")
        self.assertEqual(inv["agent"], "python-api-specialist")
        self.assertEqual(inv["phase_description"], "Planning")
        self.assertEqual(inv["agent_source"], "local")
        self.assertEqual(inv["status"], "in_progress")
        self.assertIsInstance(inv["timestamp"], datetime)

    def test_mark_complete(self):
        """Test marking a phase as complete."""
        # Record invocation
        self.tracker.record_invocation(
            phase="2",
            agent_name="python-api-specialist",
            phase_description="Planning",
            agent_source="local"
        )

        # Mark complete
        self.tracker.mark_complete(
            phase="2",
            duration_seconds=45,
            files_modified=["plan.md"]
        )

        inv = self.tracker.invocations[0]
        self.assertEqual(inv["status"], "completed")
        self.assertEqual(inv["duration"], 45)
        self.assertEqual(inv["files_modified"], ["plan.md"])
        self.assertIn("completed_at", inv)
        self.assertEqual(self.tracker.get_completed_count(), 1)

    def test_mark_skipped(self):
        """Test marking a phase as skipped."""
        self.tracker.mark_skipped(phase="3", reason="Test failed")

        self.assertEqual(len(self.tracker.invocations), 1)
        inv = self.tracker.invocations[0]
        self.assertEqual(inv["phase"], "3")
        self.assertEqual(inv["agent"], "SKIPPED")
        self.assertEqual(inv["status"], "skipped")
        self.assertEqual(inv["skip_reason"], "Test failed")

    def test_get_invocations_by_status(self):
        """Test filtering invocations by status."""
        # Add multiple invocations
        self.tracker.record_invocation("2", "agent1", "Planning", "local")
        self.tracker.mark_complete("2", 30)

        self.tracker.record_invocation("3", "agent2", "Implementation", "global")
        self.tracker.mark_skipped("4", "Not needed")

        # Test filtering
        completed = self.tracker.get_invocations_by_status("completed")
        in_progress = self.tracker.get_invocations_by_status("in_progress")
        skipped = self.tracker.get_invocations_by_status("skipped")

        self.assertEqual(len(completed), 1)
        self.assertEqual(len(in_progress), 1)
        self.assertEqual(len(skipped), 1)

    def test_add_pending_phase(self):
        """Test adding pending phase placeholders."""
        self.tracker.add_pending_phase("2", "Planning", "TBD")

        self.assertEqual(len(self.tracker.invocations), 1)
        inv = self.tracker.invocations[0]
        self.assertEqual(inv["phase"], "2")
        self.assertEqual(inv["agent"], "TBD")
        self.assertEqual(inv["status"], "pending")

    def test_add_pending_phase_duplicate(self):
        """Test that duplicate pending phases are not added."""
        self.tracker.add_pending_phase("2", "Planning", "TBD")
        self.tracker.add_pending_phase("2", "Planning", "TBD")

        # Should only have one entry
        self.assertEqual(len(self.tracker.invocations), 1)

    def test_add_pending_phases_standard(self):
        """Test adding all pending phases for standard workflow."""
        add_pending_phases(self.tracker, workflow_mode="standard")

        # Standard workflow has 5 phases
        self.assertEqual(len(self.tracker.invocations), 5)

        phases = [inv["phase"] for inv in self.tracker.invocations]
        self.assertIn("2", phases)
        self.assertIn("2.5B", phases)
        self.assertIn("3", phases)
        self.assertIn("4", phases)
        self.assertIn("5", phases)

    def test_add_pending_phases_micro(self):
        """Test adding pending phases for micro workflow."""
        add_pending_phases(self.tracker, workflow_mode="micro")

        # Micro workflow has 3 phases
        self.assertEqual(len(self.tracker.invocations), 3)

        phases = [inv["phase"] for inv in self.tracker.invocations]
        self.assertIn("3", phases)
        self.assertIn("4", phases)
        self.assertIn("5", phases)

    def test_source_icon_mapping(self):
        """Test source icon mapping."""
        test_cases = [
            ("local", "📁"),
            ("user", "👤"),
            ("global", "🌐"),
            ("template", "📦"),
            ("template:react-typescript", "📦"),
            ("unknown", "❓")
        ]

        for source, expected_icon in test_cases:
            icon = self.tracker._get_source_icon(source)
            self.assertEqual(icon, expected_icon, f"Failed for source: {source}")

    def test_status_icon_mapping(self):
        """Test status icon mapping."""
        test_cases = [
            ("completed", "✅"),
            ("in_progress", "⏳"),
            ("pending", "⏸️"),
            ("skipped", "❌")
        ]

        for status, expected_icon in test_cases:
            icon = self.tracker._get_status_icon(status)
            self.assertEqual(icon, expected_icon, f"Failed for status: {status}")

    def test_agent_info_formatting(self):
        """Test agent info formatting for different statuses."""
        # Completed
        inv_completed = {
            "agent": "python-api-specialist",
            "status": "completed",
            "agent_source": "local",
            "duration": 45
        }
        info = self.tracker._get_agent_info(inv_completed)
        self.assertIn("python-api-specialist", info)
        self.assertIn("📁", info)
        self.assertIn("local", info)
        self.assertIn("45s", info)

        # In progress
        inv_progress = {
            "agent": "task-manager",
            "status": "in_progress",
            "agent_source": "global"
        }
        info = self.tracker._get_agent_info(inv_progress)
        self.assertIn("task-manager", info)
        self.assertIn("🌐", info)
        self.assertIn("IN PROGRESS", info)

        # Skipped
        inv_skipped = {
            "agent": "SKIPPED",
            "status": "skipped",
            "agent_source": "unknown",
            "skip_reason": "Test failed"
        }
        info = self.tracker._get_agent_info(inv_skipped)
        self.assertIn("SKIPPED", info)
        self.assertIn("Test failed", info)

        # Pending
        inv_pending = {
            "agent": "TBD",
            "status": "pending",
            "agent_source": "unknown"
        }
        info = self.tracker._get_agent_info(inv_pending)
        self.assertEqual(info, "Pending")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
