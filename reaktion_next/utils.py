"""Graph helpers for routing events along flow edges."""

from typing import List
from fluss_next.api.schema import Graph
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
from .errors import FlowLogicError


def connected_events(graph: Graph, event: OutEvent, t: int) -> List[InEvent]:
    """Translate an out event into the in events of all connected nodes."""
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
