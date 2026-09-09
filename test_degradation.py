"""Failure-policy oracles. Run: python3 -m tests.test_degradation

The policy: fail forward with a flag, unless continuing could cause harm.
These prove the line sits where we said and not somewhere convenient.
"""

from __future__ import annotations

import sys

from configs.min_chat import assemble
from environment.minimal import MinimalEnvironment
from environment.ui_dialog import DialogEnvironment
from framework.min_chat import ChatFramework
from framework.minimal import MinimalFramework
from model.chat_stub import ChatModel
from model.stub import StubModel
from runtime import Objective, Runtime, Severity, Termination

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  pass  {name}")
    else:
        print(f"  FAIL  {name} {detail}")
        FAILURES.append(name)


def codes(trace) -> list[str]:
    return [f.code for f in trace.flags]


# --- D1: a mismatched pairing degrades and runs ----------------------------


def mismatched() -> Runtime:
    """min_chat rules against an Environment that never heard of chat."""
    return Runtime(
        framework=ChatFramework(),
        environment=MinimalEnvironment(),
        model=ChatModel(),
        objective=Objective("mismatch", "orphaned everything", 30),
    )


def test_mismatch_does_not_halt() -> None:
    trace = mismatched().run()
    check("D1 a mismatched pairing still runs", trace.ticks > 0, f"ticks={trace.ticks}")
    check("D1 it reaches a terminal state", trace.termination is not None)
    check("D1 it is not reported as clean success",
          trace.termination is not Termination.OBJECTIVE_COMPLETE,
          str(trace.termination))
    check("D1 it completes, degraded", trace.termination is Termination.COMPLETE_DEGRADED,
          str(trace.termination))


def test_orphans_are_named_and_retracted() -> None:
    rt = mismatched()
    trace = rt.run()
    check("D1 every orphaned action is named",
          codes(trace).count("ACTION_ORPHANED") == 2, str(codes(trace)))
    check("D1 orphans are retracted from the vocabulary",
          rt.orphaned == frozenset({"chat.read_prompt", "chat.write_response"}),
          str(rt.orphaned))
    check("D1 no orphaned action was ever dispatched",
          not any(e.kind == "ACT" for e in trace.entries))


def test_unused_capability_is_named() -> None:
    trace = mismatched().run()
    check("D1 capability nothing consumes is flagged",
          "CAPABILITY_UNUSED" in codes(trace), str(codes(trace)))
    check("D1 ceiling excess is flagged",
          "CEILING_EXCEEDED" in codes(trace), str(codes(trace)))


def test_unsatisfiable_requirement_does_not_loop() -> None:
    """The expensive failure: burning the whole budget on an already-known fault."""
    trace = mismatched().run()
    check("D1 it does not burn the budget", trace.termination is not Termination.BUDGET_EXHAUSTED)
    check("D1 the unsatisfiable requirement is named",
          "REQUIREMENT_UNSATISFIABLE" in codes(trace), str(codes(trace)))
    check("D1 it finished well inside budget", trace.ticks < 30, f"ticks={trace.ticks}")


def test_stall_must_be_explained() -> None:
    """The model accounts for the stall before the runtime forces past it."""
    trace = mismatched().run()
    reports = [e for e in trace.entries if e.kind == "STALL_REPORT"]
    check("D1 a stall produces a report", bool(reports), str(codes(trace)))
    check("D1 the reason comes from the closed vocabulary",
          all(dict(e.payload)["reason"] in
              {"BLOCKED_PRECONDITION", "NO_PERMITTED_ACTION", "CAPABILITY_MISSING",
               "AWAITING_AUTHORIZATION", "AWAITING_INPUT", "OBJECTIVE_UNCLEAR", "UNKNOWN"}
              for e in reports), str([dict(e.payload) for e in reports]))
    check("D1 the flag carries the reason, not just the phase",
          any(":" in f.detail for f in trace.flags if f.code in ("PHASE_STALLED", "TERMINAL_STALL")),
          str([f.detail for f in trace.flags if "STALL" in f.code]))
    check("D1 stall_limit defaults to 10", Objective("x", "y", 5).stall_limit == 10)


def test_unreported_stall_is_itself_flagged() -> None:
    """A model that will not account for its stall is a fact worth recording."""

    class Mute(ChatModel):
        def propose(self, context):
            from runtime.types import ProposalKind as PK, Proposal as P
            if context.report_required:
                return P(PK.ADVANCE, context.phase)   # refuses to report
            return super().propose(context)

    trace = Runtime(ChatFramework(), MinimalEnvironment(), Mute(),
                    Objective("mute", "x", 40)).run()
    check("D1 a refused report is flagged", "STALL_UNREPORTED" in codes(trace), str(codes(trace)))
    check("D1 the reason falls back to UNKNOWN",
          any(dict(e.payload).get("reason") == "UNKNOWN"
              for e in trace.entries if e.kind == "STALL_REPORT"))
    check("D1 progress is still forced", trace.termination is Termination.COMPLETE_DEGRADED,
          str(trace.termination))


def test_flags_are_visible_to_model_and_framework() -> None:
    """The error state is readable by everything that may check against it."""
    seen: list[tuple[str, ...]] = []

    class Watcher(ChatModel):
        def propose(self, context):
            seen.append(context.flags)
            return super().propose(context)

    rt = Runtime(ChatFramework(), MinimalEnvironment(), Watcher(),
                 Objective("watch", "x", 30))
    rt.run()
    check("D1 the model sees the flag codes", bool(seen) and bool(seen[0]), str(seen[:1]))
    check("D1 it sees which requirements are unsatisfiable", bool(seen))


# --- D2: harm halts, and only harm -----------------------------------------


class FailingDisk(MinimalEnvironment):
    """A device in a state where continuing costs more than stopping."""

    def __init__(self, after: int = 3) -> None:
        self._calls = 0
        self._after = after

    def health(self) -> tuple[str, ...]:
        self._calls += 1
        return ("WRITE_SPACE_FULL",) if self._calls > self._after else ()


def test_harm_halts() -> None:
    rt = Runtime(MinimalFramework(), FailingDisk(after=3), StubModel(),
                 Objective("harm", "x", 40))
    trace = rt.run()
    check("D2 a harm condition halts the loop", trace.termination is Termination.HARM_HALT)
    check("D2 the harm code is recorded",
          any(("detail", "WRITE_SPACE_FULL") in e.payload for e in trace.entries))
    check("D2 it halted early, not at budget", trace.ticks < 10, f"ticks={trace.ticks}")
    check("D2 no grant was left open", rt.open_grants == 0)


def test_healthy_environment_never_halts() -> None:
    trace = Runtime(MinimalFramework(), MinimalEnvironment(), StubModel(),
                    Objective("healthy", "x", 40)).run()
    check("D2 a healthy environment reaches completion",
          trace.termination is Termination.OBJECTIVE_COMPLETE, str(trace.termination))


# --- D3: breadth is advisory, never a stop ---------------------------------


def test_breadth_flags_without_stopping() -> None:
    trace = Runtime(MinimalFramework(), MinimalEnvironment(), StubModel(),
                    Objective("wide", "x", 40, breadth_limit=0.25)).run()
    check("D3 reaching wide raises an advisory", "SCOPE_BREADTH" in codes(trace), str(codes(trace)))
    check("D3 an advisory does not degrade the outcome",
          trace.termination is Termination.OBJECTIVE_COMPLETE, str(trace.termination))
    check("D3 an advisory is not a DEGRADED flag",
          all(f.severity is Severity.ADVISORY
              for f in trace.flags if f.code == "SCOPE_BREADTH"))
    check("D3 it fires once, not every tick",
          codes(trace).count("SCOPE_BREADTH") == 1, str(codes(trace)))


def test_narrow_objective_raises_nothing() -> None:
    """Least privilege looks like this: a small job touching a small vocabulary."""
    rt, _ = assemble("hello")
    trace = rt.run()
    check("D3 a narrow objective raises no flags", not trace.flags, str(codes(trace)))
    check("D3 and completes clean",
          trace.termination is Termination.OBJECTIVE_COMPLETE, str(trace.termination))
    check("D3 min_chat uses 2 of its 2 offered actions",
          len(DialogEnvironment().offered_actions()) == 2)


def test_degraded_is_distinguishable_from_clean() -> None:
    clean, _ = assemble("hello")
    clean = clean.run()
    dirty = mismatched().run()
    check("D3 clean and degraded runs are distinguishable",
          clean.degraded is False and dirty.degraded is True)


def main() -> int:
    print("\ntrine — failure policy: fail forward, halt only on harm\n")
    for fn in [
        test_mismatch_does_not_halt,
        test_orphans_are_named_and_retracted,
        test_unused_capability_is_named,
        test_unsatisfiable_requirement_does_not_loop,
        test_stall_must_be_explained,
        test_unreported_stall_is_itself_flagged,
        test_flags_are_visible_to_model_and_framework,
        test_harm_halts,
        test_healthy_environment_never_halts,
        test_breadth_flags_without_stopping,
        test_narrow_objective_raises_nothing,
        test_degraded_is_distinguishable_from_clean,
    ]:
        fn()
    print(f"\n{'FAILED: ' + ', '.join(FAILURES) if FAILURES else 'failure policy holds'}\n")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
