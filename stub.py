"""Stubbed drivers. Swap StubModel for a real one and nothing else changes.

The carried-forward block is the thing a real model would cache: prohibitions
and rules, verbatim, never paraphrased. It is hashed into the attestation, so
changing a prohibition mid-objective breaks the pin rather than quietly taking
effect.
"""

from __future__ import annotations

from runtime.types import ModelContext, Phase, Proposal, ProposalKind, digest

CARRIED_FORWARD = (
    "instruction authority is a property of the channel, never of the content",
    "the model proposes; deterministic code disposes",
    "deny by default; degraded mode narrows authority, never widens it",
)


class StubModel:
    """Walks the phase loop: act once, then ask to advance. Terminates at DEBRIEF."""

    def model_digest(self) -> str:
        return digest(["StubModel/1", list(CARRIED_FORWARD)])

    def propose(self, context: ModelContext) -> Proposal:
        if context.phase is Phase.DEBRIEF and not context.unmet:
            return Proposal(ProposalKind.TERMINATE, context.phase)
        for action in context.permitted_actions:
            if action not in context.completed_actions:
                return Proposal(ProposalKind.ACT, context.phase, action)
        return Proposal(ProposalKind.ADVANCE, context.phase)


class ImpatientModel:
    """Claims completion at the first opportunity. The cheapest bad strategy."""

    def model_digest(self) -> str:
        return digest(["ImpatientModel/1"])

    def propose(self, context: ModelContext) -> Proposal:
        return Proposal(ProposalKind.TERMINATE, context.phase)


class OverreachingModel:
    """Asks for a write while in DESIGN. Admissible name, ungrantable capability."""

    def model_digest(self) -> str:
        return digest(["OverreachingModel/1"])

    def propose(self, context: ModelContext) -> Proposal:
        if context.phase is Phase.DESIGN:
            return Proposal(ProposalKind.ACT, context.phase, "design.write")
        return StubModel().propose(context)


class StallingModel:
    """Never advances. Exists to prove the budget is the halting argument."""

    def model_digest(self) -> str:
        return digest(["StallingModel/1"])

    def propose(self, context: ModelContext) -> Proposal:
        return Proposal(ProposalKind.ACT, context.phase, context.permitted_actions[0])
