from typing import List, Optional
from rekuest_next.api.schema import DefinitionInput, PortInput, NodeKind
from fluss_next.api.schema import (
    GraphFragment,
    RekuestNodeFragmentBase,
    ReactiveNodeFragment,
    ReactiveImplementation,
    ArgNodeFragment,
    ReturnNodeFragment,
    GlobalArgFragment,
    FlowFragment,
)
from .events import OutEvent, InEvent
import pydantic
from .errors import FlowLogicError


def connected_events(graph: GraphFragment, event: OutEvent, t: int) -> List[InEvent]:
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
                        current_t=t,
                    )
                )
            except pydantic.ValidationError as e:
                raise FlowLogicError(f"Invalid event for {edge} : {event}") from e

    return events


def infer_kind_from_graph(graph: GraphFragment) -> NodeKind:
    kind = NodeKind.FUNCTION

    for node in graph.nodes:
        if isinstance(node, RekuestNodeFragmentBase):
            if node.kind == NodeKind.GENERATOR:
                kind = NodeKind.GENERATOR
                break
        if isinstance(node, ReactiveNodeFragment):
            if node.implementation == ReactiveImplementation.CHUNK:
                kind = NodeKind.GENERATOR
                break

    return kind


def convert_flow_to_definition(
    flow: FlowFragment,
    name: str = None,
    description: str = None,
    kind: Optional[NodeKind] = None,
) -> DefinitionInput:
    # assert localnodes are in the definitionregistry

    argNode = [x for x in flow.graph.nodes if isinstance(x, ArgNodeFragment)][0]
    returnNode = [x for x in flow.graph.nodes if isinstance(x, ReturnNodeFragment)][0]

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
