import asyncio
from typing import List
from reaktion_next.atoms.combination.base import CombinationAtom
from reaktion_next.events import EventType, OutEvent
import logging

logger = logging.getLogger(__name__)


class FilterAtom(CombinationAtom):
    # TODO: Rename to match as it maps to a specifc type
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
                    value = event.value[0]
                    real_value = value["value"]
                    index = value["use"]
                    await self.transport.put(
                        OutEvent(
                            handle=f"return_{index}",
                            type=EventType.NEXT,
                            value=(real_value,),
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
