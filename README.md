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

## Modules and configs

Anything expressible as a module must not be in core. That is the scope rule,
and the module system is what makes it decidable.

A **config** is a composition root. It names one Framework module and one
Environment module and hands both to the runtime. It is not a fourth artifact —
it has no branches and no rules. The moment a config decides something,
cross-artifact coupling has found a place to live and the diagonal is back in
disguise. An oracle checks the config for branching.

```
configs/min_chat.py          names both, decides nothing
   ├── framework/min_chat.py       rules, ceiling {ui.read, ui.write}
   └── environment/ui_dialog.py    offers {ui.read, ui.write}
```

Neither module has heard of the other. `ui-dialogwin-io` offers two
capabilities and does not know which Framework wants them.

**The pairing is verified, not trusted — and a mismatch does not stop anything.**
`Runtime.compose()` runs before ignition and checks both directions: an action
the Framework permits that the Environment cannot grant is an **orphan**, and a
capability the Environment offers that nothing consumes is **unused**. Neither
is harm. The orphan is retracted from the working vocabulary, both are flagged
by name, and the run proceeds — finishing as `COMPLETE_DEGRADED`, never
silently as `COMPLETE`.

The `min_` prefix is a declared ceiling the runtime enforces, not a naming
convention. A `min_` module paired with an Environment offering `proc.run`
raises `CEILING_EXCEEDED` naming the capability. Least privilege is the
default: there is no permit-all, and no function that could produce one.

## Failure policy

**Fail forward with a flag, unless continuing could cause harm.** A test that
loops and dies costs more than a run that finishes and says what was wrong.

Only three things stop the loop:

| Halt | Why |
|---|---|
| `HARM_HALT` | The Environment reports exhausted memory, full write space, thermal throttling, a failing device. Continuing costs more than stopping. |
| `ATTESTATION_BROKEN` | The rules changed mid-objective. Operating under an unpinned world is not recoverable. |
| `BUDGET_EXHAUSTED` | The halting argument of last resort. |

Everything else raises a **Flag** and continues:

| Flag | Severity | Meaning |
|---|---|---|
| `ACTION_ORPHANED` | DEGRADED | Permitted but ungrantable. Retracted from the vocabulary. |
| `CAPABILITY_UNUSED` | DEGRADED | Offered but nothing consumes it. |
| `CEILING_EXCEEDED` | DEGRADED | The Environment offers more than the module declared. |
| `REQUIREMENT_UNSATISFIABLE` | DEGRADED | A requirement whose action was retracted. Does not block termination. |
| `PHASE_STALLED` | DEGRADED | No state change for `stall_limit` ticks. Progress forced. |
| `SCOPE_BREADTH` | ADVISORY | The objective reached across an unusual share of the vocabulary. |

Flags reach the human, the trace, the Framework view, and the model context, so
every party that can check against the error state knows which condition was
implied and that the system ran as though it did not exist.

**The stall detector is domain-blind.** It does not know *why* a phase will not
advance — only that nothing changed for three ticks. It names the condition and
moves. A mismatched pairing that would otherwise burn a 30-tick budget finishes
in 6 with fourteen named flags.

**Breadth needs a floor as well as a ratio.** Forty tools out of two hundred is
a signal that one objective is really several. Two out of two is a two-action
vocabulary doing its job. Both `breadth_limit` and `breadth_floor` must be
crossed, and the flag is advisory — it never degrades the outcome.

**Nulled phases are traversed, not skipped.** A chat turn has no DESIGN or
IMPLEMENT vocabulary, so those phases occur in the trace, in order, at no model
cost — the only admissible proposal in a phase with no actions is ADVANCE. A
chat turn costs 5 model calls instead of 9+. Ordering is never touched.

```
python3 run_chat.py              # the min_chat composition
python3 -m tests.test_modules      # 21 module-layer oracles
python3 -m tests.test_degradation # 27 failure-policy oracles
```

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
