# KartLog Demo: Feature Suggestions for GuardKit Testing

**Date**: 2025-05-30
**Purpose**: Define compelling features to implement in forked kartlog repo as "show me the code" demos
**Source Repo**: https://github.com/ColinEberhardt/kartlog
**Live Site**: https://colineberhardt.github.io/kartlog/

---

## Overview

KartLog is an excellent candidate for GuardKit demonstrations because:

1. **Real-world complexity** - Not a toy app; has auth, database, AI integration
2. **Different tech stack** - Svelte + Firebase (tests GuardKit beyond built-in templates)
3. **Domain-specific logic** - Karting data has real business rules CTOs will recognize
4. **Active development** - Colin already uses spec-driven development manually
5. **Clear extension points** - Obvious features missing that make sense to add

### Current Tech Stack
- **Frontend**: Svelte (not React - good for demonstrating GuardKit's flexibility)
- **Backend**: Firebase (Firestore + Auth)
- **Build**: Vite
- **AI**: GPT-4 chat assistant with function calling
- **Auth**: Email/password + Google OAuth via Firebase

### Existing Features
- Equipment Management (tyres, engines, chassis)
- Session Logging (lap times, setup, race results)
- Circuit/Track Management
- AI Chat for tyre inventory queries
- CSV Import

---

## Recommended Demo Strategy

### Fork Structure
```
guardkit/kartlog-demos/
├── README.md              # Overview explaining the demo purpose
├── DEMO.md                # Exact prompts/commands used with GuardKit
├── main branch            # Production-ready with all features implemented
├── starter branch         # Fork point before GuardKit features
└── feature branches       # Each feature as separate branch for comparison
    ├── feature/weather-conditions
    ├── feature/lap-time-charts
    └── feature/session-comparison
```

### Branch Strategy
- **starter**: Clean fork, ready for "pick up where we left off" demos
- **main**: All features implemented, passing tests, production quality
- **Tagged checkpoints**: 
  - `v0.0.0-starter` - Initial fork state
  - `v0.1.0-weather` - After weather feature
  - `v0.2.0-charts` - After charts feature
  - `v1.0.0-complete` - All demos complete

---

## Feature Suggestions

### Tier 1: Quick Win (2-4 hours each)
*Good for rapid demos, shows GuardKit working end-to-end*

#### 1. Weather Conditions Tracking ⭐ RECOMMENDED FIRST
**Why this feature**: Weather directly affects lap times in karting. Temperature, humidity, and track conditions change grip levels. This is domain knowledge that skeptical CTOs will recognize as "real" not "AI slop."

**Scope**:
- Add weather fields to session form (temperature, humidity, conditions dropdown)
- Store weather data in Firestore with existing session documents
- Display weather in session list and detail views
- Update Firestore security rules

**Technical touches that signal production quality**:
- Input validation (temperature ranges, required fields)
- Responsive design for trackside mobile use
- Weather condition icons/badges
- Proper TypeScript/JSDoc types

**Demo value**: Shows GuardKit handling form extensions, database schema changes, and UI updates in a coordinated way.

---

#### 2. Personal Best Highlighting
**Why this feature**: Every racer wants to know their PB. Automatic detection shows business logic generation.

**Scope**:
- Calculate PB per circuit from existing lap data
- Highlight sessions where PB was set
- Show PB badge on session cards
- Add "PB History" view showing progression

**Technical touches**:
- Efficient queries (don't load all sessions to find PB)
- Handle edge cases (first session, tied times)
- Celebration animation when PB set
- Firestore indexes for performance

**Demo value**: Shows GuardKit generating domain-specific business logic, not just CRUD.

---

#### 3. Dark Mode
**Why this feature**: Universal web feature, touches many components, shows GuardKit handling cross-cutting concerns.

**Scope**:
- CSS custom properties for theming
- Theme toggle in navigation
- Persist preference in localStorage
- System preference detection

**Technical touches**:
- Smooth transitions between themes
- Proper contrast ratios (WCAG AA)
- Theme-aware charts/graphs
- No flash on page load

**Demo value**: Shows GuardKit making coordinated changes across the entire UI layer.

---

### Tier 2: Substantial Features (4-8 hours each)
*Good for demonstrating GuardKit on meaty features*

#### 4. Lap Time Charts & Analytics ⭐ RECOMMENDED
**Why this feature**: Visualization is where AI-generated code often fails. Getting charts right requires understanding data structures, library APIs, and UX.

**Scope**:
- Session lap time chart (line chart showing consistency)
- Session comparison chart (overlay two sessions)
- Circuit performance over time (trend line)
- Responsive charts for mobile

**Technical implementation**:
- Chart.js or D3 integration
- Lazy loading for performance
- Touch-friendly tooltips
- Export chart as image

**Production signals**:
- Proper loading states
- Empty state handling
- Axis labels and legends
- Color accessibility

**Demo value**: Charting is a common "show me the code" test because bad implementations are immediately visible. This proves GuardKit produces usable visualization code.

---

#### 5. Session Comparison View
**Why this feature**: Real analytical feature that racers would actually use to understand what changed between good and bad sessions.

**Scope**:
- Select two sessions to compare
- Side-by-side layout showing:
  - Weather conditions diff
  - Equipment diff (different tyres? different engine?)
  - Lap time comparison chart
  - Setup differences highlighted

**Technical implementation**:
- URL-based state for shareable comparisons
- Responsive layout (stack on mobile)
- Difference highlighting algorithm
- "What changed?" summary

**Demo value**: Complex UI with multiple data sources, conditional rendering, and user state management.

---

#### 6. Tyre Wear Tracking & Predictions
**Why this feature**: Domain-specific feature that demonstrates AI understanding of the problem space, not just generating generic code.

**Scope**:
- Track sessions per tyre
- Calculate estimated remaining life
- Warning indicators when tyres near end-of-life
- Tyre cost-per-session analytics

**Technical implementation**:
- Derived fields in Firestore (or computed on read)
- Configurable wear thresholds per tyre compound
- Notification/badge system
- Historical wear data

**Demo value**: Shows GuardKit can handle domain modeling and derived business logic.

---

### Tier 3: Impressive Features (8+ hours)
*For demonstrating GuardKit on architectural work*

#### 7. Offline Support (PWA)
**Why this feature**: Karting circuits often have poor connectivity. Making the app work offline then sync is a real user need that requires architectural thinking.

**Scope**:
- Service worker for offline caching
- IndexedDB for local data storage
- Sync queue when back online
- Conflict resolution strategy
- PWA manifest for installability

**Technical implementation**:
- Workbox for service worker
- Optimistic UI updates
- Sync status indicator
- Proper error handling for conflicts

**Production signals**:
- Background sync API
- Proper cache invalidation
- Network status detection
- Graceful degradation

**Demo value**: This is a significant architectural feature. Successfully implementing offline support demonstrates GuardKit can handle complex, cross-cutting concerns.

---

#### 8. Export Session Report to PDF
**Why this feature**: Common enterprise feature, demonstrates file generation and formatting.

**Scope**:
- Generate PDF report for single session
- Include lap chart, weather, equipment, notes
- Professional formatting with branding
- Download or share options

**Technical implementation**:
- Client-side PDF generation (jsPDF or pdfmake)
- Chart embedding in PDF
- Print stylesheet fallback
- Accessibility (screen reader announcement)

**Demo value**: File generation is often poorly implemented by AI. Good PDF output proves quality.

---

## Recommended Demo Sequence

For maximum impact on LinkedIn "show me the code" skeptics:

### Phase 1: Foundation (Do First)
1. **Weather Conditions** - Quick win, domain-relevant, shows E2E flow
2. **Dark Mode** - Visual impact, touches whole codebase

### Phase 2: Substance
3. **Lap Time Charts** - Visualization test, immediately visible quality
4. **Personal Bests** - Business logic, domain modeling

### Phase 3: Impressive (If Time)
5. **Session Comparison** - Complex UI, real analytical value
6. **Offline Support** - Architectural proof

---

## README Template for Demo Repo

```markdown
# KartLog + GuardKit Demo

> Real features, real code quality, no AI slop.

This repository demonstrates [GuardKit](https://github.com/guardkit/guardkit) 
implementing production-ready features in an existing Svelte + Firebase codebase.

## What This Proves

GuardKit isn't just for greenfield projects. This demo shows:

- ✅ Working with existing codebases (Svelte, not our built-in templates)
- ✅ Domain-specific features (karting business logic)
- ✅ Production patterns (error handling, validation, accessibility)
- ✅ Cross-cutting concerns (dark mode, offline support)

## Try It Yourself

```bash
# Clone and checkout starter branch
git clone https://github.com/guardkit/kartlog-demos
cd kartlog-demos
git checkout starter

# See what we started with
npm install && npm run dev

# Now use GuardKit to implement features
guardkit task-create "Add weather conditions to session tracking"
guardkit task-work TASK-001
```

## Features Implemented

| Feature | Branch | LOC Changed | Test Coverage | Time |
|---------|--------|-------------|---------------|------|
| Weather Conditions | `feature/weather` | ~450 | 87% | 2.5h |
| Lap Time Charts | `feature/charts` | ~680 | 82% | 4h |
| Dark Mode | `feature/dark-mode` | ~320 | 91% | 2h |
| Personal Bests | `feature/personal-bests` | ~380 | 89% | 3h |

## The Prompts We Used

See [DEMO.md](./DEMO.md) for the exact GuardKit commands and prompts used
for each feature.

## Quality Scorecard

```
Overall Quality: 8.7/10

✅ Type safety: Full TypeScript/JSDoc annotations
✅ Test coverage: 86% average across features
✅ Accessibility: WCAG AA compliant
✅ Mobile: Responsive, tested on iOS Safari
✅ Error handling: Graceful degradation, user feedback
✅ Documentation: Inline comments explain "why"
```

## Compare Before/After

```bash
# See the starter state
git checkout starter
npm run dev

# See the finished state  
git checkout main
npm run dev

# Compare specific feature
git diff starter..feature/weather -- src/
```
```

---

## Quality Signals to Include

For every feature implemented, ensure these production signals are present:

### Code Quality
- [ ] TypeScript/JSDoc types for all new code
- [ ] ESLint passing with zero warnings
- [ ] Consistent code style with existing codebase
- [ ] No console.log statements
- [ ] Proper error boundaries

### Testing
- [ ] Unit tests for business logic
- [ ] Integration tests for Firestore operations
- [ ] Component tests for UI changes
- [ ] 80%+ coverage for new code

### UX Quality
- [ ] Loading states for async operations
- [ ] Error states with recovery options
- [ ] Empty states with helpful messages
- [ ] Mobile-responsive design
- [ ] Keyboard navigation support

### Documentation
- [ ] Inline comments explaining non-obvious logic
- [ ] Updated README if adding new features
- [ ] Firestore security rules documented
- [ ] API/function JSDoc comments

---

## Integration with Existing Demo Tasks

This demo complements the existing backlog:

| Existing Task | KartLog Demo Role |
|--------------|-------------------|
| TASK-069 (Core Templates) | Different - tests non-template codebase |
| TASK-070 (Custom Template) | Could extract kartlog patterns as template |
| TASK-071 (Greenfield) | Different - this is brownfield |
| TASK-072 (E2E Workflow) | Shows full workflow on real codebase |
| TASK-073 (Demo Repos) | KartLog becomes a featured example |

---

## Next Steps

1. **Fork kartlog** to `guardkit` org
2. **Create starter branch** from current main
3. **Implement Weather Conditions** as first feature
4. **Document prompts** used in DEMO.md
5. **Measure and record** quality metrics
6. **Repeat** for remaining features
7. **Write LinkedIn post** with repo link and screenshots

---

## Success Criteria for "Show Me The Code" Audience

When CTOs and senior devs look at this demo, they should see:

1. **Real complexity** - Not a todo app or counter
2. **Domain awareness** - Features that make sense for karting
3. **Production patterns** - The boring stuff that matters (error handling, validation, accessibility)
4. **Clean diffs** - Changes that are focused and reviewable
5. **Test coverage** - Proof the code actually works
6. **Documentation** - Comments explaining intent, not just syntax

The goal is NOT to show GuardKit is fast. The goal is to show GuardKit produces code you'd actually ship.
