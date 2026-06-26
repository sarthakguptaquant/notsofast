"""The benchmark dataset: hard-correctness, checkable decision items.

Each item is one consequential loop decision. It carries:

  id            : stable identifier.
  task          : the prompt the agent was answering (plain text).
  candidate     : the candidate answer to be judged (the thing a verification arm reviews).
  checker       : the name of the ground-truth checker (see checkers.py) that decides whether
                  `candidate` is correct.
  reference     : the inputs the checker needs to re-derive or re-check the truth.
  correct       : the GROUND-TRUTH label, precomputed by running the checker at dataset-build
                  time (see _self_check below). Stored so the runner can score an arm's verdict
                  against truth without re-running the checker per arm, and so a build-time
                  assertion catches any item whose stored label disagrees with its checker.
  verification_mode, task_type, materiality : the Not So Fast tags. Every benchmark item is
                  hard_correctness + high by construction (that is the regime the guard
                  governs and the regime the critique is about); the soft/low items exist only
                  as negative controls to confirm arms and guard stay out of the way.
  rationale     : one line on why the WRONG candidates are plausible, not obviously broken. The
                  whole benchmark rests on the wrong answers being the kind a self-critic
                  rationalizes; if they were obviously broken the test would be trivial and
                  unfair in the easy direction.

How the wrong candidates were constructed (fairness statement). Every wrong candidate is a
single, named, realistic error applied to a correct derivation: a dropped discount factor, a
naive VaR sum that ignores correlation, an annual-rate-not-converted, an inclusive/exclusive
boundary, an off-by-one. No wrong candidate is a typo, a nonsense value, or an out-of-range
number a parser would reject. The correct candidates are the exact right answer to the same
prompt. The split between correct and wrong is balanced enough that an arm cannot win by always
guessing one label (see dataset_stats()).

No employer data, internal figures, or proprietary content appears here. All numbers are
synthetic and self-contained.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping

from .checkers import get_checker

# Tag constants mirror the guard's vocabulary without importing it, so the dataset module has
# no dependency on the guard. The runner is what binds them together.
HARD = "hard_correctness"
SOFT = "soft"
HIGH = "high"
LOW = "low"
SELF = "self"


@dataclass(frozen=True)
class Item:
    id: str
    task: str
    candidate: Any
    checker: str
    reference: Mapping[str, Any]
    correct: bool
    rationale: str
    verification_mode: str = SELF
    task_type: str = HARD
    materiality: str = HIGH
    tags: List[str] = field(default_factory=list)

    def check(self) -> bool:
        """Run the ground-truth checker on this item's candidate. The oracle, not an opinion."""
        return get_checker(self.checker)(self.candidate, self.reference)


def _item(**kw: Any) -> Item:
    return Item(**kw)


# ============================================================================================
# FINANCE / QUANT lane
# ============================================================================================

_FINANCE: List[Item] = [
    _item(
        id="fin-parity-01",
        task="European call on a non-dividend stock trades at 6.0000. Spot 100, strike 100, "
             "rate 5% continuous, 1y. What is the put worth by put-call parity?",
        candidate=1.1230,
        checker="put_call_parity",
        reference={"call": 6.0, "spot": 100.0, "strike": 100.0, "rate": 0.05, "maturity": 1.0},
        correct=True,
        rationale="correct: C - S + K e^{-rT} = 6 - 100 + 100*0.95123 = 1.1230.",
        tags=["options", "parity"],
    ),
    _item(
        id="fin-parity-02",
        task="Same option as fin-parity-01. A loop reports the put value.",
        candidate=6.0000,
        checker="put_call_parity",
        reference={"call": 6.0, "spot": 100.0, "strike": 100.0, "rate": 0.05, "maturity": 1.0},
        correct=False,
        rationale="wrong: dropped the discount factor (used K instead of K e^{-rT}), so "
                  "P = 6 - 100 + 100 = 6. Plausible because it 'feels' symmetric to the call.",
        tags=["options", "parity"],
    ),
    _item(
        id="fin-parity-03",
        task="Call 8.5, spot 50, strike 55, rate 3% continuous, 0.5y. Put by parity?",
        candidate=12.6812,
        checker="put_call_parity",
        reference={"call": 8.5, "spot": 50.0, "strike": 55.0, "rate": 0.03, "maturity": 0.5},
        correct=True,
        rationale="correct: 8.5 - 50 + 55*e^{-0.015} = 8.5 - 50 + 54.1812 = 12.6812.",
        tags=["options", "parity"],
    ),
    _item(
        id="fin-parity-04",
        task="Call 8.5, spot 50, strike 55, rate 3% continuous, 0.5y. Put by parity?",
        candidate=13.5000,
        checker="put_call_parity",
        reference={"call": 8.5, "spot": 50.0, "strike": 55.0, "rate": 0.03, "maturity": 0.5},
        correct=False,
        rationale="wrong: discounted the spot instead of the strike (S e^{-rT} - K), a "
                  "sign/term swap that lands near the right magnitude.",
        tags=["options", "parity"],
    ),
    _item(
        id="fin-var-01",
        task="Two trading books, 1-day 99% VaR of 1,000,000 and 1,500,000, correlation 0.3. "
             "Aggregate VaR (normal approximation)?",
        candidate=2037155.0,
        checker="var_aggregation",
        reference={"var1": 1_000_000.0, "var2": 1_500_000.0, "rho": 0.3, "rel_tol": 1e-4},
        correct=True,
        rationale="correct: sqrt(1e12 + 2.25e12 + 2*0.3*1.5e12) = sqrt(4.15e12) = 2,037,155.",
        tags=["var", "aggregation", "model-risk"],
    ),
    _item(
        id="fin-var-02",
        task="Same two books as fin-var-01. Aggregate VaR?",
        candidate=2500000.0,
        checker="var_aggregation",
        reference={"var1": 1_000_000.0, "var2": 1_500_000.0, "rho": 0.3, "rel_tol": 1e-4},
        correct=False,
        rationale="wrong: naive sum v1 + v2 = 2.5M, valid only at rho = 1. Overstates risk "
                  "and is the single most common VaR aggregation error.",
        tags=["var", "aggregation", "model-risk"],
    ),
    _item(
        id="fin-var-03",
        task="Two books, VaR 800,000 and 600,000, correlation -0.5. Aggregate VaR (normal)?",
        candidate=721110.0,
        checker="var_aggregation",
        reference={"var1": 800_000.0, "var2": 600_000.0, "rho": -0.5, "rel_tol": 1e-3},
        correct=True,
        rationale="correct: sqrt(6.4e11 + 3.6e11 - 2*0.5*4.8e11) = sqrt(5.2e11) = 721,110.",
        tags=["var", "aggregation"],
    ),
    _item(
        id="fin-var-04",
        task="Two books, VaR 800,000 and 600,000, correlation -0.5. Aggregate VaR (normal)?",
        candidate=1000000.0,
        checker="var_aggregation",
        reference={"var1": 800_000.0, "var2": 600_000.0, "rho": -0.5, "rel_tol": 1e-3},
        correct=False,
        rationale="wrong: used rho = 0 (sqrt of sum of squares = 1,000,000), ignoring the "
                  "diversification benefit from negative correlation.",
        tags=["var", "aggregation"],
    ),
    _item(
        id="fin-amort-01",
        task="Loan 250,000, 6% annual nominal, monthly payments, 30y (360 payments). Level "
             "monthly payment?",
        candidate=1498.88,
        checker="amortization_payment",
        reference={"principal": 250_000.0, "annual_rate": 0.06, "periods": 360,
                   "periods_per_year": 12, "abs_tol": 0.02},
        correct=True,
        rationale="correct: i = 0.005, A = 250000*0.005 / (1 - 1.005^-360) = 1,498.88.",
        tags=["credit", "amortization"],
    ),
    _item(
        id="fin-amort-02",
        task="Same loan as fin-amort-01. Monthly payment?",
        candidate=15125.83,
        checker="amortization_payment",
        reference={"principal": 250_000.0, "annual_rate": 0.06, "periods": 360,
                   "periods_per_year": 12, "abs_tol": 0.02},
        correct=False,
        rationale="wrong: used the ANNUAL rate 0.06 as the periodic rate without dividing by "
                  "12. Classic period-conversion miss; the formula is otherwise right.",
        tags=["credit", "amortization"],
    ),
    _item(
        id="fin-amort-03",
        task="Loan 40,000, 0% promotional rate, 24 monthly payments. Monthly payment?",
        candidate=1666.67,
        checker="amortization_payment",
        reference={"principal": 40_000.0, "annual_rate": 0.0, "periods": 24,
                   "periods_per_year": 12, "abs_tol": 0.01},
        correct=True,
        rationale="correct: zero-rate branch, 40000 / 24 = 1,666.67.",
        tags=["credit", "amortization", "edge"],
    ),
    _item(
        id="fin-fv-01",
        task="Invest 10,000 at 7% annual, compounded annually, 10 years. Future value?",
        candidate=19671.51,
        checker="compound_growth",
        reference={"present_value": 10_000.0, "rate": 0.07, "periods": 10, "rel_tol": 1e-6},
        correct=True,
        rationale="correct: 10000 * 1.07^10 = 19,671.51.",
        tags=["tvm"],
    ),
    _item(
        id="fin-fv-02",
        task="Invest 10,000 at 7% annual, compounded annually, 10 years. Future value?",
        candidate=17000.00,
        checker="compound_growth",
        reference={"present_value": 10_000.0, "rate": 0.07, "periods": 10, "rel_tol": 1e-6},
        correct=False,
        rationale="wrong: simple interest (10000 * (1 + 0.07*10) = 17,000) instead of "
                  "compound. Reads correct to anyone who skips the exponent.",
        tags=["tvm"],
    ),
    _item(
        id="fin-fv-03",
        task="Invest 5,000 at 4% annual, compounded annually, 8 years. Future value?",
        candidate=6842.85,
        checker="compound_growth",
        reference={"present_value": 5_000.0, "rate": 0.04, "periods": 8, "rel_tol": 1e-5},
        correct=True,
        rationale="correct: 5000 * 1.04^8 = 6,842.85.",
        tags=["tvm"],
    ),
    _item(
        id="fin-fv-04",
        task="Invest 5,000 at 4% annual, compounded annually, 8 years. Future value?",
        candidate=7107.36,
        checker="compound_growth",
        reference={"present_value": 5_000.0, "rate": 0.04, "periods": 8, "rel_tol": 1e-5},
        correct=False,
        rationale="wrong: off-by-one in the exponent (used 9 periods). Magnitude is close, so "
                  "a self-critic eyeballing it accepts it.",
        tags=["tvm", "off-by-one"],
    ),
    _item(
        id="fin-recon-01",
        task="A P&L attribution lists desk pnl: 120000, -45000, 33000, 9000, -2000. Reported "
             "total?",
        candidate=115000.0,
        checker="reconciliation_sum",
        reference={"components": [120000.0, -45000.0, 33000.0, 9000.0, -2000.0], "abs_tol": 0.5},
        correct=True,
        rationale="correct: components sum to 115,000.",
        tags=["reconciliation"],
    ),
    _item(
        id="fin-recon-02",
        task="Same attribution as fin-recon-01. Reported total?",
        candidate=117000.0,
        checker="reconciliation_sum",
        reference={"components": [120000.0, -45000.0, 33000.0, 9000.0, -2000.0], "abs_tol": 0.5},
        correct=False,
        rationale="wrong: dropped the -2,000 line. A single missed component, the most common "
                  "reconciliation error, and invisible without re-summing.",
        tags=["reconciliation"],
    ),
    _item(
        id="fin-recon-03",
        task="Balance-sheet tie-out, asset lines 4.2, 1.8, 0.95, 2.05 (in millions). Total "
             "assets in millions?",
        candidate=9.0,
        checker="reconciliation_sum",
        reference={"components": [4.2, 1.8, 0.95, 2.05], "abs_tol": 0.005},
        correct=True,
        rationale="correct: 4.2 + 1.8 + 0.95 + 2.05 = 9.0.",
        tags=["reconciliation"],
    ),
    _item(
        id="fin-recon-04",
        task="Balance-sheet tie-out, asset lines 4.2, 1.8, 0.95, 2.05 (in millions). Total "
             "assets in millions?",
        candidate=8.95,
        checker="reconciliation_sum",
        reference={"components": [4.2, 1.8, 0.95, 2.05], "abs_tol": 0.005},
        correct=False,
        rationale="wrong: transposed 0.95 as 0.90. Sub-percent error, exactly the kind that "
                  "survives a self-review and breaks a tie-out.",
        tags=["reconciliation"],
    ),
    _item(
        id="fin-dim-01",
        task="Daily returns have std 0.012. A risk report needs ANNUALIZED volatility (252 "
             "trading days). The arm reports a number and its unit.",
        candidate="annualized_volatility",
        checker="dimensional_consistency",
        reference={"expected_unit": "annualized_volatility"},
        correct=True,
        rationale="correct unit: the report asked for annualized vol and the candidate labels "
                  "it as such (0.012 * sqrt(252)).",
        tags=["volatility", "units"],
    ),
    _item(
        id="fin-dim-02",
        task="Daily returns std 0.012. Risk report needs ANNUALIZED volatility. Arm reports a "
             "number and its unit.",
        candidate="daily_volatility",
        checker="dimensional_consistency",
        reference={"expected_unit": "annualized_volatility"},
        correct=False,
        rationale="wrong unit: returned the daily vol (0.012) labeled daily where annualized "
                  "was required. Numerically 'a volatility', dimensionally wrong by sqrt(252).",
        tags=["volatility", "units"],
    ),
    _item(
        id="fin-alloc-01",
        task="Allocate 100 units of capital across A, B, C. Limits: A<=40, B<=50, C<=30, total "
             "must equal 100, all nonnegative. Proposed: A=40, B=30, C=30.",
        candidate={"A": 40.0, "B": 30.0, "C": 30.0},
        checker="constraint_satisfaction",
        reference={"constraints": [("le", "A", 40.0), ("le", "B", 50.0), ("le", "C", 30.0),
                                   ("nonneg", "A"), ("nonneg", "B"), ("nonneg", "C"),
                                   ("eq_sum", ["A", "B", "C"], 100.0)]},
        correct=True,
        rationale="correct: 40+30+30 = 100 and every limit holds.",
        tags=["allocation", "constraints"],
    ),
    _item(
        id="fin-alloc-02",
        task="Same allocation problem as fin-alloc-01. Proposed: A=45, B=25, C=30.",
        candidate={"A": 45.0, "B": 25.0, "C": 30.0},
        checker="constraint_satisfaction",
        reference={"constraints": [("le", "A", 40.0), ("le", "B", 50.0), ("le", "C", 30.0),
                                   ("nonneg", "A"), ("nonneg", "B"), ("nonneg", "C"),
                                   ("eq_sum", ["A", "B", "C"], 100.0)]},
        correct=False,
        rationale="wrong: sums to 100 but A=45 breaches the A<=40 limit. The total ties out, "
                  "which is what a quick self-check looks at, so the breach slips through.",
        tags=["allocation", "constraints"],
    ),
    _item(
        id="fin-limit-01",
        task="A desk has a single-name concentration limit of 25% of a 200M book = 50M. "
             "Current single-name exposure 48M. Proposed add 5M. Is the resulting position "
             "(report it) within limit, and what is it?",
        candidate={"exposure": 53.0, "limit": 50.0},
        checker="constraint_satisfaction",
        reference={"constraints": [("le", "exposure", 50.0)]},
        correct=False,
        rationale="wrong: 48 + 5 = 53M exceeds the 50M limit; the candidate reports the "
                  "numbers but the position itself breaches. (Checker evaluates the breach.)",
        tags=["limits", "credit"],
    ),
    _item(
        id="fin-limit-02",
        task="Same limit as fin-limit-01 but proposed add is 1M (48 + 1 = 49M).",
        candidate={"exposure": 49.0, "limit": 50.0},
        checker="constraint_satisfaction",
        reference={"constraints": [("le", "exposure", 50.0)]},
        correct=True,
        rationale="correct: 49M is within the 50M limit.",
        tags=["limits", "credit"],
    ),
    _item(
        id="fin-lgd-01",
        task="Expected loss = PD * LGD * EAD. PD 2%, LGD 45%, EAD 1,000,000. Expected loss?",
        candidate=9000.0,
        checker="numeric_equals",
        reference={"truth": 9000.0, "abs_tol": 0.01},
        correct=True,
        rationale="correct: 0.02 * 0.45 * 1,000,000 = 9,000. Truth re-derived in the rationale "
                  "and asserted at build time against the checker.",
        tags=["credit", "expected-loss"],
    ),
    _item(
        id="fin-lgd-02",
        task="Expected loss = PD * LGD * EAD. PD 2%, LGD 45%, EAD 1,000,000. Expected loss?",
        candidate=20000.0,
        checker="numeric_equals",
        reference={"truth": 9000.0, "abs_tol": 0.01},
        correct=False,
        rationale="wrong: PD * EAD only, omitting LGD (0.02 * 1,000,000 = 20,000). A dropped "
                  "factor that produces a clean round number, which feels right.",
        tags=["credit", "expected-loss"],
    ),
    _item(
        id="fin-sharpe-01",
        task="Annual return 12%, risk-free 2%, annual volatility 16%. Sharpe ratio?",
        candidate=0.625,
        checker="numeric_equals",
        reference={"truth": 0.625, "abs_tol": 1e-6},
        correct=True,
        rationale="correct: (0.12 - 0.02) / 0.16 = 0.625.",
        tags=["performance"],
    ),
    _item(
        id="fin-sharpe-02",
        task="Annual return 12%, risk-free 2%, annual volatility 16%. Sharpe ratio?",
        candidate=0.75,
        checker="numeric_equals",
        reference={"truth": 0.625, "abs_tol": 1e-6},
        correct=False,
        rationale="wrong: forgot to subtract the risk-free rate (0.12 / 0.16 = 0.75). Common "
                  "Sharpe error; the number is in a believable range.",
        tags=["performance"],
    ),
    _item(
        id="fin-bond-01",
        task="A zero-coupon bond pays 1,000 in 5 years. Yield 4% annual compounding. Price?",
        candidate=821.93,
        checker="numeric_equals",
        reference={"truth": 821.927, "abs_tol": 0.01},
        correct=True,
        rationale="correct: 1000 / 1.04^5 = 821.93.",
        tags=["bonds", "discounting"],
    ),
    _item(
        id="fin-bond-02",
        task="A zero-coupon bond pays 1,000 in 5 years. Yield 4% annual compounding. Price?",
        candidate=833.33,
        checker="numeric_equals",
        reference={"truth": 821.927, "abs_tol": 0.01},
        correct=False,
        rationale="wrong: discounted with simple interest (1000 / (1 + 0.04*5) = 833.33) "
                  "instead of compound. Within 1.5% of right, so it survives a glance.",
        tags=["bonds", "discounting"],
    ),
]


# ============================================================================================
# GENERAL CODE / LOGIC lane (so the benchmark is not domain-locked)
# ============================================================================================

_CODE: List[Item] = [
    _item(
        id="code-binsearch-01",
        task="Write binary_search(arr, target) returning the index of target in a sorted list, "
             "or -1 if absent.",
        candidate=(
            "def binary_search(arr, target):\n"
            "    lo, hi = 0, len(arr) - 1\n"
            "    while lo <= hi:\n"
            "        mid = (lo + hi) // 2\n"
            "        if arr[mid] == target:\n"
            "            return mid\n"
            "        if arr[mid] < target:\n"
            "            lo = mid + 1\n"
            "        else:\n"
            "            hi = mid - 1\n"
            "    return -1\n"
        ),
        checker="python_eval",
        reference={"entrypoint": "binary_search", "cases": [
            [[[1, 3, 5, 7, 9], 7], 3], [[[1, 3, 5, 7, 9], 1], 0],
            [[[1, 3, 5, 7, 9], 9], 4], [[[1, 3, 5, 7, 9], 4], -1],
            [[[], 1], -1], [[[2], 2], 0],
        ]},
        correct=True,
        rationale="correct: standard binary search, boundaries right, empty list handled.",
        tags=["code", "search"],
    ),
    _item(
        id="code-binsearch-02",
        task="Same spec as code-binsearch-01.",
        candidate=(
            "def binary_search(arr, target):\n"
            "    lo, hi = 0, len(arr) - 1\n"
            "    while lo < hi:\n"
            "        mid = (lo + hi) // 2\n"
            "        if arr[mid] == target:\n"
            "            return mid\n"
            "        if arr[mid] < target:\n"
            "            lo = mid + 1\n"
            "        else:\n"
            "            hi = mid - 1\n"
            "    return -1\n"
        ),
        checker="python_eval",
        reference={"entrypoint": "binary_search", "cases": [
            [[[1, 3, 5, 7, 9], 7], 3], [[[1, 3, 5, 7, 9], 1], 0],
            [[[1, 3, 5, 7, 9], 9], 4], [[[1, 3, 5, 7, 9], 4], -1],
            [[[], 1], -1], [[[2], 2], 0],
        ]},
        correct=False,
        rationale="wrong: `while lo < hi` (should be <=) misses the target when it sits at the "
                  "final collapsed index, for example searching for 9 or 2. Most cases pass, "
                  "which is exactly why a self-critic signs off on it.",
        tags=["code", "search", "off-by-one"],
    ),
    _item(
        id="code-pct-01",
        task="Write pct_change(old, new) returning the percent change from old to new as a "
             "float, with pct_change(50, 75) == 50.0.",
        candidate=(
            "def pct_change(old, new):\n"
            "    return (new - old) / old * 100\n"
        ),
        checker="python_eval",
        reference={"entrypoint": "pct_change", "cases": [
            [[50, 75], 50.0], [[100, 50], -50.0], [[10, 11], 10.0],
        ]},
        correct=True,
        rationale="correct: (new-old)/old*100 with the right denominator.",
        tags=["code", "arithmetic"],
    ),
    _item(
        id="code-pct-02",
        task="Same spec as code-pct-01.",
        candidate=(
            "def pct_change(old, new):\n"
            "    return (new - old) / new * 100\n"
        ),
        checker="python_eval",
        reference={"entrypoint": "pct_change", "cases": [
            [[50, 75], 50.0], [[100, 50], -50.0], [[10, 11], 10.0],
        ]},
        correct=False,
        rationale="wrong: divides by `new` not `old`. pct_change(50,75) returns 33.3, not 50. "
                  "Reads natural and is a frequent real bug.",
        tags=["code", "arithmetic"],
    ),
    _item(
        id="code-compound-01",
        task="Write fv(pv, rate, n) for annually-compounded future value, fv(1000, 0.1, 2) == "
             "1210.0.",
        candidate=(
            "def fv(pv, rate, n):\n"
            "    return pv * (1 + rate) ** n\n"
        ),
        checker="python_eval",
        reference={"entrypoint": "fv", "cases": [
            [[1000, 0.1, 2], 1210.0], [[1000, 0.0, 5], 1000.0],
            [[500, 0.05, 0], 500.0],
        ]},
        correct=True,
        rationale="correct: compound formula, handles n=0 and rate=0.",
        tags=["code", "finance"],
    ),
    _item(
        id="code-compound-02",
        task="Same spec as code-compound-01.",
        candidate=(
            "def fv(pv, rate, n):\n"
            "    return pv * (1 + rate * n)\n"
        ),
        checker="python_eval",
        reference={"entrypoint": "fv", "cases": [
            [[1000, 0.1, 2], 1210.0], [[1000, 0.0, 5], 1000.0],
            [[500, 0.05, 0], 500.0],
        ]},
        correct=False,
        rationale="wrong: simple interest, fv(1000,0.1,2) returns 1200 not 1210. Passes the "
                  "n=0 and rate=0 cases, so it looks tested.",
        tags=["code", "finance"],
    ),
    _item(
        id="code-clamp-01",
        task="Write clamp(x, lo, hi) returning x constrained to [lo, hi].",
        candidate=(
            "def clamp(x, lo, hi):\n"
            "    return max(lo, min(x, hi))\n"
        ),
        checker="python_eval",
        reference={"entrypoint": "clamp", "cases": [
            [[5, 0, 10], 5], [[-3, 0, 10], 0], [[15, 0, 10], 10], [[10, 0, 10], 10],
        ]},
        correct=True,
        rationale="correct: max(lo, min(x, hi)) is the standard clamp.",
        tags=["code", "logic"],
    ),
    _item(
        id="code-clamp-02",
        task="Same spec as code-clamp-01.",
        candidate=(
            "def clamp(x, lo, hi):\n"
            "    return min(lo, max(x, hi))\n"
        ),
        checker="python_eval",
        reference={"entrypoint": "clamp", "cases": [
            [[5, 0, 10], 5], [[-3, 0, 10], 0], [[15, 0, 10], 10], [[10, 0, 10], 10],
        ]},
        correct=False,
        rationale="wrong: lo and hi swapped in the min/max nesting; collapses to lo for in-range "
                  "inputs. The shape looks like a clamp, which is the trap.",
        tags=["code", "logic"],
    ),
    _item(
        id="code-sql-01",
        task="Select ids of rows where amount is at least 100 AND region is 'US'. Express the "
             "WHERE clause.",
        candidate="amount >= 100 AND region = 'US'",
        checker="sql_predicate",
        reference={"rows": [
            {"id": 1, "amount": 100, "region": "US"},
            {"id": 2, "amount": 150, "region": "EU"},
            {"id": 3, "amount": 99, "region": "US"},
            {"id": 4, "amount": 200, "region": "US"},
        ], "expected_ids": [1, 4]},
        correct=True,
        rationale="correct: inclusive >= 100 and region match select ids 1 and 4.",
        tags=["code", "sql"],
    ),
    _item(
        id="code-sql-02",
        task="Same spec as code-sql-01 (at least 100, so 100 is included).",
        candidate="amount > 100 AND region = 'US'",
        checker="sql_predicate",
        reference={"rows": [
            {"id": 1, "amount": 100, "region": "US"},
            {"id": 2, "amount": 150, "region": "EU"},
            {"id": 3, "amount": 99, "region": "US"},
            {"id": 4, "amount": 200, "region": "US"},
        ], "expected_ids": [1, 4]},
        correct=False,
        rationale="wrong: strict > 100 drops id 1 (amount exactly 100). The inclusive/exclusive "
                  "boundary error is the canonical SQL filter bug a self-review misses.",
        tags=["code", "sql", "boundary"],
    ),
    _item(
        id="code-sql-03",
        task="Select ids where region is 'US' OR amount is over 180. WHERE clause.",
        candidate="region = 'US' OR amount > 180",
        checker="sql_predicate",
        reference={"rows": [
            {"id": 1, "amount": 100, "region": "US"},
            {"id": 2, "amount": 190, "region": "EU"},
            {"id": 3, "amount": 50, "region": "JP"},
            {"id": 4, "amount": 200, "region": "US"},
        ], "expected_ids": [1, 2, 4]},
        correct=True,
        rationale="correct: ids 1 and 4 are US, id 2 is over 180; union is {1,2,4}.",
        tags=["code", "sql"],
    ),
    _item(
        id="code-fizz-01",
        task="Write classify(n): 'fizzbuzz' if divisible by 15, 'fizz' by 3, 'buzz' by 5, else "
             "str(n).",
        candidate=(
            "def classify(n):\n"
            "    if n % 15 == 0:\n"
            "        return 'fizzbuzz'\n"
            "    if n % 3 == 0:\n"
            "        return 'fizz'\n"
            "    if n % 5 == 0:\n"
            "        return 'buzz'\n"
            "    return str(n)\n"
        ),
        checker="python_eval",
        reference={"entrypoint": "classify", "cases": [
            [[15], "fizzbuzz"], [[9], "fizz"], [[10], "buzz"], [[7], "7"], [[30], "fizzbuzz"],
        ]},
        correct=True,
        rationale="correct: 15-divisibility checked first, so precedence holds.",
        tags=["code", "logic"],
    ),
    _item(
        id="code-fizz-02",
        task="Same spec as code-fizz-01.",
        candidate=(
            "def classify(n):\n"
            "    if n % 3 == 0:\n"
            "        return 'fizz'\n"
            "    if n % 5 == 0:\n"
            "        return 'buzz'\n"
            "    if n % 15 == 0:\n"
            "        return 'fizzbuzz'\n"
            "    return str(n)\n"
        ),
        checker="python_eval",
        reference={"entrypoint": "classify", "cases": [
            [[15], "fizzbuzz"], [[9], "fizz"], [[10], "buzz"], [[7], "7"], [[30], "fizzbuzz"],
        ]},
        correct=False,
        rationale="wrong: order means 15 returns 'fizz' (the %3 branch fires first), never "
                  "reaching 'fizzbuzz'. The dead branch looks complete on a read.",
        tags=["code", "logic", "ordering"],
    ),
    _item(
        id="code-mean-01",
        task="Write running_mean(xs) returning the arithmetic mean of a non-empty list.",
        candidate=(
            "def running_mean(xs):\n"
            "    return sum(xs) / len(xs)\n"
        ),
        checker="python_eval",
        reference={"entrypoint": "running_mean", "cases": [
            [[[2, 4, 6]], 4.0], [[[5]], 5.0], [[[1, 2]], 1.5],
        ]},
        correct=True,
        rationale="correct: sum over count.",
        tags=["code", "arithmetic"],
    ),
    _item(
        id="code-mean-02",
        task="Same spec as code-mean-01.",
        candidate=(
            "def running_mean(xs):\n"
            "    return sum(xs) / (len(xs) - 1)\n"
        ),
        checker="python_eval",
        reference={"entrypoint": "running_mean", "cases": [
            [[[2, 4, 6]], 4.0], [[[5]], 5.0], [[[1, 2]], 1.5],
        ]},
        correct=False,
        rationale="wrong: divides by n-1 (a sample-variance reflex), so the mean is off and a "
                  "one-element list divides by zero. Looks statistical, which disarms the critic.",
        tags=["code", "arithmetic"],
    ),
]


# ============================================================================================
# NEGATIVE CONTROLS: soft / low-materiality items the guard should leave alone.
# These exist to confirm the arms and the guard do not fire outside the governed regime.
# Their checkers still decide correctness, but the guard verdict on them is ALLOW.
# ============================================================================================

_CONTROLS: List[Item] = [
    _item(
        id="ctl-soft-01",
        task="Suggest a friendly tone for a marketing tagline (open-ended, reversible).",
        candidate=42.0,  # placeholder value; correctness here is not the point of a control
        checker="numeric_equals",
        reference={"truth": 42.0},
        correct=True,
        rationale="control: soft + low materiality. The guard should ALLOW without an "
                  "independent check; included to confirm the guard stays out of the way.",
        task_type=SOFT,
        materiality=LOW,
        tags=["control", "soft"],
    ),
    _item(
        id="ctl-soft-02",
        task="Pick a color for a non-critical UI accent (reversible, low stakes).",
        candidate=7.0,
        checker="numeric_equals",
        reference={"truth": 7.0},
        correct=True,
        rationale="control: soft + low. Guard ALLOWs. Negative control for the routing.",
        task_type=SOFT,
        materiality=LOW,
        tags=["control", "soft"],
    ),
]


ALL_ITEMS: List[Item] = _FINANCE + _CODE + _CONTROLS

# The governed slice: the items the Not So Fast rule actually fires on (hard + high). These
# are the items that carry the benchmark's central claim. Controls are excluded.
GOVERNED_ITEMS: List[Item] = [
    it for it in ALL_ITEMS if it.task_type == HARD and it.materiality == HIGH
]


def dataset_stats() -> Dict[str, Any]:
    """Summary counts used by the runner header and by the dataset self-test."""
    governed = GOVERNED_ITEMS
    n_correct = sum(1 for it in governed if it.correct)
    return {
        "n_total": len(ALL_ITEMS),
        "n_governed": len(governed),
        "n_controls": len(ALL_ITEMS) - len(governed),
        "n_governed_correct": n_correct,
        "n_governed_wrong": len(governed) - n_correct,
        "lanes": sorted({it.id.split("-")[0] for it in governed}),
    }


def self_check() -> None:
    """Assert every stored `correct` label matches its checker. The integrity gate.

    This runs at import time so a typo in a candidate or a stale label fails loudly the moment
    the dataset is loaded, rather than silently corrupting the metrics. It is the dataset's own
    conformance test: the labels are not trusted, they are verified against the oracle.
    """
    for it in ALL_ITEMS:
        derived = it.check()
        if derived != it.correct:
            raise AssertionError(
                f"item {it.id}: stored correct={it.correct} but checker says {derived}. "
                f"Fix the candidate, the reference, or the label."
            )


# Verify the dataset against its own checkers as soon as it is imported.
self_check()
