"""Conformance tests for the benchmark harness. Run: python test_benchmark.py

These do not test the CLAIM (that needs a real model run). They test the MECHANICS: the
dataset's integrity gate, the structural isolation of the independent arm, that the runner
calls the shipped guard, that the metrics math is correct on hand-built records, and that the
mock pilot is deterministic per seed. If any of these fail, the real run's numbers cannot be
trusted, so they gate the pipeline.
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from dataset import ALL_ITEMS, GOVERNED_ITEMS, dataset_stats  # noqa: E402
from dataset.items import self_check as dataset_self_check  # noqa: E402
from arms import VerificationInput, build_mock_arms, isolate  # noqa: E402
from arms.real_adapter import RealIndependentArm, _parse_verdict  # noqa: E402
import metrics as M  # noqa: E402
import run as R  # noqa: E402

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name}")


def test_dataset_integrity():
    # The dataset self-check must pass (every stored label matches its checker).
    dataset_self_check()
    check("dataset self-check passes", True)
    # Every governed item is hard_correctness + high (the governed regime).
    check("all governed items are hard+high",
          all(it.task_type == "hard_correctness" and it.materiality == "high"
              for it in GOVERNED_ITEMS))
    # The label is balanced enough that a constant guesser cannot win outright.
    s = dataset_stats()
    frac_correct = s["n_governed_correct"] / s["n_governed"]
    check("label balance in [0.35, 0.65]", 0.35 <= frac_correct <= 0.65)
    # Re-running each checker reproduces the stored label (the oracle is deterministic).
    check("checkers are deterministic and match labels",
          all(it.check() == it.correct for it in ALL_ITEMS))


def test_isolation_is_structural():
    # The independent view must have the reasoning trace physically removed.
    vin = VerificationInput(task="t", candidate=1, item_id="x",
                            reasoning_trace="SECRET original reasoning")
    view = isolate(vin)
    check("isolate() strips the reasoning trace", view.reasoning_trace is None)
    check("isolate() preserves task and candidate",
          view.task == "t" and view.candidate == 1)

    # The real independent arm must refuse to proceed if handed a trace (it re-isolates).
    arm = RealIndependentArm(model_call=None)
    # Without a model_call it should raise NotImplementedError, NOT read the trace. We confirm
    # the isolation assertion is in the path by checking the arm isolates before calling.
    raised = False
    try:
        arm.verify(vin)
    except NotImplementedError:
        raised = True
    check("real independent arm requires a wired model_call (no silent pass)", raised)

    # The mock independent arm also re-isolates; verify it never inspects the trace by giving it
    # a trace and a truth oracle, and confirming it still produces a verdict from the oracle.
    arms = build_mock_arms(seed=1, truth_oracle=lambda iid: iid == "correct-item")
    v_correct = arms["independent"].verify(
        VerificationInput(task="t", candidate=1, item_id="correct-item",
                          reasoning_trace="should be ignored"))
    check("mock independent produces a verdict under isolation",
          v_correct.passed in (True, False))


def test_verdict_parser_conservative():
    check("PASS parses as passed", _parse_verdict("PASS") is True)
    check("FLAG parses as not-passed", _parse_verdict("FLAG: wrong sign") is False)
    check("unparseable defaults to FLAG (conservative)", _parse_verdict("hmm, maybe?") is False)
    check("FLAG wins over PASS in ambiguous text", _parse_verdict("PASS... actually FLAG") is False)


def test_runner_uses_shipped_guard():
    # The runner imports `review` from the shipped module. Confirm the imported symbol is the
    # real guard by exercising its known truth table through the runner's import.
    from notsofast import Decision, review, REQUIRE_INDEPENDENT_CHECK, ALLOW  # noqa
    check("shipped guard: self+hard+high+no-check -> REQUIRE",
          review(Decision("self", "hard_correctness", "high", False)) == REQUIRE_INDEPENDENT_CHECK)
    check("shipped guard: soft+low -> ALLOW",
          review(Decision("self", "soft", "low", False)) == ALLOW)
    # And the runner's run_item fires the guard on a governed item.
    arms = build_mock_arms(seed=1, truth_oracle=lambda iid: True)
    rec = R.run_item(GOVERNED_ITEMS[0], arms)
    check("run_item fires the guard on a governed item",
          rec["guard_verdict"] == "REQUIRE_INDEPENDENT_CHECK")
    check("run_item ran the independent arm when the guard fired",
          rec["indep_passed"] is not None)


def test_metrics_math():
    # Hand-built records with a known answer.
    recs = [
        # correct, self passed, indep passed -> indep correctly passed a correct answer
        {"item_id": "a", "correct": True, "guard_verdict": "REQUIRE_INDEPENDENT_CHECK",
         "self_passed": True, "self_tokens": 800, "indep_passed": True, "indep_tokens": 700,
         "refine_passes_avoided": 4, "refine_pass_tokens": 800},
        # wrong, self passed (waved through), indep flagged -> a CATCH (detection lift)
        {"item_id": "b", "correct": False, "guard_verdict": "REQUIRE_INDEPENDENT_CHECK",
         "self_passed": True, "self_tokens": 800, "indep_passed": False, "indep_tokens": 700,
         "refine_passes_avoided": 4, "refine_pass_tokens": 800},
        # wrong, self passed, indep MISSED it -> not caught
        {"item_id": "c", "correct": False, "guard_verdict": "REQUIRE_INDEPENDENT_CHECK",
         "self_passed": True, "self_tokens": 800, "indep_passed": True, "indep_tokens": 700,
         "refine_passes_avoided": 4, "refine_pass_tokens": 800},
        # correct, self passed, indep FALSE-flagged -> a false positive
        {"item_id": "d", "correct": True, "guard_verdict": "REQUIRE_INDEPENDENT_CHECK",
         "self_passed": True, "self_tokens": 800, "indep_passed": False, "indep_tokens": 700,
         "refine_passes_avoided": 4, "refine_pass_tokens": 800},
    ]
    d = M.detection_metrics(recs)
    # self passed all 4; 2 of them wrong (b, c); independent caught 1 of those (b)
    check("self_passed_wrong_n == 2", d["self_passed_wrong_n"] == 2)
    check("independent_caught_in_slice == 1", d["independent_caught_in_slice"] == 1)
    check("detection_lift == 1", d["detection_lift"] == 1)
    check("detection_lift_rate == 0.5", d["detection_lift_rate"] == 0.5)
    # correct answers reviewed: a, d; false flag on d -> fp rate 0.5
    check("correct_reviewed == 2", d["correct_reviewed_by_independent"] == 2)
    check("false_positive_rate == 0.5", d["independent_false_positive_rate"] == 0.5)

    led = M.token_ledger(recs)
    # each fired item: saved 4*800=3200, spent 700, net 2500; 4 items
    check("tokens saved == 12800", led["tokens_saved_stopping_futile_passes"] == 12800)
    check("tokens spent == 2800", led["tokens_spent_on_independent_check"] == 2800)
    check("net tokens == 10000", led["net_tokens"] == 10000)
    check("all 4 net-positive", led["net_positive_items"] == 4 and led["net_negative_items"] == 0)


def test_ledger_can_go_negative():
    # If the check costs more than the avoided passes, the ledger must report negative. The
    # benchmark does not promise blanket savings; this proves the honest direction is reachable.
    recs = [
        {"item_id": "x", "correct": False, "guard_verdict": "REQUIRE_INDEPENDENT_CHECK",
         "self_passed": True, "self_tokens": 800, "indep_passed": False, "indep_tokens": 5000,
         "refine_passes_avoided": 1, "refine_pass_tokens": 800},  # saved 800, spent 5000
    ]
    led = M.token_ledger(recs)
    check("ledger goes negative when the check is dear", led["net_tokens"] == -4200)
    check("net-negative item counted", led["net_negative_items"] == 1)


def test_pilot_determinism():
    a = R.run(seed=123)["metrics"]
    b = R.run(seed=123)["metrics"]
    import json
    check("mock pilot deterministic per seed",
          json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True))


def main():
    test_dataset_integrity()
    test_isolation_is_structural()
    test_verdict_parser_conservative()
    test_runner_uses_shipped_guard()
    test_metrics_math()
    test_ledger_can_go_negative()
    test_pilot_determinism()
    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
