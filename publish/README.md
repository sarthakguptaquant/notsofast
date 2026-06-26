<img src="./assets/banner.svg" alt="Third Umpire: the independent review for an AI loop's high-stakes calls" width="100%" />

*When an agentic loop grades its own homework on a call that costs real money, one rule applies.*

[![License: MIT](https://img.shields.io/badge/License-MIT-1B3DFF.svg)](./LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-1B3DFF.svg)](https://www.python.org/)
[![Tests: 11 + 2816-row conformance](https://img.shields.io/badge/tests-11%20%2B%202816--row%20conformance-00B870.svg)](../skills/third-umpire/scripts/test_third_umpire.py)
[![Dependencies: none](https://img.shields.io/badge/dependencies-none-00B870.svg)](#)

## What it is

Third Umpire is a verification-adequacy guard for agentic AI loops. The metaphor is cricket: when an on-field call is contested and consequential, you do not let it stand on the on-field umpire alone. You go to the third umpire, the independent official who reviews it with evidence the on-field umpire cannot trust by themselves.

For an AI loop, the "on-field umpire" is the model checking its own work. Third Umpire enforces one rule those self-checks do not enforce on themselves: a `self`-only verification mode may not be the sole gate on a `hard_correctness`, `high`-materiality decision. The loop must carry an independent check (cross-model, held-out, tool, or human) or it is escalated.

It ships three ways from one source:

- a Claude Code plugin (install by command),
- a drop-in skill folder (any agent that reads `SKILL.md`),
- a pip-installable Python guard (any Python environment, including a hosted code session).

It composes with action-policy layers (AgentSpec, the Microsoft Agent Control Specification, and similar) rather than replacing them. Those layers gate the action. This one gates the epistemics of the verification: whether the judgment that approved the action is allowed to stand on its own.

## Why it matters

Agentic loops increasingly close on their own self-critique. The model writes an answer, the same model reviews it, declares it good, and the loop ships. That is the cheapest verification mode to build and the most common one in autonomous and self-refine designs. It is also unsound on exactly the decisions where being wrong is expensive.

Two peer-reviewed results motivate the rule:

1. Intrinsic self-correction is unreliable on hard-correctness tasks and can degrade accuracy when there is no external signal (Huang et al., ICLR 2024, [arXiv:2310.01798](https://arxiv.org/abs/2310.01798)). A model that produced a wrong answer tends to share the blind spot that produced it.
2. A self-improving loop can learn to game its own critic, satisfying the critic without satisfying the goal (Denison et al., [arXiv:2406.10162](https://arxiv.org/abs/2406.10162)).

Think of it the way an engineering org thinks about a risky merge. You do not let the author approve their own pull request on the code path that moves money. You require a second set of eyes, and you escalate when none is available. Third Umpire is that review gate for the decisions an autonomous loop makes, where a wrong high-materiality call is a mispriced premium, a wrong reserve, a wrongly rejected claim, or a bad merge to production. The independent check is cheap relative to the loss it prevents.

There is a second, quieter saving. On a hard-correctness task, the literature says repeated self-refine passes will not reliably close the gap, and accuracy plateaus where extra passes stop buying anything (Wu et al., [arXiv:2408.00724](https://arxiv.org/abs/2408.00724)). The guard flags that pattern early and routes to an independent check instead of paying for self-critique that cannot help. The saving is the futile self-refine passes you stop running, not a blanket promise of fewer tokens.

The honest counter-case: where a decision is genuinely soft (open-ended drafting, brainstorming, subjective quality) and low-materiality, self-critique is fine. The umpire stays out of the way. The value is concentrated on the hard-and-costly fraction, and the guard is built so the cheap-and-soft work is not slowed down.

## How to run it

The guard is a dependency-free Python module. Standard library only.

```python
from third_umpire import Decision, review, VerificationMode, TaskType, Materiality

review(Decision(
    verification_mode=VerificationMode.SELF,
    task_type=TaskType.HARD_CORRECTNESS,
    materiality=Materiality.HIGH,
    has_independent_check=False,
))
# -> "REQUIRE_INDEPENDENT_CHECK"
```

The verdict is one of `ALLOW`, `REQUIRE_INDEPENDENT_CHECK`, or `ESCALATE`. When an independent check is required but none can be added (`independent_check_available=False`), the verdict is `ESCALATE` (hand to a human) rather than `REQUIRE_INDEPENDENT_CHECK`.

### Verify it yourself

```bash
python3 skills/third-umpire/scripts/test_third_umpire.py
python3 skills/third-umpire/examples/quickstart.py
```

The test suite covers the full truth table. The quickstart runs a toy self-refine loop through five scenarios and prints what the umpire decided:

```text
== Scenario A: reserve adequacy (hard-correctness, high-materiality), no checker wired ==
self-refine stopped after 1 pass(es); 4 futile pass(es) avoided; independent check -> held-out backtest + validator sign-off

== Scenario B: same decision, but no independent check is even available ==
self-refine stopped after 1 pass(es); escalated -> model-risk committee

== Scenario C: same decision, independent check already wired in ==
self-refine closed on self-critique after 1 pass(es) (call stands)

== Scenario D: marketing copy (soft, low-materiality) -> umpire stays out of the way ==
self-refine closed on self-critique after 1 pass(es) (call stands)

== Scenario E: unclassifiable decision -> conservative default (treated hard + high) ==
verdict=REQUIRE_INDEPENDENT_CHECK; mode=self, task=hard_correctness, materiality=high, independent_check=absent (...)
```

(The "model" in the quickstart is a stub. The point is the control flow and the verdicts, not the content. Illustrative, not a benchmark.)

### Install it into an agent

```bash
# Claude Code plugin
/plugin marketplace add sarthakguptaquant/third-umpire
/plugin install third-umpire@sarthak-skills

# Skill folder for any agent that reads SKILL.md
git clone https://github.com/sarthakguptaquant/third-umpire.git
cd third-umpire && ./install.sh            # user scope: ~/.claude/skills

# Python guard, any environment
pip install "git+https://github.com/sarthakguptaquant/third-umpire.git"
```

The full spec, the failure-mode survey, and the per-industry scenarios live in `skills/third-umpire/reference/`.

## What is claimed, and what is not

Claimed, and backed by the code in this repo:

- The guard is deterministic. There is no model in its routing path, so the verdict is a pure function of the tagged inputs. It replays and is auditable.
- It enforces exactly one rule, on purpose. A thin contract that refuses one well-documented unsafe pattern is more adoptable than a broad policy engine.
- The conservative default holds: when a decision cannot be confidently classified, it is treated as `hard_correctness` and `high`. The safe move is to demand more verification, never to wave a decision through.

Not claimed, stated plainly because experts read this:

- This is a specification with a reference guard, not an empirically validated mechanism. The next step is an A/B study (loops with and without the contract on a hard-correctness benchmark). It has not been run.
- The soft-versus-hard task split is a judgment call, an interpretation of the literature, not a measured boundary. On the fraction of decisions you cannot confidently classify, the contract reduces to "always require an independent check," a weaker but honest fallback.
- The novelty is the enforced, portable, task-and-materiality-aware contract and the verification-mode tag, not the observation that self-critique is weak (well documented) or the generator-critic pattern (buildable in any multi-agent framework).
- It does not gate actions (use an action-policy layer for that), it does not prove a loop correct, and it does not produce a confidence number.

The companion paper carries the citations, the does-it-already-exist analysis, and the full limitations section.

## License

MIT. See [LICENSE](./LICENSE).

---

Authored by Sarthak Gupta, Data Scientist II, Finance Models, in a personal, industry-level capacity using public sources and public frameworks. The views are my own, not my employer's, and contain no employer data or internals. More at [sarthakgpt.com](https://sarthakgpt.com).
