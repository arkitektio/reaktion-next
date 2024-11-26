import asyncio
from typing import List, Optional, Deque
from collections import deque
from reaktion_next.atoms.combination.base import CombinationAtom
from reaktion_next.events import EventType, OutEvent, InEvent
import logging
from pydantic import Field
from reaktion_next.atoms.helpers import index_for_handle
import functools

logger = logging.getLogger(__name__)


class ZipAtom(CombinationAtom):
    state: List[Optional[InEvent]] = Field(default_factory=lambda: [None, None])
    complete: List[Optional[InEvent]] = Field(default_factory=lambda: [None, None])
    buffer: List[Deque[InEvent]] = Field(
        default_factory=lambda: [deque(), deque()]
    )  # Buffers for each input

    async def run(self):
        self.state = list(map(lambda x: None, self.node.ins))
        self.complete = list(map(lambda x: None, self.node.ins))
        self.buffer = list(
            map(lambda x: deque(), self.node.ins)
        )  # Initialize the buffers

        try:
            while True:
                event = await self.get()

                if event.type == EventType.ERROR:
                    await self.transport.put(
                        OutEvent(
                            handle="return_0",
                            type=EventType.ERROR,
                            exception=event.exception,
                            source=self.node.id,
                            caused_by=[event.current_t],
                        )
                    )
                    break

                if event.type == EventType.COMPLETE:
                    self.complete[index_for_handle(event.handle)] = event
                    if all(map(lambda x: x is not None, self.complete)):
                        await self.transport.put(
                            OutEvent(
                                handle="return_0",
                                type=EventType.COMPLETE,
                                source=self.node.id,
                                caused_by=map(lambda x: x.current_t, self.complete),
                            )
                        )
                        break

                if event.type == EventType.NEXT:
                    idx = index_for_handle(event.handle)
                    self.buffer[idx].append(
                        event
                    )  # Add the event to the buffer for that input

                    # Check if all buffers have at least one item
                    if all(map(lambda x: len(x) > 0, self.buffer)):
                        # If so, pop from each buffer and zip the events
                        self.state = [buffer.popleft() for buffer in self.buffer]
                        await self.transport.put(
                            OutEvent(
                                handle="return_0",
                                type=EventType.NEXT,
                                source=self.node.id,
                                value=functools.reduce(
                                    lambda a, b: a + b.value, self.state, tuple()
                                ),
                                caused_by=map(lambda x: x.current_t, self.state),
                            )
                        )
                        # No need to reinitialize self.state as we're using buffers now

        except asyncio.CancelledError as e:
            logger.warning(f"Atom {self.node} is getting cancelled")
            raise e

        except Exception:
            logger.exception(f"Atom {self.node} excepted")
