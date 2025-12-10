"""Question templates for implementation planning clarification (Context C).

Used in /task-work Phase 1.5 to clarify scope, technology choices, integration
points, trade-offs, and edge cases before implementation begins.

Based on the 5W1H framework:
- SCOPE_QUESTIONS (What): Feature boundary and scope definition
- USER_QUESTIONS (Who): User personas and stakeholders
- TECHNOLOGY_QUESTIONS (How): Technology and implementation choices
- INTEGRATION_QUESTIONS (Where): Integration points and system boundaries
- TRADEOFF_QUESTIONS (Why): Priority trade-offs and business justification
- EDGE_CASE_QUESTIONS: Edge case handling and error scenarios
"""

from ..core import Question

# =============================================================================
# SCOPE QUESTIONS (What)
# =============================================================================

SCOPE_QUESTIONS = [
    Question(
        id="scope_boundary",
        category="scope",
        text='Should "{feature}" include {related_capability}?',
        options=["[Y]es", "[N]o", "[D]etails: ___"],
        default="[Y]es",
        rationale="Common expectation for {feature}",
    ),
    Question(
        id="scope_extent",
        category="scope",
        text="What is the boundary for this task?",
        options=[
            "[M]inimal (core only)",
            "[S]tandard (core + common cases)",
            "[C]omplete (all edge cases)",
        ],
        default="[S]tandard (core + common cases)",
        rationale="Standard scope covers most use cases without over-engineering",
    ),
    Question(
        id="scope_validation",
        category="scope",
        text="What level of input validation is needed?",
        options=[
            "[B]asic (null/empty checks)",
            "[S]tandard (type + range validation)",
            "[F]ull (comprehensive validation + sanitization)",
        ],
        default="[S]tandard (type + range validation)",
        rationale="Standard validation provides good security without complexity",
    ),
    Question(
        id="scope_output",
        category="scope",
        text="What output format(s) should be supported?",
        options=["[S]ingle format", "[M]ultiple formats", "[D]etails: ___"],
        default="[S]ingle format",
        rationale="Single format is simpler to implement and test",
    ),
]

# =============================================================================
# USER QUESTIONS (Who)
# =============================================================================

USER_QUESTIONS = [
    Question(
        id="user_primary",
        category="user",
        text="Who is the primary user of this feature?",
        options=[
            "[D]evelopers",
            "[E]nd users",
            "[A]dministrators",
            "[S]ystem/API",
            "[O]ther: ___",
        ],
        default="[D]evelopers",
        rationale="Most common case for development tools",
    ),
    Question(
        id="user_expertise",
        category="user",
        text="What expertise level should we assume?",
        options=[
            "[B]eginner-friendly (extensive guidance)",
            "[I]ntermediate (moderate guidance)",
            "[A]dvanced (minimal guidance)",
        ],
        default="[I]ntermediate (moderate guidance)",
        rationale="Intermediate level balances usability and simplicity",
    ),
    Question(
        id="user_workflow",
        category="user",
        text="How will users typically interact with this?",
        options=[
            "[C]LI/command-line",
            "[G]UI/visual interface",
            "[A]PI/programmatic",
            "[M]ixed/multiple",
        ],
        default="[C]LI/command-line",
        rationale="CLI is most common for development tools",
    ),
]

# =============================================================================
# TECHNOLOGY QUESTIONS (How)
# =============================================================================

TECHNOLOGY_QUESTIONS = [
    Question(
        id="tech_approach",
        category="technology",
        text="Preferred implementation approach for {component}?",
        options=[
            "[A] {option_a}",
            "[B] {option_b}",
            "[C] Let me decide",
            "[O]ther: ___",
        ],
        default="[C] Let me decide",
        rationale="AI will recommend based on codebase patterns",
    ),
    Question(
        id="tech_existing_pattern",
        category="technology",
        text="Use existing {pattern} pattern or create new?",
        options=[
            "[E]xisting (extend/reuse)",
            "[N]ew (create from scratch)",
            "[R]ecommend (AI decides)",
        ],
        default="[R]ecommend (AI decides)",
        rationale="AI will analyze codebase for existing patterns",
    ),
    Question(
        id="tech_async",
        category="technology",
        text="Should this operation be asynchronous?",
        options=[
            "[Y]es (async/await)",
            "[N]o (synchronous)",
            "[R]ecommend (AI decides)",
        ],
        default="[R]ecommend (AI decides)",
        rationale="AI will determine based on operation characteristics",
    ),
    Question(
        id="tech_dependencies",
        category="technology",
        text="Can we add external dependencies if needed?",
        options=[
            "[Y]es (prefer well-maintained libraries)",
            "[L]imited (only if critical)",
            "[N]o (use standard library only)",
        ],
        default="[L]imited (only if critical)",
        rationale="Limit dependencies to reduce maintenance burden",
    ),
    Question(
        id="tech_backwards_compat",
        category="technology",
        text="Do we need backwards compatibility?",
        options=[
            "[Y]es (maintain existing behavior)",
            "[N]o (breaking changes OK)",
            "[P]artial (major versions only)",
        ],
        default="[P]artial (major versions only)",
        rationale="Breaking changes in major versions is standard practice",
    ),
]

# =============================================================================
# INTEGRATION QUESTIONS (Where)
# =============================================================================

INTEGRATION_QUESTIONS = [
    Question(
        id="integration_database",
        category="integration",
        text="Does this require database changes?",
        options=[
            "[Y]es (schema changes needed)",
            "[N]o (no database involvement)",
            "[M]aybe (depends on implementation)",
        ],
        default="[M]aybe (depends on implementation)",
        rationale="AI will determine based on data requirements",
    ),
    Question(
        id="integration_api",
        category="integration",
        text="Does this need to integrate with external APIs?",
        options=[
            "[Y]es ({api_name})",
            "[N]o (internal only)",
            "[U]nsure (investigate)",
        ],
        default="[N]o (internal only)",
        rationale="Most features are internal only",
    ),
    Question(
        id="integration_existing",
        category="integration",
        text="Which existing components will this interact with?",
        options=[
            "[L]ist: {components}",
            "[A]ll (system-wide)",
            "[I]solated (standalone)",
            "[U]nsure (analyze)",
        ],
        default="[U]nsure (analyze)",
        rationale="AI will analyze codebase to identify dependencies",
    ),
    Question(
        id="integration_events",
        category="integration",
        text="Should this emit events/notifications?",
        options=[
            "[Y]es (publish events)",
            "[N]o (silent operation)",
            "[C]onditional (on errors only)",
        ],
        default="[C]onditional (on errors only)",
        rationale="Error notifications are useful without being noisy",
    ),
]

# =============================================================================
# TRADEOFF QUESTIONS (Why)
# =============================================================================

TRADEOFF_QUESTIONS = [
    Question(
        id="tradeoff_priority",
        category="tradeoff",
        text="What's the primary priority for this task?",
        options=[
            "[P]erformance (speed/efficiency)",
            "[M]aintainability (clarity/simplicity)",
            "[F]eatures (functionality/completeness)",
            "[S]ecurity (safety/robustness)",
        ],
        default="[M]aintainability (clarity/simplicity)",
        rationale="Maintainability is crucial for long-term success",
    ),
    Question(
        id="tradeoff_speed_vs_quality",
        category="tradeoff",
        text="If we must trade off, prefer speed or quality?",
        options=[
            "[S]peed (ship faster, iterate)",
            "[Q]uality (thorough, polished)",
            "[B]alanced (reasonable middle ground)",
        ],
        default="[B]alanced (reasonable middle ground)",
        rationale="Balanced approach works for most situations",
    ),
    Question(
        id="tradeoff_complexity",
        category="tradeoff",
        text="How do we handle increased complexity?",
        options=[
            "[A]void (keep simple, limit features)",
            "[M]anage (accept if necessary)",
            "[E]mbrace (full-featured solution)",
        ],
        default="[M]anage (accept if necessary)",
        rationale="Accept complexity when it provides clear value",
    ),
    Question(
        id="tradeoff_testing",
        category="tradeoff",
        text="What testing depth is appropriate?",
        options=[
            "[B]asic (core functionality only)",
            "[S]tandard (common cases + errors)",
            "[C]omprehensive (all scenarios + edge cases)",
        ],
        default="[S]tandard (common cases + errors)",
        rationale="Standard testing covers most real-world usage",
    ),
]

# =============================================================================
# EDGE CASE QUESTIONS
# =============================================================================

EDGE_CASE_QUESTIONS = [
    Question(
        id="edge_case_empty",
        category="edge_case",
        text="How should we handle empty/null inputs?",
        options=[
            "[E]rror (reject invalid)",
            "[D]efault (use sensible default)",
            "[S]kip (treat as no-op)",
        ],
        default="[E]rror (reject invalid)",
        rationale="Failing fast prevents silent errors",
    ),
    Question(
        id="edge_case_large",
        category="edge_case",
        text="How should we handle large data volumes?",
        options=[
            "[L]imit (enforce maximum size)",
            "[P]aginate (chunk processing)",
            "[S]tream (memory-efficient)",
            "[N]one (no special handling)",
        ],
        default="[L]imit (enforce maximum size)",
        rationale="Limits prevent resource exhaustion",
    ),
    Question(
        id="edge_case_concurrent",
        category="edge_case",
        text="How should we handle concurrent access?",
        options=[
            "[L]ock (prevent conflicts)",
            "[R]etry (optimistic approach)",
            "[Q]ueue (serialize access)",
            "[N]one (assume single-threaded)",
        ],
        default="[N]one (assume single-threaded)",
        rationale="Most operations don't require concurrency handling",
    ),
    Question(
        id="edge_case_failure",
        category="edge_case",
        text="How should we handle partial failures?",
        options=[
            "[R]ollback (all-or-nothing)",
            "[C]ontinue (best-effort)",
            "[P]ause (manual intervention)",
        ],
        default="[R]ollback (all-or-nothing)",
        rationale="Rollback maintains data consistency",
    ),
    Question(
        id="edge_case_recovery",
        category="edge_case",
        text="Should this support automatic recovery?",
        options=[
            "[Y]es (auto-retry with backoff)",
            "[N]o (fail immediately)",
            "[M]anual (user-triggered retry)",
        ],
        default="[N]o (fail immediately)",
        rationale="Explicit failure is clearer than silent retries",
    ),
]
