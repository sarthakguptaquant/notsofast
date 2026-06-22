# DAY 01: Mapping the loop landscape and a working taxonomy

**Date:** 2026-06-15. Personal capacity, industry-level. Zero employer internals.
**Deliverable:** what "the loop" means in agentic AI now, a survey with cited sources, and
a clean taxonomy of loop types and where each is used.

---

## 1. Framing: what "the loop" actually is

Strip away the marketing and an agent is a language model wrapped in a control loop. The
model proposes, something executes, the result is fed back, and the model proposes again.
The interesting part is not the model call; it is the loop structure that decides what gets
fed back, when the loop stops, and who (or what) checks the work. Different loop structures
have different failure surfaces, and that is the angle this analysis cares about.

**Scope.** This is a map of *inference-time orchestration loops*: loops that iterate text,
plans, trajectories, or tasks at run time while the model weights stay frozen. There is a
second, equally large family of *training-time loops*, where the iterated object is the model
weights themselves and an environment reward closes the loop: agentic reinforcement learning,
PPO, GRPO, and related methods, surveyed in "The Landscape of Agentic Reinforcement Learning
for LLMs" ([arXiv:2509.02547](https://arxiv.org/abs/2509.02547)). Training-time loops are
deliberately out of scope for Day 1: they have a different governance surface (they touch the
weights, not the run) and a different tooling stack. Calling that boundary out is the honest
move, because a map of agentic loops that silently skipped RL would be a map of half the
territory.

A useful vocabulary anchor is the January 2026 survey by Arunkumar, Gangadharan and Buyya,
which breaks LLM agents into six dimensions: Perception, Brain, Planning, Action, Tool Use,
and Collaboration ([arXiv:2601.12560](https://arxiv.org/abs/2601.12560), abstract-level read).
Inference-time loops live mostly in the Brain and Planning dimensions, with Action and Tool
Use carrying the act leg and Collaboration carrying the peer-check leg. The planning-specific
survey by Huang et al. is the other reference spine: it categorizes agent planning into task
decomposition, plan selection, external module, reflection, and memory
([arXiv:2402.02716](https://arxiv.org/pdf/2402.02716)). Both treat reflection and memory as
first-class, which matters because the self-improving loop families below are built almost
entirely out of those two ingredients.

---

## 2. The loop families (with primary sources)

A flat list of "families" hides the real structure, so this map uses two tiers. **Base loops**
are the atomic iteration patterns. **Composition strategies** are loops that orchestrate base
loops into something larger. A long-horizon **autonomous wrapper** sits outside both. The
split is by what is iterated and what closes the loop, not by brand.

### Tier 1: Base loops

#### 2.1 The reason-act loop (ReAct)

The atomic case. The model interleaves a reasoning trace ("thought") with an action (a tool
call or environment step), observes the result, and repeats until it emits an answer. ReAct is
the canonical base pattern that most other loops build on. Canonical source: Yao et al.,
"ReAct: Synergizing Reasoning and Acting in Language Models," 2022
([arXiv:2210.03629](https://arxiv.org/pdf/2210.03629)), evaluated on HotPotQA, FEVER,
ALFWorld, and WebShop. Tool-result feedback (observe a tool failure, adjust, retry) is the
act-observe half of ReAct, not a separate family, which is why it is folded in here rather
than listed on its own. What closes the loop: the model decides it is done. That is also its
first weakness, examined on Day 2.

#### 2.2 The reflection / self-refine loop

The iterated object is the agent's own output, and a critic step closes the loop. Two primary
sources define the family:

- **Self-Refine** (Madaan et al., 2023,
  [arXiv:2303.17651](https://arxiv.org/pdf/2303.17651)): one model, three roles via three
  prompts: generate, give feedback on its own output, refine. No external signal required.
- **Reflexion** (Shinn et al., 2023, NeurIPS 2023,
  [arXiv:2303.11366](https://arxiv.org/pdf/2303.11366)): an Actor, an Evaluator, and a
  Self-Reflection model. The reflection is stored as verbal feedback in memory and fed into
  the next trial, which the authors frame as "verbal reinforcement learning." Reported gains
  over ReAct/CoT baselines on HotPotQA and HumanEval.

What closes the loop: an evaluator or self-critique verdict. Where it is used: code
generation, multi-hop QA, anything with a checkable output.

**Retrieval-specialized variant: the corrective-RAG loop.** When the output to be refined is a
retrieved evidence set, reflection becomes a retrieve, critique-relevance, re-retrieve loop:
Self-RAG, Corrective RAG, and the broader agentic-RAG pattern (survey on reasoning agentic RAG,
framed around System 1 versus System 2 retrieval,
[arXiv:2506.10408](https://arxiv.org/html/2506.10408v1)). Structurally this is a reflection
loop with a retrieval evaluator closing it, not a new base family, but it is the loop most
finance and enterprise teams actually run in production (retrieval over filings, policy docs,
reserving memos), so it earns an explicit mention.

### Tier 2: Composition strategies

#### 2.3 The plan-then-execute loop

The iterated object is a plan. A planner decomposes the goal into steps, an executor runs them
(each step typically a ReAct sub-loop), and a re-planner inspects results and revises the
remaining plan. The academic anchor is Plan-and-Solve prompting (Wang et al., 2023,
[arXiv:2305.04091](https://arxiv.org/abs/2305.04091)); the common implementation is the
LangGraph plan-and-execute pattern ([LangChain, Plan-and-Execute
Agents](https://www.langchain.com/blog/planning-agents)). The distinguishing move versus ReAct
is the explicit replan step: execute, replan, execute. Usually more token-efficient on long
tasks because the agent commits to a strategy instead of re-deriving it every step, at the
cost of plan staleness when the world changes mid-run. What closes the loop: the replanner
judging the plan still viable, or the goal met.

#### 2.4 The search loop (tree-structured)

When a single trajectory is not enough, the loop becomes a search over trajectories, with each
trajectory a base loop (ReAct plus reflection). Tree of Thoughts and, more completely,
Language Agent Tree Search (LATS, Zhou et al., ICML 2024,
[arXiv:2310.04406](https://arxiv.org/abs/2310.04406)) wrap reasoning, acting, and reflection
inside Monte Carlo Tree Search: select, expand, evaluate, simulate, backpropagate, and on
failure generate a reflection that seeds the next trial. Reported 92.7% pass@1 on HumanEval
with GPT-4 (a historical-context number now that HumanEval is largely saturated). What closes
the loop: a value function plus a search budget. Where it is used: hard decision-making and
code tasks where exploration pays for its cost. The cost is the catch, a Day-2 item.

#### 2.5 The multi-agent / debate loop

The iterated object is a set of competing answers across multiple model instances. Du et al.,
"Improving Factuality and Reasoning in Language Models through Multiagent Debate" (ICML 2024,
[arXiv:2305.14325](https://arxiv.org/abs/2305.14325)), is the canonical "society of minds"
source: instances propose, critique, and converge over
rounds, with reported gains on math and factuality. The pattern recurs in consensus and
council variants for hallucination and bias reduction (for example, Council Mode,
[arXiv:2604.02923](https://arxiv.org/html/2604.02923v1)). The evidence is genuinely contested:
a 2025 controlled study of debate in logical reasoning finds that majority pressure can
suppress a correct minority, and that intrinsic reasoning strength and group diversity, rather
than the debate procedure itself, are the dominant drivers of any gain
([arXiv:2511.07784](https://arxiv.org/abs/2511.07784)), while task-specific replications of the
original debate work do show real improvements. That open question is itself a Day-2 hook on
evaluation honesty. What closes the loop: convergence or a vote.

### Outer wrapper: the autonomous / self-improving loop

The most hyped and least governed, this is not a peer of the loops above but a long-horizon
wrapper that runs them repeatedly. Two sub-cases:

- **Long-running autonomous task loops.** AutoGPT and BabyAGI: a thin prompting layer on a
  recursive loop with persistent memory. BabyAGI runs create-task, execute, store result,
  reprioritize, repeat, over a vector store ([IBM, What is
  BabyAGI](https://www.ibm.com/think/topics/babyagi); [Sequoia, Exploring Autonomous
  Agents](https://sequoiacap.com/article/autonomous-agents-perspective/)). What closes the
  loop: often nothing clean. They are known to wander or never terminate, which Day 2 treats
  as a named failure mode rather than an anecdote.
- **Self-improving skill / self-modification loops.** Voyager (Wang et al., 2023,
  [arXiv:2305.16291](https://arxiv.org/abs/2305.16291)) writes executable skills, verifies
  them against environment feedback, and stores the verified ones in a growing library to
  compose later: a write-test-store-reuse loop. The Gödel Agent (2024,
  [arXiv:2410.04444](https://arxiv.org/html/2410.04444v1)) goes further and lets the agent
  modify its own logic, and explicitly acknowledges that it "is not sufficiently stable and
  may be prone to error accumulation." That admission, from the authors themselves, names the
  central problem this analysis is circling.

---

## 3. Taxonomy table

| Tier | Family | Iterated object | What closes the loop | Verification mode | Canonical source | Typical use |
|---|---|---|---|---|---|---|
| Base | Reason-act | Thought + action trace | Model self-declares done | self / tool | ReAct, [2210.03629](https://arxiv.org/pdf/2210.03629) | Tool-using production agents |
| Base | Reflection / self-refine | The agent's own output | Critic / evaluator verdict | self | Self-Refine [2303.17651](https://arxiv.org/pdf/2303.17651); Reflexion [2303.11366](https://arxiv.org/pdf/2303.11366) | Code, multi-hop QA |
| Base (variant) | Corrective RAG | Retrieved evidence set | Retrieval-relevance evaluator | tool | Agentic-RAG survey [2506.10408](https://arxiv.org/html/2506.10408v1) | Retrieval over docs / filings |
| Composition | Plan-then-execute | A plan | Replanner judges viable / goal met | self | Plan-and-Solve [2305.04091](https://arxiv.org/abs/2305.04091) | Long multi-step tasks |
| Composition | Search (tree) | A tree of trajectories | Value function + search budget | tool | LATS, [2310.04406](https://arxiv.org/abs/2310.04406) | Hard decision / code search |
| Composition | Multi-agent / debate | Competing answers | Convergence or vote | peer | Du et al., [2305.14325](https://arxiv.org/abs/2305.14325) | Factuality, hallucination reduction |
| Wrapper | Autonomous / self-improving | Tasks, skills, or own code | Often undefined | often unchecked | BabyAGI; Voyager [2305.16291](https://arxiv.org/abs/2305.16291); Gödel Agent [2410.04444](https://arxiv.org/html/2410.04444v1) | Open-ended, long-running |
| (Out of scope) | Training-time / RL | Model weights | Environment reward | reward signal | Agentic RL survey [2509.02547](https://arxiv.org/abs/2509.02547) | Policy fine-tuning |

**Cross-cutting axis: who checks the work.** The "verification mode" column above is the axis
that matters most for governance, and it is orthogonal to tier. A loop can be self-checked
(the model is its own critic, as in Self-Refine), peer-checked (other agents, as in debate),
tool-checked (a test suite, a retriever, an environment reward), or human-checked (a
human-in-the-loop gate, absent from every row above). Most hyped autonomous loops sit at the
weak end: self-checked or unchecked. A loop that touches real money or real decisions should
not be allowed to be its own only judge.

**Cross-cutting axis: cost versus reliability.** The families also form a near-monotonic
cost/reliability frontier. ReAct is cheap and fragile; reflection adds critic passes; tree
search multiplies inference by the branching factor; debate multiplies it by the number of
agents and rounds. Buying reliability costs compute, which makes "how much loop can this
decision justify" a governance variable in its own right. You cannot run Monte Carlo tree
search on every routine call, so the loop has to be sized to the stakes.

---

## 4. The through-line into Day 2 and Day 3

Reading the families together, one weak spot recurs, but precisely, not everywhere. The
self-checked and autonomous families have weak or undefined stopping and self-checking: ReAct
stops when the model says so, and autonomous loops often do not stop at all, with the Gödel
Agent authors conceding compounding error in print. The families that borrow an external
check inherit a defined stopping criterion: an evaluator verdict (reflection), a replan-or-done
test (plan-execute), a value function plus budget (search), or a convergence vote (debate). So
the honest thesis is sharper than "every loop is broken": loops are getting more autonomous
faster than their *verification and stopping criteria* are getting more rigorous, and the
weakness concentrates in exactly the self-checked and autonomous designs that are being shipped
fastest. That is the bridge to the governance angle. Day 2 maps that observation to specific
named failure modes and the open tooling that does or does not address each; Day 3 scopes a
buildable contribution on the verification axis.

---

## 5. Adversarial self-review

- **Assumption: the two-tier split is clean.** Real systems blend tiers (LATS is a search
  loop built out of reflection; Reflexion uses memory like the autonomous family). The split is
  by what is iterated and which tier composes which, not a claim that systems are pure. Stated
  so a reader does not mistake it for taxonomy fundamentalism.
- **What could be overstated.** "ReAct is the canonical base pattern" is a structural claim,
  not a deployment-share statistic; much current production is plan-execute or constrained
  graphs precisely because unconstrained ReAct is unreliable, so no frequency claim is made.
  Benchmark numbers (92.7% LATS pass@1, Reflexion gains) are as reported by the authors on
  specific datasets and are not independently reproduced here; HumanEval is now saturated, so
  the LATS figure is historical context, not live evidence.
- **Unverified / abstract-only items.** The anchor survey (2601.12560), Council Mode
  (2604.02923), the debate controlled study (2511.07784), the agentic-RAG survey (2506.10408),
  and the agentic-RL survey (2509.02547) are cited at abstract level, not full read; nothing
  load-bearing rests on their internal numbers, only on their existence and scope. The
  plan-execute lineage uses a vendor blog only for the implementation pattern; the academic
  anchor is Plan-and-Solve (2305.04091).
- **Citation-accuracy note.** An earlier draft misstated the six dimensions of 2601.12560; the
  corrected set (Perception, Brain, Planning, Action, Tool Use, Collaboration) was re-verified
  against the abstract twice before commit. ReAct, Reflexion, Self-Refine, LATS, Du et al.,
  Voyager, and Gödel Agent IDs and attributions are verified. The multi-agent debate controlled
  study (2511.07784) was re-characterized after a verification pass to match the paper's actual
  finding (majority pressure can suppress a correct minority; reasoning strength and diversity
  dominate), not a looser "gains reduce to voting" paraphrase.
- **No hard gap claims yet.** Day 1 makes no "this does not exist" claim. The forward-looking
  pointers to a verification weak spot are framing, not gap assertions; the actual
  does-it-already-exist search against GitHub and PyPI is Day-2 and Day-3 work, per the
  validation standard.
- **Reproducibility.** Every primary claim links to an arXiv abstract or PDF or a named vendor
  doc. Re-running the seed searches (ReAct, Reflexion/Self-Refine, plan-and-execute, multi-agent
  debate) plus the LATS, Voyager, RL-survey, RAG-survey, and taxonomy-survey lookups returns
  these same sources.

---

## Sources

- ReAct: [arXiv:2210.03629](https://arxiv.org/pdf/2210.03629)
- Self-Refine: [arXiv:2303.17651](https://arxiv.org/pdf/2303.17651)
- Reflexion: [arXiv:2303.11366](https://arxiv.org/pdf/2303.11366)
- Plan-and-Solve: [arXiv:2305.04091](https://arxiv.org/abs/2305.04091)
- LATS: [arXiv:2310.04406](https://arxiv.org/abs/2310.04406)
- Multiagent debate (Du et al.): [arXiv:2305.14325](https://arxiv.org/abs/2305.14325)
- Council Mode: [arXiv:2604.02923](https://arxiv.org/html/2604.02923v1)
- Debate controlled study: [arXiv:2511.07784](https://arxiv.org/abs/2511.07784)
- Voyager: [arXiv:2305.16291](https://arxiv.org/abs/2305.16291)
- Gödel Agent: [arXiv:2410.04444](https://arxiv.org/html/2410.04444v1)
- Agentic AI taxonomy survey: [arXiv:2601.12560](https://arxiv.org/abs/2601.12560)
- Planning survey (Huang et al.): [arXiv:2402.02716](https://arxiv.org/pdf/2402.02716)
- Agentic RL survey: [arXiv:2509.02547](https://arxiv.org/abs/2509.02547)
- Agentic RAG survey: [arXiv:2506.10408](https://arxiv.org/html/2506.10408v1)
- Plan-and-Execute pattern: [LangChain](https://www.langchain.com/blog/planning-agents)
- BabyAGI: [IBM](https://www.ibm.com/think/topics/babyagi); [Sequoia](https://sequoiacap.com/article/autonomous-agents-perspective/)
