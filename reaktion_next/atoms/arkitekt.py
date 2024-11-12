import asyncio

from typing import Any, List, Optional
from reaktion_next.atoms.helpers import node_to_reference
from rekuest_next.postmans.contract import RPCContract
from fluss_next.api.schema import RekuestMapNode

from reaktion_next.atoms.generic import (
    MapAtom,
    MergeMapAtom,
    AsCompletedAtom,
    OrderedAtom,
)
from reaktion_next.events import InEvent
import logging
from rekuest_next.utils import ReservationContext


logger = logging.getLogger(__name__)


class ArkitektMapAtom(MapAtom):
    node: RekuestMapNode
    contract: RPCContract

    async def map(self, event: InEvent) -> Optional[List[Any]]:
        kwargs = self.set_values

        stream_one = self.node.ins[0]
        for arg, item in zip(event.value, stream_one):
            kwargs[item.key] = arg

        returns = await self.contract.acall_raw(
            parent=self.assignment,
            reference=node_to_reference(self.node, event),
            kwargs=kwargs,
        )

        out = []
        stream_one = self.node.outs[0]
        for arg in stream_one:
            out.append(returns[arg.key])

        return out
        # return await self.contract.aassign(*args)


class ArkitektMergeMapAtom(MergeMapAtom):
    node: RekuestMapNode
    contract: RPCContract

    async def merge_map(self, event: InEvent) -> Optional[List[Any]]:
        kwargs = self.set_values

        stream_one = self.node.ins[0]
        for arg, item in zip(event.value, stream_one):
            kwargs[item.key] = arg

        async for r in self.contract.aiterate_raw(
            parent=self.assignment,
            reference=node_to_reference(self.node, event),
            kwargs=kwargs,
        ):
            out = []
            stream_one = self.node.outs[0]
            for arg in stream_one:
                out.append(r[arg.key])

            yield out


class ArkitektAsCompletedAtom(AsCompletedAtom):
    node: RekuestMapNode
    contract: RPCContract

    async def map(self, event: InEvent) -> Optional[List[Any]]:
        kwargs = self.set_values

        stream_one = self.node.instream[0]
        for arg, item in zip(event.value, stream_one):
            kwargs[item.key] = arg

        returns = await self.contract.acall_raw(
            kwargs=kwargs,
            parent=self.assignment,
            reference=node_to_reference(self.node, event),
        )

        out = []
        stream_one = self.node.outstream[0]
        for arg in stream_one:
            out.append(returns[arg.key])

        return out


class ArkitektOrderedAtom(OrderedAtom):
    node: RekuestMapNode
    contract: RPCContract

    async def map(self, event: InEvent) -> Optional[List[Any]]:
        kwargs = self.set_values

        stream_one = self.node.instream[0]
        for arg, item in zip(event.value, stream_one):
            kwargs[item.key] = arg

        returns = await self.contract.acall_raw(
            kwargs=kwargs,
            parent=self.assignment,
            reference=node_to_reference(self.node, event),
        )

        out = []
        stream_one = self.node.outstream[0]
        for arg in stream_one:
            out.append(returns[arg.key])

        return out
