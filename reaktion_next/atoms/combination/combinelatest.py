import asyncio
from typing import List, Tuple, Optional
from rekuest_next.api.schema import AssignationLogLevel
from reaktion_next.atoms.combination.base import CombinationAtom
from reaktion_next.events import EventType, OutEvent, InEvent
import logging
from pydantic import Field
import functools
from reaktion_next.atoms.helpers import index_for_handle

logger = logging.getLogger(__name__)


class CombineLatestAtom(CombinationAtom):
    state: List[Optional[InEvent]] = Field(default_factory=lambda: [None, None])

    async def run(self):
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
                                    lambda a, b: a.value + b.value, self.state
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
