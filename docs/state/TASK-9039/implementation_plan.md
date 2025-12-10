# Implementation Plan: TASK-9039

**Task**: Remove Q&A from /template-create, Use Smart Defaults
**Status**: in_progress
**Priority**: high
**Complexity**: 3.5/10 (Simple)
**Review Mode**: AUTO_PROCEED
**Created**: 2025-11-12T10:00:00Z

---

## Overview

Refactor `/template-create` to work non-interactively using smart defaults. Remove blocking Q&A session that hangs in CI/CD environments.

**Key Change**: No more interactive prompts by default - just smart detection.

---

## Complexity Evaluation

### Score Breakdown

| Factor | Score | Max | Details |
|--------|-------|-----|---------|
| File Complexity | 2.0 | 3.0 | 5 files (3 modified, 2 created) - manageable |
| Pattern Familiarity | 0.5 | 2.0 | Strategy pattern, priority resolution (familiar) |
| Risk Level | 1.0 | 3.0 | Backward compatible, detection needs validation |
| Dependencies | 0.0 | 2.0 | Stdlib only, no external deps |
| **TOTAL** | **3.5** | **10.0** | **SIMPLE** |

### Review Mode: AUTO_PROCEED

**Rationale:**
- Score 3.5/10 (Simple range: 1-3)
- No force-review triggers detected
- Standard refactoring with familiar patterns
- Good architectural review (72/100)
- Low-risk changes with backward compatibility

**Force Triggers Checked:**
- User flag (--review): ❌ NOT present
- Security keywords: ❌ NOT detected
- Breaking changes: ❌ NOT detected
- Schema changes: ❌ NOT detected
- Hotfix flag: ❌ NOT detected

---

## Architectural Review Results

**Overall Score**: 72/100 (Approved with recommendations)

**Breakdown:**
- SOLID: 35/50
- DRY: 19/25
- YAGNI: 18/25

**Critical Issues**: None

**Recommendations:**
1. ISP: Split interfaces (detection vs orchestration)
2. DIP: Inject dependencies (testability)
3. YAGNI: MVP approach (core detection first)

---

## Implementation Phases

### Phase 1: Smart Detection Module (2 hours)

**Create**: `installer/core/lib/template_create/detector.py`

**Language Detection:**
```python
class LanguageDetector:
    """Detects project language from file patterns"""

    PATTERNS = {
        'python': ['requirements.txt', 'setup.py', 'pyproject.toml', '*.py'],
        'typescript': ['package.json', 'tsconfig.json', '*.ts'],
        'javascript': ['package.json', '*.js'],
        'csharp': ['*.csproj', '*.sln', '*.cs'],
        'go': ['go.mod', 'go.sum', '*.go'],
        'rust': ['Cargo.toml', '*.rs'],
    }

    def detect(self, project_path: Path) -> str:
        """Returns detected language or 'unknown'"""
        # Priority: config files > source files
        pass
```

**Framework Detection:**
```python
class FrameworkDetector:
    """Detects frameworks from dependencies"""

    FRAMEWORKS = {
        'react': ['package.json', 'dependencies.react'],
        'fastapi': ['requirements.txt', 'fastapi'],
        'nextjs': ['package.json', 'dependencies.next'],
        'aspnet': ['*.csproj', 'Microsoft.AspNetCore'],
    }

    def detect(self, project_path: Path, language: str) -> List[str]:
        """Returns list of detected frameworks"""
        pass
```

**Priority Resolution:**
```python
class ConfigResolver:
    """Resolves final config with priority: file > detection > defaults"""

    def resolve(self,
                config_file: Optional[Path],
                project_path: Path) -> Dict[str, Any]:
        """Returns merged configuration"""
        # 1. Load defaults
        # 2. Apply detection results
        # 3. Override with config file (if provided)
        pass
```

**Estimated LOC**: ~200 lines

---

### Phase 2: Refactor Orchestrator (2 hours)

**Modify**: `installer/core/lib/template_create/orchestrator.py`

**Changes:**

1. **Remove Q&A calls**:
```python
# OLD (blocking)
def execute(self):
    config = self.qa_agent.run_qa_session()  # REMOVE
    # ...

# NEW (non-interactive)
def execute(self):
    config = self._resolve_config()  # Use resolver
    # ...
```

2. **Add config resolution**:
```python
def _resolve_config(self) -> Dict[str, Any]:
    """Resolves config: file > detection > defaults"""
    resolver = ConfigResolver()
    return resolver.resolve(
        config_file=self.args.config,
        project_path=self.project_path
    )
```

3. **Add --config flag**:
```python
# In CLI argument parser
parser.add_argument(
    '--config',
    type=Path,
    help='Path to template config file (JSON/YAML)'
)
```

4. **Backward compatibility**:
```python
# Deprecation warning for --skip-qa
if self.args.skip_qa:
    logger.warning(
        "Warning: --skip-qa is deprecated (now default behavior). "
        "Use /template-qa for interactive configuration."
    )
```

**Estimated LOC**: ~150 lines (modifications)

---

### Phase 3: Modify Command Interface (1 hour)

**Modify**: `installer/core/commands/template-create.md`

**Changes:**

1. Update usage examples (remove Q&A references)
2. Document `--config` flag
3. Add smart detection explanation
4. Note `--skip-qa` deprecation

**Estimated LOC**: Documentation only

---

### Phase 4: Testing (2 hours)

**Create**: `tests/unit/test_template_create_detector.py`

**Test Coverage:**

1. **Language Detection Tests**:
   - Python project (requirements.txt)
   - TypeScript project (tsconfig.json)
   - C# project (*.csproj)
   - Multi-language project (priority resolution)
   - Unknown language (fallback)

2. **Framework Detection Tests**:
   - React (package.json)
   - FastAPI (requirements.txt)
   - Next.js (package.json)
   - Multiple frameworks

3. **Config Resolution Tests**:
   - Config file only
   - Detection only
   - Config overrides detection
   - Defaults fallback

4. **Integration Tests** (modify existing):
   - Non-interactive execution
   - Config file usage
   - Backward compatibility (--skip-qa)

**Estimated LOC**: ~400 lines (tests)

---

## File Inventory

### Files to Create (2)
1. `installer/core/lib/template_create/detector.py` (~200 LOC)
2. `tests/unit/test_template_create_detector.py` (~400 LOC)

### Files to Modify (3)
1. `installer/core/lib/template_create/orchestrator.py` (~150 LOC changes)
2. `installer/core/commands/template-create.md` (documentation)
3. `tests/integration/test_template_create.py` (~70 LOC additions)

**Total Estimated LOC**: ~820 lines (420 code + 400 tests)

---

## Dependencies

**External**: None (stdlib only)

**Internal**:
- Uses exclusions from TASK-9037
- References /template-qa command (TASK-9038)

---

## Risk Assessment

**Low-Medium Risk** (1.0/3.0)

**Mitigations:**

1. **Detection Accuracy**:
   - Comprehensive test suite
   - Priority-based resolution
   - Fallback to defaults
   - Clear error messages

2. **Backward Compatibility**:
   - `--skip-qa` still works (deprecated)
   - No breaking changes
   - Clear migration path

3. **CI/CD Compatibility**:
   - Non-interactive by default
   - Exit codes for automation
   - JSON output option

---

## Testing Strategy

### Unit Tests (80% coverage target)
- Language detection (all patterns)
- Framework detection (major frameworks)
- Config resolution (priority logic)
- Edge cases (empty projects, conflicts)

### Integration Tests (E2E scenarios)
- Run without config (smart defaults)
- Run with config file
- Run in CI/CD environment
- Backward compatibility (--skip-qa)

### Manual Testing
- Test on real projects (Python, TypeScript, C#)
- Verify detection accuracy
- Confirm non-interactive execution

---

## Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| Phase 1 | 2 hours | Smart detection module |
| Phase 2 | 2 hours | Refactor orchestrator |
| Phase 3 | 1 hour | Update command docs |
| Phase 4 | 2 hours | Comprehensive testing |
| **TOTAL** | **6-7 hours** | *Including testing* |

**Estimated Completion**: Same day (single session)

---

## Success Criteria

**Core Functionality:**
- ✅ No interactive prompts by default
- ✅ Smart detection of language/framework
- ✅ Config file support (`--config`)
- ✅ Works in CI/CD (non-interactive)
- ✅ Backward compatible (`--skip-qa` deprecated)

**Quality Gates:**
- ✅ All tests pass (100%)
- ✅ Coverage ≥80%
- ✅ No breaking changes
- ✅ Documentation updated

---

## Related Tasks

- **TASK-9037**: Build artifact exclusion (prerequisite) ✅
- **TASK-9038**: /template-qa command (prerequisite) ✅
- **TASK-9040**: Investigate regression (related)

---

## Notes

**Architecture Decision:**
- Strategy pattern for detection (extensible)
- Priority resolution (config > detect > default)
- Dependency injection (testability)

**MVP Approach:**
- Core languages first (Python, TypeScript, C#)
- Core frameworks (React, FastAPI, Next.js)
- Can extend detection later

**Backward Compatibility:**
- `--skip-qa` deprecated but functional
- Clear warning message guides users
- No breaking changes to existing workflows
