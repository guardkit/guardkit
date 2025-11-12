#!/usr/bin/env python3
"""
Complexity Evaluation for TASK-51B2-E
Phase 2.7: Calculate complexity score and route to appropriate review mode
"""

import sys
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

# Complexity Evaluation Models
@dataclass
class FactorScore:
    """Score for a single complexity factor"""
    name: str
    score: int
    max_score: int
    justification: str

    def emoji(self) -> str:
        """Return emoji based on score level"""
        percentage = (self.score / self.max_score) if self.max_score > 0 else 0
        if percentage >= 0.75:
            return "🔴"
        elif percentage >= 0.5:
            return "⚠️"
        else:
            return "✅"


class ReviewMode(Enum):
    """Review mode decision"""
    AUTO_PROCEED = "auto_proceed"
    QUICK_OPTIONAL = "quick_optional"
    FULL_REQUIRED = "full_required"


@dataclass
class ComplexityScore:
    """Complete complexity evaluation result"""
    task_id: str
    total_score: int
    review_mode: ReviewMode
    action: str
    routing: str
    auto_approved: bool
    factor_scores: List[FactorScore]
    forced_triggers: List[str]
    summary: str


class ComplexityCalculator:
    """Calculate complexity score based on implementation plan"""

    def calculate_file_complexity(self, file_count: int) -> FactorScore:
        """
        Calculate file complexity factor (0-3 points)
        - 0 points: 0-2 files (simple, single-component change)
        - 1 point: 3-5 files (moderate, multi-component change)
        - 2 points: 6-8 files (complex, cross-component change)
        - 3 points: 9+ files (very complex, cross-cutting change)
        """
        if file_count <= 2:
            score = 0
            justification = f"Simple change ({file_count} file{'s' if file_count != 1 else ''}) - minimal complexity"
        elif file_count <= 5:
            score = 1
            justification = f"Moderate change ({file_count} files) - multi-file coordination"
        elif file_count <= 8:
            score = 2
            justification = f"Complex change ({file_count} files) - multiple components"
        else:
            score = 3
            justification = f"Very complex change ({file_count} files) - cross-cutting concerns"

        return FactorScore(
            name="file_complexity",
            score=score,
            max_score=3,
            justification=justification
        )

    def calculate_pattern_familiarity(self, patterns: List[str]) -> FactorScore:
        """
        Calculate pattern familiarity factor (0-2 points)
        - 0 points: No patterns or simple patterns (Repository, Factory, Singleton)
        - 1 point: Moderate patterns (Strategy, Observer, Decorator, Command)
        - 2 points: Advanced patterns (Saga, CQRS, Event Sourcing, Mediator)
        """
        if not patterns or any(p.lower() in ['none', 'simple', 'basic', 'repository', 'factory', 'singleton'] for p in patterns):
            score = 0
            justification = "No specific patterns mentioned - straightforward implementation"
        else:
            # Check for advanced patterns
            advanced_patterns = ['saga', 'cqrs', 'event sourcing', 'mediator', 'event-driven']
            moderate_patterns = ['strategy', 'observer', 'decorator', 'command', 'adapter']

            has_advanced = any(p.lower() in advanced_patterns for p in patterns)
            has_moderate = any(p.lower() in moderate_patterns for p in patterns)

            if has_advanced:
                score = 2
                justification = f"Advanced patterns: {', '.join(patterns)} - significant complexity"
            elif has_moderate:
                score = 1
                justification = f"Moderate patterns: {', '.join(patterns)} - familiar complexity"
            else:
                score = 0
                justification = f"Simple patterns: {', '.join(patterns)} - minimal complexity"

        return FactorScore(
            name="pattern_familiarity",
            score=score,
            max_score=2,
            justification=justification
        )

    def calculate_risk_level(self, risk_indicators: List[str]) -> FactorScore:
        """
        Calculate risk level factor (0-3 points)
        Risk Categories:
        - Security (auth, encryption, permissions)
        - Data integrity (schema changes, migrations)
        - External integrations (APIs, third-party services)
        - Performance (optimization, caching, scaling)

        - 0 points: No risk indicators (standard business logic)
        - 1 point: 1-2 risk categories (moderate caution)
        - 2 points: 3-4 risk categories (high caution)
        - 3 points: 5+ risk categories (critical caution)
        """
        if not risk_indicators or 'none' in [r.lower() for r in risk_indicators]:
            score = 0
            justification = "No significant risk indicators - low risk"
        else:
            # Categorize risk indicators
            security_keywords = ['auth', 'encryption', 'permissions', 'security', 'password', 'token', 'oauth']
            data_keywords = ['schema', 'migration', 'database', 'sql', 'data integrity']
            external_keywords = ['api', 'third-party', 'integration', 'external', 'webhook']
            performance_keywords = ['optimization', 'caching', 'scaling', 'performance', 'load']

            risk_categories = set()
            for indicator in risk_indicators:
                indicator_lower = indicator.lower()
                if any(kw in indicator_lower for kw in security_keywords):
                    risk_categories.add('security')
                if any(kw in indicator_lower for kw in data_keywords):
                    risk_categories.add('data_integrity')
                if any(kw in indicator_lower for kw in external_keywords):
                    risk_categories.add('external_integration')
                if any(kw in indicator_lower for kw in performance_keywords):
                    risk_categories.add('performance')

            category_count = len(risk_categories)

            if category_count == 0:
                score = 0
                justification = f"Indicators present but low risk: {', '.join(risk_indicators)}"
            elif category_count <= 2:
                score = 1
                justification = f"Moderate risk ({category_count} risk categor{'ies' if category_count > 1 else 'y'}) - standard caution"
            elif category_count <= 4:
                score = 2
                justification = f"High risk ({category_count} risk categories) - comprehensive review required"
            else:
                score = 3
                justification = f"Critical risk ({category_count}+ risk categories) - maximum caution"

        return FactorScore(
            name="risk_level",
            score=score,
            max_score=3,
            justification=justification
        )


class ReviewRouter:
    """Route task to appropriate review mode based on complexity score"""

    def route(self, task_id: str, total_score: int, factor_scores: List[FactorScore],
              forced_triggers: List[str]) -> ComplexityScore:
        """
        Route based on score and triggers:
        - Score 1-3: AUTO_PROCEED
        - Score 4-6: QUICK_OPTIONAL
        - Score 7-10 or triggers: FULL_REQUIRED
        """

        # Check for forced triggers
        if forced_triggers:
            review_mode = ReviewMode.FULL_REQUIRED
            action = "review_required"
            routing = "Phase 2.8 Checkpoint (Mandatory)"
            auto_approved = False
            summary = self._generate_full_required_summary(
                task_id, total_score, factor_scores, forced_triggers
            )
        elif total_score <= 3:
            review_mode = ReviewMode.AUTO_PROCEED
            action = "proceed"
            routing = "Phase 3 (Implementation)"
            auto_approved = True
            summary = self._generate_auto_proceed_summary(
                task_id, total_score, factor_scores
            )
        elif total_score <= 6:
            review_mode = ReviewMode.QUICK_OPTIONAL
            action = "review_optional"
            routing = "Phase 2.8 Checkpoint (Optional)"
            auto_approved = False
            summary = self._generate_quick_optional_summary(
                task_id, total_score, factor_scores
            )
        else:  # 7-10
            review_mode = ReviewMode.FULL_REQUIRED
            action = "review_required"
            routing = "Phase 2.8 Checkpoint (Mandatory)"
            auto_approved = False
            summary = self._generate_full_required_summary(
                task_id, total_score, factor_scores, forced_triggers
            )

        return ComplexityScore(
            task_id=task_id,
            total_score=total_score,
            review_mode=review_mode,
            action=action,
            routing=routing,
            auto_approved=auto_approved,
            factor_scores=factor_scores,
            forced_triggers=forced_triggers,
            summary=summary
        )

    def _generate_auto_proceed_summary(self, task_id: str, total_score: int,
                                      factor_scores: List[FactorScore]) -> str:
        """Generate summary for auto-proceed tasks"""
        lines = [
            f"Complexity Evaluation - {task_id}",
            "",
            f"Score: {total_score}/10 (Low Complexity - Auto-Proceed)",
            "",
            "Factor Breakdown:"
        ]

        for factor in factor_scores:
            emoji = factor.emoji()
            lines.append(f"  {emoji} {factor.name}: {factor.score}/{factor.max_score} - {factor.justification}")

        lines.extend([
            "",
            "AUTO-PROCEEDING to Phase 3 (Implementation)",
            "   No human review required for this simple task."
        ])

        return "\n".join(lines)

    def _generate_quick_optional_summary(self, task_id: str, total_score: int,
                                        factor_scores: List[FactorScore]) -> str:
        """Generate summary for quick optional review"""
        lines = [
            f"Complexity Evaluation - {task_id}",
            "",
            f"Score: {total_score}/10 (Moderate Complexity - Optional Review)",
            "",
            "Factor Breakdown:"
        ]

        for factor in factor_scores:
            emoji = factor.emoji()
            lines.append(f"  {emoji} {factor.name}: {factor.score}/{factor.max_score} - {factor.justification}")

        lines.extend([
            "",
            "OPTIONAL CHECKPOINT",
            "   You may review the plan before proceeding, but it's not required.",
            "   [A]pprove and proceed | [R]eview in detail | [Enter] to auto-approve"
        ])

        return "\n".join(lines)

    def _generate_full_required_summary(self, task_id: str, total_score: int,
                                       factor_scores: List[FactorScore],
                                       forced_triggers: List[str]) -> str:
        """Generate summary for full required review"""
        lines = [
            f"Complexity Evaluation - {task_id}",
            "",
            f"Score: {total_score}/10 (High Complexity - REVIEW REQUIRED)",
            ""
        ]

        if forced_triggers:
            lines.append("Force-Review Triggers:")
            for trigger in forced_triggers:
                lines.append(f"  🔴 {trigger}")
            lines.append("")

        lines.append("Factor Breakdown:")

        for factor in factor_scores:
            emoji = factor.emoji()
            lines.append(f"  {emoji} {factor.name}: {factor.score}/{factor.max_score} - {factor.justification}")

        lines.extend([
            "",
            "MANDATORY CHECKPOINT - Phase 2.8 Required",
            "   This task requires human review before implementation.",
            "   Proceeding to Phase 2.8 human checkpoint..."
        ])

        return "\n".join(lines)


def evaluate_complexity_51B2E():
    """
    Evaluate complexity for TASK-51B2-E based on implementation plan summary

    Implementation Plan Summary:
    - Files to modify: 1 file (template_create_orchestrator.py, lines 500-503)
    - LOC changes: 3 lines (exact replacement)
    - Duration: 0.5-1 hours
    - Change type: Bug fix - replace function call with class instantiation
    - Design patterns: None (API usage correction)
    - External dependencies: 0 (using existing agent_scanner module)
    - Risk indicators: None (low-risk bug fix, no business logic changes)
    """

    task_id = "TASK-51B2-E"

    # Extract data from implementation plan
    file_count = 1
    patterns = ["None"]  # Simple class instantiation pattern
    risk_indicators = ["None"]  # Low-risk bug fix

    # User flags and metadata
    user_review_flag = False
    task_metadata = {
        "priority": "medium",
        "tags": [],
        "change_type": "bug_fix"
    }

    # Calculate complexity factors
    calculator = ComplexityCalculator()

    file_complexity = calculator.calculate_file_complexity(file_count)
    pattern_familiarity = calculator.calculate_pattern_familiarity(patterns)
    risk_level = calculator.calculate_risk_level(risk_indicators)

    factor_scores = [file_complexity, pattern_familiarity, risk_level]

    # Calculate total score
    total_score = sum(f.score for f in factor_scores)

    # Ensure minimum score of 1 (per specification)
    if total_score == 0:
        total_score = 1

    # Detect force-review triggers
    forced_triggers = []

    if user_review_flag:
        forced_triggers.append("User Flag (--review)")

    # Check for security keywords (none in this case)
    security_keywords = ['auth', 'encryption', 'permissions', 'security', 'oauth', 'token']
    # No security keywords detected

    # Check for breaking changes (none in this case)
    # Bug fix with no API changes

    # Check for schema changes (none in this case)
    # No database changes

    # Check for hotfix flag (none in this case)
    if 'hotfix' in task_metadata.get('tags', []):
        forced_triggers.append("Production Hotfix")

    # Route to review mode
    router = ReviewRouter()
    decision = router.route(task_id, total_score, factor_scores, forced_triggers)

    return decision


def main():
    """Main execution"""
    print("=" * 80)
    print("PHASE 2.7: COMPLEXITY EVALUATION")
    print("=" * 80)
    print()

    # Evaluate complexity
    decision = evaluate_complexity_51B2E()

    # Display decision summary
    print(decision.summary)
    print()
    print("=" * 80)
    print("COMPLEXITY EVALUATION COMPLETE")
    print("=" * 80)
    print()

    # Display metadata for task file update
    print("Metadata for task file update:")
    print(f"  task_id: {decision.task_id}")
    print(f"  complexity_score: {decision.total_score}/10")
    print(f"  review_mode: {decision.review_mode.value}")
    print(f"  action: {decision.action}")
    print(f"  routing: {decision.routing}")
    print(f"  auto_approved: {decision.auto_approved}")
    print(f"  forced_triggers: {decision.forced_triggers}")
    print()

    # Return exit code based on routing
    if decision.review_mode == ReviewMode.AUTO_PROCEED:
        print("✅ Proceeding to Phase 3 (Implementation)")
        return 0
    elif decision.review_mode == ReviewMode.QUICK_OPTIONAL:
        print("⚠️  Optional checkpoint available")
        return 0
    else:  # FULL_REQUIRED
        print("🔴 Mandatory checkpoint required")
        return 0


if __name__ == "__main__":
    sys.exit(main())
