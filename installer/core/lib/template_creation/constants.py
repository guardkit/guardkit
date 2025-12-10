"""
Template Creation Constants

Shared constants for template creation workflow components.
Extracted to avoid circular imports between orchestrator and component modules.

TASK-PHASE-7-5-BATCH-PROCESSING: Moved WorkflowPhase to break circular import
"""


class WorkflowPhase:
    """
    Workflow phase constants for template creation orchestration.

    Architectural Context:
    - Eliminates magic numbers throughout codebase (DRY principle)
    - Provides semantic meaning to phase transitions
    - Enables type-safe phase routing in checkpoint-resume pattern
    - Supports both integer and float phase numbers for sub-phases

    Phase Flow:
    1.0  → AI-Native Codebase Analysis
    2.0  → Manifest Generation
    3.0  → Settings Generation
    4.0  → Template File Generation
    4.5  → Completeness Validation
    5.0  → Agent Recommendation
    6.0  → Agent Generation (uses bridge, may exit 42)
    7.0  → Agent Writing
    8.0  → CLAUDE.md Generation
    9.0  → Package Assembly
    9.5  → Extended Validation

    REMOVED: Phase 7.5 Agent Enhancement (TASK-SIMP-9ABE)
    See TASK-PHASE-8-INCREMENTAL for incremental enhancement approach.

    TASK-PHASE-7-5-FIX-FOUNDATION: Foundation quality improvement
    TASK-PHASE-7-5-BATCH-PROCESSING: Moved to constants.py to fix circular import
    """
    PHASE_1 = 1      # AI Analysis
    PHASE_2 = 2      # Manifest Generation
    PHASE_3 = 3      # Settings Generation
    PHASE_4 = 4      # Template Generation
    PHASE_4_5 = 4.5  # Completeness Validation
    PHASE_5 = 5      # Agent Recommendation
    PHASE_6 = 6      # Agent Generation (bridge)
    PHASE_7 = 7      # Agent Writing
    # REMOVED: PHASE_7_5 (Agent Enhancement) - see TASK-SIMP-9ABE
    PHASE_8 = 8      # CLAUDE.md Generation
    PHASE_9 = 9      # Package Assembly
    PHASE_9_5 = 9.5  # Extended Validation
