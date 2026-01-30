---
id: TASK-SD-CA08
title: Add Stub Detection to Phase 4.5 Quality Gate
status: backlog
priority: high
created: 2026-01-30
complexity: 5
tags: [quality-gates, stub-detection, phase-4-5, prevention]
parent_review: TASK-GC-72AF
related_analysis: .claude/reviews/TASK-GC-72AF-stub-analysis.md
---

# TASK-SD-CA08: Add Stub Detection to Phase 4.5 Quality Gate

## Problem Statement

During TASK-GC-72AF (Graphiti Core Migration), `/task-work` produced a 431-line file that looked complete but contained non-functional stub implementations. The file had:
- ✅ Perfect class structure and documentation
- ✅ Correct method signatures and type hints
- ❌ Methods that returned `[]` or `None` without doing anything
- ❌ Comments like `# In production, this would call...`

All unit tests passed because they mocked at the wrong level. The stubs were indistinguishable from working code until integration testing.

**Root Cause Analysis**: See `.claude/reviews/TASK-GC-72AF-stub-analysis.md`

## Objective

Add automated stub detection to Phase 4.5 (Test Enforcement) to catch implementations that are structurally complete but functionally empty.

## Acceptance Criteria

- [ ] Phase 4.5 detects placeholder comments across languages:
  - Python: `# In production...`, `# TODO...`
  - TypeScript/JavaScript: `// In production...`, `// TODO...`, `/* TODO */`
  - Go: `// In production...`, `// TODO...`
  - Rust: `// In production...`, `// TODO...`, `/* TODO */`
  - C#: `// In production...`, `// TODO...`
- [ ] Phase 4.5 detects stub methods/functions across languages:
  - Python: `return []`, `return None`, `pass`, `raise NotImplementedError`
  - TypeScript/JavaScript: `return []`, `return null`, `return undefined`, `throw new Error("Not implemented")`
  - Go: `return nil`, `panic("not implemented")`
  - Rust: `todo!()`, `unimplemented!()`, `panic!("not implemented")`
  - C#: `throw new NotImplementedException()`, `return null`, `return default`
- [ ] Phase 4.5 detects missing expected imports/using statements for library migration tasks
- [ ] Stub detection warnings are logged with file:line references
- [ ] Stub detection can be configured (warn vs block)
- [ ] Language detection is automatic based on file extension
- [ ] Unit tests for stub detection patterns (all supported languages)
- [ ] Documentation updated for Phase 4.5 stub detection

## Technical Approach

### 1. Language-Agnostic Stub Detection

The stub detector must support multiple languages. Detection is based on file extension.

```python
# lib/stub_detector.py

import re
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class StubFinding:
    """A detected stub pattern."""
    file_path: Path
    line_number: int
    pattern_type: str
    description: str
    severity: str  # "warning" | "error"
    language: str

# Language-specific patterns
LANGUAGE_PATTERNS: Dict[str, Dict] = {
    "python": {
        "extensions": [".py"],
        "comment_patterns": [
            r'#.*[Ii]n production.*would',
            r'#\s*(TODO|FIXME).*implement',
        ],
        "stub_patterns": [
            r'return \[\]',
            r'return None',
            r'^\s*pass\s*$',
            r'raise NotImplementedError',
        ],
    },
    "typescript": {
        "extensions": [".ts", ".tsx", ".js", ".jsx"],
        "comment_patterns": [
            r'//.*[Ii]n production.*would',
            r'//\s*(TODO|FIXME).*implement',
            r'/\*.*[Ii]n production.*would.*\*/',
        ],
        "stub_patterns": [
            r'return \[\]',
            r'return null',
            r'return undefined',
            r'throw new Error\(["\']Not implemented',
        ],
    },
    "go": {
        "extensions": [".go"],
        "comment_patterns": [
            r'//.*[Ii]n production.*would',
            r'//\s*(TODO|FIXME).*implement',
        ],
        "stub_patterns": [
            r'return nil',
            r'panic\(["\']not implemented',
        ],
    },
    "rust": {
        "extensions": [".rs"],
        "comment_patterns": [
            r'//.*[Ii]n production.*would',
            r'//\s*(TODO|FIXME).*implement',
        ],
        "stub_patterns": [
            r'todo!\(\)',
            r'unimplemented!\(\)',
            r'panic!\(["\']not implemented',
        ],
    },
    "csharp": {
        "extensions": [".cs"],
        "comment_patterns": [
            r'//.*[Ii]n production.*would',
            r'//\s*(TODO|FIXME).*implement',
        ],
        "stub_patterns": [
            r'throw new NotImplementedException\(\)',
            r'return null',
            r'return default',
        ],
    },
}

def detect_language(file_path: Path) -> str:
    """Detect language from file extension."""
    ext = file_path.suffix.lower()
    for lang, config in LANGUAGE_PATTERNS.items():
        if ext in config["extensions"]:
            return lang
    return "unknown"

def detect_stubs(file_path: Path, content: str) -> List[StubFinding]:
    """Detect potential stub implementations in a file (language-agnostic)."""
    findings = []
    language = detect_language(file_path)

    if language == "unknown":
        return findings  # Skip unknown languages

    patterns = LANGUAGE_PATTERNS[language]
    lines = content.split('\n')

    for i, line in enumerate(lines, 1):
        # Check comment patterns (placeholder comments)
        for pattern in patterns["comment_patterns"]:
            if re.search(pattern, line, re.IGNORECASE):
                findings.append(StubFinding(
                    file_path=file_path,
                    line_number=i,
                    pattern_type="placeholder_comment",
                    description=f"Found placeholder comment in {language} code",
                    severity="error",
                    language=language
                ))
                break  # Only report once per line

        # Check stub patterns (empty implementations)
        for pattern in patterns["stub_patterns"]:
            if re.search(pattern, line):
                findings.append(StubFinding(
                    file_path=file_path,
                    line_number=i,
                    pattern_type="stub_implementation",
                    description=f"Found stub implementation pattern: {pattern}",
                    severity="warning",
                    language=language
                ))
                break  # Only report once per line

    return findings
```

### 2. Library Import Verification (Language-Agnostic)

```python
def verify_library_usage(
    file_path: Path,
    content: str,
    required_imports: List[str],
    required_calls: List[str]
) -> List[StubFinding]:
    """Verify a file uses expected library imports and calls.

    Works across languages - just checks if the string is present.
    Examples:
      Python: "from graphiti_core import Graphiti"
      TypeScript: "import { Client } from '@neo4j/graphql'"
      Go: "import \"github.com/neo4j/neo4j-go-driver\""
      C#: "using Neo4j.Driver;"
    """
    language = detect_language(file_path)
    findings = []

    for imp in required_imports:
        if imp not in content:
            findings.append(StubFinding(
                file_path=file_path,
                line_number=1,
                pattern_type="missing_import",
                description=f"Expected import '{imp}' not found",
                severity="error",
                language=language
            ))

    for call in required_calls:
        if call not in content:
            findings.append(StubFinding(
                file_path=file_path,
                line_number=1,
                pattern_type="missing_call",
                description=f"Expected library call '{call}' not found",
                severity="warning",
                language=language
            ))

    return findings
```

### 3. Integration with Phase 4.5

Add to `task-work.md` Phase 4.5:

```markdown
### Step 4.5C: Stub Detection (Language-Agnostic)

**CHECK** for stub implementations in modified files:

1. Detect language from file extension (.py, .ts, .go, .rs, .cs, etc.)
2. Scan for placeholder comments:
   - Python: `# In production...`, `# TODO implement`
   - TypeScript/JS: `// In production...`, `// TODO implement`
   - Go: `// In production...`, `// TODO implement`
   - Rust: `// In production...`, `// TODO implement`
   - C#: `// In production...`, `// TODO implement`
3. Scan for stub implementations:
   - Python: `return []`, `return None`, `pass`, `raise NotImplementedError`
   - TypeScript/JS: `return []`, `return null`, `throw new Error("Not implemented")`
   - Go: `return nil`, `panic("not implemented")`
   - Rust: `todo!()`, `unimplemented!()`
   - C#: `throw new NotImplementedException()`
4. If task specifies required_imports, verify they exist
5. If task specifies required_calls, verify library is used

**IF** stub findings with severity="error" exist:
  - Display findings with file:line references
  - Block task until stubs are replaced with implementations

**IF** stub findings with severity="warning" exist:
  - Display warnings
  - Continue (unless --strict-stubs flag)
```

### 4. Task Frontmatter Extensions

For library migration tasks:

```yaml
---
id: TASK-XXX
title: Migrate to graphiti-core
stub_detection:
  required_imports:
    - "from graphiti_core import Graphiti"
  required_calls:
    - "graphiti.search"
    - "graphiti.add_episode"
  strict: true  # Block on any stub finding
---
```

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `installer/core/lib/stub_detector.py` | Create | Stub detection logic |
| `installer/core/lib/stub_detector_test.py` | Create | Unit tests |
| `installer/core/commands/task-work.md` | Modify | Add Phase 4.5C |
| `docs/guides/stub-detection.md` | Create | Documentation |

## Out of Scope

- IDE integration (future task)
- Pre-commit hook integration (future task)
- ML-based stub detection (over-engineering)

## Dependencies

- None

## Supported Languages

| Language | Extensions | Comment Style | Stub Patterns |
|----------|------------|---------------|---------------|
| Python | `.py` | `#` | `return []`, `return None`, `pass`, `raise NotImplementedError` |
| TypeScript/JS | `.ts`, `.tsx`, `.js`, `.jsx` | `//`, `/* */` | `return []`, `return null`, `throw new Error(...)` |
| Go | `.go` | `//` | `return nil`, `panic(...)` |
| Rust | `.rs` | `//`, `/* */` | `todo!()`, `unimplemented!()`, `panic!(...)` |
| C# | `.cs` | `//` | `throw new NotImplementedException()`, `return null`, `return default` |

Additional languages can be added by extending `LANGUAGE_PATTERNS` dictionary.

## Estimated Complexity

- Files: 3-4
- Pattern Familiarity: High (regex, language detection)
- Risk: Low (additive, doesn't change existing behavior)
- Dependencies: None
- Languages: 5 supported initially, extensible

**Complexity Score**: 5/10

## Notes

This task addresses a prevention mechanism. The root cause (lack of library knowledge in task context) is addressed by TASK-REV-668B.
