import asyncio
from reaktion_next.atoms.transformation.base import TransformationAtom
from reaktion_next.events import (
    CompleteOutEvent,
    ErrorOutEvent,
    EventType,
    NextOutEvent,
    OutEvent,
)
import logging

logger = logging.getLogger(__name__)


class OmitAtom(TransformationAtom):
    async def run(self):
        try:
            while True:
                event = await self.get()

                if event.type == EventType.ERROR:
                    await self.transport.put(
                        ErrorOutEvent(
                            handle="return_0",
                            exception=event.exception,
                            source=self.node.id,
                            caused_by=[event.current_t],
                        )
                    )
                    break

                if event.type == EventType.NEXT:
                    await self.transport.put(
                        NextOutEvent(
                            handle="return_0",
                            value=[],
                            source=self.node.id,
                            caused_by=[event.current_t],
                        )
                    )

                if event.type == EventType.COMPLETE:
                    await self.transport.put(
                        CompleteOutEvent(
                            handle="return_0",
                            value=[],
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
