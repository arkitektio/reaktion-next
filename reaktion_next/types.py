from typing import Protocol
from fluss_next.api.schema import FlussBinds


class ContractableNode(Protocol):
    hash: str
    bind: FlussBinds
