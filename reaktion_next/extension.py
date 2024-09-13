from reaktion_next.actor import FlowActor
from rekuest_next.agents.base import BaseAgent
from rekuest_next.actors.reactive.api import useInstanceID
import logging
from rekuest_next.register import register_func
from rekuest_next.actors.base import Actor
from rekuest_next.actors.types import Passport, Assignment
from fluss_next.api.schema import RekuestNodeFragmentBase, aget_flow
from rekuest_next.api.schema import NodeKind

from typing import Optional
from rekuest_next.api.schema import (
    PortInput,
    DependencyInput,
    DefinitionInput,
    TemplateFragment,
    NodeKind,
    acreate_template,
    afind,
    TemplateInput,
)
from fakts.fakts import Fakts
from fluss_next.api.schema import (
    FlowFragment,
)
from reaktion_next.utils import infer_kind_from_graph
from rekuest_next.widgets import StringWidget
from rekuest_next.structures.default import get_default_structure_registry
from rekuest_next.structures.registry import StructureRegistry
from pydantic import BaseModel, Field
from .utils import convert_flow_to_definition
from rekuest_next.agents.extension import AgentExtension

logger = logging.getLogger(__name__)
from rekuest_next.definition.registry import DefinitionRegistry
from rekuest_next.actors.actify import reactify
from rekuest_next.actors.base import ActorTransport
from rekuest_next.collection.collector import Collector


class ReaktionExtension(BaseModel):
    structure_registry: StructureRegistry = Field(
        default_factory=get_default_structure_registry
    )
    definition_registry: DefinitionRegistry = Field(default_factory=DefinitionRegistry)
    extension_name: str = "reaktion"

    async def astart(self, instance_id):
        pass

    async def should_cleanup_on_init(self):
        return False

    async def aspawn_actor_from_template(
        self,
        template: TemplateFragment,
        passport: Passport,
        transport: ActorTransport,
        agent: "BaseAgent",
        collector: "Collector",
    ) -> Optional[Actor]:
        x = template
        assert "flow" in x.params, "Template is not a flow"

        t = await aget_flow(id=x.params["flow"])

        return FlowActor(
            flow=t,
            is_generator=x.node.kind == NodeKind.GENERATOR,
            passport=passport,
            transport=transport,
            definition=x.node,
            agent=agent,
            collector=collector,
        )

    async def aretrieve_registry(self):
        return self.definition_registry

    async def atear_down(self):
        pass
