# Review Report: TASK-REV-2266

## Executive Summary

Analysis of `guardkit init nats-asyncio-service` failures on the nats-infrastructure project. Four distinct issues identified: one **code bug** (YAML frontmatter parsing), one **timeout exceeded** (agent episode), one **upstream LLM quality issue** (duplicate_facts), and **degraded performance** (local LLM). The YAML parsing bug is the only issue requiring a code fix; the others are environmental.

## Review Details
- **Mode**: Architectural Review (root cause analysis)
- **Depth**: Standard
- **Task**: TASK-REV-2266
- **Log**: `docs/reviews/nats-infrastructure/init-project-1.md`

---

## Findings

### Finding 1: YAML Frontmatter Parsing — CODE BUG (CRITICAL)

**Severity**: CRITICAL — affects all templates with multi-path frontmatter
**Root Cause**: Invalid YAML syntax in rule frontmatter, not a parser bug

**Evidence**: 4 rule files use bare comma-separated quoted strings in frontmatter:

```yaml
# INVALID YAML — causes parse failure
paths: "**/app.py", "**/handlers/*.py", "**/config.py"
```

YAML interprets `paths: "**/app.py"` as a valid scalar, then the `, "**/handlers/*.py"` is unexpected. The `yaml.safe_load()` call at [template_sync.py:82](guardkit/knowledge/template_sync.py#L82) correctly raises `YAMLError`, caught at [line 89](guardkit/knowledge/template_sync.py#L89).

**Affected files** (all in `installer/core/templates/nats-asyncio-service/.claude/rules/patterns/`):

| File | Current `paths:` value |
|------|----------------------|
| `module-level-singleton-for-service-instances.md` | `"**/app.py", "**/handlers/*.py", "**/config.py"` |
| `explicit-unidirectional-dependency-flow-(handler-->-service).md` | `"**/handlers/*.py", "**/services/*.py", "**/app.py"` |
| `environment-variable-configuration-via-pydantic-settings.md` | `"**/config.py", "**/.env*", "**/docker-compose*.yml"` |
| `factory-function-pattern-for-test-data.md` | `"**/tests/conftest.py", "**/tests/*.py"` |

**Additional affected files** with same pattern (other templates may have it too):
- `marker-gated-integration-tests.md` — `"**/tests/test_integration*.py", "**/pyproject.toml", "**/docker-compose*.yml"`
- `in-memory-broker-testing-via-testnatsbroker.md` — `"**/tests/test_handler*.py", "**/tests/test_*.py"`
- `correlation-id-linking-for-request/response-tracing.md` — `"**/schemas/*.py", "**/schemas.py", "**/services/*.py"`
- `pub/sub-messaging.md` — `"**/handlers/*.py", "**/app.py"`
- `handler/service-separation.md` — `"**/handlers/*.py", "**/services/*.py"`

**Impact**: Rules sync to Graphiti without path metadata. Claude Code `.claude/rules/` path-gating also won't work correctly for these rules.

**Two valid YAML formats**:

```yaml
# Option A: Single quoted string, comma-separated (parsed by template_sync split logic)
paths: "**/app.py, **/handlers/*.py, **/config.py"

# Option B: YAML list
paths:
  - "**/app.py"
  - "**/handlers/*.py"
  - "**/config.py"
```

The existing code at [template_sync.py:528-534](guardkit/knowledge/template_sync.py#L528-L534) already handles both formats correctly. The bug is in the **data**, not the **parser**.

**Working examples** in the same template:
- `code-style.md`: `paths: "**/*.py, **/*.pyx"` — single string, works correctly
- `testing.md`: `paths: "**/*.test.*, **/tests/**, **/*_test.*, **/*Test.*, **/*Spec.*"` — single string, works correctly

---

### Finding 2: Agent Episode Timeout — ENVIRONMENTAL (HIGH)

**Severity**: HIGH — but expected given local LLM constraints
**Root Cause**: Local MacBook Pro LLM too slow for `faststream-nats-broker-specialist` agent

**Evidence**:
- Agent `faststream-nats-broker-specialist` timed out after 240s
- Other agent episodes completed in 130-192s range (near the 240s ceiling)
- The 240s timeout was calibrated for GB10 vLLM (Qwen2.5-14B), not local LLM

**Timeout configuration** at [graphiti_client.py:1161](guardkit/knowledge/graphiti_client.py#L1161):
```python
elif group_id == "agents":
    episode_timeout = 240.0  # 9/18 agents timeout at 150s; raised from 150s (TASK-FIX-303e)
```

The timeout IS configurable via `--timeout` CLI override ([graphiti_client.py:1172-1174](guardkit/knowledge/graphiti_client.py#L1172-L1174)).

**Assessment**: The 240s timeout is appropriate for GB10. For local LLM scenarios, the `--timeout` override exists but isn't discoverable. The `faststream-nats-broker-specialist` is likely the largest agent (most content), which explains why it alone timed out while others completed in 130-192s.

---

### Finding 3: LLM Invalid Duplicate Facts — UPSTREAM/ENVIRONMENTAL (MEDIUM)

**Severity**: MEDIUM — data quality degradation, not data loss
**Root Cause**: Local LLM quality issue, not a code bug

**Evidence**:
- Warning: `LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)`
- 4 occurrences during edge operations
- Source: `graphiti_core.utils.maintenance.edge_operations` (upstream library)
- Appeared during the seeding phase when local LLM was performing entity extraction

**Assessment**: This is a well-known graphiti-core issue where the LLM returns out-of-range indices when identifying duplicate facts. The local MacBook Pro LLM (likely a smaller model) produces lower-quality structured outputs than GB10's Qwen2.5-14B. The `duplicate_facts` warnings appear in many previous init logs across the project history (57 files reference this pattern). Graphiti-core handles this gracefully — edges are created but deduplication may be incomplete, leading to some redundant edges in the graph.

**Not a code bug**: This is upstream `graphiti_core.utils.maintenance.edge_operations` behavior. GuardKit cannot fix this without patching graphiti-core.

---

### Finding 4: Episode Processing Times — ENVIRONMENTAL (LOW)

**Severity**: LOW — expected degradation on local LLM
**Root Cause**: Local LLM vs GB10 vLLM performance difference

**Evidence**:

| Episode Type | Time Range | Notes |
|-------------|-----------|-------|
| Project knowledge | 69s | Single episode, reasonable |
| Agent episodes | 130-192s | 7 succeeded, 1 timed out at 240s |
| Rule episodes | 93-172s | All succeeded |

**Baseline comparison**: On GB10 vLLM, agent episodes typically complete in 60-120s (based on prior review history). Local LLM is roughly 2x slower.

**Assessment**: Total init time was dominated by Graphiti seeding (~25-30 minutes for 15+ episodes). This is expected for local LLM. No code fix needed — the system correctly completed the init despite degraded performance.

---

### Finding 5: Idempotent File Handling — WORKING CORRECTLY (INFORMATIONAL)

**Evidence**: Log shows 42 "Skipping... already exists" messages for agents, rules, and config files. Template application correctly detected existing files and skipped them.

**Assessment**: The idempotent file handling is fully robust for re-init scenarios.

---

## Categorisation Summary

| # | Issue | Severity | Root Cause | Fix Needed? |
|---|-------|----------|------------|-------------|
| 1 | YAML frontmatter parsing | CRITICAL | Invalid YAML in 9+ rule files | **YES — data fix** |
| 2 | Agent episode timeout | HIGH | Local LLM too slow (240s limit) | No (environmental) |
| 3 | Duplicate facts warnings | MEDIUM | Local LLM quality / upstream graphiti-core | No (upstream) |
| 4 | Slow episode processing | LOW | Local LLM performance | No (environmental) |
| 5 | Idempotent file handling | INFO | Working correctly | No |

## Recommendations

### Priority 1: Fix YAML frontmatter in rule files (CODE FIX)

Fix all 9+ affected rule files to use valid YAML format. Convert from:
```yaml
paths: "**/app.py", "**/handlers/*.py"
```
To:
```yaml
paths: "**/app.py, **/handlers/*.py"
```

**Scope**: All nats-asyncio-service template rules with multi-path frontmatter. Also audit other templates for the same pattern.

**Effort**: Low (~30 min)
**Impact**: High — fixes path-gating for Claude Code AND Graphiti metadata

### Priority 2: Add template validation for paths format (DEFENSIVE)

Add a validation check in the template validation pipeline (`installer/core/lib/template_validation/`) that detects invalid YAML in rule frontmatter before deployment. This prevents the same class of bug from recurring.

**Effort**: Medium (~2 hours)
**Impact**: Medium — prevents future regressions

### Priority 3: Document local LLM timeout guidance (DOCS)

Add a note to the `guardkit init` output or docs that when using a local LLM, users can pass `--timeout` to increase the episode creation timeout. Example: `guardkit init nats-asyncio-service --timeout 600`.

**Effort**: Low (~15 min)
**Impact**: Low — improves developer experience for local LLM users

### Priority 4: Consider adaptive timeout based on LLM backend (ENHANCEMENT)

The timeout tiers at [graphiti_client.py:1154-1171](guardkit/knowledge/graphiti_client.py#L1154-L1171) are calibrated for GB10 vLLM. Consider reading the configured LLM endpoint from `.guardkit/graphiti.yaml` and applying a multiplier for known-slower backends. This is low priority since `--timeout` override already exists.

**Effort**: High (~4 hours)
**Impact**: Low — nice-to-have for multi-backend scenarios

### Priority 5: Monitor graphiti-core duplicate_facts upstream (TRACK)

Track the `duplicate_facts` warning in graphiti-core releases. If it persists across LLM backends, consider filing an upstream issue. No code change needed in GuardKit.

**Effort**: None (monitoring only)
**Impact**: Low

---

## Acceptance Criteria Assessment

| Criterion | Status | Notes |
|-----------|--------|-------|
| Categorise each failure by severity and root cause | **DONE** | See Findings 1-5 |
| Determine which failures are LLM vs code bugs | **DONE** | Only Finding 1 is a code bug; rest are environmental |
| Identify the YAML frontmatter parsing bug | **DONE** | Invalid YAML in data, not parser bug |
| Assess 240s timeout appropriateness | **DONE** | Appropriate for GB10; `--timeout` override exists for local |
| Recommend fixes with priority ordering | **DONE** | 5 recommendations, priority ordered |
| Determine duplicate_facts root cause | **DONE** | Local LLM quality issue + upstream graphiti-core |
