"""Case study: what does verification actually cost, once you count the rework?

THE PERSPECTIVE. The interesting number is not "how many tokens does this check cost."
It is "how many tokens does the whole work structure cost," because a wrong consequential
decision that ships does not cost nothing. It triggers a rework cycle: detection,
re-investigation, re-run, correction, sign-off. That rework is real tokens (and real
money). So:

    total cost = tokens spent verifying + tokens lost to rework on wrong decisions

Under that accounting, verification stops looking like a cost line and starts looking like
what it is: the cheap insurance that avoids the expensive rework. This study quantifies
that, honestly.

WHAT THIS IS / IS NOT. A transparent, fully seeded model. It calls the real
`third_umpire.review()` to do the routing, so the policy under test is the shipped guard.
Token costs and the rework cost are explicit constants. The accuracy dynamics are
calibrated to one published finding, not measured from live model runs:

  Huang et al., "LLMs Cannot Self-Correct Reasoning Yet," ICLR 2024 (arXiv:2310.01798):
  intrinsic self-correction does not reliably improve hard-correctness answers and can
  degrade them.

This is not a live-LLM benchmark and does not pretend to be. A live replication (swap the
accuracy/token/rework oracles for metered calls and a logged rework tally) is the next
step; the harness is built so they drop in cleanly.

EXPERIMENTAL DESIGN. To isolate exactly what the guard changes, soft (open-ended) tasks are
handled IDENTICALLY by every policy: self-refine helps there, so every policy self-refines
them the same way. The policies differ ONLY on hard-correctness decisions, which is the
only thing the guard governs. So every token of difference below is attributable to the
hard-task routing, nothing else.

Run: python run_study.py            (prints tables; writes study_results.json)
     python run_study.py --plot     (also writes the charts, needs matplotlib)
"""

from __future__ import annotations

import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from third_umpire import Decision, review  # noqa: E402

SEED = 20260617

# --- ASSUMPTIONS (all explicit; vary and re-run) --------------------------------------
GEN = 600            # initial answer
REFINE_PASS = 800    # one self-refine round (self-critique + revised answer)
INDEP_CHECK = 700    # one independent check (cross-model / held-out / tool verifier)
HUMAN_HANDOFF = 200  # tokens to package an escalation for a human
# Rework: tokens burned cleaning up ONE wrong hard+high decision that shipped. A full
# correction cycle is several passes plus a human loop, so it dwarfs a single check.
REWORK_HARD_HIGH = 9000

P0 = {"hard_correctness": 0.55, "soft": 0.75}   # single-pass base correctness
SOFT_REFINE_GAIN = 0.80      # soft: each self-refine pass multiplies the error (helps)
HARD_REFINE_DRIFT = 0.015    # hard: each self-refine pass mildly degrades (Huang 2024)
CHECK_CATCH = 0.60           # independent check catches this fraction of remaining errors
HUMAN_CATCH = 0.90           # a human catches more, used on ESCALATE
K_REFINE = 4                 # passes the naive self-refine loop uses
K_SOFT = 2                   # passes every policy uses on soft tasks (held constant)

POP_MIX = {
    ("soft", "low"): 0.35,
    ("soft", "high"): 0.15,
    ("hard_correctness", "low"): 0.20,
    ("hard_correctness", "high"): 0.30,
}
N = 1000
CHECK_AVAILABLE_RATE = 0.85   # for hard+high, a check can be added 85% of the time


def acc_self_refine(task, k):
    p0 = P0[task]
    if task == "soft":
        return 1.0 - (1.0 - p0) * (SOFT_REFINE_GAIN ** k)
    return max(p0 - HARD_REFINE_DRIFT * k, p0 - 0.06)


def after_check(acc):
    return 1.0 - (1.0 - acc) * (1.0 - CHECK_CATCH)


def after_human(acc):
    return 1.0 - (1.0 - acc) * (1.0 - HUMAN_CATCH)


def build_population(rng):
    keys, weights = zip(*POP_MIX.items())
    pop = []
    for _ in range(N):
        task, matl = rng.choices(keys, weights=weights, k=1)[0]
        pop.append({"task": task, "matl": matl, "avail": rng.random() < CHECK_AVAILABLE_RATE})
    return pop


# Soft tasks: handled identically by every policy (returns verification tokens, accuracy).
def soft_pipeline():
    return GEN + K_SOFT * REFINE_PASS, acc_self_refine("soft", K_SOFT)


# --- Hard-task handling per policy. Returns (verification_tokens, accuracy). -----------
def hard_ship(d):
    """No validation: ship the single self-critique pass."""
    return GEN, acc_self_refine("hard_correctness", 0)


def hard_refine_k(d, k=K_REFINE):
    """Naive intrinsic self-correction: K self-refine passes (futile on hard tasks)."""
    return GEN + k * REFINE_PASS, acc_self_refine("hard_correctness", k)


def hard_validate_all(d):
    """Independent check on every hard decision, regardless of materiality."""
    return GEN + INDEP_CHECK, after_check(acc_self_refine("hard_correctness", 0))


def hard_third_umpire(d):
    """Route through the real guard. Skip futile refine on hard+low (reversible, cheap);
    check hard+high where the rule fires; escalate when no check can be added."""
    verdict = review(Decision("self", "hard_correctness", d["matl"], False, d["avail"]))
    base = acc_self_refine("hard_correctness", 0)
    if verdict == "ALLOW":            # hard + low materiality: let the single pass stand
        return GEN, base
    if verdict == "REQUIRE_INDEPENDENT_CHECK":
        return GEN + INDEP_CHECK, after_check(base)
    return GEN + HUMAN_HANDOFF, after_human(base)   # ESCALATE


POLICIES = {
    "ship (no validation)": hard_ship,
    "naive self-refine (K=%d)" % K_REFINE: hard_refine_k,
    "validate everything": hard_validate_all,
    "third-umpire (routed)": hard_third_umpire,
}


def evaluate(pop, hard_fn, rework=REWORK_HARD_HIGH):
    verify = 0
    rework_tokens = 0.0
    hh_accs = []
    for d in pop:
        if d["task"] == "soft":
            v, _ = soft_pipeline()           # identical across policies
            verify += v
            continue
        v, acc = hard_fn(d)
        verify += v
        if d["matl"] == "high":              # only consequential errors trigger rework
            hh_accs.append(acc)
            rework_tokens += (1.0 - acc) * rework
    total = verify + rework_tokens
    return {
        "verify_tokens": verify,
        "rework_tokens": round(rework_tokens),
        "total_tokens": round(total),
        "acc_hard_high": sum(hh_accs) / len(hh_accs) if hh_accs else None,
        "wrong_hard_high": round(sum(1 - a for a in hh_accs), 1),
    }


def main():
    rng = random.Random(SEED)
    pop = build_population(rng)
    results = {name: evaluate(pop, fn) for name, fn in POLICIES.items()}

    print("Population N=%d, mix=%s, seed=%d, rework/wrong-hard-high=%d tokens\n"
          % (N, dict(POP_MIX), SEED, REWORK_HARD_HIGH))
    print("%-26s %12s %12s %12s %10s" %
          ("policy", "verify", "rework", "TOTAL", "acc_hh"))
    for name, r in results.items():
        print("%-26s %12d %12d %12d %10.3f" %
              (name, r["verify_tokens"], r["rework_tokens"], r["total_tokens"], r["acc_hard_high"]))

    tu = results["third-umpire (routed)"]
    print("\nNet savings on the whole work structure (verify + rework), vs each status quo:")
    for name, r in results.items():
        if name.startswith("third-umpire"):
            continue
        saved = r["total_tokens"] - tu["total_tokens"]
        pct = 100 * saved / r["total_tokens"]
        print("  vs %-26s third-umpire spends %d fewer total tokens (%.0f%% less)."
              % (name + ":", saved, pct))

    # Break-even: how cheap would rework have to be for "ship nothing" to beat the guard?
    ship = "ship (no validation)"
    lo, hi = 0.0, 50000.0
    for _ in range(40):
        mid = (lo + hi) / 2
        a = evaluate(pop, POLICIES[ship], rework=mid)["total_tokens"]
        b = evaluate(pop, hard_third_umpire, rework=mid)["total_tokens"]
        if a > b:
            hi = mid
        else:
            lo = mid
    print("\nBreak-even: once a wrong consequential decision costs more than ~%d tokens to "
          "fix, routing the check beats shipping nothing. Below that, skipping validation is "
          "cheaper. Real rework cycles run far above this." % round((lo + hi) / 2))

    out = {"assumptions": {k: v for k, v in globals().items()
                           if k.isupper() and isinstance(v, (int, float, dict))},
           "results": results,
           "disclaimer": "Transparent simulation calibrated to Huang et al. 2024; not a "
                         "live-LLM benchmark. third_umpire.review() does the actual routing. "
                         "Soft tasks handled identically across policies to isolate the guard."}
    out["assumptions"]["POP_MIX"] = {str(k): v for k, v in POP_MIX.items()}
    with open(os.path.join(os.path.dirname(__file__), "study_results.json"), "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    print("\nwrote study_results.json")

    if "--plot" in sys.argv:
        make_charts(results)


def make_charts(results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    INK, BLUE, GREEN, CREAM = "#0F0E0B", "#1B3DFF", "#00B870", "#F4F1E8"
    names = list(results.keys())
    short = ["ship\n(no check)", "naive\nself-refine", "validate\neverything", "third-umpire\n(routed)"]
    verify = [results[n]["verify_tokens"] / 1e6 for n in names]
    rework = [results[n]["rework_tokens"] / 1e6 for n in names]
    totals = [results[n]["total_tokens"] / 1e6 for n in names]

    # Chart 1: the money chart. Stacked bar, check cost vs rework cost.
    fig, ax = plt.subplots(figsize=(7.6, 4.8), dpi=160)
    fig.patch.set_facecolor(CREAM); ax.set_facecolor(CREAM)
    bars_v = ax.bar(short, verify, color=BLUE, label="tokens spent checking")
    bars_r = ax.bar(short, rework, bottom=verify, color=INK, alpha=0.78,
                    label="tokens lost to rework (wrong decisions that shipped)")
    # highlight the winner
    idx = names.index("third-umpire (routed)")
    bars_v[idx].set_color(GREEN)
    for i, t in enumerate(totals):
        ax.text(i, t + 0.05, "%.1fM" % t, ha="center", va="bottom",
                color=INK, fontsize=11, fontweight="bold")
    ax.set_ylabel("total tokens (millions)")
    ax.set_title("What the work actually costs: the check vs the mistake", color=INK)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.grid(True, axis="y", color=BLUE, alpha=0.12)
    ax.set_ylim(0, max(totals) * 1.18)
    fig.tight_layout()
    fig.savefig(os.path.join(os.path.dirname(__file__), "savings_bars.png"))
    plt.close(fig)

    # Chart 2: cost vs accuracy frontier (total cost now, not just verify).
    fig, ax = plt.subplots(figsize=(7.2, 4.6), dpi=160)
    fig.patch.set_facecolor(CREAM); ax.set_facecolor(CREAM)
    colors = [INK, INK, BLUE, GREEN]
    markers = ["x", "o", "o", "*"]
    sizes = [80, 80, 90, 200]
    for n, c, m, s, lbl in zip(names, colors, markers, sizes, short):
        ax.scatter(results[n]["total_tokens"] / 1e6, results[n]["acc_hard_high"],
                   color=c, marker=m, s=s, zorder=5,
                   alpha=0.6 if c == INK else 1.0)
        ax.annotate(lbl.replace("\n", " "), (results[n]["total_tokens"] / 1e6, results[n]["acc_hard_high"]),
                    textcoords="offset points", xytext=(8, 6), fontsize=8, color=INK)
    ax.set_xlabel("total token cost incl. rework (millions, lower is better)")
    ax.set_ylabel("accuracy on the decisions that matter")
    ax.set_title("Cheaper and more accurate, at the same time", color=INK)
    ax.grid(True, color=BLUE, alpha=0.12)
    fig.tight_layout()
    fig.savefig(os.path.join(os.path.dirname(__file__), "frontier.png"))
    plt.close(fig)
    print("wrote savings_bars.png and frontier.png")


if __name__ == "__main__":
    main()
