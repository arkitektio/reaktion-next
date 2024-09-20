import pytest
from fluss.api.schema import (
    FlowNodeFragmentBaseArkitektNode,
    FlowNodeFragmentBasePosition,
    FlowNodeFragmentBaseReactiveNode,
    StreamItemFragment,
    ReactiveImplementationModelInput,
    StreamKind,
    MapStrategy,
)
from rekuest_next_next.api.schema import NodeKind
import json
import pytest
from fluss.api.schema import FlowFragment, PortScope, StreamItemChildFragment
from .utils import build_relative


def build_flow(path):
    with open(build_relative(path), "r") as f:
        g = json.load(f)
        print(g)

    return FlowFragment(**g)



@pytest.fixture(scope="session")
def arkitekt_generator_node():
    return FlowNodeFragmentBaseArkitektNode(
        id=1,
        position=FlowNodeFragmentBasePosition(x=0, y=0),
        name="add_generator",
        hash="oisnosinsoin",
        kind=NodeKind.GENERATOR,
        mapStrategy=MapStrategy.MAP,
        reserveParams={},
        retryDelay=1000,
        assignTimeout=1000,
        yieldTimeout=1000,
        reserveTimeout=1000,    
        allowLocal=False,
        defaults={},
        constream=[],
        instream=[
            [
                StreamItemFragment(
                    key=1, kind=StreamKind.INT, nullable=False, scope=PortScope.GLOBAL
                )
            ]
        ],
        outstream=[
            [
                StreamItemFragment(
                    key=1, kind=StreamKind.INT, nullable=False, scope=PortScope.GLOBAL
                )
            ]
        ],
    )


@pytest.fixture(scope="session")
def arkitekt_functional_node():
    return FlowNodeFragmentBaseArkitektNode(
        id=1,
        position=FlowNodeFragmentBasePosition(x=0, y=0),
        name="add_function",
        hash="oisnosinsoin",
        kind=NodeKind.FUNCTION,
        mapStrategy=MapStrategy.MAP,
        reserveParams={},
        allowLocal=False,
        maxRetries=1,
        retryDelay=1000,
        assignTimeout=1000,
        yieldTimeout=1000,
        reserveTimeout=1000,    
        defaults={},
        constream=[],
        instream=[
            [
                StreamItemFragment(
                    key=1, kind=StreamKind.INT, nullable=False, scope=PortScope.GLOBAL
                )
            ]
        ],
        outstream=[
            [
                StreamItemFragment(
                    key=1, kind=StreamKind.INT, nullable=False, scope=PortScope.GLOBAL
                )
            ]
        ],
    )


@pytest.fixture(scope="session")
def reactive_zip_node():
    return FlowNodeFragmentBaseReactiveNode(
        id=1,
        position=FlowNodeFragmentBasePosition(x=0, y=0),
        implementation=ReactiveImplementationModelInput.ZIP,
        defaults={},
        constream=[],
        instream=[
            [
                StreamItemFragment(
                    key=1, kind=StreamKind.INT, nullable=False, scope=PortScope.GLOBAL
                )
            ],
            [
                StreamItemFragment(
                    key=1, kind=StreamKind.INT, nullable=False, scope=PortScope.GLOBAL
                )
            ],
        ],
        outstream=[
            [
                StreamItemFragment(
                    key=1, kind=StreamKind.INT, nullable=False, scope=PortScope.GLOBAL
                )
            ]
        ],
    )


@pytest.fixture(scope="session")
def reactive_withlatest_node():
    return FlowNodeFragmentBaseReactiveNode(
        id=1,
        position=FlowNodeFragmentBasePosition(x=0, y=0),
        implementation=ReactiveImplementationModelInput.WITHLATEST,
        defaults={},
        constream=[],
        instream=[
            [
                StreamItemFragment(
                    key=1, kind=StreamKind.INT, nullable=False, scope=PortScope.GLOBAL
                )
            ],
            [
                StreamItemFragment(
                    key=1, kind=StreamKind.INT, nullable=False, scope=PortScope.GLOBAL
                )
            ],
        ],
        outstream=[
            [
                StreamItemFragment(
                    key=1, kind=StreamKind.INT, nullable=False, scope=PortScope.GLOBAL
                )
            ]
        ],
    )


@pytest.fixture(scope="session")
def reactive_chunk_node_with_defaults():
    return FlowNodeFragmentBaseReactiveNode(
        id=1,
        position=FlowNodeFragmentBasePosition(x=0, y=0),
        implementation=ReactiveImplementationModelInput.CHUNK,
        defaults={"sleep": 1000},
        constream=[],
        instream=[
            [
                StreamItemFragment(
                    key=1,
                    kind=StreamKind.LIST,
                    nullable=False,
                    scope=PortScope.GLOBAL,
                    child=StreamItemFragment(
                        key=1, kind=StreamKind.INT, nullable=False, scope=PortScope.GLOBAL
                    ),
                )
            ]
        ],
        outstream=[
            [
                StreamItemFragment(
                    key=1, kind=StreamKind.INT, nullable=False, scope=PortScope.GLOBAL
                )
            ]
        ],
    )


@pytest.fixture(scope="session")
def reactive_chunk_node():
    return FlowNodeFragmentBaseReactiveNode(
        id=1,
        position=FlowNodeFragmentBasePosition(x=0, y=0),
        implementation=ReactiveImplementationModelInput.CHUNK,
        defaults={},
        constream=[],
        instream=[
            [
                StreamItemFragment(
                    key=1, kind=StreamKind.INT, nullable=False, scope=PortScope.GLOBAL
                )
            ]
        ],
        outstream=[
            [
                StreamItemFragment(
                    key=1, kind=StreamKind.INT, nullable=False, scope=PortScope.GLOBAL
                )
            ]
        ],
    )


@pytest.fixture(scope="session")
def reactive_split_node():
    return FlowNodeFragmentBaseReactiveNode(
        id=1,
        position=FlowNodeFragmentBasePosition(x=0, y=0),
        implementation=ReactiveImplementationModelInput.CHUNK,
        defaults={},
        constream=[],
        instream=[
            [
                StreamItemFragment(
                    key=1, kind=StreamKind.INT, nullable=True, scope=PortScope.GLOBAL
                ),
                StreamItemFragment(
                    key=1, kind=StreamKind.INT, nullable=True, scope=PortScope.GLOBAL
                ),
                StreamItemFragment(
                    key=1, kind=StreamKind.INT, nullable=True, scope=PortScope.GLOBAL
                ),
            ]
        ],
        outstream=[
            [
                StreamItemFragment(
                    key=1, kind=StreamKind.INT, nullable=False, scope=PortScope.GLOBAL
                )
            ],
            [
                StreamItemFragment(
                    key=1, kind=StreamKind.INT, nullable=False, scope=PortScope.GLOBAL
                )
            ],
            [
                StreamItemFragment(
                    key=1, kind=StreamKind.INT, nullable=False, scope=PortScope.GLOBAL
                )
            ],
        ],
    )
