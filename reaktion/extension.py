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

    async def aspawn_actor_from_template(
        self,
        template: TemplateFragment,
        passport: Passport,
        transport: ActorTransport,
        agent: "BaseAgent",
        collector: "Collector",
    ) -> Optional[Actor]:
        """Spawns an Actor from a Provision. This function closely mimics the
        spawining protocol within an actor. But maps template"""
        try:
            actor_builder = self.definition_registry.get_builder_for_interface(
                template.interface
            )

            return actor_builder(
                passport=passport,
                transport=transport,
                collector=collector,
                agent=agent,
            )

        except KeyError as e:
            # Apparetnyl this is not one of our predefined templates

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
        definition, actorBuilder = reactify(
            self.deploy_graph,
            self.structure_registry,
            interfaces=["fluss_next:deploy"],
        )

        self.definition_registry.register_at_interface(
            "deploy_graph",
            definition=definition,
            structure_registry=self.structure_registry,
            actorBuilder=actorBuilder,
        )

        definition, actorBuilder = reactify(
            self.undeploy_graph,
            self.structure_registry,
            interfaces=["fluss_next:undeploy"],
        )

        self.definition_registry.register_at_interface(
            "undeploy_graph",
            definition=definition,
            structure_registry=self.structure_registry,
            actorBuilder=actorBuilder,
        )

        return self.definition_registry

    async def deploy_graph(
        self,
        flow: FlowFragment,
        name: str = None,
        description: str = None,
        kind: Optional[NodeKind] = None,
    ) -> TemplateFragment:
        """Deploy Flow

        Deploys a Flow as a Template

        Args:
            graph (FlowFragment): The Flow
            name (str, optional): The name of this Incarnation
            description (str, optional): The name of this Incarnation

        Returns:
            TemplateFragment: The created template
        """
        print("Deploying graph")
        assert flow.title, "Graph must have a Name in order to be deployed"

        dependencies = [
            DependencyInput(
                hash=x.hash,
                reference=x.id,
                optional=False,
            )
            for x in flow.graph.nodes
            if isinstance(x, RekuestNodeFragmentBase)
        ]  # TODO: Check for local nodes

        template = await acreate_template(
            interface=f"flow:{flow.id}",
            definition=convert_flow_to_definition(
                flow, name=name, description=description, kind=kind
            ),
            instance_id=useInstanceID(),
            params={"flow": flow.id},
            extension=self.extension_name,
            dependencies=dependencies,
        )

        return template

    async def undeploy_graph(
        flow: FlowFragment,
    ):
        """Undeploy Flow

        Undeploys graph, no user will be able to reserve this graph anymore

        Args:
            graph (FlowFragment): The Flow

        """
        assert flow.name, "Graph must have a Name in order to be deployed"

        x = await afind(interface=flow.hash)

        return None
