from typing import Any, List, Optional
from rekuest_next.api.schema import AssignationLogLevel
from rekuest_next.messages import Assignation
from rekuest_next.postmans.utils import ReservationContract
from fluss_next.api.schema import ArkitektNode
from reaktion_next.atoms.generic import MapAtom
from reaktion_next.events import Returns


class TemplateMapAtom(MapAtom):
    node: ArkitektNode
    contract: ReservationContract

    async def map(self, args: Returns) -> Optional[List[Any]]:
        defaults = self.node.defaults or {}
        returns = await self.contract.aassign(
            *args,
            **defaults,
            alog=self.alog_arkitekt,
            parent=self.assignment.assignation,
        )
        return returns
        # return await self.contract.aassign(*args)

    async def alog_arkitekt(
        self, assignation: Assignation, level: AssignationLogLevel, message: str
    ):
        if self.alog:
            await self.alog(self.node.id, level, message)
