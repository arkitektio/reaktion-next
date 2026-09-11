"""Registers the generic ``run_flow`` action with the default app registry.

Importing this module makes the implementation available to any rekuest
agent built from the default registry. The rekuest server's "higher order
implementation" feature discovers it via the ``run_flow`` interface and
forwards validated flow arguments to it.
"""

from rekuest_next.actors.types import RegisterConfig
from rekuest_next.app import get_default_app_registry
from rekuest_next.register import register_func
from rekuest_next.structures.default import get_default_structure_registry

from reaktion_next.actions import flow_actifier, run_flow

# A single actor serves all flow runs, so they must not queue behind each
# other (the FunctionalActor default is "serial").
run_flow_definition, run_flow_builder = register_func(
    run_flow,
    structure_registry=get_default_structure_registry(),
    implementation_registry=get_default_app_registry(),
    config=RegisterConfig(
        interface="run_flow",
        name="Run Flow",
        bypass_expand=True,
        bypass_shrink=True,
        concurrency="parallel",
    ),
    actifier=flow_actifier,
)
