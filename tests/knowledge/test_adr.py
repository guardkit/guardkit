"""
Comprehensive Test Suite for ADR Entity Model

Tests the ADREntity dataclass, ADRStatus and ADRTrigger enums.
Tests include enum values, dataclass defaults, serialization, and field access.

Coverage Target: >=85%
Test Count: 15+ tests

This is a TDD RED phase test file - all tests will FAIL until implementation.
"""

import pytest
from datetime import datetime
from dataclasses import asdict

# EXPECTED TO FAIL - modules don't exist yet (TDD RED phase)
from guardkit.knowledge.adr import ADRStatus, ADRTrigger, ADREntity


# ============================================================================
# 1. Enum Tests (6 tests)
# ============================================================================


def test_adr_status_enum_values():
    """Test ADRStatus enum has all expected values."""
    assert ADRStatus.PROPOSED.value == "proposed"
    assert ADRStatus.ACCEPTED.value == "accepted"
    assert ADRStatus.DEPRECATED.value == "deprecated"
    assert ADRStatus.SUPERSEDED.value == "superseded"


def test_adr_status_enum_count():
    """Test ADRStatus enum has exactly 4 values."""
    assert len(list(ADRStatus)) == 4


def test_adr_trigger_enum_values():
    """Test ADRTrigger enum has all expected values."""
    assert ADRTrigger.CLARIFYING_QUESTION.value == "clarifying_question"
    assert ADRTrigger.TASK_REVIEW.value == "task_review"
    assert ADRTrigger.IMPLEMENTATION_CHOICE.value == "implementation"
    assert ADRTrigger.MANUAL.value == "manual"
    assert ADRTrigger.DISCOVERED.value == "discovered"


def test_adr_trigger_enum_count():
    """Test ADRTrigger enum has exactly 5 values."""
    assert len(list(ADRTrigger)) == 5


def test_adr_status_enum_members():
    """Test ADRStatus enum member names."""
    status_names = [s.name for s in ADRStatus]
    assert "PROPOSED" in status_names
    assert "ACCEPTED" in status_names
    assert "DEPRECATED" in status_names
    assert "SUPERSEDED" in status_names


def test_adr_trigger_enum_members():
    """Test ADRTrigger enum member names."""
    trigger_names = [t.name for t in ADRTrigger]
    assert "CLARIFYING_QUESTION" in trigger_names
    assert "TASK_REVIEW" in trigger_names
    assert "IMPLEMENTATION_CHOICE" in trigger_names
    assert "MANUAL" in trigger_names
    assert "DISCOVERED" in trigger_names


# ============================================================================
# 2. ADREntity Dataclass Tests (9 tests)
# ============================================================================


def test_adr_entity_minimal_creation():
    """Test creating ADREntity with minimal required fields."""
    adr = ADREntity(
        id="ADR-0001",
        title="Use PostgreSQL for primary database"
    )

    assert adr.id == "ADR-0001"
    assert adr.title == "Use PostgreSQL for primary database"


def test_adr_entity_default_status():
    """Test ADREntity defaults to ACCEPTED status."""
    adr = ADREntity(id="ADR-0001", title="Test Decision")

    assert adr.status == ADRStatus.ACCEPTED


def test_adr_entity_default_trigger():
    """Test ADREntity defaults to MANUAL trigger."""
    adr = ADREntity(id="ADR-0001", title="Test Decision")

    assert adr.trigger == ADRTrigger.MANUAL


def test_adr_entity_default_lists():
    """Test ADREntity defaults empty lists for alternatives and consequences."""
    adr = ADREntity(id="ADR-0001", title="Test Decision")

    assert adr.alternatives_considered == []
    assert adr.consequences == []
    assert adr.related_adrs == []
    assert adr.tags == []


def test_adr_entity_default_strings():
    """Test ADREntity defaults empty strings for text fields."""
    adr = ADREntity(id="ADR-0001", title="Test Decision")

    assert adr.context == ""
    assert adr.decision == ""
    assert adr.rationale == ""


def test_adr_entity_default_optional_fields():
    """Test ADREntity defaults None for optional fields."""
    adr = ADREntity(id="ADR-0001", title="Test Decision")

    assert adr.source_task_id is None
    assert adr.source_feature_id is None
    assert adr.source_command is None
    assert adr.supersedes is None
    assert adr.superseded_by is None
    assert adr.decided_at is None
    assert adr.deprecated_at is None


def test_adr_entity_default_created_at():
    """Test ADREntity sets created_at to current time by default."""
    before = datetime.now()
    adr = ADREntity(id="ADR-0001", title="Test Decision")
    after = datetime.now()

    assert before <= adr.created_at <= after


def test_adr_entity_full_creation():
    """Test creating ADREntity with all fields populated."""
    created = datetime(2026, 1, 24, 12, 0, 0)
    decided = datetime(2026, 1, 24, 13, 0, 0)

    adr = ADREntity(
        id="ADR-0001",
        title="Use PostgreSQL for primary database",
        status=ADRStatus.ACCEPTED,
        trigger=ADRTrigger.TASK_REVIEW,
        source_task_id="TASK-GI-004",
        source_feature_id="FEAT-GI",
        source_command="task-review",
        context="Need reliable ACID guarantees for transactions",
        decision="Use PostgreSQL 15 as primary database",
        rationale="Strong ACID compliance, mature ecosystem, team expertise",
        alternatives_considered=["MySQL", "MongoDB", "CockroachDB"],
        consequences=["Need PostgreSQL hosting", "Team training required"],
        supersedes="ADR-0000",
        superseded_by=None,
        related_adrs=["ADR-0002", "ADR-0003"],
        created_at=created,
        decided_at=decided,
        deprecated_at=None,
        tags=["database", "infrastructure"],
        confidence=0.9
    )

    assert adr.id == "ADR-0001"
    assert adr.title == "Use PostgreSQL for primary database"
    assert adr.status == ADRStatus.ACCEPTED
    assert adr.trigger == ADRTrigger.TASK_REVIEW
    assert adr.source_task_id == "TASK-GI-004"
    assert adr.source_feature_id == "FEAT-GI"
    assert adr.source_command == "task-review"
    assert adr.context == "Need reliable ACID guarantees for transactions"
    assert adr.decision == "Use PostgreSQL 15 as primary database"
    assert adr.rationale == "Strong ACID compliance, mature ecosystem, team expertise"
    assert adr.alternatives_considered == ["MySQL", "MongoDB", "CockroachDB"]
    assert adr.consequences == ["Need PostgreSQL hosting", "Team training required"]
    assert adr.supersedes == "ADR-0000"
    assert adr.superseded_by is None
    assert adr.related_adrs == ["ADR-0002", "ADR-0003"]
    assert adr.created_at == created
    assert adr.decided_at == decided
    assert adr.deprecated_at is None
    assert adr.tags == ["database", "infrastructure"]
    assert adr.confidence == 0.9


def test_adr_entity_serialization():
    """Test ADREntity can be serialized to dict using asdict."""
    adr = ADREntity(
        id="ADR-0001",
        title="Test Decision",
        status=ADRStatus.PROPOSED,
        trigger=ADRTrigger.CLARIFYING_QUESTION
    )

    data = asdict(adr)

    assert isinstance(data, dict)
    assert data["id"] == "ADR-0001"
    assert data["title"] == "Test Decision"
    # Enums should be serialized as enum objects (not values)
    assert data["status"] == ADRStatus.PROPOSED
    assert data["trigger"] == ADRTrigger.CLARIFYING_QUESTION
