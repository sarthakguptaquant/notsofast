# benchmark/

The empirical harness for the Not So Fast claim: that an isolated independent check catches
hard-correctness errors a same-context self-critic waves through, and that stopping futile
self-refine passes pays for the check often enough to matter.

This turns the central claim into two measurable numbers (detection lift, net token ledger) on a
dataset whose ground truth is arithmetic, not opinion. It ships a deterministic mock that proves
the plumbing now, and a one-function plug-in that makes the run real. Full methods, results, and
the falsification design are in `REPORT.md`.

## Run it

```bash
python benchmark/run.py            # mock pilot: validates mechanics, writes results/
python benchmark/run.py --seed 7   # a different seed
python benchmark/test_benchmark.py # 29 conformance tests for the harness itself
python benchmark/run.py --real     # real run; needs a wired model_call (see arms/real_adapter.py)
```

No third-party dependencies. Python 3.8+. The mock run does not touch the network.

## Layout

```
benchmark/
  dataset/checkers.py    ground-truth checkers (pure functions; the oracle, never a model)
  dataset/items.py       46 governed items + 2 controls, with a self-verifying integrity gate
  arms/base.py           the arm interface and isolate(): where epistemic isolation is enforced
  arms/mock.py           seeded deterministic arms for CI and the mechanics pilot
  arms/real_adapter.py   the one function you wire to make the run real (no provider hardcoded)
  metrics.py             detection lift, false-positive rate, per-arm accuracy, net-token ledger
  run.py                 wires the SHIPPED review() guard into the loop; emits run id + results
  test_benchmark.py      conformance tests (isolation, shipped-guard, metrics math, determinism)
  results/               committed pilot output (pilot-mock-latest.json)
  REPORT.md              the empirical note: claim, method, ledger, pilot, falsification
```

## The honest scope, in one line

The mock pilot proves the pipeline is correct. It does NOT prove the claim. The claim is a real
result the moment a model is wired into `model_call`, on the same dataset, guard, and metrics.
`REPORT.md` states exactly what result would falsify the claim.
