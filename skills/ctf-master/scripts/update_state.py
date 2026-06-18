#!/usr/bin/env python3
"""Append structured records to a CTFRunState JSON file."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


KIND_TO_FIELD = {
    "evidence": "evidence",
    "fact": "known_facts",
    "hypothesis": "hypotheses",
    "attempt": "attempts",
    "dead_end": "dead_ends",
    "artifact": "artifacts",
    "anti_injection": "anti_injection_findings",
    "next_action": "next_actions",
}


PREFIX = {
    "evidence": "ev",
    "fact": "fact",
    "hypothesis": "hyp",
    "attempt": "att",
    "dead_end": "dead",
    "artifact": "art",
    "anti_injection": "inj",
    "next_action": "next",
}


def next_id(items: list[Any], prefix: str) -> str:
    max_seen = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        value = str(item.get("id", ""))
        if value.startswith(prefix + "-"):
            try:
                max_seen = max(max_seen, int(value.split("-", 1)[1]))
            except ValueError:
                pass
    return f"{prefix}-{max_seen + 1:03d}"


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def build_record(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    field = KIND_TO_FIELD[args.kind]
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    record_id = args.id or next_id(state.get(field, []), PREFIX[args.kind])
    base = {
        "id": record_id,
        "timestamp": now,
        "summary": args.summary,
    }
    if args.kind == "evidence":
        base.update({
            "actor": args.actor,
            "action": args.action,
            "purpose": args.purpose,
            "inputs": args.inputs,
            "raw_artifact": args.raw_artifact,
            "exit_status": args.exit_status,
            "supports": split_csv(args.supports),
            "contradicts": split_csv(args.contradicts),
            "risk": args.risk,
        })
    elif args.kind == "hypothesis":
        base.update({
            "confidence": args.confidence,
            "next_experiment": args.next_experiment,
            "evidence": split_csv(args.evidence_ids),
        })
    elif args.kind == "fact":
        base.update({"evidence": split_csv(args.evidence_ids)})
    elif args.kind == "dead_end":
        base.update({
            "reason": args.reason,
            "evidence": split_csv(args.evidence_ids),
            "revisit_condition": args.revisit_condition,
        })
    elif args.kind == "artifact":
        base.update({
            "path": args.path,
            "artifact_type": args.artifact_type,
            "evidence": split_csv(args.evidence_ids),
        })
    elif args.kind == "attempt":
        base.update({
            "action": args.action,
            "outcome": args.outcome,
            "evidence": split_csv(args.evidence_ids),
        })
    elif args.kind == "next_action":
        base.update({"priority": args.priority})
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description="Append a record to CTFRunState")
    parser.add_argument("--state", required=True)
    parser.add_argument("--kind", choices=sorted(KIND_TO_FIELD), required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--id", default="")
    parser.add_argument("--actor", default="agent")
    parser.add_argument("--action", default="")
    parser.add_argument("--purpose", default="")
    parser.add_argument("--inputs", default="")
    parser.add_argument("--raw-artifact", default="")
    parser.add_argument("--exit-status", default="")
    parser.add_argument("--supports", default="")
    parser.add_argument("--contradicts", default="")
    parser.add_argument("--risk", default="none")
    parser.add_argument("--confidence", choices=["low", "medium", "high"], default="low")
    parser.add_argument("--next-experiment", default="")
    parser.add_argument("--evidence-ids", default="")
    parser.add_argument("--reason", default="")
    parser.add_argument("--revisit-condition", default="")
    parser.add_argument("--path", default="")
    parser.add_argument("--artifact-type", default="")
    parser.add_argument("--outcome", default="")
    parser.add_argument("--priority", choices=["low", "medium", "high"], default="medium")
    args = parser.parse_args()

    state_path = Path(args.state)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    field = KIND_TO_FIELD[args.kind]
    state.setdefault(field, [])
    record = build_record(args, state)
    if args.kind == "next_action" and len(state[field]) >= 5:
        state[field] = state[field][-4:]
    state[field].append(record)
    state["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
