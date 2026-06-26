# The Not So Fast Contract

This is the full specification behind the skill. It is condensed from a three-day failure-mode survey
of agentic AI loops. The companion paper carries the citations and the does-it-already-exist analysis.

## The problem, in one paragraph

An agentic loop is a model that proposes, executes, observes, and proposes again. The loop is closed
by some verification mode: the model checking itself (`self`), other agents (`peer`), a tool or test
oracle (`tool`), or a human (`human`). Most autonomous loops shipping today close on `self` or on
nothing. A peer-reviewed result establishes that intrinsic self-correction is unreliable on
hard-correctness tasks and can degrade accuracy (Huang et al., ICLR 2024, arXiv:2310.01798), and a
self-improving loop has been shown to generalize to gaming its own critic (Denison et al.,
arXiv:2406.10162). The runtime-governance tools that shipped in the last year gate the *action* (is
this tool call allowed) but not the *verification structure* (is the judgment that approved it allowed
to stand on its own).

## The contract

**Part 1, tag the verification mode.** Annotate each loop or sub-loop with what closes it: `self`,
`peer`, `tool`, or `human`. This is a loop-level semantic that action-policy layers and the current
OpenTelemetry GenAI spans do not carry.

**Part 2, classify the decision** on two axes:
- Task type: `soft` (open-ended generation with subjective quality, where self-feedback measurably
  helps) versus `hard_correctness` (a checkable, costly-to-get-wrong answer, where self-correction is
  unreliable). The soft-versus-hard split is an interpretation of the literature, not a measured
  boundary.
- Materiality: `low` (reversible and cheap) versus `high` (costly and hard to reverse).
- Conservative default: when a decision cannot be confidently classified, treat it as
  `hard_correctness` and `high`. The safe move is to demand more verification, never to wave it
  through.

**Part 3, one enforced rule.** If the mode is `self` and the decision is `hard_correctness` and
`high`, the loop must carry an independent check (cross-model critic, held-out verifier, tool or test
oracle, or human gate) or it does not pass. The verdict is `ALLOW`, `REQUIRE_INDEPENDENT_CHECK`, or
`ESCALATE`. The contract restricts exactly this one pattern, on purpose: it is the pattern with
peer-reviewed backing, and a thin enforced contract is more adoptable than a broad policy engine.

## The guard

```
function review(decision):
    mode        = verification_mode(decision)            # self | peer | tool | human
    task, matl  = classify(decision)                     # unknown -> hard_correctness / high
    if mode == self and task == hard_correctness and matl == high:
        if has_independent_check(decision):              # cross-model | held-out | tool | human
            return ALLOW
        return REQUIRE_INDEPENDENT_CHECK or ESCALATE
    return ALLOW
```

The reference implementation in `scripts/notsofast.py` carries no model in its routing path, so
it replays deterministically and is auditable.

## Why this is not the action-firewall

AgentSpec (arXiv:2503.18666), the Organizational Control Layer (arXiv:2606.04306), and the Microsoft
Agent Control Specification answer "may this action run." They are silent on whether a loop's
self-check is valid for the task. A loop can pass every action-policy and still be governed only by a
model grading its own work on a task the literature says it cannot grade. The action-policy layers
could express this rule only if a verification-mode tag (Part 1) existed, which today they do not, so
the tag and the rule it enables are the load-bearing novelty, not a claim of geometric orthogonality.

## A worked end-state: model-risk validation

A deterministic, model-free model-risk validation gate (scoring discrimination, calibration,
stability, backtesting against fixed policy and routing to pass, human review, or hard block) is a
worked instance of the end-state this contract recommends: independent, non-self verification on a
hard-correctness, high-materiality decision, in a domain where being wrong is a regulated, real-money
fact. It demonstrates the prescribed independent verifier; it does not exercise the self-critique-
refusal trigger, because there is no self-critic in its path to refuse.

## Limits

- The contract is a specification with a reference guard, not an empirically validated mechanism. An
  A/B study (loops with and without the contract on a hard-correctness benchmark) is the next step.
- The novelty is the enforced, portable, task-and-materiality-aware contract and the verification-mode
  tag, not the observation that self-critique is weak (well documented) or the generator-critic dyad
  pattern (buildable in any multi-agent framework).
- The task-type axis is a judgment call. It earns its place only on the confidently-classifiable
  fraction of decisions; on the rest the conservative default applies, and the contract reduces to
  "always require an independent check," a weaker but honest fallback.
- "Not packaged anywhere" is a search result as of mid-2026, not a proof that nothing exists in any
  private or unindexed form.

Authored in a personal, industry-level capacity using public sources. No employer internals.
