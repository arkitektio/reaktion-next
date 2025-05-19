import asyncio

from typing import Any, List, Optional

from pydantic import BaseModel
from reaktion_next.atoms.helpers import node_to_reference
from fluss_next.api.schema import RekuestMapActionNode, PortKind
from reaktion_next.rpc_contract import RPCContract
from reaktion_next.atoms.generic import (
    MapAtom,
    MergeMapAtom,
    AsCompletedAtom,
    OrderedAtom,
)
from reaktion_next.events import InEvent
import logging
from rekuest_next.messages import Assign


logger = logging.getLogger(__name__)


class RekuestAtom(BaseModel):
    assignment: Assign


class ArkitektMapAtom(MapAtom, RekuestAtom):
    node: RekuestMapActionNode
    contract: RPCContract

    async def map(self, event: InEvent) -> Optional[List[Any]]:
        kwargs = self.set_values
        assert event.value is not None, "Event value should not be None"

        stream_one = self.node.ins[0]
        for arg, item in zip(event.value, stream_one):
            kwargs[item.key] = arg

        returns = await self.contract.acall_raw(
            parent=self.assignment.assignation,
            reference=node_to_reference(self.node, event),
            kwargs=kwargs,
        )

        out = []
        stream_one = self.node.outs[0]
        for arg in stream_one:
            if arg.kind == PortKind.MEMORY_STRUCTURE:
                self.reference_counter.add_reference(str(returns[arg.key]))

            out.append(returns[arg.key])

        return out
        # return await self.contract.aassign(*args)


class ArkitektMergeMapAtom(MergeMapAtom, RekuestAtom):
    node: RekuestMapActionNode
    contract: RPCContract

    async def merge_map(self, event: InEvent) -> Optional[List[Any]]:
        kwargs = self.set_values

        stream_one = self.node.ins[0]
        for arg, item in zip(event.value, stream_one):
            kwargs[item.key] = arg

        async for r in self.contract.aiterate_raw(
            parent=self.assignment.assignation,
            reference=node_to_reference(self.node, event),
            kwargs=kwargs,
        ):
            out = []
            stream_one = self.node.outs[0]
            for arg in stream_one:
                if arg.kind == PortKind.MEMORY_STRUCTURE:
                    self.reference_counter.add_reference(r[arg.key])
                out.append(r[arg.key])

            yield out


class ArkitektAsCompletedAtom(AsCompletedAtom, RekuestAtom):
    node: RekuestMapActionNode
    contract: RPCContract

    async def map(self, event: InEvent) -> Optional[List[Any]]:
        kwargs = self.set_values

        stream_one = self.node.ins[0]
        for arg, item in zip(event.value, stream_one):
            kwargs[item.key] = arg

        returns = await self.contract.acall_raw(
            kwargs=kwargs,
            parent=self.assignment.assignation,
            reference=node_to_reference(self.node, event),
        )

        out = []
        stream_one = self.node.outs[0]
        for arg in stream_one:
            if arg.kind == PortKind.MEMORY_STRUCTURE:
                self.reference_counter.add_reference(returns[arg.key])

            out.append(returns[arg.key])

        return out


class ArkitektOrderedAtom(OrderedAtom, RekuestAtom):
    node: RekuestMapActionNode
    contract: RPCContract

    async def map(self, event: InEvent) -> Optional[List[Any]]:
        kwargs = self.set_values

        stream_one = self.node.ins[0]
        for arg, item in zip(event.value, stream_one):
            kwargs[item.key] = arg

        returns = await self.contract.acall_raw(
            kwargs=kwargs,
            parent=self.assignment.assignation,
            reference=node_to_reference(self.node, event),
        )

        out = []
        stream_one = self.node.outs[0]
        for arg in stream_one:
            if arg.kind == PortKind.MEMORY_STRUCTURE:
                self.reference_counter.add_reference(returns[arg.key])
            out.append(returns[arg.key])

        return out
