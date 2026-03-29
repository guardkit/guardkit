# Model Compatibility Matrix

Tested model/parser combinations for the Adversarial Cooperation template,
based on 11 factory runs. Consult this before switching models to avoid
repeating known failure modes.

## Tested Combinations

| Model | vLLM Parser | Context | Tool Calling | Reasoning | Verdict |
|-------|-------------|---------|--------------|-----------|---------|
| Qwen2.5-14B | `hermes` | 32K | Yes (`hermes`) | No native | Usable with workarounds |
| Nemotron 3 Nano 4B | `qwen3_coder` | 16K | Yes | No | Too small for adversarial cooperation |
| Qwen3.5-35B-A3B-FP8 | `qwen3_coder` | 262K | Yes | Native `<think>` | Best performer |

## Known Issues by Model

### Qwen2.5-14B

- **Double-serialised tool arguments** (TRF-001): Tool call `arguments` field
  arrives as a JSON string inside a JSON string. The Player's tool dispatch
  must call `json.loads()` twice or pre-normalise before routing.
- **Literal newlines in JSON strings** (TRF-002): Model emits unescaped `\n`
  inside JSON string values, breaking `json.loads()`. The `JsonExtractor`
  strategy 4 (repair) handles this — see `lib/json_extractor.py`.
- **No native reasoning**: Cannot produce `<think>` blocks without explicit
  prompting. If reasoning is needed, add "Think step-by-step inside
  `<think>...</think>` tags before answering" to the system prompt.

### Nemotron 3 Nano 4B

- **Insufficient capacity**: Cannot reliably follow the adversarial cooperation
  format instructions (structured JSON output, tool call sequences).
- **Context window too small** (16K): Multi-turn tool-calling conversations
  with Coach feedback loops exceed context within 2-3 iterations.
- **Not recommended** for this template. Suitable only for single-turn tasks
  with simple output formats.

### Qwen3.5-35B-A3B-FP8

- **Best performer**: Reliable tool calling, native reasoning, large context.
- **Reasoning parser pitfall** (TRF-024): Do NOT use `--reasoning-parser qwen3`
  with vLLM. It strips `<think>` blocks from `.content` and moves them to
  `reasoning_content` in `additional_kwargs`. LangChain's `ChatOpenAI` discards
  `reasoning_content` (non-standard field), so think blocks are silently lost.
  This causes `write_output` validation failures for reasoning-type examples.
- **Workaround**: Omit `--reasoning-parser` and let `<think>` blocks flow
  through in `.content`. The `JsonExtractor` already strips them before
  JSON extraction.

## vLLM Configuration Reference

### Recommended flags (Qwen3.5)

```bash
EXTRA_ARGS="--trust-remote-code \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --enable-prefix-caching"
```

### Flags to avoid

| Flag | Why |
|------|-----|
| `--reasoning-parser qwen3` | Strips `<think>` from content, breaks training example validation (TRF-024) |

### Side effects of `--reasoning-parser`

1. vLLM intercepts `<think>...</think>` blocks in model output
2. Strips them from the `content` field of the response
3. Moves them to `reasoning_content` in `additional_kwargs`
4. LangChain `ChatOpenAI` does not forward `reasoning_content` to downstream code
5. Result: think blocks silently disappear from the application's perspective

**Workaround**: Remove the parser flag. The `JsonExtractor.normalise_think_closing_tags()`
and think-block stripping in `JsonExtractor.extract()` handle `<think>` blocks
in raw content reliably.

## Minimum Requirements for Adversarial Cooperation

Any model used with this template should meet these thresholds:

| Requirement | Minimum | Reason |
|-------------|---------|--------|
| Tool calling reliability (BFCL-V4) | >= 60 | Multi-turn tool dispatch must work consistently |
| Context window | >= 64K tokens | Coach feedback loops consume context rapidly |
| JSON output reliability | Test before deploy | Structured output is the core contract |
| Parameter count | >= 14B recommended | Smaller models cannot follow complex format instructions |

### Pre-deployment validation

Before committing to a new model, run this checklist:

1. **Single-turn tool call**: Send a prompt requiring one tool call. Verify
   the `arguments` field parses with a single `json.loads()`.
2. **Multi-turn conversation**: Run 5+ turns with tool calls. Verify the
   model doesn't lose context or repeat tool calls.
3. **Structured JSON output**: Ask the model to produce a JSON object with
   nested fields. Verify it parses without repair strategies.
4. **Think block handling**: If the model supports reasoning, verify
   `<think>` blocks don't corrupt the JSON payload.

## Known Quirks by Model Family

### Qwen family

- Native thinking requires explicit prompting without vLLM reasoning parser.
  Add instructions to system prompt rather than relying on `--reasoning-parser`.
- Literal newline characters (`\n`) appear inside JSON string values. The
  `JsonExtractor` strategy 4 (repair) handles this, but custom JSON parsing
  code must account for it.
- Tool arguments may be double-serialised (JSON string within JSON string).
  Always check if `arguments` is a string and parse again if so.

### Nemotron family

- Small models (< 8B) cannot reliably follow complex format instructions.
- Tool calling works mechanically but output quality degrades with multi-step
  instructions.

### General (all models)

- All models benefit from a `CRITICAL` section placed at the end of the system
  prompt. Key constraints placed early in long prompts tend to be forgotten.
- The `create_agent()` function prepends system prompts automatically — never
  pass system-role messages in `ainvoke()` input or you get dual system messages,
  which causes vLLM to return 400 Bad Request (see `factory_guards.py`).
