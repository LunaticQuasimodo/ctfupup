#!/usr/bin/env python3
"""Validate a CTFRunState JSON file for resumability and evidence integrity."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


SUITE_ROOT = Path(__file__).resolve().parents[3]

TOP_LEVEL_FIELDS = [
    "schema",
    "created_at",
    "updated_at",
    "challenge",
    "environment",
    "evidence",
    "known_facts",
    "hypotheses",
    "attempts",
    "dead_ends",
    "artifacts",
    "anti_injection_findings",
    "next_actions",
    "handoff_ready",
]

CHALLENGE_FIELDS = [
    "title",
    "platform",
    "category_claimed",
    "category_inferred",
    "category_confidence",
    "description",
    "flag_format",
    "rules",
    "targets",
    "attachments",
    "credentials",
    "scope_status",
]

LIST_FIELDS = [
    "evidence",
    "known_facts",
    "hypotheses",
    "attempts",
    "dead_ends",
    "artifacts",
    "anti_injection_findings",
    "next_actions",
]

EVIDENCE_FIELDS = [
    "id",
    "timestamp",
    "actor",
    "action",
    "purpose",
    "inputs",
    "raw_artifact",
    "summary",
    "exit_status",
    "supports",
    "contradicts",
    "risk",
]

ALLOWED_CONFIDENCE = {"low", "medium", "high"}
ALLOWED_SCOPE = {
    "unknown_needs_confirmation",
    "local_only",
    "authorized_remote",
    "authorized_lab",
    "benchmark_scope_pending",
    "local_authorized_benchmark",
}


def load_json(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, [f"state file does not exist: {path}"]
    except json.JSONDecodeError as exc:
        return None, [f"invalid JSON: {exc}"]
    if not isinstance(data, dict):
        return None, ["state root must be a JSON object"]
    return data, []


def parse_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def ids_for(items: Any) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {str(item.get("id")) for item in items if isinstance(item, dict) and item.get("id")}


def split_artifact_paths(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,;]", value) if part.strip()]


def resolve_path(state_path: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    candidates = [
        Path.cwd() / path,
        SUITE_ROOT / path,
        state_path.parent / path,
    ]
    if path.parts and path.parts[0] == SUITE_ROOT.name:
        candidates.append(SUITE_ROOT.joinpath(*path.parts[1:]))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def validate_collection(name: str, items: Any, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(items, list):
        errors.append(f"{name} must be a list")
        return
    seen: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"{name}[{index}] must be an object")
            continue
        item_id = item.get("id")
        if not item_id:
            errors.append(f"{name}[{index}] missing id")
        elif item_id in seen:
            errors.append(f"{name} duplicate id {item_id}")
        else:
            seen.add(str(item_id))
        if "timestamp" in item and not parse_timestamp(item.get("timestamp")):
            warnings.append(f"{name}[{index}] has non-ISO timestamp")
        if not item.get("summary"):
            warnings.append(f"{name}[{index}] missing summary")


def validate_state(state_path: Path, strict_artifacts: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    state, load_errors = load_json(state_path)
    errors.extend(load_errors)
    if state is None:
        return {"schema": "ctf-run-state-validation-v1", "ok": False, "errors": errors, "warnings": warnings}

    for field in TOP_LEVEL_FIELDS:
        if field not in state:
            errors.append(f"missing top-level field {field}")
    if state.get("schema") != "ctf-run-state-v1":
        errors.append("schema must be ctf-run-state-v1")
    for field in ["created_at", "updated_at"]:
        if field in state and not parse_timestamp(state.get(field)):
            errors.append(f"{field} must be ISO 8601")

    challenge = state.get("challenge", {})
    if not isinstance(challenge, dict):
        errors.append("challenge must be an object")
        challenge = {}
    for field in CHALLENGE_FIELDS:
        if field not in challenge:
            errors.append(f"challenge missing field {field}")
    if challenge.get("category_confidence") not in ALLOWED_CONFIDENCE:
        errors.append(f"challenge.category_confidence must be one of {sorted(ALLOWED_CONFIDENCE)}")
    if challenge.get("scope_status") not in ALLOWED_SCOPE:
        errors.append(f"challenge.scope_status must be one of {sorted(ALLOWED_SCOPE)}")
    for list_field in ["rules", "targets", "attachments", "credentials"]:
        if list_field in challenge and not isinstance(challenge.get(list_field), list):
            errors.append(f"challenge.{list_field} must be a list")

    for field in LIST_FIELDS:
        validate_collection(field, state.get(field), errors, warnings)
    if isinstance(state.get("next_actions"), list) and len(state["next_actions"]) > 5:
        errors.append("next_actions must contain at most 5 items")
    if not isinstance(state.get("handoff_ready"), bool):
        errors.append("handoff_ready must be boolean")

    evidence = state.get("evidence", [])
    evidence_ids = ids_for(evidence)
    fact_ids = ids_for(state.get("known_facts", []))
    hypothesis_ids = ids_for(state.get("hypotheses", []))
    dead_end_ids = ids_for(state.get("dead_ends", []))
    artifact_ids = ids_for(state.get("artifacts", []))
    supportable_ids = fact_ids | hypothesis_ids | dead_end_ids | artifact_ids

    if isinstance(evidence, list):
        for index, item in enumerate(evidence):
            if not isinstance(item, dict):
                continue
            for field in EVIDENCE_FIELDS:
                if field not in item:
                    errors.append(f"evidence[{index}] missing field {field}")
            for ref_field in ["supports", "contradicts"]:
                refs = item.get(ref_field, [])
                if not isinstance(refs, list):
                    errors.append(f"evidence[{index}].{ref_field} must be a list")
                    continue
                for ref in refs:
                    if ref not in supportable_ids:
                        errors.append(f"evidence[{index}].{ref_field} references unknown id {ref}")
            raw_artifact = str(item.get("raw_artifact", ""))
            for artifact_path in split_artifact_paths(raw_artifact):
                if artifact_path.startswith(("http://", "https://")):
                    continue
                resolved = resolve_path(state_path, artifact_path)
                if not resolved.exists():
                    message = f"evidence[{index}].raw_artifact path does not exist: {artifact_path}"
                    if strict_artifacts:
                        errors.append(message)
                    else:
                        warnings.append(message)

    for collection_name in ["known_facts", "hypotheses", "attempts", "dead_ends", "artifacts"]:
        collection = state.get(collection_name, [])
        if not isinstance(collection, list):
            continue
        for index, item in enumerate(collection):
            if not isinstance(item, dict):
                continue
            refs = item.get("evidence", [])
            if refs in ("", None):
                refs = []
            if not isinstance(refs, list):
                errors.append(f"{collection_name}[{index}].evidence must be a list")
                continue
            for ref in refs:
                if ref not in evidence_ids:
                    errors.append(f"{collection_name}[{index}].evidence references unknown evidence id {ref}")

    return {
        "schema": "ctf-run-state-validation-v1",
        "state_path": str(state_path),
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "evidence_count": len(evidence) if isinstance(evidence, list) else 0,
        "known_fact_count": len(state.get("known_facts", [])) if isinstance(state.get("known_facts"), list) else 0,
        "hypothesis_count": len(state.get("hypotheses", [])) if isinstance(state.get("hypotheses"), list) else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a CTFRunState JSON file")
    parser.add_argument("state")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--strict-artifacts", action="store_true", help="Fail if referenced raw artifact paths are missing")
    args = parser.parse_args()

    result = validate_state(Path(args.state), strict_artifacts=args.strict_artifacts)
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = "ok" if result["ok"] else "fail"
        print(f"{status}: {result.get('state_path', args.state)}")
        for error in result["errors"]:
            print(f"ERROR: {error}")
        for warning in result["warnings"]:
            print(f"WARN: {warning}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
