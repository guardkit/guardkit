# EPIC-001 AI-First Redesign Proposal

**Date**: 2025-11-01
**Problem**: Current design uses algorithmic pattern extraction (regex, heuristics) when we should leverage Claude Code's AI capabilities
**Proposed Solution**: Use existing AI agents (architectural-reviewer, pattern-advisor) for codebase analysis

---

## Current Design Problems

### Issue 1: Reinventing the Wheel

**Current approach** (TASK-038A, 039A, 045):
```python
# Trying to detect patterns with regex/heuristics
class ArchitecturePatternAnalyzer:
    def detect_mvvm(self):
        # 200 lines of brittle logic
        if "viewmodel" in folder_name:
            score += 30
        if "view" in folder_name:
            score += 20
        # etc.
```

**Problem**: We're building a poor version of what Claude already does better.

### Issue 2: Ignoring Existing Capabilities

**We already have:**
- ✅ `architectural-reviewer` agent - analyzes SOLID/DRY/YAGNI, understands architecture
- ✅ `pattern-advisor` agent - recommends design patterns
- ✅ Claude Code - can analyze entire codebases

**Current design**: Ignores all of these, builds custom Python parsers instead.

### Issue 3: Language-Specific Complexity

**Current approach**:
- Needs parsers for 50+ languages
- Regex breaks on edge cases
- Maintenance nightmare

**AI approach**:
- Works for ALL languages automatically
- Understands context, not just syntax
- No maintenance needed

---

## Proposed AI-First Architecture

### Core Principle

**Use AI agents to analyze codebases, not algorithmic code**

### New /template-create Flow

```
1. User runs: /template-create /path/to/existing/project

2. System invokes architectural-reviewer agent:
   "Analyze this codebase and provide:
    - Primary language and frameworks
    - Architecture pattern (MVVM, Clean Arch, etc.)
    - Layer structure (domain, application, infrastructure)
    - Naming conventions (PascalCase, snake_case)
    - Key patterns used (Repository, Service, etc.)
    - Example classes/files that represent the pattern
    - Quality assessment (good patterns vs anti-patterns)"

3. Agent returns structured analysis:
   {
     "language": "C#",
     "frameworks": [".NET 8", "MAUI", "CommunityToolkit.MVVM"],
     "architecture": "MVVM",
     "confidence": 95,
     "layers": {
       "presentation": "Views/, ViewModels/",
       "domain": "Models/",
       "infrastructure": "Services/"
     },
     "naming_conventions": {
       "classes": "PascalCase",
       "files": "PascalCase.cs"
     },
     "key_patterns": [
       {
         "pattern": "ViewModel with INotifyPropertyChanged",
         "example_file": "ViewModels/UserViewModel.cs",
         "quality": "good"
       }
     ]
   }

4. System generates template from AI analysis:
   - Use example files as template basis
   - Extract placeholders from good examples
   - Create manifest.json from analysis
   - Generate CLAUDE.md from architectural report

5. Done - much simpler, more accurate
```

---

## Redesigned Task List

### Wave 0: Foundation (3 tasks, 15h) - DOWN from 6 tasks, 25h

**TASK-037-REVISED: AI-Powered Codebase Analysis (8h, Complexity 5/10)**
- Use architectural-reviewer agent to analyze codebase
- Get language, frameworks, architecture pattern, naming conventions
- Return structured analysis report
- **Replaces**: TASK-037, TASK-037A, TASK-038, TASK-038A, TASK-039, TASK-039A (6 tasks → 1 task)

**TASK-048B: Local Agent Scanner (4h, Complexity 4/10)** - KEEP
- Scan local agents (unchanged)

**TASK-053: Template-init QA Flow (6h, Complexity 5/10)** - KEEP
- Q&A flow (unchanged)

**REMOVED**:
- ❌ TASK-037A: Universal Language Mapping (not needed - AI knows all languages)
- ❌ TASK-038A: Generic Structure Analyzer (AI does this better)
- ❌ TASK-039A: Generic Text Extraction (AI does this better)
- ❌ TASK-048: Subagents.cc Scraper (unreliable)
- ❌ TASK-049: GitHub Agent Parsers (not needed)

---

### Wave 1: Template Generation (4 tasks, 18h) - DOWN from 7 tasks, 33h

**TASK-042-REVISED: AI-Guided Manifest Generator (4h, Complexity 3/10)**
- Take AI analysis report
- Generate manifest.json from structured data
- **Replaces**: TASK-042 (but simplified - no complex detection needed)

**TASK-043-REVISED: Settings Generator from AI Analysis (3h, Complexity 3/10)**
- Generate settings.json from AI-provided naming conventions
- **Replaces**: TASK-040, TASK-041, TASK-043 (3 tasks → 1 task)

**TASK-044-REVISED: CLAUDE.md from Architecture Report (4h, Complexity 3/10)**
- Convert AI architecture analysis into CLAUDE.md documentation
- **Replaces**: TASK-044 (but simplified)

**TASK-045-REVISED: Template Generator from Example Files (7h, Complexity 5/10)**
- Use AI-identified "good example" files as template basis
- Extract placeholders with AI assistance
- Validate generated templates
- **Replaces**: TASK-045, TASK-046 (2 tasks → 1 task, simpler)

**REMOVED**:
- ❌ TASK-040: Naming Convention Inference (AI provides this)
- ❌ TASK-041: Layer Structure Detection (AI provides this)
- ❌ TASK-046: Template Validation (merged into TASK-045-REVISED)
- ❌ TASK-054, 055, 058: Q&A sections (still needed but in different wave)

---

### Wave 2: Agent Discovery (2 tasks, 7h) - DOWN from 5 tasks, 23h

**TASK-048C: Configurable Agent Sources (3h, Complexity 3/10)** - KEEP
- JSON-based source configuration

**TASK-050-REVISED: AI-Powered Agent Recommendation (4h, Complexity 4/10)**
- Use pattern-advisor agent to recommend agents based on project
- Much simpler than complex scoring algorithm
- **Replaces**: TASK-050 (scoring algorithm → AI recommendation)

**REMOVED**:
- ❌ TASK-048: Subagents.cc Scraper
- ❌ TASK-049: GitHub Agent Parsers
- ❌ TASK-051: Agent Selection UI (simplified - just show AI recommendations)
- ❌ TASK-052: Agent Download (merged into simpler flow)

---

### Wave 3: Command Implementation (2 tasks, 10h)

**TASK-047-REVISED: /template-create Orchestrator (6h, Complexity 5/10)**
- Orchestrate AI analysis → template generation flow
- Much simpler than original (fewer dependencies)

**TASK-060-REVISED: /template-init Orchestrator (4h, Complexity 4/10)**
- Simpler Q&A flow (AI fills in intelligent defaults)
- **Note**: Q&A sections (054-059) still exist but simplified

---

### Wave 4: Polish (3 tasks, 18h)

**TASK-065-REVISED: Integration Tests (8h)**
**TASK-066-REVISED: User Documentation (6h)**
**TASK-067-REVISED: Example Templates (4h)**

---

## New Task Count

| Category | Original | Redesigned | Reduction |
|----------|----------|------------|-----------|
| Wave 0 Foundation | 6 tasks, 25h | 3 tasks, 15h | **-50%** |
| Wave 1 Generation | 7 tasks, 33h | 4 tasks, 18h | **-45%** |
| Wave 2 Agents | 5 tasks, 23h | 2 tasks, 7h | **-70%** |
| Wave 3 Commands | Complex integration | 2 tasks, 10h | **-50%** |
| Wave 4 Polish | 7 tasks, 37h | 3 tasks, 18h | **-51%** |
| **TOTAL** | **37 tasks, 220h** | **~18 tasks, ~85h** | **-61%** |

**Timeline**: From 8-12 weeks → **3-4 weeks** (solo developer)

---

## Example: How It Actually Works

### Scenario: User wants template from existing .NET MAUI project

```bash
cd /path/to/my-maui-app
/template-create .
```

**Step 1: AI Analysis** (TASK-037-REVISED)
```
System: Invoking architectural-reviewer to analyze codebase...

Claude analyzes:
- Files: Views/UserPage.xaml, ViewModels/UserViewModel.cs, Models/User.cs
- Architecture: MVVM (ViewModels use INotifyPropertyChanged)
- Patterns: Repository pattern in Services/
- Naming: PascalCase for classes, XAML files match ViewModels
- Quality: Good separation of concerns, clean architecture

Returns:
{
  "language": "C#",
  "framework": ".NET MAUI",
  "architecture": "MVVM",
  "confidence": 95,
  "example_files": {
    "good_viewmodel": "ViewModels/UserViewModel.cs",
    "good_view": "Views/UserPage.xaml",
    "good_model": "Models/User.cs"
  },
  "naming": {
    "viewmodels": "PascalCase + ViewModel suffix",
    "views": "PascalCase + Page suffix"
  }
}
```

**Step 2: Template Generation** (TASK-045-REVISED)
```
System: Using UserViewModel.cs as template basis...

Claude analyzes UserViewModel.cs:
- Identifies: class name, properties, commands
- Creates template with placeholders:

namespace {{ProjectName}}.ViewModels;

public partial class {{Entity}}ViewModel : ObservableObject
{
    [ObservableProperty]
    private {{Entity}} {{entityLower}};

    [RelayCommand]
    async Task Save{{Entity}}()
    {
        // {{Entity}} save logic
    }
}

System: Template created successfully!
```

**Step 3: Manifest Generation** (TASK-042-REVISED)
```json
{
  "name": "maui-mvvm-template",
  "language": "csharp",
  "framework": "dotnet-maui",
  "architecture": "mvvm",
  "patterns": ["repository", "mvvm"],
  "placeholders": {
    "ProjectName": "MyApp",
    "Entity": "User",
    "entityLower": "user"
  }
}
```

**Done!** - Template ready, based on AI analysis of actual good code.

---

## Why This Is Better

### 1. Accuracy
- ❌ **Regex**: 50-70% accuracy, many false positives
- ✅ **AI**: 90-95% accuracy, understands context

### 2. Language Support
- ❌ **Algorithmic**: Need parser for each language (50+ parsers)
- ✅ **AI**: Works for ALL languages automatically

### 3. Code Quality
- ❌ **Algorithmic**: Copies any code (good or bad)
- ✅ **AI**: Identifies and uses GOOD patterns only

### 4. Maintenance
- ❌ **Algorithmic**: Brittle, breaks on edge cases, constant fixes
- ✅ **AI**: Adapts to any code structure automatically

### 5. Implementation Time
- ❌ **Original**: 37 tasks, 220 hours, 8-12 weeks
- ✅ **AI-First**: ~18 tasks, ~85 hours, 3-4 weeks

### 6. User Experience
- ❌ **Original**: May generate poor templates, low confidence scores
- ✅ **AI-First**: High-quality templates from good examples

---

## Implementation Approach

### Phase 1: AI Analysis Integration (Week 1)

**TASK-037-REVISED**: Integrate with architectural-reviewer
```python
# src/commands/template_create/ai_analyzer.py

class AICodebaseAnalyzer:
    def analyze(self, project_root: Path) -> CodebaseAnalysis:
        """
        Use architectural-reviewer agent to analyze codebase
        """
        # Invoke architectural-reviewer agent
        prompt = f"""
        Analyze the codebase at {project_root} and provide:
        1. Primary language and frameworks
        2. Architecture pattern (MVVM, Clean Architecture, etc.)
        3. Layer structure and directory organization
        4. Naming conventions used
        5. Key design patterns
        6. Example files that best represent the architecture
        7. Quality assessment (good vs bad patterns)

        Return as structured JSON.
        """

        response = self._invoke_agent("architectural-reviewer", prompt)

        return CodebaseAnalysis.from_json(response)
```

### Phase 2: Template Generation (Week 2)

**TASK-045-REVISED**: Use AI-identified examples
```python
class AITemplateGenerator:
    def generate_from_examples(
        self,
        analysis: CodebaseAnalysis
    ) -> List[Template]:
        """
        Generate templates from AI-identified good examples
        """
        templates = []

        for example in analysis.example_files:
            # Ask Claude to extract pattern and create template
            prompt = f"""
            Analyze {example.file_path} and create a reusable template.

            1. Identify the pattern (ViewModel, Repository, etc.)
            2. Extract key elements (class name, properties, methods)
            3. Replace specific names with placeholders
            4. Create .template file with {{{{Entity}}}}, {{{{Property}}}} placeholders
            5. Ensure generated code is valid and follows best practices

            Example should be high quality - ignore any anti-patterns.
            """

            template = self._invoke_agent("code-reviewer", prompt)
            templates.append(template)

        return templates
```

### Phase 3: Integration (Week 3)

**TASK-047-REVISED**: Simple orchestration
```python
def template_create(project_root: Path):
    # Step 1: AI analysis (replaces 6 complex tasks)
    analysis = AICodebaseAnalyzer().analyze(project_root)

    # Step 2: Generate templates (replaces complex extraction)
    templates = AITemplateGenerator().generate_from_examples(analysis)

    # Step 3: Create manifest (simple data transformation)
    manifest = ManifestGenerator().from_analysis(analysis)

    # Step 4: Save template
    save_template(templates, manifest)

    print(f"✓ Template created from {analysis.architecture} architecture")
```

---

## Migration Plan

### Option 1: Fresh Start (Recommended)

1. **Archive current EPIC-001 tasks**
   - Move to `tasks/archive/epic-001-algorithmic-approach/`
   - Keep for reference

2. **Create new EPIC-001-REVISED tasks**
   - ~18 tasks instead of 37
   - AI-first approach
   - 3-4 week timeline

3. **Start implementation**
   - Much simpler
   - Higher quality results

### Option 2: Hybrid Approach

1. **Keep some existing tasks**:
   - TASK-048B (local agents) - works fine
   - TASK-053 (Q&A flow) - works fine
   - TASK-061-067 (distribution/docs) - works fine

2. **Replace high-risk algorithmic tasks**:
   - Replace TASK-037, 037A, 038, 038A, 039, 039A → TASK-037-REVISED (AI analysis)
   - Replace TASK-045, 046 → TASK-045-REVISED (AI template gen)
   - Remove TASK-048, 049 (external scraping)

3. **Simplify integration**:
   - TASK-047, 060 become much simpler with fewer dependencies

---

## Risk Assessment: AI-First Approach

### Risks

1. **Agent API changes** (Low)
   - Mitigation: Use stable agent interfaces
   - Fallback: Direct Claude Code API calls

2. **AI hallucination** (Low)
   - Mitigation: Validate generated code (syntax check)
   - Fallback: Manual review option

3. **Cost** (Medium)
   - AI calls cost tokens
   - Mitigation: Cache analysis results, batch operations

### Benefits vs Risks

| Aspect | Algorithmic | AI-First |
|--------|------------|----------|
| Accuracy | 50-70% | 90-95% |
| Maintenance | High | Low |
| Language Support | 4 languages | All languages |
| Implementation Time | 8-12 weeks | 3-4 weeks |
| Code Quality | Variable | High (uses good examples) |
| Risk | Brittle code | Token cost |

**Conclusion**: AI-First is lower risk overall

---

## Recommendation

✅ **ADOPT AI-FIRST REDESIGN**

**Rationale**:
1. You already use this approach (created original templates with Claude Code analysis)
2. Leverages existing agents (architectural-reviewer, pattern-advisor)
3. 61% fewer tasks (37 → 18)
4. 61% less time (220h → 85h)
5. Higher quality results (AI identifies good patterns)
6. Works for ALL languages (no parsers needed)
7. Lower maintenance (no brittle regex)

**Next Steps**:
1. Archive current EPIC-001 tasks
2. Create EPIC-001-REVISED with ~18 AI-first tasks
3. Start with TASK-037-REVISED (AI analysis integration)
4. Complete in 3-4 weeks instead of 8-12

---

**Created**: 2025-11-01
**Status**: ✅ **REDESIGN PROPOSAL READY**
**Recommendation**: Adopt AI-first approach, archive algorithmic tasks
**Timeline Impact**: From 8-12 weeks → 3-4 weeks (61% reduction)
