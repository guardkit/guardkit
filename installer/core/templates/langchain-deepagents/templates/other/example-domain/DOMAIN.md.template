# Example Domain Configuration

<!-- REPLACE THIS FILE with your own domain configuration.
     This example shows the expected structure — substitute your
     domain description, guidelines, criteria, and output format. -->

---

## Domain Description

<!-- Replace with a description of YOUR domain. -->

This is a generic example domain that demonstrates the Player-Coach content
generation workflow. The Player agent searches for information and generates
structured content items, while the Coach agent evaluates them against the
criteria below.

Replace this entire file with a domain configuration tailored to your use case
(e.g. product descriptions, research summaries, educational materials, data
reports).

---

## Generation Guidelines

<!-- Replace with instructions for what YOUR Player agent should generate. -->

The Player agent should:

1. Search for relevant information using the `search_data` tool.
2. Synthesise the search results into a single, self-contained content item.
3. Include at least one source reference for every factual claim.
4. Keep the content concise — aim for 150-300 words per item.
5. Use clear, accessible language appropriate for the target audience.

---

## Evaluation Criteria

<!-- Replace with the criteria YOUR Coach agent should evaluate against. -->

The Coach agent evaluates each content item on the following criteria, scoring
each from 1 (poor) to 5 (excellent):

| Criterion       | Description                                              |
|-----------------|----------------------------------------------------------|
| Accuracy        | All claims are supported by the cited sources.           |
| Completeness    | The content addresses the generation request fully.      |
| Clarity         | The content is well-structured and easy to understand.   |
| Source Quality   | References are relevant, credible, and correctly cited.  |

A content item **passes** if every criterion scores 3 or above.
A score of exactly 3 on any criterion is **borderline** — the Coach should
escalate to the human operator for review (see Coach ASK rules in AGENTS.md).

---

## Output Format

<!-- Replace with the JSON schema YOUR Player agent should produce. -->

Each content item must be valid JSON with the following structure:

```json
{
  "title": "Short descriptive title",
  "body": "Main content text (150-300 words).",
  "sources": [
    {
      "reference": "Source title or URL",
      "relevance": "Brief note on how this source supports the content"
    }
  ],
  "metadata": {
    "domain": "example-domain",
    "generated_at": "ISO-8601 timestamp"
  }
}
```
