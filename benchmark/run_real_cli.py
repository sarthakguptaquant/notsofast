"""Driver for a REAL benchmark run wired to the local Claude CLI (subscription auth, no API
key, no paid API, no account creation).

This is intentionally a separate thin script rather than a change to run.py's argument parsing,
because run.py's `main()` currently builds `model_call=None` even when `--real` is passed (see
`build_arms` call site) -- passing a model_call through argparse would mean inventing a
provider-selection flag inside a file that is deliberately provider-neutral. Instead this script
does exactly what REPORT.md's "How to do a real run" step 2 describes: it imports `run()`
directly and passes a wired `model_call`.

Usage:
    python benchmark/run_real_cli.py                    # haiku, cap 500, writes results/
    python benchmark/run_real_cli.py --model haiku --cap 500 --seed 20260626

Degrade-on-failure: if the CLI is unavailable, or the call cap is hit before the run completes,
or any call errors out after retries, this script does NOT invent numbers. It catches the
failure, writes a wiring-status note (no results claimed), and exits non-zero so the caller
knows to report a degrade, per the plan's tripwire.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from arms.cli_adapter import CliCallCounter, make_cli_model_call  # noqa: E402
import run as run_mod  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Real notsofast benchmark run via local Claude CLI.")
    ap.add_argument("--model", default="haiku", help="CLI --model alias (default: haiku)")
    ap.add_argument("--cap", type=int, default=500, help="hard cap on total CLI calls")
    ap.add_argument("--seed", type=int, default=run_mod.DEFAULT_SEED)
    ap.add_argument("--json-only", action="store_true")
    args = ap.parse_args(argv)

    status_path = os.path.join(HERE, "results", "real-cli-wiring-status.json")
    os.makedirs(os.path.dirname(status_path), exist_ok=True)

    counter = CliCallCounter(cap=args.cap)
    scratch_cwd = "/private/tmp/claude-501/-Users-sarthak-Claude-Projects-O1/1a2ec3ac-fda2-4c44-b32c-1699ad3a36de/scratchpad/nsf-cli-cwd"
    os.makedirs(scratch_cwd, exist_ok=True)

    model_call = make_cli_model_call(model=args.model, counter=counter, cwd=scratch_cwd)

    started = time.time()
    try:
        result = run_mod.run(seed=args.seed, real=True, model_call=model_call)
    except Exception as exc:  # noqa: BLE001 - this IS the degrade path
        elapsed = time.time() - started
        status = {
            "wiring": "FAILED_MID_RUN",
            "model": args.model,
            "cap": args.cap,
            "calls_made_before_failure": counter.made,
            "elapsed_s": round(elapsed, 1),
            "error": str(exc),
            "traceback": traceback.format_exc()[-4000:],
            "note": (
                "Real CLI run did not complete. No results are claimed. This is the honest "
                "degrade artifact per the plan's tripwire, not a partial result."
            ),
        }
        with open(status_path, "w") as fh:
            json.dump(status, fh, indent=2)
        print(f"REAL RUN FAILED after {counter.made} calls ({elapsed:.1f}s): {exc}",
              file=sys.stderr)
        print(f"wrote {os.path.relpath(status_path, REPO)}", file=sys.stderr)
        return 1

    elapsed = time.time() - started
    out_path = os.path.join(HERE, "results", f"{result['run_id']}.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=2, default=str)

    status = {
        "wiring": "SUCCESS",
        "model": args.model,
        "cap": args.cap,
        "calls_made": counter.made,
        "elapsed_s": round(elapsed, 1),
        "results_path": os.path.relpath(out_path, REPO),
    }
    with open(status_path, "w") as fh:
        json.dump(status, fh, indent=2)

    if not args.json_only:
        run_mod.print_human(result)
        print(f"\ncalls made: {counter.made}/{args.cap}  elapsed: {elapsed:.1f}s")
        print(f"wrote {os.path.relpath(out_path, REPO)}")
        print(f"wrote {os.path.relpath(status_path, REPO)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
