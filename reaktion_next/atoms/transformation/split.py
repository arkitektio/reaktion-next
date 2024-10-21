import asyncio
from typing import List
from reaktion_next.atoms.combination.base import CombinationAtom
from reaktion_next.events import EventType, OutEvent
import logging

logger = logging.getLogger(__name__)


class SplitAtom(CombinationAtom):
    complete: List[bool] = [False, False]

    async def run(self):
        try:
            while True:
                event = await self.get()

                if event.type == EventType.ERROR:
                    for index, stream in enumerate(self.node.outstream):
                        await self.transport.put(
                            OutEvent(
                                handle=f"return_{index}",
                                type=EventType.ERROR,
                                exception=event.exception,
                                source=self.node.id,
                                caused_by=[event.current_t],
                            )
                        )
                    break

                if event.type == EventType.NEXT:
                    for index, stream in enumerate(self.node.outstream):
                        if event.value[index] is not None:
                            await self.transport.put(
                                OutEvent(
                                    handle=f"return_{index}",
                                    type=EventType.NEXT,
                                    value=(event.value[index],),
                                    source=self.node.id,
                                    caused_by=[event.current_t],
                                )
                            )

                if event.type == EventType.COMPLETE:
                    for index, stream in enumerate(self.node.outstream):
                        await self.transport.put(
                            OutEvent(
                                handle=f"return_{index}",
                                type=EventType.COMPLETE,
                                value=None,
                                source=self.node.id,
                                caused_by=[event.current_t],
                            )
                        )
                    break

        except asyncio.CancelledError as e:
            logger.warning(f"Atom {self.node} is getting cancelled")
            raise e

        except Exception as e:
            logger.exception(f"Atom {self.node} excepted")
            raise e
