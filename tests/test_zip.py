import pytest
from .utils import expectnext
import asyncio
from reaktion_next.events import InEvent, EventType
from reaktion_next.atoms.transport import MockTransport
from .conftest import (
    ReactiveNode,
)
from reaktion_next.atoms.transformation.chunk import ChunkAtom
from reaktion_next.reference_counter import ReferenceCounter

@pytest.mark.asyncio
@pytest.mark.actor
async def test_zip_node(
    reactive_zip_node: ReactiveNode,
) -> None:
    """ Test the zip atom with a reactive node. """
    event_queue = asyncio.Queue()
    reference_counter = ReferenceCounter()
    atomtransport = MockTransport(queue=event_queue)


    async with ChunkAtom(
        node=reactive_zip_node,
        transport=atomtransport,
        reference_counter=reference_counter,
        
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

