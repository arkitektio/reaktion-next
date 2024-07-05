import asyncio
from typing import List, Tuple, Optional
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

    async def run(self):
        self.state = list(map(lambda x: None, self.node.instream))
        self.complete = list(map(lambda x: None, self.node.instream))

        try:
            while True:
                event = await self.get()

                if event.type == EventType.ERROR:
                    await self.transport.put(
                        OutEvent(
                            handle="return_0",
                            type=EventType.ERROR,
                            value=event.value,
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
                    self.state[index_for_handle(event.handle)] = event
                    if all(map(lambda x: x is not None, self.state)):
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
                        # Reinitalizing
                        self.state = list(map(lambda x: None, self.node.instream))

        except asyncio.CancelledError as e:
            logger.warning(f"Atom {self.node} is getting cancelled")
            raise e

        except Exception:
            logger.exception(f"Atom {self.node} excepted")
