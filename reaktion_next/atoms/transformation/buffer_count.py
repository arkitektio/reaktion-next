import asyncio
from typing import List
from reaktion_next.atoms.transformation.base import TransformationAtom
from reaktion_next.events import (
    ErrorOutEvent,
    EventType,
    OutEvent,
    InEvent,
    ErrorInEvent,
    NextOutEvent,
    CompleteOutEvent,
)
import logging
from pydantic import Field
from functools import reduce

logger = logging.getLogger(__name__)


class BufferCountAtom(TransformationAtom):
    buffer: List[InEvent] = Field(default_factory=list)

    async def run(self):
        try:
            while True:
                event = await self.get()

                if event.type == EventType.ERROR:
                    await self.transport.put(
                        ErrorOutEvent(
                            handle="return_0",
                            type=EventType.ERROR,
                            exception=event.exception,
                            source=self.node.id,
                            caused_by=[event.current_t],
                        )
                    )
                    break

                if event.type == EventType.NEXT:
                    self.buffer.append(event)
                    if len(self.buffer) == self.set_values.get("count", 1):
                        await self.transport.put(
                            NextOutEvent(
                                handle="return_0",
                                value=[
                                    reduce(
                                        lambda a, b: a + list(b.value), self.buffer, []
                                    )
                                ],  # double brakcets because its  alist :)
                                source=self.node.id,
                                caused_by=[ev.current_t for ev in self.buffer],
                            )
                        )
                        self.buffer = []

                if event.type == EventType.COMPLETE:
                    await self.transport.put(
                        NextOutEvent(
                            handle="return_0",
                            value=[
                                reduce(lambda a, b: a + list(b.value), self.buffer, [])
                            ],  # double brakcets because its  alist :)
                            source=self.node.id,
                            caused_by=[ev.current_t for ev in self.buffer],
                        )
                    )
                    await self.transport.put(
                        CompleteOutEvent(
                            handle="return_0",
                            value=[],
                            source=self.node.id,
                            caused_by=[ev.current_t for ev in self.buffer],
                        )
                    )
                    break

        except asyncio.CancelledError as e:
            logger.warning(f"Atom {self.node} is getting cancelled")
            raise e

        except Exception as e:
            logger.exception(f"Atom {self.node} excepted")
            raise e
