#!/usr/bin/env python3
"""Single enforcement point for a workflow's health state (stdlib only).

Reads the `health` object ({"state": HEALTHY|DEGRADED|FAILED|NOT_APPLICABLE, "reasons": [...]}) from a
status JSON the job wrote, writes a GitHub step summary, and decides the job's colour:

  HEALTHY / NOT_APPLICABLE -> exit 0
  DEGRADED                 -> exit 0 with a ::warning:: annotation (never fail just to communicate)
  FAILED                   -> exit 1 with an ::error:: annotation
  status file missing, unparsable or without a health state -> exit 1 (fail closed: no evidence)

`--upstream-outcome` is the outcome of the step that should have written the status file. When that step
did not succeed (timed out, crashed, cancelled), the job is already red from that step; the gate records
FAILED in the summary and exits 0 so one problem does not produce two failing steps.

usage: health_gate.py <status.json> --label <workflow> [--upstream-outcome success|failure|cancelled|skipped]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

OK_STATES = {"HEALTHY", "NOT_APPLICABLE"}
KNOWN_STATES = OK_STATES | {"DEGRADED", "FAILED"}


def evaluate(status_path: Path, upstream_outcome: str = "success") -> tuple[str, list[str], int]:
    """Return (state, reasons, exit_code)."""
    if upstream_outcome != "success":
        return "FAILED", [f"upstream_step_{upstream_outcome}"], 0
    try:
        doc = json.loads(status_path.read_text())
    except FileNotFoundError:
        return "FAILED", ["status_missing"], 1
    except (OSError, ValueError) as exc:
        return "FAILED", [f"status_unreadable:{str(exc)[:80]}"], 1
    health = doc.get("health") if isinstance(doc, dict) else None
    state = health.get("state") if isinstance(health, dict) else None
    if state not in KNOWN_STATES:
        return "FAILED", [f"health_state_invalid:{state!r}"], 1
    reasons = [str(r) for r in (health.get("reasons") or [])]
    return state, reasons, (1 if state == "FAILED" else 0)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("status")
    ap.add_argument("--label", required=True)
    ap.add_argument("--upstream-outcome", default="success")
    a = ap.parse_args(argv)
    state, reasons, code = evaluate(Path(a.status), a.upstream_outcome)
    why = ", ".join(reasons) or "-"
    if state == "FAILED":
        print(f"::error::{a.label} health FAILED: {why}")
    elif state == "DEGRADED":
        print(f"::warning::{a.label} health DEGRADED: {why}")
    else:
        print(f"{a.label} health {state}: {why}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"## {a.label} health: {state}\n\n")
            for r in reasons:
                fh.write(f"- {r}\n")
            if code == 0 and state == "FAILED":
                fh.write("\n(the failing upstream step already marks this run red)\n")
            fh.write("\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
