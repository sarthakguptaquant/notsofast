# Security

## Threat surface

Third Umpire is intentionally small. The reference guard (`third_umpire.py`) is pure Python standard
library, makes no network calls, reads no files, spawns no processes, and has no third-party runtime
dependencies. The verdict is a deterministic function of the inputs you pass it. There is no telemetry
and nothing is sent anywhere. It does not require, and does not include, an MCP server.

This means the guard cannot exfiltrate data or reach an external service on its own. If you extend it
to call out (for example, to look up a model version or to record an escalation), that integration is
your code and your threat surface, not the guard's.

## Scope and non-guarantees

Third Umpire is a governance guard, not a security control and not a correctness proof. It refuses one
unsafe verification pattern. It does not validate the content of a decision, gate actions, or prevent
prompt injection. Pair it with an action-policy layer and input/output filtering for those concerns.

## Reporting

If you find a security issue in the guard itself, open a GitHub issue, or for anything sensitive,
contact the maintainer via the repository profile. There is no formal SLA on this project.
