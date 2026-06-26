"""Tests for the Not So Fast guard. Run: python test_notsofast.py"""

from notsofast import (
    Decision,
    review,
    VerificationMode,
    TaskType,
    Materiality,
    ALLOW,
    REQUIRE_INDEPENDENT_CHECK,
    ESCALATE,
)


def check(name, got, want):
    assert got == want, f"{name}: got {got!r}, want {want!r}"
    print(f"  ok: {name}")


def main():
    # The rule fires: self-only, hard-correctness, high-materiality, no independent check.
    check(
        "self+hard+high+no-check -> require",
        review(Decision(VerificationMode.SELF, TaskType.HARD_CORRECTNESS,
                        Materiality.HIGH, has_independent_check=False)),
        REQUIRE_INDEPENDENT_CHECK,
    )
    # Independent check present: allowed.
    check(
        "self+hard+high+check -> allow",
        review(Decision(VerificationMode.SELF, TaskType.HARD_CORRECTNESS,
                        Materiality.HIGH, has_independent_check=True)),
        ALLOW,
    )
    # No independent check available at all: escalate to a human.
    check(
        "self+hard+high+no-check+unavailable -> escalate",
        review(Decision(VerificationMode.SELF, TaskType.HARD_CORRECTNESS,
                        Materiality.HIGH, has_independent_check=False,
                        independent_check_available=False)),
        ESCALATE,
    )
    # Soft, low-materiality: the rule does not fire even for self-only.
    check(
        "self+soft+low -> allow",
        review(Decision(VerificationMode.SELF, TaskType.SOFT, Materiality.LOW)),
        ALLOW,
    )
    # Unknown task/materiality default to the safe side, so the rule fires.
    check(
        "self+unknown+unknown -> require (conservative default)",
        review(Decision(VerificationMode.SELF, TaskType.UNKNOWN, Materiality.UNKNOWN)),
        REQUIRE_INDEPENDENT_CHECK,
    )
    # Non-self modes are never restricted by this rule.
    for mode in (VerificationMode.PEER, VerificationMode.TOOL, VerificationMode.HUMAN):
        check(
            f"{mode}+hard+high -> allow",
            review(Decision(mode, TaskType.HARD_CORRECTNESS, Materiality.HIGH)),
            ALLOW,
        )
    # Self on hard-correctness but low materiality: rule does not fire.
    check(
        "self+hard+low -> allow",
        review(Decision(VerificationMode.SELF, TaskType.HARD_CORRECTNESS, Materiality.LOW)),
        ALLOW,
    )
    # Self on soft but high materiality: rule does not fire (task is soft).
    check(
        "self+soft+high -> allow",
        review(Decision(VerificationMode.SELF, TaskType.SOFT, Materiality.HIGH)),
        ALLOW,
    )
    # Bad mode raises.
    try:
        review(Decision("magic", TaskType.SOFT, Materiality.LOW))
        raise AssertionError("expected ValueError for unknown mode")
    except ValueError:
        print("  ok: unknown mode raises ValueError")

    print("all tests passed")


if __name__ == "__main__":
    main()
