import asyncio

import pytest
from rekuest_next_next.actors.base import Assignment

from reaktion_next.atoms.transformation.split import SplitAtom
from reaktion_next.atoms.transport import MockTransport
from reaktion_next.events import EventType, InEvent

from .conftest import (
    FlowNodeFragmentBaseReactiveNode,
)
from .utils import expecterror, expectnext


@pytest.mark.asyncio
@pytest.mark.actor
async def test_split(
    reactive_split_node: FlowNodeFragmentBaseReactiveNode,
):
    event_queue = asyncio.Queue()
    atomtransport = MockTransport(queue=event_queue)

    assignment = Assignment(assignation=1, user=1, provision=1, args=[])

    async with SplitAtom(
        node=reactive_split_node,
        transport=atomtransport,
        assignment=assignment,
    ) as atom:
        task = asyncio.create_task(atom.start())

        await atom.put(
            InEvent(
                target=atom.node.id,
                handle="arg_0",
                type=EventType.NEXT,
                value=(1, None, 3),
                current_t=0,
            )
        )

        answer = await atomtransport.get(timeout=0.2)
        expectnext(answer)
        assert answer.handle == "return_0", "Expected return_0, got %s" % answer.handle

        answer = await atomtransport.get(timeout=0.2)
        expectnext(answer)
        assert answer.handle == "return_2", "Expected return_2, got %s" % answer.handle

        print("Waiting for error")
        await atom.put(
            InEvent(
                target=atom.node.id,
                handle="arg_0",
                type=EventType.NEXT,
                value=(None, 1, None),
                current_t=1,
            )
        )

        answer = await atomtransport.get(timeout=0.2)
        expectnext(answer)
        assert answer.handle == "return_1", "Expected return_1, got %s" % answer.handle

        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=0.2)
        except asyncio.CancelledError:
            pass
