---
name: third-umpire
description: >
  Use when designing, reviewing, or governing an agentic AI loop and you need to check that the
  loop's verification structure is adequate for the stakes. Enforces one rule: a self-only critic
  may not be the sole gate on a hard-correctness, high-materiality decision; the loop must add an
  independent check (cross-model, held-out, tool, or human) or escalate. Triggers on agent loop
  design, self-refine or reflection loops, autonomous or self-improving agents, AI governance,
  human-in-the-loop decisions, model risk, and "should this loop be allowed to check its own work".
---

# Third Umpire

> The independent review for an AI loop's high-stakes calls. When a loop wants to close on the
> model's own self-critique and the decision is costly and checkable, the call does not stand on the
> on-field umpire alone. It goes to the third umpire.

## The problem it solves

Agentic loops increasingly close on their own self-critique. A model writes an answer, the same
model reviews it, declares it good, and the loop ships the result. This is the cheapest verification
mode to build and the most common one in autonomous and self-refine designs. It is also unsound on
exactly the decisions where it matters most.

Two failure modes drive this:

1. **Self-correction does not reliably work on hard-correctness tasks.** A peer-reviewed result shows
   intrinsic self-correction is unreliable and can *degrade* accuracy when there is no external signal
   (Huang et al., ICLR 2024, arXiv:2310.01798). A model that produced a wrong answer tends to share
   the blind spot that produced it.
2. **A self-improving loop can game its own critic.** When the actor and the critic are the same
   system, the loop can learn to satisfy the critic without satisfying the goal (Denison et al.,
   arXiv:2406.10162; sycophancy in Sharma et al., arXiv:2310.13548).

The action-level guardrails that shipped in the last year (AgentSpec, the Microsoft Agent Control
Specification, and similar) check whether an *action* is allowed. None of them checks whether the
*judgment* that approved the action is allowed to stand on its own. That is the gap Third Umpire fills:
it enforces verification adequacy.

## What it saves you

- **Avoided high-cost errors (the main value).** On a hard-correctness, high-materiality decision, a
  wrong answer that a self-critic waved through is expensive in the real world: a mispriced position, a
  wrong risk number, a bad credit decision, a bad code merge to production, a flawed compliance
  determination. The contract forces a second, independent set of eyes (model, tool, or human) before
  such a decision stands. The check is cheap relative to the loss it prevents.
- **Reduced token and cost waste on futile self-refinement.** Refinement loops are a major share of
  agentic token spend (the iterative review stage alone consumed 59.4 percent of tokens in one study
  of agentic software engineering, Salim et al., arXiv:2601.14470), and inference-scaling work shows
  inference-scaling work finds a compute-optimal point past which extra passes stop being worth their
  cost (Wu et al., arXiv:2408.00724). On a
  hard-correctness task the literature says self-critique will not reliably close the gap, so repeated
  self-refine passes burn tokens without improving the answer. Third Umpire flags that pattern early
  and routes to an independent check or escalation instead of paying for more self-critique that cannot
  help. The saving is the self-refine iterations you stop running, not a guarantee of fewer tokens
  overall.
- **A clean audit trail.** The verdict is a deterministic function of tagged inputs, so every call
  replays and is explainable, which is what an auditor or a risk function asks for.

The honest counter-case: where a decision is genuinely soft (open-ended drafting, brainstorming,
subjective quality) and low-materiality, self-critique is fine and Third Umpire leaves it alone. The
value is concentrated on the hard-and-costly fraction, and the skill is built so the cheap-and-soft
work is not slowed down.

## Where it applies (industries)

Anywhere agentic loops make decisions that are both checkable and costly to get wrong:

- **Finance and model risk:** credit decisions, VaR and pricing model outputs, capital and forecast
  sign-off. (Worked end-state in `reference/CONTRACT.md`.)
- **Healthcare:** clinical decision support, triage, coding and prior-authorization.
- **Legal and compliance:** contract review, regulatory determinations, policy checks.
- **Software engineering:** autonomous code-generation and PR agents merging to production.
- **Enterprise operations and support:** autonomous workflow agents and consequential ticket
  resolution that take real-world actions.

Concrete per-industry scenarios, each showing the decision, the verification mode, the classification,
and the verdict, are in `reference/USE-CASES.md`.

## When to apply it

Apply this whenever a loop closes on its own self-critique (reflection, self-refine, a ReAct agent
that decides it is done, an autonomous wrapper with no external gate) and the decision it produces is
consequential. Skip it for cheap, reversible, open-ended generation where self-feedback is known to
help.

## The contract

1. **Tag the verification mode:** `self`, `peer`, `tool`, or `human` (what closes the loop).
2. **Classify the decision:** task type `soft` versus `hard_correctness`; materiality `low` versus
   `high`. When you cannot confidently classify, default to `hard_correctness` and `high`. The safe
   move is to demand more verification, never to wave a decision through.
3. **Send it to the umpire:** if the mode is `self` and the decision is `hard_correctness` and `high`,
   the loop must have an independent check or it does not pass. The call is `ALLOW`,
   `REQUIRE_INDEPENDENT_CHECK`, or `ESCALATE`.

## How to use the bundled guard

`scripts/third_umpire.py` is a dependency-free reference implementation:

```python
from third_umpire import Decision, review, VerificationMode, TaskType, Materiality

verdict = review(Decision(
    verification_mode=VerificationMode.SELF,
    task_type=TaskType.HARD_CORRECTNESS,
    materiality=Materiality.HIGH,
    has_independent_check=False,
))
# verdict == "REQUIRE_INDEPENDENT_CHECK"
```

Run `python scripts/test_third_umpire.py` for the test suite, and
`python examples/quickstart.py` for a worked self-refine-loop walkthrough.

## What this is not

It does not gate actions (use an action-policy layer for that), it does not prove a loop correct, and
it does not produce a confidence number. It is a thin, auditable contract that refuses one specific
unsafe pattern, and it composes with action-policy layers rather than replacing them.

## Honest limits

The soft-versus-hard classification is a judgment call, closed by the conservative default above. The
contract is a specification with a reference guard, not an empirically validated mechanism. Full
reasoning, the failure-mode survey, and the limits are in `reference/CONTRACT.md`.
