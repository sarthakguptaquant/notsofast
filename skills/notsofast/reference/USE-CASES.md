# Use cases: where the notsofast contract earns its place

Each scenario names the loop, the decision it produces, the verification mode that closes it, the
two-axis classification, and the verdict the guard returns. The pattern is always the same: a
self-only critic on a hard-correctness, high-materiality decision is refused; everything else passes.
These are illustrative scenarios, not measured results.

## 1. Finance and model risk

- **Loop:** an autonomous agent drafts and self-reviews a quarterly forecast sign-off, or scores a
  credit decision and critiques its own rationale.
- **Decision:** approve the forecast / approve or decline the applicant.
- **Verification mode:** `self`.
- **Classification:** `hard_correctness` (there is a right answer the outcome later reveals), `high`
  (capital, regulatory exposure, real lending loss).
- **Verdict:** `REQUIRE_INDEPENDENT_CHECK`. Route to a held-out backtest, a second model, or a
  validator. A deterministic model-risk validation gate is the worked end-state (see CONTRACT.md).
- **Why it matters:** model risk is assumption risk; a model grading its own assumptions is the
  failure regulators care about most.

## 2. Trading and markets

- **Loop:** an autonomous agent sizes a position or signs off a mark-to-market valuation, then
  self-checks its own pricing.
- **Decision:** put on the position at that size; accept the valuation.
- **Verification mode:** `self`.
- **Classification:** `hard_correctness`, `high` (a mispriced book or an oversized position is real
  money and a risk-limit matter).
- **Verdict:** `REQUIRE_INDEPENDENT_CHECK`. Add an independent pricing model or a risk-limit tool
  check, or escalate to a risk officer for the large-notional band.

## 3. Healthcare

- **Loop:** a clinical-decision-support agent proposes a triage level or a prior-authorization
  determination and reviews its own reasoning.
- **Decision:** triage acuity, authorize or deny, suggested coding.
- **Verification mode:** `self`.
- **Classification:** `hard_correctness`, `high` (patient-safety and reimbursement consequences).
- **Verdict:** `ESCALATE` where no independent automated check exists; a clinician is the independent
  verifier. The contract makes the human gate non-optional for this class.

## 4. Legal and compliance

- **Loop:** a contract-review or regulatory-determination agent flags clauses and self-confirms.
- **Decision:** "this clause is compliant" / "this filing meets the rule."
- **Verification mode:** `self`.
- **Classification:** `hard_correctness`, `high` (a wrong determination carries legal and regulatory
  liability).
- **Verdict:** `REQUIRE_INDEPENDENT_CHECK`. A cross-model review or a human attorney sign-off.

## 5. Software engineering

- **Loop:** an autonomous PR agent writes code, runs its own self-review, and opens a merge.
- **Decision:** merge to a production branch.
- **Verification mode:** `self`, unless a test suite closes the loop.
- **Classification:** `hard_correctness` (tests define correctness), materiality depends on the target
  (a production branch is `high`; a scratch branch is `low`).
- **Verdict:** for the production merge, `REQUIRE_INDEPENDENT_CHECK` until a `tool` gate (the test
  suite or CI) is the closing mode. This is the case where the cheapest fix is wiring the existing test
  suite in as the independent check, which the contract makes explicit.

## 6. Low-stakes generation (the contract stays out of the way)

- **Loop:** a drafting agent writes marketing copy or brainstorms options and self-refines.
- **Decision:** which draft to present.
- **Verification mode:** `self`.
- **Classification:** `soft` (subjective quality, self-feedback measurably helps), `low` (reversible,
  cheap).
- **Verdict:** `ALLOW`. The rule does not fire. This is the boundary that keeps the contract from
  becoming "always require a human," and it is why the two-axis classification exists.

## The economic logic, stated honestly

The contract pays off in two ways. First and primarily, it prevents a class of expensive errors by
refusing to let a self-critic be the only gate where being wrong is costly. Second, on hard-correctness
tasks where self-correction is known to be unreliable, it stops the loop from spending more tokens on
self-refine passes that will not close the gap, and routes to an independent check or a human instead.
It does not promise lower total token use in every case (adding an independent check has its own cost);
it promises that the spend goes to verification that can actually help, on the decisions that justify
it. Where a decision is soft and low-materiality, the contract adds nothing and slows nothing.
