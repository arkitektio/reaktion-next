from typing import Protocol, runtime_checkable
from rekuest_next.postmans.utils import RPCContract, arkiuse, mockuse, actoruse
from fluss_next.api.schema import (
    RekuestNodeFragmentBase,
)
from rekuest_next.api.schema import afind, BindsInput
from rekuest_next.postmans.vars import get_current_postman
from rekuest_next.actors.base import Actor
from rekuest_next.utils import reserved


@runtime_checkable
class NodeContractor(Protocol):
    async def __call__(
        self, node: RekuestNodeFragmentBase, actor: Actor
    ) -> RPCContract: ...


async def arkicontractor(node: RekuestNodeFragmentBase, actor: Actor) -> RPCContract:
    arkinode = await afind(hash=node.hash)
    return reserved(node=arkinode, reference=node.id)


async def arkimockcontractor(
    node: RekuestNodeFragmentBase, actor: Actor
) -> RPCContract:
    return mockuse(
        node=node,
        provision=actor.passport.provision,
        shrink_inputs=False,
        shrink_outputs=False,
    )  # No need to shrink inputs/outputs for arkicontractors
