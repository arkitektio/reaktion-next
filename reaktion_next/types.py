from typing import Protocol
from fluss_next.api.schema import FlussBindsFragment


class ContractableNode(Protocol):
    hash: str
    bind: FlussBindsFragment
