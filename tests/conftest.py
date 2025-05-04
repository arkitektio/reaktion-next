"""Conftest file for pytest fixtures."""

import pytest
from fluss_next.api.schema import (
    MapStrategy,
    ReactiveNode,
    BaseGraphNodePosition,
    ReactiveImplementation,
    PortKind,
    GraphNodeKind,
    FlussPort
    
)



@pytest.fixture(scope="session")
def reactive_zip_node() -> ReactiveNode:
    """Fixture for a reactive zip node."""
    return ReactiveNode(
        id=1,
        position=BaseGraphNodePosition(x=0, y=0),
        implementation=ReactiveImplementation.ZIP,
        constantsMap={},
        globalsMap={},
        title="Zip",
        kind=GraphNodeKind.REACTIVE,
        description="Zip two streams together",
        constants=[],
        voids=[],
        ins=[
            [
                FlussPort(
                    key="x", kind=PortKind.INT, nullable=False,
                )
            ],
            [
                FlussPort(
                    key="y", kind=PortKind.INT, nullable=False
                )
            ],
        ],
        outs=[
            [
                FlussPort(
                    key="return0", kind=PortKind.INT, nullable=False, 
                )
            ]
        ],
    )

