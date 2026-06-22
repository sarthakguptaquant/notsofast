# third-umpire Validation Report

Date: 2026-06-17
Method: 12-agent parallel authentication workflow (run wf_99466d16-04f). Every check was executed,
not asserted: both test suites, the worked example, and the guard demo were run on four Python
interpreters; the seeded case study was reproduced from scratch and diffed against the committed
JSON; the contract was independently re-derived and enumerated against the live code; and the
headline result was stress-tested across seed and assumption sweeps.

## 1. Verdict

**AUTHENTIC. Publishable after one disclosure fix, which has now been applied and re-validated.**

The guard and case study are genuine. Cross-environment behavior is identical and clean on Python
3.8 / 3.9 / 3.11 / 3.13, the seeded study reproduces the committed numbers exactly and
deterministically, and the guard conforms to its documented contract with zero divergences across
the full input space. The headline ("cheaper and more accurate at the same time") is real and
robust to seed (75/75) and to population mix. It rests on two calibration assumptions; one
(cheap-rework break-even) was already disclosed, the other (a human catches more than an
independent check) was load-bearing for the accuracy half and was not disclosed. That gap is now
closed in study/STUDY.md.

## 2. Fixes applied this pass (study/STUDY.md)

1. The accuracy claim is now qualified: the edge over validate-everything depends on a human
   catching more errors than an independent check (HUMAN_CATCH 0.90 above CHECK_CATCH 0.60); if a
   check were as good as a human, validate-everything would tie on accuracy while still losing on
   cost.
2. "What would move the result" now lists both load-bearing inequalities explicitly:
   HUMAN_HANDOFF (200) below INDEP_CHECK (700) drives the cost win; HUMAN_CATCH (0.90) above
   CHECK_CATCH (0.60) drives the accuracy win; the both-win result holds only while both hold.
3. The bold headline now reads "the cheapest total, and the most accurate under these assumptions,
   at the same time," so it is not read in isolation.

Re-validation of the claim before writing it: a direct sweep confirmed third-umpire wins accuracy
10/10 seeds at CHECK_CATCH 0.60 and 0.80, and validate-everything matches or beats it 10/10 at
CHECK_CATCH 0.90 and 0.95. The crossover sits exactly at check-quality equal to human-quality, so
the new sentence is accurate. No number, token total, or chart value changed; none was wrong.

---

(The full adversarial synthesis follows.)

## Authentication verdict: AUTHENTIC, publish with one disclosure fix

The third-umpire guard and case study are genuine. Cross-environment behavior is identical and clean on Python 3.8/3.9/3.11/3.13, the seeded study reproduces the committed numbers exactly and deterministically, and the guard conforms to its documented contract with zero divergences across the full input space. The headline ("cheaper AND more accurate") is real and robust to seed (75/75), but it rests on two calibration assumptions. One of them (cheap-rework) is already disclosed honestly in the study. The other (a human catches more than an independent check) is load-bearing for the accuracy half of the headline and is not disclosed. That single gap is the only thing standing between this and an unqualified publish.

### Phase 1: Cross-environment (PASS)

| Python | Source | test suite | rigorous (N=2816) | quickstart | guard demo | All pass |
|---|---|---|---|---|---|---|
| 3.8.20 | uv | ok (11) | ALL PASSED | A-E as spec | 6 lines | yes |
| 3.9.6 | system | ok (11) | ALL PASSED | A-E as spec | 6 lines | yes |
| 3.11.15 | uv | ok (11) | ALL PASSED | A-E as spec | 6 lines | yes |
| 3.13.14 | uv | ok (11) | ALL PASSED | A-E as spec | 6 lines | yes |

Empirically executed, exit code 0 everywhere, zero warnings or deprecation notices. Zero-dependency claim holds. No crack.

### Phase 2: Study reproduction (PASS)

Committed study_results.json verified on disk and matches the brief. Reproduced under Python 3.13.14 and 3.9.6.

| policy | committed total_tokens | reproduced | committed acc_hard_high | reproduced (max abs diff) |
|---|---:|---|---:|---|
| ship (no validation) | 2,605,300 | exact | 0.55 | match (~9e-16) |
| naive self-refine (K=4) | 4,369,420 | exact | 0.49000000000000005 | match (~1e-15) |
| validate everything | 2,231,860 | exact | 0.8200000000000001 | match (~5e-15) |
| third-umpire (routed) | 1,998,865 | exact | 0.844010067114094 | match (~3e-15) |

wrong_hard_high=46.5 matches. All four token totals are bit-exact integers; accuracies match to ~1e-14, far inside the 1e-6 tolerance. Determinism: identical across two runs. The only per-run difference is the hex memory addresses inside assumptions.POLICIES function-repr strings, which are cosmetic Python process artifacts, not results. third-umpire is simultaneously lowest cost (1,998,865) and highest accuracy (0.8440) in the committed run. No crack.

### Phase 3: Contract conformance (PASS)

| Check | Result |
|---|---|
| Full input-space enumeration | 448/448 combinations, 0 divergences |
| (a) Decision frozen, mutation raises FrozenInstanceError | pass |
| (b) Unknown verification_mode raises ValueError | pass |
| (c) Unknown task/materiality, no check, addable -> REQUIRE_INDEPENDENT_CHECK | pass |
| (d) Unknown task/materiality, no check, not addable -> ESCALATE | pass |

Conservative default (unknown -> hard_correctness/high) verified in source and tests. No crack.

### Phase 4: Robustness (MOSTLY ROBUST)

| Sweep | Runs | Both-win rate | Verdict |
|---|---:|---:|---|
| Seed (1..75, defaults) | 75 | 1.00 | robust |
| Rework cost (500..60000 x 15 seeds) | 120 | 0.75 | mostly_robust |
| Base accuracy x CHECK_CATCH (5x3x10) | 150 | 1.00 in grid | robust in grid |
| POP_MIX x K_REFINE (9x10) | 90 | 1.00 | robust |

The result is structural, not seed-luck: the per-policy cost and accuracy math is independent of the draw, so the seed only reshuffles the population mix. It does not depend on a cherry-picked seed.

It is conditional on two assumption constants:

1. Cost-win inverts when rework is cheap. Below ~2,000-2,400 tokens per wrong hard+high decision, "ship nothing" is cheaper (0/15 seeds win for third-umpire at rework=500 and 1000; 15/15 at rework>=2400). The study's chosen value (9,000) sits firmly in the robust regime, and STUDY.md "The honest break-even" discloses this clearly. Disclosed limitation, not a hidden one.

2. Accuracy-win over validate-everything inverts when an independent check is at least as good as a human. The edge comes entirely from escalating no-check-available hard+high items to a human (HUMAN_CATCH=0.90) versus validate-everything running only a check (CHECK_CATCH=0.60). Probing outside the requested grid, at CHECK_CATCH >= 0.90 the strict accuracy win drops to 0/10. This dependency was NOT disclosed in STUDY.md; it is now (see section 2).

Both inequalities are confirmed in source: study/run_study.py (INDEP_CHECK=700, HUMAN_HANDOFF=200, CHECK_CATCH=0.60, HUMAN_CATCH=0.90). The cost win on escalations is structural (HUMAN_HANDOFF < INDEP_CHECK) and never breaks in anything tested.

### Cracks (status after this pass)

- Undisclosed accuracy dependency: FIXED in study/STUDY.md (section 2 above).
- Disclosed cheap-rework inversion: real but already covered by "The honest break-even". No action.
- Cosmetic: function-repr memory addresses make a whole-file byte diff noisy. Results are deterministic; left as-is by design.
- Calibration not measurement: accuracy dynamics are simulated from Huang et al. ICLR 2024, disclosed in STUDY.md. The 0.84/0.82 figures are model outputs, never to be cited as measured LLM accuracies.

### Bottom line

Sound, reproducible, contract-conformant work that survives adversarial scrutiny on every empirical
axis. The cost claim is honestly bounded by a disclosed break-even. The accuracy claim is true under
the model and now carries its one load-bearing assumption (human > check) in the open. With the
disclosure fixes applied, the recommendation moves from publish_with_fixes to publish-ready. The
public repo flip itself remains Sarthak's manual step.
