# Contributing to Not So Fast

Thanks for considering a contribution. The project is deliberately small and opinionated, so a few
ground rules keep it that way.

## Principles

- **The guard stays dependency-free.** `notsofast.py` uses the Python standard library only. No
  third-party runtime dependencies. This is what lets the guard replay deterministically and run in any
  environment.
- **The contract stays thin.** It enforces exactly one rule. Proposals to add a second enforced rule
  need a strong, citable justification, because the value of a thin contract is that people adopt it.
- **Honesty over marketing.** Claims are grounded in cited sources, and limits are stated plainly. Keep
  it that way. No fabricated citations.
- **House style:** no em dashes, no exclamation points, dry and direct.

## How to contribute

- **Report an issue or a false verdict:** open a GitHub issue with the `Decision` inputs and the
  verdict you expected versus what you got.
- **Propose a task-type or materiality refinement:** the soft-versus-hard axis is the most contestable
  part. Bring a concrete decision example and the reasoning, ideally with a reference.
- **Add a use case:** extend `skills/notsofast/reference/USE-CASES.md` with a new industry scenario
  in the existing format (decision, verification mode, classification, verdict).

## Before you open a pull request

Run the suite and the example. Both must pass.

```bash
cd skills/notsofast/scripts && python test_notsofast.py
python test_notsofast_rigorous.py     # 2816-row conformance suite behind the tests badge
cd ../examples && python quickstart.py
```

CI runs the same on Python 3.8, 3.11, and 3.13. Keep new code compatible with 3.8.
