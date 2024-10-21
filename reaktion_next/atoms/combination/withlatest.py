import asyncio
from typing import List, Optional
from reaktion_next.atoms.helpers import index_for_handle
from reaktion_next.atoms.combination.base import CombinationAtom
from reaktion_next.events import EventType, OutEvent, InEvent
import logging
import functools
from typing import Optional
from pydantic import Field

logger = logging.getLogger(__name__)


class WithLatestAtom(CombinationAtom):
    state: List[Optional[InEvent]] = Field(default_factory=lambda: [None, None])

    async def run(self):
        self.state = list(map(lambda x: None, self.node.instream))
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

                streamIndex = index_for_handle(event.handle)

                if event.type == EventType.COMPLETE:
                    if streamIndex == 0:
                        await self.transport.put(
                            OutEvent(
                                handle="return_0",
                                type=EventType.COMPLETE,
                                source=self.node.id,
                                caused_by=[event.current_t],
                            )
                        )
                        break

                if event.type == EventType.NEXT:
                    self.state[streamIndex] = event

                    if all(map(lambda x: x is not None, self.state)):
                        await self.transport.put(
                            OutEvent(
                                handle="return_0",
                                type=EventType.NEXT,
                                value=functools.reduce(
                                    lambda a, b: a + b.value, self.state, tuple()
                                ),
                                source=self.node.id,
                                caused_by=map(lambda x: x.current_t, self.state),
                            )
                        )

        except asyncio.CancelledError as e:
            logger.warning(f"Atom {self.node} is getting cancelled")
            raise e

        except Exception:
            logger.exception(f"Atom {self.node} excepted")
