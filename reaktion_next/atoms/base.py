import asyncio
from typing import Awaitable, Callable, Optional
from pydantic import BaseModel, Field
from fluss_next.api.schema import BaseGraphNodeBase
from reaktion_next.atoms.errors import AtomQueueFull
from reaktion_next.events import EventType, InEvent, OutEvent
import logging
from rekuest_next.messages import Assign
from reaktion_next.atoms.transport import AtomTransport
from reaktion_next.reference_counter import ReferenceCounter
from rekuest_next.actors.base import Actor
from pydantic import BaseModel, ConfigDict
from typing import Dict, Any
from reaktion_next.events import InEvent, OutEvent, EventType, ErrorOutEvent

logger = logging.getLogger(__name__)


class Atom(BaseModel):
    """Base class for all atoms."""

    node: BaseGraphNodeBase
    reference_counter: ReferenceCounter
    transport: AtomTransport
    globals: Dict[str, Any] = Field(default_factory=dict)
    hold_references: Dict[str, Any] = Field(default_factory=dict)
    _private_queue: Optional[asyncio.Queue[InEvent]] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def run(self) -> None:
        raise NotImplementedError("This needs to be implemented")

    async def get(self) -> InEvent:
        assert self._private_queue is not None, "Atom not started"
        return await self._private_queue.get()

    async def put(self, event: InEvent):
        assert self._private_queue is not None, "Atom not started"
        try:
            logger.info(f"Putting event {event}")
            await self._private_queue.put(event)  # TODO: Make put no wait?
        except asyncio.QueueFull as e:
            logger.error(f"{self.node.id} private queue is full")
            raise AtomQueueFull(f"{self.node.id} private queue is full") from e
        except Exception as e:
            logger.error(f"{self.node.id} FAILED", exc_info=True)
            await self.transport.put(
                ErrorOutEvent(
                    handle="return_0",
                    source=self.node.id,
                    exception=e,
                    caused_by=[-1],
                )
            )

    async def aenter(self):
        self._private_queue = asyncio.Queue()

    async def aexit(self):
        self._private_queue = None

    async def __aenter__(self):
        await self.aenter()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aexit()

    async def start(self):
        try:
            await self.run()
        except Exception as e:
            logger.error(f"{self.node.id} FAILED", exc_info=True)
            await self.transport.put(
                OutEvent(
                    handle="return_0",
                    type=EventType.ERROR,
                    source=self.node.id,
                    exception=e,
                    caused_by=[-1],
                )
            )

    @property
    def set_values(self) -> Dict[str, Any]:
        defaults = self.node.constants_map or {}
        my_globals = self.globals or {}
        return {**defaults, **my_globals}
