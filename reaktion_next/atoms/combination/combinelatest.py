import asyncio
from typing import List, Optional
from reaktion_next.atoms.combination.base import CombinationAtom
from reaktion_next.events import NextInEvent, EventType, ErrorOutEvent, CompleteOutEvent, NextOutEvent
import logging
from pydantic import Field
from reaktion_next.atoms.helpers import index_for_handle

logger = logging.getLogger(__name__)


class CombineLatestAtom(CombinationAtom):
    state: List[Optional[NextInEvent]] = Field(default_factory=lambda: [None, None])

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
                            caused_by=(event.current_t,),
                        )
                    )
                    break

                streamIndex = index_for_handle(event.handle)

                if event.type == EventType.COMPLETE:
                    if streamIndex == 0:
                        await self.transport.put(
                            CompleteOutEvent(
                                handle="return_0",
                                type=EventType.COMPLETE,
                                source=self.node.id,
                                caused_by=(event.current_t,),
                            )
                        )
                        break

                if event.type == EventType.NEXT:
                    self.state[streamIndex] = event

                    if all(map(lambda x: x is not None, self.state)):
                        
                        next = ()
                        caused_by = ()
                        
                        for i in range(len(self.state)):
                            inevent = self.state[i]
                            if inevent is not None:
                                next += inevent.value
                                caused_by += (inevent.current_t,)
                                
                            
                            
                        
                        
                        await self.transport.put(
                            NextOutEvent(
                                handle="return_0",
                                value=next,
                                source=self.node.id,
                                caused_by=caused_by
                            )
                        )

        except asyncio.CancelledError as e:
            logger.warning(f"Atom {self.node} is getting cancelled")
            raise e

        except Exception:
            logger.exception(f"Atom {self.node} excepted")
