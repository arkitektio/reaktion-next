import logging
from typing import Callable, Dict, Optional
import asyncio
from pydantic import BaseModel, Field

from fluss_next.api.schema import (
    ArgNodeFragment,
    RekuestNodeFragmentBase,
    FlowFragment,
    ReactiveNodeFragment,
    RekuestFilterNodeFragment,
    ReturnNodeFragment,
    acreate_run,
    asnapshot,
    aclose_run,
    atrack,
)
from reaktion_next.atoms.transport import AtomTransport

from reaktion_next.atoms.utils import atomify
from reaktion_next.contractors import NodeContractor, arkicontractor
from reaktion_next.events import EventType, InEvent, OutEvent

from reaktion_next.utils import connected_events
from rekuest_next.actors.base import Actor
from rekuest_next.api.schema import (
    AssignationEventKind,
    ReservationFragment,
    NodeFragment,
)
from rekuest_next.postmans.utils import RPCContract, ContractStatus
from typing import Any
from rekuest_next.collection.collector import AssignationCollector
from rekuest_next.actors.transport.types import AssignTransport
from rekuest_next.actors.types import Assignment, Passport

logger = logging.getLogger(__name__)


class NodeState(BaseModel):
    latestevent: OutEvent


class FlowActor(Actor):
    definition: NodeFragment
    is_generator: bool = False
    flow: FlowFragment
    agent: Any
    contracts: Dict[str, RPCContract] = Field(default_factory=dict)
    expand_inputs: bool = False
    shrink_outputs: bool = False
    provided: bool = False
    arkitekt_contractor: NodeContractor = arkicontractor
    snapshot_interval: int = 40
    condition_snapshot_interval: int = 40
    contract_states: Dict[str, ContractStatus] = Field(default_factory=dict)
    contract_t: int = 0

    # Functionality for running the flow

    # Assign Related Functionality
    run_mutation: Callable = acreate_run
    snapshot_mutation: Callable = asnapshot
    track_mutation: Callable = atrack
    close_mutation: Callable = aclose_run

    atomifier: Callable = atomify
    """ Atomifier is a function that takes a node and returns an atom """

    run_states: Dict[
        str,
        Dict[str, NodeState],
    ] = Field(default_factory=dict)

    reservation_state: Dict[str, ReservationFragment] = Field(default_factory=dict)
    _lock: Optional[asyncio.Lock] = None

    async def on_provide(self, passport: Passport):
        self._lock = asyncio.Lock()

    async def on_local_log(self, reference, *args, **kwargs):
        logger.log(f"Contract log for {reference} {args} {kwargs}")

    async def on_assign(
        self,
        assignment: Assignment,
        collector: AssignationCollector,
        transport: AssignTransport,
    ):
        try:
            rekuest_nodes = [
                x
                for x in self.flow.graph.nodes
                if isinstance(x, RekuestNodeFragmentBase)
            ]

            rekuest_contracts = {
                node.id: await self.arkitekt_contractor(node, self)
                for node in rekuest_nodes
            }

            self.contracts = {**rekuest_contracts}
            futures = [contract.aenter() for contract in self.contracts.values()]
            await asyncio.gather(*futures)

            run = await self.run_mutation(
                assignation=assignment.assignation,
                flow=self.flow,
                snapshot_interval=self.snapshot_interval,
            )

            t = 0
            state = {}
            await self.snapshot_mutation(run=run, events=list(state.values()), t=t)

            event_queue = asyncio.Queue()

            atomtransport = AtomTransport(queue=event_queue)

            argNode = [
                x for x in self.flow.graph.nodes if isinstance(x, ArgNodeFragment)
            ][0]
            returnNode = [
                x for x in self.flow.graph.nodes if isinstance(x, ReturnNodeFragment)
            ][0]

            participatingNodes = [
                x
                for x in self.flow.graph.nodes
                if isinstance(x, RekuestNodeFragmentBase)
                or isinstance(x, ReactiveNodeFragment)
            ]

            stream = argNode.outs[0]
            stream_keys = []
            for i in stream:
                stream_keys.append(i.key)

            return_stream = returnNode.outs[0]

            global_keys = []
            for i in self.flow.graph.globals:
                global_keys.append(i.port.key)

            globalMap: Dict[str, Dict[str, Any]] = {}
            streamMap: Dict[str, Any] = {}

            for port in self.definition.args:
                if port.key in stream_keys:
                    streamMap[port.key] = assignment.args[port.key]
                if port.key in global_keys:
                    for i in self.flow.graph.globals:
                        if i.port.key == port.key:
                            for map in i.to_keys:
                                nodeid, key = map.split(".")
                                globalMap.setdefault(nodeid, {})[key] = assignment.args[
                                    port.key
                                ]

            atoms = {
                x.id: self.atomifier(
                    x,
                    atomtransport,
                    self.contracts.get(x.id, None),
                    globalMap.get(x.id, {}),
                    assignment,
                    alog=transport.log_event,
                )
                for x in participatingNodes
            }

            await asyncio.gather(*[atom.aenter() for atom in atoms.values()])
            tasks = [asyncio.create_task(atom.start()) for atom in atoms.values()]
            logger.info("Starting all Atoms")
            value = [streamMap[key] for key in stream_keys]

            initial_event = OutEvent(
                handle="return_0",
                type=EventType.NEXT,
                source=argNode.id,
                value=value,
                caused_by=[t],
            )
            initial_done_event = OutEvent(
                handle="return_0",
                type=EventType.COMPLETE,
                source=argNode.id,
                caused_by=[t],
            )

            logger.info(f"Putting initial event {initial_event}")

            await event_queue.put(initial_event)
            await event_queue.put(initial_done_event)

            edge_targets = [e.target for e in self.flow.graph.edges]
            nodes_without_instream = [
                x
                for x in participatingNodes
                if len(x.ins[0]) == 0 and x.id not in edge_targets
            ]

            for node in nodes_without_instream:
                assert node.id in atoms, "Atom not found. Should not happen."
                atom = atoms[node.id]

                initial_event = InEvent(
                    target=node.id,
                    handle="arg_0",
                    type=EventType.NEXT,
                    value=[],
                    current_t=t,
                )
                done_event = InEvent(
                    target=node.id,
                    handle="arg_0",
                    type=EventType.COMPLETE,
                    current_t=t,
                )

                await atom.put(initial_event)
                await atom.put(done_event)

            complete = False

            returns = []

            while not complete:
                event: OutEvent = await event_queue.get()
                event_queue.task_done()

                if event.type == EventType.ERROR:
                    # raise event.value
                    pass

                track = await self.track_mutation(
                    reference=event.source + "_track_" + str(t),
                    run=run,
                    source=event.source,
                    handle=event.handle,
                    caused_by=event.caused_by,
                    value=(
                        event.value
                        if event.value and not isinstance(event.value, Exception)
                        else str(event.value)
                    ),
                    kind=event.type,
                    t=t,
                )
                state[event.source] = track.id

                # We tracked the events and proceed

                if t % self.snapshot_interval == 0:
                    await self.snapshot_mutation(
                        run=run, events=list(state.values()), t=t
                    )

                # Creat new events with the new timepoint
                spawned_events = connected_events(self.flow.graph, event, t)
                # Increment timepoint
                t += 1
                # needs to be the old one for now
                if not spawned_events:
                    logger.warning(f"No events spawned from {event}")

                for spawned_event in spawned_events:
                    logger.info(f"-> {spawned_event}")

                    if spawned_event.target == returnNode.id:
                        track = await self.track_mutation(
                            reference=event.source + "_track_" + str(t),
                            run=run,
                            source=spawned_event.target,
                            handle="return_0",
                            caused_by=event.caused_by,
                            value=(
                                spawned_event.value
                                if spawned_event.value
                                and not isinstance(spawned_event.value, Exception)
                                else str(spawned_event.value)
                            ),
                            kind=spawned_event.type,
                            t=t,
                        )
                        if spawned_event.type == EventType.NEXT:
                            yield_dict = {}

                            for port, value in zip(return_stream, spawned_event.value):
                                yield_dict[port.key] = value

                            await transport.log_event(
                                kind=AssignationEventKind.YIELD,
                                returns=yield_dict,
                            )

                        if spawned_event.type == EventType.ERROR:
                            raise spawned_event.value

                        if spawned_event.type == EventType.COMPLETE:
                            await self.snapshot_mutation(
                                run=run, events=list(state.values()), t=t
                            )
                            await transport.log_event(
                                kind=AssignationEventKind.DONE,
                                message="Done ! :)",
                            )

                            logger.info("Done ! :)")

                    else:
                        assert (
                            spawned_event.target in atoms
                        ), "Unknown target. Your flow is connected wrong"
                        if spawned_event.target in atoms:
                            await atoms[spawned_event.target].put(spawned_event)

            for task in tasks:
                task.cancel()

            await asyncio.gather(*tasks, return_exceptions=True)
            logging.info("Collecting...")
            await self.collector.collect(assignment.id)
            logging.info("Done ! :)")
            await self.close_mutation(run=run.id)

        except asyncio.CancelledError:
            for task in tasks:
                task.cancel()
            await self.snapshot_mutation(run=run, events=list(state.values()), t=t)

            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True), timeout=4
                )
            except asyncio.TimeoutError:
                pass

            await self.close_mutation(run=run.id)

            await self.collector.collect(assignment.id)
            await transport.log_event(
                kind=AssignationEventKind.CANCELLED, message="Cancelled"
            )

        except Exception as e:
            logging.critical(f"Assignation {assignment} failed", exc_info=True)
            await self.snapshot_mutation(run=run, events=list(state.values()), t=t)

            await self.close_mutation(run=run.id)
            await self.collector.collect(assignment.id)
            await transport.log_event(
                kind=AssignationEventKind.CRITICAL,
                message=repr(e),
            )

    async def on_unprovide(self):
        for contract in self.contracts.values():
            await contract.aexit()
