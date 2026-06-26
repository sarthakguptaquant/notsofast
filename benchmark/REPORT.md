# The Not So Fast benchmark: detection lift and the net-token ledger

This is the empirical harness for the one claim Not So Fast makes:

> A `self`-only critic is not an adequate sole gate on a `hard_correctness`, `high`-materiality
> decision. On those decisions, require an INDEPENDENT check (a verifier with no access to the
> original chain of reasoning), and stop futile self-refine passes.

The repository ships a deterministic guard and a conformance suite, but until now no measurement
that the gate catches errors a self-critic misses, or that it spends tokens it is worth. A fair
critique put it plainly: a seeded simulation cannot show either, so the claim is an assertion,
not a result. This harness is built to turn it into a result. It does not yet contain the
result, and it says so in the same breath: the numbers below come from a deterministic MOCK that
validates the plumbing. The real numbers arrive when a model is wired into one function. The
point of shipping the harness first is that the real run is then a one-line plug-in, run on a
dataset whose ground truth is arithmetic, not opinion.

## What is claimed, precisely

Two measurable quantities, both on the slice of decisions the guard governs (hard-correctness,
high-materiality, closed by self-critique):

1. **Detection lift.** Among candidates the same-context self-critic waved through ("looks
   correct"), how many does an isolated-context independent check catch as wrong?
   `detection_lift = independent_caught - self_caught`, evaluated on the self-passed slice
   (where `self_caught` is 0 by construction). Reported alongside the independent check's
   **false-positive rate** on genuinely-correct answers, because flagging good work is a real
   cost and a lift number is meaningless without it.

2. **Net token ledger.** When the guard fires, it stops a naive self-refine loop from burning
   futile passes on a hard answer it cannot fix, and spends one independent check instead.
   `net = tokens_saved_on_stopped_passes - tokens_spent_on_the_check`, summed across governed
   items, split into where the guard is net-positive and where it is net-negative. No blanket
   savings are promised. The README is careful here, and so is this.

## How it is tested, and why the test is fair

### The dataset is checkable, not judged

`benchmark/dataset/` holds 46 governed decision items (plus 2 soft/low negative controls)
across two lanes: finance and quant (put-call parity, VaR aggregation across correlated books,
amortization, time-value, P&L and balance-sheet reconciliation, dimensional consistency,
allocation and limit constraints, expected loss, Sharpe, zero-coupon pricing) and general code
correctness (binary search boundaries, percent-change denominators, compound-vs-simple growth,
clamp logic, SQL filter boundaries, FizzBuzz precedence, mean-vs-sample-variance). It is not
domain-locked.

Each item carries a candidate answer that is either exactly correct or wrong by a single, named,
realistic error. Ground truth is decided by a CHECKER: a pure Python function that re-derives
the right answer from the task's inputs (the parity formula, the correlated-VaR formula, the
annuity payment, a sum, an executed function against a fixed input/output table) and compares.
The checker never asks a model. That is the property that keeps the benchmark from being
circular: correctness is settled by computation, so an arm cannot be graded against another
model's possibly-wrong opinion.

The wrong candidates are constructed to be PLAUSIBLE, not broken. A dropped discount factor in a
put price. A naive `v1 + v2` VaR that ignores correlation. An annual rate used as a monthly rate.
An inclusive boundary written exclusive. An off-by-one loop bound that passes most test cases.
These are the errors a same-context self-critic rationalizes, because the critic shares the
reasoning that produced them. None is a typo or an out-of-range value a parser would reject. The
correct candidates are the exact right answer to the same prompt. The split is balanced (24
correct, 22 wrong) so no arm can win by always guessing one label.

The dataset verifies itself at import time: `items.self_check()` runs every checker against
every stored label and raises if any disagree. A bad candidate or a stale label fails loudly
before it can reach the metrics. During construction this gate caught three of my own arithmetic
slips. That is the gate working, not a flaw.

### The three arms, and the isolation that is the whole point

`benchmark/arms/` defines three verification arms behind one interface:

- **NO_CHECK** ships the candidate unverified. It establishes the baseline error rate.
- **SELF_CRITIC** has the same reasoner review its own answer WITH full prior context: the task,
  its own recorded reasoning. This is the cheap, common mode the critique is about.
- **INDEPENDENT** has a verifier evaluate the answer in a FRESH context with NO access to the
  original chain of reasoning. It re-derives or re-checks from the task alone.

The independent arm's isolation is structural, not a promise in a comment. `arms/base.isolate`
takes the verification input and returns a new frozen object with the `reasoning_trace` field
set to `None`. The independent arm calls `isolate` and then asserts the trace is gone before it
builds its prompt. The data class is frozen, so the arm cannot mutate its way back to the trace,
and the field is physically absent, so there is nothing to peek at. In the real adapter, this
means the independent verifier model literally never receives the original reasoning in its
context window. The ONLY difference between the self-critic and independent arms is context
access: same task, same candidate, one sees the prior reasoning, one does not. That is the
single variable the benchmark isolates.

### Mock now, real with one function

Each arm has two backends. The MOCK backend (`arms/mock.py`) is seeded and deterministic, with
no network, so the whole pipeline is testable in CI. The REAL backend (`arms/real_adapter.py`)
wraps a single user-supplied function:

```python
def model_call(prompt: str) -> ModelResponse:   # ModelResponse(text, tokens)
    ...
```

No provider is hardcoded, no API key is read, and nothing calls a paid API by default. You wire
`model_call` to the model of your choice, and the self-critic and independent arms become real
verification arms. The same runner, the same metrics, the same ledger produce real numbers. The
adapter is a documented, typed stub that raises a clear error until you implement it.

### The runner measures the SHIPPED policy

`benchmark/run.py` does not reimplement the routing. It imports `review` from the shipped
`notsofast` module and consults it on each item's tags. On the governed items it fires
(`REQUIRE_INDEPENDENT_CHECK`), which is what triggers the independent arm and the stopping of
futile passes. So every token and every catch is attributed to the policy the repo actually
ships, not to a model of it.

## The methods section IS the ledger design

The token ledger rests on three explicit constants, all in `run.py` and mirrored in the
companion study so the two are comparable:

- `NAIVE_REFINE_PASSES = 5`: how many self-refine passes a naive loop would run on a hard answer
  before shipping.
- `REFINE_PASS_TOKENS = 800`: the token cost of one such pass.
- The independent check costs `INDEPENDENT_TOKENS = 700` in the mock; in a real run it is the
  metered token count of the check call.

When the guard fires, the first self-refine pass (the one that produced the self-critique) is
already spent, so the guard avoids `NAIVE_REFINE_PASSES - 1 = 4` passes and spends one check:

```
tokens_saved = refine_passes_avoided * REFINE_PASS_TOKENS   # 4 * 800 = 3200 per item
tokens_spent = indep_tokens                                 # 700 per item (mock)
net          = tokens_saved - tokens_spent                  # +2500 per item, here
```

This is net-positive only while the avoided passes outweigh the check. If a loop runs few
refine passes, or the independent check is expensive (a large reasoning model, a tool with a
real cost), the ledger goes negative. The harness reports both directions, and the metrics test
explicitly proves a negative ledger is reachable (`test_ledger_can_go_negative`). The honest
framing is: the guard converts spend on futile self-refinement into spend on a check that can
actually catch the error, and whether that is a saving depends on how many passes your loop
would otherwise burn.

The detection side uses no token assumptions at all. It is a count of catches and false flags on
labeled items, so it transfers directly from mock to real with no constant to argue about.

## What the mock pilot shows (mechanics, not the claim)

Committed at `benchmark/results/pilot-mock-latest.json`, run id `nsf-bench-mock-seed20260626`.
Reproduce: `python benchmark/run.py`.

```
DETECTION LIFT (on the slice the self-critic waved through):
  self-critic passed                : 37 items
  ... of which actually WRONG       : 18   <- the danger set
  independent caught in that slice  : 15
  detection lift                    : 15
  detection lift rate (recall)      : 0.8333

FALSE-POSITIVE COST (flagging genuinely-correct answers):
  correct answers independent saw   : 24
  ... falsely flagged               : 3
  independent false-positive rate   : 0.125

ARM ACCURACY vs ground truth (governed slice):
  no_check (ship everything)        : 0.5217
  self_critic                       : 0.5000
  independent                       : 0.8261

NET TOKEN LEDGER (futile passes stopped minus check cost):
  items the guard fired on          : 46
  tokens saved (futile passes)      : 147,200
  tokens spent (independent checks) : 32,200
  NET                               : 115,000  (46 net-positive, 0 net-negative)
```

Read this for what it is. These numbers are a function of the mock's stated knobs (a self-critic
that passes about 86 percent of items roughly independent of correctness, an independent checker
modeled as catching 78 percent of wrongs and false-flagging 8 percent of corrects, both seeded).
They do NOT show that an independent model beats a self-critic. They show that IF the two arms
behave the way the literature describes, the pipeline measures the right quantities, routes
through the real guard, balances the ledger, and is deterministic per seed. The mock independent
arm is given a truth oracle as a simulation knob, and the report labels that everywhere; the
real adapter replaces the oracle with a live model call and changes nothing else. The mock proves
the mechanics. The claim waits on the real run.

The self-critic's accuracy (0.50) sitting at the no-check baseline (0.52) is the mock encoding
the central finding: a self-critic that ratifies its own work adds essentially nothing on
hard-correctness items. The independent arm's edge (0.83) is what the real run must reproduce
against a live model to substantiate the claim.

## How to do a real run

1. Implement `model_call(prompt) -> ModelResponse(text, tokens)` against your model. Keep the
   temperature at 0 if you want the run to replay. Return the real total token count so the
   ledger is metered.
2. Wire it into `arms/real_adapter.build_real_arms`, or extend `run.py` to pass it through
   `--real`. The harness raises a clear `NotImplementedError` if `--real` is used without it.
3. Run `python benchmark/run.py --real`. The output is the same shape as the pilot, with
   detection lift, false-positive rate, arm accuracy, and the token ledger computed from live
   verdicts and metered tokens.

The same dataset, the same checkers, the same shipped guard, the same metrics. Only the arms'
backend changes.

## What would FALSIFY the claim

This is the part that makes the benchmark worth running. The claim is falsifiable, and here is
exactly how a real run could refute it:

- **If the independent check does not beat the self-critic on the self-passed slice** (detection
  lift at or near zero), the central claim fails on this data. An independent verifier that
  catches no more of the self-critic's missed errors than the self-critic itself is no
  improvement, and Not So Fast would be demanding a check that buys nothing. The harness reports
  the lift without spin; if it is zero, that is the headline.
- **If the independent check's false-positive rate is high enough to swamp the lift** (it flags
  so many correct answers that the rework from false alarms costs more than the errors it
  catches), the gate is net-harmful even when it detects, and the two numbers reported together
  will show it.
- **If the token ledger is net-negative across realistic loops** (the check routinely costs more
  than the futile passes it stops), the token argument fails, and the harness already proves
  that regime is reachable.

Any of these would be a real, publishable negative result. None is assumed away. The benchmark is
designed so that the data, not the author, decides.

## Honest weaknesses a reviewer should flag

- **The mock independent arm uses a truth oracle.** It must, to model noisy-but-truth-correlated
  detection without a model. This makes the mock detection number an artifact of its knobs, which
  is why every mock claim here is labeled mechanics-only. The real run removes the oracle. A
  reviewer should not read any mock detection number as evidence for the claim, and the report
  does not ask them to.
- **The dataset is small (46 governed items) and authored, not sampled.** It is large enough to
  exercise the pipeline and varied enough to span two lanes, but a real result on it carries the
  usual small-sample caveats, and the items are ones I wrote, so they reflect my sense of what a
  plausible error looks like. Growing it and drawing items from an external corpus would
  strengthen it.
- **Materiality and task-hardness are tagged by construction.** Every governed item is hard+high
  by design, because that is the regime the guard governs. The benchmark therefore measures the
  gate's behavior INSIDE its target regime; it does not test the classifier that decides whether
  a real decision belongs in that regime. That classifier is a separate, harder problem the
  contract addresses with a conservative default, not measured here.
- **The token constants are stipulated, not measured, in the mock.** The real run meters them.
  Until then, the ledger's magnitude is illustrative; only its sign logic (and the proof it can
  flip) is load-bearing.
- **A single model wired into both arms shares a training distribution.** Even with isolated
  context, an independent check by the same model family may inherit some systematic errors. The
  cleanest real run uses a different model for the independent arm; the adapter allows it (wire a
  different `model_call`), and a reviewer should expect that to be reported when claimed.

Authored in a personal, industry-level capacity using public sources. No employer data, internal
figures, or system names appear in this benchmark or its code. All dataset values are synthetic.
