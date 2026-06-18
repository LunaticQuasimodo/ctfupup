#!/usr/bin/env python3
"""Create an initial CTFRunState JSON file."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a CTFRunState file")
    parser.add_argument("--title", required=True)
    parser.add_argument("--category", default="unknown")
    parser.add_argument("--platform", default="unknown")
    parser.add_argument("--flag-format", default="unknown")
    parser.add_argument("--out", default="ctf-state.json")
    args = parser.parse_args()

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    state = {
        "schema": "ctf-run-state-v1",
        "created_at": now,
        "updated_at": now,
        "challenge": {
            "title": args.title,
            "platform": args.platform,
            "category_claimed": args.category,
            "category_inferred": "unknown",
            "category_confidence": "low",
            "description": "",
            "flag_format": args.flag_format,
            "rules": [],
            "targets": [],
            "attachments": [],
            "credentials": [],
            "scope_status": "unknown_needs_confirmation",
        },
        "environment": {},
        "evidence": [],
        "known_facts": [],
        "hypotheses": [],
        "attempts": [],
        "dead_ends": [],
        "artifacts": [],
        "anti_injection_findings": [],
        "next_actions": [],
        "handoff_ready": False,
    }

    out = Path(args.out)
    out.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
