# AGENTS.md — verification-adequacy

This file lets any agent runtime that reads `AGENTS.md` (Codex, Cursor, and similar) pick up the
same contract the Claude skill (`skills/verification-adequacy/SKILL.md`) encodes. The rule is
runtime-agnostic.

## The rule

When an agentic loop produces a consequential decision, check its verification structure before
acting on it:

1. Identify what closes the loop: `self` (the model critiques itself), `peer` (other agents), `tool`
   (a test suite, retriever, or environment oracle), or `human`.
2. Classify the decision: task type `soft` (open-ended generation, self-feedback helps) versus
   `hard_correctness` (a checkable, costly-to-get-wrong answer); materiality `low`
   (reversible-and-cheap) versus `high` (costly-and-hard-to-reverse). If you cannot confidently
   classify, treat it as `hard_correctness` and `high`.
3. If the mode is `self` and the decision is `hard_correctness` and `high`, do not let it stand on
   self-critique alone. Add an independent check (cross-model, held-out, tool, or human) or escalate
   to a human.

## The guard

`skills/verification-adequacy/scripts/adequacy_gate.py` is a dependency-free Python implementation.
In any Python environment:

```bash
pip install "git+https://github.com/sarthakguptaquant/verification-adequacy.git"
```

```python
from adequacy_gate import Decision, adequacy_gate, VerificationMode, TaskType, Materiality

adequacy_gate(Decision(VerificationMode.SELF, TaskType.HARD_CORRECTNESS, Materiality.HIGH,
                       has_independent_check=False))
# -> "REQUIRE_INDEPENDENT_CHECK"
```

## Scope

This gates the epistemics of verification, not the action. It composes with action-policy layers
(AgentSpec, the Microsoft Agent Control Specification), it does not replace them. Full spec and limits
are in `skills/verification-adequacy/reference/CONTRACT.md`. No external service or MCP server is
required.
