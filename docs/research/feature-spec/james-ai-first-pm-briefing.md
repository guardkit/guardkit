# Becoming an AI-First Product Manager: A Practical Guide

**For**: James Guest
**From**: Rich Woollcott
**Date**: February 2026

---

## The Big Idea

Every useful command in GuardKit and RequireKit started the same way: I used Claude Code for real work, noticed I was repeating the same patterns, and then formalised those patterns into reusable commands and skills. The `/task-review` command, for example, came from a workflow I kept doing manually — using plan mode to analyse a problem area, generating tasks, breaking them into waves, identifying dependencies, and structuring an implementation guide.

**The insight**: I shouldn't build PM tools *for* you. You should build them *yourself*, using the same pattern-harvesting approach. Here's why:

1. **Tools born from your actual workflow will stick.** Tools built by someone else for how they *imagine* your workflow won't.
2. **You own the iteration loop.** No handoff latency, no context loss between us, no "try it → give feedback → wait for changes → try again" death spiral.
3. **The story is stronger.** "I build my own AI-augmented PM tooling" is a fundamentally more credible narrative than "my developer built me some tools."

---

## What We've Already Learned (Your Head Start)

### Your Feedback Already Identified the Patterns

When you tried RequireKit and gave feedback, you actually did the first step of pattern harvesting without realising it. You identified eight friction points — things like needing a prep template before diving into questions, wanting to say "you decide" when you don't know an answer, and wanting to import existing docs rather than re-enter everything.

That feedback became a detailed analysis mapping your needs to four potential feature specs (FEAT-RK-002 through 005). I'll share that analysis with you — not because I want you to implement those specs, but because it's a worked example of **how patterns become tools**.

### The ClosedLoop Example

Kris Wong at ClosedLoop shared publicly that his team has built a private Claude Code plugin marketplace containing 4 plugins with 13 skills, 59 agents, and 22 commands — and they're adding more every week. On the product side, they have tools that help PMs draft PRDs and automatically publish them to Confluence for review.

This is what "AI-first PM" looks like at scale. But it started with individuals noticing what they repeated and codifying it.

### Skills Are Just Markdown Files

The technical barrier is lower than you might think. A Claude Code "skill" is literally a folder containing a `SKILL.md` file — a markdown document that tells Claude how to do something. No code, no build step, no deployment. You write instructions in plain English, organised into a structure Claude understands, and it applies them automatically when relevant.

Here's a simplified example of what a PM skill might look like:

```
.claude/skills/
└── prd-drafting/
    ├── SKILL.md              # "When drafting a PRD, follow this structure..."
    └── resources/
        └── prd-template.md   # Your preferred PRD format
```

Commands are similar — markdown files that define a specific workflow Claude should follow when you type a slash command.

---

## The Three-Tier Approach

### Tier 1: Just Use It (This Week)

Pick one real PM task and do it entirely with Claude (either Claude Code or Claude Desktop — whichever feels more natural). Good candidates:

- **Write a PRD or product brief** for something you're actually working on
- **Analyse competitor features** — give Claude a list of competitors and ask it to map their capabilities
- **Prepare for a stakeholder meeting** — have Claude help you structure your agenda, anticipate questions, draft talking points
- **Review and refine user stories** — paste in rough stories and iterate on acceptance criteria
- **Create a feature prioritisation framework** — describe your constraints and have Claude help you build a scoring model

Don't try to formalise anything yet. Just notice what works, what you repeat, and where Claude needs more guidance.

### Tier 2: Spot the Patterns (After 1-2 Weeks)

Keep a simple log — even just a text file or a note on your phone. Every time you find yourself giving Claude the same kind of instruction, write it down:

- "I keep telling Claude our PRD format has these specific sections..."
- "Every time I do competitor analysis, I start by asking Claude to..."
- "When I refine user stories, I always ask Claude to check for..."

These repeated instructions are your automation candidates. They're the raw material for skills and commands.

### Tier 3: Create Your First Skill (When Ready)

Take your most repeated pattern and turn it into a `SKILL.md` file. Start small — even a skill that just says "when I'm writing a PRD, always use this template and check for these common gaps" is valuable.

I can help you structure your first skill once you've identified the pattern. The process is straightforward:

1. Write out the instructions you keep giving Claude, in plain English
2. Organise them into a SKILL.md with a description of when to apply them
3. Drop the folder into your `.claude/skills/` directory
4. Claude picks it up automatically — no restart needed

---

## Reference Materials I'm Sharing

Along with this document, you'll have access to:

1. **Your Feedback Analysis** (`james-feedback-analysis-v2.md`) — Your eight friction points mapped to four potential feature specs. This shows the pattern-to-spec journey in action.

2. **FEAT-RK-002 Spec** — The full "Session Prep & Adaptive Conversations" feature spec we developed from your feedback. This is an example of how a harvested pattern gets formalised into something implementable. Read it for the methodology, not necessarily to implement it.

3. **Skills Architecture Research** — Our analysis of how Claude Skills work, the hybrid approach of keeping commands for explicit workflows while using skills for standards that should apply automatically, and the progressive disclosure pattern that keeps things efficient.

---

## The Mindset Shift

The traditional model is: PM defines requirements → Developer builds tools → PM uses tools. The feedback loop is slow, lossy, and the PM is always a consumer.

The AI-first model is: PM uses AI tools → PM notices patterns → PM formalises patterns into reusable skills and commands → PM's tooling evolves with their workflow. The feedback loop is immediate and the PM is a builder.

You don't need to become a developer to do this. You need to become someone who notices their own patterns and writes them down in a structured way. Claude handles the rest.

---

## Next Steps

1. **Pick your first task** from the Tier 1 list and do it with Claude this week
2. **Start your pattern log** — even a simple note each time you repeat yourself
3. **When you've got 3-5 patterns**, let's have a working session where we turn one into your first skill
4. **Share what you build** — your skills and commands become part of the RequireKit story, authored by a PM, not a developer
