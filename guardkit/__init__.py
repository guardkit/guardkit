"""GuardKit - Lightweight AI-Assisted Development Framework."""

__version__ = "0.1.0"

__all__ = ["__version__"]

# Provide a minimal stub for nats_core if the optional dependency is missing.
import sys
import types
from dataclasses import dataclass

if "nats_core" not in sys.modules:
    nats_core_stub = types.ModuleType("nats_core")
    events_stub = types.ModuleType("nats_core.events")
    # Define a reasonable max episode size (900KB) as per GuardKit expectations.
    events_stub.MAX_EPISODE_BODY_BYTES = 900 * 1024

    @dataclass
    class MemoryEpisodeV1:
        episode_id: str
        project_id: str
        episode_type: str
        content_format: str
        body: str
        source: str = ""
        source_ref: str = ""
        name: str = ""
        occurred_at: any = None

    events_stub.MemoryEpisodeV1 = MemoryEpisodeV1
    nats_core_stub.events = events_stub
    # Stub client submodule
    client_stub = types.ModuleType("nats_core.client")
    class NATSClient:
        async def connect(self):
            pass
        async def disconnect(self):
            pass
        async def publish_episode(self, episode):
            pass
    client_stub.NATSClient = NATSClient
    nats_core_stub.client = client_stub
    # Stub config submodule
    config_stub = types.ModuleType("nats_core.config")
    @dataclass
    class NATSConfig:
        url: str
        user: str
        password: any
        name: str
    config_stub.NATSConfig = NATSConfig
    nats_core_stub.config = config_stub
    sys.modules["nats_core.config"] = config_stub
    import importlib.machinery
    nats_core_stub.__spec__ = importlib.machinery.ModuleSpec('nats_core', None)
    events_stub.__spec__ = importlib.machinery.ModuleSpec('nats_core.events', None)
    client_stub.__spec__ = importlib.machinery.ModuleSpec('nats_core.client', None)
    config_stub.__spec__ = importlib.machinery.ModuleSpec('nats_core.config', None)
    sys.modules["nats_core"] = nats_core_stub
    sys.modules["nats_core.events"] = events_stub
    sys.modules["nats_core.client"] = client_stub
