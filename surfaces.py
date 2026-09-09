"""The fixed halves.

A Framework and an Environment each have two halves. This module is the half
that faces the runtime: fixed, small, identical in every deployment. The other
half — how the rules are expressed, what the capabilities actually do — is the
implementation's business and the runtime never sees it.

The runtime depends on these protocols. It does not depend on any
implementation of them, and no implementation depends on another.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import FrameworkView, Grant, ModelContext, Phase, Proposal, Result, Verdict


@runtime_checkable
class FrameworkPort(Protocol):
    """The rules. Consulted at admission and nowhere else."""

    def rules_digest(self) -> str:
        """Stable digest of the rule set. Changing a rule must change this."""

    def permitted_actions(self, phase: Phase) -> tuple[str, ...]:
        """The closed action vocabulary for a phase."""

    def admit(self, view: FrameworkView, proposal: Proposal) -> Verdict:
        """Binary. The only place a rule is evaluated."""

    def may_enter(self, view: FrameworkView, target: Phase) -> Verdict:
        """Whether the objective may advance into `target`."""

    def unmet(self, view: FrameworkView) -> tuple[str, ...]:
        """Outstanding requirement codes. Empty means the runtime may stop."""


@runtime_checkable
class EnvironmentPort(Protocol):
    """The world. Grants capability and performs the effect."""

    def capability_digest(self) -> str:
        """Stable digest of the capability map."""

    def grant(self, phase: Phase, action: str) -> Grant | None:
        """Bound capability for one action in one phase. None means refuse."""

    def dispatch(self, grant: Grant, proposal: Proposal) -> Result:
        """Perform the effect. The runtime does not observe how."""


@runtime_checkable
class ModelPort(Protocol):
    """The driver. Sees exactly a ModelContext and returns exactly a Proposal."""

    def model_digest(self) -> str:
        """Identity of the model and its carried-forward block."""

    def propose(self, context: ModelContext) -> Proposal:
        ...
