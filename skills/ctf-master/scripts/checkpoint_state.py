#!/usr/bin/env python3
"""Render a compact, resumable checkpoint from CTFRunState JSON."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from validate_state import validate_state


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def trim_text(value: Any, limit: int = 220) -> str:
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def compact_items(items: list[Any], *, fields: list[str], limit: int) -> list[dict[str, Any]]:
    compacted = []
    for item in items[-limit:]:
        if not isinstance(item, dict):
            continue
        row: dict[str, Any] = {}
        for field in fields:
            if field in item and item[field] not in ("", [], None):
                value = item[field]
                if isinstance(value, str):
                    value = trim_text(value)
                row[field] = value
        compacted.append(row)
    return compacted


def collect_artifact_paths(state: dict[str, Any], limit: int) -> list[str]:
    paths: list[str] = []
    for item in as_list(state.get("evidence")):
        if not isinstance(item, dict):
            continue
        raw = str(item.get("raw_artifact", "")).strip()
        for part in [value.strip() for value in re.split(r"[,;]", raw) if value.strip()]:
            if part not in paths:
                paths.append(part)
    for item in as_list(state.get("artifacts")):
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", "")).strip()
        if path and path not in paths:
            paths.append(path)
    return paths[-limit:]


def build_resume_risks(state: dict[str, Any], validation: dict[str, Any]) -> list[str]:
    challenge = state.get("challenge", {}) if isinstance(state.get("challenge"), dict) else {}
    risks = []
    if not validation.get("ok"):
        risks.append("state_validation_failed")
    if challenge.get("scope_status") in {"unknown_needs_confirmation", "benchmark_scope_pending", None, ""}:
        risks.append("scope_not_confirmed")
    if not as_list(state.get("evidence")):
        risks.append("no_evidence_recorded")
    if len(as_list(state.get("dead_ends"))) >= 3:
        risks.append("three_or_more_dead_ends")
    if not as_list(state.get("next_actions")):
        risks.append("no_next_actions")
    if as_list(state.get("anti_injection_findings")):
        risks.append("untrusted_content_findings_present")
    return risks


def build_checkpoint(state_path: Path, *, strict_artifacts: bool = False, max_items: int = 5) -> dict[str, Any]:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    validation = validate_state(state_path, strict_artifacts=strict_artifacts)
    challenge = state.get("challenge", {}) if isinstance(state.get("challenge"), dict) else {}
    counts = {
        "evidence": len(as_list(state.get("evidence"))),
        "known_facts": len(as_list(state.get("known_facts"))),
        "hypotheses": len(as_list(state.get("hypotheses"))),
        "attempts": len(as_list(state.get("attempts"))),
        "dead_ends": len(as_list(state.get("dead_ends"))),
        "artifacts": len(as_list(state.get("artifacts"))),
        "anti_injection_findings": len(as_list(state.get("anti_injection_findings"))),
        "next_actions": len(as_list(state.get("next_actions"))),
    }
    checkpoint = {
        "schema": "ctf-run-checkpoint-v1",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "state_path": str(state_path),
        "validation": {
            "ok": validation.get("ok") is True,
            "errors": validation.get("errors", []),
            "warnings": validation.get("warnings", []),
        },
        "challenge": {
            "title": challenge.get("title", "unknown"),
            "platform": challenge.get("platform", "unknown"),
            "category": challenge.get("category_inferred") or challenge.get("category_claimed", "unknown"),
            "category_confidence": challenge.get("category_confidence", "unknown"),
            "scope_status": challenge.get("scope_status", "unknown"),
            "flag_format": challenge.get("flag_format", "unknown"),
            "targets": challenge.get("targets", []),
            "rules": challenge.get("rules", []),
        },
        "counts": counts,
        "current_facts": compact_items(
            as_list(state.get("known_facts")),
            fields=["id", "summary", "evidence"],
            limit=max_items,
        ),
        "active_hypotheses": compact_items(
            as_list(state.get("hypotheses")),
            fields=["id", "summary", "confidence", "next_experiment", "evidence"],
            limit=max_items,
        ),
        "recent_evidence": compact_items(
            as_list(state.get("evidence")),
            fields=["id", "summary", "action", "purpose", "raw_artifact", "exit_status", "risk", "supports", "contradicts"],
            limit=max_items,
        ),
        "recent_attempts": compact_items(
            as_list(state.get("attempts")),
            fields=["id", "summary", "action", "outcome", "evidence"],
            limit=max_items,
        ),
        "dead_ends": compact_items(
            as_list(state.get("dead_ends")),
            fields=["id", "summary", "reason", "evidence", "revisit_condition"],
            limit=max_items,
        ),
        "anti_injection_findings": compact_items(
            as_list(state.get("anti_injection_findings")),
            fields=["id", "summary", "evidence"],
            limit=max_items,
        ),
        "next_actions": compact_items(
            as_list(state.get("next_actions")),
            fields=["id", "summary", "priority"],
            limit=max_items,
        ),
        "artifact_paths": collect_artifact_paths(state, max_items * 2),
    }
    checkpoint["resume_risks"] = build_resume_risks(state, validation)
    checkpoint["resume_checklist"] = [
        "Verify scope_status before remote or active testing.",
        "Read recent_evidence and current_facts before running new tools.",
        "Use active_hypotheses to pick the next smallest confirming experiment.",
        "Open artifact_paths only as needed; keep raw outputs outside main context.",
        "Update CTFRunState after the next experiment, then regenerate this checkpoint.",
    ]
    return checkpoint


def render_markdown(checkpoint: dict[str, Any]) -> str:
    challenge = checkpoint["challenge"]
    validation = checkpoint["validation"]
    lines = [
        f"# Checkpoint: {challenge['title']}",
        "",
        "## Challenge",
        f"- Platform: {challenge['platform']}",
        f"- Category: {challenge['category']} ({challenge['category_confidence']})",
        f"- Scope status: {challenge['scope_status']}",
        f"- Flag format: {challenge['flag_format']}",
        f"- Validation: {'ok' if validation['ok'] else 'failed'}",
    ]
    if checkpoint["resume_risks"]:
        lines.append(f"- Resume risks: {', '.join(checkpoint['resume_risks'])}")
    lines.extend(["", "## Counts"])
    for key, value in checkpoint["counts"].items():
        lines.append(f"- {key}: {value}")

    def add_section(title: str, rows: list[dict[str, Any]], summary_fields: list[str]) -> None:
        lines.extend(["", f"## {title}"])
        if not rows:
            lines.append("- none")
            return
        for row in rows:
            label = row.get("id", "item")
            details = []
            for field in summary_fields:
                if field in row:
                    details.append(f"{field}={row[field]}")
            lines.append(f"- {label}: {'; '.join(details)}")

    add_section("Current Facts", checkpoint["current_facts"], ["summary", "evidence"])
    add_section("Active Hypotheses", checkpoint["active_hypotheses"], ["summary", "confidence", "next_experiment", "evidence"])
    add_section("Recent Evidence", checkpoint["recent_evidence"], ["summary", "raw_artifact", "exit_status", "risk"])
    add_section("Recent Attempts", checkpoint["recent_attempts"], ["summary", "outcome", "evidence"])
    add_section("Dead Ends", checkpoint["dead_ends"], ["summary", "reason", "evidence", "revisit_condition"])
    add_section("Next Actions", checkpoint["next_actions"], ["summary", "priority"])

    lines.extend(["", "## Artifact Paths"])
    if checkpoint["artifact_paths"]:
        for path in checkpoint["artifact_paths"]:
            lines.append(f"- {path}")
    else:
        lines.append("- none")

    lines.extend(["", "## Resume Checklist"])
    for item in checkpoint["resume_checklist"]:
        lines.append(f"- {item}")
    if validation["errors"]:
        lines.extend(["", "## Validation Errors"])
        for item in validation["errors"]:
            lines.append(f"- {item}")
    if validation["warnings"]:
        lines.extend(["", "## Validation Warnings"])
        for item in validation["warnings"]:
            lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a resumable CTFRunState checkpoint")
    parser.add_argument("state_json")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--out")
    parser.add_argument("--strict-artifacts", action="store_true")
    parser.add_argument("--allow-invalid", action="store_true")
    parser.add_argument("--max-items", type=int, default=5)
    args = parser.parse_args()

    state_path = Path(args.state_json).resolve()
    checkpoint = build_checkpoint(state_path, strict_artifacts=args.strict_artifacts, max_items=args.max_items)
    output = json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n" if args.as_json else render_markdown(checkpoint)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    if checkpoint["validation"]["ok"] or args.allow_invalid:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
