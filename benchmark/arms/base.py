"""Verification arms: the three ways a loop can decide an answer is good enough to ship.

The benchmark compares three arms, all behind one interface so the runner is arm-agnostic:

  NO_CHECK    : ship the candidate. No verification. The baseline error rate.
  SELF_CRITIC : the SAME reasoner reviews its own answer WITH full prior context (the task, its
                own chain of reasoning, its own intermediate notes). This is the cheap, common
                mode the critique is about. It tends to ratify its own plausible errors.
  INDEPENDENT : a verifier evaluates the answer in a FRESH context with NO access to the
                original chain of reasoning. True epistemic isolation. It re-derives or
                re-checks from the task alone, so it cannot inherit the original error.

The crux of the whole benchmark is that INDEPENDENT isolation is REAL, not nominal. The
contract below makes it structural: an arm receives a `VerificationInput`, and the INDEPENDENT
arm is constructed so the fields carrying the original reasoning are physically absent from the
object it sees. See arms/mock.py and arms/real_adapter.py for how each enforces it.

A `VerificationVerdict` is the arm's call on one candidate:
  passed=True  : the arm believes the candidate is correct ("looks correct, ship it").
  passed=False : the arm flags the candidate as wrong (catches it).
  tokens       : tokens the arm spent producing this verdict (0 for NO_CHECK).

The arm NEVER sees the ground-truth checker or the `correct` label. It only sees what its
isolation level permits. The runner compares the arm's verdict to ground truth afterward.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Protocol


@dataclass(frozen=True)
class VerificationInput:
    """Everything an arm MIGHT be given about a decision. What it actually receives depends on
    the arm's isolation level.

    task             : the original prompt (every arm sees this; the verifier needs the question).
    candidate        : the answer under review (every arm sees this; it is the thing being judged).
    reasoning_trace  : the original reasoner's chain of thought / intermediate work. ONLY the
                       SELF_CRITIC arm is allowed to see this. For the INDEPENDENT arm it is
                       withheld (set to None at construction), which is the isolation.
    item_id          : identifier, for logging only. Carries no answer information.
    reference        : the checker's reference inputs. NEVER given to any arm. It is listed here
                       only to document, loudly, that arms do not receive ground truth. The
                       runner holds it; the arm does not.
    """

    task: str
    candidate: Any
    item_id: str
    reasoning_trace: Optional[str] = None
    # reference is deliberately NOT a field: ground truth never enters an arm's input object.


@dataclass(frozen=True)
class VerificationVerdict:
    """An arm's call on one candidate."""

    passed: bool          # True = "looks correct, ship it"; False = "flagged as wrong"
    tokens: int           # tokens spent producing this verdict
    arm: str              # which arm produced it
    note: str = ""        # optional short rationale, for the audit trail


class Arm(Protocol):
    """The pluggable interface every verification arm implements.

    name        : a stable label ("no_check", "self_critic", "independent").
    isolation   : "none" | "shared_context" | "isolated". The INDEPENDENT arm MUST report
                  "isolated" and MUST refuse to read a reasoning_trace even if one is present.
    verify(...) : take a VerificationInput, return a VerificationVerdict.
    """

    name: str
    isolation: str

    def verify(self, vin: VerificationInput) -> VerificationVerdict:
        ...


def isolate(vin: VerificationInput) -> VerificationInput:
    """Strip the original reasoning from an input, producing the view an INDEPENDENT verifier
    is allowed to see. This is the single, auditable point where epistemic isolation is
    enforced.

    It returns a NEW frozen input with `reasoning_trace=None`. Because VerificationInput is
    frozen, the INDEPENDENT arm cannot mutate its way back to the trace, and because the field
    is physically None, there is nothing for the arm to peek at even by mistake. An arm that
    wants to cheat would have to be handed the un-isolated object, which the runner never does
    for the independent arm. The isolation is therefore a property of the data flow, not a
    promise in a docstring.
    """
    return VerificationInput(
        task=vin.task,
        candidate=vin.candidate,
        item_id=vin.item_id,
        reasoning_trace=None,
    )
