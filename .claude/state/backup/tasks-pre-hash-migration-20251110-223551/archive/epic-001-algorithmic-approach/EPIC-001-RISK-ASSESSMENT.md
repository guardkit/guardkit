# EPIC-001 Technical Risk Assessment

**Date**: 2025-11-01
**Epic**: EPIC-001 - Template Creation Automation
**Purpose**: Identify high-risk tasks where implementation might not work

---

## Risk Classification

- 🔴 **HIGH RISK**: Fundamental feasibility concerns, might not work as designed
- 🟡 **MEDIUM RISK**: Technical challenges, may require significant iteration
- 🟢 **LOW RISK**: Straightforward implementation, low probability of failure

---

## 🔴 HIGH RISK TASKS (4 tasks)

### 1. TASK-048: Subagents.cc Scraper 🔴

**Risk Level**: HIGH (8/10)
**Hours**: 6h | **Complexity**: 6/10

**Why High Risk:**
- **Web scraping is inherently fragile**
  - Website HTML structure can change at any time
  - No official API, rely on DOM parsing
  - Rate limiting, anti-scraping measures
  - Site downtime or redesign breaks everything

- **Maintenance burden**
  - Requires constant updates when site changes
  - No guarantees of stability
  - Could break weeks after implementation

**Feasibility Assessment:**
- ✅ Technically possible to implement
- ❌ High probability of breaking over time
- ❌ No control over upstream changes

**Mitigation Strategies:**

1. **Make it optional, not required:**
   ```python
   def discover_agents():
       agents = []

       # Try subagents.cc (may fail)
       try:
           subagents = scrape_subagents_cc()
           agents.extend(subagents)
       except Exception as e:
           logger.warning(f"Subagents.cc unavailable: {e}")
           # Continue without it

       # Other sources still work
       agents.extend(discover_local_agents())
       agents.extend(discover_github_agents())

       return agents
   ```

2. **Implement robust error handling:**
   - Cache last successful scrape
   - Graceful degradation if scraping fails
   - Clear user messaging: "Subagents.cc unavailable, using cached data"

3. **Add monitoring/alerting:**
   - Detect when scraper breaks
   - Alert for manual fixing
   - Document expected HTML structure

4. **Consider alternatives:**
   - Contact subagents.cc for official API
   - Use RSS feed if available
   - Manual curation fallback

**Recommendation**: ⚠️ **Implement with VERY defensive coding**
- Must not block template creation if unavailable
- Consider marking as "experimental" feature
- Document expected maintenance burden

**Alternative Approach**: Skip TASK-048 entirely, rely only on:
- Local agents (TASK-048B) - 15+ agents, reliable
- GitHub agents (TASK-049) - stable API
- User-configured sources (TASK-048C)

---

### 2. TASK-038A: Generic Structure Analyzer 🔴

**Risk Level**: MEDIUM-HIGH (7/10)
**Hours**: 6h | **Complexity**: 6/10

**Why High Risk:**
- **Pattern detection accuracy concerns**
  - Detecting MVVM from folder names is heuristic-based
  - High false positive rate (folder named "views" doesn't guarantee MVC)
  - Missing patterns (unconventional structures)
  - Low confidence scores may make feature useless

- **Language/framework variations**
  - Go projects: flat structure common
  - Ruby on Rails: convention over configuration
  - Microservices: non-standard layouts
  - Monorepos: multiple patterns in one project

**Example Failure Case:**
```
Project structure:
  /app
    /components    <- Is this "presentation" layer?
    /services      <- Is this "application" layer?
    /models        <- Is this "domain" layer?

Could be:
1. Clean Architecture (domain/application/presentation)
2. Generic MVC (models/views/controllers but views=components)
3. Service Layer pattern
4. Just random folder names

Confidence: LOW (30-40%)
```

**Feasibility Assessment:**
- ✅ Can implement heuristics
- ⚠️ Accuracy likely 50-70% at best
- ❌ May produce misleading results

**Mitigation Strategies:**

1. **Lower expectations, higher thresholds:**
   ```python
   # Original design: threshold 60%
   # Revised: threshold 75% to reduce false positives

   PATTERN_SIGNATURES = {
       ArchitecturePattern.CLEAN_ARCHITECTURE: PatternSignature(
           confidence_threshold=75  # Was 60
       )
   }
   ```

2. **Add "UNKNOWN" as valid result:**
   ```python
   def detect_patterns(self):
       patterns = # ... detection logic

       if not patterns or patterns[0].confidence < 75:
           return PatternDetection(
               pattern=ArchitecturePattern.UNKNOWN,
               confidence=100,
               message="No clear pattern detected - using generic structure"
           )
   ```

3. **Show confidence scores to user:**
   - Don't hide low confidence
   - Let user override detection
   - Provide "not sure" option

4. **Combine with other signals:**
   - Check for framework-specific files (e.g., `.csproj` → likely MVVM)
   - Look for package.json dependencies
   - Cross-reference with language detection

**Recommendation**: ✅ **Implement with lower confidence thresholds**
- Accept that it won't be 100% accurate
- Make it advisory, not authoritative
- Provide manual override option
- Default to "generic structure" when unsure

**Fallback**: If confidence < 50%, use generic folder mapping without pattern detection

---

### 3. TASK-039A: Generic Text-Based Extraction 🔴

**Risk Level**: MEDIUM-HIGH (7/10)
**Hours**: 5h | **Complexity**: 5/10

**Why High Risk:**
- **Regex brittleness across languages**
  - Language syntax variations are enormous
  - Comments, strings, multi-line statements break regex
  - Edge cases: nested classes, generics, macros

- **False positives/negatives**
  ```python
  # Python regex: r'class\s+(\w+)\s*(?:\(.*?\))?\s*:'

  # Matches correctly:
  class User:
  class User(BaseModel):

  # Fails:
  class User(
      BaseModel,
      SomeMixin
  ):  # Multi-line

  # False positive:
  # class OldUser:  <- In comment!
  "class FakeClass:"  <- In string!
  ```

- **70% confidence baseline may be too optimistic**
  - Real-world accuracy likely 50-60%
  - Lots of edge cases

**Feasibility Assessment:**
- ✅ Basic patterns extractable
- ⚠️ Accuracy will be inconsistent
- ❌ Won't handle complex cases well

**Mitigation Strategies:**

1. **Focus on high-confidence simple cases:**
   ```python
   # Instead of trying to parse everything,
   # focus on patterns we can detect reliably:

   SIMPLE_PATTERNS = {
       'class': r'^class\s+(\w+)',      # Only BOL classes
       'function': r'^def\s+(\w+)\(',   # Only BOL functions
       'import': r'^import\s+(\w+)',    # Only simple imports
   }

   # Skip complex cases:
   # - Nested classes
   # - Multi-line definitions
   # - Decorators
   # - Generics
   ```

2. **Add validation step:**
   ```python
   def validate_extraction(self, elements):
       """
       Remove likely false positives
       """
       validated = []
       for element in elements:
           # Skip if found in comment line
           if self._is_in_comment(element.line):
               continue

           # Skip if found in string
           if self._is_in_string(element.line):
               continue

           validated.append(element)

       return validated
   ```

3. **Lower confidence scores:**
   ```python
   # Original: 70% confidence for text-based
   # Revised: 50% confidence, honest about limitations

   return CodeElement(
       confidence=50,  # Honest assessment
       metadata={'extraction_method': 'text_regex', 'may_be_inaccurate': True}
   )
   ```

4. **Provide AST fallback path:**
   ```python
   def extract_patterns(self, file_path):
       # Try AST first (if available)
       try:
           return self._extract_with_ast(file_path)  # 90% confidence
       except:
           pass

       # Fallback to text-based
       return self._extract_with_regex(file_path)  # 50% confidence
   ```

**Recommendation**: ✅ **Implement with realistic expectations**
- Target 50% confidence, not 70%
- Focus on simple cases only
- Add AST parsing for supported languages (Python, JavaScript)
- Accept that some extractions will be wrong

**Critical**: Document that this is "best effort" extraction, not guaranteed accurate

---

### 4. TASK-045: Code Template Generator 🔴

**Risk Level**: MEDIUM-HIGH (6/10)
**Hours**: 8h | **Complexity**: 7/10

**Why High Risk:**
- **Generated code quality concerns**
  - Templates based on extracted patterns may be low quality
  - Placeholder replacement could break syntax
  - Generated code might not compile
  - May not follow best practices

- **Garbage in, garbage out**
  - If TASK-039/039A extracts poorly, templates will be poor
  - No guarantee source code was good to begin with
  - May copy anti-patterns

**Example Failure Case:**
```python
# Extracted pattern (from bad code):
class {{ClassName}}Controller:
    def process(self):
        # TODO: implement
        pass

# Generated template copies bad pattern:
class UserController:  # Missing constructor!
    def process(self):  # No parameters!
        # TODO: implement  # Leaves TODOs!
        pass
```

**Feasibility Assessment:**
- ✅ Can generate templates mechanically
- ⚠️ Quality highly variable
- ❌ May generate broken/poor code

**Mitigation Strategies:**

1. **Add validation phase:**
   ```python
   def generate_template(self, pattern):
       template = self._create_template(pattern)

       # Validate generated template
       if not self._validate_template(template):
           # Fall back to generic template
           return self._get_generic_template()

       return template
   ```

2. **Use curated templates as baseline:**
   ```python
   # Don't rely solely on extraction
   # Have hand-crafted baseline templates per language

   BASELINE_TEMPLATES = {
       'python_class': """
   class {{ClassName}}:
       \"\"\"{{Description}}\"\"\"

       def __init__(self):
           pass
       """,
       'typescript_class': """
   export class {{ClassName}} {
       constructor() {}
   }
       """
   }

   # Merge extracted patterns with baseline
   def generate(self):
       baseline = BASELINE_TEMPLATES[self.template_type]
       extracted = self.extract_patterns()

       # Enhance baseline with extracted patterns, don't replace
       return self.merge(baseline, extracted)
   ```

3. **Add manual review checkpoint:**
   ```python
   # After template generation, show to user:
   print("Generated template:")
   print(template_code)

   choice = input("Accept (a), Edit (e), Use generic (g): ")

   if choice == 'e':
       # Open in editor for manual fixing
       return self._manual_edit(template_code)
   elif choice == 'g':
       return self._generic_template()
   ```

4. **Syntax validation:**
   ```python
   def validate_template(self, template, language):
       # Try to parse with language parser
       if language == 'python':
           try:
               ast.parse(template)
               return True
           except SyntaxError:
               return False
   ```

**Recommendation**: ✅ **Implement with hybrid approach**
- Don't rely solely on extraction
- Use hand-crafted baseline + extraction enhancement
- Add validation and fallback to generic templates
- Allow manual review/editing

**Fallback**: Maintain library of hand-crafted templates for common patterns

---

## 🟡 MEDIUM RISK TASKS (6 tasks)

### 5. TASK-037A: Universal Language Mapping 🟡

**Risk Level**: MEDIUM (5/10)
**Hours**: 3h | **Complexity**: 3/10

**Why Medium Risk:**
- **Completeness concerns**
  - 50+ languages is a lot of manual data entry
  - Easy to have incorrect metadata (wrong frameworks, test tools)
  - Maintenance burden as languages evolve

- **Not really high risk for failure**
  - The implementation itself is straightforward
  - Just data structures
  - Risk is more about quality/completeness

**Feasibility Assessment:**
- ✅ Definitely implementable (just data)
- ⚠️ May be incomplete or have errors
- ⚠️ Requires ongoing maintenance

**Mitigation:**
- Start with 10-15 most common languages
- Mark others as "partial support"
- Allow user contributions to expand
- Version the language database

**Recommendation**: ✅ **Implement incrementally**
- Phase 1: 10 most common languages (Go, Rust, Python, TypeScript, Java, C#, Ruby, PHP, Kotlin, Swift)
- Phase 2: Add 20 more languages over time
- Accept that it won't be 100% complete immediately

---

### 6. TASK-049: GitHub Agent Parsers 🟡

**Risk Level**: MEDIUM (5/10)
**Hours**: 8h | **Complexity**: 7/10

**Why Medium Risk:**
- **Repository structure variations**
  - wshobson/agents and VoltAgent may not have consistent structure
  - Parsing logic might break if repos are reorganized
  - Reliance on specific file formats

- **Better than web scraping (GitHub API is stable)**
  - But still dependent on external repos

**Mitigation:**
- Use GitHub API (stable)
- Handle missing/malformed files gracefully
- Cache successfully parsed agents

**Recommendation**: ✅ **Implement with error handling**

---

### 7. TASK-050: Agent Matching Algorithm 🟡

**Risk Level**: MEDIUM (4/10)
**Hours**: 7h | **Complexity**: 6/10

**Why Medium Risk:**
- **Weight tuning challenges**
  - Technology (40%), Pattern (30%), Tools (20%), Community (10%)
  - These percentages are arbitrary
  - May need significant tuning

- **Subjective quality of matches**
  - "Good match" is subjective
  - Users may disagree with scores

**Mitigation:**
- Make weights configurable
- Add manual override option
- Show reasoning for scores

**Recommendation**: ✅ **Implement with configurable weights**

---

### 8. TASK-060: /template-init Orchestrator 🟡

**Risk Level**: MEDIUM (5/10)
**Hours**: 6h | **Complexity**: 6/10

**Why Medium Risk:**
- **Integration complexity**
  - 12 dependencies
  - Lots of moving parts
  - Coordination challenges

- **Not fundamental feasibility risk**
  - More about integration bugs
  - Fixable through testing

**Mitigation:**
- Comprehensive integration tests
- Incremental integration (add one Q&A section at a time)
- Fallback to manual template creation

**Recommendation**: ✅ **Implement with thorough testing**

---

### 9. TASK-047: /template-create Orchestrator 🟡

**Risk Level**: MEDIUM (5/10)
**Hours**: 6h | **Complexity**: 6/10

**Why Medium Risk:**
- Similar to TASK-060
- Integration complexity
- Not fundamental feasibility

**Mitigation:**
- Same as TASK-060

**Recommendation**: ✅ **Implement with thorough testing**

---

### 10. TASK-065: Integration Tests 🟡

**Risk Level**: MEDIUM (4/10)
**Hours**: 10h | **Complexity**: 7/10

**Why Medium Risk:**
- **Test coverage challenges**
  - Hard to test all edge cases
  - Multi-language testing complexity
  - Mocking external dependencies (GitHub, subagents.cc)

**Mitigation:**
- Focus on happy path first
- Add edge case tests incrementally
- Use recording/replay for external APIs

**Recommendation**: ✅ **Implement incrementally**

---

## 🟢 LOW RISK TASKS (27 tasks)

All other tasks (27 remaining) are LOW RISK:
- Straightforward data structures
- Well-defined interfaces
- Standard implementations
- Low probability of fundamental failure

Examples:
- TASK-037: Stack detection (file pattern matching)
- TASK-040: Naming convention inference (straightforward analysis)
- TASK-042: Manifest generator (JSON generation)
- TASK-043: Settings generator (JSON generation)
- TASK-053-058: Q&A sections (simple input/validation)

---

## Risk Mitigation Summary

### Recommended Changes to Epic

#### 1. Make Subagents.cc Optional (TASK-048)

**Option A**: Make it non-blocking
```python
# Template creation works even if subagents.cc fails
agents = discover_local_agents()  # Always works
agents += discover_github_agents()  # Likely works

try:
    agents += discover_subagents_cc()  # May fail
except:
    logger.warning("Subagents.cc unavailable")
```

**Option B**: Skip entirely
- Remove TASK-048 from critical path
- Only use local + GitHub + user-configured sources
- Add subagents.cc later if stable API becomes available

**Recommendation**: Option A (optional feature)

#### 2. Lower Confidence Expectations

Update task acceptance criteria:

| Task | Original Confidence | Realistic Confidence |
|------|---------------------|---------------------|
| TASK-038A | Pattern detection works | Pattern detection works for common cases (60%+ accuracy) |
| TASK-039A | 70% baseline confidence | 50% baseline confidence, with AST fallback |
| TASK-045 | Templates generated | Valid templates generated (may need manual review) |

#### 3. Add Fallback Strategies

For each high-risk task, add explicit fallback:

```
TASK-048: Subagents.cc → Fallback: Skip, use cached data
TASK-038A: Pattern detection → Fallback: "Unknown" pattern, generic structure
TASK-039A: Text extraction → Fallback: AST parsing or manual specification
TASK-045: Template generation → Fallback: Hand-crafted generic templates
```

#### 4. Add Validation Tasks

Insert validation tasks after high-risk tasks:

```
TASK-045 (Template Generator)
  ↓
TASK-045.1 (NEW): Template Validation & Manual Review (2h)
  - Syntax check generated templates
  - Human review for quality
  - Option to use generic template instead
```

---

## Overall Risk Assessment

**Epic Feasibility**: ✅ **FEASIBLE with modifications**

**Risk Distribution**:
- 🔴 HIGH RISK: 4 tasks (11%, 25 hours)
- 🟡 MEDIUM RISK: 6 tasks (16%, 47 hours)
- 🟢 LOW RISK: 27 tasks (73%, 148 hours)

**Critical Risks**:
1. **Web scraping fragility** (TASK-048)
2. **Pattern detection accuracy** (TASK-038A, TASK-039A)
3. **Generated code quality** (TASK-045)

**Recommended Actions**:

1. ✅ **Proceed with implementation** (epic is viable)
2. ⚠️ **Mark TASK-048 as optional** (don't block on it)
3. ⚠️ **Add fallback strategies** for TASK-038A, 039A, 045
4. ⚠️ **Lower confidence expectations** (50% vs 70%)
5. ⚠️ **Add manual review checkpoints** for generated templates
6. ✅ **Implement hybrid approach** (extraction + hand-crafted baselines)

**Timeline Impact**: None if mitigations implemented upfront

**Success Probability**:
- Without mitigations: 60-70%
- With mitigations: 85-90%

---

## Recommendations by Risk Level

### 🔴 HIGH RISK - Immediate Action Required

1. **TASK-048** → Make optional or skip
2. **TASK-038A** → Add "Unknown" fallback, lower threshold to 75%
3. **TASK-039A** → Lower confidence to 50%, add AST fallback
4. **TASK-045** → Hybrid approach (baseline + extraction)

### 🟡 MEDIUM RISK - Monitor Closely

5. **TASK-037A** → Start with 10 languages, expand iteratively
6. **TASK-049** → Robust error handling
7. **TASK-050** → Configurable weights
8. **TASK-047, 060** → Comprehensive integration tests

### 🟢 LOW RISK - Proceed Normally

All other tasks → Low risk, standard implementation

---

## Decision Points

### Decision 1: Include Subagents.cc?

**Option A**: Include as optional feature
- ✅ More agent sources
- ❌ Maintenance burden
- ❌ Fragile dependency

**Option B**: Skip entirely
- ✅ Reduced risk
- ✅ Simpler implementation
- ❌ Fewer agents available

**Recommendation**: Option A (optional), with clear fallback

### Decision 2: Text-based extraction accuracy?

**Option A**: Target 70% confidence as designed
- ❌ Likely unachievable
- ❌ Sets wrong expectations

**Option B**: Target 50% confidence, add AST fallback
- ✅ Realistic
- ✅ Honest about limitations
- ✅ Better user experience

**Recommendation**: Option B (50% + AST)

### Decision 3: Template generation quality?

**Option A**: Rely solely on extraction
- ❌ Variable quality
- ❌ May generate broken code

**Option B**: Hybrid (baseline + extraction enhancement)
- ✅ Guaranteed valid baseline
- ✅ Enhanced with extracted patterns
- ✅ Manual review option

**Recommendation**: Option B (hybrid)

---

## Conclusion

**EPIC-001 is FEASIBLE** with the following modifications:

1. Make TASK-048 (Subagents.cc) optional
2. Lower confidence expectations for pattern detection
3. Add fallback strategies for all high-risk tasks
4. Use hybrid approach (hand-crafted + extraction) for template generation
5. Add validation checkpoints for generated code

**With these mitigations**: 85-90% success probability
**Without mitigations**: 60-70% success probability

**Recommendation**: ✅ **PROCEED with mitigations implemented**

---

**Created**: 2025-11-01
**Status**: ✅ **RISK ASSESSMENT COMPLETE**
**Action Required**: Implement mitigations before starting high-risk tasks
