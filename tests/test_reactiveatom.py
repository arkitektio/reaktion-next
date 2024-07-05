import pytest
from .utils import expectnext
from rekuest_next.actors.base import Assignment
from rekuest_next.agents.transport.protocols.agent_json import *
import asyncio
from reaktion_next.events import InEvent, EventType
from reaktion_next.atoms.transport import MockTransport
from .conftest import (
    FlowNodeFragmentBaseReactiveNode,
)
from reaktion_next.atoms.combination.zip import ZipAtom
from reaktion_next.atoms.combination.withlatest import WithLatestAtom


@pytest.mark.asyncio
@pytest.mark.actor
async def test_zip_atom(
    reactive_zip_node: FlowNodeFragmentBaseReactiveNode,
):
    event_queue = asyncio.Queue()
    atomtransport = MockTransport(queue=event_queue)

    assignment = Assignment(assignation=1, user=1, provision=1, args=[])

    async with ZipAtom(
        node=reactive_zip_node,
        transport=atomtransport,
        assignment=assignment,
    ) as atom:
        task = asyncio.create_task(atom.start())
        await asyncio.sleep(0.1)

        await atom.put(
            InEvent(
                target=atom.node.id,
                handle="arg_0",
                type=EventType.NEXT,
                value=(1,),
                current_t=0,
            )
        )
        await asyncio.sleep(0.1)
        await atom.put(
            InEvent(
                target=atom.node.id,
                handle="arg_1",
                type=EventType.NEXT,
                value=(2,),
                current_t=1,
            )
        )

        answer = await atomtransport.get()
        expectnext(answer)
        assert answer.value == (1, 2)

        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=0.1)
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
@pytest.mark.actor
async def test_with_latest(
    reactive_withlatest_node: FlowNodeFragmentBaseReactiveNode,
):
    event_queue = asyncio.Queue()
    atomtransport = MockTransport(queue=event_queue)

    assignment = Assignment(assignation=1, user=1, provision=1, args=[])

    async with WithLatestAtom(
        node=reactive_withlatest_node,
        transport=atomtransport,
        assignment=assignment,
    ) as atom:
        task = asyncio.create_task(atom.start())
        await asyncio.sleep(0.1)

        await atom.put(
            InEvent(
                target=atom.node.id,
                handle="arg_0",
                type=EventType.NEXT,
                value=(1,),
                current_t=0,
            )
        )
        await asyncio.sleep(0.1)
        await atom.put(
            InEvent(
                target=atom.node.id,
                handle="arg_1",
                type=EventType.NEXT,
                value=(2,),
                current_t=1,
            )
        )

        answer = await atomtransport.get()
        expectnext(answer)
        assert answer.value == (1, 2)

        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=0.1)
        except asyncio.CancelledError:
            pass
