"""Fixed vocabulary. Every value that crosses a boundary has a type here.

Nothing in this module knows what a Framework or an Environment is. It is the
shared alphabet, not a dependency on either.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum

MAX_SCALAR_LEN = 64


class Phase(Enum):
    """The model's loop. Ordered, fixed, never reordered by a deployment."""

    INTENT = 1
    PLAN = 2
    DESIGN = 3
    SCAFFOLD = 4
    IMPLEMENT = 5
    VERIFY = 6
    EVALUATE = 7
    DELIVER = 8
    DEBRIEF = 9

    def next(self) -> "Phase | None":
        return PHASE_ORDER[self.value] if self.value < len(PHASE_ORDER) else None


PHASE_ORDER: tuple[Phase, ...] = tuple(sorted(Phase, key=lambda p: p.value))


class ProposalKind(Enum):
    ACT = "ACT"
    ADVANCE = "ADVANCE"
    TERMINATE = "TERMINATE"
    REPORT = "REPORT"


class StallReason(Enum):
    """Closed vocabulary for 'why am I not moving'.

    The model is required to account for a stall before the runtime forces
    progress past it. An enum, not prose: a stall report that arrived as a
    sentence would be the first thing to cross the boundary uninspected, and
    an unrecognised code is recorded as UNKNOWN rather than trusted.
    """

    BLOCKED_PRECONDITION = "BLOCKED_PRECONDITION"
    NO_PERMITTED_ACTION = "NO_PERMITTED_ACTION"
    CAPABILITY_MISSING = "CAPABILITY_MISSING"
    AWAITING_AUTHORIZATION = "AWAITING_AUTHORIZATION"
    AWAITING_INPUT = "AWAITING_INPUT"
    OBJECTIVE_UNCLEAR = "OBJECTIVE_UNCLEAR"
    UNKNOWN = "UNKNOWN"


class Reason(Enum):
    """Refusal codes. Enumerated so a refusal never carries prose."""

    OK = "OK"
    WRONG_PHASE = "WRONG_PHASE"
    ACTION_NOT_PERMITTED = "ACTION_NOT_PERMITTED"
    ACTION_UNKNOWN = "ACTION_UNKNOWN"
    NO_CAPABILITY = "NO_CAPABILITY"
    PHASE_ENTRY_UNMET = "PHASE_ENTRY_UNMET"
    REQUIREMENTS_UNMET = "REQUIREMENTS_UNMET"
    NOT_TERMINAL_PHASE = "NOT_TERMINAL_PHASE"
    MALFORMED = "MALFORMED"


class Status(Enum):
    FULFILLED = "FULFILLED"
    FAILED = "FAILED"
    REFUSED = "REFUSED"


class Termination(Enum):
    """Only the last two are catastrophic. Everything else finishes."""

    OBJECTIVE_COMPLETE = "OBJECTIVE_COMPLETE"
    COMPLETE_DEGRADED = "COMPLETE_DEGRADED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    ATTESTATION_BROKEN = "ATTESTATION_BROKEN"
    HARM_HALT = "HARM_HALT"


class Severity(Enum):
    """A flag is not a failure. The show goes on and says so."""

    ADVISORY = "ADVISORY"
    DEGRADED = "DEGRADED"


def digest(value: object) -> str:
    """Canonical digest. Same value, same string, every run, every machine."""
    blob = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _check_scalar(key: str, value: object) -> None:
    if not isinstance(value, (str, int, bool)):
        raise ValueError(f"arg {key!r} is not a scalar")
    if isinstance(value, str) and len(value) > MAX_SCALAR_LEN:
        raise ValueError(f"arg {key!r} exceeds {MAX_SCALAR_LEN} chars")


@dataclass(frozen=True)
class Objective:
    """What resolution is being sought. Opaque to the runtime."""

    objective_id: str
    target: str
    budget: int
    breadth_limit: float = 0.30
    breadth_floor: int = 5
    """Reaching wide is the signature of an objective that is really several.
    Both conditions must hold: more than `breadth_limit` of the offered
    vocabulary AND at least `breadth_floor` distinct actions. A ratio alone is
    meaningless over a two-action vocabulary, where every honest run is 100%.
    Advisory, never a halt."""

    stall_limit: int = 10
    """Consecutive ticks with no state change before the runtime stops waiting.
    A real model needs room to propose, be refused, and adjust; three was
    aggressive enough to force it out of phases it was working in honestly.
    On reaching the limit the model must file a StallReason, which is flagged
    and recorded, and then progress is forced."""

    def __post_init__(self) -> None:
        if self.budget < 1:
            raise ValueError("budget must be >= 1")
        if not 0 < self.breadth_limit <= 1:
            raise ValueError("breadth_limit must be in (0, 1]")
        if self.breadth_floor < 1 or self.stall_limit < 1:
            raise ValueError("breadth_floor and stall_limit must be >= 1")

    def to_digest(self) -> str:
        return digest([self.objective_id, self.target, self.budget,
                       self.breadth_limit, self.breadth_floor, self.stall_limit])


@dataclass(frozen=True)
class Proposal:
    """Model output. A request, never an action.

    Args are scalars only and bounded in length. This is where 'no prose
    crosses a boundary' stops being a preference and becomes a constructor.
    """

    kind: ProposalKind
    phase: Phase
    action: str = ""
    args: tuple[tuple[str, str | int | bool], ...] = ()

    def __post_init__(self) -> None:
        if len(self.action) > MAX_SCALAR_LEN:
            raise ValueError("action name too long")
        if self.kind is ProposalKind.ACT and not self.action:
            raise ValueError("ACT proposal requires an action")
        if self.kind is not ProposalKind.ACT and self.action:
            raise ValueError("only ACT proposals carry an action")
        if self.kind is ProposalKind.REPORT:
            args = dict(self.args)
            if set(args) != {"stall"}:
                raise ValueError("REPORT proposal carries exactly one arg: stall")
            if args["stall"] not in {r.value for r in StallReason}:
                raise ValueError("stall reason must come from the closed vocabulary")
        for key, value in self.args:
            _check_scalar(key, value)


@dataclass(frozen=True)
class Verdict:
    admitted: bool
    reason: Reason = Reason.OK


@dataclass(frozen=True)
class Grant:
    """A bounded capability, scoped to one phase and one proposal. Single use."""

    grant_id: str
    phase: Phase
    action: str
    capabilities: frozenset[str]


@dataclass(frozen=True)
class Result:
    status: Status
    code: str = ""

    def __post_init__(self) -> None:
        _check_scalar("code", self.code)


@dataclass(frozen=True)
class Flag:
    """A named condition the system is operating in spite of."""

    severity: Severity
    code: str
    detail: str = ""

    def __post_init__(self) -> None:
        _check_scalar("code", self.code)
        _check_scalar("detail", self.detail)


@dataclass(frozen=True)
class FrameworkView:
    """Everything the Framework may see. Closed and finite by construction."""

    phase: Phase
    tick: int
    completed_actions: frozenset[str]
    flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModelContext:
    """Everything the model may see. Closed and finite by construction.

    No wildcards, no 'and any relevant files'. If a thing is not a field here,
    the model does not have it.
    """

    phase: Phase
    target: str
    permitted_actions: tuple[str, ...]
    completed_actions: tuple[str, ...]
    unmet: tuple[str, ...]
    unsatisfiable: tuple[str, ...]
    flags: tuple[str, ...]
    stall_ticks: int
    report_required: bool
    """True when the runtime has stopped waiting and needs an account of the
    stall before it forces progress. The only tick where REPORT is admissible."""
    last_status: str
    tick: int
    budget: int


@dataclass(frozen=True)
class Attestation:
    """The pin. Taken once, before ignition, and rechecked every tick."""

    rules_digest: str
    capability_digest: str
    objective_digest: str
    model_digest: str

    @property
    def pin(self) -> str:
        return digest(
            [
                self.rules_digest,
                self.capability_digest,
                self.objective_digest,
                self.model_digest,
            ]
        )


@dataclass(frozen=True)
class Entry:
    """One link in the record. Hash-chained, append-only."""

    index: int
    tick: int
    kind: str
    payload: tuple[tuple[str, str | int | bool], ...]
    prev_hash: str

    @property
    def entry_hash(self) -> str:
        return digest([self.index, self.tick, self.kind, list(self.payload), self.prev_hash])


@dataclass
class Trace:
    pin: str
    entries: list[Entry] = field(default_factory=list)
    termination: Termination | None = None
    final_phase: Phase = Phase.INTENT
    ticks: int = 0
    flags: list[Flag] = field(default_factory=list)

    @property
    def degraded(self) -> bool:
        return any(f.severity is Severity.DEGRADED for f in self.flags)

    def append(self, tick: int, kind: str, /, **payload: str | int | bool) -> Entry:
        prev = self.entries[-1].entry_hash if self.entries else self.pin
        entry = Entry(
            index=len(self.entries),
            tick=tick,
            kind=kind,
            payload=tuple(sorted(payload.items())),
            prev_hash=prev,
        )
        self.entries.append(entry)
        return entry

    def verify_chain(self) -> bool:
        prev = self.pin
        for i, entry in enumerate(self.entries):
            if entry.index != i or entry.prev_hash != prev:
                return False
            prev = entry.entry_hash
        return True
