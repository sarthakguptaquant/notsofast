"""Rigorous, adversarial conformance test for the notsofast guard.

This is an INDEPENDENT check, not a restatement of the implementation. The expected
verdict is derived from the documented contract (the module and Decision docstrings),
encoded here by hand, and compared against the live code across the full input cross
product plus hostile inputs. If the code ever drifts from its own documentation, this
fails. Standard library only; run with: python test_notsofast_rigorous.py
"""

from __future__ import annotations

import itertools

import notsofast as tu
from notsofast import Decision


# --- Independent restatement of the documented contract -------------------------------
# Derived from the docstrings in notsofast.py, written WITHOUT looking at the branch
# order in review(). If this disagrees with the code, one of them is wrong.

VALID_MODES = {"self", "peer", "tool", "human"}


def expected_verdict(mode, task, matl, has_check, check_available):
    """The contract, restated independently."""
    if mode not in VALID_MODES:
        return "ValueError"
    eff_task = "soft" if task == "soft" else "hard_correctness"
    eff_matl = "low" if matl == "low" else "high"
    rule_applies = (mode == "self" and eff_task == "hard_correctness" and eff_matl == "high")
    if not rule_applies:
        return "ALLOW"
    if has_check:
        return "ALLOW"
    if check_available:
        return "REQUIRE_INDEPENDENT_CHECK"
    return "ESCALATE"


# --- Input space, including garbage on every free-text field --------------------------
MODES = ["self", "peer", "tool", "human", "unknown", "Self", "SELF", "", "self ", None, 0]
TASKS = ["soft", "hard_correctness", "unknown", "Soft", "HARD_CORRECTNESS", "", "garbage", None]
MATLS = ["low", "high", "unknown", "Low", "HIGH", "", "garbage", None]
BOOLS = [True, False]

failures = []
checked = 0


def actual_verdict(d):
    try:
        return tu.review(d)
    except ValueError:
        return "ValueError"


# 1. EXHAUSTIVE CONFORMANCE: full cross product vs the independent contract.
for mode, task, matl, has_check, avail in itertools.product(MODES, TASKS, MATLS, BOOLS, BOOLS):
    d = Decision(mode, task, matl, has_check, avail)
    exp = expected_verdict(mode, task, matl, has_check, avail)
    act = actual_verdict(d)
    checked += 1
    if exp != act:
        failures.append(f"CONFORMANCE: {mode!r},{task!r},{matl!r},{has_check},{avail} "
                        f"expected {exp} got {act}")

# 2. CONSERVATIVE DEFAULTS: every non-'soft' task on a self+high+no-check decision must
#    fire the rule (treated as hard); every non-'low' materiality likewise.
for task in TASKS:
    d = Decision("self", task, "high", False, True)
    want = "ALLOW" if task == "soft" else "REQUIRE_INDEPENDENT_CHECK"
    if tu.review(d) != want:
        failures.append(f"DEFAULT(task={task!r}): expected {want} got {tu.review(d)}")
for matl in MATLS:
    d = Decision("self", "hard_correctness", matl, False, True)
    want = "ALLOW" if matl == "low" else "REQUIRE_INDEPENDENT_CHECK"
    if tu.review(d) != want:
        failures.append(f"DEFAULT(matl={matl!r}): expected {want} got {tu.review(d)}")

# 3. ESCALATE vs REQUIRE hinge: identical decision, only check-availability flips.
req = Decision("self", "hard_correctness", "high", False, True)
esc = Decision("self", "hard_correctness", "high", False, False)
if tu.review(req) != "REQUIRE_INDEPENDENT_CHECK":
    failures.append("HINGE: available->should REQUIRE")
if tu.review(esc) != "ESCALATE":
    failures.append("HINGE: unavailable->should ESCALATE")

# 4. ONLY SELF IS RESTRICTED: peer/tool/human always ALLOW even at hard+high+no-check.
for mode in ("peer", "tool", "human"):
    d = Decision(mode, "hard_correctness", "high", False, False)
    if tu.review(d) != "ALLOW":
        failures.append(f"NON-SELF {mode}: expected ALLOW got {tu.review(d)}")

# 5. BAD MODE RAISES: None, "", wrong case, numbers.
for bad in (None, "", "SELF", "Self", "selff", 0, 42):
    try:
        tu.review(Decision(bad, "hard_correctness", "high"))
        failures.append(f"BAD MODE {bad!r}: expected ValueError, none raised")
    except ValueError:
        pass

# 6. DETERMINISM / PURITY: same decision reviewed 1000x is identical; explain() agrees
#    with review(); the frozen dataclass cannot be mutated.
d = Decision("self", "unknown", "unknown", False, True)
verdicts = {tu.review(d) for _ in range(1000)}
if len(verdicts) != 1:
    failures.append(f"DETERMINISM: {verdicts}")
for mode, task, matl, hc, av in itertools.product(VALID_MODES, ["soft", "hard_correctness", "x"],
                                                  ["low", "high", "x"], BOOLS, BOOLS):
    dd = Decision(mode, task, matl, hc, av)
    if not tu.explain(dd).startswith(f"verdict={tu.review(dd)};"):
        failures.append(f"EXPLAIN mismatch: {mode},{task},{matl},{hc},{av}")
try:
    d.verification_mode = "peer"  # frozen -> should raise
    failures.append("PURITY: frozen dataclass was mutated")
except Exception:
    pass

# --- Report ---------------------------------------------------------------------------
print(f"checked {checked} cross-product rows + defaults + hinge + non-self + bad-mode "
      f"+ determinism + explain + immutability")
if failures:
    print(f"FAILURES ({len(failures)}):")
    for f in failures[:40]:
        print("  -", f)
    raise SystemExit(1)
print("ALL RIGOROUS CHECKS PASSED")
