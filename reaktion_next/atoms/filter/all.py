import asyncio
from typing import List
from reaktion_next.atoms.transformation.base import TransformationAtom
from reaktion_next.events import EventType, OutEvent, InEvent
import logging
from pydantic import Field
from functools import reduce

logger = logging.getLogger(__name__)


class AllAtom(TransformationAtom):
    def assert_values(self, values, check_list_length=True):
        if not isinstance(values, list):
            raise ValueError("AllAtom expects a list of values")

        if not all([v is not None for v in values]):
            raise ValueError("Atom expects all values to be not None")

        if check_list_length:
            if not all([len(v) != 0 for v in values if isinstance(v, List)]):
                raise ValueError("Atom expects all lists to be not empty")

    async def run(self):
        list_length = self.set_values.get("list_length", False)
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
                    try:
                        self.assert_values(event.value, check_list_length=list_length)
                        await self.transport.put(
                            OutEvent(
                                handle="return_0",
                                type=EventType.NEXT,
                                value=event.value,
                                source=self.node.id,
                                caused_by=[event.current_t],
                            )
                        )
                    except ValueError as e:
                        logger.exception(f"Atom {self.node} filtered out an event")

                        await self.transport.put(
                            OutEvent(
                                handle="return_1",
                                type=EventType.NEXT,
                                value=event.value,
                                source=self.node.id,
                                caused_by=[event.current_t],
                            )
                        )

        except asyncio.CancelledError as e:
            logger.warning(f"Atom {self.node} is getting cancelled")
            raise e

        except Exception as e:
            logger.exception(f"Atom {self.node} excepted")
            raise e
