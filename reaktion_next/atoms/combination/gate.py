import asyncio
from typing import List, Optional
from reaktion_next.atoms.helpers import index_for_handle
from reaktion_next.atoms.combination.base import CombinationAtom
from reaktion_next.events import EventType, OutEvent, InEvent
import logging
import functools
import asyncio
from typing import Optional
from pydantic import Field

logger = logging.getLogger(__name__)


class GateAtom(CombinationAtom):
    buffer: Optional[asyncio.Queue] = None

    async def run(self):
        self.buffer = asyncio.Queue()

        forward_first = self.set_values.get("forward_first", True)

        try:
            while True:
                event = await self.get()
                logger.info(f"GateAtom {self.node} received {event}")

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
                        if forward_first:
                            await self.transport.put(
                                OutEvent(
                                    handle="return_0",
                                    type=EventType.COMPLETE,
                                    value=event.value,
                                    source=self.node.id,
                                    caused_by=[event.current_t],
                                )
                            )
                            forward_first = False

                        else:
                            await self.buffer.put(event)

                if event.type == EventType.NEXT:
                    if streamIndex == 0:
                        if forward_first:
                            await self.transport.put(
                                OutEvent(
                                    handle="return_0",
                                    type=EventType.NEXT,
                                    value=event.value,
                                    source=self.node.id,
                                    caused_by=[event.current_t],
                                )
                            )
                            forward_first = False

                        else:
                            logger.info("Buffering event")
                            await self.buffer.put(event)

                    else:
                        if self.buffer.empty():
                            forward_first = True
                            logger.info("Buffer is empty, waiting for first event")
                        else:
                            get_event = await self.buffer.get()
                            if get_event.type == EventType.COMPLETE:
                                await self.transport.put(
                                    OutEvent(
                                        handle="return_0",
                                        type=EventType.COMPLETE,
                                        source=self.node.id,
                                        caused_by=[
                                            get_event.current_t,
                                            event.current_t,
                                        ],
                                    )
                                )
                                break
                            else:
                                await self.transport.put(
                                    OutEvent(
                                        handle="return_0",
                                        type=EventType.NEXT,
                                        value=get_event.value,
                                        source=self.node.id,
                                        caused_by=[
                                            get_event.current_t,
                                            event.current_t,
                                        ],
                                    )
                                )

        except asyncio.CancelledError as e:
            logger.warning(f"Atom {self.node} is getting cancelled")
            raise e

        except Exception:
            logger.exception(f"Atom {self.node} excepted")
