# proto-psymbiote
# trine

Three artifacts. It runs. That is the whole claim.

```
python3 main.py                  # one objective, end to end, prints the trace
python3 -m tests.test_conditions # 28 oracles, one per binding condition
```

## The shape

**Runtime** is fixed and universal. It depends on nothing. It defines two
surfaces and drives one cycle.

**Framework** and **Environment** each have two halves. The fixed half faces
the runtime and is identical in every deployment. The fluid half is the
implementation and the runtime never sees it. The *what* stays; the *how*
adapts.

```
            ┌───────────────┐
            │    Runtime    │   fixed. imports nothing.
            └───┬───────┬───┘
      fixed half│       │fixed half
        ┌───────▼──┐ ┌──▼───────┐
        │Framework │ │Environmt │   conformance-checkable alone
        │  fluid   │ │  fluid   │   never reach each other
        └──────────┘ └──────────┘
```

## The two loops

They nest. The model's loop is per-objective; the runtime's is per-tick.
IMPLEMENT may take forty ticks. They meet at DEBRIEF because DEBRIEF is the
last phase, not because two parallel tracks converge.

```
outer (model)   INTENT → PLAN → DESIGN → SCAFFOLD → IMPLEMENT
                       → VERIFY → EVALUATE → DELIVER → DEBRIEF

inner (runtime) attest → [ ignite → propose → admit → grant
                           → dispatch → return → record → progress ]*
```

**The phase is the grant scope.** DESIGN holds no write capability, so a write
in DESIGN is refused by construction rather than by instruction. The model's
loop is not choreography it is asked to follow; it is the thing that determines
what it can do.

Variation is expressed by nulling a segment, never by reordering one. A
deployment needing no capability supplies an Environment that grants the empty
set. The moment a use case justifies reordering, it is not this runtime.

## Binding conditions

Each has an oracle. A condition without an oracle is a preference, and it
degrades the first time someone is in a hurry.

| # | Condition | Oracle |
|---|---|---|
| C1 | Runtime imports no artifact. No diagonal between Framework and Environment. | import scan |
| C2 | Each artifact conforms to its surface with the other absent. | protocol check |
| C3 | No prose crosses a boundary — scalars only, length-bounded. | constructor raises |
| C4 | Every objective halts. The budget is the runtime's argument, not the framework's. | stalling model |
| C5 | The model proposes. It never advances or terminates itself. Capability comes only from the phase. | adversarial models |
| C6 | Attestation pins the world before ignition and is rechecked every tick. The record is hash-chained. | mutation + tamper |

## What is deliberately absent

The Environment performs a null effect. The model is a stub. There is no
persistence, no server, no crypto, no real capability.

That is the point. This is the first version that can be *wrong*. Everything
added next should either break it or be rejected — which is a standard the
design could not be held to while it was only on paper.

## Swapping the stub

`model/stub.py` implements three methods. Replace `StubModel` with a real
driver and nothing else changes. `CARRIED_FORWARD` is the cached block: rules
and prohibitions, verbatim, never paraphrased — a summary becomes the operative
rule and nobody notices which clause went missing. It hashes into the
attestation, so changing a prohibition mid-objective breaks the pin instead of
quietly taking effect.
