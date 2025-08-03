from rath.scalars import ID
from reaktion_next.actor import FlowActor
from rekuest_next.agents.base import BaseAgent
import logging
from rekuest_next.actors.base import Actor
from fluss_next.api.schema import aget_flow
from rekuest_next.api.schema import (
    ImplementationInput,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ReaktionExtension(BaseModel):
    extension_name: str = "reaktion"
    cleanup: bool = False

    async def astart(self, instance_id: str):
        pass

    def get_name(self):
        return self.extension_name

    def should_cleanup_on_init(self):
        return False

    async def aspawn_actor_for_interface(
        self,
        agent: "BaseAgent",
        interface: str,
    ) -> Actor:
        t = await aget_flow(id=ID.validate(interface))

        return FlowActor(
            flow=t,
            agent=agent,
        )

    async def aget_implementations(
        self,
    ) -> list[ImplementationInput]:
        templates: list[ImplementationInput] = []
        return templates

    async def atear_down(self):
        pass
