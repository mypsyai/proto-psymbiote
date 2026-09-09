"""Run the min_chat composition."""

from configs.min_chat import assemble


def main() -> int:
    runtime, env = assemble(prompt="what is the time?")
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
    print(f"window        {env.window}")
    print(f"termination   {trace.termination.value}")
    print(f"ticks         {trace.ticks}   model calls = ticks")
    print(f"chain intact  {trace.verify_chain()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
