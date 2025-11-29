# Template Removal Plan

**Plan Date**: 2025-11-08
**Related**: TASK-056 (Template Audit), TASK-060 (Template Removal Implementation)
**Status**: PROPOSED
**Approval Required**: Yes

---

## Executive Summary

Based on the comprehensive template audit (TASK-056), this plan outlines the removal of 2 low-quality templates and the deprecation strategy to minimize user impact.

**Templates Scheduled for Removal**:
1. **dotnet-aspnetcontroller** (Score: 6.5/10, Grade: C)
2. **default** (Score: 6.0/10, Grade: C)

**Rationale**: Both templates score below the 8.0/10 quality threshold and provide limited value compared to alternatives.

---

## Templates Scheduled for Removal

### 1. dotnet-aspnetcontroller (6.5/10)

**Current Status**:
- Path: `installer/global/templates/dotnet-aspnetcontroller/`
- Technology: .NET + ASP.NET Core Controllers + MVC pattern + ErrorOr
- Created: 2024-01-01 (estimated)
- Last Updated: 2025-11-08 (manifest.json added during audit)

**Removal Rationale**:
1. **Below Quality Threshold**: Scores 6.5/10 (below 8.0 minimum for reference templates)
2. **Pattern Redundancy**: Traditional MVC pattern less favored than modern alternatives
3. **Better Alternatives Available**:
   - `dotnet-fastendpoints`: Modern REPR pattern, vertical slices, FastEndpoints framework
   - `dotnet-minimalapi`: Lightweight .NET 8+ Minimal API, route groups, endpoint filters
4. **Confusing Proliferation**: 3 .NET API templates may overwhelm users
5. **Limited Differentiation**: ErrorOr pattern is also available in dotnet-fastendpoints

**User Impact Assessment**:
- **Estimated Current Usage**: LOW (traditional pattern, newer alternatives preferred)
- **Breaking Change**: Yes (template will no longer be available)
- **Migration Complexity**: LOW to MEDIUM (similar patterns, minimal code changes)

**Recommended Alternative**: **dotnet-fastendpoints**
- Similar layered architecture
- Modern REPR pattern (Request-Endpoint-Response)
- ErrorOr pattern included
- Better performance than traditional controllers
- More explicit request/response handling

---

### 2. default (6.0/10)

**Current Status**:
- Path: `installer/global/templates/default/`
- Technology: Language-agnostic
- Created: 2024-01-01 (estimated)
- Last Updated: 2025-11-08 (manifest.json added during audit)

**Removal Rationale**:
1. **Below Quality Threshold**: Scores 6.0/10 (lowest score, well below 8.0 minimum)
2. **Too Generic**: Provides minimal architectural guidance or patterns
3. **Limited Reference Value**: No specific technology stack or best practices
4. **Better User Experience**: Users benefit more from technology-specific templates
5. **Minimal Content**: Sparse CLAUDE.md, basic settings.json, no template files

**User Impact Assessment**:
- **Estimated Current Usage**: LOW (users likely choose technology-specific templates)
- **Breaking Change**: Yes (template will no longer be available)
- **Migration Complexity**: MINIMAL (users should choose appropriate stack template)

**Recommended Alternatives**: **Technology-Specific Templates**
- **Frontend**: react (7.5/10, improving to 8.5+/10)
- **Backend/AI**: python (7.5/10, improving to 8.5+/10)
- **Full-Stack**: fullstack (8.0/10)
- **Mobile**: maui-appshell (8.8/10) or maui-navigationpage (8.5/10)
- **Backend API**: typescript-api (7.2/10) or dotnet-fastendpoints (7.0/10)

---

## Templates to Keep (8 templates)

### High Quality - Reference Templates (3)
1. **maui-appshell** (8.8/10) - ✅ KEEP
2. **maui-navigationpage** (8.5/10) - ✅ KEEP
3. **fullstack** (8.0/10) - ✅ KEEP

### Medium Quality - Improvement Candidates (5)
4. **react** (7.5/10) - ✅ KEEP & IMPROVE
5. **python** (7.5/10) - ✅ KEEP & IMPROVE
6. **typescript-api** (7.2/10) - ✅ KEEP & IMPROVE
7. **dotnet-fastendpoints** (7.0/10) - ✅ KEEP & IMPROVE
8. **dotnet-minimalapi** (6.8/10) - ✅ KEEP & IMPROVE (borderline)

---

## Migration Paths

### From dotnet-aspnetcontroller → dotnet-fastendpoints

**Similarity Matrix**:
| Feature | dotnet-aspnetcontroller | dotnet-fastendpoints |
|---------|------------------------|----------------------|
| Error Handling | ErrorOr ✓ | ErrorOr ✓ |
| Layering | Controllers/Services/Repositories | Endpoints/Domain/Services/Repositories |
| DI | ✓ | ✓ |
| Testing | xUnit/NSubstitute ✓ | xUnit/NSubstitute ✓ |
| Pattern | MVC (Controller→Service→Repository) | REPR (Request→Endpoint→Response) |
| Routing | Attribute-based `[Route]` | FastEndpoints routing |
| Request/Response | Controller actions return IActionResult | Endpoints with typed requests/responses |

**Migration Steps**:
1. **Controllers → Endpoints**: Convert each controller action to a FastEndpoints endpoint
   ```csharp
   // Before (Controller)
   [HttpPost]
   public async Task<IActionResult> CreateUser([FromBody] CreateUserDto dto)

   // After (FastEndpoints)
   public class CreateUserEndpoint : Endpoint<CreateUserRequest, CreateUserResponse>
   ```

2. **Preserve Domain/Service/Repository layers**: No changes needed (same patterns)

3. **Update routing**: Replace attribute routing with FastEndpoints routing configuration

4. **Update DI registration**: Register endpoints instead of controllers

**Estimated Migration Effort**: 2-4 hours per medium-sized project (10-20 endpoints)

**Migration Guide Location**: `docs/guides/migrate-aspnetcontroller-to-fastendpoints.md` (to be created)

---

### From default → Technology-Specific Template

**Decision Tree**:
```
What are you building?
├─ Frontend web app → react
├─ Backend API
│  ├─ TypeScript → typescript-api
│  ├─ .NET
│  │  ├─ Modern, lightweight → dotnet-minimalapi
│  │  └─ Full-featured → dotnet-fastendpoints
│  └─ Python/AI → python
├─ Mobile app → maui-appshell or maui-navigationpage
└─ Full-stack → fullstack
```

**Migration Steps**:
1. **Identify project type**: Determine which technology stack fits your project
2. **Re-initialize**: Run `/agentic-init [template-name]` in new directory
3. **Copy custom code**: Manually copy any project-specific code from default template
4. **Adopt patterns**: Follow the technology-specific patterns in new template's CLAUDE.md

**Estimated Migration Effort**: 30 minutes to 2 hours (mostly one-time setup)

**Migration Guide Location**: `docs/guides/migrate-from-default-template.md` (to be created)

---

## Deprecation Timeline

### Phase 1: Announcement (Week 1) - 2025-11-11 to 2025-11-17

**Actions**:
- [ ] Add deprecation warning to dotnet-aspnetcontroller/CLAUDE.md
- [ ] Add deprecation warning to default/CLAUDE.md
- [ ] Update root CLAUDE.md with deprecation notice
- [ ] Create migration guides:
  - `docs/guides/migrate-aspnetcontroller-to-fastendpoints.md`
  - `docs/guides/migrate-from-default-template.md`
- [ ] Update template list in documentation
- [ ] Post announcement in project README.md (if applicable)

**User Communication**:
```markdown
## ⚠️ DEPRECATION NOTICE

This template (`dotnet-aspnetcontroller` / `default`) is scheduled for removal.

**Removal Date**: 2025-12-09 (Week 5)
**Reason**: Below quality threshold (scored 6.5/10, minimum 8.0 required)
**Alternative**: See migration guide at `docs/guides/migrate-*.md`

You can continue using this template during the deprecation period (4 weeks).
Please migrate to the recommended alternative before the removal date.
```

---

### Phase 2: Soft Deprecation (Weeks 2-3) - 2025-11-18 to 2025-12-01

**Actions**:
- [ ] Mark templates as `[DEPRECATED]` in template selection
- [ ] Add runtime warning when template is selected
- [ ] Monitor usage (if analytics available)
- [ ] Provide support for migration questions
- [ ] Continue maintaining templates (bug fixes only)

**User Communication**:
```bash
# When user tries to use deprecated template
$ /agentic-init dotnet-aspnetcontroller

⚠️ WARNING: 'dotnet-aspnetcontroller' is deprecated and will be removed on 2025-12-09.
   Please use 'dotnet-fastendpoints' instead.

   Migration guide: docs/guides/migrate-aspnetcontroller-to-fastendpoints.md

   Continue anyway? (y/N):
```

---

### Phase 3: Hard Deprecation (Week 4) - 2025-12-02 to 2025-12-08

**Actions**:
- [ ] Move templates to `.deprecated/` directory within installer/global/templates/
- [ ] Block new project creation with deprecated templates
- [ ] Allow existing projects to continue (no breaking changes to running code)
- [ ] Final migration reminder

**User Communication**:
```bash
# When user tries to use deprecated template
$ /agentic-init dotnet-aspnetcontroller

❌ ERROR: 'dotnet-aspnetcontroller' has been deprecated and is no longer available.

   Please use one of these alternatives:
   - dotnet-fastendpoints (recommended, modern REPR pattern)
   - dotnet-minimalapi (lightweight, .NET 8+ Minimal API)

   Migration guide: docs/guides/migrate-aspnetcontroller-to-fastendpoints.md
```

---

### Phase 4: Removal (Week 5+) - 2025-12-09 onwards

**Actions**:
- [ ] Remove templates from installer/global/templates/
- [ ] Archive in docs/archive/deprecated-templates/
- [ ] Update all documentation to remove references
- [ ] Update installer scripts (if applicable)
- [ ] Update tests that reference deprecated templates
- [ ] Create release notes documenting removal

**Archive Location**:
```
docs/archive/deprecated-templates/
├── dotnet-aspnetcontroller/
│   ├── CLAUDE.md
│   ├── manifest.json
│   ├── settings.json
│   ├── README-ARCHIVED.md (explains why archived, alternatives)
│   └── ... (original template files)
└── default/
    ├── CLAUDE.md
    ├── manifest.json
    ├── README-ARCHIVED.md
    └── ... (original template files)
```

---

## User Impact Assessment

### Impact by User Type

**New Users**:
- **Impact**: NONE (will use recommended templates)
- **Action**: None required

**Existing Users (dotnet-aspnetcontroller)**:
- **Impact**: LOW to MEDIUM
- **Affected**: Users who recently started projects with dotnet-aspnetcontroller
- **Action**: Follow migration guide to dotnet-fastendpoints
- **Support**: 4-week migration window + migration guide
- **Effort**: 2-4 hours per project

**Existing Users (default)**:
- **Impact**: MINIMAL
- **Affected**: Users who used generic default template
- **Action**: Choose appropriate technology-specific template for new projects
- **Support**: Decision tree + migration guides
- **Effort**: 30 minutes to 2 hours (one-time setup)

### Breaking Changes

**For New Projects**:
- ✅ No breaking changes (templates simply not available)
- ✅ Clear error messages with alternatives

**For Existing Projects**:
- ✅ No breaking changes (code continues to work)
- ✅ Projects already initialized are unaffected
- ⚠️ May not be able to reference deprecated template documentation

---

## Communication Strategy

### Channels

1. **In-Product Warnings**: Runtime deprecation warnings when selecting templates
2. **Documentation**: Updated CLAUDE.md, README.md in project root
3. **Migration Guides**: Step-by-step guides in `docs/guides/`
4. **Changelog**: Entry in project CHANGELOG.md (if exists)
5. **Release Notes**: Documented in release notes for version including removal

### Messaging Tone

- **Helpful, not apologetic**: Frame as quality improvement
- **Solution-focused**: Emphasize better alternatives
- **Supportive**: Provide clear migration paths and support
- **Transparent**: Explain quality scoring and rationale

### Sample Message

```markdown
## Template Quality Improvement Initiative

We've completed a comprehensive audit of all Taskwright templates and identified
opportunities to improve template quality and reduce user confusion.

**What's Changing**:
- Removing 2 low-quality templates: `dotnet-aspnetcontroller` and `default`
- Focusing on 8 high-quality templates with ongoing improvements
- Keeping 3 reference templates as best-in-class examples

**Why**:
- `dotnet-aspnetcontroller` (6.5/10): Modern alternatives (dotnet-fastendpoints,
  dotnet-minimalapi) provide better patterns
- `default` (6.0/10): Generic template provides minimal value; technology-specific
  templates offer better guidance

**For Existing Users**:
- **4-week migration window**: Continue using during deprecation period
- **Migration guides**: Step-by-step guides available
- **Support**: Questions welcome during migration

**For New Users**:
- Choose from our curated selection of high-quality templates
- Better patterns, clearer guidance, higher quality
```

---

## Rollback Plan

### Triggers for Rollback

Rollback if:
1. **High user impact**: >50% of users affected negatively
2. **Critical migration issues**: Migration path doesn't work as documented
3. **Lost functionality**: Alternative templates missing critical features
4. **Community pushback**: Strong negative feedback from users

### Rollback Procedure

**If triggered during Phase 1-2** (Weeks 1-3):
1. Remove deprecation warnings
2. Keep templates available
3. Reassess removal plan
4. Fix identified issues

**If triggered during Phase 3** (Week 4):
1. Move templates back from `.deprecated/` to main directory
2. Remove blocking warnings
3. Reassess removal plan
4. Improve migration guides

**If triggered during Phase 4** (Week 5+):
1. Restore from archive: docs/archive/deprecated-templates/ → installer/global/templates/
2. Update documentation
3. Announce restoration
4. Create action plan to address root cause

### Risk Mitigation

**Proactive Measures**:
- 4-week deprecation period (allows time to identify issues)
- Comprehensive migration guides (reduces migration friction)
- Clear communication (sets expectations)
- Archive preservation (enables quick rollback)

**Monitoring**:
- Track usage during deprecation period (if possible)
- Monitor for migration-related issues
- Solicit user feedback

---

## Dependencies

### Blocking Dependencies
None - can proceed immediately after TASK-056 approval

### Related Tasks

**Prerequisite**:
- ✅ TASK-056: Template Audit (COMPLETE)

**Dependent**:
- TASK-060: Remove Low-Quality Templates (implementation)
- TASK-056B: Validate Created Manifests (recommended before removal)
- TASK-056C: Enhance React Template (improves alternatives)
- TASK-056D: Enhance Python Template (improves alternatives)

---

## Success Metrics

### Quantitative

**Before Removal**:
- Total templates: 10
- High-quality templates (8+/10): 3 (30%)
- Low-quality templates (<7/10): 2 (20%)

**After Removal**:
- Total templates: 8
- High-quality templates (8+/10): 3 (37.5%)
- Low-quality templates (<7/10): 0 (0%)

**User Metrics** (if measurable):
- Migration completion rate: Target >80%
- User satisfaction: Maintain or improve
- Support requests: Minimize during migration

### Qualitative

**Success Indicators**:
- ✅ Templates meet quality threshold (8+/10)
- ✅ Clear template selection (no confusion from redundant options)
- ✅ Users successfully migrate with guides
- ✅ No rollback required
- ✅ Improved template discoverability
- ✅ Better user onboarding experience

**Failure Indicators**:
- ❌ High support burden from migration issues
- ❌ Users unable to migrate successfully
- ❌ Loss of critical functionality
- ❌ Negative community feedback

---

## Approval Requirements

**Approvers**:
- [ ] Product Owner / Project Maintainer
- [ ] Technical Lead
- [ ] (Optional) Community / User Representative

**Approval Criteria**:
1. Rationale for removal is sound (quality threshold + redundancy)
2. Migration paths are clear and documented
3. User impact is acceptable (minimal disruption)
4. Timeline provides adequate migration window (4 weeks)
5. Rollback plan is in place

**Approval Deadline**: Before 2025-11-11 (start of Phase 1)

---

## Implementation Tasks

### Documentation Tasks
- [ ] Create `docs/guides/migrate-aspnetcontroller-to-fastendpoints.md`
- [ ] Create `docs/guides/migrate-from-default-template.md`
- [ ] Update `CLAUDE.md` with deprecation notice
- [ ] Update `README.md` (if applicable) with announcement
- [ ] Update template selection documentation

### Code Tasks
- [ ] Add deprecation warnings to templates (Phase 1)
- [ ] Add runtime warnings to template selection (Phase 2)
- [ ] Move templates to `.deprecated/` (Phase 3)
- [ ] Remove templates from codebase (Phase 4)
- [ ] Archive templates in docs/archive/deprecated-templates/ (Phase 4)
- [ ] Update installer scripts (if needed)
- [ ] Update tests referencing deprecated templates

### Process Tasks
- [ ] Create TASK-060 for implementation
- [ ] Schedule deprecation phases
- [ ] Monitor user feedback during deprecation
- [ ] Prepare rollback procedure (just in case)

---

## Conclusion

This removal plan provides a structured, user-friendly approach to removing 2 low-quality templates while minimizing disruption:

**Strengths**:
- ✅ Clear rationale (quality threshold, redundancy)
- ✅ Adequate migration window (4 weeks)
- ✅ Comprehensive migration guides
- ✅ Phased approach (soft → hard deprecation → removal)
- ✅ Rollback plan in place
- ✅ Improves overall template quality (removes all templates <7/10)

**User Impact**:
- Minimal: Only 2 low-usage templates affected
- Supported: Clear migration paths and guides
- Beneficial: Users gain access to better alternatives

**Outcome**:
- 8 high-quality templates remain
- 37.5% are reference-quality (8+/10), up from 30%
- 0% are below standard (<7/10), down from 20%
- Clearer template selection for users
- Higher quality baseline for all templates

---

**Plan Status**: ✅ READY FOR APPROVAL
**Approval Deadline**: 2025-11-11
**Implementation Task**: TASK-060
