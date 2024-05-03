from typing import Awaitable, Callable, Dict
from rekuest.api.schema import AssignationLogLevel, NodeKind
from rekuest.messages import Assignation
from fluss.api.schema import (
    ArkitektNodeFragment,
    LocalNodeFragment,
    FlowNodeFragment,
    ArkitektFilterNodeFragment,
    ReactiveImplementationModelInput,
    ReactiveNodeFragment,
    MapStrategy,
)
import asyncio
from reaktion_next.atoms.arkitekt import (
    ArkitektMapAtom,
    ArkitektMergeMapAtom,
    ArkitektAsCompletedAtom,
    ArkitektOrderedAtom,
)
from reaktion_next.atoms.arkitekt_filter import ArkitektFilterAtom
from reaktion_next.atoms.local import LocalMapAtom, LocalMergeMapAtom
from reaktion_next.atoms.transformation.chunk import ChunkAtom
from reaktion_next.atoms.transformation.buffer_complete import BufferCompleteAtom
from reaktion_next.atoms.transformation.split import SplitAtom
from reaktion_next.atoms.combination.zip import ZipAtom
from reaktion_next.atoms.transformation.filter import FilterAtom
from reaktion_next.atoms.combination.withlatest import WithLatestAtom
from reaktion_next.atoms.combination.gate import GateAtom
from reaktion_next.atoms.filter.all import AllAtom
from rekuest.postmans.utils import RPCContract
from .base import Atom
from .transport import AtomTransport
from rekuest.actors.types import Assignment
from typing import Any, Optional
from reaktion_next.atoms.operations.math import MathAtom, operation_map


def atomify(
    node: FlowNodeFragment,
    transport: AtomTransport,
    contract: Optional[RPCContract],
    globals: Dict[str, Any],
    assignment: Assignment,
    alog: Callable[[Assignation, AssignationLogLevel, str], Awaitable[None]] = None,
) -> Atom:
    if isinstance(node, ArkitektNodeFragment):
        if node.kind == NodeKind.FUNCTION:
            if node.map_strategy == MapStrategy.MAP:
                return ArkitektMapAtom(
                    node=node,
                    contract=contract,
                    transport=transport,
                    assignment=assignment,
                    globals=globals,
                    alog=alog,
                )
            if node.map_strategy == MapStrategy.AS_COMPLETED:
                return ArkitektAsCompletedAtom(
                    node=node,
                    contract=contract,
                    transport=transport,
                    assignment=assignment,
                    globals=globals,
                    alog=alog,
                )
            if node.map_strategy == MapStrategy.ORDERED:
                return ArkitektAsCompletedAtom(
                    node=node,
                    contract=contract,
                    transport=transport,
                    assignment=assignment,
                    globals=globals,
                    alog=alog,
                )
        if node.kind == NodeKind.GENERATOR:
            return ArkitektMergeMapAtom(
                node=node,
                contract=contract,
                transport=transport,
                assignment=assignment,
                globals=globals,
                alog=alog,
            )
    if isinstance(node, ArkitektFilterNodeFragment):
        if node.kind == NodeKind.FUNCTION:
            if node.map_strategy == MapStrategy.MAP:
                return ArkitektFilterAtom(
                    node=node,
                    contract=contract,
                    transport=transport,
                    assignment=assignment,
                    globals=globals,
                    alog=alog,
                )
        if node.kind == NodeKind.GENERATOR:
            raise NotImplementedError("Generator cannot be used as a filter")

    if isinstance(node, LocalNodeFragment):
        if node.kind == NodeKind.FUNCTION:
            return LocalMapAtom(
                node=node,
                contract=contract,
                transport=transport,
                assignment=assignment,
                globals=globals,
                alog=alog,
            )
        if node.kind == NodeKind.GENERATOR:
            return LocalMergeMapAtom(
                node=node,
                contract=contract,
                transport=transport,
                assignment=assignment,
                globals=globals,
                alog=alog,
            )

    if isinstance(node, ReactiveNodeFragment):
        if node.implementation == ReactiveImplementationModelInput.ZIP:
            return ZipAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                alog=alog,
            )
        if node.implementation == ReactiveImplementationModelInput.FILTER:
            return FilterAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                alog=alog,
            )
        if node.implementation == ReactiveImplementationModelInput.CHUNK:
            return ChunkAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                alog=alog,
            )
        if node.implementation == ReactiveImplementationModelInput.GATE:
            return GateAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                alog=alog,
            )
        if node.implementation == ReactiveImplementationModelInput.BUFFER_COMPLETE:
            return BufferCompleteAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                alog=alog,
            )
        if node.implementation == ReactiveImplementationModelInput.WITHLATEST:
            return WithLatestAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                alog=alog,
            )
        if node.implementation == ReactiveImplementationModelInput.COMBINELATEST:
            return WithLatestAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                alog=alog,
            )
        if node.implementation == ReactiveImplementationModelInput.SPLIT:
            return SplitAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                alog=alog,
            )
        if node.implementation == ReactiveImplementationModelInput.ALL:
            return AllAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                alog=alog,
            )
        if node.implementation in operation_map:
            return MathAtom(
                node=node,
                transport=transport,
                assignment=assignment,
                globals=globals,
                alog=alog,
            )

    raise NotImplementedError(f"Atom for {node} is not implemented")
