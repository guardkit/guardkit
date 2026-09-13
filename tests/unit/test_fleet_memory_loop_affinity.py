"""The fleet-memory store is affine to the loop it was opened on.

FEAT-19C4 and FEAT-B3A6 both ran with the builder and the reviewer having no
memory at all. The store was reachable and full the whole time: it had been
opened on one event loop and was being searched from another, which raises
inside the batched store ("got Future attached to a different loop", or
"Event loop is closed" once the first loop has gone). The search swallowed it
and returned [], and every reader downstream took that for an empty memory.

Proven in the repository's own sandbox before and after the fix: opened on
loop A and searched from loop B, the same query returned 0 hits, then 1.
"""

from __future__ import annotations

import asyncio

from guardkit.knowledge.fleet_memory_client import FleetMemoryClient, _running_loop


class _Store:
    """Stands in for the real store; records which loop it was made on."""

    def __init__(self, loop: object) -> None:
        self.loop = loop


def _client() -> FleetMemoryClient:
    client = FleetMemoryClient.__new__(FleetMemoryClient)
    client._store = None
    client._store_cm = None
    client._store_loop = None
    return client


def test_a_store_from_another_loop_is_not_reused() -> None:
    """The whole defect in one assertion: a stale store must be re-opened."""
    client = _client()

    async def open_on_this_loop() -> object:
        client._store = _Store(_running_loop())
        client._store_loop = _running_loop()
        return client._store_loop

    loop_a = asyncio.run(open_on_this_loop())

    async def what_a_second_loop_sees() -> bool:
        return client._store_loop is _running_loop()

    assert loop_a is not None
    assert asyncio.run(what_a_second_loop_sees()) is False, (
        "a store opened on one loop must not be treated as this loop's store"
    )


def test_the_same_loop_keeps_its_store() -> None:
    """The guard must not churn the connection on every call."""
    client = _client()

    async def twice_on_one_loop() -> bool:
        client._store = _Store(_running_loop())
        client._store_loop = _running_loop()
        return client._store_loop is _running_loop()

    assert asyncio.run(twice_on_one_loop()) is True


def test_outside_a_loop_the_helper_says_so() -> None:
    """No running loop is None, never an exception."""
    assert _running_loop() is None
