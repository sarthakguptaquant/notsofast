---
name: verification-adequacy
description: >
  Use when designing, reviewing, or governing an agentic AI loop and you need to check that the
  loop's verification structure is adequate for the stakes. Enforces one rule: a self-only critic
  may not be the sole gate on a hard-correctness, high-materiality decision; the loop must add an
  independent check (cross-model, held-out, tool, or human) or escalate. Triggers on agent loop
  design, self-refine or reflection loops, autonomous or self-improving agents, AI governance,
  human-in-the-loop decisions, and "should this loop be allowed to check its own work" questions.
---

# Verification Adequacy

## What this is

A small, portable governance contract for agentic AI loops. It does one thing the action-level
guardrails (AgentSpec, Microsoft Agent Control Specification, and similar) do not: it asks whether a
loop's *verification structure* is valid for the decision it is about to make, rather than whether the
*action* is allowed.

The one rule, in plain terms: do not let a model be its own only judge when being wrong is both
costly and has a checkable right answer. This is grounded in a peer-reviewed negative result that
intrinsic self-correction is unreliable on hard-correctness tasks (Huang et al., ICLR 2024,
arXiv:2310.01798) and evidence that a self-improving loop can game its own critic (Denison et al.,
arXiv:2406.10162).

## When to apply it

Apply this whenever a loop closes on its own self-critique (reflection, self-refine, a ReAct agent
that decides it is done, an autonomous wrapper with no external gate) and the decision it produces is
consequential. Skip it for cheap, reversible, open-ended generation where self-feedback is known to
help.

## The contract

1. **Tag the verification mode.** Identify what closes the loop: `self` (the model critiques itself),
   `peer` (other agents), `tool` (a test suite, retriever, or environment oracle), or `human`.
2. **Classify the decision** on two axes: task type (`soft` open-ended generation versus
   `hard_correctness` a checkable, costly-to-get-wrong answer) and materiality (`low`
   reversible-and-cheap versus `high` costly-and-hard-to-reverse). When you cannot confidently
   classify, default to `hard_correctness` and `high`. The safe move is to demand more verification,
   never to wave a decision through.
3. **Enforce the rule.** If the mode is `self` and the decision is `hard_correctness` and `high`, the
   loop must have an independent check or it does not pass. Return one of: `ALLOW` (an independent
   check is present), `REQUIRE_INDEPENDENT_CHECK` (add a cross-model, held-out, tool, or human check),
   or `ESCALATE` (no independent check is available; route to a human).

## How to use the bundled guard

`scripts/adequacy_gate.py` is a dependency-free reference implementation. Import it and call
`adequacy_gate(decision)` on each consequential loop decision:

```python
from adequacy_gate import Decision, adequacy_gate, VerificationMode, TaskType, Materiality

verdict = adequacy_gate(Decision(
    verification_mode=VerificationMode.SELF,
    task_type=TaskType.HARD_CORRECTNESS,
    materiality=Materiality.HIGH,
    has_independent_check=False,
))
# verdict == "REQUIRE_INDEPENDENT_CHECK"
```

Run `python scripts/test_adequacy_gate.py` to confirm the guard behaves as specified.

## What this is not

It does not gate actions (use an action-policy layer for that), it does not prove a loop correct, and
it does not produce a confidence number. It is a thin, auditable contract that refuses one specific
unsafe pattern. The full reasoning, the failure-mode survey behind it, and the limits are in
`reference/CONTRACT.md`.

## Honest limits

The soft-versus-hard classification is a judgment call, closed by the conservative default above. The
contract is a specification with a reference guard, not an empirically validated mechanism. See the
limits section of `reference/CONTRACT.md`.
