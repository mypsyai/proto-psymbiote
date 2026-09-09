"""A Framework. Not the Framework — one implementation of the fixed surface.

The fixed half is the five methods. Everything below them — that rules happen
to be expressed as a table of action names, that entry conditions happen to be
expressed as required completions — is the fluid half. Swap all of it and the
runtime does not notice.
"""

from __future__ import annotations

from runtime.types import (
    FrameworkView,
    Phase,
    Proposal,
    ProposalKind,
    Reason,
    Verdict,
    digest,
)

# ---- fluid half -----------------------------------------------------------

PERMITTED: dict[Phase, tuple[str, ...]] = {
    Phase.INTENT: ("intent.state",),
    Phase.PLAN: ("plan.draft",),
    Phase.DESIGN: ("design.draft", "design.read"),
    Phase.SCAFFOLD: ("scaffold.create",),
    Phase.IMPLEMENT: ("implement.write", "implement.read"),
    Phase.VERIFY: ("verify.run",),
    Phase.EVALUATE: ("evaluate.score",),
    Phase.DELIVER: ("deliver.emit",),
    Phase.DEBRIEF: ("debrief.record",),
}

# A phase may only be entered once these actions have completed.
ENTRY: dict[Phase, tuple[str, ...]] = {
    Phase.PLAN: ("intent.state",),
    Phase.DESIGN: ("plan.draft",),
    Phase.SCAFFOLD: ("design.draft",),
    Phase.IMPLEMENT: ("scaffold.create",),
    Phase.VERIFY: ("implement.write",),
    Phase.EVALUATE: ("verify.run",),
    Phase.DELIVER: ("evaluate.score",),
    Phase.DEBRIEF: ("deliver.emit",),
}

# The runtime may not stop until every one of these has happened.
REQUIRED = ("verify.run", "evaluate.score", "deliver.emit", "debrief.record")

PROHIBITIONS = (
    "the model never advances its own phase without admission",
    "the model never terminates its own objective",
    "no action outside the phase vocabulary",
)


class MinimalFramework:
    # ---- fixed half -------------------------------------------------------

    def rules_digest(self) -> str:
        return digest(
            [
                {p.name: list(a) for p, a in PERMITTED.items()},
                {p.name: list(a) for p, a in ENTRY.items()},
                list(REQUIRED),
                list(PROHIBITIONS),
            ]
        )

    def permitted_actions(self, phase: Phase) -> tuple[str, ...]:
        return PERMITTED.get(phase, ())

    def admit(self, view: FrameworkView, proposal: Proposal) -> Verdict:
        if proposal.kind is ProposalKind.ACT:
            if proposal.action not in PERMITTED.get(view.phase, ()):
                return Verdict(False, Reason.ACTION_NOT_PERMITTED)
            return Verdict(True)
        # ADVANCE and TERMINATE are admissible as proposals; whether they are
        # *satisfiable* is decided by may_enter / unmet, which the model does
        # not influence.
        return Verdict(True)

    def may_enter(self, view: FrameworkView, target: Phase) -> Verdict:
        for need in ENTRY.get(target, ()):
            if need not in view.completed_actions:
                return Verdict(False, Reason.PHASE_ENTRY_UNMET)
        return Verdict(True)

    def unmet(self, view: FrameworkView) -> tuple[str, ...]:
        return tuple(a for a in REQUIRED if a not in view.completed_actions)
