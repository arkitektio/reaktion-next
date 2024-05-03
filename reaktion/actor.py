import logging
from typing import Callable, Dict
import asyncio
from pydantic import BaseModel, Field

from fluss.api.schema import (
    ArgNodeFragment,
    ArkitektNodeFragment,
    FlowFragment,
    LocalNodeFragment,
    ReactiveNodeFragment,
    ArkitektFilterNodeFragment,
    ReturnNodeFragment,
    arun,
    asnapshot,
    atrack,
    acondition_snapshot,
    astart_trace,
    atrace,
)
from reaktion_next.atoms.transport import AtomTransport

from reaktion_next.atoms.utils import atomify
from reaktion_next.contractors import NodeContractor, arkicontractor
from reaktion_next.events import EventType, InEvent, OutEvent

from reaktion_next.utils import connected_events
from rekuest.actors.base import Actor
from rekuest.api.schema import (
    AssignationStatus,
    ProvisionStatus,
    ReservationFragment,
    ReservationStatus,
    ProvisionMode,
    NodeFragment,
)
from rekuest.messages import Assignation, Provision
from rekuest.postmans.utils import RPCContract, ContractStatus
from typing import Any
from rekuest.collection.collector import AssignationCollector, ActorCollector
from rekuest.actors.transport.types import AssignTransport
from rekuest.actors.types import Assignment, Passport
from rekuest.actors.transport.local_transport import ProxyActorTransport

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
    provided = False
    is_generator: bool = False
    arkitekt_contractor: NodeContractor = arkicontractor
    snapshot_interval: int = 40
    condition_snapshot_interval: int = 40
    contract_states: Dict[str, ContractStatus] = Field(default_factory=dict)
    contract_t: int = 0

    # Functionality for running the flow

    # Assign Related Functionality
    run_mutation: Callable = arun
    snapshot_mutation: Callable = asnapshot
    track_mutation: Callable = atrack

    start_trace_mutation: Callable = astart_trace
    condition_snapshot_mutation: Callable = acondition_snapshot
    trace_mutation: Callable = atrace

    atomifier: Callable = atomify
    """ Atomifier is a function that takes a node and returns an atom """

    run_states: Dict[
        str,
        Dict[str, NodeState],
    ] = Field(default_factory=dict)

    reservation_state: Dict[str, ReservationFragment] = Field(default_factory=dict)
    _lock = None
    _condition = None

    async def on_provide(self, passport: Passport):
        self._lock = asyncio.Lock()

        self._condition = await self.start_trace_mutation(
            provision=passport.provision,
            flow=self.flow,
            snapshot_interval=self.condition_snapshot_interval,
        )

        [x for x in self.flow.graph.nodes if isinstance(x, ArgNodeFragment)][0]
        [x for x in self.flow.graph.nodes if isinstance(x, ReturnNodeFragment)][0]

        arkitektNodes = [
            x
            for x in self.flow.graph.nodes
            if isinstance(x, ArkitektNodeFragment)
            or isinstance(x, ArkitektFilterNodeFragment)
        ]

        arkitekt_contracts = {
            node.id: await self.arkitekt_contractor(node, self)
            for node in arkitektNodes
        }

        self.contracts = {**arkitekt_contracts}
        futures = [contract.aenter() for contract in self.contracts.values()]
        await asyncio.gather(*futures)

    async def on_local_log(self, reference, *args, **kwargs):
        logger.log(f"Contract log for {reference} {args} {kwargs}")

    async def on_local_change(
        self,
        reference,
        status: ProvisionStatus = None,
        message: str = None,
        mode: ProvisionMode = None,
    ):
        await self.trace_mutation(
            condition=self._condition, source=reference, value=str(status)
        )

    async def on_contract_change(
        self, state: ContractStatus = None, reference: str = None
    ):
        logger.debug(f"Contract change {reference}: {state} ")

        async with self._lock:
            if reference:
                self.contract_states[reference] = await self.trace_mutation(
                    condition=self._condition,
                    source=reference,
                    state=state,
                    value="Nothing",
                )

            inactive_contracts = [
                res
                for res in self.contracts.values()
                if res.state != ContractStatus.ACTIVE
            ]

            if len(inactive_contracts) > 0:
                await self.aset_status(
                    status=ProvisionStatus.CRITICAL,
                    message="One or more contracts are inactive",
                )
                logger.warning("Contract is inactive")

            else:
                await self.aset_status(
                    status=ProvisionStatus.ACTIVE,
                )

            if self.contract_t % self.snapshot_interval == 0:
                await self.condition_snapshot_mutation(
                    condition=self._condition,
                    events=list(self.contract_states.values()),
                )

            self.contract_t += 1

    async def on_assign(
        self,
        assignment: Assignment,
        collector: AssignationCollector,
        transport: AssignTransport,
    ):
        run = await self.run_mutation(
            assignation=assignment.assignation,
            flow=self.flow,
            snapshot_interval=self.snapshot_interval,
        )
        print(self.is_generator)

        await transport.log(level="INFO", message="Starting")

        t = 0
        state = {}
        await self.snapshot_mutation(run=run, events=list(state.values()), t=t)

        try:
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
                if isinstance(x, ArkitektNodeFragment)
                or isinstance(x, ArkitektFilterNodeFragment)
                or isinstance(x, ReactiveNodeFragment)
                or isinstance(x, LocalNodeFragment)
            ]

            await transport.log(level="INFO", message="Set up the graph")

            stream = self.flow.graph.args
            stream_keys = []
            for i in stream:
                stream_keys.append(i.key)

            global_keys = []
            for i in self.flow.graph.globals:
                global_keys.append(i.port.key)

            globalMap: Dict[str, Dict[str, Any]] = {}
            streamMap: Dict[str, Any] = {}

            assert len(self.definition.args) == len(
                assignment.args
            ), "Wrong number of args"

            for port, arg in zip(self.definition.args, assignment.args):
                if port.key in stream_keys:
                    streamMap[port.key] = arg
                if port.key in global_keys:
                    for i in self.flow.graph.globals:
                        if i.port.key == port.key:
                            for map in i.to_keys:
                                nodeid, key = map.split(".")
                                globalMap.setdefault(nodeid, {})[key] = arg

            async def ass_log(assignation: Assignation, level, message):
                await transport.log(level, message)
                logging.info(f"{assignation}, {message}")

            atoms = {
                x.id: self.atomifier(
                    x,
                    atomtransport,
                    self.contracts.get(x.id, None),
                    globalMap.get(x.id, {}),
                    assignment,
                    alog=ass_log,
                )
                for x in participatingNodes
            }

            await transport.log(level="INFO", message="Atomification complete")

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
                if len(x.instream[0]) == 0 and x.id not in edge_targets
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

                if self.flow.brittle:
                    if event.type == EventType.ERROR:
                        raise event.value

                track = await self.track_mutation(
                    run=run,
                    source=event.source,
                    handle=event.handle,
                    caused_by=event.caused_by,
                    value=event.value
                    if event.value and not isinstance(event.value, Exception)
                    else str(event.value),
                    type=event.type,
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
                        if spawned_event.type == EventType.NEXT:
                            returns = spawned_event.value
                            if self.is_generator:
                                print("Yielded")
                                await transport.change(
                                    status=AssignationStatus.YIELD,
                                    returns=returns,
                                )

                        if spawned_event.type == EventType.ERROR:
                            await self.snapshot_mutation(
                                run=run, events=list(state.values()), t=t
                            )
                            raise spawned_event.value

                        if spawned_event.type == EventType.COMPLETE:
                            await self.snapshot_mutation(
                                run=run, events=list(state.values()), t=t
                            )
                            complete = True
                            if not self.is_generator:
                                await transport.change(
                                    status=AssignationStatus.RETURNED,
                                    returns=returns,
                                )
                            else:
                                print("Done")
                                await transport.change(
                                    status=AssignationStatus.DONE,
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

            await self.collector.collect(assignment.id)
            await transport.change(status=AssignationStatus.CANCELLED)

        except Exception as e:
            logging.critical(f"Assignation {assignment} failed", exc_info=True)
            await self.snapshot_mutation(run=run, events=list(state.values()), t=t)
            await transport.log(message="Starting", level=AssignationStatus.ERROR)

            await self.collector.collect(assignment.id)
            await transport.change(
                status=AssignationStatus.CRITICAL,
                message=repr(e),
            )

    async def on_unprovide(self):
        for contract in self.contracts.values():
            await contract.aexit()
