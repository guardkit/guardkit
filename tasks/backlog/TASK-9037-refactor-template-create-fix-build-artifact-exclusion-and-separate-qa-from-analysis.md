# TASK-9037: Refactor /template-create: Fix build artifact exclusion and separate Q&A from analysis

**Status**: backlog
**Priority**: high
**Created**: 2025-11-12T00:00:00Z
**Updated**: 2025-11-12T00:00:00Z
**Tags**: #template-create #architecture #bugfix
**Complexity**: 8/10 (Complex - architectural refactoring)

---

## Description

The `/template-create` command has critical architectural and functional issues that prevent it from correctly analyzing codebases and require a fundamental refactoring to separate concerns.

**Root Problems Identified:**

1. **Build Artifacts Not Excluded**
   - Counts auto-generated files (e.g., 606 Java files in `obj/Debug/` Android bindings)
   - Misdetects .NET MAUI project as Java (606 .java vs 373 .cs files)
   - No exclusion patterns for `obj/`, `bin/`, `node_modules/`, etc.

2. **Interactive Q&A Blocks Non-Interactive Use**
   - Command hangs waiting for user input in CI/CD or automated workflows
   - `--skip-qa` bypasses questions but makes wrong assumptions
   - No way to provide answers programmatically

3. **Tight Coupling (Single Responsibility Violation)**
   - Q&A + Analysis + Generation all in one command
   - Hard to test individual phases
   - Can't rerun analysis without Q&A
   - Difficult to debug when failures occur

---

## Current Behavior (BROKEN)

### Test Case: .NET MAUI Project Analysis

```bash
cd ~/Projects/DeCUK.Mobile.MyDrive
/template-create --validate --skip-qa
```

**Result:**
- ❌ Detects as "Java" project (606 .java files counted)
- ❌ Ignores actual source: 373 .cs files
- ❌ Generates wrong template: `java-standard-structure-template`
- ❌ Missing: ViewModels, Database layers, MAUI patterns
- ❌ 0 template files created (only metadata: manifest.json, settings.json, CLAUDE.md)
- ❌ Agent scanner error: `module 'installer.global.lib.agent_scanner' has no attribute 'scan_agents'`
- ❌ Phase 6 (Agent Recommendation) fails
- ❌ Validation gives 9.8/10 (false positive - wrong technology detected)

**Why:** Counted all files including:
- `obj/Debug/net9.0-android/android/src/crc64c0976fbcdb365652/*.java` (auto-generated)
- Build artifacts, intermediate files, temporary files

**Additional Issues:**
- Agent scanner module missing `scan_agents()` function
- Validation doesn't check language detection accuracy
- Template generation creates metadata but no actual template files

---

## Expected Behavior (FIXED)

### Phase 1: Q&A Session (New Command)

```bash
/template-qa
# Interactive Q&A session
# Saves answers to: .template-create-config.json
```

**Outputs:**
```json
{
  "template_name": "maui-mobile-app",
  "primary_language": "csharp",
  "frameworks": ["MAUI", "Realm", "CommunityToolkit"],
  "architecture_pattern": "MVVM",
  "testing_strategy": "integration-focused",
  "excluded_patterns": [
    "obj/", "bin/", "*.user", "*.suo",
    "node_modules/", ".git/", "coverage/"
  ],
  "custom_context": {
    "api_configuration": "ConfigurationRepository contains API endpoints",
    "testing_notes": "No unit tests for repositories (Realm issues)",
    "test_focus": "Integration/Feature tests (SignIn pattern)"
  }
}
```

### Phase 2: Analysis & Generation (Refactored Command)

```bash
/template-create --config .template-create-config.json --validate
```

**Behavior:**
1. ✅ Reads saved Q&A answers
2. ✅ Excludes build artifacts using patterns
3. ✅ Correctly detects: .NET MAUI (373 .cs files, excluding obj/)
4. ✅ Generates: `maui-mvvm-realm-template`
5. ✅ Includes: ViewModels, Database (Realm), MAUI patterns
6. ✅ Respects custom context (no API constants, integration test focus)

---

## Acceptance Criteria

### 1. Build Artifact Exclusion (Critical)

- [ ] Default exclusion patterns implemented:
  - [ ] `obj/` and `bin/` (.NET build artifacts)
  - [ ] `node_modules/` (Node.js dependencies)
  - [ ] `.git/` (version control)
  - [ ] `target/` (Maven/Gradle builds)
  - [ ] `build/`, `dist/`, `out/` (common build dirs)
  - [ ] `*.pyc`, `__pycache__/` (Python bytecode)
  - [ ] `coverage/`, `.coverage` (test coverage)
  - [ ] `*.log`, `*.tmp`, `*.cache` (temporary files)

- [ ] Exclusion patterns configurable in Q&A session
- [ ] File counting respects exclusions
- [ ] Language detection uses only source files
- [ ] Validation report shows excluded file counts

### 2. Command Separation (Architecture)

- [ ] New command: `/template-qa`
  - [ ] Interactive Q&A session
  - [ ] Saves answers to `.template-create-config.json`
  - [ ] Supports `--resume` flag for editing saved answers
  - [ ] Validates all answers before saving

- [ ] Refactored command: `/template-create`
  - [ ] Reads config from `--config <file>` flag
  - [ ] Falls back to interactive Q&A if no config found
  - [ ] Separates analysis phase from generation phase
  - [ ] Can run `--analyze-only` for dry-run
  - [ ] Can run `--generate-only` (requires existing analysis)

- [ ] Backward compatibility:
  - [ ] `/template-create` without flags still works (runs Q&A inline)
  - [ ] Old usage patterns continue to function

### 3. Non-Interactive Support (CI/CD)

- [ ] Config file can be committed to repository
- [ ] `--config` flag allows pre-configured runs
- [ ] No user input prompts when config provided
- [ ] Exit codes indicate success/failure clearly:
  - [ ] `0` - Success
  - [ ] `1` - Analysis failed
  - [ ] `2` - Generation failed
  - [ ] `3` - Invalid configuration

### 4. Agent Scanner Fix (Bug Fix)

- [ ] Fix `agent_scanner` module error
  - [ ] Implement missing `scan_agents()` function
  - [ ] Or fix import path if function exists elsewhere
  - [ ] Phase 6 (Agent Recommendation) completes successfully
- [ ] Add unit tests for agent scanner
- [ ] Document agent scanner API

### 5. Template File Generation (Quality Gate)

- [ ] **Minimum template file requirement**:
  - [ ] At least 3 template files generated in `templates/` directory
  - [ ] Not just metadata files (manifest.json, settings.json, CLAUDE.md)
  - [ ] Must include actual code templates
- [ ] Validation report shows template file count
- [ ] Fail validation if 0 template files generated
- [ ] Error message explains why no templates created

### 6. Validation Enhancement (False Positive Prevention)

- [ ] **Language detection validation**:
  - [ ] Check detected language matches project files (.csproj → C#)
  - [ ] Fail validation if language mismatch detected
  - [ ] Show confidence score for language detection
- [ ] **Template consistency validation**:
  - [ ] Verify template language matches detected language
  - [ ] Check framework consistency (MAUI templates for MAUI projects)
  - [ ] Validate naming conventions match detected stack
- [ ] **Minimum quality thresholds**:
  - [ ] Lower validation score if language misdetected (9.8/10 → 3.0/10)
  - [ ] Require ≥5.0/10 to pass validation
  - [ ] Clear error messages for each validation failure

### 7. Improved Error Messages

- [ ] Clear error when build artifacts cause misdetection
- [ ] Suggest exclusion patterns when unexpected file counts detected
- [ ] Warn when primary language has <100 source files
- [ ] Show file count breakdown (source vs excluded)

### 8. Custom Context Support

- [ ] Q&A session accepts freeform "additional context" field
- [ ] Context passed to AI analyzer agents
- [ ] Example contexts saved in documentation:
  - [ ] API configuration patterns
  - [ ] Testing strategies
  - [ ] Architecture decisions

---

## Technical Design

### File Structure (New)

```
installer/global/commands/
├── template-qa.md                  # New command: Q&A session only
├── template-create.md              # Refactored: analysis + generation
└── lib/
    ├── template_create_orchestrator.py  # Refactored
    ├── template_qa_orchestrator.py      # New
    └── template_creation/
        ├── config.py                    # New: Config file management
        ├── exclusions.py                # New: Build artifact exclusions
        └── ...
```

### Configuration Schema

**File:** `.template-create-config.json`

```json
{
  "$schema": "https://taskwright.dev/schemas/template-config.schema.json",
  "version": "1.0",
  "template_name": "string",
  "primary_language": "csharp|java|python|typescript|...",
  "frameworks": ["string"],
  "architecture_pattern": "string",
  "testing_strategy": "string",
  "excluded_patterns": ["string"],
  "included_patterns": ["string"],  // Override exclusions
  "custom_context": {
    "key": "value"
  },
  "output_location": "global|repo",
  "validation_level": "basic|extended|comprehensive"
}
```

### Exclusion Patterns (New Module)

**File:** `installer/global/lib/template_creation/exclusions.py`

```python
DEFAULT_EXCLUSIONS = [
    # .NET build artifacts
    "obj/", "bin/", "*.user", "*.suo", "*.sln.docstates",

    # Node.js
    "node_modules/", "package-lock.json", "yarn.lock",

    # Python
    "__pycache__/", "*.pyc", "*.pyo", ".venv/", "venv/",

    # Java/JVM
    "target/", "*.class", "*.jar", "*.war",

    # Build outputs
    "build/", "dist/", "out/", "*.log",

    # Version control
    ".git/", ".svn/", ".hg/",

    # IDE
    ".vscode/", ".idea/", "*.swp", "*.swo",

    # Testing/Coverage
    "coverage/", ".coverage", ".pytest_cache/", "htmlcov/",

    # Temporary
    "*.tmp", "*.temp", "*.cache", ".DS_Store"
]

def should_exclude_file(filepath: Path, exclusions: List[str]) -> bool:
    """Check if file should be excluded from analysis."""
    ...

def get_source_files(root: Path, exclusions: List[str]) -> List[Path]:
    """Get all source files respecting exclusions."""
    ...
```

### Refactored Orchestrator

**Key Changes:**

1. **Separate Concerns:**
   ```python
   # Old (monolithic)
   def run_template_create():
       qa_answers = run_qa_session()  # Interactive
       analysis = analyze_codebase(qa_answers)
       generate_template(analysis)

   # New (separated)
   def run_template_qa():
       answers = run_qa_session()
       save_config(answers, ".template-create-config.json")

   def run_template_create(config_file=None):
       config = load_config(config_file) or run_qa_session()
       analysis = analyze_codebase(config, exclude_patterns=config.excluded_patterns)
       generate_template(analysis, config)
   ```

2. **Exclusion Integration:**
   ```python
   def analyze_codebase(config, exclude_patterns):
       source_files = get_source_files(
           root=Path(config.codebase_path),
           exclusions=exclude_patterns
       )

       # Count files by extension (only source files)
       file_counts = count_by_extension(source_files)

       # Detect primary language (correct now!)
       primary_language = detect_language(file_counts)
       ...
   ```

---

## Implementation Plan

### Phase 1: Add Build Artifact Exclusions (2 hours)

**Goal:** Fix immediate issue - exclude build artifacts from analysis

1. **Create exclusions module** (`exclusions.py`)
   - Define `DEFAULT_EXCLUSIONS` list
   - Implement `should_exclude_file()` function
   - Implement `get_source_files()` function
   - Add unit tests for exclusion logic

2. **Integrate into analyzer** (`codebase_analyzer.py`)
   - Pass exclusions to file collection
   - Update file counting to respect exclusions
   - Add `excluded_count` to analysis output
   - Show exclusion summary in logs

3. **Test with .NET MAUI project**
   - Run analyzer on `DeCUK.Mobile.MyDrive`
   - Verify: .cs files counted, .java files excluded
   - Verify: Detects as "C#" not "Java"
   - Verify: Generated template is MAUI-focused

**Acceptance Test:**
```bash
cd ~/Projects/DeCUK.Mobile.MyDrive
/template-create --validate --skip-qa

# Expected Output:
# Primary Language: C# (373 source files)
# Excluded Files: 606 (build artifacts, auto-generated)
# Template: maui-mvvm-realm-template
```

### Phase 2: Create /template-qa Command (3 hours)

**Goal:** Separate Q&A session into standalone command

1. **Create Q&A orchestrator** (`template_qa_orchestrator.py`)
   - Extract Q&A logic from `template_create_orchestrator.py`
   - Add config file save functionality
   - Add `--resume` flag support
   - Add validation before save

2. **Create config module** (`config.py`)
   - Define `TemplateConfig` dataclass
   - Implement `save_config()` function
   - Implement `load_config()` function
   - Add schema validation

3. **Create /template-qa command** (`template-qa.md`)
   - Command documentation
   - Python execution block
   - Usage examples

4. **Add tests**
   - Test Q&A flow
   - Test config save/load
   - Test resume functionality

**Acceptance Test:**
```bash
# Run Q&A session
/template-qa
# Answer questions interactively
# Output: Saved configuration to .template-create-config.json

# Review saved config
cat .template-create-config.json

# Resume to edit answers
/template-qa --resume
```

### Phase 3: Refactor /template-create Command (3 hours)

**Goal:** Make `/template-create` use config file, support phases

1. **Refactor orchestrator** (`template_create_orchestrator.py`)
   - Add `--config` flag support
   - Load config or fall back to inline Q&A
   - Add `--analyze-only` flag
   - Add `--generate-only` flag
   - Pass exclusions from config to analyzer

2. **Update command file** (`template-create.md`)
   - Document new flags
   - Show config file usage examples
   - Add backward compatibility notes

3. **Add integration tests**
   - Test with config file
   - Test without config file (inline Q&A)
   - Test `--analyze-only`
   - Test `--generate-only`

**Acceptance Test:**
```bash
# Create config first
/template-qa
# (answers saved to .template-create-config.json)

# Run analysis with config
/template-create --config .template-create-config.json --validate

# Expected: No Q&A prompts, uses saved answers
```

### Phase 4: Add Custom Context Support (1 hour)

**Goal:** Allow users to provide domain-specific context

1. **Update Q&A session**
   - Add "Additional Context" prompt at end
   - Accept multi-line input
   - Save to `config.custom_context`

2. **Pass context to AI analyzer**
   - Include custom context in agent prompts
   - Show context in analysis output

3. **Document common patterns**
   - API configuration examples
   - Testing strategy examples
   - Architecture decision examples

**Acceptance Test:**
```bash
/template-qa
# ... standard questions ...
# Q: Any additional context? (optional, press Enter to skip)
# A: ConfigurationRepository contains API endpoints. No API Constants needed.
#    Remove repository unit tests (Realm issues). Focus on integration tests.

# Config saved with custom_context field

/template-create --config .template-create-config.json
# Analysis includes custom context in prompts
```

### Phase 5: Fix Agent Scanner Bug (1 hour)

**Goal:** Fix Phase 6 (Agent Recommendation) failure

1. **Investigate agent scanner module**
   - Locate `installer/global/lib/agent_scanner.py`
   - Check if `scan_agents()` function exists
   - If missing, implement function
   - If misnamed, fix import/reference

2. **Implement or fix scan_agents()**
   ```python
   def scan_agents(agent_dir: Path) -> List[AgentInfo]:
       """Scan agent directory and return agent metadata."""
       agents = []
       for agent_file in agent_dir.glob("*.md"):
           # Parse agent markdown file
           # Extract: name, description, capabilities
           agents.append(AgentInfo(...))
       return agents
   ```

3. **Add unit tests**
   - Test agent directory scanning
   - Test agent metadata extraction
   - Test error handling (missing dir, invalid files)

**Acceptance Test:**
```bash
/template-create --validate --skip-qa
# Expected: Phase 6 (Agent Recommendation) completes without errors
# No "has no attribute 'scan_agents'" error
```

### Phase 6: Add Template File Generation Validation (1 hour)

**Goal:** Prevent 0 template files from passing validation

1. **Update validation logic** (`template_creation/validator.py`)
   - Add check: `len(templates_dir.glob("*.tpl")) >= 3`
   - Fail validation if no template files
   - Show error: "No template files generated. Check language detection."

2. **Update validation report**
   - Add section: "Template Files" with count
   - Show list of generated template files
   - Warn if count < expected based on codebase size

3. **Add test**
   - Test validation fails with 0 template files
   - Test validation passes with ≥3 template files

**Acceptance Test:**
```bash
# (With current bug - wrong language detected)
/template-create --validate --skip-qa
# Expected: Validation FAILS (not 9.8/10)
# Error: "Template validation failed: 0 template files generated"
# Suggestion: "Check language detection - detected Java but project is C#"
```

### Phase 7: Enhance Validation (Language Detection) (2 hours)

**Goal:** Prevent false positive validations (9.8/10 for wrong template)

1. **Add language detection validation**
   ```python
   def validate_language_detection(analysis: CodebaseAnalysis, manifest: TemplateManifest):
       # Check 1: Project files consistency
       if has_csproj_files and manifest.language != "csharp":
           return ValidationError("Language mismatch: .csproj files found but detected as {manifest.language}")

       # Check 2: Source file ratios
       if source_cs_files > source_java_files and manifest.language == "java":
           return ValidationError("Language mismatch: More .cs than .java source files")

       # Check 3: Framework consistency
       if "MAUI" in frameworks and manifest.language != "csharp":
           return ValidationError("Framework mismatch: MAUI requires C#")

       return None  # Validation passed
   ```

2. **Update validation scoring**
   - Language mismatch: -6.0 points (9.8/10 → 3.8/10)
   - 0 template files: -5.0 points
   - Framework inconsistency: -4.0 points

3. **Add confidence scores**
   - Show language detection confidence (0-100%)
   - Warn if confidence < 70%
   - Require manual review if confidence < 50%

**Acceptance Test:**
```bash
# (With current bug - wrong language detected)
/template-create --validate --skip-qa

# Expected validation output:
# ❌ VALIDATION FAILED: 3.8/10 (Grade: F)
#
# Critical Issues:
# - Language mismatch: Detected Java but project has .csproj files (C# project)
# - 0 template files generated
# - Source file ratio: 373 .cs files > 606 .java files (after excluding obj/)
#
# Recommendation: Review build artifact exclusions and language detection
```

### Phase 8: Documentation & Migration (1 hour)

**Goal:** Document changes, provide migration guide

1. **Update documentation**
   - `/template-qa` command guide
   - `/template-create` refactoring guide
   - Config file schema reference
   - Exclusion patterns guide
   - Agent scanner API reference
   - Validation enhancement notes

2. **Create migration guide**
   - Old workflow → New workflow
   - Benefits of new approach
   - Backward compatibility notes

3. **Update tests**
   - Add end-to-end tests
   - Update existing tests for new architecture

---

## Testing Strategy

### Unit Tests

1. **Exclusions Module:**
   - Test `should_exclude_file()` with various patterns
   - Test `get_source_files()` on mock directory structure
   - Verify DEFAULT_EXCLUSIONS coverage

2. **Config Module:**
   - Test config save/load roundtrip
   - Test schema validation
   - Test invalid config rejection

3. **Q&A Orchestrator:**
   - Test interactive flow (mocked input)
   - Test resume functionality
   - Test validation logic

### Integration Tests

1. **End-to-End Workflow:**
   - Run `/template-qa` → save config
   - Run `/template-create --config` → generate template
   - Verify template correctness

2. **Real Codebase Tests:**
   - Test on .NET MAUI project (DeCUK.Mobile.MyDrive)
   - Test on React TypeScript project
   - Test on Python FastAPI project
   - Verify correct language detection
   - Verify build artifacts excluded

3. **Backward Compatibility:**
   - Test old usage: `/template-create` (no flags)
   - Verify inline Q&A still works
   - Verify generated templates unchanged

### Manual Testing

1. **User Experience:**
   - Run complete workflow from user perspective
   - Verify prompts are clear
   - Verify error messages are helpful
   - Verify config file is readable

2. **Edge Cases:**
   - Empty config file
   - Missing config file
   - Corrupted config file
   - Very large codebase (>10k files)
   - Codebase with multiple primary languages

---

## Risks & Mitigations

### Risk 1: Breaking Existing Workflows
**Severity:** High
**Mitigation:**
- Maintain backward compatibility (inline Q&A if no config)
- Comprehensive testing of old workflows
- Clear migration guide with examples

### Risk 2: Exclusion Patterns Too Aggressive
**Severity:** Medium
**Mitigation:**
- Conservative default exclusions
- Allow overrides via `included_patterns`
- Show excluded file count in output
- Document how to customize exclusions

### Risk 3: Config File Management Complexity
**Severity:** Low
**Mitigation:**
- Simple JSON schema (human-readable/editable)
- Clear validation error messages
- Resume flag for easy editing
- Examples in documentation

---

## Benefits

### Immediate Benefits

1. **Correct Language Detection:**
   - .NET MAUI projects correctly identified as C#
   - No more Java/C# confusion
   - Better template generation accuracy

2. **CI/CD Support:**
   - Pre-configure answers in config file
   - Commit config to repository
   - Automated template generation possible

3. **Testability:**
   - Each phase independently testable
   - Mock Q&A answers in tests
   - Faster test execution

### Long-Term Benefits

1. **Maintainability:**
   - Single Responsibility Principle followed
   - Easier to add new features
   - Clearer code organization

2. **Debuggability:**
   - Can rerun analysis without Q&A
   - Can inspect saved config
   - Clear phase separation

3. **Extensibility:**
   - Easy to add new Q&A questions
   - Easy to add new exclusion patterns
   - Easy to add new config options

---

## Definition of Done

### Core Functionality
- [ ] Build artifacts excluded by default
- [ ] `/template-qa` command created and working
- [ ] `/template-create --config` working
- [ ] Config file schema documented
- [ ] Custom context support implemented

### Testing
- [ ] Unit tests: 100% coverage on new modules
- [ ] Integration tests: All workflows covered
- [ ] Manual testing: User experience validated
- [ ] Real codebase tests: .NET MAUI, React, Python

### Documentation
- [ ] `/template-qa` command guide written
- [ ] `/template-create` changes documented
- [ ] Config schema reference created
- [ ] Migration guide written
- [ ] Examples added for common use cases

### Quality Gates
- [ ] All tests passing (100%)
- [ ] Architectural review approved (≥80/100)
- [ ] Code review approved
- [ ] Backward compatibility verified
- [ ] No breaking changes to existing users

---

## Timeline Estimate

- **Phase 1 (Build Artifact Exclusions):** 2 hours
- **Phase 2 (Q&A Command Creation):** 3 hours
- **Phase 3 (Refactor /template-create):** 3 hours
- **Phase 4 (Custom Context Support):** 1 hour
- **Phase 5 (Agent Scanner Bug Fix):** 1 hour
- **Phase 6 (Template File Generation Validation):** 1 hour
- **Phase 7 (Validation Enhancement):** 2 hours
- **Phase 8 (Documentation & Migration):** 1 hour
- **Total:** 14 hours (~1.75 days)

---

## Related Issues

- **TASK-BRIDGE-006:** Fixed command structure (COMPLETED)
- **User Report:** "Java detected in .NET MAUI project"
- **User Report:** "Interactive Q&A blocks CI/CD"
- **Execution Log:** Template creation completed with exit code 0 but generated wrong template
- **Bug Report:** Agent scanner module missing `scan_agents()` function
- **Bug Report:** Validation gives 9.8/10 despite 0 template files and wrong language detection

---

## References

- Current implementation: `installer/global/commands/lib/template_create_orchestrator.py`
- Test case: `~/Projects/DeCUK.Mobile.MyDrive` (.NET MAUI project)
- Validation output: `~/.agentecflow/templates/java-standard-structure-template/validation-report.md`
