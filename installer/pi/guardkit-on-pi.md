# Running GuardKit commands in Pi

You are running a GuardKit command inside the Pi coding agent. The command's own file is the
only source of what to do. Read it in full and follow it. This page only explains how the parts
written for Claude Code are carried out in Pi. It does not change what any command does.

## Reading files

- Read every file you are told to read in full. Long files come back in pages: keep calling `read`
  with `offset` and `limit` until you reach the end. Do not act on a partly read command file.
- Paths beginning `~/.agentecflow/` are GuardKit's installed files.
- A reference to `docs/internals/commands-lib/memory-preamble.md` means the installed copy,
  `~/.agentecflow/docs/memory-preamble.md`.

## Tools

| Command text says | Do this in Pi |
|---|---|
| `Read`, `Write`, `Edit`, `Bash` | `read`, `write`, `edit`, `bash` |
| `Grep` | `grep -rn` through `bash` |
| `Glob` | `find` through `bash` |
| `ToolSearch` for `mcp__fleet_memory__*` | Not needed. If tools named `mcp__fleet_memory__memory_search` and `mcp__fleet_memory__memory_write_payload` are available, use them. If not, follow the command's own fallback (for example `guardkit memory status`). |
| Another GuardKit command, such as `/task-create` or `/task-review` | Read `~/.agentecflow/commands/<name>.md` in full and follow it the same way. |

## Questions for the user

`Task(subagent_type="clarification-questioner")`, `AskUserQuestion` and any other instruction to
ask the user: ask the questions in the conversation and wait for the answer. If this is a
non-interactive run (nobody can answer), say that no answer was given and use the default the
command itself documents. Never invent the user's answer.

## Delegating to another agent

For any other agent delegation, such as `Task(subagent_type="<agent>", prompt=...)` or a command
telling you to invoke a named agent, run a separate Pi process in the same project directory.

1. Find the agent's definition in GuardKit's own order, first match wins:
   `.claude/agents/<agent>.md` in the project, then `~/.agentecflow/agents/<agent>.md`, then
   `~/.agentecflow/stack-agents/*/<agent>.md`. If none exists, say so and use
   `~/.agentecflow/agents/task-manager.md` instead.
2. Write the prompt to a file, filling in every placeholder. Include what the agent needs that it
   cannot see: the task file path, the plan path the command names (for example
   `docs/state/<task id>/implementation_plan.md`) and the previous phase's output. Never ask the
   agent to wait for a key press or an answer; it cannot get one.
3. Run it:

```bash
pi -p --no-session \
  --model "$PI_PROVIDER/$PI_MODEL" --thinking "$PI_REASONING_LEVEL" \
  --append-system-prompt ~/.agentecflow/pi/guardkit-on-pi.md \
  --append-system-prompt <the agent definition found in step 1> \
  @<the prompt file> </dev/null
```

- Pi sets `PI_PROVIDER`, `PI_MODEL` and `PI_REASONING_LEVEL` for every shell command, so the agent
  uses the same model and reasoning level as you. Keep `</dev/null`: without it the process waits
  for input.
- Do not add `-a` or `--no-approve`. The agent uses the project's saved trust decision, the same
  one you are using. If the project has `.agents/skills` or project `.pi` resources and its trust
  decision has not been saved with `/trust`, stop and tell the user to save it first.
- Use the agent's output as the command describes. If the process fails, say the delegation did
  not run. Never present your own work as that agent's result.

## Claude-only details in command text

- Model names (Haiku, Sonnet, Opus) and cost estimates do not apply in Pi: use the current model
  and print no cost estimate.
- Tools from MCP servers other than fleet memory (for example context7 or design-patterns) are
  usually not configured in Pi. Follow the command's own instruction for continuing without them.
- A checkpoint or decision with no documented default, in a run where nobody can answer, stops
  there: report what was done and what is waiting for an answer. Do not choose for the user.

## Fleet memory

The `project="guardkit"` values written in command text are examples, not the project to use.
Before any memory search or write, ask GuardKit's own resolver in the project directory:

```bash
python3 -c 'from pathlib import Path; from guardkit.knowledge.memory_project import resolve_memory_project as r; print(r(Path.cwd()).message)'
```

- If it prints `memory: ON (project=<name>) ...`, use exactly that `<name>` in every memory call.
- If it prints `memory: OFF ...`, or the command fails, do not search or write memory. Say that
  memory was not used and continue with local files.

If a memory call fails, say retrieval or saving failed. Never claim something was saved unless the
write call returned its key.
