from typing import Protocol, runtime_checkable
from rekuest_next.postmans.contract import RPCContract
from rekuest_next.postmans.utils import localuse
from fluss_next.api.schema import (
    RekuestNodeBase,
)
from rekuest_next.api.schema import afind, BindsInput
from rekuest_next.postmans.vars import get_current_postman
from rekuest_next.actors.base import Actor
from rekuest_next.utils import reserved, direct


@runtime_checkable
class NodeContractor(Protocol):
    async def __call__(self, node: RekuestNodeBase, actor: Actor) -> RPCContract: ...


async def arkicontractor(node: RekuestNodeBase, actor: Actor) -> RPCContract:
    """A contractor that can either spawn local, actors
    of use remote actors to perform the task


    """

    localtemplate = await actor.agent.afind_local_template_for_nodehash(node.hash)

    if localtemplate:
        return localuse(template=localtemplate, supervisor=actor, reference=node.id)

    arkinode = await afind(hash=node.hash)

    return direct(node=arkinode, reference=node.id)


async def arkimockcontractor(node: RekuestNodeBase, actor: Actor) -> RPCContract:
    return mockuse(
        node=node,
        provision=actor.passport.provision,
        shrink_inputs=False,
        shrink_outputs=False,
    )  # No need to shrink inputs/outputs for arkicontractors
