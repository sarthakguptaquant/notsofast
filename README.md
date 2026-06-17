# Third Umpire

**The independent review for an AI loop's high-stakes calls.** When an agentic loop wants to close on
the model's own self-critique and the decision is costly and checkable, the call does not stand on the
on-field umpire alone. It goes to the third umpire: an independent check (cross-model, held-out, tool,
or human), or it is escalated.

![CI](https://github.com/sarthakguptaquant/third-umpire/actions/workflows/ci.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)
![Dependencies: none](https://img.shields.io/badge/dependencies-none-success)

Third Umpire enforces one rule the action-level guardrails do not: a `self`-only verification mode is
not adequate as the sole gate on a `hard_correctness`, `high`-materiality decision. It ships three ways
from one source: a **Claude Code plugin** (install by command), a **drop-in skill folder** (any agent
that reads `SKILL.md`), and a **pip-installable Python guard** (any Python environment, including a
hosted code session). It composes with action-policy layers such as AgentSpec and the Microsoft Agent
Control Specification rather than replacing them: those gate the action, this gates the epistemics of
the verification.

## Why this exists

**The problem.** Agentic loops increasingly close on their own self-critique: the model writes an
answer, the same model reviews it, and the loop ships. That is the cheapest verification mode and the
most common in autonomous and self-refine designs, and it is unsound on exactly the decisions that
matter. A peer-reviewed result shows intrinsic self-correction is unreliable and can degrade accuracy
on hard-correctness tasks (Huang et al., ICLR 2024, arXiv:2310.01798), and a self-improving loop has
been shown to game its own critic (Denison et al., arXiv:2406.10162). The action-level guardrails that
shipped recently check whether an action is allowed; none checks whether the judgment that approved it
may stand on its own.

**What it saves you.**
- *Avoided high-cost errors (the main value):* a wrong high-materiality decision a self-critic waved
  through is expensive in the real world (a mispriced premium, a wrong reserve, a wrongly rejected
  claim, a bad merge to production). Third Umpire forces an independent check before such a decision
  stands; the check is cheap relative to the loss.
- *Reduced token waste on futile self-refinement:* refinement loops are a large share of agentic token
  spend (the review stage alone was 59.4 percent of tokens in one study, Salim et al., arXiv:2601.14470)
  and accuracy plateaus where extra passes stop helping (Wu et al., arXiv:2408.00724). On a
  hard-correctness task, more self-refine passes will not close the gap, so the umpire stops them early
  and routes to an independent check instead of paying for self-critique that cannot help. The saving is
  the futile passes you stop running, not a blanket promise of fewer tokens.
- *A clean audit trail:* the verdict is a deterministic function of tagged inputs, so it replays and is
  explainable.

**Where it applies.** Finance and model risk, insurance, healthcare, legal and compliance, autonomous
software-engineering agents, and enterprise operations and support: anywhere a loop makes a decision
that is both checkable and costly to get wrong. Per-industry scenarios with verdicts are in
[`skills/third-umpire/reference/USE-CASES.md`](skills/third-umpire/reference/USE-CASES.md). A runnable
walkthrough is [`skills/third-umpire/examples/quickstart.py`](skills/third-umpire/examples/quickstart.py).

## Install

### A. Claude Code plugin (one command)

```text
/plugin marketplace add sarthakguptaquant/third-umpire
/plugin install third-umpire@sarthak-skills
```

Non-interactive (terminal) equivalent:

```bash
claude plugin marketplace add sarthakguptaquant/third-umpire --scope user
claude plugin install third-umpire@sarthak-skills --scope user
```

A private repository works for manual install via your existing `gh auth` credentials; set
`GITHUB_TOKEN` if you also want background auto-updates.

### B. Skill folder (Claude Code, or any agent that reads SKILL.md)

One-liner (works once the repo is public):

```bash
curl -fsSL https://raw.githubusercontent.com/sarthakguptaquant/third-umpire/main/install.sh | bash
```

Or clone and run the installer (works for a private repo with your git credentials):

```bash
git clone https://github.com/sarthakguptaquant/third-umpire.git
cd third-umpire && ./install.sh            # user scope: ~/.claude/skills
./install.sh --project                     # project scope: ./.claude/skills
```

### C. Python guard (any environment)

```bash
pip install "git+https://github.com/sarthakguptaquant/third-umpire.git"
```

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

## What it does (demo output)

```text
$ python examples/quickstart.py
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

## Works with

| Runtime | How |
|---|---|
| Claude Code | plugin (`/plugin install`) or skill folder in `~/.claude/skills` |
| Cursor, OpenAI Codex, other AGENTS.md-aware agents | clone the repo; the agent reads `AGENTS.md` |
| Any agent that reads `SKILL.md` folders | `./install.sh` into its skills directory |
| Any Python program | `pip install` the guard and call `review(...)` |

## Layout

```
third-umpire/                                  repo root = plugin root = marketplace root
  .claude-plugin/marketplace.json              lets `/plugin marketplace add` discover the plugin
  .claude-plugin/plugin.json                   plugin manifest
  .github/workflows/ci.yml                     runs the tests and example on every push
  skills/third-umpire/SKILL.md                 the skill (auto-discovered by Claude Code)
  skills/third-umpire/reference/CONTRACT.md    full spec and limits
  skills/third-umpire/reference/USE-CASES.md   per-industry scenarios with verdicts
  skills/third-umpire/scripts/third_umpire.py  the deterministic guard
  skills/third-umpire/scripts/test_third_umpire.py   the test suite
  skills/third-umpire/examples/quickstart.py   runnable self-refine-loop walkthrough
  install.sh, pyproject.toml, AGENTS.md, CHANGELOG.md, CONTRIBUTING.md, SECURITY.md, README.md, LICENSE
```

## Verify

```bash
python3 skills/third-umpire/scripts/test_third_umpire.py
python3 skills/third-umpire/examples/quickstart.py
```

## Do you need an MCP server?

No. Third Umpire is self-contained: instructions plus a pure-Python guard with no external calls, so
there is nothing for an MCP server to connect to. An MCP server becomes relevant only if you extend
the skill to reach a live external service (a model registry to look up which model version closed a
loop, a tracker to record escalations). For v1, none is required. See `SECURITY.md`.

## Status and honest scope

The contract is a specification with a reference guard, not an empirically validated mechanism. The
soft-versus-hard task classification is a judgment call, closed by a conservative default (an
unclassifiable decision is treated as hard and high). Full limitations are in
`skills/third-umpire/reference/CONTRACT.md`. Authored in a personal, industry-level capacity using
public sources.
