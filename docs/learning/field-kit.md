# Reusable records for a team

Copy the relevant record into your team's existing repository or knowledge system.
Each answers a practical question; none requires a new ticket type or approval step.
Keep links to executed evidence beside the claims they support.

## Feature contract

Use this before implementation, whether work happens in a coding harness or a factory.
It is a communication template, not a GuardKit configuration schema.

```markdown
# Feature: <observable user outcome>

## Request
Who needs what, and why?

## Scope
What behaviour changes? What important behaviour must remain?
Which assumptions need an answer before coding?

## Examples
- Starting state:
- User action or agent decision:
- Expected observable result:
- Failure case and expected handling:

## Verification
- Example -> check/command -> evidence -> reviewer
- Existing baseline failures and their recorded disposition:
- Candidate revision:

## Context
- Project map and relevant decision links:
- Dependencies and environment:
- Prototype/reference version, if relevant:

## Completion
What proves implementation, acceptance and delivery separately?
Who has the existing authority to accept and release it?
```

## Learning record

Use this when an incident or experiment changes how the team should work.

```markdown
# Lesson: <specific behaviour or failure>
Observed on: <date, source revision, environment>

Trigger:
What we expected:
What actually happened:
Evidence:
Cause supported by that evidence:
Change made:
Check showing the change helped:
What remains uncertain:
Where the next engineer encounters this guidance:
Owner:
```

**Worked example:** a candidate passed its component tests but failed when the UI
called the real API. The lesson is to test that connected journey. It is not evidence
that component tests are useless or that every future integration failure is solved.
Use your actual result in the record; do not copy this example as historical evidence.

## Decision record

```markdown
# Decision: <choice the team needs to remember>
Date and owner:
Problem and constraints:
Options considered:
Decision and reason:
Evidence and tradeoffs:
What would cause us to revisit it:
Implementation/status links:
```

A decision to try a mechanism is not evidence that it has been implemented. Keep the
status link current and retain the earlier reasoning when the choice changes.

## Experiment record

```markdown
# Experiment: <question>
Owner and date:
Hypothesis:
Task cohort and number of attempts:
Repository and immutable starting revision:
Acceptance checks fixed before the run:
Models, harnesses, prompts and tool versions:
Resource/time/repair limits:
What changes between arms:
What stays the same:
Known prior task exposure or other confounders:
Outcome categories, including failed and cancelled attempts:
Human effort and cost measurement method:
Raw results and evidence:
Conclusion supported by the results:
What this experiment cannot establish:
Next question:
Review trigger or date:
```

## Handover and teach-back

```markdown
# Handover: <workflow or service>
Receiving engineer/team:
Purpose and architecture diagram:
Source-of-truth repository and current revision:
Commands for setup, normal use, verification and cleanup:
Required access, obtained through the team's existing process:
Known failure symptoms and recovery steps:
Current limitations and unfinished work:
One successful example and one failed example:
Fresh task the receiver completed without the author driving:
What the receiver changed or clarified in this document:
Next owner and review trigger:
```

## A presentation evidence card

```markdown
# Claim: <one sentence suitable for a slide>
Claim type: implementation / observed run / external report / proposed practice
Source URL or internal evidence link:
Revision and observation/publication date:
Screenshot or diagram:
Denominator and conditions, if reporting a metric:
Limit that must stay beside the claim:
Public-safe example or redactions needed:
```

Use this card with the [presentation kit](presentation-kit.md). It keeps source
research attached to a talk without putting source-code listings on every slide.
