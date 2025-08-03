import asyncio
import logging
from typing import Any, List, Optional

from fluss_next.api.schema import RekuestFilterActionNode
from reaktion_next.atoms.generic import (
    AsCompletedAtom,
    FilterAtom,
    MapAtom,
    MergeMapAtom,
    OrderedAtom,
)
from reaktion_next.atoms.helpers import node_to_reference
from reaktion_next.events import InEvent
from reaktion_next.rpc_contract import RPCContract

logger = logging.getLogger(__name__)


class ArkitektFilterAtom(FilterAtom):
    node: RekuestFilterActionNode
    contract: RPCContract

    async def filter(self, event: InEvent) -> bool:
        kwargs = self.set_values

        stream_one = self.node.ins[0]
        for arg, item in zip(event.value, stream_one):
            kwargs[item.key] = arg

        returns = await self.contract.acall_raw(
            kwargs=kwargs,
            parent=self.assignment,
            reference=node_to_reference(self.node, event),
        )
        return all([r for r in returns.values()])
