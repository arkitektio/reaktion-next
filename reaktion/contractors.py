from typing import Protocol, runtime_checkable
from rekuest_next.postmans.utils import RPCContract, arkiuse, mockuse, actoruse
from fluss_next.api.schema import (
    RekuestNodeFragmentBase,
)
from rekuest_next.api.schema import afind, BindsInput
from rekuest_next.postmans.vars import get_current_postman
from rekuest_next.actors.base import Actor


@runtime_checkable
class NodeContractor(Protocol):
    async def __call__(
        self, node: RekuestNodeFragmentBase, actor: Actor
    ) -> RPCContract: ...


async def arkicontractor(node: RekuestNodeFragmentBase, actor: Actor) -> RPCContract:
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
        return arkiuse(
            binds=BindsInput(clients=node.binds.clients, templates=node.binds.templates)
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


async def arkimockcontractor(
    node: RekuestNodeFragmentBase, actor: Actor
) -> RPCContract:
    return mockuse(
        node=node,
        provision=actor.passport.provision,
        shrink_inputs=False,
        shrink_outputs=False,
    )  # No need to shrink inputs/outputs for arkicontractors
