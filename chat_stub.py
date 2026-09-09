"""A stubbed chat driver. Reads, then responds, then terminates."""

from __future__ import annotations

from runtime.types import (
    ModelContext,
    Phase,
    Proposal,
    ProposalKind,
    StallReason,
    digest,
)

CARRIED_FORWARD = (
    "respond only; do not advise, assist, or assume expertise",
    "the model proposes; deterministic code disposes",
)


def _stall_report(context: ModelContext) -> Proposal:
    """A stub's honest account. A real model would reason about this."""
    if context.unsatisfiable:
        reason = StallReason.CAPABILITY_MISSING
    elif not context.permitted_actions:
        reason = StallReason.NO_PERMITTED_ACTION
    else:
        reason = StallReason.BLOCKED_PRECONDITION
    return Proposal(ProposalKind.REPORT, context.phase, args=(("stall", reason.value),))


class ChatModel:
    def model_digest(self) -> str:
        return digest(["ChatModel/1", list(CARRIED_FORWARD)])

    def propose(self, context: ModelContext) -> Proposal:
        if context.report_required:
            return _stall_report(context)
        if context.phase is Phase.DEBRIEF and not context.unmet:
            return Proposal(ProposalKind.TERMINATE, context.phase)
        for action in context.permitted_actions:
            if action not in context.completed_actions:
                args = ()
                if action == "chat.write_response":
                    args = (("text", "a response"),)
                return Proposal(ProposalKind.ACT, context.phase, action, args)
        return Proposal(ProposalKind.ADVANCE, context.phase)
