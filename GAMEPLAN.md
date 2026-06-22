# Agentic AI Loops — shortcomings research + public-contribution scoping

**Status:** Day 0, scaffolding. Started 2026-06-14.
**Owner:** Sarthak Gupta. Personal capacity, industry-level. Zero employer internals.

## Goal

"The loop" (autonomous, scheduled, self-improving agent loops) is one of the biggest agentic-AI
trends right now. This is a short, deep, adversarially-vetted research push to (1) map what the
loop actually is in agentic AI today, (2) find its real shortcomings and the gaps in open tooling,
and (3) scope a defensible, solo-buildable PUBLIC contribution (open-source repo or benchmark)
that earns genuine attention and reads as an original contribution of major significance, anchored
to Sarthak's governance thesis (validation triggers, human-in-the-loop, real-money stakes).

This feeds the public-repo idea. The flagship public repo remains the model-risk-agents project;
whatever this scopes should compose with it into ONE coherent story, not a scattered third repo.

## PUBLIC-SAFETY GUARDRAILS (binding)

- Everything here is GENERIC, industry-level research. ZERO references to Sarthak's O-1/EB-1A or
  any visa/immigration angle, zero references to this campaign or its scheduled-task machinery as
  his personal system, and zero Amazon internals/data/figures. Anything that could become public
  must be framed as a general agentic-AI-governance contribution, full stop.
- No fabricated citations or invented references. Quant/ML readers will check.
- No em dashes. No exclamation points. Dry, AI-first, Sarthak's voice.

## Validation standard (binding on every day)

1. Sources verified to primary or reputable secondary, with working URLs. No paraphrase-from-memory
   passed as a citation.
2. "Already exists" vs "real gap" decided by actual search (papers, GitHub, PyPI), naming what
   exists and why it falls short.
3. Adversarial self-review section: assumptions, failure modes, what could be wrong, unverified items.
4. Reproducible: anyone can re-run the searches; sources listed.
5. Build on, do not rederive: research/model-risk-agents/ and briefings/research/2026-06-14-gap-hunt.md
   (agentic-finance gaps) and 2026-06-14-new-resources.md already exist. This focuses on the LOOP
   angle specifically, broader than finance.

## 3-day plan — one committed artifact per day, self-stops at completion

### Day 1 — Map the loop landscape + taxonomy → daily/DAY-01.md [DONE 2026-06-15]
What "the loop" means in agentic AI now: ReAct / reflection loops, plan-and-execute, self-refine /
self-improvement loops, multi-agent debate and council loops, and long-running autonomous /
scheduled agents. Survey the trend with cited sources. Define a clean taxonomy of loop types and
where each is used.

### Day 2 — Shortcomings + failure modes, mapped to tooling gaps → daily/DAY-02.md [DONE 2026-06-16]
The real failure modes: error compounding across iterations, loop instability / non-termination,
cost and token runaway, evaluation and observability gaps, drift, reward hacking and proxy-gaming,
absence of validation / governance / human-in-the-loop standards, reproducibility, safety. For each,
name the open tooling that exists and what is missing.

### Day 3 — Scope the public contribution, adversarially vetted → daily/DAY-03.md [DONE 2026-06-17]
Synthesize one (or two) concrete, solo-buildable, free public contributions (open-source library or
benchmark) that fill a real loop-tooling gap, anchored to the governance thesis (adversarially-
validated, human-in-the-loop, materiality-gated loops). Vet each with a does-it-already-exist /
buildable / PR-potential / EB-1A-value pass. Output v1 scope + PR plan + how it composes with the
model-risk-agents flagship. End with a go / no-go recommendation.

## Daily job

A scheduled research routine runs once per night, executes the next undone day with an adversarial
build-vs-critique-vs-judge gate, commits the artifact, and self-stops after Day 3. Nothing publishes
without Sarthak's sign-off.

**Research complete 2026-06-17, awaiting Sarthak review.** All three days committed. Go/no-go (DAY-03):
GO on a verification-adequacy contract (refuse a self-only verification gate where being wrong is
hard-correctness and high-materiality), built as the generic core of the model-risk-agents flagship,
not a third repo. The broad action-governance-firewall and trace-schema readings of the gap are now
occupied (AgentSpec, OCL, GAAT, Microsoft ACS); the verification-validity slice is the one still open
and the one with peer-reviewed backing. Nothing published; staged locally.
