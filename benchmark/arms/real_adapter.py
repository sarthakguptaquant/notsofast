"""Real-model adapter: the one function you wire to make the benchmark a real result.

The whole benchmark is built so that swapping the mock arms for real model calls is a single
plug-in. You implement ONE function, `model_call`, and the self-critic and independent arms
below turn into real verification arms. Nothing else in the harness changes. No provider is
hardcoded here, no API key is read, and no network call is made by default. If you run the
harness without wiring this, you get the mock pilot (mechanics only). If you wire it, you get
the actual detection-lift and token numbers.

WHY THIS DESIGN

The critique the benchmark answers is: "a seeded simulation can't show the gate catches errors
a self-critic misses or saves net tokens." The honest fix is to make the real run trivial to
perform and identical in plumbing to the mock run, so the same metrics code produces real
numbers the moment a model is attached. That is what this file is. It is deliberately a stub:
shipping it pre-wired to a paid provider would (a) hardcode a vendor, (b) need keys, (c) cost
money on import. All three are off-limits here. So it is documented, typed, and raises a clear
error until you implement `model_call`.

THE CONTRACT YOU IMPLEMENT

    def model_call(prompt: str) -> ModelResponse: ...

It takes a single prompt string and returns a ModelResponse(text, tokens). `tokens` should be
the real total token count for the call (prompt + completion) so the token ledger is metered,
not assumed. Use whatever provider and model you like. Keep it deterministic if you can
(temperature 0) so the run replays.

ISOLATION IS STILL STRUCTURAL

The RealIndependentArm builds its prompt from base.isolate(vin), so the reasoning trace is
physically stripped before the prompt is assembled. The independent verifier model literally
never receives the original chain of reasoning in its context window. The RealSelfCriticArm
includes the trace. That is the only difference between the two arms, which is exactly the
variable the benchmark isolates: context access, nothing else. Same model, same task, same
candidate; one sees the original reasoning, one does not.

VERDICT PARSING

Each arm asks the model for a strict verdict token (PASS or FLAG) and parses it. A response
that does not contain a clear verdict is treated as FLAG (conservative: an unparseable check is
not a passing check), mirroring the guard's own conservative-default philosophy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .base import VerificationInput, VerificationVerdict, isolate


@dataclass(frozen=True)
class ModelResponse:
    text: str
    tokens: int


# The single function the user wires. Left as None so the harness fails loudly if a real run is
# requested without it being implemented. Assign your implementation to this name (see
# `set_model_call`) or pass it into the arm constructors.
ModelCall = Callable[[str], ModelResponse]


def _require(model_call: Optional[ModelCall]) -> ModelCall:
    if model_call is None:
        raise NotImplementedError(
            "Real-model run requested but no model_call is wired. Implement a function "
            "`model_call(prompt: str) -> ModelResponse` (text + real token count) and pass it "
            "to the arm constructors, or to run.py via --real. No provider is hardcoded; wire "
            "your own. See benchmark/arms/real_adapter.py and benchmark/REPORT.md."
        )
    return model_call


def _parse_verdict(text: str) -> bool:
    """Parse a model verdict. Returns True for PASS, False for FLAG.

    Conservative: anything that is not an unambiguous PASS is treated as FLAG. A check that
    cannot state clearly that the answer is correct is not allowed to wave it through.
    """
    upper = text.upper()
    # Look for the explicit tokens; FLAG/WRONG/INCORRECT win ties (conservative).
    if "FLAG" in upper or "WRONG" in upper or "INCORRECT" in upper:
        return False
    if "PASS" in upper or "CORRECT" in upper:
        return True
    return False


_SELF_PROMPT = """You proposed an answer to the task below and recorded your reasoning.
Review your own answer. If it is correct, reply with exactly PASS. If it is wrong, reply with
exactly FLAG, then one short reason.

TASK:
{task}

YOUR REASONING:
{reasoning}

YOUR ANSWER:
{candidate}

Verdict:"""


_INDEPENDENT_PROMPT = """You are an independent verifier. You are given a task and a candidate
answer produced by someone else. You do NOT have their reasoning. Re-derive or re-check the
answer from the task alone. If the candidate is correct, reply with exactly PASS. If it is
wrong, reply with exactly FLAG, then one short reason.

TASK:
{task}

CANDIDATE ANSWER:
{candidate}

Verdict:"""


class RealSelfCriticArm:
    """Same-model self-review WITH the original reasoning in context."""

    name = "self_critic"
    isolation = "shared_context"

    def __init__(self, model_call: Optional[ModelCall] = None):
        self._model_call = model_call

    def verify(self, vin: VerificationInput) -> VerificationVerdict:
        call = _require(self._model_call)
        prompt = _SELF_PROMPT.format(
            task=vin.task,
            reasoning=vin.reasoning_trace or "(no reasoning recorded)",
            candidate=vin.candidate,
        )
        resp = call(prompt)
        passed = _parse_verdict(resp.text)
        return VerificationVerdict(passed=passed, tokens=resp.tokens, arm=self.name,
                                   note=resp.text.strip()[:120])


class RealIndependentArm:
    """Isolated-context verification. The reasoning trace is stripped before the prompt is
    built, so the model never sees the original chain of reasoning. This is the isolation.
    """

    name = "independent"
    isolation = "isolated"

    def __init__(self, model_call: Optional[ModelCall] = None):
        self._model_call = model_call

    def verify(self, vin: VerificationInput) -> VerificationVerdict:
        call = _require(self._model_call)
        view = isolate(vin)  # structural isolation: reasoning_trace is now None
        assert view.reasoning_trace is None, "independent arm must not see the reasoning trace"
        prompt = _INDEPENDENT_PROMPT.format(task=view.task, candidate=view.candidate)
        resp = call(prompt)
        passed = _parse_verdict(resp.text)
        return VerificationVerdict(passed=passed, tokens=resp.tokens, arm=self.name,
                                   note=resp.text.strip()[:120])


class RealNoCheck:
    name = "no_check"
    isolation = "none"

    def verify(self, vin: VerificationInput) -> VerificationVerdict:
        return VerificationVerdict(passed=True, tokens=0, arm=self.name, note="shipped (no check)")


def build_real_arms(model_call: Optional[ModelCall]) -> dict:
    """Construct the three real arms around a single wired model_call. The same model is used
    for self-critic and independent; only context access differs.
    """
    return {
        "no_check": RealNoCheck(),
        "self_critic": RealSelfCriticArm(model_call=model_call),
        "independent": RealIndependentArm(model_call=model_call),
    }
