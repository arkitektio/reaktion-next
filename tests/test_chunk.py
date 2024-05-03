import pytest
from .utils import expectnext
from rekuest.actors.base import Assignment
from rekuest.agents.transport.protocols.agent_json import *
import asyncio
from reaktion.events import InEvent, EventType
from reaktion.atoms.transport import MockTransport
from .conftest import (
    FlowNodeFragmentBaseReactiveNode,
)
from reaktion.atoms.transformation.chunk import ChunkAtom


@pytest.mark.asyncio
@pytest.mark.actor
async def test_chunk_without_defaults(
    reactive_chunk_node: FlowNodeFragmentBaseReactiveNode,
):
    event_queue = asyncio.Queue()
    atomtransport = MockTransport(queue=event_queue)

    assignation = Assignment(assignation=1, user=1, provision=1, args=[])

    async with ChunkAtom(
        node=reactive_chunk_node,
        transport=atomtransport,
        assignment=assignation,
    ) as atom:
        task = asyncio.create_task(atom.start())
        await asyncio.sleep(0.1)

        await atom.put(
            InEvent(
                target=atom.node.id,
                handle="arg_0",
                type=EventType.NEXT,
                value=([1, 2, 3],),
                current_t=0,
            )
        )

        answer = await atomtransport.get(timeout=0.1)
        expectnext(answer)
        assert answer.value == (1,)

        answer = await atomtransport.get(timeout=0.1)
        expectnext(answer)
        assert answer.value == (2,)

        answer = await atomtransport.get(timeout=0.1)
        expectnext(answer)
        assert answer.value == (3,)

        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=0.1)
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
@pytest.mark.actor
@pytest.mark.skip(reason="Needs to be fixed")
async def test_chunk_with_sleep_defaults(
    reactive_chunk_node_with_defaults: FlowNodeFragmentBaseReactiveNode,
):
    event_queue = asyncio.Queue()
    atomtransport = MockTransport(queue=event_queue)

    assignation = Assignment(assignation=1, user=1, provision=1, args=[])
    assert reactive_chunk_node_with_defaults.defaults == {"sleep": 1000}

    async with ChunkAtom(
        node=reactive_chunk_node_with_defaults,
        transport=atomtransport,
        assignment=assignation,
    ) as atom:
        task = asyncio.create_task(atom.start())
        await asyncio.sleep(0.1)

        await atom.put(
            InEvent(
                target=atom.node.id,
                handle="arg_0",
                type=EventType.NEXT,
                value=([1, 2, 3],),
                current_t=0,
            )
        )

        answer = await atomtransport.get(timeout=1.1)
        expectnext(answer)
        assert answer.value == (1,)

        with pytest.raises(asyncio.TimeoutError):
            await atomtransport.get(
                timeout=0.1
            )  # this should timeout because we sleep for one second

        answer = await atomtransport.get(timeout=1.1)
        expectnext(answer)
        assert answer.value == (2,)

        answer = await atomtransport.get(timeout=1.1)
        expectnext(answer)
        assert answer.value == (3,)

        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=0.1)
        except asyncio.CancelledError:
            pass
