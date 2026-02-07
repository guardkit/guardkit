# Visual Architecture: Episode Serialization (TASK-GBF-001)

## Current State: Dual Paths (Problematic)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CALLING CODE                                │
│  (seed_*.py, *_manager.py, operations)                              │
└──────────────────────┬──────────────────────────────────────────────┘

                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼

    Path 1:        Path 2:         Path 3:
    Entity-Level   Client-Level    Manual-Level

┌──────────────┐ ┌──────────────────┐ ┌──────────────────┐
│Entity.       │ │GraphitiClient.   │ │seed_helpers.     │
│to_episode_   │ │add_episode()     │ │_add_episodes()   │
│body()        │ │   └─ inject_     │ │                  │
│              │ │     metadata()   │ │ Manually creates │
│ Returns dict │ │                  │ │ _metadata dict   │
│ with:        │ │ Injects:         │ │ then calls add_  │
│ - entity_    │ │ - source         │ │ episode()        │
│   type       │ │ - version        │ │                  │
│ - created_at │ │ - timestamps     │ │ Double injection!│
│ - updated_at │ │ - source_hash    │ │                  │
│              │ │ - entity_id      │ │ Result: Two      │
│ PROBLEM:     │ │                  │ │ metadata blocks  │
│ Inconsistent │ │ STRENGTH:        │ │ (dict + markdown)│
│ fields!      │ │ Single point     │ │                  │
└──────────────┘ └──────────────────┘ └──────────────────┘

        │              │              │
        └──────────────┼──────────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │  GRAPHITI KNOWLEDGE  │
            │      GRAPH           │
            │                      │
            │ Episodes with mixed  │
            │ metadata sources =   │
            │ Inconsistency risk!  │
            └──────────────────────┘
```

**Problems with Current Architecture:**
1. Entity level embeds metadata (mixed concerns)
2. Client level also injects metadata (redundancy)
3. Manual seeding injects TWICE (duplication)
4. Three paths = three places for bugs
5. Inconsistent metadata fields across entities
6. TaskOutcome returns `str` (breaks abstraction)

---

## Proposed State: Single Canonical Path

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CALLING CODE                                │
│  (seed_*.py, *_manager.py, operations)                              │
│                                                                     │
│  goal: Create clean domain data, pass to client                    │
└──────────────────────┬──────────────────────────────────────────────┘

                       │ Passes: body + metadata parameters
                       │
                       ▼
        ┌──────────────────────────────────────────┐
        │                                          │
        │     ENTITY LAYER (Domain Only)           │
        │                                          │
        │  entity.to_episode_body()                │
        │  ├─ Returns: dict (clean domain data)   │
        │  ├─ No metadata fields embedded         │
        │  ├─ Handles enum/datetime serialization │
        │  └─ Lightweight, single concern         │
        │                                          │
        │  Example return:                         │
        │  {                                       │
        │    "id": "TURN-001",                     │
        │    "feature_id": "FEAT-001",             │
        │    "turn_number": 1,                     │
        │    "player_summary": "...",              │
        │    "started_at": "2025-02-07T12:00:00Z" │
        │  }                                       │
        └──────────────┬──────────────────────────┘

                       │ Passes clean dict + parameters
                       │
                       ▼
        ┌──────────────────────────────────────────────────────┐
        │                                                      │
        │     CLIENT LAYER (Infrastructure)                    │
        │                                                      │
        │  GraphitiClient.add_episode(                         │
        │      name, body_json,                               │
        │      group_id, source, entity_type, entity_id       │
        │  )                                                   │
        │  ├─ Parses body_json to dict                        │
        │  ├─ Creates EpisodeMetadata                         │
        │  ├─ Injects metadata via _inject_metadata()         │
        │  ├─ Serializes to JSON                              │
        │  └─ Stores in Graphiti                              │
        │                                                      │
        │  Single Point of Injection:                         │
        │  ALWAYS through _inject_metadata()                  │
        │                                                      │
        │  Result dict structure:                             │
        │  {                                                  │
        │    "id": "TURN-001",                   // domain     │
        │    "feature_id": "FEAT-001",           // domain     │
        │    "turn_number": 1,                   // domain     │
        │    "player_summary": "...",            // domain     │
        │    "started_at": "2025-02-07T12:00:00Z",// domain   │
        │    "_metadata": {                      // injected   │
        │      "entity_id": "TURN-001",                       │
        │      "entity_type": "turn_state",                   │
        │      "source": "guardkit_seeding",                  │
        │      "version": "1.0.0",                            │
        │      "created_at": "2025-02-07T12:05:00Z",         │
        │      "updated_at": "2025-02-07T12:05:00Z",         │
        │      "source_hash": null                            │
        │    }                                                │
        │  }                                                  │
        └──────────────┬───────────────────────────────────────┘

                       │ Returns: Consistent, enriched episode
                       │
                       ▼
            ┌──────────────────────────┐
            │  GRAPHITI KNOWLEDGE      │
            │      GRAPH               │
            │                          │
            │ All episodes have:       │
            │ - Clean domain data      │
            │ - Consistent metadata    │
            │ - Single injection path  │
            │ - Zero duplication       │
            │                          │
            │ RESULT: Consistency!     │
            └──────────────────────────┘
```

**Benefits of Proposed Architecture:**
1. Single serialization path (client-level only)
2. Clean separation: domain logic vs infrastructure
3. Consistent metadata across all episodes
4. No double injection
5. Easy to add new entities
6. Type-safe: all methods return `dict`

---

## Entity Serialization Comparison

### Before: Inconsistent

```
┌────────────────────────────────────────────────────────────────┐
│                  CURRENT ENTITY RETURNS                        │
│                  (INCONSISTENT)                                │
├────────────────────────────────────────────────────────────────┤

TaskOutcome.to_episode_body()
├─ Type: str (string)                    ← ❌ DIFFERENT TYPE
├─ Content: Human-readable text
└─ Metadata: NONE (provided by client)

TurnStateEntity.to_episode_body()
├─ Type: dict                            ← ✓ Type OK
├─ Content: Domain + metadata fields
├─ Has: entity_type (metadata)           ← ❌ Embedded metadata
└─ Missing: created_at, updated_at       ← ❌ Inconsistent fields

FailedApproachEpisode.to_episode_body()
├─ Type: dict                            ← ✓ Type OK
├─ Content: Domain + metadata fields
├─ Has: entity_type (metadata)           ← ❌ Embedded metadata
└─ Missing: other metadata fields        ← ❌ Inconsistent fields

FeatureOverviewEntity.to_episode_body()
├─ Type: dict                            ← ✓ Type OK
├─ Content: Domain + metadata fields
├─ Has: entity_type, created_at, updated_at ← ❌ Different set
└─ Different from others                 ← ❌ Inconsistent fields

QualityGateConfigFact.to_episode_body()
├─ Type: dict                            ← ✓ Type OK
├─ Content: Domain + metadata fields
├─ Has: entity_type, version, effective_from ← ❌ Different set
└─ Different from others                 ← ❌ Inconsistent fields

RoleConstraintFact.to_episode_body()
├─ Type: dict                            ← ✓ Type OK
├─ Content: Domain + metadata fields
├─ Has: entity_type, created_at          ← ❌ Different set
└─ Different from others                 ← ❌ Inconsistent fields
```

**Issue Matrix:**
```
Entity                    | Return Type | Has entity_type? | Has created_at? | Has updated_at?
--------------------------|-------------|------------------|-----------------|----------------
TaskOutcome               | str ❌      | N/A              | N/A             | N/A
TurnStateEntity          | dict ✓      | Yes ❌           | No              | No
FailedApproachEpisode    | dict ✓      | Yes ❌           | No              | No
FeatureOverviewEntity    | dict ✓      | Yes ❌           | Yes ❌          | Yes ❌
QualityGateConfigFact    | dict ✓      | Yes ❌           | No              | No
RoleConstraintFact       | dict ✓      | Yes ❌           | Yes ❌          | No
```

---

### After: Unified

```
┌────────────────────────────────────────────────────────────────┐
│                  PROPOSED ENTITY RETURNS                       │
│                  (UNIFIED)                                     │
├────────────────────────────────────────────────────────────────┤

ALL entities follow same pattern:

Entity.to_episode_body()
├─ Type: dict                            ← ✓ Consistent
├─ Content: Domain fields ONLY
├─ No metadata fields                    ← ✓ Clean separation
└─ Metadata injected by client          ← ✓ Single path

Examples:

TaskOutcome.to_episode_body()
├─ Type: dict                            ← ✓ SAME TYPE
├─ Content: {
│     "id": "OUT-001",
│     "outcome_type": "TASK_COMPLETED",
│     "task_id": "TASK-001",
│     "success": true,
│     "summary": "...",
│     ...
│   }
└─ No metadata fields                    ← ✓ Clean

TurnStateEntity.to_episode_body()
├─ Type: dict                            ← ✓ SAME TYPE
├─ Content: {
│     "id": "TURN-001",
│     "feature_id": "FEAT-001",
│     "turn_number": 1,
│     "player_summary": "...",
│     ...
│   }
└─ No metadata fields                    ← ✓ Clean

FailedApproachEpisode.to_episode_body()
├─ Type: dict                            ← ✓ SAME TYPE
├─ Content: {
│     "id": "FAIL-001",
│     "approach": "...",
│     "symptom": "...",
│     ...
│   }
└─ No metadata fields                    ← ✓ Clean

FeatureOverviewEntity.to_episode_body()
├─ Type: dict                            ← ✓ SAME TYPE
├─ Content: {
│     "id": "FEAT-001",
│     "name": "...",
│     "tagline": "...",
│     ...
│   }
└─ No metadata fields                    ← ✓ Clean

QualityGateConfigFact.to_episode_body()
├─ Type: dict                            ← ✓ SAME TYPE
├─ Content: {
│     "id": "QG-001",
│     "name": "...",
│     "task_type": "...",
│     ...
│   }
└─ No metadata fields                    ← ✓ Clean

RoleConstraintFact.to_episode_body()
├─ Type: dict                            ← ✓ SAME TYPE
├─ Content: {
│     "role": "player",
│     "context": "...",
│     "primary_responsibility": "...",
│     ...
│   }
└─ No metadata fields                    ← ✓ Clean
```

**Unified Matrix:**
```
Entity                    | Return Type | Metadata Fields | Status
--------------------------|-------------|-----------------|--------
TaskOutcome               | dict ✓      | None ✓          | CLEAN
TurnStateEntity          | dict ✓      | None ✓          | CLEAN
FailedApproachEpisode    | dict ✓      | None ✓          | CLEAN
FeatureOverviewEntity    | dict ✓      | None ✓          | CLEAN
QualityGateConfigFact    | dict ✓      | None ✓          | CLEAN
RoleConstraintFact       | dict ✓      | None ✓          | CLEAN
```

---

## Metadata Injection Flow

### Current Flow (Multiple Paths)

```
Seeding Path:
┌──────────────────┐
│ seed_helpers.py  │
│ _add_episodes()  │
└────────┬─────────┘
         │
         ├─ Manually creates: body["_metadata"] = {...}  ← Path 1
         │
         └─► client.add_episode(json.dumps(body))
                 │
                 ├─ Also calls _inject_metadata()  ← Path 2
                 │
                 └─► RESULT: Double injection!

Manager Path:
┌──────────────────┐
│ *_manager.py     │
│ add_episode()    │
└────────┬─────────┘
         │
         └─► client.add_episode(json.dumps(body))
                 │
                 └─ Calls _inject_metadata()  ← Path 2 only
                    │
                    └─► RESULT: Single injection
                        (correct by accident)
```

### Proposed Flow (Single Path)

```
ALL paths:
┌──────────────────┐
│ Calling Code     │
│ (any layer)      │
└────────┬─────────┘
         │
         │ Calls with clean body + metadata parameters
         │
         ▼
┌──────────────────────────┐
│ client.add_episode()     │
│ (SINGLE ENTRY POINT)     │
└────────┬────────────────┘
         │
         ├─ Validates: body has no metadata
         │
         ├─ Creates: EpisodeMetadata from parameters
         │
         └─► _inject_metadata()  ← Single path
             │
             ├─ Merges domain data + metadata
             │
             └─► Store in Graphiti  ← Single output

RESULT:
- All metadata injected the same way
- No duplication
- No missed metadata
- Consistent format
```

---

## Seeding Helper Transformation

### Before: Manual Metadata Injection

```python
# seed_helpers.py BEFORE
async def _add_episodes(client, episodes, group_id, category_name):
    for name, body in episodes:
        # Step 1: Manually create metadata
        body_with_metadata = {
            **body,
            "_metadata": {  # ← MANUALLY CREATED
                "source": "guardkit_seeding",
                "version": SEEDING_VERSION,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "source_hash": None,
                "entity_id": name,
            }
        }

        # Step 2: Call client (which ALSO injects metadata)
        await client.add_episode(
            name=name,
            episode_body=json.dumps(body_with_metadata),
            group_id=group_id
            # ❌ Missing: source, entity_type, entity_id parameters!
        )

# Calling code BEFORE
episodes = [
    ("FAIL-SUBPROCESS", {"approach": "...", "symptom": "...", ...}),
    ("FAIL-TIMEOUT", {"approach": "...", "symptom": "...", ...}),
]
await _add_episodes(client, episodes, "failed_approaches", "Failed Approaches")
```

### After: Client-Level Injection

```python
# seed_helpers.py AFTER
async def _add_episodes(client, episodes, group_id, category_name):
    """Add episodes with client-level metadata injection.

    Episodes are 4-tuples: (name, body_dict, entity_type, entity_id)
    Client automatically handles metadata injection via _inject_metadata().
    """
    for name, body_dict, entity_type, entity_id in episodes:
        # Clean body, let client handle metadata
        await client.add_episode(
            name=name,
            episode_body=json.dumps(body_dict),  # ← CLEAN, no metadata
            group_id=group_id,
            source="guardkit_seeding",  # ← Pass to client
            entity_type=entity_type,    # ← Pass to client
            entity_id=entity_id         # ← Pass to client
        )

# Calling code AFTER
episodes = [
    (
        "FAIL-SUBPROCESS",
        {"approach": "...", "symptom": "...", ...},  # Clean body
        "failed_approach",                            # entity_type
        "FAIL-SUBPROCESS"                            # entity_id
    ),
    (
        "FAIL-TIMEOUT",
        {"approach": "...", "symptom": "...", ...},  # Clean body
        "failed_approach",                            # entity_type
        "FAIL-TIMEOUT"                               # entity_id
    ),
]
await _add_episodes(client, episodes, "failed_approaches", "Failed Approaches")
```

---

## Data Structure Changes

### Episode Structure in Graphiti

**Before: Mixed Metadata**
```json
{
  "id": "TURN-FEAT-GBF-1",
  "entity_type": "turn_state",              // From entity body
  "feature_id": "FEAT-GBF",
  "turn_number": 1,
  "player_summary": "...",
  "_metadata": {                            // From _inject_metadata()
    "source": "...",
    "version": "...",
    "created_at": "...",                    // Two created_at values!
    "updated_at": "...",
    "source_hash": null,
    "entity_id": "TURN-FEAT-GBF-1"
  }
  // Problem: entity_type appears in both places
  // Potential: created_at could be different!
}
```

**After: Unified Metadata**
```json
{
  "id": "TURN-FEAT-GBF-1",
  "feature_id": "FEAT-GBF",
  "turn_number": 1,
  "player_summary": "...",
  "_metadata": {                            // Only source of metadata
    "entity_id": "TURN-FEAT-GBF-1",
    "entity_type": "turn_state",
    "source": "guardkit_seeding",
    "version": "1.0.0",
    "created_at": "2025-02-07T12:00:00Z",
    "updated_at": "2025-02-07T12:00:00Z",
    "source_hash": null
  }
  // Clean: metadata in one place only
  // Consistent: same structure for all episodes
}
```

---

## Summary Table: Current vs Proposed

| Aspect | Current ❌ | Proposed ✓ |
|--------|-----------|-----------|
| **Number of paths** | 3 (entity, client, manual) | 1 (client only) |
| **Entity return type** | Mixed (str and dict) | Unified (dict) |
| **Metadata location** | Scattered (multiple places) | Centralized (_inject_metadata) |
| **Double injection** | Yes (seeding) | No |
| **Type safety** | Weak (str vs dict) | Strong (all dict) |
| **Maintainability** | Hard (3 paths) | Easy (1 path) |
| **Adding new entity** | Complex (pick a path) | Simple (just implement to_episode_body) |
| **Testing** | Fragile (3 paths) | Robust (1 path) |
| **Metadata consistency** | No | Yes |

---

## Migration Example: Outcome Entity

### Current Implementation (Problematic)

```python
class TaskOutcome:
    def to_episode_body(self) -> str:  # ← Wrong return type!
        """Return human-readable outcome text."""
        lines = []
        lines.append(f"Outcome ID: {self.id}")
        lines.append(f"Outcome Type: {self.outcome_type.value}")
        lines.append(f"Task ID: {self.task_id}")
        # ... 20+ more lines of text formatting
        lines.append(f"Summary:")
        lines.append(self.summary)
        # ... etc
        return "\n".join(lines)  # ← Returns string, not dict!

# Usage (must handle str return):
outcome = TaskOutcome(...)
body_str = outcome.to_episode_body()  # str
body_dict = json.loads(body_str)  # WRONG! Not valid JSON
# OR
# Just pass the string directly (but what is it?)
```

### Proposed Implementation (Clean)

```python
class TaskOutcome:
    def to_episode_body(self) -> dict:  # ← Correct return type
        """Return structured outcome data."""
        return {
            "id": self.id,
            "outcome_type": self.outcome_type.value,
            "task_id": self.task_id,
            "task_title": self.task_title,
            "task_requirements": self.task_requirements,
            "success": self.success,
            "summary": self.summary,
            "approach_used": self.approach_used,
            "patterns_used": self.patterns_used,
            "problems_encountered": self.problems_encountered,
            "lessons_learned": self.lessons_learned,
            "tests_written": self.tests_written,
            "test_coverage": self.test_coverage,
            "review_cycles": self.review_cycles,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_minutes": self.duration_minutes,
            "feature_id": self.feature_id,
            "related_adr_ids": self.related_adr_ids,
        }

# Usage (predictable dict return):
outcome = TaskOutcome(...)
body_dict = outcome.to_episode_body()  # dict
await client.add_episode(
    name=outcome.id,
    episode_body=json.dumps(body_dict),  # Clean JSON
    group_id="outcomes",
    source="feature_build_orchestrator",
    entity_type="task_outcome",
    entity_id=outcome.id
)
```

---

**This visual architecture makes the design clear and unambiguous for the implementation team.**
