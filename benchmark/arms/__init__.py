"""Verification arms: NO_CHECK, SELF_CRITIC, INDEPENDENT.

Two backends behind one interface:
  - build_mock_arms : seeded, deterministic, no network. For CI and the mechanics pilot.
  - build_real_arms : wraps a single user-supplied model_call. For the real result.

The isolation that defines the INDEPENDENT arm lives in base.isolate and is enforced in both
backends. See base.py for the contract.
"""

from .base import (  # noqa: F401
    Arm,
    VerificationInput,
    VerificationVerdict,
    isolate,
)
from .mock import (  # noqa: F401
    INDEPENDENT_TOKENS,
    SELF_CRITIC_TOKENS,
    build_mock_arms,
)
from .real_adapter import (  # noqa: F401
    ModelResponse,
    build_real_arms,
)
