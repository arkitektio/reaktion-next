"""The flow execution engine.

Runs a fluss flow graph as a plain async generator, independent of any
actor subclass: values are received raw (already shrunk and validated by
the rekuest server) and return dicts are yielded raw. Yield/Done/Cancelled/
Critical events are the caller's responsibility (FunctionalActor sends them
when the engine is driven through the registered ``run_flow`` action).
"""

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from fluss_next.api.schema import (
    ArgNode,
    Flow,
    ReactiveNode,
    RekuestActionNodeBase,
    ReturnNode,
    RunEventKind,
    TrackMutationTrack,
    aclose_run,
    acreate_run,
    asnapshot,
    atrack,
)
from rath.scalars import ID
from rekuest_next.actors.base import Actor
from rekuest_next.actors.helper import AssignmentHelper
from rekuest_next.actors.vars import get_current_assignation_helper
from rekuest_next.api.schema import acollect
from rekuest_next.messages import Assign

from reaktion_next.atoms.transport import AtomTransport
from reaktion_next.atoms.utils import atomify
from reaktion_next.contractors import NodeContractor, arkicontractor
from reaktion_next.events import (
    CompleteInEvent,
    CompleteOutEvent,
    ErrorInEvent,
    EventType,
    NextInEvent,
    NextOutEvent,
    OutEvent,
)
from reaktion_next.reference_counter import ReferenceCounter
from reaktion_next.rpc_contract import RPCContract
from reaktion_next.utils import connected_events

logger = logging.getLogger(__name__)

DEFAULT_SNAPSHOT_INTERVAL = 40


async def arun_flow(
    flow: Flow,
    kwargs: Dict[str, Any],
    *,
    contractor: NodeContractor = arkicontractor,
    snapshot_interval: int = DEFAULT_SNAPSHOT_INTERVAL,
    assignment: Optional[Assign] = None,
    actor: Optional[Actor] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Run a flow and yield its return dicts as they are produced.

    ``kwargs`` carries the flow's arg-node stream values and global values,
    keyed by port key, in raw (shrunk) form. Each value reaching the flow's
    return node is yielded as ``{return_port_key: value}``.

    ``assignment``/``actor`` default to the surrounding assignation context
    (the registered action path); pass them explicitly to drive the engine
    outside an assignation, e.g. in tests.
    """
    helper: Optional[AssignmentHelper] = None
    if assignment is None:
        helper = get_current_assignation_helper()
        assignment = helper.assignment
        if actor is None:
            actor = helper.actor

    reference_counter = ReferenceCounter()

    run = await acreate_run(
        assignation=ID.validate(assignment.assignation),
        flow=flow.id,
        snapshot_interval=snapshot_interval,
    )
    # Runs track the state of the flow interactively

    t = 0
    state: Dict[ID, TrackMutationTrack] = {}
    tasks: List[asyncio.Task[None]] = []
    contracts: Dict[str, RPCContract] = {}

    try:
        rekuest_nodes = [
            x for x in flow.graph.nodes if isinstance(x, RekuestActionNodeBase)
        ]

        contracts = {node.id: await contractor(node, actor) for node in rekuest_nodes}
        await asyncio.gather(*[contract.aenter() for contract in contracts.values()])

        await asnapshot(run=run.id, events=list(state.values()), t=t)

        event_queue: asyncio.Queue[OutEvent] = asyncio.Queue()

        atomtransport = AtomTransport(queue=event_queue)

        argNode = [x for x in flow.graph.nodes if isinstance(x, ArgNode)][0]
        returnNode = [x for x in flow.graph.nodes if isinstance(x, ReturnNode)][0]

        participatingNodes = [
            x
            for x in flow.graph.nodes
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
        for i in flow.graph.globals:
            global_keys.append(i.port.key)

        for node in participatingNodes:
            for port_key, global_key in node.globals_map.items():
                if global_key not in global_keys:
                    raise ValueError(f"Global key {global_key} not found in globals")
                if global_key not in kwargs:
                    raise ValueError(f"Global key {global_key} not found in {kwargs}")
                if node.id not in globalMap:
                    globalMap[node.id] = {}

                globalMap[node.id][port_key] = kwargs[global_key]

        # We need to map the stream keys to the actual values from the kwargs
        # Args nodes have a stream that maps the port key to the stream key

        for key in stream_keys:
            if key in kwargs:
                streamMap[key] = kwargs[key]
            else:
                raise ValueError(f"Stream key {key} not found in {kwargs}")

        atoms = {
            x.id: atomify(
                x,
                atomtransport,
                contracts.get(x.id, None),
                globalMap.get(x.id, {}),
                assignment,
                reference_counter,
                actor,
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

        edge_targets = [e.target for e in flow.graph.edges]

        # Get all nodes that have no instream
        nodes_without_instream = [
            x
            for x in participatingNodes
            if len(x.ins[0]) == 0 and x.id not in edge_targets
        ]

        # Get all nodes that are connected to argNode
        connected_arg_nodes = [
            e.target for e in flow.graph.edges if e.source == argNode.id
        ]

        # Get the nodes that are not connected to argNode AND have no instream
        nodes_without_instream = [
            node for node in nodes_without_instream if node.id not in connected_arg_nodes
        ]

        # Send initial events to nodes without instream (they are not connected
        # to argNode so need to be triggered)
        for node in nodes_without_instream:
            assert node.id in atoms, "Atom not found. Should not happen."
            atom = atoms[node.id]

            await atom.put(
                NextInEvent(
                    target=node.id,
                    handle="arg_0",
                    type=EventType.NEXT,
                    value=[],
                    current_t=t,
                )
            )
            await atom.put(
                CompleteInEvent(
                    target=node.id,
                    handle="arg_0",
                    type=EventType.COMPLETE,
                    current_t=t,
                )
            )

        complete = False

        while not complete:
            if helper is not None:
                await helper.abreakpoint()
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
                kind=RunEventKind(event.type.value),
                t=t,
            )
            state[event.source] = track.id

            # We tracked the events and proceed

            if t % snapshot_interval == 0:
                await asnapshot(run=run, events=list(state.values()), t=t)

            # Create new events with the new timepoint
            spawned_events = connected_events(flow.graph, event, t)
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
                        exception=(
                            str(spawned_event.exception)
                            if isinstance(spawned_event, ErrorInEvent)
                            else None
                        ),
                        kind=RunEventKind(spawned_event.type.value),
                        t=t,
                    )

                    if spawned_event.type == EventType.NEXT:
                        yield_dict = {}

                        for port, port_value in zip(
                            return_stream, spawned_event.value
                        ):
                            yield_dict[port.key] = port_value

                        yield yield_dict

                    if spawned_event.type == EventType.ERROR:
                        raise spawned_event.exception

                    if spawned_event.type == EventType.COMPLETE:
                        await asnapshot(run=run, events=list(state.values()), t=t)
                        complete = True

                        logger.info("Done ! :)")

                else:
                    assert spawned_event.target in atoms, (
                        "Unknown target. Your flow is connected wrong"
                    )
                    await atoms[spawned_event.target].put(spawned_event)

    except asyncio.CancelledError:
        await asnapshot(run=run, events=list(state.values()), t=t)
        raise

    except Exception:
        logging.critical(f"Assignation {assignment} failed", exc_info=True)
        await asnapshot(run=run, events=list(state.values()), t=t)
        raise

    finally:
        for task in tasks:
            task.cancel()

        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=4
            )
        except asyncio.TimeoutError:
            pass

        await acollect(list(reference_counter.references))
        await aclose_run(run=run.id)
        await asyncio.gather(
            *[contract.aexit() for contract in contracts.values()],
            return_exceptions=True,
        )
