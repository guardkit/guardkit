  
**Appmilla**

Automated Development Pipeline

*From Feature Plan to Pull Request*

Overview for the Appmilla Team

February 2026

Status: Architecture Design

# **What Are We Building?**

We are building an **automated development pipeline** that connects the way we plan features to the way they get implemented. Today, when a feature is planned and ready to build, someone has to manually set up the development environment, run the build tools, and manage the back-and-forth. The pipeline automates that entire middle section.

In practical terms: you approve a feature in Linear, and the system automatically picks it up, builds it using our AI-augmented development tools (GuardKit AutoBuild), creates a pull request, and updates the Linear ticket. The human stays in the loop for the decisions that matter — approving what gets built and reviewing what was built — while the mechanical steps happen automatically.

# **Why Does This Matter?**

Three reasons:

* **Speed.** Features move from "Ready for Dev" to "In Review" without waiting for someone to manually trigger builds. The Dell ProMax can be working on implementations overnight or while we focus on other things.

* **Consistency.** Every feature goes through the same quality gates — the Player-Coach adversarial loop in GuardKit ensures independent validation. No shortcuts, no forgotten tests. The pipeline enforces the process.

* **Visibility.** Everyone on the team can see exactly where things stand. James sees feature progress in Linear without needing to ask Rich for status updates. Build completions and failures show up automatically in your project management tool.

# **How It Works**

The pipeline uses an **event messaging system** (NATS) as its backbone. Think of it as an internal notification system that connects all the moving parts. When something happens at one stage, it sends a message that triggers the next stage. Here is the end-to-end flow:

| Step | What Happens | Details |
| :---- | :---- | :---- |
| **1** | **Feature Planning** | Rich plans the feature using Claude Desktop and RequireKit. This produces a structured feature spec with tasks broken into waves (groups that can run in parallel). |
| **2** | **Ticket Created** | The pipeline automatically creates a Linear ticket (or GitHub issue) with the feature details, task breakdown, and complexity scores. No manual ticket creation needed. |
| **3** | **Human Approval** | Someone (James, Rich, or Mark) reviews the ticket and moves it to "Ready for Dev" in Linear. This is the human gate — nothing builds without explicit approval. |
| **4** | **Automatic Build** | The Build Agent on the Dell ProMax picks up the event, pulls the code, and runs GuardKit AutoBuild. This is the Player-Coach loop — one AI implements, another independently validates. Multiple rounds until quality gates pass. |
| **5** | **PR Created** | When the build succeeds, a pull request is automatically created on GitHub. The Linear ticket is updated to "In Review" with a link to the PR. |
| **6** | **Human Review** | Rich (or a reviewer) checks the PR. This is the second human gate. If approved, it merges. If changes needed, it goes back through the loop. |

The key insight is that **humans control the on-ramps and off-ramps** (approving what to build, reviewing what was built), while the pipeline handles everything in between automatically.

# **What This Looks Like for You**

## **As a Product Owner / Project Manager**

Your workflow barely changes. You continue working in Linear as you do today:

* Feature tickets appear automatically when Rich plans them, already populated with task breakdowns and complexity estimates.

* You move tickets to "Ready for Dev" when you are happy they should be built.

* You see real-time status updates as the build progresses — which wave is running, which tasks have passed, any failures.

* When a build completes, the ticket moves to "In Review" with a link to the pull request.

* If a build fails, the ticket is updated with the failure reason so you know what happened without chasing anyone.

## **As CEO with Full Visibility**

You have access to see all projects across Appmilla — internal tools, client work, personal projects. The system uses project-level isolation so that client team members (like Mark on FinProxy) can only see their own projects, but you and Rich see everything. This gives you a real-time view of development velocity across the entire portfolio.

# **Multi-Project Support**

The pipeline supports multiple concurrent projects with proper isolation. Each project gets its own messaging channel and permissions:

| Project | Who Can See It | Example Use |
| :---- | :---- | :---- |
| **GuardKit (internal)** | Rich, James | Building our own development tools |
| **RequireKit (internal)** | Rich, James | Requirements and planning tools |
| **GCSE English Tutor** | Rich, James | AI tutoring product for GCSE students |
| **FinProxy LPA Platform** | Rich, James, Mark | Client project — Mark scoped to this only |
| **Future Client Projects** | Rich, James, \+ client team | Same pattern — client team scoped to their project |

This isolation is enforced at the infrastructure level, not just by convention. A client team member physically cannot see events from other projects.

# **Linear Integration**

Linear is the primary project management tool for team-facing workflows. The pipeline integrates bidirectionally:

* **Inbound:** When a feature is planned, the pipeline creates a Linear issue with sub-issues for each task. Complexity scores, wave structure, and the feature spec are attached automatically.

* **Outbound:** When you move a Linear issue to "Ready for Dev", a webhook notifies the pipeline to start the build. When the build completes or fails, Linear is updated automatically.

* **Swap-friendly:** If we later prefer GitHub Projects or Jira for a particular client, we add an adapter for that tool. The core pipeline does not change — only the integration layer.

# **Where It Runs**

Everything runs on hardware we already own, connected securely via Tailscale (the VPN mesh we already use):

| Machine | Role in the Pipeline |
| :---- | :---- |
| **Dell ProMax GB10** | Runs the message bus, Build Agent, and PM adapters. This is where the automated builds happen. Also runs the AI models for AutoBuild. |
| **MacBook Pro M2 Max** | Where Rich plans features using Claude Desktop and RequireKit. Publishes feature-planned events to the pipeline. |
| **Synology NAS** | Hosts the knowledge graph (development context and learnings) and shared storage. Connected via Tailscale. |

No cloud bills during development. If we need cloud hosting for client deployments (for availability or compliance reasons), we can move to AWS later — the system is containerised and ready for that.

For team members who need access (e.g., if you want to see the pipeline dashboard or trigger builds directly), your MacBook gets added to the Tailscale network. You would already have this set up from the NAS access.

# **The Bigger Picture**

This development pipeline is part of a broader vision for Appmilla’s AI platform. The same messaging infrastructure that coordinates build agents will eventually coordinate other AI agents — research assistants, content generators, the Reachy Mini robots, and more. We are calling this broader system the **agent fleet**.

By building the pipeline first, we solve an immediate problem (automating our own development workflow) while laying the foundation for the platform capabilities we will offer clients. The FinProxy LPA Platform would be the first client project to use this pipeline, giving us a real-world validation with proper multi-tenancy and team visibility.

# **Implementation Timeline**

The pipeline will be built in phases. Each phase delivers working functionality:

| Phase | What Gets Built | What It Enables | Duration |
| :---- | :---- | :---- | :---- |
| **1** | Shared message schemas and client library | Common language for all pipeline components | 1–2 weeks |
| **2** | Message bus infrastructure \+ Build Agent | Automated builds triggered by events | 2–3 weeks |
| **3** | GuardKit integration (progress events) | Real-time build progress visibility | 1–2 weeks |
| **4** | RequireKit integration (feature events) | Automatic ticket creation from planning | 1 week |
| **5** | Linear adapter (bidirectional) | Full Linear integration for the team | 1–2 weeks |
| **6** | Multi-tenancy and hardening | Client project isolation (FinProxy ready) | 1–2 weeks |

# **Key Design Decisions**

A few decisions worth being aware of:

* **Event-driven, not webhook-driven.** The message bus is the backbone, not Linear or GitHub webhooks. This means if we swap Linear for something else, only the adapter changes. The core pipeline is untouched.

* **Human gates at both ends.** Nothing builds without someone explicitly approving it (moving to "Ready for Dev"). Nothing merges without a human reviewing the PR. The automation sits between these two human decisions.

* **Single build queue initially.** The system processes one feature build at a time to start. If we find the queue backs up, we can add parallel builds per project later. Simpler to start and optimise once we have real data.

* **Local-first infrastructure.** We use our own hardware and avoid cloud costs during development. Cloud deployment is ready when we need it for client-facing work.

* **Knowledge capture.** The system learns from every build — what worked, what failed, what patterns to avoid. This knowledge travels with the project, so when we hand over a codebase to a client, they get the accumulated development intelligence as well.

# **Open Questions**

A few things we should discuss as a team:

* **Linear vs GitHub Projects for internal work.** The pipeline supports both. Linear is the plan for team-facing projects (FinProxy). For internal Appmilla projects, do we want Linear too, or is GitHub Projects sufficient?

* **Dashboard priority.** We can build a visual dashboard showing build status, queue depth, and project health. Is this a priority for you, or is Linear visibility enough for now?

* **FinProxy as first client project.** The plan is to use FinProxy LPA Platform as the first project running through this pipeline with full multi-tenancy. Does that timing work from a client perspective?

*Prepared by Rich Wainwright — February 2026*  
*For discussion with the Appmilla team. Technical architecture document available separately.*