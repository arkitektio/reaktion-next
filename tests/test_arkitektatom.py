import pytest
from fluss.api.schema import (
    ArkitektNodeFragment,
    FlowNodeFragmentBaseArkitektNode,
)
from .utils import expectnext
from rekuest_next_next.agents.transport.protocols.agent_json import *
from rekuest_next_next.postmans.utils import mockuse
from reaktion_next.atoms.arkitekt import (
    ArkitektMapAtom,
    ArkitektMergeMapAtom,
    ArkitektAsCompletedAtom,
    ArkitektOrderedAtom,
)
import asyncio
from reaktion_next.events import InEvent, EventType
from reaktion_next.atoms.transport import AtomTransport
from rekuest_next_next.actors.base import Assignment


def mock_stream(s):
    return "d"

async def mockcontractor(node: ArkitektNodeFragment):
    return mockuse(
        returns=[mock_stream(streamitem) for streamitem in node.outstream[0]],
        reserve_sleep=0.1,
        assign_sleep=0.1,
    )


@pytest.mark.asyncio
@pytest.mark.actor
@pytest.mark.skip(reason="Needs to be fixed")
async def test_arkitekt_atom(
    arkitekt_functional_node: FlowNodeFragmentBaseArkitektNode,
):
    # This parts simpulates the provision

    provision = Provision(provision=1, guardian=1, user=1)

    contract = await mockcontractor(arkitekt_functional_node, provision)
    await contract.aenter()  # We need to enter the context manager

    # This part simulates the assignation

    event_queue = asyncio.Queue()
    atomtransport = AtomTransport(queue=event_queue)

    assignment = Assignment(assignation=1, user=1, provision=1, args=[])

    async with ArkitektMapAtom(
        node=arkitekt_functional_node,
        contract=contract,
        transport=atomtransport,
        assignment=assignment,
    ) as atom:
        task = asyncio.create_task(atom.start())
        await asyncio.sleep(0.1)

        await atom.put(
            InEvent(
                target=1, handle="arg_1", type=EventType.NEXT, value=(1,), current_t=0
            )
        )
        answer = await atomtransport.get()
        expectnext(answer)

        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=0.1)
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
@pytest.mark.actor
@pytest.mark.skip(reason="Needs to be fixed")
async def test_arkitekt_merge_atom(
    arkitekt_functional_node: FlowNodeFragmentBaseArkitektNode,
):
    # This parts simpulates the provision

    provision = Provision(provision=1, guardian=1, user=1)

    contract = await mockcontractor(arkitekt_functional_node, provision)
    await contract.aenter()  # We need to enter the context manager

    # This part simulates the assignation

    event_queue = asyncio.Queue()
    atomtransport = AtomTransport(queue=event_queue)

    assignment = Assignment(assignation=1, user=1, provision=1, args=[])

    async with ArkitektMergeMapAtom(
        node=arkitekt_functional_node,
        contract=contract,
        transport=atomtransport,
        assignment=assignment,
    ) as atom:
        task = asyncio.create_task(atom.start())
        await asyncio.sleep(0.1)

        await atom.put(
            InEvent(
                target=1, handle="arg_1", type=EventType.NEXT, value=(1,), current_t=0
            )
        )
        answer = await atomtransport.get()
        expectnext(answer)

        answer = await atomtransport.get()
        expectnext(answer)

        answer = await atomtransport.get()
        expectnext(answer)

        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=0.1)
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
@pytest.mark.actor
@pytest.mark.skip(reason="Needs to be fixed")
async def test_arkitekt_as_completed_atom(
    arkitekt_functional_node: FlowNodeFragmentBaseArkitektNode,
):
    # This parts simpulates the provision

    provision = Provision(provision=1, guardian=1, user=1)

    contract = await mockcontractor(arkitekt_functional_node, provision)
    await contract.aenter()  # We need to enter the context manager

    # This part simulates the assignation

    event_queue = asyncio.Queue()
    atomtransport = AtomTransport(queue=event_queue)

    assignment = Assignment(assignation=1, user=1, provision=1, args=[])

    async with ArkitektAsCompletedAtom(
        node=arkitekt_functional_node,
        contract=contract,
        transport=atomtransport,
        assignment=assignment,
    ) as atom:
        task = asyncio.create_task(atom.start())
        await asyncio.sleep(0.1)

        for i in range(20):
            await atom.put(
                InEvent(
                    target=1,
                    handle="arg_1",
                    type=EventType.NEXT,
                    value=(1,),
                    current_t=i,
                )
            )

        for i in range(20):
            answer = await atomtransport.get()
            expectnext(answer)
            # answer.caused_by[0] == i, "The order is not preserved"

        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=0.1)
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
@pytest.mark.actor
@pytest.mark.skip(reason="Needs to be fixed")
async def test_arkitekt_ordered_atom(
    arkitekt_functional_node: FlowNodeFragmentBaseArkitektNode,
):
    # This parts simpulates the provision

    provision = Provision(provision=1, guardian=1, user=1)

    contract = await mockcontractor(arkitekt_functional_node, provision)
    await contract.aenter()  # We need to enter the context manager

    # This part simulates the assignation

    event_queue = asyncio.Queue()
    atomtransport = AtomTransport(queue=event_queue)

    assignment = Assignment(assignation=1, user=1, provision=1, args=[])

    async with ArkitektOrderedAtom(
        node=arkitekt_functional_node,
        contract=contract,
        transport=atomtransport,
        assignment=assignment,
    ) as atom:
        task = asyncio.create_task(atom.start())
        await asyncio.sleep(0.1)

        for i in range(20):
            await atom.put(
                InEvent(
                    target=1,
                    handle="arg_1",
                    type=EventType.NEXT,
                    value=(1,),
                    current_t=i,
                )
            )

        for i in range(20):
            answer = await atomtransport.get()
            expectnext(answer)
            answer.caused_by[0] == i, "The order is not preserved"

        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=0.1)
        except asyncio.CancelledError:
            pass
