# GuardKit Content Strategy & Ideas

## Overview

This document outlines content ideas for promoting GuardKit and establishing Feature Plan Development (FPD) as a recognised methodology. The focus is on demonstrating practical value through comparisons, tutorials, and thought leadership.

---

## Content Philosophy

### Core Messages

1. **"Plan Features. Build Faster."** - The tagline should appear consistently
2. **Natural workflow** - GuardKit mirrors how developers actually think
3. **One command** - The simplicity of `/feature-plan` vs multi-step alternatives
4. **Parallel execution** - Unique wave analysis capability
5. **Quality without ceremony** - Built-in gates, not bolted-on process

### Tone Guidelines

- Pragmatic, not preachy
- Show don't tell (demos over manifestos)
- Acknowledge competitors' strengths honestly
- Focus on "when to use" not "why we're better"

---

## Blog Post Ideas

### Comparison/Positioning Posts

#### 1. "Feature Plan Development: A Lighter Alternative to Spec-Driven Development"
**Angle:** SDD (SpecKit, etc.) requires you to write specifications. FPD generates them from intent.

**Key points:**
- What SDD gets right (structure, documentation)
- Where it creates friction (upfront spec writing)
- How FPD inverts the model
- When to use each approach

**Hook:** "What if you could describe what you want to build and have the spec generated for you?"

---

#### 2. "GuardKit vs TaskMaster: Features vs Tasks"
**Angle:** Direct, honest comparison. Not attacking TaskMaster, but showing different use cases.

**Structure:**
- What TaskMaster does well (PRD parsing, task management)
- What it doesn't do (parallel analysis, quality gates, feature-level planning)
- Side-by-side demo of the same feature
- "Choose TaskMaster when... Choose GuardKit when..."

**Hook:** "TaskMaster has 15,000 stars. Here's why we built something different."

---

#### 3. "Why I Stopped Using BMAD (And What I Use Instead)"
**Angle:** Personal journey from complexity to simplicity.

**Structure:**
- The appeal of BMAD (full team simulation)
- Where it broke down (overhead, context switching)
- The search for something lighter
- How FPD solved the problem

**Hook:** "19 agents sounded amazing until I spent more time managing them than building."

---

#### 4. "The Problem with Spec-First Development in 2025"
**Angle:** Thought leadership on why specs-before-code doesn't work for everyone.

**Key points:**
- Specs assume you know what you're building
- Iteration is faster than specification
- AI can generate specs from intent
- When specs ARE valuable (contracts, APIs, compliance)

**Hook:** "We've been writing specs for 50 years. Maybe it's time to generate them instead."

---

### Tutorial/How-To Posts

#### 5. "From Feature Idea to Implementation Guide in 60 Seconds"
**Angle:** Pure demo of the `/feature-plan` workflow.

**Structure:**
- The command
- What gets generated
- How to read the implementation guide
- Starting the first wave

**Format:** Mostly screenshots/code blocks, minimal text.

---

#### 6. "Parallel Feature Development with GuardKit and Conductor"
**Angle:** Deep dive into wave analysis and worktree-based parallel execution.

**Key points:**
- Why parallel execution matters
- How GuardKit detects parallel-safe tasks
- Setting up Conductor worktrees
- Merging waves safely

**Hook:** "Stop doing tasks sequentially. Here's how to 3x your throughput."

---

#### 7. "Adding Quality Gates Without Adding Process"
**Angle:** The [A]/[R]/[I]/[C] decision flow and why it works.

**Key points:**
- The problem with optional quality steps
- How GuardKit embeds gates in the workflow
- When each checkpoint triggers
- Customising gate behaviour

**Hook:** "Quality gates that developers actually use (because they can't skip them)."

---

### Thought Leadership Posts

#### 8. "The Unit of AI-Assisted Development Should Be Features, Not Tasks"
**Angle:** Philosophical piece on why features are the right abstraction.

**Key points:**
- Tasks are too granular for planning
- Specs are too abstract for action
- Features are what users and developers both understand
- How FPD bridges planning and execution

**Hook:** "We've been optimising the wrong thing."

---

#### 9. "What Agile Got Wrong About AI-Assisted Development"
**Angle:** Provocative take on why simulating Agile ceremonies (BMAD) misses the point.

**Key points:**
- Agile was designed for human coordination
- AI doesn't need standups or sprint planning
- What AI DOES need (clear scope, quality checks, parallel paths)
- Post-Agile patterns for AI-native development

**Hook:** "Your AI agent doesn't need a Scrum Master."

---

#### 10. "The Spec-Driven Development Spectrum"
**Angle:** Position the different approaches on a spectrum, with GuardKit in a specific niche.

**Spectrum:**
- Heavy (BMAD) → Medium (SpecKit) → Light (OpenSpec) → Lightest (GuardKit)
- When each is appropriate
- Honest assessment of trade-offs

**Hook:** "There's no 'best' approach—only the right one for your situation."

---

## Video Content Ideas

### Short-Form (YouTube Shorts, TikTok, LinkedIn)

#### 1. "One Command Feature Planning" (30-60 sec)
- Type `/feature-plan "add dark mode"`
- Show the generated structure
- End with "That's it. Start building."

#### 2. "GuardKit vs TaskMaster in 60 Seconds"
- Split screen comparison
- TaskMaster: Write PRD → Parse → Navigate tasks
- GuardKit: One command → Done
- "Which would you choose?"

#### 3. "The Problem with Spec-First" (45 sec)
- Pain point: "Write a spec before you code"
- Counter: "What if you don't know the spec yet?"
- Solution: "Describe intent, generate the spec"

---

### Long-Form (YouTube, 10-20 min)

#### 4. "Complete GuardKit Walkthrough: Feature to Deployment"
**Structure:**
- 0:00 - Intro (the problem)
- 2:00 - `/feature-plan` demo
- 5:00 - Understanding the implementation guide
- 8:00 - Working through Wave 1
- 12:00 - Quality gates in action
- 15:00 - Merging and completion
- 18:00 - Recap and when to use

---

#### 5. "I Tried BMAD, SpecKit, TaskMaster, and GuardKit"
**Structure:**
- Same feature implemented with each tool
- Honest pros/cons for each
- Time comparison
- Final recommendation matrix

**Angle:** Fair, balanced, educational. Not a hit piece.

---

#### 6. "Feature Plan Development Explained"
**Structure:**
- What is FPD?
- How it differs from SDD
- The philosophy behind it
- Live demo
- Q&A format with common objections

---

### Live/Interactive

#### 7. "Build With Me: Feature Planning Session"
- Live stream building a real feature
- Audience suggests the feature
- Walk through the entire FPD workflow
- Answer questions in real-time

---

## Social Media Strategy

### Twitter/X Thread Ideas

1. **"Thread: Why I built GuardKit after trying every SDD tool"**
   - Personal story format
   - 10-15 tweets
   - End with link to demo

2. **"The 5 things every AI development tool gets wrong"**
   - Listicle format
   - Each point links to how GuardKit solves it

3. **"Unpopular opinion: Specs are a bottleneck, not a feature"**
   - Provocative take
   - Expect engagement/debate
   - Link to longer blog post

### LinkedIn Strategy

- **Audience:** CTOs, engineering managers, senior developers
- **Tone:** Professional, focused on outcomes
- **Content:** 
  - "How we reduced feature planning time by 70%"
  - Case studies once available
  - Thought leadership on AI-assisted development

### Reddit/HackerNews

- **Don't:** Shill or self-promote aggressively
- **Do:** Answer questions in relevant threads
- **Do:** Share comparison posts as "here's what I found"
- **Target subreddits:** r/ClaudeAI, r/CursorAI, r/programming, r/ExperiencedDevs

---

## Launch Content Sequence

### Week 1: Foundation
- [ ] Publish "Feature Plan Development Philosophy" on README
- [ ] Create comparison table (GuardKit vs competitors)
- [ ] Record 60-second demo video

### Week 2: Awareness
- [ ] Blog post: "Feature Plan Development: A Lighter Alternative"
- [ ] Twitter thread announcing GuardKit
- [ ] Submit to relevant GitHub awesome lists

### Week 3: Education
- [ ] Tutorial: "From Feature Idea to Implementation Guide"
- [ ] Long-form YouTube walkthrough
- [ ] Answer questions on Reddit/HN

### Week 4: Comparison
- [ ] Blog post: "GuardKit vs TaskMaster"
- [ ] Side-by-side video comparison
- [ ] Engage with TaskMaster community constructively

### Ongoing
- [ ] Weekly tip tweets
- [ ] Monthly case study (when users adopt)
- [ ] Respond to issues/discussions publicly

---

## Metrics to Track

### Awareness
- GitHub stars/week
- Website traffic
- Social mentions

### Engagement
- Issues opened
- Documentation page views
- Video completion rates

### Adoption
- Installs (if tracking available)
- Projects using GuardKit (search GitHub)
- Community contributions

---

## Content Calendar Template

| Week | Blog Post | Video | Social | Community |
|------|-----------|-------|--------|-----------|
| 1 | Philosophy | 60s demo | Announcement thread | - |
| 2 | Comparison intro | - | Daily tips | Answer Qs |
| 3 | Tutorial | Full walkthrough | Share video | Reddit post |
| 4 | vs TaskMaster | Comparison | Engage critics | HN if ready |

---

## Key Talking Points Reference

### When asked "How is this different from TaskMaster?"
> "TaskMaster is great for breaking down PRDs into tasks. GuardKit works at the feature level—you describe what you want, and it generates the plan, the tasks, the parallel execution waves, and tells you how to implement each piece. It's features, not just tasks."

### When asked "Why not just use SpecKit?"
> "SpecKit asks you to write specifications before you can start. GuardKit inverts that—you describe your intent, and the specification gets generated. If you already know exactly what you're building, SpecKit is great. If you want to move faster, try GuardKit."

### When asked "Isn't this just another AI dev tool?"
> "Most tools focus on either specs (write docs first) or tasks (manage a backlog). GuardKit focuses on features—the natural unit of what developers actually build. One command, parallel execution awareness, and quality gates that don't slow you down."

---

## Notes on Building Following

### Reality Check
- Starting from zero is hard
- Stars ≠ quality, but they do = visibility
- Consistency matters more than virality
- One genuine adopter is worth 100 stars

### What Actually Works
1. **Solve a real problem** - GuardKit does this
2. **Show, don't tell** - Demos over documentation
3. **Be where your users are** - Claude Code users, AI-native devs
4. **Help before promoting** - Answer questions, contribute to discussions
5. **Let users be advocates** - Make it easy to share wins

### What Doesn't Work
- Fake enthusiasm
- Attacking competitors
- Spamming every forum
- Claiming to be "the best"
- Ignoring feedback

---

## Appendix: Competitor Content Analysis

### TaskMaster's Content Strategy
- Heavy YouTube presence (tutorials, "90% fewer errors")
- Reddit engagement (helpful, not pushy)
- Simple value prop repeated everywhere
- Fast iteration on feedback

**Lesson:** Simple message, repeated consistently.

### BMAD's Content Strategy
- Medium articles (thought leadership)
- Detailed documentation
- Enterprise-focused messaging
- Expansion packs for different audiences

**Lesson:** Go deep on one audience rather than broad.

### SpecKit's Content Strategy
- GitHub brand does the marketing
- Official blog posts with high production value
- Integration with existing GitHub content

**Lesson:** Leverage existing platforms/brands where possible.
