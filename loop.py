"""The runtime cycle. Fixed order, every deployment, forever.

    attest -> [ ignite -> propose -> admit -> grant -> dispatch -> return
                -> record -> progress ] * -> terminate

Variation is expressed by nulling a segment, never by reordering one. A
deployment that needs no capability supplies an Environment that grants an
empty set. The ordering is what makes this the same runtime.
"""

from __future__ import annotations

from .surfaces import EnvironmentPort, FrameworkPort, ModelPort
from .types import (
    Attestation,
    FrameworkView,
    ModelContext,
    Objective,
    Phase,
    Proposal,
    ProposalKind,
    Reason,
    Result,
    Status,
    Termination,
    Trace,
    Verdict,
)


class Runtime:
    def __init__(
        self,
        framework: FrameworkPort,
        environment: EnvironmentPort,
        model: ModelPort,
        objective: Objective,
    ) -> None:
        self._framework = framework
        self._environment = environment
        self._model = model
        self._objective = objective
        self._phase = Phase.INTENT
        self._completed: set[str] = set()
        self._tick = 0
        self._last_status = "NONE"
        self._open_grants: set[str] = set()

    # -- segment 0: attest ------------------------------------------------

    def attest(self) -> Attestation:
        """Pin the world. Nothing ignites until this returns."""
        return Attestation(
            rules_digest=self._framework.rules_digest(),
            capability_digest=self._environment.capability_digest(),
            objective_digest=self._objective.to_digest(),
            model_digest=self._model.model_digest(),
        )

    def _view(self) -> FrameworkView:
        return FrameworkView(
            phase=self._phase,
            tick=self._tick,
            completed_actions=frozenset(self._completed),
        )

    # -- the cycle --------------------------------------------------------

    def run(self) -> Trace:
        pin = self.attest()
        trace = Trace(pin=pin.pin)
        trace.append(0, "ATTEST", pin=pin.pin, phase=self._phase.name)

        while True:
            # Re-attest. Anything mutable between pin and use was never pinned.
            if self.attest().pin != pin.pin:
                trace.append(self._tick, "HALT", reason=Termination.ATTESTATION_BROKEN.value)
                trace.termination = Termination.ATTESTATION_BROKEN
                break

            if self._tick >= self._objective.budget:
                trace.append(self._tick, "HALT", reason=Termination.BUDGET_EXHAUSTED.value)
                trace.termination = Termination.BUDGET_EXHAUSTED
                break

            self._tick += 1
            proposal = self._ignite()
            trace.append(
                self._tick,
                "PROPOSE",
                kind=proposal.kind.value,
                phase=proposal.phase.name,
                action=proposal.action,
            )

            done = self._service(proposal, trace)
            if done:
                trace.termination = Termination.OBJECTIVE_COMPLETE
                break

        trace.final_phase = self._phase
        trace.ticks = self._tick
        return trace

    # -- segment 1: ignite ------------------------------------------------

    def _ignite(self) -> Proposal:
        context = ModelContext(
            phase=self._phase,
            target=self._objective.target,
            permitted_actions=self._framework.permitted_actions(self._phase),
            completed_actions=tuple(sorted(self._completed)),
            unmet=self._framework.unmet(self._view()),
            last_status=self._last_status,
            tick=self._tick,
            budget=self._objective.budget,
        )
        return self._model.propose(context)

    # -- segments 2-6 -----------------------------------------------------

    def _service(self, proposal: Proposal, trace: Trace) -> bool:
        """Returns True only when the objective is complete."""

        # The runtime's own check, before the framework's: a proposal for a
        # phase we are not in is malformed regardless of what any rule says.
        if proposal.phase is not self._phase:
            self._refuse(trace, Reason.WRONG_PHASE)
            return False

        verdict = self._framework.admit(self._view(), proposal)
        if not verdict.admitted:
            self._refuse(trace, verdict.reason)
            return False

        if proposal.kind is ProposalKind.TERMINATE:
            return self._service_terminate(trace)
        if proposal.kind is ProposalKind.ADVANCE:
            return self._service_advance(trace)
        return self._service_act(proposal, trace)

    def _service_terminate(self, trace: Trace) -> bool:
        # Self-declared completion is a proposal, not a fact. Two independent
        # conditions the model does not control must also hold.
        if self._phase is not Phase.DEBRIEF:
            self._refuse(trace, Reason.NOT_TERMINAL_PHASE)
            return False
        unmet = self._framework.unmet(self._view())
        if unmet:
            self._refuse(trace, Reason.REQUIREMENTS_UNMET, detail=unmet[0])
            return False
        trace.append(self._tick, "TERMINATE", phase=self._phase.name)
        self._last_status = Status.FULFILLED.value
        return True

    def _service_advance(self, trace: Trace) -> bool:
        target = self._phase.next()
        if target is None:
            self._refuse(trace, Reason.WRONG_PHASE)
            return False
        entry = self._framework.may_enter(self._view(), target)
        if not entry.admitted:
            self._refuse(trace, entry.reason)
            return False
        self._phase = target
        self._last_status = Status.FULFILLED.value
        trace.append(self._tick, "ADVANCE", phase=self._phase.name)
        return False

    def _service_act(self, proposal: Proposal, trace: Trace) -> bool:
        # segment 3: grant. Phase is the scope; capability comes from nowhere else.
        grant = self._environment.grant(self._phase, proposal.action)
        if grant is None:
            self._refuse(trace, Reason.NO_CAPABILITY)
            return False
        self._open_grants.add(grant.grant_id)

        # segment 4: dispatch. The runtime does not perform, and does not watch.
        result = self._environment.dispatch(grant, proposal)

        # segment 5: return. The grant closes here whatever the outcome.
        self._open_grants.discard(grant.grant_id)
        self._last_status = result.status.value
        if result.status is Status.FULFILLED:
            self._completed.add(proposal.action)

        # segment 6: record.
        trace.append(
            self._tick,
            "ACT",
            action=proposal.action,
            status=result.status.value,
            code=result.code,
            caps=len(grant.capabilities),
        )
        return False

    def _refuse(self, trace: Trace, reason: Reason, detail: str = "") -> None:
        self._last_status = Status.REFUSED.value
        trace.append(self._tick, "REFUSE", reason=reason.value, detail=detail)

    @property
    def open_grants(self) -> int:
        return len(self._open_grants)
