# Thoughts: run_flow and higher-order implementations

Design notes from the 2026-06-11 rewrite of reaktion_next and the accompanying
server-side design discussion. This documents *why* the package looks the way
it does now, and the intended (not yet built) rekuest-server counterpart.

## The client-side rewrite (done)

reaktion_next used to register a `ReaktionExtension` that spawned a `FlowActor`
per flow interface, deriving each flow's typed definition client-side
(`convert_flow_to_definition`). That path was doubly dead:

1. It was broken — rekuest-next removed the extension registry; agents now
   serve actors exclusively from the unified `AppRegistry`.
2. It put type derivation/validation on the wrong side. The server is the
   natural place to infer a flow's typed ports and validate caller args.

It was replaced with a single registered **generator action**:

```
run_flow(flow, kwargs) -> yields dicts
```

- `reaktion_next/engine.py` — `arun_flow(...)`: the old FlowActor event loop as
  a plain async generator. Yields `{return_port_key: value}` dicts, re-raises
  on error/cancellation. All Yield/Done/Cancelled/Critical events are sent by
  the surrounding `FunctionalActor`, never by the engine.
- `reaktion_next/actions.py` — the `run_flow` action plus a handcrafted
  `DefinitionInput` (no `PortKind.ANY` exists, so the untyped `kwargs`/`returns`
  DICT ports can't be signature-derived) via a custom actifier.
- `reaktion_next/rekuest.py` — registers it with `bypass_expand`/`bypass_shrink`
  (args arrive raw, already validated and shrunk by the server) and
  `concurrency="parallel"` (one actor serves all flow runs).

Key insight that makes this work: the flow engine always operated on raw
(shrunk) values end-to-end — `assignment.args` was used directly and node calls
went through `acall_raw`/`aiterate_raw`. So a generic untyped executor is a
passthrough, not a redesign.

## The wire contract (server must match)

- Implementation interface: `"run_flow"`; definition `interfaces` tag:
  `("flow_runner",)`; kind GENERATOR.
- Server sends: `{"flow": "<flow id>", "kwargs": {<flow arg/global port key>: <shrunk value>}}`.
  The `flow` port is STRUCTURE `@fluss/flow`; with bypass_expand the function
  receives the raw ID and fetches the flow itself.
- Each engine yield arrives at the server as
  `YieldEvent(returns={"returns": {<return port key>: value}})` — the server
  unwraps the `returns` collector and re-keys to the typed wrapper's ports.
- The `kwargs`/`returns` DICT ports carry a placeholder STRING child; the
  server must never validate forwarded values against it.

## Server-side design: how should this be registered?

Question considered: should there be an `is_low_level` flag on implementations,
making it clear users can create higher-order implementations for them?

**Answer: no bare boolean.** Two reasons:

1. A boolean doesn't tell the server *how* to wrap — the packing convention
   (`{"flow": id, "kwargs": {...}}` in, `{"returns": {...}}` out) is the actual
   information.
2. A richer marker already exists: the `flow_runner` interfaces tag on the
   definition (queryable via `Action.interfaces`, optionally promoted to a
   `Protocol` via `infer_protocols()`). A semantic tag tells UIs *what kind*
   of higher-order implementation can be created; `is_low_level` can't.

**The headline finding:** the live rekuest server
(`/home/jhnnsrs/Code/deployments/next/mounts/rekuest`) already has the right
primitive, completely unused: `Implementation.higher_order_for`
(facade/models.py:908), a nullable self-FK whose help text already describes
this exact mechanism. The design fills in around that FK:

### 1. Low-level marking — already done

The `flow_runner` tag is the marker. "Can I deploy a flow to this agent?"
becomes "does the agent have an implementation whose action carries the
`flow_runner` protocol/interface?"

### 2. A generic `create_higher_order_implementation` mutation

Crucial architectural point: **the caller supplies the derived typed
definition; rekuest stays flow-agnostic.** The server has zero fluss awareness
today and should keep it that way. Fluss already knows how to derive a typed
definition from a flow graph (the deleted client-side
`convert_flow_to_definition` logic naturally moves to fluss-server or the
deploying UI).

```graphql
createHigherOrderImplementation(input: {
  forImplementation: ID          # the run_flow implementation
  interface: String              # e.g. "flow:123" (unique per agent)
  definition: DefinitionInput    # typed, derived by the caller (fluss)
  boundArgs: Args                # {"flow": "123"}
  argsCollector: String          # "kwargs"
  returnsCollector: String       # "returns"
})
```

Creates the Action via the normal `hash_definition` dedup, then an
Implementation on the *same agent* with `higher_order_for=<run_flow impl>` and
the binding stored in `params`. At creation time, validate the contract
structurally against the target action: every target arg port is either in
`boundArgs` or is the designated DICT collector. That structural check is what
replaces the `is_low_level` flag — wrappability is verified once, not asserted.

This also stays generic: the same mechanism can later wrap any generic
executor (script runner, prompt template), not just flows.

### 3. Assign-time forwarding (facade/backend.py `assign()`)

When `implementation.higher_order_for` is set:

- **Validate** `input.args` against the wrapper action's ports. This is new —
  the server currently does *no* arg validation anywhere (`args` is a
  passthrough scalar). The relational `ArgPort` tree with `compiled_jsonpath`
  looks built for exactly this.
- **Transform**: `args = {**bound_args, args_collector: validated_args}`;
  broadcast the Assign with the *lower* implementation's
  interface/extension/action hash, while the Assignation row keeps pointing at
  the higher-order implementation (tracking/UI shows "ran flow X").
- **Unwrap yields**: re-key each YieldEvent from `{"returns": {...}}` back to
  the wrapper's return ports before forwarding to the waiter.

### Gotchas (verified in server code)

- **Agent reconnect wipes wrappers.** `implement_agent`
  (facade/mutations/agent.py:138, 185-189) deletes every implementation the
  agent didn't re-report. Cleanup must become
  `filter(agent=agent, higher_order_for__isnull=True)`.
- **`on_delete=SET_NULL`** on `higher_order_for` leaves orphaned wrappers if
  the executor implementation is deleted. CASCADE is probably right for
  wrappers; at minimum `assign()` must fail cleanly on a null FK.
- Uniqueness works out: each wrapper has its own derived Action, and
  `interface="flow:{id}"` keeps `(interface, agent)` unique. `run_flow` is
  registered `concurrency="parallel"`, so one actor serves many wrappers.
- The existing `Shortcut` model (saved_args pre-binding) is *not* the right
  base: it pre-fills args on the *same* typed action at the user/toolbox
  level, whereas a higher-order implementation needs a *new typed signature*
  repacked into an untyped collector. Keep them separate.

## Open items

- No `PortKind.ANY` exists; the DICT placeholder child is cosmetic but should
  eventually become a real ANY kind server-side.
- Until the server feature lands, deployed flows are not schedulable (the
  per-flow client implementations are gone) — intentional sequencing.
- The discovery strings (`"run_flow"` interface, `"flow_runner"` tag) must
  match between reaktion_next and the server feature.
- Sequencing of remaining work: rekuest-server mutation + assign forwarding +
  cleanup fix; fluss-side flow→DefinitionInput derivation + deploy call.
