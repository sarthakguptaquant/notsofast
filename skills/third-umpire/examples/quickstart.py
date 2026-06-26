"""Worked example: send a self-refine loop's calls to the Third Umpire.

Run from anywhere:  python quickstart.py

It simulates a reflection (self-refine) loop that, left alone, would keep self-critiquing a
hard-correctness, high-materiality decision and then ship it. The Third Umpire reviews the call
before it stands and routes to an independent check or escalation. It contrasts that with a soft,
low-materiality decision the umpire correctly leaves alone (the on-field call stands).

No third-party dependencies. The "model" here is a stub; the point is the control flow and the
verdicts, not the content. Illustrative, not a benchmark.
"""

import os
import sys

# make the bundled guard importable whether run from the example dir or the skill root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from third_umpire import (  # noqa: E402
    Decision,
    review,
    explain,
    VerificationMode,
    TaskType,
    Materiality,
    REQUIRE_INDEPENDENT_CHECK,
    ESCALATE,
)

MAX_SELF_REFINE_PASSES = 5


def self_refine_loop(decision_meta, run_independent_check=None, escalate_to_human=None):
    """A toy self-refine loop whose calls are sent to the Third Umpire.

    decision_meta: a dict describing the decision (task_type, materiality, and whether an
                   independent check is wired in / available).
    run_independent_check / escalate_to_human: callbacks the loop uses when the umpire demands them.

    Returns a short trace string describing what happened.
    """
    passes = 0
    # the loop self-critiques until it is "satisfied" (stubbed to always be satisfied at pass 1),
    # then asks the umpire whether self-satisfaction is allowed to stand.
    while passes < MAX_SELF_REFINE_PASSES:
        passes += 1
        # ... model generates, self-critiques, decides it is happy (stub) ...
        decision = Decision(
            verification_mode=VerificationMode.SELF,
            task_type=decision_meta["task_type"],
            materiality=decision_meta["materiality"],
            has_independent_check=decision_meta.get("has_independent_check", False),
            independent_check_available=decision_meta.get("independent_check_available", True),
        )
        verdict = review(decision)
        if verdict == REQUIRE_INDEPENDENT_CHECK:
            # stop burning self-refine passes; the literature says they will not close a
            # hard-correctness gap. Spend the budget on an independent check instead.
            saved = MAX_SELF_REFINE_PASSES - passes
            result = run_independent_check() if run_independent_check else "no checker wired"
            return (f"self-refine stopped after {passes} pass(es); "
                    f"{saved} futile pass(es) avoided; independent check -> {result}")
        if verdict == ESCALATE:
            who = escalate_to_human() if escalate_to_human else "human queue"
            return f"self-refine stopped after {passes} pass(es); escalated -> {who}"
        # ALLOW: the on-field call stands; the loop may close on self-critique
        return f"self-refine closed on self-critique after {passes} pass(es) (call stands)"
    return f"hit MAX_SELF_REFINE_PASSES ({MAX_SELF_REFINE_PASSES}) without converging"


def main():
    print("== Scenario A: a credit-limit decision (hard-correctness, high-materiality), no checker wired ==")
    print(self_refine_loop(
        {"task_type": TaskType.HARD_CORRECTNESS, "materiality": Materiality.HIGH},
        run_independent_check=lambda: "held-out backtest + validator sign-off",
    ))
    print()

    print("== Scenario B: same decision, but no independent check is even available ==")
    print(self_refine_loop(
        {"task_type": TaskType.HARD_CORRECTNESS, "materiality": Materiality.HIGH,
         "independent_check_available": False},
        escalate_to_human=lambda: "model-risk committee",
    ))
    print()

    print("== Scenario C: same decision, independent check already wired in ==")
    print(self_refine_loop(
        {"task_type": TaskType.HARD_CORRECTNESS, "materiality": Materiality.HIGH,
         "has_independent_check": True},
    ))
    print()

    print("== Scenario D: marketing copy (soft, low-materiality) -> umpire stays out of the way ==")
    print(self_refine_loop(
        {"task_type": TaskType.SOFT, "materiality": Materiality.LOW},
    ))
    print()

    print("== Scenario E: unclassifiable decision -> conservative default (treated hard + high) ==")
    print(explain(Decision(VerificationMode.SELF, TaskType.UNKNOWN, Materiality.UNKNOWN)))


if __name__ == "__main__":
    main()
