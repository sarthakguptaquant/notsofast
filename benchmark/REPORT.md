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

## The first real run

`model_call` is now wired (`benchmark/arms/cli_adapter.py`) to the LOCAL Claude CLI already
authenticated on this machine (subscription session, no API key read, no paid API, no account
created). Both the self-critic and independent arms use the same model, **haiku**
(`claude-haiku-4-5-20251001`), called through `claude -p --model haiku --output-format json`
with a minimal `--system-prompt` that carries no project context, from a neutral scratch working
directory so no CLAUDE.md leaks into the verification prompt. Each call is a fresh, session-less
invocation (no conversation state persists between calls), so the isolation the independent arm
depends on (`arms/base.isolate`) is real at the CLI-process level, not just the data-structure
level already enforced in code. A hard cap of 500 total CLI calls was set before the run; the
run used 92 (46 self-critic + 46 independent, one call per arm per governed item, since the
shipped guard fires on all 46 governed items in this dataset).

Committed at `benchmark/results/nsf-bench-real-seed20260626-20260708T025434Z.json`, run id
`nsf-bench-real-seed20260626-20260708T025434Z`, mode `real`. Reproduce with
`python benchmark/run_real_cli.py --model haiku --cap 500 --seed 20260626` (a thin driver script
that imports `run.py`'s `run()` directly and passes the wired `model_call` through, since
`run.py`'s own `--real` flag does not yet accept a provider argument by design; see that file's
docstring). Wiring status logged separately at `benchmark/results/real-cli-wiring-status.json`
(`SUCCESS`, 92/500 calls, 1102.7s elapsed). Every number below was re-derived by hand from
`records` in the results JSON and matched `metrics.py`'s output exactly before being written
here.

```
DETECTION LIFT (on the slice the self-critic waved through):
  self-critic passed                : 24 items
  ... of which actually WRONG       : 1   <- the danger set
  independent caught in that slice  : 1
  detection lift                    : 1
  detection lift rate               : 1.0   (n=1; see caveat below)

FALSE-POSITIVE COST (flagging genuinely-correct answers):
  correct answers independent saw   : 24
  ... falsely flagged               : 4
  independent false-positive rate   : 0.1667

ARM ACCURACY vs ground truth (governed slice, n=46):
  no_check (ship everything)        : 0.5217
  self_critic                       : 0.9565
  independent                       : 0.9130

NET TOKEN LEDGER (futile passes stopped minus check cost):
  items the guard fired on          : 46
  tokens saved (futile passes)      : 147,200   (unchanged: the naive-loop assumption, not measured)
  tokens spent (independent checks) : 988,840    (real, metered: ~21,500 tokens/call average)
  NET                               : -841,640   (46 net-negative, 0 net-positive)
```

**Read this for what it is, honestly, against the mock:**

- **The self-critic was far more accurate here than the mock assumed (0.9565 vs the mock's
  0.50).** Haiku, reviewing its own stated reasoning against these 46 finance/code arithmetic
  items, waved through only 1 of the 22 genuinely wrong candidates. This is a real, measured
  result on this dataset and this model, not a knob. It also means the self-passed "danger
  slice" the detection-lift metric is computed on shrank to just 1 item, because there was only
  1 wrong answer left for the self-critic to have missed. The independent arm caught that one
  item, so detection lift is 1/1 (100% recall) but on a single-item slice, which is not a
  statistically meaningful recall estimate. **The honest read is: on this run, hard evidence for
  a "self-critic misses errors an independent check catches" pattern is thin, because
  self-critique itself was strong.** A larger dataset, or a harder model/dataset pairing where
  self-critique is weaker, is needed before this claim is well-powered.
- **The independent arm's overall accuracy (0.9130) is LOWER than the self-critic's (0.9565) on
  this run.** This is the falsification case the section below names directly: an independent
  check that does not clearly beat self-critique is a real, reportable outcome, not something to
  paper over. The independent arm's 4 false positives on genuinely-correct answers (a 16.67%
  false-positive rate) account for the gap: it flagged correct amortization, future-value, and a
  dimensional-consistency item that self-critique had rightly passed. Inspecting the flagged
  responses shows real haiku reasoning errors (e.g. a future-value miscalculation on `fin-fv-01`
  used to justify a false FLAG), not a parsing artifact; the verdict parser (`_parse_verdict`) was
  independently checked against the raw model text and is behaving correctly.
- **The token ledger flips sign in the real run and goes sharply net-negative** (-841,640 vs the
  mock's illustrative +115,000). The `tokens_saved` side is unchanged (147,200: still the
  `NAIVE_REFINE_PASSES`/`REFINE_PASS_TOKENS` stipulated constants, not measured, exactly as
  REPORT.md's methods section says they are). The `tokens_spent` side is now real and metered,
  and it is roughly 30x the mock's assumed 700-tokens-per-check: each CLI invocation carries real
  cache-creation overhead (the harness/tool-schema context Claude Code loads per session, even
  with a stripped custom system prompt and no tools invoked) on top of the actual verification
  text. This is a genuine measured cost of THIS wiring choice (one `claude -p` process per call),
  not a property of "an independent check" in the abstract; a persistent-session or raw-API
  wiring would likely show a very different, much smaller per-call token cost. The ledger's sign
  logic worked exactly as designed (REPORT.md already proves a negative ledger is reachable); this
  run is a live instance of that regime, not a bug.
- **Lane split:** 31 finance items (16 correct / 15 wrong), 15 code items (8 correct / 7 wrong).
  The dataset is not domain-locked and this run exercised both lanes.

**What this run is, and is not.** It is one real measurement: one model (haiku), one dataset (46
items), one wiring choice (fresh per-call CLI subprocess), one seed. It is not the live-agent
study the notsofast paper (still PLAN-ONLY) would need, and it should not be read as settling
the central claim either way. What it demonstrates is that the harness's plumbing produces real,
internally-consistent, hand-verifiable numbers the moment a model is attached, exactly as
designed, and that on this first real attachment the self-critic outperformed the independent
check on raw accuracy while the token ledger went firmly negative. Both are reportable results,
and neither was true of the mock's assumed knobs.

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

**Against the first real run above: case 3 (net-negative token ledger) is directly hit** (-841,640
net, 46/46 items net-negative). Case 1 (detection lift near zero) is not cleanly resolved either
way; the danger slice was too small (n=1) on this run to call it, though the independent arm's
LOWER overall accuracy than self-critic is adjacent evidence against the claim on this run, not
for it. Case 2 (false positives swamping the lift) is arguably also in play: 4 false flags against
1 true catch is a 4:1 ratio in the wrong direction. **On its own, this first real run does not
support the central claim; a fair reading is closer to a partial falsification, pending a larger
dataset and a wiring choice with a lower per-call token floor.** This is reported without spin, per
the section above.

## Claims ledger (real run)

Every claim in "The first real run" section traces to this artifact and these keys, so a reviewer
can re-derive each number without re-running anything:

| Claim | Artifact | Key path |
|---|---|---|
| Wiring succeeded, 92/500 calls, 1102.7s | `results/real-cli-wiring-status.json` | `.wiring`, `.calls_made`, `.cap`, `.elapsed_s` |
| Model = haiku (claude-haiku-4-5-20251001) | CLI call construction | `arms/cli_adapter.py::make_cli_model_call` default; per-call model tag not persisted in results JSON (see weaknesses) |
| self_passed_n=24, self_passed_wrong_n=1 | `results/nsf-bench-real-seed20260626-20260708T025434Z.json` | `.metrics.detection.self_passed_n`, `.self_passed_wrong_n` |
| detection_lift=1, detection_lift_rate=1.0 | same file | `.metrics.detection.detection_lift`, `.detection_lift_rate` |
| independent_false_flags=4, fp_rate=0.1667 | same file | `.metrics.detection.independent_false_flags`, `.independent_false_positive_rate` |
| no_check/self_critic/independent accuracy = 0.5217 / 0.9565 / 0.9130 | same file | `.metrics.arm_accuracy.*` |
| tokens_saved=147200, tokens_spent=988840, net=-841640 | same file | `.metrics.token_ledger.tokens_saved_stopping_futile_passes`, `.tokens_spent_on_independent_check`, `.net_tokens` |
| net_negative_items=46, net_positive_items=0 | same file | `.metrics.token_ledger.net_negative_items`, `.net_positive_items` |
| fin-limit-01 is the one detection-lift catch | same file | `.records[]` where `item_id == "fin-limit-01"` |
| fin-amort-01, fin-fv-01, fin-fv-03, fin-dim-01 are the 4 false positives | same file | `.records[]` where `correct == true and indep_passed == false` |
| Lane split 31 fin (16c/15w) / 15 code (8c/7w) | same file | derived from `.records[].item_id` prefix and `.correct`, re-derivable with a one-line groupby |
| All headline metrics independently re-derived by hand and matched `metrics.py` exactly | this session's verification pass | re-derivation script run inline, not persisted as a separate file; reproducible by running the groupby/sum shown in "The first real run" against `.records` |

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
- **The real run's per-call token cost is a property of the CLI wiring, not just the model.** Each
  verification call in `arms/cli_adapter.py` is a fresh `claude -p` subprocess, which pays real
  cache-creation cost for the CLI's own tool-schema/session context on every call (confirmed
  directly: a single isolated smoke-test call before the full run showed ~20,500 of ~20,600 total
  tokens were `cache_creation_input_tokens`, not prompt/completion text). A raw API call or a
  persistent-session wiring would likely show a much lower per-check token floor, so the
  -841,640 net-token result is real but should be read as "this wiring choice, measured
  honestly," not as an intrinsic property of independent verification. This is flagged, not
  hidden, because it is exactly the kind of caveat a reviewer would otherwise have to dig for.
- **The results JSON does not persist which model made each call.** The run used haiku
  (`claude-haiku-4-5-20251001`) for every arm by construction (`run_real_cli.py --model haiku`,
  the plan's specified tier), and `results/real-cli-wiring-status.json` records the model for
  the run as a whole, but individual records in the results file do not carry a per-call model
  tag. Not a correctness issue on this single-model run; would need to be added before mixing
  models across arms (REPORT.md's own suggestion under "single model wired into both arms" below).
- **Per-item audit notes are truncated to 120 characters** (`arms/real_adapter.py`, both real
  arms call `resp.text.strip()[:120]` before storing `note`). The verdict itself is parsed from
  the FULL response text before truncation, so PASS/FLAG decisions are not affected, but a
  reviewer spot-checking a specific item's reasoning from the results JSON alone only sees the
  first ~120 characters of the model's response, not the full justification. Confirmed by
  checking the parsing code path directly; not a bug in this run, but a pre-existing
  observability gap worth fixing before a larger real run (raise or remove the truncation).
- **A single model wired into both arms shares a training distribution.** Even with isolated
  context, an independent check by the same model family may inherit some systematic errors. The
  cleanest real run uses a different model for the independent arm; the adapter allows it (wire a
  different `model_call`), and a reviewer should expect that to be reported when claimed.

Authored in a personal, industry-level capacity using public sources. No employer data, internal
figures, or system names appear in this benchmark or its code. All dataset values are synthetic.
