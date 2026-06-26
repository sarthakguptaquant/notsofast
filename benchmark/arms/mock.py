"""Deterministic mock arms for CI and conformance.

These exist to prove the PLUMBING end to end without a network or a paid API: the dataset
flows through the arms, the guard routes, the metrics compute, the ledger balances. They do
NOT prove the central claim. The claim needs real model verdicts (see real_adapter.py). A mock
that read the ground-truth label and then "decided" would be circular and worthless, so these
mocks are built to never see the label and to behave like the two failure modes the literature
describes, parameterized by stated, seeded rates.

What each mock models, and why it is honest:

  MockNoCheck      : ships everything. passed=True always, 0 tokens. This is just the baseline;
                     there is nothing to model.

  MockSelfCritic   : the same reasoner reviewing its own work. The key empirical fact it
                     encodes (from Huang et al. 2024) is that intrinsic self-critique on a
                     hard-correctness task does not reliably catch the reasoner's own errors,
                     because the critic shares the flawed reasoning. So this mock ratifies its
                     own candidate at a high rate REGARDLESS of whether the candidate is right
                     or wrong: it has a high pass rate on wrong answers (low detection) and a
                     high pass rate on correct answers (low false-positive). It derives its
                     verdict from a seeded draw with a fixed self-pass probability, NOT from the
                     truth label. The asymmetry that makes self-critique weak is exactly that
                     its pass rate barely depends on correctness.

  MockIndependent  : a verifier in isolation. It does NOT see the original reasoning (enforced
                     structurally by base.isolate). It re-derives from the task alone. It is
                     modeled as a NOISY but truth-correlated checker: it catches a wrong answer
                     with probability `detect_rate` and it falsely flags a correct answer with
                     probability `false_positive_rate`. Both are seeded draws. To stay honest
                     about where the mock's correlation with truth comes from, this mock IS
                     given a `truth_oracle` callback by the runner that returns the item's
                     correctness, and it uses that oracle ONLY to model its own detection and
                     false-positive behavior as noisy functions of truth. This is a SIMULATION
                     KNOB, not a verifier that cheats: the real adapter replaces this oracle
                     with an actual independent model call and the rest of the harness is
                     unchanged. The mock is labeled, everywhere, as mechanics-not-claim.

Determinism: every random draw is keyed by (arm name, item_id, global seed), so the same item
gets the same verdict on every run and across machines. No reliance on dict ordering or wall
clock.
"""

from __future__ import annotations

import hashlib
from typing import Callable, Optional

from .base import Arm, VerificationInput, VerificationVerdict, isolate

# Token costs for the mock arms. Explicit constants, mirrored in the report. A real run reads
# these from metered usage instead; here they are fixed so the ledger is reproducible.
SELF_CRITIC_TOKENS = 800       # one self-review pass (re-reads context, re-critiques)
INDEPENDENT_TOKENS = 700       # one isolated check (re-derives from the task)


def _unit_draw(seed: int, arm: str, item_id: str, salt: str = "") -> float:
    """A deterministic pseudo-random float in [0, 1), keyed by (seed, arm, item, salt).

    Uses a hash so it is stable across Python versions and machines (unlike hash()), and
    independent per arm and per item so the arms' draws do not correlate by accident.
    """
    key = f"{seed}|{arm}|{item_id}|{salt}".encode("utf-8")
    digest = hashlib.sha256(key).digest()
    # take 8 bytes -> integer -> scale to [0, 1)
    n = int.from_bytes(digest[:8], "big")
    return n / float(1 << 64)


class MockNoCheck:
    name = "no_check"
    isolation = "none"

    def verify(self, vin: VerificationInput) -> VerificationVerdict:
        # Ships everything, unconditionally, for free. The baseline error rate is whatever the
        # dataset's wrong-answer fraction is.
        return VerificationVerdict(passed=True, tokens=0, arm=self.name, note="shipped (no check)")


class MockSelfCritic:
    """Same-context self-review. Pass rate barely depends on correctness (that is the point)."""

    name = "self_critic"
    isolation = "shared_context"

    def __init__(self, seed: int, self_pass_rate: float = 0.86):
        # self_pass_rate: probability the self-critic says "looks correct" on ANY hard item,
        # right or wrong. High and roughly truth-independent, per Huang et al. 2024. A small
        # truth sensitivity is allowed (correct answers pass slightly more) but it is weak,
        # which is what makes self-critique a poor gate.
        self.seed = seed
        self.self_pass_rate = self_pass_rate

    def verify(self, vin: VerificationInput) -> VerificationVerdict:
        # The self-critic is allowed to read the reasoning_trace (shared context). It does not
        # help it on hard-correctness items, by construction.
        draw = _unit_draw(self.seed, self.name, vin.item_id)
        passed = draw < self.self_pass_rate
        note = "self-review ratified" if passed else "self-review flagged"
        return VerificationVerdict(passed=passed, tokens=SELF_CRITIC_TOKENS, arm=self.name, note=note)


class MockIndependent:
    """Isolated verifier. Truth-correlated but noisy: catches wrongs at detect_rate, falsely
    flags corrects at false_positive_rate. The truth_oracle is a SIMULATION KNOB (see module
    docstring); the real adapter swaps it for a live independent model call.
    """

    name = "independent"
    isolation = "isolated"

    def __init__(
        self,
        seed: int,
        truth_oracle: Callable[[str], bool],
        detect_rate: float = 0.78,
        false_positive_rate: float = 0.08,
    ):
        self.seed = seed
        self.truth_oracle = truth_oracle
        self.detect_rate = detect_rate
        self.false_positive_rate = false_positive_rate

    def verify(self, vin: VerificationInput) -> VerificationVerdict:
        # Enforce isolation structurally: rebuild the input with the reasoning trace stripped,
        # then assert it is gone before proceeding. Even if the runner forgot to isolate, this
        # arm refuses to look at a trace.
        view = isolate(vin)
        assert view.reasoning_trace is None, "INDEPENDENT arm must not see the reasoning trace"

        is_correct = self.truth_oracle(view.item_id)
        if is_correct:
            # might falsely flag a good answer (the real cost of an independent check)
            flag = _unit_draw(self.seed, self.name, view.item_id, "fp") < self.false_positive_rate
            passed = not flag
            note = "isolated check passed" if passed else "isolated check FALSE-flagged a correct answer"
        else:
            # might catch the wrong answer (detection), might miss it
            caught = _unit_draw(self.seed, self.name, view.item_id, "detect") < self.detect_rate
            passed = not caught
            note = "isolated check caught a wrong answer" if caught else "isolated check missed a wrong answer"
        return VerificationVerdict(passed=passed, tokens=INDEPENDENT_TOKENS, arm=self.name, note=note)


def build_mock_arms(
    seed: int,
    truth_oracle: Callable[[str], bool],
    self_pass_rate: float = 0.86,
    detect_rate: float = 0.78,
    false_positive_rate: float = 0.08,
) -> dict:
    """Construct the three mock arms with a shared seed and the simulation knobs.

    truth_oracle: item_id -> bool, returns whether that item's candidate is actually correct.
    Used ONLY by the independent mock to model noisy-but-truth-correlated detection. The
    self-critic and no-check arms never receive it.
    """
    return {
        "no_check": MockNoCheck(),
        "self_critic": MockSelfCritic(seed=seed, self_pass_rate=self_pass_rate),
        "independent": MockIndependent(
            seed=seed,
            truth_oracle=truth_oracle,
            detect_rate=detect_rate,
            false_positive_rate=false_positive_rate,
        ),
    }
