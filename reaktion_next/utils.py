from typing import List, Optional
from rekuest_next.api.schema import DefinitionInput, PortInput, ActionKind
from fluss_next.api.schema import (
    Graph,
    RekuestActionNodeBase,
    ReactiveNode,
    ReactiveImplementation,
    ArgNode,
    ReturnNode,
    Flow,
)
from .events import (
    NextInEvent,
    NextOutEvent,
    ErrorInEvent,
    ErrorOutEvent,
    CompleteInEvent,
    CompleteOutEvent,
    OutEvent,
    InEvent,
)
import pydantic
from .errors import FlowLogicError


def connected_events(graph: Graph, event: OutEvent, t: int) -> List[InEvent]:
    events = []

    for edge in graph.edges:
        if edge.source == event.source and edge.source_handle == event.handle:
            match event:
                case NextOutEvent():
                    events.append(
                        NextInEvent(
                            target=edge.target,
                            handle=edge.target_handle,
                            value=event.value,
                            current_t=t,
                        )
                    )
                case ErrorOutEvent():
                    events.append(
                        ErrorInEvent(
                            target=edge.target,
                            handle=edge.target_handle,
                            exception=event.exception,
                            current_t=t,
                        )
                    )

                case CompleteOutEvent():
                    events.append(
                        CompleteInEvent(
                            target=edge.target,
                            handle=edge.target_handle,
                            current_t=t,
                        )
                    )
                case _:
                    raise FlowLogicError(f"Unknown event type: {event}")

    return events


def infer_kind_from_graph(graph: Graph) -> ActionKind:
    kind = ActionKind.FUNCTION

    for node in graph.nodes:
        if isinstance(node, RekuestActionNodeBase):
            if node.action_kind == ActionKind.GENERATOR:
                kind = ActionKind.GENERATOR
                break
        if isinstance(node, ReactiveNode):
            if node.implementation == ReactiveImplementation.CHUNK:
                kind = ActionKind.GENERATOR
                break

    return kind


def convert_flow_to_definition(
    flow: Flow,
    name: str = None,
    description: str = None,
    kind: Optional[ActionKind] = None,
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
