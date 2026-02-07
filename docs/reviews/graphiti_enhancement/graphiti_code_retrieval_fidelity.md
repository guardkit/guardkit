# Graphiti Code Retrieval Fidelity Assessment

**Date**: 2026-02-05
**Related Tasks**: TASK-CR-006, TASK-CR-006-FIX, TASK-CR-007, TASK-CR-008
**Feature**: FEAT-CR01 (Context Reduction via Graphiti Migration)

## Executive Summary

Investigation of Graphiti's ability to store and retrieve Python code examples reveals a fundamental architectural mismatch: **Graphiti is a knowledge graph that extracts semantic facts, not a document store that preserves verbatim content**. This means code examples cannot be reliably retrieved in copy-paste usable form.

**Recommendation**: Cancel TASK-CR-007 and TASK-CR-008. Keep pattern files as-is (already path-gated for conditional loading).

## Background

The FEAT-CR01 context reduction initiative included a plan to:
1. Seed Python code examples from pattern files into Graphiti (TASK-CR-006)
2. Trim pattern markdown files by removing code examples (TASK-CR-007, TASK-CR-008)
3. Rely on Graphiti retrieval to provide code examples on-demand

This approach assumed Graphiti could store and retrieve code blocks with sufficient fidelity for developer use.

## Investigation Method

### Test Setup
1. Seeded `seed_pattern_examples.py` containing 17 pattern episodes with full Python code blocks
2. Each episode contained:
   - Pattern name (e.g., "Dataclass Pattern: JSON Serialization with asdict()")
   - Full code example with imports, class definitions, usage examples
   - "When to use" guidance

### Example Seeded Content
```python
episodes.append({
    "name": "Dataclass Pattern: JSON Serialization with asdict()",
    "body": """Serialize dataclasses to JSON using asdict():

```python
from dataclasses import dataclass, asdict
import json
from pathlib import Path

@dataclass
class OrchestrationState:
    agent_file: str
    template_dir: str
    timestamp: str

# Serialize to JSON
state = OrchestrationState(...)
json_str = json.dumps(asdict(state), indent=2)
```

**When to use:**
- Need to persist state to disk
- Checkpoint-resume workflows
"""
})
```

### Retrieval Tests

| Query | Expected | Actual Result |
|-------|----------|---------------|
| `"dataclass JSON serialization"` | Full code block with `@dataclass`, `asdict()` | "asdict() supports JSON serialization" (fact) |
| `"OrchestrationState"` | Class definition with fields | "OrchestrationState has a field named strategy" (fact) |
| `"@dataclass"` | Code with decorator | "EnhancementResult dataclass has computed properties" (fact) |
| `"pipeline step execution"` | Pipeline orchestration code | "ImplementOrchestrator parses subtasks from review" (fact) |

## Key Findings

### Finding 1: Graphiti Extracts Facts, Not Code

Graphiti processes episode content through its knowledge extraction pipeline:

```
Input: Full Python code block (50+ lines)
   ↓
Processing: Entity/relationship extraction via LLM
   ↓
Storage: Facts stored in Neo4j graph
   ↓
Output: "OrchestrationState has a field named strategy"
```

The actual code syntax is **not preserved**. Instead, Graphiti creates semantic facts about what the code does.

### Finding 2: Relevance Scores Are 0.00

All queries returned `[0.00]` relevance scores despite finding related facts:

```
Found 5 results for 'dataclass JSON serialization':

1. [0.00] asdict() supports JSON serialization.
2. [0.00] Dataclasses provide asdict() for JSON serialization.
3. [0.00] ImplementOrchestrationState supports JSON serialization...
```

This suggests either:
- A scoring/display issue in the CLI
- Facts are being found by text search, not semantic similarity

### Finding 3: Semantic Understanding IS Preserved

The extracted facts correctly capture what the code does:

| Code Element | Extracted Fact |
|--------------|----------------|
| `@dataclass class OrchestrationState` | "OrchestrationState uses dataclasses for minimal state objects" |
| `asdict(state)` | "Dataclasses provide asdict() for JSON serialization" |
| `@property def files(self)` | "EnhancementResult dataclass has a property called files" |
| `field(default_factory=list)` | "ProcessedFile uses field(default_factory) to create default values" |

This semantic extraction is **valuable for understanding** but **not for code retrieval**.

### Finding 4: Pattern Group Has High Episode Count

```
patterns: 100 episodes (search limit reached)
```

The seeding worked - 100+ facts were extracted from the 17 pattern episodes.

## Impact Assessment

### What Works
- ✅ Semantic queries about code concepts
- ✅ Understanding what patterns exist and their purpose
- ✅ Finding related patterns for a given problem
- ✅ Knowledge graph relationships between concepts

### What Doesn't Work
- ❌ Retrieving copy-paste usable code
- ❌ Getting exact Python syntax
- ❌ Preserving code formatting and indentation
- ❌ Replacing documentation with retrieval

## Options Analysis

### Option A: Cancel CR-007/CR-008, Keep Pattern Files
**Recommended**

- Pattern files remain as-is (already path-gated)
- Token savings: 0 (patterns load conditionally anyway)
- Risk: None
- Effort: Minimal (update task statuses)

### Option B: Explore Alternative Storage
Not recommended for this use case

- Could use Graphiti's raw episode storage
- Would bypass knowledge extraction
- Loses semantic search benefits
- Essentially building a document store inside a knowledge graph

### Option C: Hybrid Approach
Potentially valuable for future

- Keep code in static files (path-gated)
- Use Graphiti for semantic "which pattern?" queries
- Retrieve pattern file on-demand based on semantic match

## Recommendations

### Immediate Actions

1. **Cancel TASK-CR-007** - Trimming orchestrators.md
   - Status: `cancelled`
   - Reason: "Graphiti code retrieval fidelity insufficient - cannot preserve Python code blocks"

2. **Cancel TASK-CR-008** - Trimming dataclasses.md/pydantic-models.md
   - Status: `cancelled`
   - Reason: Same as above

3. **Complete TASK-CR-006-FIX** - Mark as completed with findings
   - The wiring works correctly
   - Seeding executes successfully
   - Fidelity finding is the key outcome

4. **Update TASK-CR-006** - Mark original task as superseded
   - Superseded by TASK-CR-006-FIX
   - Implementation exists but acceptance criteria cannot be met

### Documentation Updates

1. Add to Graphiti documentation:
   - "Graphiti extracts semantic facts, not verbatim content"
   - "Not suitable for code block retrieval"
   - "Best used for concept queries and relationship discovery"

2. Update FEAT-CR01 feature spec:
   - Remove pattern file trimming from scope
   - Document lessons learned

### Future Considerations

The `seed_pattern_examples.py` module IS valuable for:
- Answering "which pattern should I use for X?"
- Finding related patterns
- Understanding pattern relationships

Consider keeping it for semantic queries while keeping static files for code retrieval.

## Appendix: Test Commands

```bash
# Seed patterns
guardkit graphiti seed --force

# Verify seeding
guardkit graphiti status --verbose

# Test retrieval
guardkit graphiti search "dataclass JSON serialization" --group patterns
guardkit graphiti search "OrchestrationState" --group patterns
guardkit graphiti search "@dataclass" --group patterns

# Show pattern details
guardkit graphiti show "Dataclass Pattern"
```

## Appendix: Files Involved

| File | Purpose | Location |
|------|---------|----------|
| `seed_pattern_examples.py` | Seeding module | `guardkit/knowledge/seed_pattern_examples.py` |
| `seeding.py` | Main orchestrator | `guardkit/knowledge/seeding.py` |
| `dataclasses.md` | Pattern file (keep) | `.claude/rules/patterns/dataclasses.md` |
| `pydantic-models.md` | Pattern file (keep) | `.claude/rules/patterns/pydantic-models.md` |
| `orchestrators.md` | Pattern file (keep) | `.claude/rules/patterns/orchestrators.md` |
