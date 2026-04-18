# Pattern Rules

Rule files in this directory document the architectural patterns used by the
`langchain-deepagents` base template (adversarial cooperation, factory
tool-allowlisting, memory injection, domain-driven configuration, tool
delegation).

## `Source:` path convention

Each pattern rule ends with one or more `Source: <path>` lines pointing at the
scaffold or library files that implement the pattern
(e.g. `Source: scaffold/orchestrator_pattern.py.template`).

These paths are **post-render** — they refer to the layout a user sees in their
rendered project, not paths inside this template's source tree. In the template
source tree the referenced files live under `templates/other/...`
(e.g. `templates/other/scaffold/orchestrator_pattern.py.template`); once the
template is applied to a user project, those files appear at the paths cited in
the rule files. Do not "correct" `Source:` paths to match the template tree.
