"""Module-layer oracles. Run: python3 -m tests.test_modules

The config asserts a pairing. These prove the runtime verifies it instead of
trusting it, and that a mismatch fails at boot rather than at tick forty.
"""

from __future__ import annotations

import re
import pathlib
import sys

from configs.min_chat import ENVIRONMENT_MODULE, FRAMEWORK_MODULE, assemble
from environment.minimal import MinimalEnvironment
from environment.ui_dialog import DialogEnvironment
from framework.min_chat import ChatFramework
from framework.minimal import MinimalFramework
from model.chat_stub import ChatModel
from runtime import EnvironmentPort, FrameworkPort, Objective, Runtime, Termination

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  pass  {name}")
    else:
        print(f"  FAIL  {name} {detail}")
        FAILURES.append(name)


# --- M1: modules obey the same divisions as the artifacts ------------------


def test_modules_conform() -> None:
    check("M1 framework module satisfies the fixed surface", isinstance(ChatFramework(), FrameworkPort))
    check("M1 environment module satisfies the fixed surface", isinstance(DialogEnvironment(), EnvironmentPort))


def test_modules_hold_the_no_diagonal_line() -> None:
    fw = re.compile(r"^\s*(from|import)\s+environment\b", re.M)
    env = re.compile(r"^\s*(from|import)\s+framework\b", re.M)
    bad = [p.name for p in (ROOT / "framework").glob("*.py") if fw.search(p.read_text())]
    bad += [p.name for p in (ROOT / "environment").glob("*.py") if env.search(p.read_text())]
    check("M1 no module reaches across", not bad, str(bad))


def test_runtime_untouched_by_modules() -> None:
    forbidden = re.compile(r"^\s*(from|import)\s+(framework|environment|model|configs)\b", re.M)
    bad = [p.name for p in (ROOT / "runtime").glob("*.py") if forbidden.search(p.read_text())]
    check("M1 runtime knows no module and no config", not bad, str(bad))


def test_config_has_no_logic() -> None:
    """A config that decides is a fourth artifact wearing a disguise."""
    src = (ROOT / "configs" / "min_chat.py").read_text()
    body = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    smells = [kw for kw in (" if ", "\nif ", " for ", "\nfor ", " while ", "try:") if kw in body]
    check("M1 config contains no branching", not smells, str(smells))


# --- M2: the asserted pairing is verified, not trusted ---------------------


def test_valid_pairing_composes() -> None:
    runtime, _ = assemble("hello")
    check("M2 declared pairing composes clean", runtime.compose() == [], str(runtime.compose()))


def test_mismatched_pairing_is_flagged_not_fatal() -> None:
    """min_chat rules against an Environment that never heard of chat actions."""
    runtime = Runtime(
        framework=ChatFramework(),
        environment=MinimalEnvironment(),
        model=ChatModel(),
        objective=Objective("bad-pair", "mismatch", 60),
    )
    flags = runtime.compose()
    trace = runtime.run()
    check("M2 mismatch detected before ignition", bool(flags), str(flags))
    check("M2 mismatch degrades rather than halting",
          trace.termination is Termination.COMPLETE_DEGRADED, str(trace.termination))
    check("M2 the flag names the phase and action",
          any(f.detail == "INTENT:chat.read_prompt" for f in flags),
          str([f.detail for f in flags]))
    check("M2 the orphan is retracted, never dispatched",
          not any(e.kind == "ACT" for e in trace.entries))


def test_ceiling_is_enforced_not_named() -> None:
    """The `min_` prefix means something because the runtime checks it."""
    runtime = Runtime(
        framework=ChatFramework(),
        environment=MinimalEnvironment(),  # offers fs.write, proc.run, artifact.emit
        model=ChatModel(),
        objective=Objective("ceiling", "excess", 20),
    )
    flags = [f for f in runtime.compose() if f.code == "CEILING_EXCEEDED"]
    check("M2 environment exceeding the declared ceiling is flagged", bool(flags), str(flags))
    check("M2 the excess capability is named",
          any(f.detail == "proc.run" for f in flags), str([f.detail for f in flags]))


def test_ceiling_holds_for_the_real_pairing() -> None:
    runtime, env = assemble("hello")
    excess = env.offered_capabilities() - ChatFramework.ceiling
    check("M2 ui-dialogwin-io stays under the min_chat ceiling", not excess, str(excess))


# --- M3: nulling, not reordering -------------------------------------------


def test_all_nine_phases_occur_in_order() -> None:
    runtime, _ = assemble("hello")
    trace = runtime.run()
    seen = [dict(e.payload)["phase"] for e in trace.entries
            if e.kind in ("ATTEST", "ADVANCE", "TRAVERSE")]
    expected = ["INTENT", "PLAN", "DESIGN", "SCAFFOLD", "IMPLEMENT",
                "VERIFY", "EVALUATE", "DELIVER", "DEBRIEF"]
    check("M3 every phase occurs, in the fixed order", seen == expected, str(seen))


def test_empty_phases_cost_no_model_call() -> None:
    runtime, _ = assemble("hello")
    trace = runtime.run()
    ignitions = len([e for e in trace.entries if e.kind == "PROPOSE"])
    traversed = len([e for e in trace.entries if e.kind == "TRAVERSE"])
    check("M3 nulled phases are traversed without ignition", traversed == 6, f"n={traversed}")
    check("M3 a chat turn costs 5 model calls, not 9+", ignitions == 5, f"n={ignitions}")


def test_chat_completes_and_writes() -> None:
    runtime, env = assemble("what is the time?")
    trace = runtime.run()
    check("M3 chat objective completes", trace.termination is Termination.OBJECTIVE_COMPLETE)
    check("M3 the window holds one in and one out", len(env.window) == 2, str(env.window))
    check("M3 record chain intact", trace.verify_chain())


def test_module_swap_leaves_runtime_identical() -> None:
    """Two unrelated compositions, one runtime, no runtime edit between them."""
    a = Runtime(MinimalFramework(), MinimalEnvironment(), __import__(
        "model.stub", fromlist=["StubModel"]).StubModel(), Objective("a", "x", 40)).run()
    b, _ = assemble("hello")
    b = b.run()
    check("M3 both compositions complete on the same runtime",
          a.termination is Termination.OBJECTIVE_COMPLETE
          and b.termination is Termination.OBJECTIVE_COMPLETE)
    check("M3 the two pins differ", a.pin != b.pin)


def main() -> int:
    print(f"\ntrine — module layer  [{FRAMEWORK_MODULE} + {ENVIRONMENT_MODULE}]\n")
    for fn in [
        test_modules_conform,
        test_modules_hold_the_no_diagonal_line,
        test_runtime_untouched_by_modules,
        test_config_has_no_logic,
        test_valid_pairing_composes,
        test_mismatched_pairing_is_flagged_not_fatal,
        test_ceiling_is_enforced_not_named,
        test_ceiling_holds_for_the_real_pairing,
        test_all_nine_phases_occur_in_order,
        test_empty_phases_cost_no_model_call,
        test_chat_completes_and_writes,
        test_module_swap_leaves_runtime_identical,
    ]:
        fn()
    print(f"\n{'FAILED: ' + ', '.join(FAILURES) if FAILURES else 'module layer holds'}\n")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
