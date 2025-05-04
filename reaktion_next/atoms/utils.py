from typing import Awaitable, Callable, Dict
from reaktion_next.atoms.transformation.buffer_count import BufferCountAtom
from rekuest_next.messages import Assign
from fluss_next.api.schema import (
    RekuestFilterActionNode,
    RekuestMapActionNode,
    ReactiveNode,
    BaseGraphNodeBase,
    MapStrategy,
    ReactiveImplementation,
    ActionKind,
)
import asyncio
from reaktion_next.atoms.arkitekt import (
    ArkitektMapAtom,
    ArkitektMergeMapAtom,
    ArkitektAsCompletedAtom,
    ArkitektOrderedAtom,
)
from reaktion_next.atoms.arkitekt_filter import ArkitektFilterAtom
from reaktion_next.atoms.transformation.chunk import ChunkAtom
from reaktion_next.atoms.transformation.buffer_complete import BufferCompleteAtom
from reaktion_next.atoms.transformation.split import SplitAtom
from reaktion_next.atoms.transformation.omit import OmitAtom
from reaktion_next.atoms.combination.zip import ZipAtom
from reaktion_next.atoms.transformation.filter import FilterAtom
from reaktion_next.atoms.combination.withlatest import WithLatestAtom
from reaktion_next.atoms.combination.gate import GateAtom
from reaktion_next.atoms.filter.all import AllAtom
from reaktion_next.rpc_contract import RPCContract
from .base import Atom
from .transport import AtomTransport
from rekuest_next.messages import Assign
from typing import Any, Optional
from reaktion_next.atoms.operations.math import MathAtom, operation_map
from rekuest_next.actors.base import Actor
from reaktion_next.reference_counter import ReferenceCounter


def atomify(
    node: BaseGraphNodeBase,
    transport: AtomTransport,
    contract: Optional[RPCContract],
    globals: Dict[str, Any],
    assignment: Assign,
    reference_counter: ReferenceCounter,
    actor: Actor = None,
) -> Atom:
    if isinstance(node, RekuestMapActionNode):
        if node.action_kind == ActionKind.FUNCTION:
            if node.map_strategy == MapStrategy.MAP:
                return ArkitektMapAtom(
                    node=node,
                    contract=contract,
                    transport=transport,
                    assignment=assignment,
                    globals=globals,
                    actor=actor,
                    reference_counter=reference_counter,
                )
            if node.map_strategy == MapStrategy.AS_COMPLETED:
                return ArkitektAsCompletedAtom(
                    node=node,
                    contract=contract,
                    transport=transport,
                    assignment=assignment,
                    globals=globals,
                    actor=actor,
                    reference_counter=reference_counter,
                )
            if node.map_strategy == MapStrategy.ORDERED:
                return ArkitektAsCompletedAtom(
                    node=node,
                    contract=contract,
                    transport=transport,
                    assignment=assignment,
                    globals=globals,
                    actor=actor,
                    reference_counter=reference_counter,
                )

            raise NotImplementedError(
                f"Map strategy {node.map_strategy} is not implemented"
            )
        if node.action_kind == ActionKind.GENERATOR:
            return ArkitektMergeMapAtom(
                node=node,
                contract=contract,
                transport=transport,
                assignment=assignment,
                globals=globals,
                actor=actor,
                reference_counter=reference_counter,
            )

        raise NotImplementedError(f"Node kind {node.kind} is not implemented")
    if isinstance(node, RekuestFilterActionNode):
        if node.action_kind == ActionKind.FUNCTION:
            if node.map_strategy == MapStrategy.MAP:
                return ArkitektFilterAtom(
                    node=node,
                    contract=contract,
                    transport=transport,
                    assignment=assignment,
                    globals=globals,
                    actor=actor,
                    reference_counter=reference_counter,
                )
        if node.action_kind == ActionKind.GENERATOR:
            raise NotImplementedError("Generator cannot be used as a filter")

    if isinstance(node, ReactiveNode):
        if node.implementation == ReactiveImplementation.ZIP:
            return ZipAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                actor=actor,
                reference_counter=reference_counter,
            )
        if node.implementation == ReactiveImplementation.BUFFER_COUNT:
            return BufferCountAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                actor=actor,
                reference_counter=reference_counter,
            )
        if node.implementation == ReactiveImplementation.FILTER:
            return FilterAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                actor=actor,
                reference_counter=reference_counter,
            )
        if node.implementation == ReactiveImplementation.CHUNK:
            return ChunkAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                actor=actor,
                reference_counter=reference_counter,
            )
        if node.implementation == ReactiveImplementation.GATE:
            return GateAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                actor=actor,
                reference_counter=reference_counter,
            )
        if node.implementation == ReactiveImplementation.OMIT:
            return OmitAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                actor=actor,
                reference_counter=reference_counter,
            )

        if node.implementation == ReactiveImplementation.BUFFER_COMPLETE:
            return BufferCompleteAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                actor=actor,
                reference_counter=reference_counter,
            )
        if node.implementation == ReactiveImplementation.WITHLATEST:
            return WithLatestAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                actor=actor,
                reference_counter=reference_counter,
            )
        if node.implementation == ReactiveImplementation.COMBINELATEST:
            return WithLatestAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                actor=actor,
                reference_counter=reference_counter,
            )
        if node.implementation == ReactiveImplementation.SPLIT:
            return SplitAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                actor=actor,
                reference_counter=reference_counter,
            )
        if node.implementation == ReactiveImplementation.ALL:
            return AllAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                actor=actor,
                reference_counter=reference_counter,
            )
        if node.implementation in operation_map:
            return MathAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                actor=actor,
                reference_counter=reference_counter,
            )

    raise NotImplementedError(f"Atom for {node} {type(node)} is not implemented")
