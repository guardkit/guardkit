# Template Notes — Prompt-Schema Contract Pattern

Lessons learned from specialist-agent testing sessions (14-15 April 2026).
These patterns prevent Category B bugs (prompt-schema alignment mismatches).

## The Prompt-Schema Contract

Every Pydantic model (or dataclass) that validates Player output has a
corresponding prompt section that shows the model what to produce. These
form a **contract**: the prompt tells the LLM what shape to emit, and the
schema validates that the emitted shape is correct.

Breaking one side of the contract without updating the other causes
silent failures that are hard to diagnose.

### Rules

1. **Enum/Literal values in the schema MUST match the values shown in
   prompt examples.** If the schema says `Literal["accept", "reject"]`,
   the prompt must show `"accept"` and `"reject"` — not `"accepted"` or
   `"ACCEPT"`. Mismatches cause Pydantic validation failures that look
   like model quality issues but are actually template bugs.

2. **When adding a new output type**: write the Pydantic model first,
   then derive the prompt examples from the model's field names and
   types. Never write the prompt first and hope the model matches.

3. **When changing enum values**: update BOTH the schema AND all prompts
   that reference it. Search for the old value across all prompt files
   before considering the change complete.

4. **When adding a new field to a schema**: add a corresponding example
   in the prompt's JSON example block. Models are more likely to emit
   fields they've seen in examples.

5. **When removing a field from a schema**: remove it from prompt
   examples too, or the model will emit it and waste tokens on content
   that gets discarded.

### Contract Locations in This Template

| Schema | Prompt | Contract |
|--------|--------|----------|
| `WeightedVerdict` (pipeline.py.j2) | `_build_critical_response_format()` (coach_template.py) | Coach evaluation output |
| `PipelineResult` (pipeline.py.j2) | Internal — not shown to LLMs | Orchestrator result tracking |
| `GoalSchema` (goal_schema.py.j2) | `goal.md.j2` (templates/) | Domain configuration |
| `CriterionScore` (pipeline.py.j2) | `_build_criteria_section()` (coach_template.py) | Per-criterion scoring |

### Field Name Alignment Checklist

When the Coach prompt says:

```json
{
  "accepted": true,
  "scores": { ... },
  "weighted_score": 0.82
}
```

Then `WeightedVerdict.from_json()` must parse:
- `data["accepted"]` or `data["decision"]` (not both without fallback)
- `data["scores"]` or `data["criteria"]` (must match prompt key)
- `data["weighted_score"]` or `data["composite_score"]` (must match)

**Current state**: The Coach prompt uses `accepted`/`scores`/`weighted_score`
in examples, while `WeightedVerdict.from_json()` reads `decision`/`criteria`/
computes composite from criterion weights. This asymmetry works because the
prompt's CRITICAL section is positioned last (recency bias) and the parser
handles both forms — but new contributors should be aware of the mapping.

## Automated Validation (Optional)

For additional safety, consider adding a pre-commit hook or CI step that:

1. Parses Player/Coach prompt files for JSON example blocks
2. Extracts field names and enum values from the examples
3. Validates them against the corresponding Pydantic model definitions
4. Fails if any field name or enum value is present in one but not the other

This eliminates the entire class of Category B bugs at CI time rather than
discovering them during long-running agent sessions.

### Example CI Check (pseudocode)

```python
# ci/check_prompt_schema_alignment.py
import ast
import json
import re

def extract_json_examples(prompt_file: str) -> list[dict]:
    """Extract JSON blocks from prompt template."""
    content = open(prompt_file).read()
    blocks = re.findall(r'```json\n(.*?)\n```', content, re.DOTALL)
    return [json.loads(b) for b in blocks]

def extract_model_fields(schema_file: str, class_name: str) -> set[str]:
    """Extract field names from a dataclass/Pydantic model."""
    tree = ast.parse(open(schema_file).read())
    # ... walk AST to find class_name and extract field annotations
    pass

def check_alignment(prompt_examples, model_fields):
    """Verify prompt example keys match model field names."""
    for example in prompt_examples:
        example_keys = set(example.keys())
        missing_in_prompt = model_fields - example_keys
        extra_in_prompt = example_keys - model_fields
        if missing_in_prompt or extra_in_prompt:
            raise ValueError(f"Misaligned: missing={missing_in_prompt}, extra={extra_in_prompt}")
```

## References

- specialist-agent testing sessions (14-15 April 2026) — Category B bugs
- `prompts/coach_template.py` — Coach prompt with CRITICAL response format
- `scaffold/pipeline.py.j2` — WeightedVerdict and CriterionScore schemas
- `prompts/adversarial_base.py` — Player prompt (keep focused on generation)
