from pydantic import BaseModel
import asyncio
from reaktion_next.events import OutEvent


class AtomTransport(BaseModel):
    queue: asyncio.Queue

    async def put(self, event: OutEvent):
        await self.queue.put(event)

    async def get(self) -> OutEvent:
        return await self.queue.get()

    class Config:
        arbitrary_types_allowed = True


class MockTransport(AtomTransport):
    async def get(self, timeout=3) -> OutEvent:
        return await asyncio.wait_for(self.queue.get(), timeout=timeout)

    pass
