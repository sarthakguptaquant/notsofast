"""Run the Not So Fast benchmark.

Pipeline, per governed (hard-correctness + high-materiality) item:

  1. The reasoner has produced a candidate answer (the dataset carries it). A same-context
     SELF_CRITIC reviews it and either passes ("looks correct") or flags it.
  2. The SHIPPED guard (`notsofast.review`) is consulted on the decision's tags. On these
     items it fires (REQUIRE_INDEPENDENT_CHECK, or ESCALATE when no check is available),
     because the regime is exactly the one the rule governs. When it fires, the loop stops
     burning futile self-refine passes and runs an INDEPENDENT (isolated-context) check.
  3. Ground truth (the dataset's checker) labels whether the candidate was actually correct.
  4. Metrics compare the self-critic and the independent check against ground truth, and tally
     the token ledger.

This measures the SHIPPED policy: step 2 calls the real `review()` from the package, not a
reimplementation. Swap the mock arms for real ones (--real, see arms/real_adapter.py) and the
same pipeline produces real numbers.

Determinism: a single --seed drives the mock arms; the dataset is fixed; the guard is pure. Two
runs with the same seed produce byte-identical records (modulo the timestamp in the run id,
which is recorded but not used in any computation).

Usage:
  python run.py                      # mock pilot, default seed, writes results/
  python run.py --seed 7             # different seed
  python run.py --json-only          # suppress the human table
  python run.py --real               # real arms; requires a wired model_call (raises if absent)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# Import the SHIPPED guard. It lives at skills/notsofast/scripts/notsofast.py and is also the
# pip module `notsofast`. Try the installed module first, then fall back to the in-repo path so
# the benchmark runs from a fresh clone without an install step.
try:
    from notsofast import Decision, review, REQUIRE_INDEPENDENT_CHECK, ESCALATE, ALLOW  # type: ignore
except ImportError:
    sys.path.insert(0, os.path.join(REPO, "skills", "notsofast", "scripts"))
    from notsofast import Decision, review, REQUIRE_INDEPENDENT_CHECK, ESCALATE, ALLOW  # type: ignore

sys.path.insert(0, HERE)
from dataset import GOVERNED_ITEMS, ALL_ITEMS, dataset_stats  # noqa: E402
from dataset.items import Item  # noqa: E402
from arms import VerificationInput, build_mock_arms, build_real_arms  # noqa: E402
import metrics as M  # noqa: E402

DEFAULT_SEED = 20260626

# How many self-refine passes a NAIVE loop would run on a hard answer before shipping, and the
# token cost of one such pass. These are the ledger's "what the guard avoids" constants. They
# mirror the companion study's constants so the two are comparable, and they are explicit so a
# reviewer can change them and re-run. The first pass (producing the initial self-critique) is
# already spent, so the guard avoids (K - 1) of them when it stops the loop.
NAIVE_REFINE_PASSES = 5
REFINE_PASS_TOKENS = 800


def _synthetic_reasoning(item: Item) -> str:
    """A stand-in reasoning trace the SELF_CRITIC arm is allowed to see and the INDEPENDENT arm
    is not. In a real run this is the reasoner's actual chain of thought. Here it is the item's
    own rationale text, which is enough to exercise the context-access difference between the
    arms. It is never shown to the independent arm (arms/base.isolate strips it).
    """
    return f"My working for '{item.id}': {item.rationale}"


def run_item(item: Item, arms: Dict[str, Any]) -> Dict[str, Any]:
    """Run one governed item through the arms and the shipped guard; return a metrics record."""
    vin = VerificationInput(
        task=item.task,
        candidate=item.candidate,
        item_id=item.id,
        reasoning_trace=_synthetic_reasoning(item),
    )

    # 1. self-critic reviews its own work (shared context)
    self_v = arms["self_critic"].verify(vin)

    # 2. the shipped guard decides whether self-critique may stand
    decision = Decision(
        verification_mode=item.verification_mode,
        task_type=item.task_type,
        materiality=item.materiality,
        has_independent_check=False,           # the loop closed on self-critique
        independent_check_available=True,      # a check can be added for these items
    )
    verdict = review(decision)

    # 3. if the guard fires, stop futile self-refine passes and run the independent check
    indep_v = None
    refine_passes_avoided = 0
    if verdict in (REQUIRE_INDEPENDENT_CHECK, ESCALATE):
        refine_passes_avoided = max(NAIVE_REFINE_PASSES - 1, 0)  # first pass already spent
        if verdict == REQUIRE_INDEPENDENT_CHECK:
            indep_v = arms["independent"].verify(vin)
        else:
            # ESCALATE: no independent check available -> handed to a human. None of the
            # benchmark items are unavailable, so this branch is not exercised by the default
            # dataset; it is here so the path is covered when an item sets it.
            indep_v = None

    return {
        "item_id": item.id,
        "correct": item.correct,
        "guard_verdict": verdict,
        "self_passed": self_v.passed,
        "self_tokens": self_v.tokens,
        "indep_passed": (indep_v.passed if indep_v is not None else None),
        "indep_tokens": (indep_v.tokens if indep_v is not None else 0),
        "refine_passes_avoided": refine_passes_avoided,
        "refine_pass_tokens": REFINE_PASS_TOKENS,
        "self_note": self_v.note,
        "indep_note": (indep_v.note if indep_v is not None else None),
    }


def build_arms(seed: int, real: bool, model_call: Optional[Callable] = None) -> Dict[str, Any]:
    if real:
        return build_real_arms(model_call=model_call)
    # the mock independent arm needs a truth oracle (a SIMULATION KNOB, see arms/mock.py).
    truth = {it.id: it.correct for it in ALL_ITEMS}
    return build_mock_arms(seed=seed, truth_oracle=lambda iid: truth[iid])


def make_run_id(seed: int, real: bool) -> str:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    mode = "real" if real else "mock"
    return f"nsf-bench-{mode}-seed{seed}-{stamp}"


def run(seed: int = DEFAULT_SEED, real: bool = False,
        model_call: Optional[Callable] = None) -> Dict[str, Any]:
    arms = build_arms(seed=seed, real=real, model_call=model_call)
    records = [run_item(it, arms) for it in GOVERNED_ITEMS]
    summary = M.summarize(records)
    return {
        "run_id": make_run_id(seed, real),
        "mode": "real" if real else "mock",
        "seed": seed,
        "dataset": dataset_stats(),
        "constants": {
            "NAIVE_REFINE_PASSES": NAIVE_REFINE_PASSES,
            "REFINE_PASS_TOKENS": REFINE_PASS_TOKENS,
        },
        "metrics": summary,
        "records": records,
        "disclaimer": (
            "MOCK MODE validates the harness mechanics end to end (dataset -> arms -> shipped "
            "guard -> metrics -> ledger). It does NOT establish the central claim: the mock "
            "independent arm's detection is a seeded, truth-correlated simulation, not a model "
            "re-deriving the answer. Run with --real and a wired model_call for the real "
            "result. The self-critic and no-check arms are honest in both modes."
            if not real else
            "REAL MODE: detection and tokens come from live model calls via the wired "
            "model_call. Numbers are a measured result for the model and dataset used."
        ),
    }


def print_human(result: Dict[str, Any]) -> None:
    d = result["metrics"]["detection"]
    led = result["metrics"]["token_ledger"]
    acc = result["metrics"]["arm_accuracy"]
    ds = result["dataset"]

    print(f"run_id: {result['run_id']}  (mode={result['mode']}, seed={result['seed']})")
    print(f"dataset: {ds['n_governed']} governed items "
          f"({ds['n_governed_correct']} correct, {ds['n_governed_wrong']} wrong), "
          f"{ds['n_controls']} controls, lanes={ds['lanes']}")
    print()
    print("DETECTION LIFT (on the slice the self-critic waved through):")
    print(f"  self-critic passed                : {d['self_passed_n']} items")
    print(f"  ... of which actually WRONG       : {d['self_passed_wrong_n']}  <- the danger set")
    print(f"  independent caught in that slice  : {d['independent_caught_in_slice']}")
    print(f"  self caught in that slice         : {d['self_caught_in_slice']} (0 by construction)")
    print(f"  detection lift                    : {d['detection_lift']} "
          f"(independent - self on the self-passed slice)")
    print(f"  detection lift rate (recall)      : {d['detection_lift_rate']}")
    print()
    print("FALSE-POSITIVE COST (flagging genuinely-correct answers):")
    print(f"  correct answers independent saw   : {d['correct_reviewed_by_independent']}")
    print(f"  ... falsely flagged               : {d['independent_false_flags']}")
    print(f"  independent false-positive rate   : {d['independent_false_positive_rate']}")
    print()
    print("ARM ACCURACY vs ground truth (governed slice):")
    print(f"  no_check (ship everything)        : {acc['no_check_accuracy']}")
    print(f"  self_critic                       : {acc['self_critic_accuracy']}")
    print(f"  independent                       : {acc['independent_accuracy']} "
          f"(n={acc['independent_n_reviewed']})")
    print()
    print("NET TOKEN LEDGER (futile passes stopped minus check cost):")
    print(f"  items the guard fired on          : {led['items_guard_fired']}")
    print(f"  tokens saved (futile passes)      : {led['tokens_saved_stopping_futile_passes']:,}")
    print(f"  tokens spent (independent checks) : {led['tokens_spent_on_independent_check']:,}")
    print(f"  NET                               : {led['net_tokens']:,}")
    print(f"  net-positive items / net-negative : {led['net_positive_items']} / "
          f"{led['net_negative_items']}")
    print()
    print(result["disclaimer"])


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Run the Not So Fast benchmark.")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--real", action="store_true",
                    help="use real model arms (requires a wired model_call; raises if absent)")
    ap.add_argument("--json-only", action="store_true", help="suppress the human-readable table")
    ap.add_argument("--out", default=None, help="path for the JSON results file")
    args = ap.parse_args(argv)

    result = run(seed=args.seed, real=args.real)

    # The default committed artifact is a STABLE file whose run_id carries no timestamp, so
    # re-running the pilot does not churn git (the metrics are deterministic per seed; only a
    # wall-clock id would change). Pass --out to write a uniquely-stamped file instead.
    if args.out:
        out_path = args.out
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as fh:
            json.dump(result, fh, indent=2, default=str)
    elif not args.real:
        stable = dict(result)
        stable["run_id"] = f"nsf-bench-mock-seed{args.seed}"  # deterministic, no timestamp
        stable["note"] = ("Stable committed pilot. run_id is timestamp-free so re-running does "
                          "not churn git; metrics are deterministic per seed. Use --out for a "
                          "stamped run.")
        out_path = os.path.join(HERE, "results", "pilot-mock-latest.json")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as fh:
            json.dump(stable, fh, indent=2, default=str)
    else:
        out_path = os.path.join(HERE, "results", f"{result['run_id']}.json")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as fh:
            json.dump(result, fh, indent=2, default=str)

    if not args.json_only:
        print_human(result)
        print(f"\nwrote {os.path.relpath(out_path, REPO)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
