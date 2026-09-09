"""ui-dialogwin-io — Environment module. A dialog window and nothing else.

This module has never heard of min_chat. It offers two capabilities and does
not know or care which Framework asks for them. That is the no-diagonal rule
holding at the module layer.
"""

from __future__ import annotations

import uuid

from runtime.types import Grant, Phase, Proposal, Result, Status, digest

MODULE_ID = "ui-dialogwin-io"

PHASE_CAPS: dict[Phase, frozenset[str]] = {
    Phase.INTENT: frozenset({"ui.read"}),
    Phase.PLAN: frozenset(),
    Phase.DESIGN: frozenset(),
    Phase.SCAFFOLD: frozenset(),
    Phase.IMPLEMENT: frozenset(),
    Phase.VERIFY: frozenset(),
    Phase.EVALUATE: frozenset(),
    Phase.DELIVER: frozenset({"ui.write"}),
    Phase.DEBRIEF: frozenset(),
}

ACTION_CAPS: dict[str, frozenset[str]] = {
    "chat.read_prompt": frozenset({"ui.read"}),
    "chat.write_response": frozenset({"ui.write"}),
}


class DialogEnvironment:
    module_id = MODULE_ID

    def __init__(self, prompt: str = "hello") -> None:
        self._prompt = prompt
        self.window: list[tuple[str, str]] = []

    def capability_digest(self) -> str:
        return digest(
            [
                MODULE_ID,
                {p.name: sorted(c) for p, c in PHASE_CAPS.items()},
                {a: sorted(c) for a, c in ACTION_CAPS.items()},
            ]
        )

    def offered_capabilities(self) -> frozenset[str]:
        return frozenset().union(*PHASE_CAPS.values()) if PHASE_CAPS else frozenset()

    def offered_actions(self) -> frozenset[str]:
        return frozenset(ACTION_CAPS)

    def capabilities_for(self, action: str) -> frozenset[str]:
        return ACTION_CAPS.get(action, frozenset())

    def health(self) -> tuple[str, ...]:
        return ()  # a real Environment probes memory, disk, and thermal here

    def can_grant(self, phase: Phase, action: str) -> bool:
        needed = ACTION_CAPS.get(action)
        if needed is None:
            return False
        return needed.issubset(PHASE_CAPS.get(phase, frozenset()))

    def grant(self, phase: Phase, action: str) -> Grant | None:
        if not self.can_grant(phase, action):
            return None
        return Grant(
            grant_id=uuid.uuid4().hex,
            phase=phase,
            action=action,
            capabilities=frozenset(ACTION_CAPS[action]),
        )

    def dispatch(self, grant: Grant, proposal: Proposal) -> Result:
        if grant.action == "chat.read_prompt":
            self.window.append(("in", self._prompt))
            return Result(Status.FULFILLED, "READ")
        if grant.action == "chat.write_response":
            text = dict(proposal.args).get("text", "")
            self.window.append(("out", str(text)))
            return Result(Status.FULFILLED, "WROTE")
        return Result(Status.REFUSED, "NO_HANDLER")
