# TASK-REV-SEC2: Claude Code Security Plugin Analysis Report

## Executive Summary

This analysis examines two Anthropic security resources to identify techniques applicable to the Coach agent security integration (TASK-SEC-001 through TASK-SEC-006):

1. **[security-guidance plugin](https://github.com/anthropics/claude-code/tree/main/plugins/security-guidance)** - Lightweight hook-based security reminders
2. **[claude-code-security-review](https://github.com/anthropics/claude-code-security-review)** - AI-powered security review GitHub Action

**Key Finding**: The Claude Code security approach is complementary to our planned implementation. The security-guidance plugin uses a simpler, warning-based approach, while the security-review tool uses AI-powered semantic analysis. Our planned hybrid approach (quick checks + full review) effectively combines the best of both.

## Source Analysis

### 1. Security-Guidance Plugin

**Repository**: `anthropics/claude-code/plugins/security-guidance`

#### Architecture

```
.claude-plugin/
└── plugin.json          # Plugin metadata
hooks/
├── hooks.json           # Hook configuration
└── security_reminder_hook.py  # Detection logic
```

#### How It Works

1. **Hook Trigger**: Activates on `PreToolUse` events for Edit, Write, MultiEdit tools
2. **Pattern Matching**: Uses substring matching (not regex) against 9 security patterns
3. **State Management**: Tracks shown warnings per session in `~/.claude/` JSON files
4. **Exit Behavior**: Returns exit code 2 to block execution if unshown warnings found

#### Security Patterns Detected

| Pattern | Detection Method | Description |
|---------|------------------|-------------|
| GitHub Actions injection | Path check + substring | Workflow file changes with shell commands |
| child_process.exec() | Substring | Node.js command execution |
| new Function() | Substring | Dynamic code generation |
| eval() | Substring | JavaScript eval |
| dangerouslySetInnerHTML | Substring | React XSS risk |
| document.write() | Substring | DOM XSS |
| innerHTML | Substring | DOM manipulation XSS |
| pickle | Substring (Python files) | Deserialization attacks |
| os.system() | Substring | Python command execution |

#### Key Design Decisions

1. **Warning-only approach**: Displays reminder, doesn't enforce blocking
2. **Once-per-session**: Each warning shown only once per file/rule combo
3. **Substring vs Regex**: Uses simpler substring matching
4. **Path-based filtering**: Some checks only apply to specific file types
5. **Environment toggle**: Can disable via `ENABLE_SECURITY_REMINDER=0`

### 2. Claude Code Security Review

**Repository**: `anthropics/claude-code-security-review`

#### Architecture

```
claudecode/
├── github_action_audit.py    # Main audit orchestrator
├── prompts.py                # Security audit prompts
├── findings_filter.py        # False positive filtering
├── claude_api_client.py      # Claude API integration
└── json_parser.py            # Response parsing
```

#### How It Works

1. **Diff Analysis**: Analyzes PR diffs for security vulnerabilities
2. **Semantic Understanding**: Uses Claude AI for context-aware detection
3. **Finding Generation**: Produces structured findings with severity/confidence
4. **False Positive Filtering**: Two-stage filtering (hard rules + AI)
5. **PR Comments**: Posts findings as line-specific review comments

#### Vulnerability Categories (10)

1. Injection Attacks (SQL, command, LDAP, XPath, NoSQL, XXE)
2. Authentication & Authorization (bypass, privilege escalation, IDOR)
3. Data Exposure (hardcoded secrets, PII, sensitive logging)
4. Cryptographic Issues (weak algorithms, key management)
5. Input Validation (missing validation, improper sanitization)
6. Business Logic Flaws (race conditions, TOCTOU)
7. Configuration Security (insecure defaults, CORS, headers)
8. Supply Chain (vulnerable dependencies, typosquatting)
9. Code Execution (deserialization, pickle, eval injection)
10. Cross-Site Scripting (reflected, stored, DOM-based)

#### False Positive Filtering

**Hard Exclusions** (always filtered):
- Denial of Service / resource exhaustion
- Rate limiting recommendations
- Memory leaks / resource management
- Open redirects
- Regex injection
- Memory safety in non-C/C++ code
- SSRF in HTML files
- Findings in markdown files

**Confidence Threshold**: >80% required for findings

## Comparison with Our Planned Approach

### Feature Comparison

| Feature | security-guidance | security-review | Our Hybrid (TASK-SEC-*) |
|---------|-------------------|-----------------|-------------------------|
| Detection Method | Substring | AI Semantic | Regex + AI |
| Blocking Behavior | Warning only | Optional | Configurable (critical blocks) |
| Performance | Instant (~1s) | Minutes | 30s quick + optional full |
| Severity Levels | Implied (all warnings) | HIGH/MEDIUM/LOW | critical/high/medium/low/info |
| Configuration | Env var toggle | GitHub inputs | YAML frontmatter |
| False Positive Handling | State tracking | Hard rules + AI | skip_checks config |
| Integration | PreToolUse hook | GitHub Action | Coach validator |

### What We Can Adopt

#### From security-guidance Plugin

1. **Substring matching for simple patterns** - Faster than regex for basic checks
2. **Path-based filtering** - Only check relevant file types
3. **Once-per-session state** - Avoid repeated warnings
4. **Environment toggle** - Allow disabling for CI/CD

#### From security-review Tool

1. **Hard exclusion rules** - Pre-filter low-value findings
2. **Confidence scoring** - Require >80% confidence
3. **Category taxonomy** - 10-category vulnerability classification
4. **Structured finding format** - JSON with severity, confidence, location
5. **False positive filtering** - DOS, rate limiting, resource management exclusions

## Recommendations by Task

### TASK-SEC-001: Quick Security Checks

**Adopt from Claude Code**:

1. **Expand pattern list** - Add these from security-guidance:
   ```python
   # JavaScript/TypeScript patterns
   {"id": "dangerous-inner-html", "pattern": "dangerouslySetInnerHTML", "severity": "high"},
   {"id": "document-write", "pattern": "document.write", "severity": "high"},
   {"id": "inner-html", "pattern": ".innerHTML", "severity": "medium"},
   {"id": "new-function", "pattern": "new Function(", "severity": "high"},

   # Additional Python patterns
   {"id": "pickle-load", "pattern": "pickle.load", "severity": "critical"},
   ```

2. **Add path-based filtering**:
   ```python
   PATH_SPECIFIC_CHECKS = {
       "pickle-load": ["*.py"],
       "dangerous-inner-html": ["*.tsx", "*.jsx"],
       "github-actions-injection": [".github/workflows/*.yml"]
   }
   ```

3. **Consider substring matching** for simple patterns (faster):
   ```python
   # For simple checks, substring is 10x faster than regex
   if "eval(" in content:
       # Found eval usage
   ```

### TASK-SEC-002: Security Config Schema

**Adopt from Claude Code**:

1. **Add hard exclusion categories** from security-review:
   ```yaml
   security:
     exclude_categories:
       - dos
       - rate-limiting
       - resource-management
       - open-redirect
   ```

2. **Add file type filtering**:
   ```yaml
   security:
     exclude_patterns:
       - "*.md"       # Markdown files
       - "*.test.*"   # Test files
       - "docs/**"    # Documentation
   ```

3. **Add toggle option** like `ENABLE_SECURITY_REMINDER`:
   ```yaml
   security:
     enabled: true  # Can be overridden by GUARDKIT_SECURITY_SKIP=1
   ```

### TASK-SEC-003: Security-Specialist Invocation

**Adopt from Claude Code**:

1. **Use security-review prompt structure**:
   ```python
   SECURITY_REVIEW_PROMPT = """
   Identify HIGH-CONFIDENCE security vulnerabilities with real exploitation potential.

   VULNERABILITY CATEGORIES:
   1. Injection Attacks: SQL, command, LDAP, XPath, NoSQL, XXE
   2. Authentication/Authorization: bypass, privilege escalation, IDOR
   3. Data Exposure: hardcoded secrets, PII, sensitive logging
   4. Cryptographic Issues: weak algorithms, key management
   5. Input Validation: missing validation, improper sanitization
   6. Business Logic: race conditions, TOCTOU
   7. Configuration: insecure defaults, CORS, headers
   8. Supply Chain: vulnerable dependencies
   9. Code Execution: deserialization, pickle, eval
   10. XSS: reflected, stored, DOM-based

   REQUIREMENTS:
   - Confidence must be >80%
   - Provide exploitation scenario for each finding
   - Exclude: DOS, rate limiting, resource exhaustion

   OUTPUT: JSON array with severity, confidence, location, description, remediation
   """
   ```

2. **Add confidence scoring** to SecurityFinding:
   ```python
   @dataclass
   class SecurityFinding:
       check_id: str
       severity: Literal["critical", "high", "medium", "low", "info"]
       confidence: float  # 0.0 - 1.0, filter below 0.8
       description: str
       file_path: str
       line_number: int
       exploitation_scenario: str  # NEW: How could this be exploited?
       recommendation: str
   ```

3. **Add post-filtering** like findings_filter.py:
   ```python
   def filter_findings(findings: List[SecurityFinding]) -> List[SecurityFinding]:
       """Apply hard exclusion rules to reduce false positives."""
       exclusions = [
           (r"denial of service|resource exhaustion", "DOS finding"),
           (r"rate limit", "Rate limiting recommendation"),
           (r"memory leak|connection leak", "Resource management"),
       ]
       return [f for f in findings if not matches_exclusion(f, exclusions)]
   ```

### TASK-SEC-004: Task Tagging Detection

**Adopt from Claude Code**:

1. **Align with security-review categories** for consistency:
   ```python
   SECURITY_TAGS = {
       # Map to security-review categories
       "authentication", "authorization",  # Auth category
       "injection", "sql", "command",      # Injection category
       "crypto", "encryption",             # Crypto category
       "validation", "input",              # Input validation
       "xss", "sanitization",              # XSS category
       "secrets", "credentials",           # Data exposure
   }
   ```

2. **Add category-based full review triggers**:
   ```python
   # High-risk categories always trigger full review
   HIGH_RISK_CATEGORIES = {"authentication", "authorization", "injection", "crypto"}

   def should_run_full_review(task: dict, config: SecurityConfig) -> bool:
       task_tags = set(task.get("tags", []))
       if task_tags & HIGH_RISK_CATEGORIES:
           return True
       # ... rest of logic
   ```

### TASK-SEC-005: Security Validation Tests

**Adopt from Claude Code**:

1. **Add false positive test cases** from security-review:
   ```python
   class TestFalsePositiveFiltering:
       """Test that low-value findings are filtered."""

       def test_dos_findings_excluded(self):
           """DOS vulnerabilities should be filtered."""
           finding = SecurityFinding(
               description="Infinite loop could cause denial of service"
           )
           assert is_excluded(finding)

       def test_rate_limit_findings_excluded(self):
           """Rate limiting recommendations should be filtered."""
           ...

       def test_markdown_files_excluded(self):
           """Findings in .md files should be excluded."""
           ...
   ```

2. **Add confidence threshold tests**:
   ```python
   def test_low_confidence_filtered(self):
       """Findings with confidence < 0.8 should be filtered."""
       finding = SecurityFinding(confidence=0.6, ...)
       assert is_excluded(finding)
   ```

### TASK-SEC-006: Documentation Update

**Adopt from Claude Code**:

1. **Document exclusion categories** like security-review:
   ```markdown
   ### Excluded Finding Types

   The following finding types are automatically excluded as low-value:
   - Denial of Service / resource exhaustion
   - Rate limiting recommendations
   - Memory leaks / resource management
   - Open redirect vulnerabilities
   - Findings in documentation files (*.md)
   ```

2. **Document confidence thresholds**:
   ```markdown
   ### Confidence Scoring

   Security findings include a confidence score (0.0-1.0).
   Only findings with confidence ≥ 0.8 are reported.
   ```

## Licensing Considerations

- **security-guidance**: Part of claude-code repository (check license)
- **security-review**: Check repository license before using prompts
- **Recommendation**: Use patterns and architecture as inspiration, implement independently

## Performance Characteristics

### security-guidance Plugin
- **Execution time**: ~1 second (substring matching)
- **Memory**: Minimal (no model loading)
- **Scalability**: Handles large files easily

### security-review Tool
- **Execution time**: 2-10 minutes (AI analysis)
- **API calls**: 1-2 calls per review (audit + filtering)
- **Token usage**: ~5000-15000 tokens per review

### Our Hybrid Approach (Recommended)
- **Quick checks**: 5-30 seconds (regex/substring)
- **Full review**: 2-5 minutes (security-specialist agent)
- **Triggered conditionally**: Only security-tagged tasks

## Recommendations Matrix

| TASK-SEC-* | Claude Code Technique | Applicability | Priority |
|------------|----------------------|---------------|----------|
| SEC-001 | Substring matching | High | Implement |
| SEC-001 | Path-based filtering | High | Implement |
| SEC-001 | Expanded pattern list | High | Implement |
| SEC-002 | Hard exclusion categories | High | Implement |
| SEC-002 | File type filtering | Medium | Implement |
| SEC-002 | Environment toggle | Low | Consider |
| SEC-003 | Confidence scoring | High | Implement |
| SEC-003 | 10-category taxonomy | High | Implement |
| SEC-003 | Post-filtering | High | Implement |
| SEC-004 | Category-based triggers | Medium | Implement |
| SEC-005 | False positive tests | High | Implement |
| SEC-005 | Confidence threshold tests | Medium | Implement |
| SEC-006 | Exclusion documentation | High | Implement |

## Conclusion

The Claude Code security approach validates our hybrid design while offering specific techniques to adopt:

1. **Quick checks (SEC-001)**: Expand patterns, add substring matching, add path filtering
2. **Configuration (SEC-002)**: Add exclusion categories and file type filtering
3. **Full review (SEC-003)**: Adopt 10-category taxonomy, confidence scoring, post-filtering
4. **Tag detection (SEC-004)**: Align tags with security-review categories
5. **Testing (SEC-005)**: Add false positive and confidence threshold tests
6. **Documentation (SEC-006)**: Document exclusions and confidence thresholds

**Overall Recommendation**: Proceed with TASK-SEC-001 through SEC-006 implementation, incorporating the specific techniques identified above. The Claude Code security tools confirm our hybrid approach is sound while providing concrete patterns to improve detection accuracy and reduce false positives.

---

*Analysis completed: 2025-12-31*
*Related tasks: TASK-SEC-001 through TASK-SEC-006*
*Sources: [security-guidance plugin](https://github.com/anthropics/claude-code/tree/main/plugins/security-guidance), [claude-code-security-review](https://github.com/anthropics/claude-code-security-review)*
