# verification-adequacy

A portable governance skill for agentic AI loops. It enforces one rule that the action-level
guardrails do not: a model may not be its own only judge when being wrong is both costly and has a
checkable right answer. In contract terms, a `self`-only verification mode is not adequate as the
sole gate on a `hard_correctness`, `high`-materiality decision; such a decision must carry an
independent check (cross-model, held-out, tool, or human) or be escalated.

It ships three ways from one source: as a **Claude Code plugin** (install by command), as a
**drop-in skill folder** (any agent that reads `SKILL.md`), and as a **pip-installable Python guard**
(any Python environment, including a hosted code session). It composes with action-policy layers such
as AgentSpec and the Microsoft Agent Control Specification rather than replacing them: those gate the
action, this gates the epistemics of the verification.

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
  claim, a bad merge to production). The contract forces an independent check before such a decision
  stands; the check is cheap relative to the loss.
- *Reduced token waste on futile self-refinement:* refinement loops are a large share of agentic token
  spend (the review stage alone was 59.4 percent of tokens in one study, Salim et al., arXiv:2601.14470)
  and accuracy plateaus where extra passes stop helping (Wu et al., arXiv:2408.00724). On a
  hard-correctness task, more self-refine passes will not close the gap, so the guard stops them early
  and routes to an independent check instead of paying for self-critique that cannot help. The saving is
  the futile passes you stop running, not a blanket promise of fewer tokens.
- *A clean audit trail:* the verdict is a deterministic function of tagged inputs, so it replays and is
  explainable.

**Where it applies.** Finance and model risk, insurance, healthcare, legal and compliance, autonomous
software-engineering agents, and enterprise operations and support: anywhere a loop makes a decision
that is both checkable and costly to get wrong. Per-industry scenarios with verdicts are in
[`skills/verification-adequacy/reference/USE-CASES.md`](skills/verification-adequacy/reference/USE-CASES.md).
A runnable walkthrough is
[`skills/verification-adequacy/examples/quickstart.py`](skills/verification-adequacy/examples/quickstart.py)
(`python quickstart.py`).

## Install

### A. Claude Code plugin (one command)

```text
/plugin marketplace add sarthakguptaquant/verification-adequacy
/plugin install verification-adequacy@sarthak-skills
```

Non-interactive (terminal) equivalent:

```bash
claude plugin marketplace add sarthakguptaquant/verification-adequacy --scope user
claude plugin install verification-adequacy@sarthak-skills --scope user
```

A private repository works for manual install via your existing `gh auth` credentials; set
`GITHUB_TOKEN` if you also want background auto-updates.

### B. Skill folder (Claude Code, or any agent that reads SKILL.md)

One-liner (works once the repo is public):

```bash
curl -fsSL https://raw.githubusercontent.com/sarthakguptaquant/verification-adequacy/main/install.sh | bash
```

Or clone and run the installer (works for a private repo with your git credentials):

```bash
git clone https://github.com/sarthakguptaquant/verification-adequacy.git
cd verification-adequacy && ./install.sh            # user scope: ~/.claude/skills
./install.sh --project                              # project scope: ./.claude/skills
```

### C. Python guard (any environment)

```bash
pip install "git+https://github.com/sarthakguptaquant/verification-adequacy.git"
```

```python
from adequacy_gate import Decision, adequacy_gate, VerificationMode, TaskType, Materiality

adequacy_gate(Decision(
    verification_mode=VerificationMode.SELF,
    task_type=TaskType.HARD_CORRECTNESS,
    materiality=Materiality.HIGH,
    has_independent_check=False,
))
# -> "REQUIRE_INDEPENDENT_CHECK"
```

## Layout

```
verification-adequacy/                         repo root = plugin root = marketplace root
  .claude-plugin/marketplace.json              lets `/plugin marketplace add` discover the plugin
  .claude-plugin/plugin.json                   plugin manifest
  skills/verification-adequacy/SKILL.md        the skill (auto-discovered by Claude Code)
  skills/verification-adequacy/reference/CONTRACT.md   full spec and limits
  skills/verification-adequacy/reference/USE-CASES.md  per-industry scenarios with verdicts
  skills/verification-adequacy/scripts/adequacy_gate.py        the deterministic guard
  skills/verification-adequacy/scripts/test_adequacy_gate.py   the test suite
  skills/verification-adequacy/examples/quickstart.py          runnable self-refine-loop walkthrough
  install.sh                                   skill-folder installer
  pyproject.toml                               pip packaging for the guard
  AGENTS.md                                    cross-agent instructions (Codex, Cursor, etc.)
  README.md, LICENSE
```

## Verify

```bash
python3 skills/verification-adequacy/scripts/test_adequacy_gate.py
```

## Do you need an MCP server?

No. The skill is self-contained: instructions plus a pure-Python guard with no external calls, so
there is nothing for an MCP server to connect to. An MCP server becomes relevant only if you extend
the skill to reach a live external service (a model registry to look up which model version closed a
loop, a tracker to record escalations). For v1, none is required.

## Status and honest scope

The contract is a specification with a reference guard, not an empirically validated mechanism. The
soft-versus-hard task classification is a judgment call, closed by a conservative default (an
unclassifiable decision is treated as hard and high). Full limitations are in
`skills/verification-adequacy/reference/CONTRACT.md`. Authored in a personal, industry-level capacity
using public sources.
