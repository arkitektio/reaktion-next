from fluss_next.api.schema import GraphNodeBase
from reaktion_next.events import InEvent


def index_for_handle(handle: str) -> int:
    return int(handle.split("_")[1])


def node_to_reference(node: GraphNodeBase, event: InEvent) -> str:
    return f"{node.id}_{event.current_t}"
