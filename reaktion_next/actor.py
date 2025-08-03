import logging
from typing import Dict
import asyncio
from pydantic import BaseModel, Field

from fluss_next.api.schema import (
    ArgNode,
    RekuestActionNodeBase,
    Flow,
    ReactiveNode,
    ReturnNode,
    acreate_run,
    asnapshot,
    aclose_run,
    TrackMutationTrack,
    atrack,
)
from rath.scalars import ID
from reaktion_next.atoms.transport import AtomTransport

from reaktion_next.atoms.utils import atomify
from reaktion_next.contractors import NodeContractor, arkicontractor
from reaktion_next.events import (
    ErrorInEvent,
    EventType,
    InEvent,
    OutEvent,
    NextInEvent,
    CompleteInEvent,
    NextOutEvent,
    CompleteOutEvent,
)
from rekuest_next import messages
from reaktion_next.utils import connected_events
from rekuest_next.actors.base import Actor
from rekuest_next.api.schema import (
    Reservation,
    acollect,
)
from reaktion_next.rpc_contract import RPCContract


from typing import Any
from rekuest_next.messages import Assign
from reaktion_next.reference_counter import ReferenceCounter

logger = logging.getLogger(__name__)


class NodeState(BaseModel):
    """NodeState is a state of a node in the flow."""

    latestevent: OutEvent


class FlowActor(Actor):
    """FlowActor is an Actor that runs a workflow.


    Flow actors load the flow during execution and then run the flow
    by sending the events to the nodes in the flow. These nodes acts
    as "Atoms" that are executed in parallel.


    """

    is_generator: bool = False
    """is_generator is a flag that indicates if the actor is a generator or not. """
    flow: Flow = Field(
        description="Flow is the flow that the actor runs. It will be set by the flow extension.",
    )
    contracts: Dict[str, RPCContract] = Field(
        default_factory=dict, description="Contracts that are used to run the flow. "
    )
    expand_inputs: bool = False
    shrink_outputs: bool = False
    provided: bool = False
    arkitekt_contractor: NodeContractor = Field(
        default=arkicontractor,
        description="A node contractor that can either spawn local, actors of use remote actors to perform the task",
    )
    """ Arkitekt contractor is a function that takes a node and returns a contract """
    snapshot_interval: int = Field(
        default=40,
        description="Snapshot interval is the interval at which the flow is snapshotted. "
        "This is used to track the state of the flow and to resume it later.",
    )
    """ Snapshot interval is the interval at which the flow is snapshotted. """
    condition_snapshot_interval: int = 40
    contract_t: int = 0

    # Functionality for running the flow

    atomifier = atomify
    """ Atomifier is a function that takes a node and returns an atom """

    run_states: Dict[
        str,
        Dict[str, NodeState],
    ] = Field(default_factory=dict)

    reservation_state: Dict[str, Reservation] = Field(default_factory=dict)

    async def on_assign(
        self,
        assignment: Assign,
    ) -> None:
        """On assign is called when the workflow is run"""
        reference_counter = ReferenceCounter()

        run = await acreate_run(
            assignation=ID.validate(assignment.assignation),
            flow=self.flow.id,
            snapshot_interval=self.snapshot_interval,
        )
        # Runs track the state of the flow interactively

        t = 0
        state: Dict[ID, TrackMutationTrack] = {}
        tasks = []

        try:
            rekuest_nodes = [
                x for x in self.flow.graph.nodes if isinstance(x, RekuestActionNodeBase)
            ]

            rekuest_contracts = {
                node.id: await self.arkitekt_contractor(node, self)
                for node in rekuest_nodes
            }

            self.contracts = {**rekuest_contracts}
            futures = [contract.aenter() for contract in self.contracts.values()]
            await asyncio.gather(*futures)

            await asnapshot(run=run.id, events=list(state.values()), t=t)

            event_queue: asyncio.Queue[OutEvent] = asyncio.Queue()

            atomtransport = AtomTransport(queue=event_queue)

            argNode = [x for x in self.flow.graph.nodes if isinstance(x, ArgNode)][0]
            returnNode = [
                x for x in self.flow.graph.nodes if isinstance(x, ReturnNode)
            ][0]

            participatingNodes = [
                x
                for x in self.flow.graph.nodes
                if isinstance(x, RekuestActionNodeBase) or isinstance(x, ReactiveNode)
            ]

            # Return node has only one input stream the returns
            return_stream = returnNode.ins[0]
            # Arg node has only one output stream
            stream = argNode.outs[0]
            stream_keys: list[str] = []
            for i in stream:
                stream_keys.append(i.key)

            globalMap: Dict[str, Dict[str, Any]] = {}
            streamMap: Dict[str, Any] = {}

            # We need to map the global keys to the actual values from the kwargs
            # Each node has a globals_map that maps the port key to the global key
            # So we need to map the global key to the actual value from the kwargs

            global_keys: list[str] = []
            for i in self.flow.graph.globals:
                global_keys.append(i.port.key)

            for node in participatingNodes:
                for port_key, global_key in node.globals_map.items():
                    if global_key not in global_keys:
                        raise ValueError(
                            f"Global key {global_key} not found in globals"
                        )
                    if node.id not in globalMap:
                        globalMap[node.id] = {}

                    globalMap[node.id][port_key] = assignment.args[global_key]

            # Print the global Map for debugging

            # We need to map the stream keys to the actual values from the kwargs
            # Args nodes have a stream that maps the port key to the stream key

            for key in stream_keys:
                if key in assignment.args:
                    streamMap[key] = assignment.args[key]
                else:
                    raise ValueError(
                        f"Stream key {key} not found in args {assignment.args}"
                    )

            for key in global_keys:
                if key not in assignment.args:
                    raise ValueError(
                        f"Global key {key} not found in args {assignment.args}"
                    )
                streamMap[key] = assignment.args[key]

            atoms = {
                x.id: atomify(
                    x,
                    atomtransport,
                    self.contracts.get(x.id, None),
                    globalMap.get(x.id, {}),
                    assignment,
                    reference_counter,
                    self,
                )
                for x in participatingNodes
            }

            await asyncio.gather(*[atom.aenter() for atom in atoms.values()])
            tasks = [asyncio.create_task(atom.start()) for atom in atoms.values()]
            logger.info("Starting all Atoms")
            value = [streamMap[key] for key in stream_keys]

            initial_event = NextOutEvent(
                handle="return_0",
                source=argNode.id,
                value=value,
                caused_by=[t],
            )
            initial_done_event = CompleteOutEvent(
                handle="return_0",
                type=EventType.COMPLETE,
                source=argNode.id,
                caused_by=[t],
            )

            logger.info(f"Putting initial event {initial_event}")

            await event_queue.put(initial_event)
            await event_queue.put(initial_done_event)

            edge_targets = [e.target for e in self.flow.graph.edges]

            # Get all nodes that have no instream
            nodes_without_instream = [
                x
                for x in participatingNodes
                if len(x.ins[0]) == 0 and x.id not in edge_targets
            ]

            # Get all nodes that are connected to argNode
            connected_arg_nodes = [
                e.target for e in self.flow.graph.edges if e.source == argNode.id
            ]

            # Get the nodes that are not connected to argNode AND have no instream
            nodes_without_instream = [
                node
                for node in nodes_without_instream
                if node.id not in connected_arg_nodes
            ]

            # Send initial events to nodes without instream (they are not connected to argNode so need to be triggered)
            for node in nodes_without_instream:
                assert node.id in atoms, "Atom not found. Should not happen."
                atom = atoms[node.id]

                initial_event = NextInEvent(
                    target=node.id,
                    handle="arg_0",
                    type=EventType.NEXT,
                    value=[],
                    current_t=t,
                )
                done_event = CompleteInEvent(
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
                await self.abreak(assignation_id=assignment.assignation)
                event: OutEvent = await event_queue.get()
                event_queue.task_done()

                track = await atrack(
                    reference=event.source + "_track_" + str(t),
                    run=run,
                    source=event.source,
                    handle=event.handle,
                    caused_by=event.caused_by,
                    value=event.value if event.type == EventType.NEXT else None,
                    exception=str(event.exception)
                    if event.type == EventType.ERROR
                    else None,
                    kind=event.type,
                    t=t,
                )
                state[event.source] = track.id

                # We tracked the events and proceed

                if t % self.snapshot_interval == 0:
                    await asnapshot(run=run, events=list(state.values()), t=t)

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
                        track = await atrack(
                            reference=event.source + "_track_" + str(t),
                            run=run,
                            source=spawned_event.target,
                            handle="return_0",
                            caused_by=event.caused_by,
                            value=(
                                spawned_event.value
                                if isinstance(spawned_event, NextInEvent)
                                else None
                            ),
                            # If it is an error event, we need to set the exception
                            exception=(
                                str(spawned_event.exception)
                                if isinstance(spawned_event, ErrorInEvent)
                                else None
                            ),
                            kind=spawned_event.type,
                            t=t,
                        )

                        if spawned_event.type == EventType.NEXT:
                            yield_dict = {}

                            for port, value in zip(return_stream, spawned_event.value):
                                yield_dict[port.key] = value

                            await self.asend(
                                message=messages.YieldEvent(
                                    assignation=assignment.assignation,
                                    returns=yield_dict,
                                )
                            )

                        if spawned_event.type == EventType.ERROR:
                            raise spawned_event.exception

                        if spawned_event.type == EventType.COMPLETE:
                            await asnapshot(run=run, events=list(state.values()), t=t)
                            await self.asend(
                                message=messages.DoneEvent(
                                    assignation=assignment.assignation,
                                )
                            )
                            complete = True

                            logger.info("Done ! :)")

                    else:
                        assert spawned_event.target in atoms, (
                            "Unknown target. Your flow is connected wrong"
                        )
                        if spawned_event.target in atoms:
                            await atoms[spawned_event.target].put(spawned_event)

            for task in tasks:
                task.cancel()

            await asyncio.gather(*tasks, return_exceptions=True)
            logging.info("Collecting...")
            await acollect(list(reference_counter.references))
            logging.info("Done ! :)")
            await aclose_run(run=run.id)

        except asyncio.CancelledError:
            for task in tasks:
                task.cancel()
            await asnapshot(run=run, events=list(state.values()), t=t)

            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True), timeout=4
                )
            except asyncio.TimeoutError:
                pass

            await aclose_run(run=run.id)

            await acollect(list(reference_counter.references))
            await self.asend(
                message=messages.CancelledEvent(
                    assignation=assignment.assignation,
                )
            )

        except Exception as e:
            logging.critical(f"Assignation {assignment} failed", exc_info=True)
            await asnapshot(run=run, events=list(state.values()), t=t)

            await aclose_run(run=run.id)
            await acollect(list(reference_counter.references))
            await self.asend(
                message=messages.CriticalEvent(
                    assignation=assignment.assignation,
                    error=repr(e),
                )
            )

    async def on_unprovide(self):
        for contract in self.contracts.values():
            await contract.aexit()
