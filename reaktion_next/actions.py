"""The generic ``run_flow`` action.

A single registered implementation that runs any fluss flow: the rekuest
server derives a typed "higher order implementation" from the flow graph,
validates and shrinks the caller's arguments, and forwards them here in raw
form. The definition is handcrafted (via :func:`flow_actifier`) because its
``kwargs``/``returns`` ports carry arbitrary, server-validated values that
cannot be expressed through signature inference.
"""

from functools import partial
from typing import Any, AsyncGenerator, Dict, Optional, Tuple

from fluss_next.api.schema import Flow, aget_flow
from rath.scalars import ID
from rekuest_next.actors.actify import derive_implementation_details
from rekuest_next.actors.functional import GEN, FunctionalActor
from rekuest_next.actors.types import (
    ActorBuilder,
    AnyFunction,
    ImplementationDetails,
    RegisterConfig,
)
from rekuest_next.api.schema import (
    ActionKind,
    ArgPortInput,
    DefinitionInput,
    PortKind,
    ReturnPortInput,
)
from rekuest_next.structures.registry import StructureRegistry

from reaktion_next.engine import arun_flow


async def run_flow(
    flow: str, kwargs: Dict[str, Any]
) -> AsyncGenerator[Dict[str, Any], None]:
    """Run Flow

    Runs a fluss flow with pre-validated, shrunk argument values keyed by the
    flow's arg and global port keys, yielding raw return dicts keyed by the
    flow's return port keys.
    """
    # Inputs arrive unexpanded (bypass_expand), so the flow port is a raw ID.
    resolved = await aget_flow(id=ID.validate(flow))

    async for returns in arun_flow(resolved, kwargs or {}):
        yield returns


def build_run_flow_definition(
    structure_registry: StructureRegistry,
) -> DefinitionInput:
    """Build the handcrafted definition for the ``run_flow`` action."""
    flow_port = structure_registry.get_argport_for_cls(
        Flow,
        "flow",
        nullable=False,
        description="The fluss flow to run",
    )

    # The DICT child kind is a placeholder: values are validated by the
    # server's higher-order implementation, never against this port.
    kwargs_port = ArgPortInput(
        key="kwargs",
        kind=PortKind.DICT,
        nullable=False,
        description=(
            "Shrunk values keyed by the flow's arg and global port keys, "
            "validated by the server"
        ),
        children=(
            ArgPortInput(
                key="...",
                kind=PortKind.STRING,
                nullable=True,
            ),
        ),
    )

    returns_port = ReturnPortInput(
        key="returns",
        kind=PortKind.DICT,
        nullable=False,
        description="Raw values keyed by the flow's return port keys",
        children=(
            ReturnPortInput(
                key="...",
                kind=PortKind.STRING,
                nullable=True,
            ),
        ),
    )

    return DefinitionInput(
        name="Run Flow",
        key="run_flow",
        version="1",
        kind=ActionKind.GENERATOR,
        description="Runs a fluss flow as a generic higher-order executor",
        args=(flow_port, kwargs_port),
        returns=(returns_port,),
        stateful=False,
        isDev=False,
        collections=(),
        portGroups=(),
        isTestFor=(),
        interfaces=("flow_runner",),
    )


def flow_actifier(
    function: AnyFunction,
    structure_registry: StructureRegistry,
    config: Optional[RegisterConfig] = None,
) -> Tuple[DefinitionInput, ImplementationDetails, ActorBuilder]:
    """Actifier for ``run_flow``: like ``reactify`` but with the handcrafted
    definition instead of a signature-derived one."""
    config = config or RegisterConfig()

    implementation_details = derive_implementation_details(function, config)
    definition = build_run_flow_definition(structure_registry)

    return (
        definition,
        implementation_details,
        partial(
            FunctionalActor,
            iterator=GEN,
            assign=function,
            expand_inputs=False,
            shrink_outputs=False,
            structure_registry=structure_registry,
            definition=definition,
            state_variables=implementation_details.state_variables,
            state_returns=implementation_details.state_returns,
            context_variables=implementation_details.context_variables,
            context_returns=implementation_details.context_returns,
            dependency_variables=implementation_details.dependency_variables,
            locks=implementation_details.locks,
            concurrency=config.concurrency,
        ),
    )
