"""Run one objective end to end and print the trace."""

from environment.minimal import MinimalEnvironment
from framework.minimal import MinimalFramework
from model.stub import StubModel
from runtime import Objective, Runtime


def main() -> int:
    objective = Objective(
        objective_id="obj-0001",
        target="prove the loop runs",
        budget=40,
    )
    runtime = Runtime(
        framework=MinimalFramework(),
        environment=MinimalEnvironment(),
        model=StubModel(),
        objective=objective,
    )
    trace = runtime.run()

    for e in trace.entries:
        args = "  ".join(f"{k}={v}" for k, v in e.payload)
        print(f"{e.index:>3}  t{e.tick:<3} {e.kind:<10} {args}")

    print()
    if trace.flags:
        print("  !! OPERATING WITH FLAGS — the human needs to see this")
        for fl in trace.flags:
            print(f"     [{fl.severity.value}] {fl.code}  {fl.detail}")
        print()
    print(f"pin           {trace.pin[:16]}")
    print(f"chain intact  {trace.verify_chain()}")
    print(f"termination   {trace.termination.value}")
    print(f"final phase   {trace.final_phase.name}")
    print(f"ticks         {trace.ticks} / {objective.budget}")
    print(f"open grants   {runtime.open_grants}")
    return 0 if trace.termination.value == "OBJECTIVE_COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
