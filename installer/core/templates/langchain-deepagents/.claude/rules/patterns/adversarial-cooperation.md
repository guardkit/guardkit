# Adversarial Cooperation Pattern

Three-role architecture for quality-gated content generation: Orchestrator (plain Python loop), Player (content producer), Coach (evaluator). Only the Orchestrator may write output, and only after Coach acceptance.

Fixes prevented: TRF-003, TRF-005, TRF-006, TRF-016.

## Three-Role Architecture

| Role | Implementation | Tools | Responsibility |
|------|---------------|-------|---------------|
| Orchestrator | Plain Python loop (`agent.py`) | `write_output` (programmatic) | Coordinates Player/Coach loop, owns all writes |
| Player | DeepAgent via `create_agent()` | Domain tools only (e.g. `search_data`) | Generates content, revises on rejection |
| Coach | DeepAgent via `create_agent()` | NONE (empty `tools=[]`) | Evaluates Player output, returns structured verdict |

The Orchestrator is NOT a DeepAgent. It is module-level Python wiring in `agent.py` that:
1. Creates Player and Coach agents
2. Invokes Player to generate content
3. Passes output to Coach for evaluation
4. Writes output ONLY after Coach acceptance (via `OrchestratorWriteGate`)

## CoachVerdict Dataclass

Binary accept/reject verdict returned by the Coach as JSON:

```python
@dataclass
class CoachVerdict:
    """Structured verdict from the Coach agent."""
    decision: str   # "accept" or "reject"
    score: int      # 1-5
    issues: list[str] = field(default_factory=list)
    criteria_met: bool = False
    quality_assessment: str = "needs_revision"

    @property
    def accepted(self) -> bool:
        return self.decision == "accept"

    @classmethod
    def from_json(cls, raw: str) -> "CoachVerdict":
        data = json.loads(raw)
        if "decision" not in data or "score" not in data:
            raise ValueError("Coach response missing required fields")
        return cls(
            decision=data["decision"],
            score=data["score"],
            issues=data.get("issues", []),
            criteria_met=data.get("criteria_met", False),
            quality_assessment=data.get("quality_assessment", "needs_revision"),
        )
```

Scoring: accept at 4-5, reject at 1-3. Score 3 is borderline (escalate to human).

## OrchestratorWriteGate

The write gate enforces orchestrator-gated writes with retry exhaustion:

```python
class OrchestratorWriteGate:
    def __init__(self, write_fn, max_retries=3, on_rejection=None, on_exhaustion=None):
        self._write_fn = write_fn
        self._max_retries = max_retries

    def attempt_write(self, content, output_path, coach_verdict, attempt=1):
        """Write proceeds ONLY if Coach accepted. Returns WriteResult."""
        if attempt > self._max_retries:
            return WriteResult(success=False, target=output_path, ...)
        if not coach_verdict.accepted:
            return WriteResult(success=False, ...)
        # Coach accepted - Orchestrator performs the write
        result = self._write_fn(content, output_path)
        return WriteResult(success=True, target=output_path, attempts=attempt)
```

Source: `scaffold/orchestrator_pattern.py.template`

## Rejection-Revision Loop

When Coach rejects, the Orchestrator feeds issues back to the Player for revision:

```python
# Orchestration loop (in agent.py or calling code)
for attempt in range(1, max_retries + 1):
    player_output = await player.ainvoke(input_messages)
    verdict = CoachVerdict.from_json(await coach.ainvoke(player_output))

    if verdict.accepted:
        write_gate.attempt_write(player_output, target, verdict, attempt)
        break

    # Rejection: feed issues back to Player
    issues = verdict.issues
    input_messages = {
        "messages": [{
            "role": "user",  # NOT "system" — see ainvoke() contract
            "content": (
                "Coach feedback: " + "; ".join(issues) + "\n\n"
                + player_output
            ),
        }]
    }
```

## ainvoke() Message Contract (TASK-REV-R2A1)

`create_agent()` unconditionally prepends `system_prompt` on every `ainvoke()` call. Input messages must use only `user` or `assistant` roles. **Never pass `system` messages in ainvoke() input.**

Violation causes dual system messages, which vLLM rejects with HTTP 400 Bad Request.

```python
# CORRECT: use "user" role for retry reinforcement
retry_input = {"messages": [{"role": "user", "content": feedback}]}

# WRONG: causes dual system messages -> vLLM 400
retry_input = {"messages": [{"role": "system", "content": feedback}]}
```

Use `assert_no_system_messages()` from `factory_guards.py` at every `ainvoke()` call site.

## When to Use

- Content generation with quality evaluation (verifiable domains)
- Any workflow where output must meet measurable acceptance criteria
- Research-generate-evaluate-revise loops
- Data synthesis, schema conformance, structured content creation

## When NOT to Use

- Simple single-agent tasks with no evaluation step
- Subjective quality that needs weighted scoring (use `langchain-deepagents-weighted-evaluation` template)
- Tasks where the cost of retry loops outweighs the quality benefit
