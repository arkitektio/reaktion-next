from typing import List, Optional
from rekuest_next.api.schema import DefinitionInput, PortInput, NodeKind
from fluss_next.api.schema import (
    Graph,
    RekuestNodeBase,
    ReactiveNode,
    ReactiveImplementation,
    ArgNode,
    ReturnNode,
    GlobalArg,
    Flow,
)
from .events import OutEvent, InEvent
import pydantic
from .errors import FlowLogicError


def connected_events(graph: Graph, event: OutEvent, t: int) -> List[InEvent]:
    events = []

    for edge in graph.edges:
        if edge.source == event.source and edge.source_handle == event.handle:
            try:
                events.append(
                    InEvent(
                        target=edge.target,
                        handle=edge.target_handle,
                        type=event.type,
                        value=event.value,
                        exception=event.exception,
                        current_t=t,
                    )
                )
            except pydantic.ValidationError as e:
                raise FlowLogicError(f"Invalid event for {edge} : {event}") from e

    return events


def infer_kind_from_graph(graph: Graph) -> NodeKind:
    kind = NodeKind.FUNCTION

    for node in graph.nodes:
        if isinstance(node, RekuestNodeBase):
            if node.kind == NodeKind.GENERATOR:
                kind = NodeKind.GENERATOR
                break
        if isinstance(node, ReactiveNode):
            if node.implementation == ReactiveImplementation.CHUNK:
                kind = NodeKind.GENERATOR
                break

    return kind


def convert_flow_to_definition(
    flow: Flow,
    name: str = None,
    description: str = None,
    kind: Optional[NodeKind] = None,
) -> DefinitionInput:
    # assert localnodes are in the definitionregistry

    argNode = [x for x in flow.graph.nodes if isinstance(x, ArgNode)][0]
    returnNode = [x for x in flow.graph.nodes if isinstance(x, ReturnNode)][0]

    args = [PortInput(**x.dict(by_alias=True)) for x in argNode.outs[0]]
    returns = [PortInput(**x.dict(by_alias=True)) for x in returnNode.ins[0]]

    globals = [
        PortInput(**glob.port.dict(by_alias=True)) for glob in flow.graph.globals
    ]

    return DefinitionInput(
        name=name or flow.title,
        kind=kind or infer_kind_from_graph(flow.graph),
        args=args + globals,
        returns=returns,
        portGroups=[],
        description=description,
        interfaces=[
            "workflow",
            f"diagram:{flow.workspace.id}",
            f"flow:{flow.id}",
        ],
    )
