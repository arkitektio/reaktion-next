from typing import List, Optional
from rekuest.api.schema import NodeKindInput, DefinitionInput, PortInput, NodeKind
from fluss.api.schema import (
    FlowFragmentGraph,
    FlowNodeFragmentBaseArkitektNode,
    FlowNodeFragmentBaseReactiveNode,
    ReactiveImplementationModelInput,
    FlowFragment,
    LocalNodeFragment,
    ArkitektNodeFragment,
    GraphNodeFragment,
)
from .events import OutEvent, InEvent
import pydantic
from .errors import FlowLogicError


def connected_events(
    graph: FlowFragmentGraph, event: OutEvent, t: int
) -> List[InEvent]:
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


def infer_kind_from_graph(graph: FlowFragmentGraph) -> NodeKindInput:
    kind = NodeKindInput.FUNCTION

    for node in graph.nodes:
        if isinstance(node, FlowNodeFragmentBaseArkitektNode):
            if node.kind == NodeKindInput.GENERATOR:
                kind = NodeKindInput.GENERATOR
                break
        if isinstance(node, FlowNodeFragmentBaseReactiveNode):
            if node.implementation == ReactiveImplementationModelInput.CHUNK:
                kind = NodeKindInput.GENERATOR
                break

    return kind


def convert_flow_to_definition(
    flow: FlowFragment,
    name: str = None,
    description: str = None,
    kind: Optional[NodeKindInput] = None,
) -> DefinitionInput:
    # assert localnodes are in the definitionregistry
    localNodes = [x for x in flow.graph.nodes if isinstance(x, LocalNodeFragment)]
    graphNodes = [x for x in flow.graph.nodes if isinstance(x, GraphNodeFragment)]
    assert len(graphNodes) == 0, "GraphNodes are not supported yet"

    for node in localNodes:
        assert node.hash, f"LocalNode {node.name} must have a definition"

    args = [PortInput(**x.dict(by_alias=True)) for x in flow.graph.args]
    returns = [PortInput(**x.dict(by_alias=True)) for x in flow.graph.returns]

    globals = [
        PortInput(**glob.port.dict(by_alias=True)) for glob in flow.graph.globals
    ]

    return DefinitionInput(
        name=name or flow.workspace.name,
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
