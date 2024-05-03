from typing import Protocol, runtime_checkable
from rekuest.postmans.utils import RPCContract, arkiuse, mockuse, actoruse
from fluss.api.schema import (
    ArkitektNodeFragment,
    FlowNodeFragmentBaseArkitektNode,
    LocalNodeFragment,
)
from rekuest.api.schema import afind, ReserveBindsInput, amytemplatefor, NodeScope
from rekuest.postmans.vars import get_current_postman
from rekuest.structures.registry import get_current_structure_registry
from rekuest.actors.base import Actor


@runtime_checkable
class NodeContractor(Protocol):
    async def __call__(
        self, node: ArkitektNodeFragment, actor: Actor
    ) -> RPCContract: ...


async def arkicontractor(node: ArkitektNodeFragment, actor: Actor) -> RPCContract:
    try:
        template = await amytemplatefor(
            hash=node.hash, instance_id=actor.agent.instance_id
        )

        return actoruse(
            template=template,
            supervisor=actor,
            reference=node.id,
            state_hook=actor.on_contract_change,
            assign_timeout=node.assign_timeout or None,
            yield_timeout=node.yield_timeout or None,
            max_retries=node.max_retries,
            retry_delay_ms=node.retry_delay,
        )
    except Exception as e:
        arkinode = await afind(hash=node.hash)
        assert (
            arkinode.scope == NodeScope.GLOBAL
        ), "Non GlobalNodes that are not implemented on this agent cannot be put into a workflow"
        return arkiuse(
            binds=ReserveBindsInput(
                clients=node.binds.clients, templates=node.binds.templates
            )
            if node.binds
            else None,
            hash=node.hash,
            postman=get_current_postman(),
            provision=actor.passport.provision,
            reference=node.id,
            state_hook=actor.on_contract_change,
            assign_timeout=node.assign_timeout or None,
            yield_timeout=node.yield_timeout or None,
            reserve_timeout=node.reserve_timeout or None,
            max_retries=node.max_retries,
            retry_delay_ms=node.retry_delay,
        )  # No need to shrink inputs/outsputs for arkicontractors


async def arkimockcontractor(node: ArkitektNodeFragment, actor: Actor) -> RPCContract:
    return mockuse(
        node=node,
        provision=actor.passport.provision,
        shrink_inputs=False,
        shrink_outputs=False,
    )  # No need to shrink inputs/outputs for arkicontractors
