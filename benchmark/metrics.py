"""Metrics for the Not So Fast benchmark.

Two headline numbers, plus the supporting accounting. Every metric is computed from per-item
records produced by the runner; nothing here calls a model or reads ground truth except through
the records the runner already labeled.

A per-item record (one dict per governed item) carries, at minimum:
    item_id, correct (ground truth, bool),
    guard_verdict (ALLOW | REQUIRE_INDEPENDENT_CHECK | ESCALATE),
    self_passed (bool), self_tokens (int),
    indep_passed (bool | None), indep_tokens (int),
    refine_passes_avoided (int), refine_pass_tokens (int)

----------------------------------------------------------------------------------------------
1. DETECTION LIFT
----------------------------------------------------------------------------------------------
The question the critique demands an answer to: among decisions the same-context self-critic
WAVED THROUGH ("looks correct"), how many does the isolated independent check catch as wrong?

We restrict to the slice the self-critic passed. On that slice:
  - self_caught is 0 by definition (the self-critic passed everything in it).
  - among the items in that slice that are ACTUALLY wrong, count how many the independent arm
    flagged. That is the lift the independent check buys you over trusting self-critique.

We report:
  self_passed_wrong            : wrong answers the self-critic let through (the danger set).
  independent_caught_in_slice  : how many of those the independent arm flagged.
  detection_lift               : independent_caught_in_slice - self_caught_in_slice. Since the
                                 slice is self-PASSED, self_caught_in_slice is 0, so the lift is
                                 simply independent_caught_in_slice. It is still computed as a
                                 difference so the definition is explicit and survives a change
                                 to how the slice is defined.
  detection_lift_rate          : caught / self_passed_wrong (recall of the independent check on
                                 the dangerous slice).

----------------------------------------------------------------------------------------------
2. FALSE-POSITIVE RATE (the real cost of an independent check)
----------------------------------------------------------------------------------------------
Flagging good work is not free: it triggers needless rework or a needless escalation. So we
report the independent arm's false-positive rate on GENUINELY CORRECT answers:
    indep_false_positive_rate = (correct answers the independent arm flagged) /
                                (correct answers it reviewed)
A detection lift means nothing if the check flags half the good answers too. The two numbers
must be read together.

----------------------------------------------------------------------------------------------
3. NET TOKEN LEDGER
----------------------------------------------------------------------------------------------
The guard's token story is NOT "the check is free." It is: when the rule fires, the guard stops
a naive self-refine loop from burning K futile passes on a hard answer it cannot fix, and
spends one independent check instead. So per governed item where the guard fired:

    tokens_saved   = refine_passes_avoided * refine_pass_tokens   (futile passes not run)
    tokens_spent   = indep_tokens                                  (the check that replaces them)
    net            = tokens_saved - tokens_spent

We sum these and report where the guard is net-POSITIVE (saved > spent) and where it is
net-NEGATIVE (the check costs more than the passes it avoided). We do NOT claim blanket savings.
If refine_passes_avoided is small or the check is expensive, the ledger goes negative, and the
benchmark says so.

The comparison baseline for "what would have happened" is the naive self-refine loop: without
the guard, a hard+high item runs K self-refine passes and ships. With the guard, it runs the
independent check. The avoided passes are K (the loop's configured pass budget) minus the one
pass already spent producing the self-critique. The runner sets refine_passes_avoided.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Guard verdict strings (kept local so metrics has no hard import of the guard module; the
# runner passes the verdict strings through verbatim).
REQUIRE_INDEPENDENT_CHECK = "REQUIRE_INDEPENDENT_CHECK"
ESCALATE = "ESCALATE"
ALLOW = "ALLOW"


def detection_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detection lift and false-positive rate on the governed items.

    Operates over ALL governed records (the runner already filtered to hard+high). The
    independent verdict may be None on records where the independent arm was not run; those are
    excluded from the independent-side counts and reported separately.
    """
    self_passed = [r for r in records if r["self_passed"]]
    self_passed_wrong = [r for r in self_passed if not r["correct"]]

    # independent-side counts on the self-passed-wrong slice (the danger set)
    indep_run = [r for r in self_passed_wrong if r.get("indep_passed") is not None]
    independent_caught = sum(1 for r in indep_run if r["indep_passed"] is False)
    self_caught_in_slice = 0  # by construction: this slice is what self-critic PASSED

    detection_lift = independent_caught - self_caught_in_slice
    lift_rate = (independent_caught / len(indep_run)) if indep_run else None

    # false-positive rate on genuinely correct answers the independent arm reviewed
    correct_reviewed = [
        r for r in records if r["correct"] and r.get("indep_passed") is not None
    ]
    false_flags = sum(1 for r in correct_reviewed if r["indep_passed"] is False)
    fp_rate = (false_flags / len(correct_reviewed)) if correct_reviewed else None

    # for context: how many wrong answers did the self-critic let through in total
    total_wrong = [r for r in records if not r["correct"]]
    self_passed_wrong_n = len(self_passed_wrong)

    return {
        "n_governed": len(records),
        "n_wrong_total": len(total_wrong),
        "self_passed_n": len(self_passed),
        "self_passed_wrong_n": self_passed_wrong_n,
        "independent_reviewed_in_danger_slice": len(indep_run),
        "independent_caught_in_slice": independent_caught,
        "self_caught_in_slice": self_caught_in_slice,
        "detection_lift": detection_lift,
        "detection_lift_rate": _round(lift_rate),
        "correct_reviewed_by_independent": len(correct_reviewed),
        "independent_false_flags": false_flags,
        "independent_false_positive_rate": _round(fp_rate),
    }


def token_ledger(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Net token ledger: futile self-refine passes the guard stopped minus the check's cost."""
    fired = [r for r in records if r["guard_verdict"] in (REQUIRE_INDEPENDENT_CHECK, ESCALATE)]

    total_saved = 0
    total_spent = 0
    net_positive_items = 0
    net_negative_items = 0
    per_item = []
    for r in fired:
        saved = r["refine_passes_avoided"] * r["refine_pass_tokens"]
        spent = r["indep_tokens"]
        net = saved - spent
        total_saved += saved
        total_spent += spent
        if net > 0:
            net_positive_items += 1
        elif net < 0:
            net_negative_items += 1
        per_item.append({
            "item_id": r["item_id"], "saved": saved, "spent": spent, "net": net,
            "guard_verdict": r["guard_verdict"],
        })

    return {
        "items_guard_fired": len(fired),
        "tokens_saved_stopping_futile_passes": total_saved,
        "tokens_spent_on_independent_check": total_spent,
        "net_tokens": total_saved - total_spent,
        "net_positive_items": net_positive_items,
        "net_negative_items": net_negative_items,
        "per_item": per_item,
    }


def arm_accuracy(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Per-arm agreement with ground truth, for the summary table.

    For each arm, a verdict is 'right' when passed==correct (passed a correct answer or flagged
    a wrong one). NO_CHECK passes everything, so its accuracy equals the correct-answer rate.
    """
    n = len(records)
    correct_rate = sum(1 for r in records if r["correct"]) / n if n else None

    # self-critic
    self_right = sum(1 for r in records if r["self_passed"] == r["correct"])
    # independent (only where run)
    indep_recs = [r for r in records if r.get("indep_passed") is not None]
    indep_right = sum(1 for r in indep_recs if r["indep_passed"] == r["correct"])

    return {
        "no_check_accuracy": _round(correct_rate),
        "self_critic_accuracy": _round(self_right / n) if n else None,
        "independent_accuracy": _round(indep_right / len(indep_recs)) if indep_recs else None,
        "independent_n_reviewed": len(indep_recs),
    }


def summarize(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Bundle the three metric blocks for the results file."""
    return {
        "detection": detection_metrics(records),
        "token_ledger": token_ledger(records),
        "arm_accuracy": arm_accuracy(records),
    }


def _round(x: Any, ndigits: int = 4) -> Any:
    return round(x, ndigits) if isinstance(x, float) else x
