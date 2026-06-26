# Changelog

All notable changes to Not So Fast are recorded here. The format follows Keep a Changelog, and the
project uses semantic versioning.

## [0.1.0] - 2026-06-17

First release.

- The verification-adequacy contract: tag a loop's verification mode (self, peer, tool, human),
  classify the decision by task type and materiality, and refuse a self-only critic as the sole gate
  on a hard-correctness, high-materiality decision (require an independent check or escalate).
- `notsofast.py`: a deterministic, dependency-free reference guard with `review()` and `explain()`,
  conservative defaults for unclassifiable decisions, and an ESCALATE path when no independent check is
  available.
- Ships three ways: Claude Code plugin (marketplace + plugin manifests), drop-in skill folder
  (`install.sh`), and a pip-installable module (`pyproject.toml`).
- `AGENTS.md` for non-Claude agent runtimes.
- Reference spec (`CONTRACT.md`), per-industry use cases (`USE-CASES.md`), a runnable example
  (`quickstart.py`), and a test suite.
