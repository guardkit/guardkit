# Template Spec: nats-asyncio-service
# GuardKit workflow: bootstrap source repo → /template-create --name nats-asyncio-service --path <source_repo>
# Then: /agent-enhance on generated specialist agents

## What This Is

A GuardKit project template for Python asyncio services that communicate via NATS
subjects and JetStream — event-driven daemons that subscribe to messages, process
them (typically with Claude API), and publish results. No HTTP entrypoint at the
top level (optional lightweight health check only).

## Framework Decision: FastStream

Use **FastStream** (`faststream[nats]`) not raw nats-py as the primary framework.
The decisive reason: `TestNatsBroker` provides in-memory testing without a running
NATS server — this is equivalent to the `not integration` gate in the python-library
template. Handler unit tests require zero infrastructure.

## Source Repo Strategy

**There is no existing source repo to use directly** — this template is greenfield.

The correct approach (per guardkit.ai template philosophy and your established pattern):

### Option A: Bootstrap via cookiecutter, then `/template-create` (Recommended)

```bash
# 1. Generate a FastStream NATS project
pip install cookiecutter
cookiecutter https://github.com/airtai/cookiecutter-faststream.git
# → Select: NATS broker, not Kafka/RabbitMQ/Redis
# → Name it: nats-asyncio-service-exemplar

# 2. Add production patterns to the generated project:
#    - handler/service separation (move logic out of @broker.subscriber into services/)
#    - docker-compose.yml with NATS -js flag (JetStream enabled)
#    - pydantic-settings config
#    - AGENTS.md with ALWAYS/NEVER/ASK boundaries
#    - structured logging to stderr

# 3. Run template-create from guardkit
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit
/template-create --name nats-asyncio-service --path /path/to/nats-asyncio-service-exemplar
```

### Option B: Create minimal exemplar by hand via AutoBuild

Create a new repo `nats-asyncio-service-exemplar` with:
- A FastStream NatsBroker app
- One @broker.subscriber handler calling a service
- TestNatsBroker in tests
- docker-compose.yml with NATS + service
- AGENTS.md

Then run `/template-create` on it.

**Option A is faster.** Option B gives more control over what patterns get extracted.

## Core Patterns the Template Must Capture

These must be present in the source repo before running `/template-create`:

### Handler/Service separation
```python
# handlers/domain.py — thin: validate → call service → return
@broker.subscriber("pipeline.video.plan")
@broker.publisher("pipeline.video.planned")
async def handle_message(msg: InboundMessage, svc: DomainService) -> OutboundMessage:
    return await svc.process(msg)

# services/domain.py — pure logic, no NATS dependency
class DomainService:
    async def process(self, msg: InboundMessage) -> OutboundMessage: ...
```

### TestNatsBroker for unit tests (no real NATS needed)
```python
async def test_handler():
    async with TestNatsBroker(broker) as tb:
        await tb.publish(InboundMessage(...), "pipeline.video.plan")
        handle_message.mock.assert_called_once()
```

### pydantic-settings config
```python
class Settings(BaseSettings):
    nats_url: str = "nats://localhost:4222"
    anthropic_api_key: str = ""
    class Config:
        env_file = ".env"
```

### Lifespan context manager
```python
@asynccontextmanager
async def lifespan(app: FastStream):
    # startup: init Claude client, etc.
    yield
    # shutdown: cleanup
```

### docker-compose with JetStream
```yaml
services:
  nats:
    image: nats:latest
    command: ["-js", "-m", "8222"]   # -js = JetStream enabled
```

### Subject hierarchy convention
`domain.action.qualifier.{id}` — e.g. `pipeline.video.plan`, `pipeline.video.planned`

### AGENTS.md with ALWAYS/NEVER/ASK
ALWAYS: define Pydantic schema per subject, keep handlers thin, use TestNatsBroker
NEVER: put business logic in handlers, pass raw bytes, skip ack()
ASK: push vs pull subscribe, stream retention policy

## pyproject.toml Key Dependencies

```toml
dependencies = [
    "faststream[nats]>=0.5.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-m 'not integration'"
markers = [
    "integration: requires real NATS server (run with '-m integration')",
    "seam: cross-module contract tests",
]
```

## Post-Creation Enhancements

After `/template-create` generates the template:

1. **Run `/agent-enhance`** on all generated agents — especially:
   - `nats-service-specialist` — subject hierarchy, TestNatsBroker, handler/service split
   - `nats-testing-specialist` — TestNatsBroker in-memory vs integration test discipline
   - `nats-schema-specialist` — Pydantic message design, subject-to-schema mapping

2. **Add raw nats-py guidance** to rules as a fallback pattern for JetStream features
   FastStream doesn't expose (KV watch, custom stream provisioning):
   ```python
   js = nc.jetstream()
   await js.add_stream(StreamConfig(name="PIPELINE", subjects=["pipeline.>"]))
   kv = await js.create_key_value(bucket="agent-status")
   ```

3. **Add AGENTS.md template** to the generated project template files — this is the
   ALWAYS/NEVER/ASK service boundary document that every bootstrapped project should
   customise for its specific subject domain.

## Template Name and Location

- **Template name:** `nats-asyncio-service`
- **Display name:** `NATS Asyncio Service`
- **Install location:** `installer/core/templates/nats-asyncio-service/`

## Primary Use Cases (context for agent enhancement)

- `youtube-pipeline` — Video Planning Pipeline triggered by NATS messages (Feature 2+3)
- Ship's Computer agents in the require-kit ecosystem (PM adapters, build agents)
- Any always-on autonomous agent reacting to events rather than HTTP requests

## Reference Links

- https://github.com/ag2ai/faststream — FastStream framework
- https://github.com/airtai/cookiecutter-faststream — Bootstrap cookiecutter
- https://faststream.airt.ai/latest/nats/ — FastStream NATS docs
- https://docs.nats.io/nats-concepts/jetstream — JetStream concepts

## Success Criteria

- `guardkit template-validate nats-asyncio-service` passes
- A project bootstrapped with `guardkit init nats-asyncio-service` installs cleanly
- `pytest` runs with zero NATS server required (TestNatsBroker handles it)
- `python -m {service_name}` starts, connects to NATS (via docker-compose), and
  shuts down cleanly on Ctrl-C
- Handler test using TestNatsBroker verifies publish → handler invocation → result publish
- Integration test (`-m integration`) passes with real NATS via docker-compose
