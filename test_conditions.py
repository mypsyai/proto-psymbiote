"""One test per binding condition. A condition without an oracle is a preference.

Run: python3 -m tests.test_conditions
"""

from __future__ import annotations

import pathlib
import re
import sys

from environment.minimal import MinimalEnvironment
from framework import minimal as fw_module
from framework.minimal import MinimalFramework
from model.stub import ImpatientModel, OverreachingModel, StallingModel, StubModel
from runtime import (
    EnvironmentPort,
    FrameworkPort,
    ModelPort,
    Objective,
    Phase,
    Proposal,
    ProposalKind,
    Runtime,
    Termination,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  pass  {name}")
    else:
        print(f"  FAIL  {name} {detail}")
        FAILURES.append(name)


def build(model, budget: int = 40) -> Runtime:
    return Runtime(
        framework=MinimalFramework(),
        environment=MinimalEnvironment(),
        model=model,
        objective=Objective("obj-test", "test target", budget),
    )


# --- C1: the direction is one-way ------------------------------------------


def test_dependency_direction() -> None:
    """Runtime imports nothing from Framework, Environment, or Model."""
    forbidden = re.compile(r"^\s*(from|import)\s+(framework|environment|model)\b", re.M)
    dirty = [
        p.name
        for p in (ROOT / "runtime").glob("*.py")
        if forbidden.search(p.read_text())
    ]
    check("C1 runtime depends on nothing", not dirty, str(dirty))


def test_no_diagonal() -> None:
    """Framework never reaches Environment and Environment never reaches Framework."""
    fw = re.compile(r"^\s*(from|import)\s+environment\b", re.M)
    env = re.compile(r"^\s*(from|import)\s+framework\b", re.M)
    fw_dirty = [p.name for p in (ROOT / "framework").glob("*.py") if fw.search(p.read_text())]
    env_dirty = [p.name for p in (ROOT / "environment").glob("*.py") if env.search(p.read_text())]
    check("C1 no diagonal edge", not fw_dirty and not env_dirty, str(fw_dirty + env_dirty))


def test_ports_are_satisfied() -> None:
    """Each artifact is conformance-checkable alone, without the other present."""
    check("C2 framework conforms in isolation", isinstance(MinimalFramework(), FrameworkPort))
    check("C2 environment conforms in isolation", isinstance(MinimalEnvironment(), EnvironmentPort))
    check("C2 model conforms in isolation", isinstance(StubModel(), ModelPort))


# --- C3: no prose crosses a boundary ---------------------------------------


def test_no_prose() -> None:
    long = "x" * 200
    try:
        Proposal(ProposalKind.ACT, Phase.INTENT, "intent.state", (("note", long),))
        ok = False
    except ValueError:
        ok = True
    check("C3 oversized arg rejected at construction", ok)

    try:
        Proposal(ProposalKind.ACT, Phase.INTENT, "intent.state", (("blob", {"a": 1}),))
        ok = False
    except ValueError:
        ok = True
    check("C3 non-scalar arg rejected at construction", ok)


# --- C4: the loop runs and halts -------------------------------------------


def test_completes() -> None:
    trace = build(StubModel()).run()
    check("C4 objective completes", trace.termination is Termination.OBJECTIVE_COMPLETE)
    check("C4 ends in DEBRIEF", trace.final_phase is Phase.DEBRIEF)
    check("C4 record chain intact", trace.verify_chain())


def test_budget_halts() -> None:
    """The halting argument is the runtime's, not the framework's."""
    trace = build(StallingModel(), budget=7).run()
    check("C4 budget halts a stalling model", trace.termination is Termination.BUDGET_EXHAUSTED)
    check("C4 halted at the budget", trace.ticks == 7, f"ticks={trace.ticks}")


def test_deterministic() -> None:
    a, b = build(StubModel()).run(), build(StubModel()).run()
    same = [e.entry_hash for e in a.entries] == [e.entry_hash for e in b.entries]
    check("C4 identical inputs give an identical trace", same)


# --- C5: the model does not adjudicate itself ------------------------------


def test_self_termination_refused() -> None:
    trace = build(ImpatientModel(), budget=5).run()
    refusals = [e for e in trace.entries if e.kind == "REFUSE"]
    check("C5 self-declared completion never terminates",
          trace.termination is Termination.BUDGET_EXHAUSTED)
    check("C5 every attempt was refused", len(refusals) == 5, f"n={len(refusals)}")
    check("C5 refused for a named reason",
          any(("reason", "NOT_TERMINAL_PHASE") in e.payload for e in refusals))


def test_phase_is_grant_scope() -> None:
    """An action the framework would admit is still ungrantable in the wrong phase."""
    trace = build(OverreachingModel(), budget=12).run()
    refusals = [e for e in trace.entries if e.kind == "REFUSE"]
    check("C5 DESIGN cannot obtain a write capability",
          any(("reason", "ACTION_NOT_PERMITTED") in e.payload
              or ("reason", "NO_CAPABILITY") in e.payload for e in refusals),
          str([dict(e.payload) for e in refusals]))
    check("C5 no write ever executed in DESIGN",
          not any(e.kind == "ACT" and dict(e.payload).get("action") == "design.write"
                  for e in trace.entries))

    # The above passes because the Framework refused first. Prove the
    # Environment refuses independently, so the two layers are not one layer.
    env = MinimalEnvironment()
    check("C5 environment alone denies a write in DESIGN",
          env.grant(Phase.DESIGN, "design.write") is None)
    check("C5 environment alone allows a write in IMPLEMENT",
          env.grant(Phase.IMPLEMENT, "implement.write") is not None)
    check("C5 environment denies an unknown action",
          env.grant(Phase.IMPLEMENT, "not.a.real.action") is None)


def test_grants_always_close() -> None:
    rt = build(StubModel())
    rt.run()
    check("C5 no grant outlives its dispatch", rt.open_grants == 0)


def test_wrong_phase_refused() -> None:
    class Liar:
        def model_digest(self) -> str:
            return "liar"

        def propose(self, context):
            return Proposal(ProposalKind.ACT, Phase.IMPLEMENT, "implement.write")

    trace = build(Liar(), budget=3).run()
    check("C5 a proposal for another phase is refused by the runtime itself",
          all(("reason", "WRONG_PHASE") in e.payload
              for e in trace.entries if e.kind == "REFUSE"))


# --- C6: attestation is meaningful -----------------------------------------


def test_attestation_detects_change() -> None:
    rt = build(StubModel())
    before = rt.attest().pin
    original = fw_module.REQUIRED
    try:
        fw_module.REQUIRED = original + ("smuggled.rule",)
        after = rt.attest().pin
    finally:
        fw_module.REQUIRED = original
    check("C6 a changed rule set breaks the pin", before != after)
    check("C6 restoring the rule set restores the pin", rt.attest().pin == before)


def test_attestation_halts_mid_run() -> None:
    """Mutating the world mid-objective halts on the next tick, not silently."""

    class Mutator:
        def __init__(self) -> None:
            self.fired = False

        def model_digest(self) -> str:
            return "mutator"

        def propose(self, context):
            if not self.fired:
                self.fired = True
                fw_module.REQUIRED = fw_module.REQUIRED + ("smuggled.rule",)
            return Proposal(ProposalKind.ACT, context.phase, context.permitted_actions[0])

    original = fw_module.REQUIRED
    try:
        trace = build(Mutator(), budget=10).run()
    finally:
        fw_module.REQUIRED = original
    check("C6 mid-run mutation halts the objective",
          trace.termination is Termination.ATTESTATION_BROKEN)


def test_tamper_detected() -> None:
    trace = build(StubModel()).run()
    check("C6 clean chain verifies", trace.verify_chain())
    trace.entries[3] = trace.entries[3].__class__(
        index=3, tick=99, kind="ACT", payload=(("action", "forged"),),
        prev_hash=trace.entries[3].prev_hash,
    )
    check("C6 an edited record fails verification", not trace.verify_chain())


def main() -> int:
    print("\ntrine — binding conditions\n")
    for fn in [
        test_dependency_direction,
        test_no_diagonal,
        test_ports_are_satisfied,
        test_no_prose,
        test_completes,
        test_budget_halts,
        test_deterministic,
        test_self_termination_refused,
        test_phase_is_grant_scope,
        test_grants_always_close,
        test_wrong_phase_refused,
        test_attestation_detects_change,
        test_attestation_halts_mid_run,
        test_tamper_detected,
    ]:
        fn()
    print(f"\n{'FAILED: ' + ', '.join(FAILURES) if FAILURES else 'all conditions hold'}\n")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
