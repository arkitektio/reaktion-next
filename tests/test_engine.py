"""Tests for the flow execution engine (`arun_flow`)."""

import asyncio
import itertools
from typing import Any, AsyncGenerator, Dict, List, Optional

import pytest
from fluss_next.api.schema import Flow
from rekuest_next.messages import Assign

import reaktion_next.engine as engine_module
from reaktion_next.engine import arun_flow


def make_port(key: str, kind: str = "INT", nullable: bool = False) -> Dict[str, Any]:
    """Build a FlussPort dict."""
    return {"__typename": "Port", "key": key, "kind": kind, "nullable": nullable}


def make_node(
    id: str,
    kind: str,
    ins: List[List[Dict[str, Any]]],
    outs: List[List[Dict[str, Any]]],
    globals_map: Optional[Dict[str, str]] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Build a graph node dict."""
    return {
        "id": id,
        "position": {"x": 0, "y": 0},
        "globalsMap": globals_map or {},
        "constantsMap": {},
        "title": id,
        "description": "",
        "kind": kind,
        "ins": ins,
        "outs": outs,
        "constants": [],
        "voids": [],
        **extra,
    }


def make_flow(
    action_kind: str = "FUNCTION",
    globals_map: Optional[Dict[str, str]] = None,
    graph_globals: Optional[List[Dict[str, Any]]] = None,
) -> Flow:
    """Build a minimal flow: ArgNode(x) -> rekuest node -> ReturnNode(out)."""
    return Flow.model_validate(
        {
            "__typename": "Flow",
            "id": "flow-1",
            "title": "test flow",
            "createdAt": "2026-01-01T00:00:00Z",
            "workspace": {"__typename": "Workspace", "id": "1"},
            "graph": {
                "__typename": "Graph",
                "globals": graph_globals or [],
                "nodes": [
                    {
                        "__typename": "ArgNode",
                        **make_node("arg", "ARGS", [[]], [[make_port("x")]]),
                    },
                    {
                        "__typename": "RekuestMapActionNode",
                        **make_node(
                            "middle",
                            "REKUEST",
                            [[make_port("x")]],
                            [[make_port("return0")]],
                            globals_map=globals_map,
                        ),
                        "hash": "h-middle",
                        "mapStrategy": "MAP",
                        "allowLocalExecution": False,
                        "binds": {"__typename": "Binds", "implementations": []},
                        "actionKind": action_kind,
                    },
                    {
                        "__typename": "ReturnNode",
                        **make_node("returns", "RETURNS", [[make_port("out")]], [[]]),
                    },
                ],
                "edges": [
                    {
                        "__typename": "VanillaEdge",
                        "id": "e1",
                        "kind": "VANILLA",
                        "stream": [],
                        "source": "arg",
                        "sourceHandle": "return_0",
                        "target": "middle",
                        "targetHandle": "arg_0",
                    },
                    {
                        "__typename": "VanillaEdge",
                        "id": "e2",
                        "kind": "VANILLA",
                        "stream": [],
                        "source": "middle",
                        "sourceHandle": "return_0",
                        "target": "returns",
                        "targetHandle": "arg_0",
                    },
                ],
            },
        }
    )


class MockContract:
    """An RPCContract double that records calls and returns canned results."""

    def __init__(
        self,
        call_result: Optional[Dict[str, Any]] = None,
        iterate_results: Optional[List[Dict[str, Any]]] = None,
        error: Optional[Exception] = None,
        hang: bool = False,
    ) -> None:
        """Configure the canned behaviour for acall_raw/aiterate_raw."""
        self.call_result = call_result
        self.iterate_results = iterate_results
        self.error = error
        self.hang = hang
        self.calls: List[Dict[str, Any]] = []
        self.entered = False
        self.exited = False

    async def aenter(self) -> "MockContract":
        """Record that the contract was entered."""
        self.entered = True
        return self

    async def aexit(self) -> "MockContract":
        """Record that the contract was exited."""
        self.exited = True
        return self

    async def __aenter__(self) -> "MockContract":
        """Enter the contract."""
        return await self.aenter()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the contract."""
        await self.aexit()

    def __enter__(self) -> "MockContract":
        """Enter the contract synchronously."""
        return self

    async def acall_raw(
        self,
        kwargs: Dict[str, Any],
        parent: Any = None,
        reference: Optional[str] = None,
        assign_timeout: Optional[float] = None,
        timeout_is_recoverable: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Record the call and return the canned result."""
        self.calls.append(kwargs)
        if self.hang:
            await asyncio.Event().wait()
        if self.error is not None:
            raise self.error
        return self.call_result

    async def aiterate_raw(
        self,
        kwargs: Dict[str, Any],
        parent: Any = None,
        reference: Optional[str] = None,
        assign_timeout: Optional[float] = None,
        timeout_is_recoverable: bool = False,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Record the call and yield the canned results."""
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        for result in self.iterate_results or []:
            yield result


@pytest.fixture
def fake_assignment() -> Assign:
    """A fake Assign message to drive the engine outside an assignation."""
    return Assign(
        interface="run_flow",
        extension="test",
        assignation="assignation-1",
        user="user-1",
        app="app-1",
        action="action-1",
        args={},
    )


@pytest.fixture
def fluss_calls(monkeypatch: pytest.MonkeyPatch) -> Dict[str, List[Any]]:
    """Stub out the fluss run-tracking API in the engine's namespace."""
    calls: Dict[str, List[Any]] = {
        "create": [],
        "track": [],
        "snapshot": [],
        "close": [],
        "collect": [],
    }

    counter = itertools.count()

    class StubRun:
        id = "run-1"

    class StubTrack:
        def __init__(self, id: str) -> None:
            self.id = id

    async def acreate_run(**kwargs: Any) -> StubRun:
        calls["create"].append(kwargs)
        return StubRun()

    async def atrack(**kwargs: Any) -> StubTrack:
        calls["track"].append(kwargs)
        return StubTrack(str(next(counter)))

    async def asnapshot(**kwargs: Any) -> None:
        calls["snapshot"].append(kwargs)

    async def aclose_run(**kwargs: Any) -> None:
        calls["close"].append(kwargs)

    async def acollect(references: List[str]) -> None:
        calls["collect"].append(references)

    monkeypatch.setattr(engine_module, "acreate_run", acreate_run)
    monkeypatch.setattr(engine_module, "atrack", atrack)
    monkeypatch.setattr(engine_module, "asnapshot", asnapshot)
    monkeypatch.setattr(engine_module, "aclose_run", aclose_run)
    monkeypatch.setattr(engine_module, "acollect", acollect)
    return calls


def make_contractor(contract: MockContract) -> Any:
    """A contractor that hands the given contract to every rekuest node."""

    async def contractor(node: Any, actor: Any) -> MockContract:
        return contract

    return contractor


async def run_to_list(
    flow: Flow,
    kwargs: Dict[str, Any],
    contract: MockContract,
    assignment: Assign,
) -> List[Dict[str, Any]]:
    """Drive arun_flow to completion and collect the yielded dicts."""
    return [
        returns
        async for returns in arun_flow(
            flow,
            kwargs,
            contractor=make_contractor(contract),
            assignment=assignment,
            actor=None,
        )
    ]


@pytest.mark.asyncio
async def test_function_flow_yields_once(
    fluss_calls: Dict[str, List[Any]], fake_assignment: Assign
) -> None:
    """A function flow yields a single dict keyed by the return port keys."""
    contract = MockContract(call_result={"return0": 2})

    results = await run_to_list(make_flow(), {"x": 1}, contract, fake_assignment)

    assert results == [{"out": 2}]
    assert contract.calls == [{"x": 1}]
    assert contract.entered and contract.exited
    assert len(fluss_calls["create"]) == 1
    assert len(fluss_calls["close"]) == 1
    assert len(fluss_calls["collect"]) == 1


@pytest.mark.asyncio
async def test_generator_flow_yields_multiple(
    fluss_calls: Dict[str, List[Any]], fake_assignment: Assign
) -> None:
    """A generator flow yields one dict per value reaching the return node."""
    contract = MockContract(iterate_results=[{"return0": 1}, {"return0": 2}])

    results = await run_to_list(
        make_flow(action_kind="GENERATOR"), {"x": 1}, contract, fake_assignment
    )

    assert results == [{"out": 1}, {"out": 2}]


@pytest.mark.asyncio
async def test_globals_are_passed_to_nodes(
    fluss_calls: Dict[str, List[Any]], fake_assignment: Assign
) -> None:
    """Global values from kwargs are merged into the node call kwargs."""
    flow = make_flow(
        globals_map={"scale": "scale"},
        graph_globals=[
            {"__typename": "GlobalArg", "key": "scale", "port": make_port("scale")}
        ],
    )
    contract = MockContract(call_result={"return0": 10})

    results = await run_to_list(flow, {"x": 1, "scale": 10}, contract, fake_assignment)

    assert results == [{"out": 10}]
    assert contract.calls == [{"scale": 10, "x": 1}]


@pytest.mark.asyncio
async def test_missing_stream_key_raises(
    fluss_calls: Dict[str, List[Any]], fake_assignment: Assign
) -> None:
    """A missing arg key fails fast and still closes the run."""
    contract = MockContract(call_result={"return0": 2})

    with pytest.raises(ValueError, match="Stream key x not found"):
        await run_to_list(make_flow(), {}, contract, fake_assignment)

    assert len(fluss_calls["close"]) == 1
    assert contract.exited


@pytest.mark.asyncio
async def test_missing_global_key_raises(
    fluss_calls: Dict[str, List[Any]], fake_assignment: Assign
) -> None:
    """A missing global key fails fast."""
    flow = make_flow(
        globals_map={"scale": "scale"},
        graph_globals=[
            {"__typename": "GlobalArg", "key": "scale", "port": make_port("scale")}
        ],
    )
    contract = MockContract(call_result={"return0": 2})

    with pytest.raises(ValueError, match="Global key scale not found"):
        await run_to_list(flow, {"x": 1}, contract, fake_assignment)


@pytest.mark.asyncio
async def test_node_error_propagates(
    fluss_calls: Dict[str, List[Any]], fake_assignment: Assign
) -> None:
    """An exception inside a node call propagates out of the engine."""
    contract = MockContract(error=RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        await run_to_list(make_flow(), {"x": 1}, contract, fake_assignment)

    assert len(fluss_calls["close"]) == 1
    assert contract.exited


@pytest.mark.asyncio
async def test_cancellation_cleans_up(
    fluss_calls: Dict[str, List[Any]], fake_assignment: Assign
) -> None:
    """Cancelling the consumer cancels atom tasks and closes the run."""
    contract = MockContract(hang=True)

    task = asyncio.create_task(
        run_to_list(make_flow(), {"x": 1}, contract, fake_assignment)
    )
    await asyncio.sleep(0.2)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert len(fluss_calls["close"]) == 1
    assert len(fluss_calls["collect"]) == 1
    assert contract.exited


@pytest.mark.asyncio
async def test_run_flow_action_is_registered() -> None:
    """Importing reaktion_next registers run_flow in the default app registry."""
    import reaktion_next  # noqa: F401
    from rekuest_next.app import get_default_app_registry

    registry = get_default_app_registry()
    implementation = registry.implementations["run_flow"]

    assert implementation.definition.kind == "GENERATOR"
    assert [port.key for port in implementation.definition.args] == ["flow", "kwargs"]
    assert implementation.definition.args[0].identifier == "@fluss/flow"
    assert [port.key for port in implementation.definition.returns] == ["returns"]
    assert "flow_runner" in implementation.definition.interfaces

    builder = registry.actor_builders["run_flow"]
    assert builder.keywords["expand_inputs"] is False
    assert builder.keywords["shrink_outputs"] is False
    assert builder.keywords["concurrency"] == "parallel"
