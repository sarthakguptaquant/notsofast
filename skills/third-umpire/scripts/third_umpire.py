"""Third Umpire: a deterministic, dependency-free verification-adequacy guard for agentic loops.

The metaphor is cricket. When an on-field call is high-stakes and contested, you do not let it
stand on the on-field umpire alone; you go to the third umpire, the independent official who reviews
it with evidence the on-field umpire cannot trust by themselves. This guard is that third umpire for
an AI loop: when a loop closes on the model's own self-critique (the on-field call) and the decision
is hard-correctness and high-materiality (a contested, consequential call), the call may not stand on
self-critique alone. It must carry an independent check (cross-model, held-out, tool, or human) or be
escalated.

Grounding (motivation, not proof of this guard):
  - Huang et al., "LLMs Cannot Self-Correct Reasoning Yet," ICLR 2024 (arXiv:2310.01798):
    intrinsic self-correction is unreliable on hard-correctness tasks and can degrade accuracy.
  - Denison et al., "Sycophancy to Subterfuge" (arXiv:2406.10162): a self-improving loop can
    generalize to gaming its own critic.

There is no model in this routing path. The verdict is a pure function of the tagged inputs, so it
replays deterministically and is auditable.

Personal capacity, industry-level. No external dependencies (standard library only).
"""

from __future__ import annotations

from dataclasses import dataclass


class VerificationMode:
    """What closes the loop. SELF (the on-field call) is the only mode the rule restricts."""
    SELF = "self"
    PEER = "peer"
    TOOL = "tool"
    HUMAN = "human"
    ALL = (SELF, PEER, TOOL, HUMAN)


class TaskType:
    """SOFT: open-ended generation where self-feedback helps. HARD_CORRECTNESS: a checkable,
    costly-to-get-wrong answer where intrinsic self-correction is unreliable. UNKNOWN defaults
    to HARD_CORRECTNESS (the safe side)."""
    SOFT = "soft"
    HARD_CORRECTNESS = "hard_correctness"
    UNKNOWN = "unknown"


class Materiality:
    """LOW: reversible and cheap. HIGH: costly and hard to reverse. UNKNOWN defaults to HIGH."""
    LOW = "low"
    HIGH = "high"
    UNKNOWN = "unknown"


# Verdicts (the third umpire's call)
ALLOW = "ALLOW"
REQUIRE_INDEPENDENT_CHECK = "REQUIRE_INDEPENDENT_CHECK"
ESCALATE = "ESCALATE"


@dataclass(frozen=True)
class Decision:
    """A single consequential loop decision to be reviewed.

    verification_mode    : one of VerificationMode.* (what closes the loop).
    task_type            : one of TaskType.* (UNKNOWN allowed; defaults conservatively).
    materiality          : one of Materiality.* (UNKNOWN allowed; defaults conservatively).
    has_independent_check: True iff a non-self check (cross-model, held-out, tool, or human) is
                           already in the loop for this decision.
    independent_check_available: whether the loop *could* add one. If False and an independent
                           check is required but absent, the verdict is ESCALATE (hand to a human)
                           rather than REQUIRE_INDEPENDENT_CHECK (which assumes one can be added).
    """
    verification_mode: str
    task_type: str = TaskType.UNKNOWN
    materiality: str = Materiality.UNKNOWN
    has_independent_check: bool = False
    independent_check_available: bool = True


def _effective_task(task_type: str) -> str:
    """UNKNOWN or anything unrecognized resolves to HARD_CORRECTNESS (the safe side)."""
    return TaskType.SOFT if task_type == TaskType.SOFT else TaskType.HARD_CORRECTNESS


def _effective_materiality(materiality: str) -> str:
    """UNKNOWN or anything unrecognized resolves to HIGH (the safe side)."""
    return Materiality.LOW if materiality == Materiality.LOW else Materiality.HIGH


def review(decision: Decision) -> str:
    """The third umpire's call on a decision: ALLOW, REQUIRE_INDEPENDENT_CHECK, or ESCALATE.

    The rule fires only when the loop is closed by self-critique on a hard-correctness,
    high-materiality decision. In every other case the verdict is ALLOW: the contract is
    deliberately thin and restricts exactly one unsafe pattern.
    """
    if decision.verification_mode not in VerificationMode.ALL:
        raise ValueError(
            f"unknown verification_mode {decision.verification_mode!r}; "
            f"expected one of {VerificationMode.ALL}"
        )

    mode = decision.verification_mode
    task = _effective_task(decision.task_type)
    matl = _effective_materiality(decision.materiality)

    rule_applies = (
        mode == VerificationMode.SELF
        and task == TaskType.HARD_CORRECTNESS
        and matl == Materiality.HIGH
    )
    if not rule_applies:
        return ALLOW
    if decision.has_independent_check:
        return ALLOW
    if decision.independent_check_available:
        return REQUIRE_INDEPENDENT_CHECK
    return ESCALATE


def explain(decision: Decision) -> str:
    """Human-readable rationale for the call, for logging and audit."""
    verdict = review(decision)
    task = _effective_task(decision.task_type)
    matl = _effective_materiality(decision.materiality)
    defaulted = []
    if decision.task_type not in (TaskType.SOFT, TaskType.HARD_CORRECTNESS):
        defaulted.append(f"task_type defaulted to {task}")
    if decision.materiality not in (Materiality.LOW, Materiality.HIGH):
        defaulted.append(f"materiality defaulted to {matl}")
    note = f" ({'; '.join(defaulted)})" if defaulted else ""
    return (
        f"verdict={verdict}; mode={decision.verification_mode}, task={task}, materiality={matl}, "
        f"independent_check={'present' if decision.has_independent_check else 'absent'}{note}"
    )


if __name__ == "__main__":
    examples = [
        Decision(VerificationMode.SELF, TaskType.HARD_CORRECTNESS, Materiality.HIGH, False),
        Decision(VerificationMode.SELF, TaskType.HARD_CORRECTNESS, Materiality.HIGH, True),
        Decision(VerificationMode.SELF, TaskType.SOFT, Materiality.LOW, False),
        Decision(VerificationMode.SELF, TaskType.UNKNOWN, Materiality.UNKNOWN, False),
        Decision(VerificationMode.TOOL, TaskType.HARD_CORRECTNESS, Materiality.HIGH, False),
        Decision(VerificationMode.SELF, TaskType.HARD_CORRECTNESS, Materiality.HIGH, False,
                 independent_check_available=False),
    ]
    for d in examples:
        print(explain(d))
