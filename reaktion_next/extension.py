from rath.scalars import ID
from reaktion_next.actor import FlowActor
from rekuest_next.agents.base import BaseAgent
import logging
from rekuest_next.actors.base import Actor
from fluss_next.api.schema import aget_flow
from rekuest_next.agents.hooks.registry import BackgroundTask
from rekuest_next.api.schema import (
    ImplementationInput,
    LockSchemaInput,
    StateSchemaInput,
)
from pydantic import BaseModel
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ReaktionExtension(BaseModel):
    extension_name: str = "reaktion"
    cleanup: bool = False

    async def astart(self, instance_id: str, app_context: Any) -> None:
        """This should be called when the agent starts"""
        pass

    def get_name(self):
        return self.extension_name

    def should_cleanup_on_init(self):
        return False

    def get_implementations(self) -> list[ImplementationInput]:
        return []

    def get_state_schemas(self) -> Dict[str, StateSchemaInput]:
        return {}

    def get_lock_schemas(self) -> Dict[str, LockSchemaInput]:
        return {}

    def get_background_workers(self) -> Dict[str, BackgroundTask]:
        return {}

    def get_startup_hooks(self) -> Dict[str, BackgroundTask]:
        return {}

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
