#!/usr/bin/env python3
"""Update ChallengeProfile fields inside a CTFRunState file."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import mimetypes
from pathlib import Path
from typing import Any


ALLOWED_CONFIDENCE = {"low", "medium", "high"}
ALLOWED_SCOPE = {
    "unknown_needs_confirmation",
    "local_only",
    "authorized_remote",
    "authorized_lab",
    "benchmark_scope_pending",
    "local_authorized_benchmark",
}


def load_state(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def split_values(values: list[str]) -> list[str]:
    items: list[str] = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part:
                items.append(part)
    return items


def append_unique(items: list[Any], values: list[Any], *, key: str | None = None) -> int:
    before = len(items)
    if key:
        seen = {str(item.get(key, "")) for item in items if isinstance(item, dict)}
        for value in values:
            if not isinstance(value, dict):
                continue
            marker = str(value.get(key, ""))
            if marker and marker not in seen:
                items.append(value)
                seen.add(marker)
    else:
        seen = {json.dumps(item, sort_keys=True, ensure_ascii=False) for item in items}
        for value in values:
            marker = json.dumps(value, sort_keys=True, ensure_ascii=False)
            if marker not in seen:
                items.append(value)
                seen.add(marker)
    return len(items) - before


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_attachment(path_text: str, trust: str) -> dict[str, Any]:
    path = Path(path_text)
    item: dict[str, Any] = {"path": path_text, "trust": trust}
    if path.exists() and path.is_file():
        item["sha256"] = sha256_file(path)
        item["size"] = path.stat().st_size
        item["type"] = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    else:
        item["sha256"] = "unknown"
        item["size"] = 0
        item["type"] = "unknown"
        item["missing_at_update"] = True
    return item


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError("expected boolean true/false")


def main() -> int:
    parser = argparse.ArgumentParser(description="Update ChallengeProfile in a CTFRunState")
    parser.add_argument("--state", required=True)
    parser.add_argument("--title")
    parser.add_argument("--platform")
    parser.add_argument("--category-claimed")
    parser.add_argument("--category-inferred")
    parser.add_argument("--category-confidence", choices=sorted(ALLOWED_CONFIDENCE))
    parser.add_argument("--description")
    parser.add_argument("--flag-format")
    parser.add_argument("--scope-status", choices=sorted(ALLOWED_SCOPE))
    parser.add_argument("--add-target", action="append", default=[])
    parser.add_argument("--add-rule", action="append", default=[])
    parser.add_argument("--add-credential-note", action="append", default=[], help="Add sanitized credential description; do not store raw secrets")
    parser.add_argument("--add-attachment", action="append", default=[], help="Add local attachment path and compute sha256/size when present")
    parser.add_argument("--attachment-trust", default="untrusted")
    parser.add_argument("--handoff-ready", type=parse_bool)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    state_path = Path(args.state)
    state = load_state(state_path)
    challenge = state.setdefault("challenge", {})
    changes: list[str] = []

    field_map = {
        "title": args.title,
        "platform": args.platform,
        "category_claimed": args.category_claimed,
        "category_inferred": args.category_inferred,
        "category_confidence": args.category_confidence,
        "description": args.description,
        "flag_format": args.flag_format,
        "scope_status": args.scope_status,
    }
    for field, value in field_map.items():
        if value is not None and challenge.get(field) != value:
            challenge[field] = value
            changes.append(f"set challenge.{field}")

    for list_name, raw_values in [
        ("targets", args.add_target),
        ("rules", args.add_rule),
        ("credentials", args.add_credential_note),
    ]:
        values = split_values(raw_values)
        if values:
            challenge.setdefault(list_name, [])
            added = append_unique(challenge[list_name], values)
            if added:
                changes.append(f"added {added} challenge.{list_name}")

    attachments = [build_attachment(value, args.attachment_trust) for value in split_values(args.add_attachment)]
    if attachments:
        challenge.setdefault("attachments", [])
        added = append_unique(challenge["attachments"], attachments, key="path")
        if added:
            changes.append(f"added {added} challenge.attachments")

    if args.handoff_ready is not None and state.get("handoff_ready") != args.handoff_ready:
        state["handoff_ready"] = args.handoff_ready
        changes.append("set handoff_ready")

    write_state(state_path, state)
    result = {
        "schema": "ctf-profile-update-v1",
        "state_path": str(state_path),
        "changed": bool(changes),
        "changes": changes,
        "challenge": challenge,
        "handoff_ready": state.get("handoff_ready"),
    }
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"profile_update_changed={result['changed']}")
        for change in changes:
            print(change)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
