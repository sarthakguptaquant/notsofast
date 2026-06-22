# DAY 03: Scope the public contribution, adversarially vetted

**Date:** 2026-06-17. Personal capacity, industry-level. Zero employer internals.
**Deliverable:** one defensible, solo-buildable, free public contribution that fills a real
loop-tooling gap, anchored to the governance thesis (adversarially validated, human-in-the-loop,
materiality-gated loops). Each candidate is run through a does-it-already-exist, buildable,
contribution-significance, and composes-with-the-flagship pass. The artifact ends on a go / no-go.

---

## 0. What Day 1 and Day 2 leave on the table

Day 1 mapped the loop families and isolated the axis that matters for governance: *who checks the
work*, self / peer / tool / human, with most shipped autonomous loops sitting at the weak end
(self-checked or unchecked). Day 2 turned nine failure modes into a gap table and named the single
most defensible anchor: there is a peer-reviewed negative result that intrinsic self-correction is
unreliable on hard-correctness tasks (Huang et al., ICLR 2024,
[arXiv:2310.01798](https://arxiv.org/abs/2310.01798)), the follow-up that it can actively inject bias
(Zhang et al., ACL 2025, [arXiv:2412.14959](https://arxiv.org/abs/2412.14959)), direct evidence that
a self-improving loop can game its own critic (Denison et al.,
[arXiv:2406.10162](https://arxiv.org/abs/2406.10162)), and measured self-preference and position bias
in LLM-as-judge ([arXiv:2410.21819](https://arxiv.org/abs/2410.21819),
[arXiv:2406.07791](https://arxiv.org/abs/2406.07791)), yet no open tool enforces "do not let a
self-critic be the only gate when being wrong is costly."

Day 2 section 11 grouped the gaps into three would-be primitives: (a) a runtime gate that decides
continue / stop / escalate by progress, cost-vs-accuracy, and materiality; (b) a check that a loop is
not relying on a single self-critic where self-checking is invalid or gameable; (c) a loop-level
replayable trajectory record the first two can read. Day 3's job is to decide which of these is still
genuinely open in mid-2026, scope it, and decide whether to build.

---

## 1. The does-it-already-exist pass, run first and honestly

This is the pass that kills weak contributions, so it goes first. The runtime-governance space moved
fast in the twelve months to June 2026, and a Day-2 reader who skipped this would have proposed a
me-too. Searching arXiv, GitHub, PyPI, and vendor docs in June 2026 returns a crowded field for
primitives (a) and (c):

- **AgentSpec** ("Customizable Runtime Enforcement for Safe and Reliable LLM Agents," Wang, Poskitt,
  Sun, ICSE 2026, [arXiv:2503.18666](https://arxiv.org/abs/2503.18666); code at
  [github.com/haoyuwang99/AgentSpec](https://github.com/haoyuwang99/AgentSpec)) is a domain-specific
  language for runtime constraints on LLM agents: triggers, predicates, and enforcement that block
  unsafe actions before they execute, demonstrated on code, embodied, and driving agents. This is a
  machine-readable action-policy layer, open and published.
- **Organizational Control Layer** (Shi et al., June 3 2026,
  [arXiv:2606.04306](https://arxiv.org/abs/2606.04306)) is a model-agnostic layer that intercepts
  generated actions before execution through policy enforcement and escalation, without modifying the
  underlying LLM generator, with reported large drops in unsafe executions. It is a very recent
  preprint, posted days before this writing, so it is treated as fresh and not yet settled.
- **Governance-Aware Agent Telemetry** (Pathak, Jain, April 6 2026,
  [arXiv:2604.05119](https://arxiv.org/abs/2604.05119)) extends OpenTelemetry with a governance
  schema, real-time policy-violation detection, a graduated-intervention enforcement bus, and
  cryptographic provenance, explicitly to close the "observe-but-do-not-act" gap.
- **Microsoft Agent Control Specification**
  ([commandline.microsoft.com](https://commandline.microsoft.com/agent-control-specification-runtime-governance/))
  is a framework-agnostic controls layer with eight lifecycle interception points, each returning
  allow / warn / deny / escalate, portable across Python, Node, .NET, and Rust.
- **LangSmith LLM Gateway**
  ([langchain.com](https://www.langchain.com/blog/introducing-llm-gateway)) folds runtime policy
  events into the same workspace as traces and evaluations.
- **OpenTelemetry GenAI semantic conventions**
  ([opentelemetry.io](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/)) define
  invoke-agent and execute-tool spans built for non-deterministic loops. As of mid-2026 the GenAI
  conventions have moved to a dedicated OpenTelemetry GenAI repository and the older spec page is no
  longer maintained there, so they are still actively evolving rather than stable.
- **LangGraph** ships a hard `recursion_limit` and interrupt-and-approve nodes
  ([docs.langchain.com](https://docs.langchain.com/oss/python/langgraph/errors/GRAPH_RECURSION_LIMIT)).

Read together, these converge on one pattern: intercept the *action* at a lifecycle point, evaluate a
policy, return allow / warn / deny / escalate, optionally tier the autonomy, and record telemetry and
provenance. Primitive (a) as a generic action-governance firewall is therefore **occupied**, by both
open research (OCL, AgentSpec) and a major vendor (Microsoft). The *generic* governance trace schema
plus provenance of primitive (c) is **substantially occupied** by GAAT and the maturing OTel GenAI
conventions. The one slice of (c) that is not occupied is the same slice as the contribution below: a
*verification-mode* attribute on those spans, which none of them carries today. Proposing the broad
versions of (a) or (c) as an original contribution in mid-2026 would not survive a knowledgeable reader.
That is the honest result, and it eliminates two of the three Day-2 primitives.

**What none of them does.** Every entrant above gates the *action*: is this tool call, this output,
this state change allowed. None of them asks whether the loop's *verification structure* is
epistemically valid for the decision it is about to make. Microsoft's own write-up scopes ACS to
action-lifecycle interception: it calls ACS "a controls layer, not an agent framework" that "does not
orchestrate the loop, choose tools, or manage memory." The page is silent on verification adequacy. It
offers no mechanism to validate whether a verification method like self-critique is appropriate for a
given task type, which is an absence rather than an explicit disclaimer, but it leaves the question
unaddressed all the same. A June-2026 search of PyPI and GitHub for a packaged verification-mode or
critic-independence
contract returns architecture patterns and blog advice (generator-critic dyads, "verification
independence," complementary epistemic constraints) but no portable enforced artifact. Primitive (b),
the verification-validity check, is the one of the three still open, and it is the one anchored to the
strongest *motivating* evidence in the whole study (evidence that the problem is real, not yet
evidence that any contract fixes it).

---

## 2. The surviving contribution: a verification-adequacy contract

**Working name (provisional):** the Verification Adequacy Contract, with a small reference guard.
Sober name on purpose; the flagship names things plainly and this should match.

**The one-line claim.** A loop's verification mode (self / peer / tool / human, the Day-1 axis) must
be adequate for the decision's task type and materiality, and a self-only mode is not adequate as the
sole gate on a hard-correctness, high-materiality decision. The contract makes that requirement
explicit, machine-readable, and enforceable around any existing loop, and the action-governance layers
above do not.

**What it is, concretely.** Three parts, in order of how load-bearing each is.

1. **Verification-mode tagging at the loop level.** Each loop or sub-loop is annotated with which
   verification mode actually closes it. This is the Day-1 taxonomy column promoted to a runtime tag.
   It is a loop-level semantic that neither the OTel GenAI spans nor the action-firewalls carry today;
   they see tool calls and outputs, not "this iteration was closed by the model judging itself." This
   is the cheapest part and the precondition for the other two.

2. **A two-axis classification of the decision.** Task type on one axis: *soft* (open-ended
   generation with subjective quality, where self-feedback measurably helps, per Self-Refine,
   [arXiv:2303.17651](https://arxiv.org/abs/2303.17651)) versus *hard-correctness* (a checkable,
   costly-to-get-wrong answer, where intrinsic self-correction is unreliable or backfires, per Huang
   et al.). Materiality on the other axis: reversible-and-cheap versus costly-and-hard-to-reverse. The
   soft-versus-hard split is this study's reading of Huang et al. against Madaan et al., flagged as an
   interpretation in Day 2 section 12 and carried with the same caveat here.

3. **One enforced rule, and only one.** A self-only verification mode is refused as the *sole* gate on
   a decision classified hard-correctness and high-materiality. The loop must then add an independent
   check (a cross-model critic, a held-out verifier, a tool or test oracle, or a human gate) or
   escalate. Resisting the urge to add a second or third rule is deliberate: the single rule is the one
   with peer-reviewed backing, and a thin enforced contract is more defensible and more adoptable than
   a broad policy engine competing head-on with AgentSpec and OCL.

**Why this is not the action-firewall again.** AgentSpec, OCL, and ACS answer "may this action run."
This answers "is the *judgment* that approved this action allowed to stand on its own." A loop can pass
every action-policy and still be governed only by a model grading its own homework on a task the
literature says it cannot grade. The firewall gates the act; the adequacy contract gates the epistemics
of the verification, a distinct question the action-policy layers do not currently encode. They could
express it only if a verification-mode tag like part 1's existed, which today it does not, so the
load-bearing novelty is that tag and the rule it enables, not a claim that the two are geometrically
orthogonal. That distinction, and the tag that makes it expressible, is the contribution's whole
defensibility.

---

## 3. The runner-up, and why it loses

The natural second candidate is a **semantic loop-controller**: online oscillation detection (the
loop ping-ponging between two failing states) and a diminishing-returns stop (accuracy has plateaued
while tokens keep flowing, detectable in principle per the inference-scaling result,
[arXiv:2408.00724](https://arxiv.org/abs/2408.00724)). It is real and useful. It loses to the
verification-adequacy contract on three counts. It is more crowded: LangGraph's `recursion_limit` is
the crude version, AgentBoard's progress-rate metric ([arXiv:2401.13178](https://arxiv.org/abs/2401.13178))
is the offline version, and adaptive-compute methods exist in the research literature, so the
contribution would be "package an online detector," a smaller delta. It is weaker on evidence: it rests
on a plateau being detectable, not on a peer-reviewed negative result that the dominant practice is
unsound. And it composes less cleanly with the flagship, whose entire thesis is about *who checks the
work*, not *when to stop iterating*. It is worth one paragraph in the eventual write-up as the obvious extension,
not the headline.

---

## 4. The four passes on the chosen contribution

**Pass 1, does it already exist.** Run in section 1. The action-governance and telemetry primitives
are occupied; the verification-adequacy / critic-independence primitive is not packaged as a portable
enforced contract, confirmed against AgentSpec, OCL, GAAT, ACS, LangSmith Gateway, OTel GenAI, and a
PyPI / GitHub sweep, each of which scopes itself to action interception or telemetry and does not speak
to verification adequacy. The principle (do not let the
critic share the actor's blind spot) is well known; the enforced, task-and-materiality-aware contract
is not shipped. **Verdict: open, narrowly and defensibly.**

**Pass 2, buildable by one person, free.** Yes. Part 1 is annotation plus an OTel-compatible span
attribute. Part 2 is a small classifier interface with conservative defaults (unknown task type
defaults to hard-correctness, unknown materiality defaults to high, so the safe action is to *demand*
an independent check, never to wave a decision through). Part 3 is a guard that inspects the declared
verification mode against the classification and raises a deterministic refusal or escalation, exactly
the shape of the flagship's `evaluate_gate`: a severity decision over typed inputs, no model in the
routing path. A v1 wrapping one or two open frameworks (LangGraph, plain LangChain) is a few hundred
lines plus tests plus a documented spec. No paid dependency, no hosted service, standard library plus
numpy in the flagship's style. **Verdict: buildable, free, solo.**

**Pass 3, contribution significance, will it earn genuine attention.** This is the pass that justifies
the effort. The contribution sits on the strongest *motivating* evidence in the three-day study (a
peer-reviewed negative result plus a reward-tampering result plus measured judge bias): that
establishes the problem is real, not that this contract solves it. It occupies a gap the fast-moving
governance field left open and that the named action-governance specs do not address (they scope
themselves to action interception and are silent on verification adequacy), and it reframes a known
architecture pattern (generator-critic dyads) as an enforceable contract with a clear rule. The honest
ceiling is stated plainly: the contract is an unvalidated but falsifiable mechanism, a specification
and a reference guard, not a proof of loop correctness, and the soft-versus-hard task classification is
a judgment axis that will need defensible defaults and will be contestable at the margin. Within that ceiling it is a clean, citable,
original artifact that a practitioner can adopt and a reviewer can check. **Verdict: significant within
a stated and honest scope.**

**Pass 4, composes with the flagship.** This is the decisive pass, because the binding rule is one
coherent story, not a scattered third repo. The flagship's thesis note (`THESIS-assumption-risk.md`)
argues you cannot calibrate confidence over an API-hosted agent and that the safe design is an
external, standing adversarial critic plus a deterministic gate, never the model judging itself. The
flagship's `ValidationGate` is a deterministic, LLM-free verifier for VaR, credit, and reserving
models: it scores stored statistics with a fixed policy, with no model in the routing path. It is
therefore not an instance of a loop refusing its own self-critique, because there is no LLM self-critic
in its path to refuse. It is a worked instance of the *end-state the contract recommends*: independent,
non-self verification on a hard-correctness, high-materiality decision, in a domain where "costly" is a
regulated, real-money fact. The honest seam, stated rather than hidden: the contract's self-critique-
refusal trigger is the general mechanism for a generic loop that has no such external gate; the
flagship demonstrates the prescribed independent verifier, not the trigger firing. The narrative is
still single and tight: agentic loops are shipping with self-checking as their only gate; here is a
verification-adequacy contract that refuses that where being wrong is costly, and here is a worked
reference implementation in model risk of what compliance with it looks like. **Verdict: composes as a
worked reference application, with one honest seam; strengthens the flagship rather than forking from
it.**

---

## 5. v1 scope and PR plan

Scope kept deliberately thin, so it ships and so it does not drift into competing with the
action-firewalls.

- **The spec (front matter).** A short written contract: the verification-mode vocabulary (self /
  peer / tool / human, from Day 1), the two-axis classification, the single enforced rule, the
  conservative defaults, and an explicit non-goals section (it does not gate actions, that is what
  AgentSpec / OCL / ACS do; it does not prove correctness; it does not produce a calibrated confidence
  number, per the flagship thesis). The agentic-loops Day-1 and Day-2 artifacts become its cited
  background.
- **The reference guard (code).** A framework-agnostic core: a `VerificationMode` tag, a
  `classify(decision) -> (task_type, materiality)` interface with safe defaults, and an
  `adequacy_gate` that returns allow / require-independent-check / escalate, mirroring the flagship's
  severity-join shape and staying LLM-free on the routing path. Plus one adapter (LangGraph) so it is
  demonstrably real, with tests in the flagship's deterministic, replayable style.
- **Where it lives.** As a generic core module that the flagship's `monitor_gate` /
  `human_review` path can be shown to satisfy, with the finance system as the canonical worked
  example. One repo, one story.
- **PR plan if upstreaming is ever pursued (later, optional).** The natural homes are an OTel GenAI
  semantic-convention proposal for a verification-mode span attribute (the conventions are actively
  evolving in their dedicated repository, so a well-argued attribute proposal is plausibly in scope,
  status to re-confirm against the live repo first) and a small adapter PR to an agent framework.
  Both are deferred; v1 stands alone and is staged locally for review first. No external publishing in
  this track without sign-off.

---

## 6. Go / no-go

**Go, on the verification-adequacy contract, as the generic core of the existing flagship rather than
a new standalone repo.** The reasoning is the four passes: the gap is open where the rest of the field
is crowded, it is solo-buildable and free, it rests on the strongest evidence in the study *for the
problem*, and it is the abstraction whose prescribed end-state the flagship's deterministic gate
already demonstrates in one domain. The runner-up loop-controller is a
no-go as a headline and a yes as a one-paragraph future extension. The single largest risk to the
contribution is not technical but framing: overclaiming originality on the *observation* that
self-critique is weak (that is well documented) instead of on the *enforced, task-and-materiality-aware
contract* (that is not shipped). The write-up must lead with the contract and the rule, cite the
negative results as motivation, and credit the action-governance entrants explicitly so the distinct
question, and the verification-mode tag that makes it expressible, is the headline, not a hidden
assumption.

---

## 7. Adversarial self-review

- **Citation accuracy.** New IDs introduced today were fetched to their live abstract pages and
  checked for matching title, authors, and finding before commit: 2503.18666 (AgentSpec, Wang /
  Poskitt / Sun, with a live GitHub repo), 2606.04306 (Organizational Control Layer, Shi et al., June
  3 2026, action interception before execution), 2604.05119 (Governance-Aware Agent Telemetry, Pathak
  and Jain, April 6 2026, OTel extension plus enforcement bus). The Microsoft Agent Control
  Specification and OTel GenAI conventions are official vendor / project pages. All Day-1 and Day-2 IDs
  reused here were verified on their own days and are not re-cited as new.
- **The strongest objection, stated.** "This is just the generator-critic / LLM-as-judge-with-a-second-model
  pattern with a coat of paint." Answer: the pattern is indeed known and buildable in any multi-agent
  framework, which is conceded in section 1. The contribution is not the pattern; it is the portable,
  enforced contract that *requires* an independent check as a function of task type and materiality,
  refuses a self-only gate where being wrong is costly, and sits in a gap the action-governance specs
  do not address (they scope themselves to action interception and are silent on verification
  adequacy). If a reader still reads that as
  incremental, the contribution degrades to a clean spec and reference implementation, which is a
  smaller but still honest claim. This is the load-bearing risk and it is named, not hidden.
- **The soft-versus-hard axis is a judgment call, and the classification is itself a verification act.**
  The whole rule pivots on classifying a decision as hard-correctness, and that classification is this
  study's reading of the literature, not a measured boundary. Worse, deciding "is this hard-correctness"
  can be as hard as the task itself, which threatens an infinite regress. The regress is closed by
  construction, not by assuming the classifier is reliable: any decision that cannot be confidently
  classified falls to the conservative default and is treated as hard-correctness and high-materiality,
  so an unclassifiable decision is covered by demanding an independent check, never waved through. That
  raises the honest tension: if the default is conservative and classification is unreliable, does the
  two-axis split do any work, or does the contract collapse into "always require an independent check".
  The axis earns its place only on the *confidently-classifiable* fraction, where it prevents
  false-positive over-escalation on cheap, reversible, soft tasks (open-ended generation where
  self-feedback measurably helps, per Self-Refine) that would otherwise be forced through a costly
  independent check. The claim the contract must stand behind is that this confidently-soft-and-low
  fraction is non-trivial in real loops; if it is empty, the axis is decoration and the contract reduces
  to "always require an independent check," a weaker but still honest fallback. The default handles only
  the uncertain residue.
- **"Not packaged anywhere" is a coverage claim, not a proof.** Section 1 rests on a June-2026 search
  of arXiv, GitHub, PyPI, and the named vendor docs. It is reproducible and stated as a search result,
  so it can be re-run before anything is published; it is not a proof that nothing exists in any
  private or unindexed form.
- **The field will keep moving.** The action-governance space added several entrants in the year to
  mid-2026, so the verification-adequacy gap could close before a v1 ships. The mitigation is that the
  contribution is thin and fast to build, and that even if an entrant adds a verification-mode check,
  the distinct-question framing and the worked model-risk reference still stand.
- **Public-safety pass.** Generic, industry-level throughout. No employer internals, data, or figures;
  no reference to any personal campaign, immigration matter, or the scheduling machinery that produced
  this. The contribution is framed solely as a general agentic-AI-governance artifact that composes
  with the public model-risk-agents repo. No em dashes, no exclamation points.

---

## 8. Through-line: the three-day study, closed

Day 1 found the axis (who checks the work). Day 2 found the evidence (self-checking is unreliable on
hard-correctness tasks, and the gate that should catch this is missing). Day 3 found that the broad
governance-firewall reading of that gap was closed by other people in the last year, and that the
narrow, evidence-anchored reading, a verification-adequacy contract that refuses self-only gating
where being wrong is costly, is still open, and that the model-risk flagship's deterministic gate is a
worked example of the independent-verification end-state the contract recommends. The recommendation is
to build that contract, as the flagship's generic core, not as a third repo. Staged locally for review;
nothing publishes without sign-off.

---

## Sources

New for Day 3:
- AgentSpec (Wang, Poskitt, Sun): [arXiv:2503.18666](https://arxiv.org/abs/2503.18666); code
  [github.com/haoyuwang99/AgentSpec](https://github.com/haoyuwang99/AgentSpec)
- Organizational Control Layer (Shi et al.): [arXiv:2606.04306](https://arxiv.org/abs/2606.04306)
- Governance-Aware Agent Telemetry (Pathak, Jain): [arXiv:2604.05119](https://arxiv.org/abs/2604.05119)
- Microsoft Agent Control Specification: [commandline.microsoft.com](https://commandline.microsoft.com/agent-control-specification-runtime-governance/)
- LangSmith LLM Gateway: [langchain.com](https://www.langchain.com/blog/introducing-llm-gateway)
- OpenTelemetry GenAI agent spans: [opentelemetry.io](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/)
  (this page notes the GenAI conventions have moved to a dedicated OpenTelemetry GenAI repository as of mid-2026; re-source from the new repo before any PR)

Carried from Days 1 and 2 (verified on their own days):
- LLMs Cannot Self-Correct Reasoning Yet (ICLR 2024): [arXiv:2310.01798](https://arxiv.org/abs/2310.01798)
- Dark Side of Intrinsic Self-Correction (ACL 2025): [arXiv:2412.14959](https://arxiv.org/abs/2412.14959)
- Self-Refine (NeurIPS 2023): [arXiv:2303.17651](https://arxiv.org/abs/2303.17651)
- Sycophancy to Subterfuge (reward-tampering): [arXiv:2406.10162](https://arxiv.org/abs/2406.10162)
- Self-preference bias in LLM-as-judge: [arXiv:2410.21819](https://arxiv.org/abs/2410.21819)
- Position bias in LLM-as-judge: [arXiv:2406.07791](https://arxiv.org/abs/2406.07791)
- Inference Scaling Laws: [arXiv:2408.00724](https://arxiv.org/abs/2408.00724)
- AgentBoard (NeurIPS 2024): [arXiv:2401.13178](https://arxiv.org/abs/2401.13178)
- LangGraph recursion limit: [docs.langchain.com](https://docs.langchain.com/oss/python/langgraph/errors/GRAPH_RECURSION_LIMIT)

Flagship cross-reference:
- `research/model-risk-agents/THESIS-assumption-risk.md` (you cannot calibrate confidence over an
  API-hosted agent; external standing critic plus deterministic gate)
- `research/model-risk-agents/code/monitor_gate.py`, `triggers.py` (the deterministic, LLM-free
  ValidationGate this contribution generalizes)
</content>
