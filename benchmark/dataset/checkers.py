"""Ground-truth checkers for the Not So Fast benchmark.

A checker is the ONLY source of truth about whether a candidate answer is correct. It is a
pure Python function that takes the parsed candidate value and the item's reference data and
returns True (correct) or False (wrong). It never asks a model. This is the property that
makes the benchmark falsifiable rather than circular: correctness is decided by arithmetic,
not by an opinion that could itself be wrong.

Design rules for every checker here:
  - Deterministic. Same inputs, same verdict, no randomness, no clock, no network.
  - Tolerance is explicit. Floating-point answers compare with a stated absolute or relative
    tolerance, declared per item, so "close enough" is a number, not a vibe.
  - The checker is independent of how the candidate was produced. It re-derives the right
    answer (or re-checks a stated invariant) from the task's inputs, then compares.

Each checker is registered by name. A dataset item names its checker and supplies the
reference inputs the checker needs. The arms never see the checker; only the runner calls it,
after the arms have rendered their verdicts. That separation is what lets us measure whether a
verification arm agrees with ground truth without leaking ground truth to the arm.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, Mapping

# A checker takes (candidate_value, reference) and returns True iff the candidate is correct.
Checker = Callable[[Any, Mapping[str, Any]], bool]

_REGISTRY: Dict[str, Checker] = {}


def checker(name: str) -> Callable[[Checker], Checker]:
    """Register a checker under a stable name used by dataset items."""

    def wrap(fn: Checker) -> Checker:
        if name in _REGISTRY:
            raise ValueError(f"duplicate checker name {name!r}")
        _REGISTRY[name] = fn
        return fn

    return wrap


def get_checker(name: str) -> Checker:
    if name not in _REGISTRY:
        raise KeyError(f"no checker registered under {name!r}")
    return _REGISTRY[name]


def _close(a: float, b: float, abs_tol: float = 0.0, rel_tol: float = 0.0) -> bool:
    """True if a and b agree within the stated absolute OR relative tolerance.

    Both default to zero, so a checker that forgets to pass a tolerance demands exact
    equality. That is the safe direction: a missing tolerance fails a candidate rather than
    waving it through.
    """
    if abs_tol and abs(a - b) <= abs_tol:
        return True
    if rel_tol and abs(a - b) <= rel_tol * max(abs(a), abs(b)):
        return True
    return a == b


# --- Finance / quant checkers ---------------------------------------------------------------


@checker("numeric_equals")
def numeric_equals(candidate: Any, ref: Mapping[str, Any]) -> bool:
    """Candidate scalar must equal ref['truth'] within ref's tolerance.

    The truth is re-stated in the reference, but every dataset item that uses this checker
    documents how that truth was derived (a closed-form formula or an independent computation),
    so the number is auditable, not asserted. Items that need the truth derived in-checker use
    the dedicated checkers below instead.
    """
    truth = float(ref["truth"])
    return _close(
        float(candidate),
        truth,
        abs_tol=float(ref.get("abs_tol", 0.0)),
        rel_tol=float(ref.get("rel_tol", 0.0)),
    )


@checker("put_call_parity")
def put_call_parity(candidate: Any, ref: Mapping[str, Any]) -> bool:
    """Re-derive the put price from put-call parity and compare to the candidate.

    Parity: C - P = S - K * exp(-r * T). So the correct put is
        P = C - S + K * exp(-r * T).
    The checker recomputes P from the item's (C, S, K, r, T) and compares, so the truth is the
    formula, not a stored number. Catches candidates that drop the discount factor or flip a
    sign, which is exactly the plausible-but-wrong pattern a self-critic tends to ratify.
    """
    c = float(ref["call"])
    s = float(ref["spot"])
    k = float(ref["strike"])
    r = float(ref["rate"])
    t = float(ref["maturity"])
    put = c - s + k * math.exp(-r * t)
    return _close(float(candidate), put, abs_tol=float(ref.get("abs_tol", 1e-4)))


@checker("var_aggregation")
def var_aggregation(candidate: Any, ref: Mapping[str, Any]) -> bool:
    """Re-derive aggregated VaR for two books and compare.

    For two normally-distributed books with standalone VaRs v1, v2 and correlation rho, the
    aggregated VaR is
        sqrt(v1^2 + v2^2 + 2 * rho * v1 * v2).
    Naive addition (v1 + v2) is only correct at rho = 1 and otherwise overstates risk; that is
    the classic error this item catches. The checker recomputes from (v1, v2, rho).
    """
    v1 = float(ref["var1"])
    v2 = float(ref["var2"])
    rho = float(ref["rho"])
    agg = math.sqrt(v1 * v1 + v2 * v2 + 2.0 * rho * v1 * v2)
    return _close(float(candidate), agg, rel_tol=float(ref.get("rel_tol", 1e-4)))


@checker("amortization_payment")
def amortization_payment(candidate: Any, ref: Mapping[str, Any]) -> bool:
    """Re-derive the level payment on an amortizing loan and compare.

    Standard annuity payment for principal P, periodic rate i, n periods:
        A = P * i / (1 - (1 + i)^(-n))           for i != 0
        A = P / n                                  for i == 0
    The reference carries the ANNUAL rate and the period count per year, so the checker also
    catches the common error of forgetting to convert the annual rate to a periodic one.
    """
    principal = float(ref["principal"])
    annual_rate = float(ref["annual_rate"])
    periods = int(ref["periods"])
    per_year = int(ref.get("periods_per_year", 12))
    i = annual_rate / per_year
    if i == 0:
        payment = principal / periods
    else:
        payment = principal * i / (1.0 - (1.0 + i) ** (-periods))
    return _close(float(candidate), payment, abs_tol=float(ref.get("abs_tol", 0.01)))


@checker("compound_growth")
def compound_growth(candidate: Any, ref: Mapping[str, Any]) -> bool:
    """Re-derive a compounded future value and compare.

    FV = PV * (1 + r) ** n. Catches simple-interest-instead-of-compound errors and
    off-by-one period errors.
    """
    pv = float(ref["present_value"])
    r = float(ref["rate"])
    n = int(ref["periods"])
    fv = pv * (1.0 + r) ** n
    return _close(float(candidate), fv, rel_tol=float(ref.get("rel_tol", 1e-6)))


@checker("reconciliation_sum")
def reconciliation_sum(candidate: Any, ref: Mapping[str, Any]) -> bool:
    """The candidate total must equal the sum of the line items within tolerance.

    A reconciliation item ships a list of components and a claimed total. The checker sums the
    components itself. Catches a dropped line or a transposed digit in the claimed total.
    """
    components = [float(x) for x in ref["components"]]
    return _close(float(candidate), sum(components), abs_tol=float(ref.get("abs_tol", 0.005)))


@checker("dimensional_consistency")
def dimensional_consistency(candidate: Any, ref: Mapping[str, Any]) -> bool:
    """The candidate's stated unit must match the unit implied by the operation.

    The reference gives the operation's expected output unit (derived from the input units and
    the operator). The candidate is the unit string the answer claims. Catches answers that are
    numerically plausible but dimensionally wrong, for example reporting an annualized
    volatility where a daily one is required, or a rate where a price is required.
    """
    return str(candidate).strip().lower() == str(ref["expected_unit"]).strip().lower()


@checker("constraint_satisfaction")
def constraint_satisfaction(candidate: Any, ref: Mapping[str, Any]) -> bool:
    """Candidate is a dict of variable assignments; all listed constraints must hold.

    Each constraint is a tuple (kind, *args). The checker evaluates them against the
    assignment. Constraints supported:
      ("le", var, bound)        : candidate[var] <= bound
      ("ge", var, bound)        : candidate[var] >= bound
      ("eq_sum", [vars], total) : sum(candidate[v] for v in vars) == total (with tol)
      ("nonneg", var)           : candidate[var] >= 0
    This models allocation, limit, and budget problems where a plausible answer violates one
    constraint the proposer glossed over.
    """
    assign = dict(candidate)
    tol = float(ref.get("abs_tol", 1e-9))
    for cons in ref["constraints"]:
        kind = cons[0]
        if kind == "le":
            if not assign[cons[1]] <= cons[2] + tol:
                return False
        elif kind == "ge":
            if not assign[cons[1]] >= cons[2] - tol:
                return False
        elif kind == "nonneg":
            if not assign[cons[1]] >= -tol:
                return False
        elif kind == "eq_sum":
            if not _close(sum(assign[v] for v in cons[1]), float(cons[2]), abs_tol=max(tol, 1e-6)):
                return False
        else:
            raise ValueError(f"unknown constraint kind {kind!r}")
    return True


# --- General code / logic checkers ----------------------------------------------------------


@checker("python_eval")
def python_eval(candidate: Any, ref: Mapping[str, Any]) -> bool:
    """Run the candidate's function body against a fixed input/output table.

    The candidate is the SOURCE of a single function whose name is ref['entrypoint']. The
    checker execs it in a restricted namespace (no builtins beyond a tiny safe set), then calls
    it on each (args, expected) case in ref['cases']. The function is the candidate's claimed
    solution; the cases are the ground truth. This catches off-by-one and edge-case bugs that a
    same-context self-critic reading its own code typically rationalizes.

    Safety: the candidate code in this dataset is authored by us, not by a model, and runs with
    a minimal builtins set. A real run that wires a model into the arms would still only EVAL
    candidate verdicts (correct / wrong), never exec model-authored code; the python_eval items
    exist so the harness can exercise a code-correctness lane deterministically.
    """
    src = str(candidate)
    entry = ref["entrypoint"]
    safe_builtins = {
        "len": len, "range": range, "min": min, "max": max, "abs": abs,
        "sum": sum, "sorted": sorted, "enumerate": enumerate, "int": int,
        "float": float, "str": str, "list": list, "dict": dict, "set": set,
        "bool": bool, "round": round, "zip": zip, "any": any, "all": all,
    }
    namespace: Dict[str, Any] = {"__builtins__": safe_builtins}
    try:
        exec(src, namespace)  # noqa: S102 - sandboxed builtins, dataset-authored source only
    except Exception:
        return False
    fn = namespace.get(entry)
    if not callable(fn):
        return False
    float_tol = float(ref.get("float_tol", 1e-9))
    for args, expected in ref["cases"]:
        try:
            got = fn(*args)
        except Exception:
            return False
        # Floats compare within a tolerance so legitimate rounding does not fail a correct
        # function; everything else compares exactly.
        if isinstance(expected, float) and isinstance(got, (int, float)):
            if abs(got - expected) > float_tol:
                return False
        elif got != expected:
            return False
    return True


@checker("sql_predicate")
def sql_predicate(candidate: Any, ref: Mapping[str, Any]) -> bool:
    """Evaluate a candidate SQL WHERE clause against in-memory rows via a tiny safe evaluator.

    The candidate is a boolean expression over row columns (a stand-in for a WHERE clause),
    written in Python-compatible syntax (=, AND, OR translated). The checker compiles it once,
    runs it over ref['rows'], and compares the selected id set to ref['expected_ids']. This
    catches the classic inclusive/exclusive boundary error and the AND/OR precedence error in a
    filter, both of which read as correct to a self-critic.
    """
    expr = str(candidate)
    # translate a minimal SQL dialect to Python; intentionally narrow.
    py = expr.replace("<>", "!=")
    # convert standalone '=' (not '==', '<=', '>=', '!=') to '=='
    out = []
    i = 0
    while i < len(py):
        ch = py[i]
        if ch == "=" and (i == 0 or py[i - 1] not in "<>=!") and (i + 1 >= len(py) or py[i + 1] != "="):
            out.append("==")
        else:
            out.append(ch)
        i += 1
    py = "".join(out)
    py = _replace_word(py, "AND", "and")
    py = _replace_word(py, "OR", "or")
    py = _replace_word(py, "NOT", "not")
    try:
        code = compile(py, "<sql_predicate>", "eval")
    except SyntaxError:
        return False
    selected = set()
    for row in ref["rows"]:
        try:
            if eval(code, {"__builtins__": {}}, dict(row)):  # noqa: S307 - empty builtins, fixed cols
                selected.add(row["id"])
        except Exception:
            return False
    return selected == set(ref["expected_ids"])


def _replace_word(text: str, word: str, repl: str) -> str:
    """Replace whole-word occurrences of `word` (case-insensitive) with `repl`."""
    import re

    return re.sub(rf"\b{re.escape(word)}\b", repl, text, flags=re.IGNORECASE)
