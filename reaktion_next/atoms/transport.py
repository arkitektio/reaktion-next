from pydantic import BaseModel, ConfigDict
import asyncio
from reaktion_next.events import OutEvent


class AtomTransport(BaseModel):
    queue: asyncio.Queue[OutEvent]
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    
    async def put(self, event: OutEvent):
        await self.queue.put(event)

    async def get(self) -> OutEvent:
        return await self.queue.get()



class MockTransport(AtomTransport):
    async def get(self, timeout: float =3) -> OutEvent:
        return await asyncio.wait_for(self.queue.get(), timeout=timeout)

    pass
