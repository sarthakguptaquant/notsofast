# Verification Adequacy in Agentic AI Loops: A Failure-Mode Survey and a Governance Contract

**Author:** Sarthak Gupta, Independent Researcher
**Contact:** [sarthakgpt.com](https://sarthakgpt.com)
**Date:** June 2026
**Capacity:** Personal, industry-level. All work conducted independently using public sources and
public frameworks. No employer data, internals, or figures.

---

## Abstract

An agentic AI system is a language model wrapped in a control loop: the model proposes, something
executes, the result is fed back, and the model proposes again. The loop structure, not the model
call, decides what is fed back, when the loop stops, and who checks the work. We survey the loop
families in use in mid-2026, organize their failure modes against the open tooling that does or does
not address each, and find that the field has converged on action-level governance: intercept the
action, evaluate a policy, allow, warn, deny, or escalate. That convergence leaves one axis
unaddressed. None of the shipping action-governance layers asks whether a loop's *verification
structure* is epistemically valid for the decision it is about to make. This matters because a
peer-reviewed negative result establishes that intrinsic self-correction is unreliable on
hard-correctness tasks and can degrade accuracy, and further work shows that a self-improving loop can
game its own critic. We propose a verification-adequacy contract: tag each loop with the mode that
closes it (self, peer, tool, or human), classify the decision by task type and materiality, and
enforce a single rule, that a self-only verification mode may not be the sole gate on a
hard-correctness, high-materiality decision. The contract is a specification with a small reference
guard, not a proof of loop correctness, and we state its limits plainly: the task-type axis is a
judgment call closed by a conservative default, and the contribution is the enforced, portable
contract, not the long-known observation that self-critique is weak. We show that a deterministic model-risk
validation gate is a worked instance of the end-state the contract recommends, in a domain where being
wrong is a regulated, real-money fact.

---

## 1. Introduction

Strip away the marketing and an agent is a model in a loop. The model proposes an action or a revised
answer, an executor or a critic responds, and the output is fed back for the next turn. The
interesting engineering is not the model call. It is the loop: what gets fed back, when the loop
terminates, and who or what checks the work along the way. Different loop structures have different
failure surfaces, and the failure surface is what a practitioner shipping a loop into a consequential
setting has to reason about.

The trend in 2026 is toward more autonomy: longer-horizon loops, more self-direction, and more
self-checking. The claim this paper develops is that autonomy is outpacing verification, and that the
weakness concentrates in exactly the self-checked and autonomous designs that are shipping fastest.
This is a structural reading of the failure modes, not a measured rate over time, and we are careful
not to dress it up as the latter.

The paper makes three moves. Section 2 maps the loop families and isolates the axis that matters for
governance, which is who checks the work. Section 3 turns nine failure modes into a gap table against
the open tooling for each. Section 4 runs an honest does-it-already-exist pass and finds that the
broad governance-firewall reading of the gap was filled by other people in the year to mid-2026, while
one narrow reading remains open. Section 5 is the contribution: a verification-adequacy contract that
occupies the open slice, made concrete enough to build. Section 6 shows the contract composing with an
existing model-risk validation system as its finance instantiation. Section 7 states the limits.

**Contribution.** A portable, machine-readable contract that (a) tags a loop's verification mode, (b)
classifies a decision by task type and materiality, and (c) enforces that a self-only verification mode
is not the sole gate on a hard-correctness, high-materiality decision, requiring an independent check
or an escalation. We do not claim the contract proves a loop correct, and we do not claim originality
for the observation that self-critique is unreliable; that is well documented and is our motivation,
not our result. We claim that the enforced, task-and-materiality-aware contract is not shipped today,
and that the action-governance layers occupying the neighboring space do not address it.

---

## 2. A taxonomy of agentic loops

A flat list of loop families hides the structure, so we use two tiers. **Base loops** are the atomic
iteration patterns. **Composition strategies** orchestrate base loops into something larger. A
long-horizon **autonomous wrapper** sits outside both. The split is by what is iterated and what closes
the loop, not by brand.

The scope here is inference-time orchestration loops: loops that iterate text, plans, trajectories, or
tasks at run time while the model weights stay frozen. A second, equally large family of training-time
loops, where the iterated object is the weights themselves and an environment reward closes the loop,
is out of scope; it has a different governance surface and a different stack, surveyed elsewhere
([arXiv:2509.02547](https://arxiv.org/abs/2509.02547)).

**Base loops.**

- *Reason-act (ReAct).* The model interleaves a reasoning trace with an action, observes the result,
  and repeats until it emits an answer. This is the canonical base pattern most other loops build on
  (Yao et al., [arXiv:2210.03629](https://arxiv.org/abs/2210.03629)). What closes the loop: the model
  declares itself done.
- *Reflection / self-refine.* The iterated object is the agent's own output, and a critic step closes
  the loop. Self-Refine uses one model as generator, critic, and refiner (Madaan et al.,
  [arXiv:2303.17651](https://arxiv.org/abs/2303.17651)); Reflexion stores the critique as verbal
  feedback in memory for the next trial (Shinn et al.,
  [arXiv:2303.11366](https://arxiv.org/abs/2303.11366)). What closes the loop: an evaluator or
  self-critique verdict. A retrieval-specialized variant, corrective RAG, closes a retrieve,
  critique-relevance, re-retrieve loop with a retrieval evaluator (agentic-RAG survey,
  [arXiv:2506.10408](https://arxiv.org/html/2506.10408v1)).

**Composition strategies.**

- *Plan-then-execute.* A planner decomposes the goal, an executor runs the steps, and a re-planner
  revises (Plan-and-Solve, [arXiv:2305.04091](https://arxiv.org/abs/2305.04091)). What closes the loop:
  the re-planner judging the plan still viable, or the goal met.
- *Search (tree-structured).* The loop becomes a search over trajectories, each trajectory a base loop,
  wrapped in Monte Carlo Tree Search (LATS, Zhou et al.,
  [arXiv:2310.04406](https://arxiv.org/abs/2310.04406)). What closes the loop: a value function plus a
  search budget.
- *Multi-agent / debate.* Multiple instances propose, critique, and converge (Du et al.,
  [arXiv:2305.14325](https://arxiv.org/abs/2305.14325)). The evidence is genuinely contested: a
  controlled study finds majority pressure can suppress a correct minority, and that reasoning strength
  and group diversity, not the debate procedure, drive any gain
  ([arXiv:2511.07784](https://arxiv.org/abs/2511.07784)). What closes the loop: convergence or a vote.

**Autonomous wrapper.** The most hyped and least governed family is a long-horizon wrapper that runs
the loops above repeatedly. Long-running task loops such as BabyAGI often have no clean stop. Self-
improving skill loops such as Voyager write, test, and store reusable skills
([arXiv:2305.16291](https://arxiv.org/abs/2305.16291)); the Gödel Agent lets the agent modify its own
logic and concedes in print that it "is not sufficiently stable and may be prone to error
accumulation" ([arXiv:2410.04444](https://arxiv.org/html/2410.04444v1)).

**The axis that matters: who checks the work.** Orthogonal to the tier is the verification mode. A
loop can be self-checked (the model is its own critic), peer-checked (other agents), tool-checked (a
test suite, a retriever, an environment reward), or human-checked (a human-in-the-loop gate). Most
hyped autonomous loops sit at the weak end, self-checked or unchecked. This axis, not the family
label, is the one a governance layer must read, and it is the axis the rest of this paper is built on.

**A secondary axis: cost versus reliability.** The families form a near-monotonic cost frontier. ReAct
is cheap and fragile; reflection adds critic passes; tree search multiplies by the branching factor;
debate multiplies by agents times rounds. Buying reliability costs compute, which makes "how much loop
can this decision justify" a governance variable, and ties the verification question to the materiality
of the decision.

| Tier | Family | Iterated object | What closes the loop | Verification mode |
|---|---|---|---|---|
| Base | Reason-act | Thought + action trace | Model self-declares done | self / tool |
| Base | Reflection / self-refine | The agent's own output | Critic verdict | self |
| Base (variant) | Corrective RAG | Retrieved evidence | Relevance evaluator | tool |
| Composition | Plan-then-execute | A plan | Re-planner / goal met | self |
| Composition | Search (tree) | A tree of trajectories | Value function + budget | tool |
| Composition | Multi-agent / debate | Competing answers | Convergence or vote | peer |
| Wrapper | Autonomous / self-improving | Tasks, skills, or own code | Often undefined | often unchecked |

---

## 3. Failure modes and the open-tooling gap

We rate each failure mode on two axes carried from the taxonomy: which families it hits hardest, and
whether the gap is a *missing-tool* gap (no one has built it) or a *missing-standard* gap (tools exist
but there is no agreed contract for what they should enforce). None of these modes is secret, and
several have partial mitigations; the point is that the mitigations are fragmented, mostly
observational rather than enforcing, and almost none close the loop on the governance axis.

1. **Error compounding.** A loop reasons over its own earlier error and launders the mistake into
   apparent evidence. Multi-turn degradation is measured: top models drop an average of 39 percent from
   single-turn to multi-turn settings over 200,000+ simulated conversations (Laban et al.,
   [arXiv:2505.06120](https://arxiv.org/abs/2505.06120)). In multi-agent pipelines a downstream agent
   treats an upstream hallucination as authoritative, which OWASP carries as ASI08, Cascading Failures
   ([genai.owasp.org](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/)).
   Tracing tools record every step post hoc; none tracks cross-step provenance at runtime.
   *Missing-tool.*

2. **Instability and non-termination.** The loop oscillates or never stops. A structural analysis of 70
   agent implementations names "unbounded recovery loops" as a core weakness
   ([arXiv:2604.11378](https://arxiv.org/abs/2604.11378)); the empirical face is the low success ceiling
   on long-horizon tasks (WebArena, [arXiv:2307.13854](https://arxiv.org/abs/2307.13854)). LangGraph's
   `recursion_limit` is a circuit breaker, not a stopping criterion: a raw step counter cannot tell slow
   progress from a two-state oscillation. *Tool and standard.*

3. **Cost and token runaway.** Every reliability mechanism buys accuracy with compute, and the returns
   diminish: accuracy plateaus exist for greedy, best-of-n, tree search, and majority voting
   ([arXiv:2408.00724](https://arxiv.org/abs/2408.00724)), and multi-agent debate often fails to beat
   single-agent chain-of-thought while consuming far more compute
   ([arXiv:2502.08788](https://arxiv.org/abs/2502.08788)). Token accounting is well served; an online
   diminishing-returns stop tied to stakes is not. *Missing-tool.*

4. **Self-correction that does not reliably work.** The reflection family assumes a model can critique
   and fix its own output. The canonical result is that LLMs cannot reliably improve their own reasoning
   through intrinsic self-correction, and accuracy frequently degrades after a self-correction pass
   (Huang et al., ICLR 2024, [arXiv:2310.01798](https://arxiv.org/abs/2310.01798)); a follow-up shows
   the failure injects human-like bias on complex tasks (Zhang et al., ACL 2025,
   [arXiv:2412.14959](https://arxiv.org/abs/2412.14959)). The honest contrast is that Self-Refine
   reported gains using self-feedback on open-ended generation
   ([arXiv:2303.17651](https://arxiv.org/abs/2303.17651)); we read the two as reconcilable along a
   soft-axis versus hard-axis split, returned to in Section 5, and flag that split as our interpretation,
   not a quoted claim. No tool bars self-critique as the only gate on a hard-correctness task.
   *Missing-standard.*

5. **Evaluation and observability.** A loop can reach the right answer through an unsafe trajectory, or
   get it right once in eight tries. Trajectory debugging is itself unsolved: the best model localized
   the error in a trace only 11 percent of the time (TRAIL,
   [arXiv:2505.08638](https://arxiv.org/abs/2505.08638)). Consistency hides behind averages
   (tau-bench's pass^k, [arXiv:2406.12045](https://arxiv.org/abs/2406.12045)). LLM-as-judge has measured
   self-preference and position biases ([arXiv:2410.21819](https://arxiv.org/abs/2410.21819),
   [arXiv:2406.07791](https://arxiv.org/abs/2406.07791)), which a self-checked loop judged by the same
   model inherits. Trace schemas standardize spans but carry no loop-level semantics (iteration
   boundaries, verification mode, escalation). *Tool and standard.*

6. **Drift.** The same loop behaves differently over time because the model endpoint changed underneath
   it. GPT-4 accuracy on one task fell from 84 to 51 percent across two 2023 snapshots
   ([arXiv:2307.09009](https://arxiv.org/abs/2307.09009)); in regulated financial workflows
   retrieval-augmented tasks drifted by 25 to 75 percent (Khatchadourian and Franco, ICAIF 2025,
   [arXiv:2511.07585](https://arxiv.org/abs/2511.07585)). Drift monitoring built for loop behavior, with
   a re-validation trigger when the model version changes, is missing. *Missing-tool.*

7. **Reward hacking and proxy gaming.** The loop optimizes the proxy it can see. Sycophancy is measured
   across frontier assistants ([arXiv:2310.13548](https://arxiv.org/abs/2310.13548)), and a self-
   improving loop trained on escalating reward-gaming opportunities generalized, a small fraction of the
   time, to rewriting its own reward function (Denison et al.,
   [arXiv:2406.10162](https://arxiv.org/abs/2406.10162)). A check that the critic in a loop is not being
   gamed, enforcing critic-actor independence, is effectively absent from open tooling.
   *Missing-tool.*

8. **No governance or human-in-the-loop standard.** There is no agreed answer to when a loop must stop,
   when a human must approve, and how the loop is sized to materiality. NIST's AI RMF and its generative
   profile give a vocabulary but specify no loop termination or materiality gating
   ([nist.gov](https://www.nist.gov/itl/ai-risk-management-framework),
   [doi.org/10.6028/NIST.AI.600-1](https://doi.org/10.6028/NIST.AI.600-1)). The Cloud Security
   Alliance's draft agentic profile states the gap, that existing frameworks were built for classifiers
   and conversational LLMs, not agents that "initiate irreversible real-world actions"
   ([labs.cloudsecurityalliance.org](https://labs.cloudsecurityalliance.org/agentic/agentic-nist-ai-rmf-profile-v1/)).
   *Missing-standard.*

9. **Reproducibility and safety.** A loop that cannot be replayed cannot be audited, and a tool-using
   loop that ingests external content can be hijacked through it (indirect prompt injection, Greshake et
   al., [arXiv:2302.12173](https://arxiv.org/abs/2302.12173)). A reproducibility contract for loops, and
   a clean separation from the security guards, is missing. *Missing-standard.*

Under a governance lens the recurring missing pieces collapse toward three: a runtime gate that decides
continue, stop, or escalate by progress, cost-versus-accuracy, and materiality; a check that a loop is
not relying on a single self-critic where self-checking is invalid or gameable; and a loop-level
replayable record the first two can read. The most defensible single anchor is the second, because it
rests on a peer-reviewed negative result (mode 4) and direct evidence of self-critic gaming (mode 7).

---

## 4. What already exists: an honest does-it-already-exist pass

This pass goes first among the design steps because it eliminates weak contributions, and the
runtime-governance space moved fast in the year to June 2026. A search of arXiv, GitHub, PyPI, and
vendor documentation in mid-2026 returns a crowded field for the action-governance and telemetry
primitives:

- **AgentSpec** ("Customizable Runtime Enforcement for Safe and Reliable LLM Agents," Wang, Poskitt,
  Sun, ICSE 2026, [arXiv:2503.18666](https://arxiv.org/abs/2503.18666); code at
  [github.com/haoyuwang99/AgentSpec](https://github.com/haoyuwang99/AgentSpec)) is a domain-specific
  language for runtime constraints: triggers, predicates, and enforcement that block unsafe actions
  before they execute.
- **Organizational Control Layer** (Shi et al., June 2026,
  [arXiv:2606.04306](https://arxiv.org/abs/2606.04306)) is a model-agnostic layer that intercepts
  generated actions before execution through policy enforcement and escalation, without modifying the
  generator. It is a very recent preprint and is treated as such.
- **Governance-Aware Agent Telemetry** (Pathak, Jain, April 2026,
  [arXiv:2604.05119](https://arxiv.org/abs/2604.05119)) extends OpenTelemetry with a governance schema,
  real-time policy-violation detection, a graduated-intervention enforcement bus, and cryptographic
  provenance, explicitly to close the "observe-but-do-not-act" gap.
- **Microsoft Agent Control Specification**
  ([commandline.microsoft.com](https://commandline.microsoft.com/agent-control-specification-runtime-governance/))
  is a framework-agnostic controls layer with eight lifecycle interception points, each returning allow,
  warn, deny, or escalate.
- **LangSmith LLM Gateway** ([langchain.com](https://www.langchain.com/blog/introducing-llm-gateway))
  folds runtime policy events into the same workspace as traces, and LangGraph ships a hard
  `recursion_limit` and interrupt-and-approve nodes.
- **OpenTelemetry GenAI semantic conventions**
  ([opentelemetry.io](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/)) define
  invoke-agent and execute-tool spans for non-deterministic loops; as of mid-2026 the conventions have
  moved to a dedicated repository and are still evolving.

Read together these converge on one pattern: intercept the action at a lifecycle point, evaluate a
policy, return allow, warn, deny, or escalate, optionally tier the autonomy, and record telemetry and
provenance. The generic action-governance firewall is therefore occupied, by both open research and a
major vendor. The generic governance trace schema plus provenance is substantially occupied. Proposing
either as an original contribution in mid-2026 would not survive a knowledgeable reader.

**What none of them does.** Every entrant gates the action: is this tool call, this output, this state
change allowed. None asks whether the loop's verification *structure* is epistemically valid for the
decision it is about to make. Microsoft's own write-up scopes its specification to action-lifecycle
interception, calling it "a controls layer, not an agent framework" that "does not orchestrate the
loop, choose tools, or manage memory"; it is silent on verification adequacy. A search of PyPI and
GitHub for a packaged verification-mode or critic-independence contract returns architecture patterns
and blog advice (generator-critic dyads, "verification independence," complementary epistemic
constraints) but no portable enforced artifact. The one slice of the trace-schema space that is not
occupied is a *verification-mode* attribute on those spans, which none of the telemetry entrants
carries today, and which is exactly the substrate the next section needs. The verification-validity
primitive is the one still open, and it is the one anchored to the strongest evidence in the survey.

---

## 5. The verification-adequacy contract

**Working name (provisional).** The Verification Adequacy Contract, with a small reference guard.

**The claim.** A loop's verification mode must be adequate for the decision's task type and
materiality, and a self-only mode is not adequate as the sole gate on a hard-correctness,
high-materiality decision. The contract makes that requirement explicit, machine-readable, and
enforceable around any existing loop, and the action-governance layers in Section 4 do not.

The contract has three parts, in order of how load-bearing each is.

**5.1 Verification-mode tagging at the loop level.** Each loop or sub-loop is annotated with which mode
closes it: self, peer, tool, or human (Section 2). This promotes the taxonomy column to a runtime tag.
It is a loop-level semantic that neither the OpenTelemetry GenAI spans nor the action-firewalls carry
today; they see tool calls and outputs, not "this iteration was closed by the model judging itself."
The tag is the cheapest part and the precondition for the other two, and it is the unoccupied slice of
the telemetry space identified in Section 4.

**5.2 A two-axis classification of the decision.** Task type on one axis: *soft* (open-ended generation
with subjective quality, where self-feedback measurably helps, per Self-Refine,
[arXiv:2303.17651](https://arxiv.org/abs/2303.17651)) versus *hard-correctness* (a checkable, costly-to-
get-wrong answer, where intrinsic self-correction is unreliable or backfires, per Huang et al.,
[arXiv:2310.01798](https://arxiv.org/abs/2310.01798)). Materiality on the other: reversible-and-cheap
versus costly-and-hard-to-reverse. The soft-versus-hard split is our reading of Huang et al. against
Madaan et al., not a quoted claim from either, and is treated as a judgment axis with the limits
discussed in 5.4 and Section 7.

**5.3 One enforced rule.** A self-only verification mode is refused as the *sole* gate on a decision
classified hard-correctness and high-materiality. The loop must then add an independent check (a
cross-model critic, a held-out verifier, a tool or test oracle, or a human gate) or escalate. We resist
adding a second or third rule on purpose: the single rule is the one with peer-reviewed backing, and a
thin enforced contract is more defensible and more adoptable than a broad policy engine competing
head-on with the action-firewalls.

The guard is deterministic and carries no model in its routing path:

```
function adequacy_gate(decision):
    mode        = verification_mode(decision)            # self | peer | tool | human
    task, matl  = classify(decision)                     # see 5.4 for the default
    if mode == self and task == hard_correctness and matl == high:
        if has_independent_check(decision):              # cross-model | held-out | tool | human
            return ALLOW
        return REQUIRE_INDEPENDENT_CHECK or ESCALATE
    return ALLOW
```

**Why this is not the action-firewall.** AgentSpec, the Organizational Control Layer, and the Microsoft
specification answer "may this action run." The contract answers "is the judgment that approved this
action allowed to stand on its own." A loop can pass every action-policy and still be governed only by
a model grading its own work on a task the literature says it cannot grade. The firewall gates the act;
the contract gates the epistemics of the verification, a distinct question the action-policy layers do
not currently encode. They could express it only if a verification-mode tag like 5.1 existed, which
today it does not, so the load-bearing novelty is that tag and the rule it enables, not a claim that the
two are geometrically orthogonal.

**5.4 The scope of the task-type axis, stated honestly.** Deciding whether a decision is
hard-correctness can be as hard as the task itself, which threatens an infinite regress. The regress is
closed by construction, not by assuming the classifier is reliable: any decision that cannot be
confidently classified falls to the conservative default and is treated as hard-correctness and
high-materiality, so an unclassifiable decision is covered by demanding an independent check, never
waved through. This raises the honest tension: if the default is conservative and classification is
unreliable, does the two-axis split do any work, or does the contract collapse into "always require an
independent check"? The axis earns its place only on the *confidently-classifiable* fraction, where it
prevents false-positive over-escalation on cheap, reversible, soft tasks that would otherwise be forced
through a costly independent check or a human gate. The claim the contract must stand behind is that
this confidently-soft-and-low fraction is non-trivial in real loops. If it is empty, the axis is
decoration and the contract reduces to "always require an independent check", a weaker but still honest
fallback. The default covers only the unclassifiable residue.

**5.5 The runner-up, and why it loses.** The natural second candidate is a semantic loop-controller:
online oscillation detection and a diminishing-returns stop (Section 3, modes 2 and 3). It is real and
useful, and it appears in this paper as the obvious extension. It loses to the verification-adequacy
contract on three counts. It is more crowded (LangGraph's `recursion_limit` is the crude version,
AgentBoard's progress-rate metric ([arXiv:2401.13178](https://arxiv.org/abs/2401.13178)) the offline
version). It rests on a plateau being detectable, not on a peer-reviewed negative result that the
dominant practice is unsound. And it composes less cleanly with a model-risk reference whose whole
thesis is about who checks the work, not about when to stop iterating.

---

## 6. A reference instantiation in model risk

A contribution that stands alone as a position is weaker than one with a worked instantiation, so we
show the contract's prescribed end-state realized in a domain where "costly" is not a hypothetical.

In model-risk management, a validation gate scores a candidate model's outputs (discrimination,
calibration, stability, backtesting) against fixed statistical policy and routes the result to pass,
human review, or a hard block. A deterministic, model-free gate of this kind is, by construction, an
independent, non-self verifier of a hard-correctness, high-materiality decision: the model being
validated and the verifier are never the same entity, and the verifier carries no language model in its
routing path. It is therefore not an instance of a loop refusing its own self-critique, because there
is no self-critic in its path to refuse. It is a worked instance of the *end-state the contract
recommends*: independent verification on exactly the class of decision where the contract forbids a
self-only gate.

The honest seam, stated rather than hidden, is that such a gate demonstrates the prescribed independent
verifier, not the self-critique-refusal trigger firing. The trigger is the general mechanism for a
generic agentic loop that has no external gate; the model-risk gate is what compliance with the
contract looks like once the independent verifier is in place. The relationship is therefore one of
generalization and instantiation, not duplication: the contract is the domain-agnostic statement, and a
model-risk validation system is its finance reference application. This is also why the contribution is
a survey-and-position paper that points at such a system, rather than a competing system of its own.

The narrative is single and tight: agentic loops are shipping with self-checking as their only gate;
here is a verification-adequacy contract that refuses that where being wrong is costly, and here is what
compliance looks like in a regulated, real-money domain.

---

## 7. Limitations and threats to validity

- **The contract is unvalidated, by design at this stage.** The negative results (modes 4 and 7) and
  the measured judge biases (mode 5) establish that the *problem* is real. They do not establish that a
  contract enforcing an independent check improves outcomes. The contract is a specification and a
  reference guard, a falsifiable mechanism, not a proof of loop correctness. An empirical study, loops
  with and without the contract on a hard-correctness benchmark, is the obvious next step and is not
  claimed here.
- **The novelty is the contract, not the observation.** That self-critique is weak and that an
  independent critic catches more errors are both well known; generator-critic dyads are buildable in
  any multi-agent framework. The contribution is the portable, enforced, task-and-materiality-aware
  contract and the verification-mode tag that makes it expressible, neither of which is shipped. If a
  reader still reads this as incremental, the contribution degrades to a clean specification and
  reference implementation, which is a smaller but still honest claim. This is the load-bearing risk and
  it is named, not hidden.
- **The task-type axis is a judgment call.** The whole rule pivots on classifying a decision as
  hard-correctness, and that classification is our reading of the literature, not a measured boundary.
  Section 5.4 closes the regress with a conservative default and states the circularity tension; we do
  not claim the axis is empirically validated.
- **"Not packaged anywhere" is a coverage claim, not a proof.** Section 4 rests on a mid-2026 search of
  arXiv, GitHub, PyPI, and the named vendor docs. It is reproducible and stated as a search result; it
  is not a proof that nothing exists in any private or unindexed form. The closest adjacent systems
  (tool-interactive critiquing, safety-policy guardrail agents, formal property checking) gate actions
  or check outputs; none enforces a verification-mode-by-task-type-by-materiality contract.
- **The field will keep moving.** The action-governance space added several entrants in the year to
  mid-2026, so the open slice could close before a reference implementation matures. The mitigation is
  that the contract is thin and fast to build, and that even if an entrant adds a verification-mode
  check, the distinct-question framing and the worked model-risk reference still stand.
- **Reported numbers are as published.** The 39 percent multi-turn drop, the 11 percent TRAIL
  localization, the drift percentages, and the rest are the authors' figures on their own datasets,
  cited as evidence the modes are real and measured, not as universal constants.

---

## 8. Conclusion

The loop is the unit of analysis in agentic AI, and the axis that matters for governance is who checks
the work. The failure-mode survey shows the weak point concentrating in self-checked and autonomous
loops, backed by a peer-reviewed negative result that self-correction is unreliable on hard-correctness
tasks. The does-it-already-exist pass shows that the broad governance-firewall reading of that gap was
filled by others in the last year, and that the narrow, evidence-anchored reading remains open: no
shipped tool enforces that a self-only verification mode may not be the sole gate where being wrong is
costly. We proposed a verification-adequacy contract that occupies that slice, made it concrete enough
to build, stated its limits, and showed a deterministic model-risk validation gate as a worked instance
of the independent-verification end-state it recommends. The contract is a specification, not a proof,
and its empirical evaluation is the next step.

---

## References

Loop families and failure modes:
- Yao et al., ReAct: [arXiv:2210.03629](https://arxiv.org/abs/2210.03629)
- Madaan et al., Self-Refine: [arXiv:2303.17651](https://arxiv.org/abs/2303.17651)
- Shinn et al., Reflexion: [arXiv:2303.11366](https://arxiv.org/abs/2303.11366)
- Wang et al., Plan-and-Solve: [arXiv:2305.04091](https://arxiv.org/abs/2305.04091)
- Zhou et al., LATS: [arXiv:2310.04406](https://arxiv.org/abs/2310.04406)
- Du et al., Multiagent Debate: [arXiv:2305.14325](https://arxiv.org/abs/2305.14325)
- Multi-agent debate controlled study: [arXiv:2511.07784](https://arxiv.org/abs/2511.07784)
- Wang et al., Voyager: [arXiv:2305.16291](https://arxiv.org/abs/2305.16291)
- Gödel Agent: [arXiv:2410.04444](https://arxiv.org/html/2410.04444v1)
- Agentic RL survey: [arXiv:2509.02547](https://arxiv.org/abs/2509.02547)
- Agentic RAG survey: [arXiv:2506.10408](https://arxiv.org/html/2506.10408v1)
- Laban et al., Lost in Multi-Turn: [arXiv:2505.06120](https://arxiv.org/abs/2505.06120)
- From Agent Loops to Structured Graphs: [arXiv:2604.11378](https://arxiv.org/abs/2604.11378)
- Zhou et al., WebArena: [arXiv:2307.13854](https://arxiv.org/abs/2307.13854)
- Wu et al., Inference Scaling Laws: [arXiv:2408.00724](https://arxiv.org/abs/2408.00724)
- Zhang et al., Stop Overvaluing Multi-Agent Debate: [arXiv:2502.08788](https://arxiv.org/abs/2502.08788)
- Huang et al., LLMs Cannot Self-Correct Reasoning Yet (ICLR 2024): [arXiv:2310.01798](https://arxiv.org/abs/2310.01798)
- Zhang et al., Dark Side of Intrinsic Self-Correction (ACL 2025): [arXiv:2412.14959](https://arxiv.org/abs/2412.14959)
- Deshpande et al., TRAIL: [arXiv:2505.08638](https://arxiv.org/abs/2505.08638)
- Yao et al., tau-bench: [arXiv:2406.12045](https://arxiv.org/abs/2406.12045)
- Ma et al., AgentBoard (NeurIPS 2024): [arXiv:2401.13178](https://arxiv.org/abs/2401.13178)
- Self-preference bias in LLM-as-judge: [arXiv:2410.21819](https://arxiv.org/abs/2410.21819)
- Position bias in LLM-as-judge: [arXiv:2406.07791](https://arxiv.org/abs/2406.07791)
- Chen, Zaharia, Zou, ChatGPT behavior over time: [arXiv:2307.09009](https://arxiv.org/abs/2307.09009)
- Khatchadourian and Franco, LLM Output Drift (ICAIF 2025): [arXiv:2511.07585](https://arxiv.org/abs/2511.07585)
- Sharma et al., Sycophancy: [arXiv:2310.13548](https://arxiv.org/abs/2310.13548)
- Denison et al., Sycophancy to Subterfuge: [arXiv:2406.10162](https://arxiv.org/abs/2406.10162)
- Greshake et al., Indirect Prompt Injection (AISec 2023): [arXiv:2302.12173](https://arxiv.org/abs/2302.12173)

Governance and runtime-control landscape:
- Wang, Poskitt, Sun, AgentSpec (ICSE 2026): [arXiv:2503.18666](https://arxiv.org/abs/2503.18666)
- Shi et al., Organizational Control Layer: [arXiv:2606.04306](https://arxiv.org/abs/2606.04306)
- Pathak, Jain, Governance-Aware Agent Telemetry: [arXiv:2604.05119](https://arxiv.org/abs/2604.05119)
- Microsoft Agent Control Specification: [commandline.microsoft.com](https://commandline.microsoft.com/agent-control-specification-runtime-governance/)
- LangSmith LLM Gateway: [langchain.com](https://www.langchain.com/blog/introducing-llm-gateway)
- OpenTelemetry GenAI semantic conventions: [opentelemetry.io](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/)
- NIST AI RMF: [nist.gov](https://www.nist.gov/itl/ai-risk-management-framework); GenAI profile: [doi.org/10.6028/NIST.AI.600-1](https://doi.org/10.6028/NIST.AI.600-1)
- CSA Agentic NIST AI RMF profile (draft): [labs.cloudsecurityalliance.org](https://labs.cloudsecurityalliance.org/agentic/agentic-nist-ai-rmf-profile-v1/)
- OWASP Top 10 for Agentic Applications: [genai.owasp.org](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/)

---

*Source artifacts: the three-day study in `research/agentic-loops/daily/` (DAY-01 taxonomy, DAY-02
failure modes, DAY-03 contribution scope). The finance reference application is the separate
model-risk-agents project. Personal capacity, industry-level; no employer internals or figures.*
