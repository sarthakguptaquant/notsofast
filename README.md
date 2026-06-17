# verification-adequacy

A portable governance skill for agentic AI loops. It enforces one rule that the action-level
guardrails do not: a model may not be its own only judge when being wrong is both costly and has a
checkable right answer. In contract terms, a `self`-only verification mode is not adequate as the
sole gate on a `hard_correctness`, `high`-materiality decision; such a decision must carry an
independent check (cross-model, held-out, tool, or human) or be escalated.

This is a Claude Agent Skill plus a dependency-free reference guard. It composes with, and does not
replace, action-policy layers such as AgentSpec and the Microsoft Agent Control Specification: those
gate the action, this gates the epistemics of the verification.

## Contents

```
verification-adequacy/
  SKILL.md                      the skill definition (name, description, how-to)
  reference/CONTRACT.md         the full spec, the failure-mode survey behind it, and the limits
  scripts/adequacy_gate.py      the deterministic reference guard (standard library only)
  scripts/test_adequacy_gate.py the test suite
  LICENSE                       MIT
```

## Installing the skill

A Claude Agent Skill is a folder containing `SKILL.md`. To add it:

- **Claude Code (personal):** copy this folder into `~/.claude/skills/verification-adequacy/`.
- **A project:** copy it into `.claude/skills/verification-adequacy/` inside the repo.
- **A plugin:** include the folder under the plugin's `skills/` directory.

Claude discovers the skill from its `SKILL.md` frontmatter (`name` and `description`) and loads the
body on demand when a relevant task appears.

## Using the guard directly (no skill runtime needed)

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

Run the tests:

```bash
cd scripts && python test_adequacy_gate.py
```

## Do you need an MCP server?

No. This skill is self-contained: instructions plus a pure-Python guard with no external calls, so
there is nothing for an MCP server to connect to. An MCP server becomes relevant only if you extend
the skill to reach a live external service (for example, a model registry to look up which model
version closed a loop, or a tracker to record escalations). For the v1 guard, none is required.

## Status and honest scope

The contract is a specification with a reference guard, not an empirically validated mechanism. The
soft-versus-hard task classification is a judgment call, closed by a conservative default (an
unclassifiable decision is treated as hard and high). The full limitations are in
`reference/CONTRACT.md`. Authored in a personal, industry-level capacity using public sources.
