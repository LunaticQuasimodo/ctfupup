#!/usr/bin/env python3
"""Normalize source notes into JSON lines."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys


FIELDS = [
    "source_name",
    "url_or_path",
    "source_type",
    "topic",
    "relevance",
    "core_claim",
    "borrowable_design",
    "do_not_blindly_copy",
    "skill_conversion",
    "credibility",
    "freshness",
    "local_verification_needed",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create one source-matrix JSONL record")
    for field in FIELDS:
        parser.add_argument(f"--{field.replace('_', '-')}", default="")
    args = parser.parse_args()
    record = {field: getattr(args, field) for field in FIELDS}
    record["recorded_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    if not record["source_name"] or not record["url_or_path"]:
        print("source_name and url_or_path are required", file=sys.stderr)
        return 2
    print(json.dumps(record, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
