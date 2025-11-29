---
id: TASK-OPUS-89AA
title: "Integrate Opus 4.5 into /task-review with depth-based model routing"
status: completed
created: 2025-11-25T13:15:00Z
updated: 2025-11-26T13:30:00Z
completed_at: 2025-11-25T17:53:00Z
priority: high
tags: [optimization, model-selection, task-review, opus-4.5]
complexity: 6
estimated_hours: 8
actual_hours: 8
related_tasks: [TASK-895A]
test_results:
  status: passed
  coverage: 100
  test_count: 18
  last_run: 2025-11-25T17:53:00Z
implementation_summary: "Implemented intelligent model routing for /task-review command with Opus 4.5 for high-value scenarios. Created ModelRouter class with depth-based routing matrix (80% Sonnet, 20% Opus). Security reviews always use Opus 4. Comprehensive architectural reviews and standard+ decision reviews use Opus 4. All other scenarios use Sonnet 4.5 for cost efficiency. Includes cost transparency, graceful degradation, and comprehensive unit tests (18 tests)."
completed_location: tasks/completed/TASK-OPUS-89AA/
organized_files: ["TASK-OPUS-89AA.md"]
---

# Task: Integrate Opus 4.5 into `/task-review` with Depth-Based Model Routing

## Executive Summary

Implement intelligent model routing for the `/task-review` command to use **Opus 4.5 for high-value review scenarios** while maintaining **Sonnet 4.5 for cost-effective reviews**. This addresses the user's direction to leverage Opus 4.5's superior reasoning capabilities for critical analysis tasks while keeping scope minimal to avoid regressions.

**Key Decision from TASK-895A**: Opus 4.5 was deferred for general use (planning, implementation) but makes strategic sense for `/task-review` where deep analysis justifies the 67% cost premium.

## Context and Analysis

### User Request
> "For the TaskReview command, which model would this be using? Because I'm thinking really for TaskReview we ought to be using opus 4.5 now."

### Current State
- `/task-review` command is **working** (user confirmed active use)
- Currently uses **Sonnet 4.5** for all review modes
- 5 review modes: architectural, code-quality, decision, technical-debt, security
- 3 depth levels: quick (15-30min), standard (1-2h), comprehensive (4-6h)

### TASK-895A Analysis Findings

**Opus 4.5 Pricing**:
- Input: $5 per M tokens (vs $3 Sonnet) = 67% more expensive
- Output: $25 per M tokens (vs $15 Sonnet) = 67% more expensive

**Cost Comparison** (typical review):
- Sonnet: $0.27 per standard review
- Opus: $0.45 per standard review
- **Increase**: +$0.18 (+67%) per Opus review

**Why Opus Was Deferred for Implementation**:
- Planning/coding doesn't show quality gap with Sonnet
- Phase 4.5 test enforcement catches implementation issues
- 67% cost increase not justified for routine tasks

**Why Opus Makes Sense for Reviews**:
- Reviews are **analysis-heavy, not implementation**
- No auto-fix loop (decisions are one-shot)
- **High-impact decisions** justify premium cost
- Security breaches cost $100K-$10M (model cost: $1-5)
- Wrong architecture costs 6-12 months rework ($200K-$1M)

### Strategic Value

**Cost Impact** (monthly, hypothetical team):
- 10 quick reviews: +$0.06 (only security uses Opus)
- 20 standard reviews: +$0.72 (20% use Opus for decisions/security)
- 5 comprehensive reviews: +$1.35 (60% use Opus)
- **Total**: +$2.13/month or **~9% increase**

**ROI Analysis**:
- Security audit: Opus cost $1-5, breach prevention: $100K-$10M = **20,000x-2,000,000x ROI**
- Architectural decision: Opus cost $1-2, wrong choice: $200K-$1M = **200,000x-1,000,000x ROI**
- Technical debt: Opus cost $1-2, wrong priority: $50K-$200K = **50,000x-200,000x ROI**

## Problem Statement

Current `/task-review` uses Sonnet 4.5 for all scenarios, missing opportunities to leverage Opus 4.5's superior reasoning for:
1. **Security audits** (all depths) - security breaches cost exponentially more than model costs
2. **Comprehensive architectural reviews** - deep analysis needed for SOLID/DRY/YAGNI compliance
3. **Decision analysis** (standard/comprehensive) - complex trade-offs require strong reasoning
4. **Technical debt prioritization** (comprehensive) - nuanced analysis of effort vs impact

## Proposed Solution

### Depth-Based Routing Matrix

Implement intelligent routing that balances cost efficiency with quality requirements:

```
┌──────────────┬───────────────┬────────────────┬─────────────────┐
│ Mode         │ Quick         │ Standard       │ Comprehensive   │
├──────────────┼───────────────┼────────────────┼─────────────────┤
│ Architectural│ Sonnet 4.5    │ Sonnet 4.5     │ Opus 4.5        │
│ Code Quality │ Sonnet 4.5    │ Sonnet 4.5     │ Sonnet 4.5      │
│ Decision     │ Sonnet 4.5    │ Opus 4.5       │ Opus 4.5        │
│ Tech Debt    │ Sonnet 4.5    │ Sonnet 4.5     │ Opus 4.5        │
│ Security     │ Opus 4.5      │ Opus 4.5       │ Opus 4.5        │
└──────────────┴───────────────┴────────────────┴─────────────────┘
```

**Rationale**:
- **Quick reviews**: Speed matters, Sonnet sufficient (except security)
- **Standard reviews**: Balance cost/quality, Opus only for decisions/security
- **Comprehensive reviews**: High-value analysis justifies Opus cost (except metrics-based code quality)
- **Security**: Always Opus 4.5 (non-negotiable - security is critical)

**Result**: 12/15 scenarios (80%) use Sonnet, 3/15 (20%) use Opus

### Architecture Design

**Minimal Scope Strategy**:
- ✅ Create ONE new file: `model_router.py` (centralized routing logic)
- ✅ Modify TWO existing files minimally:
  - `orchestrator.py`: Add model selection call
  - `agent_invoker.py`: Accept optional model parameter
- ❌ NO changes to agent files (agents are model-agnostic)
- ❌ NO changes to command specification

**Component Structure**:
```
installer/global/lib/
├── task_review/
│   ├── __init__.py
│   ├── orchestrator.py           # MODIFY: Add model selection
│   ├── model_router.py           # NEW: Routing logic
│   ├── review_agents.py          # No changes
│   └── report_generator.py       # No changes
└── core/
    ├── agent_invoker.py          # MODIFY: Accept model param
    └── llm_client.py             # No changes
```

## Detailed Implementation Specification

### 1. New File: `model_router.py`

**Location**: `installer/global/lib/task_review/model_router.py`

**Purpose**: Centralized model selection logic with cost transparency

**Complete Implementation**:

```python
"""
Model Router for Task Review Command

Determines optimal Claude model based on review mode and depth.
Balances cost efficiency with quality requirements.

Decision Matrix:
- Quick reviews: Sonnet (speed matters)
- Standard reviews: Mixed (Opus for critical scenarios)
- Comprehensive reviews: Opus for high-value analysis
- Security: Always Opus (security breaches cost more than models)
"""

from typing import Dict, Literal, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

ReviewMode = Literal["architectural", "code-quality", "decision", "technical-debt", "security"]
ReviewDepth = Literal["quick", "standard", "comprehensive"]
ModelId = Literal["claude-opus-4.5-20250514", "claude-sonnet-4.5-20250929"]


@dataclass
class ModelCostInfo:
    """Cost information for model selection transparency."""
    model_id: str
    input_cost_per_mtok: float  # Per million tokens
    output_cost_per_mtok: float
    estimated_tokens: int
    estimated_cost_usd: float
    rationale: str


class ModelRouter:
    """
    Routes review tasks to appropriate Claude model.

    Philosophy:
    - Quick: Speed > thoroughness (except security)
    - Standard: Balance cost/quality (Opus for critical scenarios)
    - Comprehensive: Quality justifies cost (high-value analysis)
    - Security: Always Opus (breaches cost more than models)
    """

    # Model routing matrix (80% Sonnet, 20% Opus)
    ROUTING_MATRIX: Dict[ReviewDepth, Dict[ReviewMode, ModelId]] = {
        "quick": {
            "architectural": "claude-sonnet-4.5-20250929",
            "code-quality": "claude-sonnet-4.5-20250929",
            "decision": "claude-sonnet-4.5-20250929",
            "technical-debt": "claude-sonnet-4.5-20250929",
            "security": "claude-opus-4.5-20250514",  # Exception: Always critical
        },
        "standard": {
            "architectural": "claude-sonnet-4.5-20250929",
            "code-quality": "claude-sonnet-4.5-20250929",
            "decision": "claude-opus-4.5-20250514",  # Decisions need deep reasoning
            "technical-debt": "claude-sonnet-4.5-20250929",
            "security": "claude-opus-4.5-20250514",  # Always critical
        },
        "comprehensive": {
            "architectural": "claude-opus-4.5-20250514",  # Deep SOLID/DRY/YAGNI analysis
            "code-quality": "claude-sonnet-4.5-20250929",  # Metrics are objective
            "decision": "claude-opus-4.5-20250514",  # Critical decisions
            "technical-debt": "claude-opus-4.5-20250514",  # Complex prioritization
            "security": "claude-opus-4.5-20250514",  # Always critical
        }
    }

    # Pricing per million tokens
    PRICING = {
        "claude-opus-4.5-20250514": {"input": 5.00, "output": 25.00},
        "claude-sonnet-4.5-20250929": {"input": 3.00, "output": 15.00},
    }

    # Estimated token usage by depth
    TOKEN_ESTIMATES = {
        "quick": 20_000,      # 15-30 min
        "standard": 60_000,   # 1-2 hours
        "comprehensive": 150_000,  # 4-6 hours
    }

    def get_model_for_review(
        self,
        mode: ReviewMode,
        depth: ReviewDepth = "standard"
    ) -> ModelId:
        """
        Select optimal model for review task.

        Args:
            mode: Type of review (architectural, security, etc.)
            depth: Review thoroughness (quick, standard, comprehensive)

        Returns:
            Claude model ID to use
        """
        model_id = self.ROUTING_MATRIX[depth][mode]

        logger.info(
            f"Model routing: mode={mode}, depth={depth} → {model_id}",
            extra={
                "review_mode": mode,
                "review_depth": depth,
                "selected_model": model_id,
            }
        )

        return model_id

    def get_cost_estimate(
        self,
        mode: ReviewMode,
        depth: ReviewDepth = "standard"
    ) -> ModelCostInfo:
        """
        Estimate cost for review task with transparency.

        Args:
            mode: Type of review
            depth: Review thoroughness

        Returns:
            Cost information including model, pricing, and rationale
        """
        model_id = self.get_model_for_review(mode, depth)
        pricing = self.PRICING[model_id]
        estimated_tokens = self.TOKEN_ESTIMATES[depth]

        # Assume 70/30 input/output split
        input_tokens = int(estimated_tokens * 0.7)
        output_tokens = int(estimated_tokens * 0.3)

        estimated_cost = (
            (input_tokens / 1_000_000) * pricing["input"] +
            (output_tokens / 1_000_000) * pricing["output"]
        )

        rationale = self._get_routing_rationale(mode, depth, model_id)

        return ModelCostInfo(
            model_id=model_id,
            input_cost_per_mtok=pricing["input"],
            output_cost_per_mtok=pricing["output"],
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=round(estimated_cost, 2),
            rationale=rationale,
        )

    def _get_routing_rationale(
        self,
        mode: ReviewMode,
        depth: ReviewDepth,
        model_id: ModelId
    ) -> str:
        """Generate human-readable rationale for model selection."""

        if mode == "security":
            return "Security reviews always use Opus 4.5 (security breaches cost exponentially more than model costs)"

        if model_id.startswith("claude-opus"):
            reasons = []
            if depth == "comprehensive":
                reasons.append(f"{depth} depth requires deep analysis")
            if mode == "decision":
                reasons.append("complex decisions require strong reasoning capabilities")
            if mode == "architectural":
                reasons.append("thorough SOLID/DRY/YAGNI evaluation needs deep pattern recognition")
            if mode == "technical-debt":
                reasons.append("debt prioritization requires nuanced effort vs impact analysis")

            return f"Using Opus 4.5: {', '.join(reasons)}"
        else:
            reasons = []
            if depth == "quick":
                reasons.append("quick reviews prioritize speed over thoroughness")
            if mode == "code-quality":
                reasons.append("quality metrics are objective and well-suited for Sonnet")

            return f"Using Sonnet 4.5: {', '.join(reasons) or 'cost-effective for this review type'}"

    def log_model_usage(
        self,
        task_id: str,
        mode: ReviewMode,
        depth: ReviewDepth,
        model_id: ModelId,
        actual_tokens: int = None
    ) -> None:
        """
        Log model usage for cost tracking and analysis.

        Args:
            task_id: Task being reviewed
            mode: Review mode
            depth: Review depth
            model_id: Model used
            actual_tokens: Actual token count (if available)
        """
        logger.info(
            f"Review completed: {task_id} using {model_id}",
            extra={
                "task_id": task_id,
                "review_mode": mode,
                "review_depth": depth,
                "model_id": model_id,
                "actual_tokens": actual_tokens,
            }
        )
```

### 2. Modify: `orchestrator.py`

**Location**: `installer/global/lib/task_review/orchestrator.py`

**Changes Required** (MINIMAL SCOPE):

```python
# At the top of the file, add import:
from .model_router import ModelRouter, ReviewMode, ReviewDepth

class TaskReviewOrchestrator:
    """Orchestrates task review workflow with optimal model selection."""

    def __init__(self):
        self.model_router = ModelRouter()  # NEW: Add model router
        self.agent_invoker = AgentInvoker()
        self.task_manager = TaskManager()

    def execute_review(
        self,
        task_id: str,
        mode: ReviewMode = "architectural",
        depth: ReviewDepth = "standard",
        output_format: Literal["summary", "detailed", "presentation"] = "detailed"
    ) -> dict:
        """Execute review workflow with optimal model selection."""

        # NEW: Phase 0 - Model selection and cost transparency
        model_id = self.model_router.get_model_for_review(mode, depth)
        cost_info = self.model_router.get_cost_estimate(mode, depth)

        logger.info(f"Starting review: {task_id}")
        logger.info(f"Model: {model_id}")
        logger.info(f"Estimated cost: ${cost_info.estimated_cost_usd}")

        # NEW: Display cost info to user
        self._display_cost_info(cost_info)

        # Existing Phase 1: Load review context
        context = self._load_review_context(task_id)

        # MODIFIED Phase 2: Execute review analysis (pass model preference)
        findings = self._execute_review_analysis(
            context=context,
            mode=mode,
            depth=depth,
            model_id=model_id  # NEW: Pass model to agent invocation
        )

        # Existing Phase 3: Synthesize recommendations
        recommendations = self._synthesize_recommendations(findings, mode, model_id)

        # Existing Phase 4: Generate review report
        report = self._generate_report(
            task_id=task_id,
            mode=mode,
            depth=depth,
            findings=findings,
            recommendations=recommendations,
            output_format=output_format,
            model_used=model_id  # NEW: Include model in report
        )

        # Existing Phase 5: Human decision checkpoint
        decision = self._decision_checkpoint(task_id, report)

        # NEW: Log model usage
        self.model_router.log_model_usage(
            task_id=task_id,
            mode=mode,
            depth=depth,
            model_id=model_id
        )

        return {
            "task_id": task_id,
            "mode": mode,
            "depth": depth,
            "model_used": model_id,  # NEW: Include in result
            "findings": findings,
            "recommendations": recommendations,
            "report_path": report["path"],
            "decision": decision,
        }

    # NEW: Cost display method
    def _display_cost_info(self, cost_info) -> None:
        """Display cost information to user before starting review."""
        print(f"\n{'='*70}")
        print(f"📊 Review Cost Estimate")
        print(f"{'='*70}")
        print(f"Model: {cost_info.model_id}")
        print(f"Estimated tokens: {cost_info.estimated_tokens:,}")
        print(f"Estimated cost: ${cost_info.estimated_cost_usd:.2f}")
        print(f"Rationale: {cost_info.rationale}")
        print(f"{'='*70}\n")

    # MODIFIED: Pass model to agent invocation
    def _execute_review_analysis(
        self,
        context: dict,
        mode: ReviewMode,
        depth: ReviewDepth,
        model_id: str  # NEW parameter
    ) -> dict:
        """Execute review analysis using appropriate agents with model preference."""

        # Map mode to primary agent (existing logic)
        agent_mapping = {
            "architectural": "architectural-reviewer",
            "code-quality": "code-reviewer",
            "decision": "software-architect",
            "technical-debt": "code-reviewer",
            "security": "security-specialist",
        }

        primary_agent = agent_mapping[mode]

        # MODIFIED: Invoke agent with model preference
        findings = self.agent_invoker.invoke_agent(
            agent_name=primary_agent,
            context=context,
            model=model_id,  # NEW: Pass model preference
            depth=depth
        )

        return findings
```

### 3. Modify: `agent_invoker.py`

**Location**: `installer/global/lib/core/agent_invoker.py`

**Changes Required** (MINIMAL SCOPE):

```python
class AgentInvoker:
    """Invokes agents with configurable model selection."""

    DEFAULT_MODEL = "claude-sonnet-4.5-20250929"

    # MODIFIED: Accept optional model parameter
    def invoke_agent(
        self,
        agent_name: str,
        context: dict,
        model: Optional[str] = None,  # NEW: Optional model override
        **kwargs
    ) -> dict:
        """
        Invoke agent with optional model preference.

        Args:
            agent_name: Agent to invoke
            context: Context for agent
            model: Optional model override (defaults to Sonnet 4.5)
            **kwargs: Additional agent parameters

        Returns:
            Agent response
        """

        # NEW: Use provided model or fall back to default
        selected_model = model or self.DEFAULT_MODEL

        logger.info(
            f"Invoking agent: {agent_name} with model: {selected_model}",
            extra={
                "agent_name": agent_name,
                "model_id": selected_model,
                "model_override": model is not None,
            }
        )

        # Existing: Load agent definition
        agent_def = self._load_agent_definition(agent_name)

        # Existing: Build prompt from agent definition + context
        prompt = self._build_agent_prompt(agent_def, context, **kwargs)

        # MODIFIED: Invoke LLM with selected model
        try:
            response = self._invoke_llm(
                prompt=prompt,
                model=selected_model  # NEW: Pass model to LLM client
            )
            return response

        except Exception as e:
            # NEW: Graceful degradation - fall back to Sonnet if Opus fails
            if selected_model.startswith("claude-opus"):
                logger.warning(
                    f"Opus invocation failed, falling back to Sonnet: {e}",
                    extra={"agent_name": agent_name, "error": str(e)}
                )
                return self._invoke_llm(
                    prompt=prompt,
                    model=self.DEFAULT_MODEL
                )
            else:
                raise

    # MODIFIED: Accept model parameter
    def _invoke_llm(self, prompt: str, model: str) -> dict:
        """
        Actual LLM invocation.

        Args:
            prompt: Prompt to send
            model: Claude model ID to use

        Returns:
            LLM response
        """
        # Existing implementation - just ensure model is passed to API
        # (Implementation depends on your LLM client)
        pass
```

## Acceptance Criteria

### Functional Requirements

- [ ] **AC1**: `ModelRouter` class implemented with routing matrix
- [ ] **AC2**: Quick security reviews use Opus 4.5
- [ ] **AC3**: Standard decision reviews use Opus 4.5
- [ ] **AC4**: Comprehensive architectural reviews use Opus 4.5
- [ ] **AC5**: Comprehensive security reviews use Opus 4.5
- [ ] **AC6**: Quick non-security reviews use Sonnet 4.5
- [ ] **AC7**: Standard non-decision reviews use Sonnet 4.5
- [ ] **AC8**: Code quality reviews always use Sonnet 4.5
- [ ] **AC9**: Cost estimate displayed before review starts
- [ ] **AC10**: Model selection logged for cost tracking

### Quality Requirements

- [ ] **AC11**: Zero changes to agent files (agents remain model-agnostic)
- [ ] **AC12**: Backward compatible (default behavior unchanged)
- [ ] **AC13**: Graceful degradation (Opus failure → Sonnet fallback)
- [ ] **AC14**: Clear rationale displayed for model selection
- [ ] **AC15**: Model selection is deterministic (same inputs → same model)

### Testing Requirements

- [ ] **AC16**: Unit tests for all routing matrix scenarios (15 tests)
- [ ] **AC17**: Unit tests for cost estimation accuracy
- [ ] **AC18**: Integration test: comprehensive security review uses Opus
- [ ] **AC19**: Integration test: graceful degradation on Opus failure
- [ ] **AC20**: Integration test: cost info displayed to user

### Performance Requirements

- [ ] **AC21**: Model selection adds <100ms overhead
- [ ] **AC22**: Routing logic has zero external dependencies
- [ ] **AC23**: Cost calculation completes in <10ms

## Testing Strategy

### Unit Tests

**File**: `tests/unit/lib/task_review/test_model_router.py`

```python
import pytest
from installer.global.lib.task_review.model_router import ModelRouter

OPUS_ID = "claude-opus-4.5-20250514"
SONNET_ID = "claude-sonnet-4.5-20250929"

class TestModelRouter:
    """Unit tests for model routing logic."""

    def test_quick_architectural_uses_sonnet(self):
        router = ModelRouter()
        assert router.get_model_for_review("architectural", "quick") == SONNET_ID

    def test_quick_security_uses_opus(self):
        """Security is always Opus, even for quick reviews."""
        router = ModelRouter()
        assert router.get_model_for_review("security", "quick") == OPUS_ID

    def test_standard_decision_uses_opus(self):
        """Decisions need deep reasoning at standard depth."""
        router = ModelRouter()
        assert router.get_model_for_review("decision", "standard") == OPUS_ID

    def test_standard_security_uses_opus(self):
        """Security is always Opus."""
        router = ModelRouter()
        assert router.get_model_for_review("security", "standard") == OPUS_ID

    def test_comprehensive_architectural_uses_opus(self):
        """Comprehensive architectural analysis needs Opus."""
        router = ModelRouter()
        assert router.get_model_for_review("architectural", "comprehensive") == OPUS_ID

    def test_comprehensive_code_quality_uses_sonnet(self):
        """Code quality metrics are objective, Sonnet sufficient."""
        router = ModelRouter()
        assert router.get_model_for_review("code-quality", "comprehensive") == SONNET_ID

    def test_all_security_uses_opus(self):
        """Security always uses Opus regardless of depth."""
        router = ModelRouter()
        for depth in ["quick", "standard", "comprehensive"]:
            assert router.get_model_for_review("security", depth) == OPUS_ID

    def test_cost_estimate_accuracy_sonnet(self):
        """Cost estimates are accurate for Sonnet."""
        router = ModelRouter()
        cost_info = router.get_cost_estimate("code-quality", "standard")

        assert cost_info.model_id == SONNET_ID
        assert cost_info.input_cost_per_mtok == 3.00
        assert cost_info.output_cost_per_mtok == 15.00
        assert cost_info.estimated_tokens == 60_000
        # 70/30 split: (42K * $3 + 18K * $15) / 1M = $0.126 + $0.270 = $0.396
        assert 0.39 <= cost_info.estimated_cost_usd <= 0.41

    def test_cost_estimate_accuracy_opus(self):
        """Cost estimates are accurate for Opus."""
        router = ModelRouter()
        cost_info = router.get_cost_estimate("security", "comprehensive")

        assert cost_info.model_id == OPUS_ID
        assert cost_info.input_cost_per_mtok == 5.00
        assert cost_info.output_cost_per_mtok == 25.00
        assert cost_info.estimated_tokens == 150_000
        # 70/30 split: (105K * $5 + 45K * $25) / 1M = $0.525 + $1.125 = $1.65
        assert 1.60 <= cost_info.estimated_cost_usd <= 1.70

    def test_rationale_generation_security(self):
        """Security reviews have clear rationale."""
        router = ModelRouter()
        cost_info = router.get_cost_estimate("security", "quick")

        assert "security breaches cost" in cost_info.rationale.lower()
        assert "opus" in cost_info.rationale.lower()

    def test_rationale_generation_comprehensive(self):
        """Comprehensive reviews explain why Opus is needed."""
        router = ModelRouter()
        cost_info = router.get_cost_estimate("architectural", "comprehensive")

        assert "opus" in cost_info.rationale.lower()
        assert "comprehensive" in cost_info.rationale.lower() or "deep" in cost_info.rationale.lower()

    def test_routing_matrix_coverage(self):
        """All mode/depth combinations are defined."""
        router = ModelRouter()

        modes = ["architectural", "code-quality", "decision", "technical-debt", "security"]
        depths = ["quick", "standard", "comprehensive"]

        for mode in modes:
            for depth in depths:
                model = router.get_model_for_review(mode, depth)
                assert model in [OPUS_ID, SONNET_ID]
```

### Integration Tests

**File**: `tests/integration/test_task_review_opus_integration.py`

```python
import pytest
from installer.global.lib.task_review.orchestrator import TaskReviewOrchestrator

class TestTaskReviewOpusIntegration:
    """Integration tests for Opus 4.5 in task reviews."""

    @pytest.fixture
    def orchestrator(self):
        return TaskReviewOrchestrator()

    def test_comprehensive_security_review_uses_opus(self, orchestrator):
        """Comprehensive security reviews use Opus 4.5."""
        result = orchestrator.execute_review(
            task_id="TASK-TEST-SEC-001",
            mode="security",
            depth="comprehensive"
        )

        assert result["model_used"] == "claude-opus-4.5-20250514"
        assert "opus" in result["report_path"]

    def test_standard_decision_review_uses_opus(self, orchestrator):
        """Standard decision reviews use Opus 4.5."""
        result = orchestrator.execute_review(
            task_id="TASK-TEST-DEC-001",
            mode="decision",
            depth="standard"
        )

        assert result["model_used"] == "claude-opus-4.5-20250514"

    def test_quick_code_quality_uses_sonnet(self, orchestrator):
        """Quick code quality reviews use Sonnet 4.5."""
        result = orchestrator.execute_review(
            task_id="TASK-TEST-QUAL-001",
            mode="code-quality",
            depth="quick"
        )

        assert result["model_used"] == "claude-sonnet-4.5-20250929"

    def test_cost_info_displayed(self, orchestrator, capsys):
        """Cost information is displayed before review."""
        orchestrator.execute_review(
            task_id="TASK-TEST-COST-001",
            mode="security",
            depth="standard"
        )

        captured = capsys.readouterr()
        assert "Review Cost Estimate" in captured.out
        assert "opus" in captured.out.lower()
        assert "$" in captured.out

    @pytest.mark.skipif(not opus_available(), reason="Opus API not available")
    def test_graceful_degradation_on_opus_failure(self, orchestrator, mock_opus_failure):
        """System falls back to Sonnet if Opus fails."""
        with mock_opus_failure():
            result = orchestrator.execute_review(
                task_id="TASK-TEST-FALLBACK-001",
                mode="decision",
                depth="comprehensive"
            )

            # Should have fallen back to Sonnet
            assert result["model_used"] == "claude-sonnet-4.5-20250929"
            assert "degraded" in result.get("warnings", [])
```

## Risk Assessment and Mitigation

### High Risk: API Compatibility Issues

**Risk**: Opus 4.5 API might differ from Sonnet 4.5
**Probability**: Low (both use same Claude API)
**Impact**: High (review failures)
**Mitigation**:
- Graceful degradation: Opus failure → automatic Sonnet fallback
- Clear error messages logged
- Unit tests with mock API responses

### Medium Risk: Cost Overruns

**Risk**: Users accidentally using Opus when not needed
**Probability**: Low (routing is automatic and documented)
**Impact**: Medium (increased costs)
**Mitigation**:
- Pre-review cost display (user awareness)
- Routing matrix prevents casual Opus use (only 20% of scenarios)
- Logging for cost tracking and analysis

### Medium Risk: Model Unavailability

**Risk**: Opus might be rate-limited or unavailable
**Probability**: Medium (new model, possible limits)
**Impact**: Medium (review delays)
**Mitigation**:
- Automatic fallback to Sonnet with warning
- Track degradation events for monitoring
- Document fallback behavior in user guide

### Low Risk: Performance Degradation

**Risk**: Opus is slower than Sonnet
**Probability**: High (larger model = slower)
**Impact**: Low (comprehensive reviews already take 4-6h)
**Mitigation**:
- Opus only for scenarios where quality > speed
- Set user expectations in documentation
- Monitor review duration metrics

### Low Risk: Configuration Drift

**Risk**: Hardcoded routing matrix might need updates
**Probability**: Low (routing should be stable)
**Impact**: Low (requires code change)
**Mitigation**:
- Document routing rationale clearly
- Can externalize to config file in future if needed
- Comprehensive unit tests prevent accidental changes

## Rollback Strategy

### Immediate Rollback (<1 minute)

Force all routes to Sonnet by modifying `model_router.py`:

```python
# Emergency rollback - comment out routing matrix, use Sonnet everywhere
ROUTING_MATRIX = {
    depth: {mode: "claude-sonnet-4.5-20250929" for mode in ALL_MODES}
    for depth in ["quick", "standard", "comprehensive"]
}
```

### Partial Rollback (Specific Modes)

Disable Opus for specific modes while keeping others:

```python
# Disable Opus for decisions only
ROUTING_MATRIX["standard"]["decision"] = "claude-sonnet-4.5-20250929"
ROUTING_MATRIX["comprehensive"]["decision"] = "claude-sonnet-4.5-20250929"
```

### Feature Flag (Future Enhancement)

Add environment variable to disable Opus globally:

```python
USE_OPUS_FOR_REVIEWS = os.getenv("TASKWRIGHT_USE_OPUS", "true") == "true"

def get_model_for_review(self, mode, depth):
    if not USE_OPUS_FOR_REVIEWS:
        return "claude-sonnet-4.5-20250929"
    return self.ROUTING_MATRIX[depth][mode]
```

## Success Criteria

### Cost Impact
- [ ] Monthly cost increase ≤10% for typical team usage
- [ ] Opus usage ≤25% of total review invocations
- [ ] Cost transparency: users see estimate before every review

### Quality Impact
- [ ] Security reviews achieve ≥95% accuracy (vs ≥90% with Sonnet)
- [ ] Comprehensive architectural reviews catch 15-20% more issues
- [ ] Decision analysis provides 2-3 more actionable options

### User Experience
- [ ] Review quality noticeably improved for Opus scenarios
- [ ] No user complaints about unexpected costs
- [ ] Clear documentation explaining when Opus is used and why

### Technical Quality
- [ ] Zero regressions in existing review functionality
- [ ] Test coverage ≥90% for new model router code
- [ ] ≥80% overall test coverage maintained
- [ ] All integration tests passing

## Implementation Timeline

**Estimated Effort**: 8 hours

### Phase 1: Core Infrastructure (3 hours)
- Implement `ModelRouter` class
- Add model parameter to `AgentInvoker`
- Unit tests for routing logic
- **No behavior change** (all routes default to Sonnet initially)

### Phase 2: Gradual Rollout (2 hours)
- Enable Opus for security reviews only
- Integration testing
- Monitor costs and quality
- **Minimal risk** (security is high-value scenario)

### Phase 3: Full Deployment (2 hours)
- Enable full routing matrix
- Comprehensive testing
- Update documentation
- **Complete feature** (all modes routed optimally)

### Phase 4: Documentation & Monitoring (1 hour)
- User guide updates
- Cost tracking dashboard
- Monitoring alerts
- **Production ready**

## Documentation Updates

### User-Facing Documentation

**Update**: `installer/global/commands/task-review.md`

Add section after "Review Modes (Detailed)":

```markdown
## Model Selection Strategy

The `/task-review` command automatically selects the optimal Claude model based on review mode and depth, balancing cost efficiency with quality requirements.

### When Opus 4.5 Is Used

**Opus 4.5** provides superior reasoning for high-value scenarios:

1. **Security reviews** (all depths) - Security breaches cost $100K-$10M, model costs $1-5
2. **Decision analysis** (standard/comprehensive) - Complex trade-offs require deep reasoning
3. **Comprehensive architectural reviews** - Thorough SOLID/DRY/YAGNI analysis
4. **Comprehensive technical debt** - Nuanced effort vs impact prioritization

**Cost**: $0.45-$1.65 per review (67% premium vs Sonnet)

### When Sonnet 4.5 Is Used

**Sonnet 4.5** provides excellent quality for most scenarios:

1. **Quick reviews** (except security) - Speed matters
2. **Code quality reviews** (all depths) - Metrics are objective
3. **Standard architectural reviews** - Pattern-based analysis sufficient
4. **Standard technical debt** - Straightforward prioritization

**Cost**: $0.09-$0.68 per review

### Cost Transparency

Before each review, you'll see:
```
============================================================
📊 Review Cost Estimate
============================================================
Model: claude-opus-4.5-20250514
Estimated tokens: 150,000
Estimated cost: $1.13
Rationale: comprehensive depth requires deep analysis,
           security reviews always use Opus 4.5
============================================================
```

This ensures you always know which model will be used and why.
```

### Developer Documentation

**Create**: `docs/architecture/model-selection-strategy.md`

Document:
- Routing matrix rationale
- Cost/benefit analysis per scenario
- How to modify routing matrix
- Monitoring and cost tracking
- Rollback procedures

## Files Changed

### New Files (1)
- `installer/global/lib/task_review/model_router.py` (~250 lines)

### Modified Files (2)
- `installer/global/lib/task_review/orchestrator.py` (~50 lines changed)
- `installer/global/lib/core/agent_invoker.py` (~30 lines changed)

### Test Files (2)
- `tests/unit/lib/task_review/test_model_router.py` (new, ~150 lines)
- `tests/integration/test_task_review_opus_integration.py` (new, ~100 lines)

### Documentation Files (2)
- `installer/global/commands/task-review.md` (+30 lines)
- `docs/architecture/model-selection-strategy.md` (new, ~200 lines)

**Total**: 7 files (3 new, 2 modified, 2 documentation)

## Related Tasks

- **TASK-895A**: Model selection strategy review (COMPLETED - provided decision foundation)
- **TASK-EE41**: Original model optimization (COMPLETED - established Sonnet/Haiku strategy)
- **Haiku Agent Implementation**: Separate initiative for Phase 3 optimization

## Next Steps

1. Review this specification with team
2. Approve scope and approach
3. Begin Phase 1 implementation (core infrastructure)
4. Incremental rollout with security-first approach
5. Monitor costs and quality for 2 weeks
6. Iterate routing matrix based on feedback

---

**Created**: 2025-11-25
**Estimated Effort**: 8 hours
**Priority**: High (user-requested feature)
**Complexity**: 6/10 (medium-complex, well-designed with minimal scope)
**Scope**: MINIMAL - 3 new files, 2 modified files, zero agent changes
