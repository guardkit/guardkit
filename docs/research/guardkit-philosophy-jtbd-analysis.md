# GuardKit Philosophy: Jobs to Be Done Analysis

## The Real-World Problem with Spec-Driven Development

### What SDD Tools Assume

SpecKit, BMAD, and similar tools assume:
- Someone writes detailed specs before development begins
- That person (Product Owner, BA, PM) is available and engaged
- The team has time for specification ceremonies
- Specs are valuable enough to justify the upfront investment

### What Actually Happens in Most Teams

Reality for the majority of development teams:
- Product owner gives you a Jira ticket with three bullet points
- "Just make it work like the competitor's thing"
- Requirements arrive as Slack messages or verbal conversations
- Specs get written *after* the code ships (if ever)
- Getting PO time for detailed specification is a process challenge
- Teams don't usually create specifications to that extent

### GuardKit's Response

GuardKit doesn't fight that reality—it works with it:
- You describe intent ("implement dark mode")
- The tool generates the structure
- The "spec" emerges from the planning process rather than gating it
- No upfront ceremony required

---

## What "AI-Native" Actually Means

The term "AI-native" gets thrown around loosely. For GuardKit, it has specific meaning:

### AI Does the Tedious Work
- Decomposition (breaking features into tasks)
- Parallel analysis (identifying concurrent-safe work)
- Documentation generation (implementation guides, READMEs)
- Pattern detection (implementation mode tagging)

### Humans Make the Decisions
- Approve / Revise / Implement / Cancel checkpoints
- Scope validation
- Risk assessment
- Final quality judgment

### The Workflow Assumes AI
Rather than bolting AI onto a human process, the workflow is designed for how AI actually works:
- Generate structure quickly
- Get human validation at key points
- Execute with built-in quality gates
- Iterate based on feedback

### Contrast with Competitors

**BMAD:** Simulates a human Agile team *with* AI
- 19 agents playing human roles (PM, Architect, Scrum Master, QA...)
- Recreates human ceremonies digitally
- AI performs tasks humans would do

**GuardKit:** Designed for how AI *actually* works
- AI generates, humans validate
- No ceremony simulation
- Quality gates are checkpoints, not role-playing

---

## Jobs to Be Done Analysis

### The JTBD Framework

Clayton Christensen's "Jobs to Be Done" theory states:
> People don't buy products—they hire them to do a job.

The classic example: "People don't want a quarter-inch drill, they want a quarter-inch hole."

Applied to development tools: **What are you actually trying to do?**

### How Competitors Frame the Job

| Tool | Question Asked |
|------|----------------|
| **BMAD** | "How do we run Agile with AI?" |
| **SpecKit** | "How do we write specs with AI?" |
| **TaskMaster** | "How do we manage tasks with AI?" |
| **OpenSpec** | "How do we manage spec changes with AI?" |
| **GuardKit** | "What are you actually trying to do?" |

The first four are **process questions**—they're about doing an existing process with AI assistance.

GuardKit asks a different question entirely. And the answer is simply:

> "Build this feature."

That's it. Not:
- "Help me write specs" (that's a means, not an end)
- "Help me manage tasks" (that's coordination, not the goal)
- "Help me run Agile ceremonies" (that's process, not outcome)

The job is **building the feature**. Everything else is in service of that.

### The JTBD Insight

**BMAD, SpecKit, etc. have digitised existing manual processes:**
- Manual process: Agile team with ceremonies → BMAD: AI agents playing those roles
- Manual process: Write specs before coding → SpecKit: AI-assisted spec writing
- Manual process: Break PRD into tasks → TaskMaster: AI-powered task decomposition

**GuardKit takes a different approach:**
- Skip the process question entirely
- Ask: "What's the actual outcome you want?"
- Answer: "I want to build a feature"
- Solution: One command that generates everything needed to build the feature

### Why This Matters

When you digitise an existing process, you inherit its constraints:
- Specs-first means you need specs (process constraint)
- Agile ceremonies mean you need roles (organisational constraint)
- PRD parsing means you need PRDs (documentation constraint)

When you focus on the job, you can eliminate unnecessary steps:
- No specs required—intent is enough
- No role simulation—just generation and validation
- No PRD—describe what you want to build

---

## The Spectrum of Automation

### Level 1: Tool Enhancement
"Make the existing tool faster"
- Example: AI autocomplete in IDEs
- The process is unchanged, just accelerated

### Level 2: Process Digitisation
"Make the existing process run with AI"
- Example: BMAD (Agile team → AI agents)
- Example: SpecKit (spec writing → AI-assisted specs)
- The process is preserved, participants are replaced

### Level 3: Job Reimagination
"Rethink what we're actually trying to accomplish"
- Example: GuardKit
- The process is eliminated or transformed
- Only the outcome matters

**GuardKit operates at Level 3.**

---

## Implications for Positioning

### Don't Compete on Process
- Don't say "better specs than SpecKit"
- Don't say "simpler than BMAD"
- These comparisons accept the process framing

### Compete on Outcome
- "Build features faster"
- "From idea to implementation guide in 60 seconds"
- "Plan features, not processes"

### The Messaging Shift

| Process-Focused (Competitors) | Outcome-Focused (GuardKit) |
|------------------------------|---------------------------|
| "Write better specifications" | "Build what you're imagining" |
| "Manage tasks efficiently" | "Ship features faster" |
| "Run AI Agile teams" | "Plan once, build parallel" |
| "Document requirements" | "Describe intent, get structure" |

---

## Validation Questions

To test this JTBD framing, ask developers:

1. "When you start a new feature, what do you actually want?"
   - Expected: "To build it" / "To ship it" / "To get it done"
   - Not: "To write a spec" / "To create tasks" / "To run ceremonies"

2. "What's the most annoying part of starting a feature?"
   - Expected: "Figuring out where to start" / "Breaking it down" / "Knowing what can be parallel"
   - Not: "My spec template is wrong" / "My Agile board is messy"

3. "If you could skip one thing, what would it be?"
   - Expected: "The planning overhead" / "The documentation ceremony"
   - Not: "I wish I had MORE process"

---

## Summary

### The Insight

BMAD and similar tools have digitised existing manual processes—they've made AI perform the roles humans played in traditional development workflows.

GuardKit takes a Jobs to Be Done approach: rather than asking "how do we do this process with AI?", it asks "what are you actually trying to do?" and builds directly toward that outcome.

### The Job

**"I want to build this feature."**

Everything in GuardKit—the `/feature-plan` command, the automatic decomposition, the wave analysis, the implementation guides—serves that single job.

### The Tagline (Revisited)

**"Plan Features. Build Faster."**

This is outcome language, not process language. It describes the job, not the method.

---

## Related Reading

- Clayton Christensen, "Competing Against Luck" (JTBD theory)
- Des Traynor (Intercom), "Know Your Customers' Jobs to Be Done"
- Alan Klement, "When Coffee and Kale Compete" (JTBD practitioner guide)
