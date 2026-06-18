#!/usr/bin/env python3
"""Render post-run CTF skill improvement candidates from CTFRunState JSON."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


MISSING_TOOL_RE = re.compile(r"missing|not found|dependency|license|docker|vpn|proxy|timeout|unavailable", re.I)
INJECTION_RE = re.compile(r"prompt|inject|fake flag|ignore previous|hidden instruction|tool poisoning|severity=(suspicious|hostile)", re.I)
BENIGN_INJECTION_RE = re.compile(r"no hostile|severity=benign|finding_count.?0", re.I)
ROUTE_RE = re.compile(r"route|deep-topic|candidate|ambiguous|category", re.I)


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def text_of(item: Any) -> str:
    if isinstance(item, dict):
        return " ".join(str(item.get(key, "")) for key in ("summary", "action", "purpose", "risk", "reason", "outcome"))
    return str(item)


def add_candidate(candidates: list[dict[str, Any]], *, target: str, priority: str, trigger: str, suggestion: str, evidence_ids: list[str] | None = None) -> None:
    key = (target, trigger, suggestion)
    for item in candidates:
        if (item["target"], item["trigger"], item["suggestion"]) == key:
            for evidence_id in evidence_ids or []:
                if evidence_id not in item["evidence_ids"]:
                    item["evidence_ids"].append(evidence_id)
            return
    candidates.append({
        "id": f"improve-{len(candidates) + 1:03d}",
        "target": target,
        "priority": priority,
        "trigger": trigger,
        "suggestion": suggestion,
        "evidence_ids": evidence_ids or [],
    })


def analyze(state: dict[str, Any]) -> dict[str, Any]:
    challenge = state.get("challenge", {})
    evidence = as_list(state.get("evidence"))
    facts = as_list(state.get("known_facts"))
    hypotheses = as_list(state.get("hypotheses"))
    attempts = as_list(state.get("attempts"))
    dead_ends = as_list(state.get("dead_ends"))
    artifacts = as_list(state.get("artifacts"))
    findings = as_list(state.get("anti_injection_findings"))
    next_actions = as_list(state.get("next_actions"))
    candidates: list[dict[str, Any]] = []

    if challenge.get("scope_status") in {"unknown_needs_confirmation", "benchmark_scope_pending"}:
        add_candidate(
            candidates,
            target="ctf-master/references/acceptance-gates.md",
            priority="high",
            trigger=f"scope_status={challenge.get('scope_status')}",
            suggestion="Tighten the scope gate or ask for authorization before active remote work.",
        )

    for item in evidence:
        if not isinstance(item, dict):
            continue
        evidence_id = str(item.get("id", ""))
        item_text = text_of(item)
        if MISSING_TOOL_RE.search(item_text) or str(item.get("exit_status", "")) not in {"", "0", "success"}:
            add_candidate(
                candidates,
                target="ctf-tool-preflight/references/tool-cards.md",
                priority="high" if item.get("risk") != "none" else "medium",
                trigger=item.get("summary", "tool failure or nonzero exit"),
                suggestion="Add or refine a ToolCard with preflight, failure class, retry rule, and compression guidance.",
                evidence_ids=[evidence_id] if evidence_id else [],
            )
        if INJECTION_RE.search(item_text) and not BENIGN_INJECTION_RE.search(item_text):
            add_candidate(
                candidates,
                target="ctf-anti-injection/references/untrusted-content.md",
                priority="medium",
                trigger=item.get("summary", "untrusted-content signal"),
                suggestion="Add this pattern as a prompt injection or anti-injection example only after local evidence confirms the useful clue or fake instruction.",
                evidence_ids=[evidence_id] if evidence_id else [],
            )
        raw_artifact = str(item.get("raw_artifact", ""))
        if not raw_artifact:
            add_candidate(
                candidates,
                target="ctf-master/references/state-schema.md",
                priority="medium",
                trigger=f"{evidence_id or 'evidence'} has no raw_artifact",
                suggestion="Require a raw artifact path, transcript, screenshot, or explicit observation note for every EvidenceRecord.",
                evidence_ids=[evidence_id] if evidence_id else [],
            )

    if len(dead_ends) >= 3:
        add_candidate(
            candidates,
            target="ctf-handoff-report/references/handoff-template.md",
            priority="high",
            trigger=f"{len(dead_ends)} dead ends recorded",
            suggestion="Render a handoff and force a strategy reset before more tool execution.",
            evidence_ids=[str(item.get("id", "")) for item in dead_ends if isinstance(item, dict) and item.get("id")],
        )

    route_like = [item for item in hypotheses if ROUTE_RE.search(text_of(item))]
    if len(route_like) > 1 and challenge.get("category_confidence") != "high":
        add_candidate(
            candidates,
            target="ctf-master/references/deep-topic-router.md",
            priority="medium",
            trigger="multiple route-like hypotheses with non-high category confidence",
            suggestion="Add clearer tie-break signals or first-confirmation checks for this ambiguous category pattern.",
            evidence_ids=[str(item.get("id", "")) for item in route_like if isinstance(item, dict) and item.get("id")],
        )

    for collection_name, collection in [("known_facts", facts), ("hypotheses", hypotheses), ("attempts", attempts), ("dead_ends", dead_ends), ("artifacts", artifacts)]:
        for item in collection:
            if isinstance(item, dict) and collection_name != "hypotheses" and not item.get("evidence"):
                add_candidate(
                    candidates,
                    target="ctf-master/scripts/update_state.py",
                    priority="low",
                    trigger=f"{collection_name} item {item.get('id', '?')} has no evidence IDs",
                    suggestion="Record supporting EvidenceRecord IDs so future handoff/writeup can reproduce the claim.",
                    evidence_ids=[],
                )

    if findings:
        add_candidate(
            candidates,
            target="ctf-anti-injection/scripts/scan_untrusted_text.py",
            priority="medium",
            trigger=f"{len(findings)} anti-injection findings recorded",
            suggestion="Review whether any finding should become a scanner pattern, false-positive exception, or visual/long-text rule.",
            evidence_ids=[str(item.get("id", "")) for item in findings if isinstance(item, dict) and item.get("id")],
        )

    if not next_actions:
        add_candidate(
            candidates,
            target="ctf-master/references/ctf-loop.md",
            priority="medium",
            trigger="no next_actions recorded",
            suggestion="Add at least one prioritized continuation or validation action before pausing the run.",
        )

    if not candidates:
        add_candidate(
            candidates,
            target="regression-suite",
            priority="low",
            trigger="no obvious run friction detected",
            suggestion="Preserve this state as a positive regression example if it represents a real or benchmark solve pattern.",
        )

    questions = [
        "Which repeated manual step should become a script or ToolCard?",
        "Which observation would another agent fail to reproduce from the current evidence?",
        "Which clue looked persuasive but lacked local verification?",
        "Which safety or scope assumption was implicit rather than recorded?",
    ]

    return {
        "schema": "ctf-run-reflection-v1",
        "challenge": {
            "title": challenge.get("title", "unknown"),
            "platform": challenge.get("platform", "unknown"),
            "category": challenge.get("category_inferred") or challenge.get("category_claimed", "unknown"),
            "scope_status": challenge.get("scope_status", "unknown"),
        },
        "counts": {
            "evidence": len(evidence),
            "known_facts": len(facts),
            "hypotheses": len(hypotheses),
            "attempts": len(attempts),
            "dead_ends": len(dead_ends),
            "artifacts": len(artifacts),
            "anti_injection_findings": len(findings),
            "next_actions": len(next_actions),
        },
        "improvement_candidates": candidates,
        "hard_questions": questions,
    }


def render_markdown(reflection: dict[str, Any]) -> str:
    challenge = reflection["challenge"]
    lines = [
        f"# Reflection: {challenge['title']}",
        "",
        "## Run Summary",
        f"- Platform: {challenge['platform']}",
        f"- Category: {challenge['category']}",
        f"- Scope status: {challenge['scope_status']}",
        "",
        "## Counts",
    ]
    for key, value in reflection["counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Improvement Candidates"])
    for item in reflection["improvement_candidates"]:
        evidence = ", ".join(item["evidence_ids"]) or "none"
        lines.append(f"- [{item['priority']}] {item['target']}: {item['suggestion']} Trigger: {item['trigger']} Evidence: {evidence}")
    lines.extend(["", "## Hard Questions"])
    for question in reflection["hard_questions"]:
        lines.append(f"- {question}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render CTF run reflection from CTFRunState JSON")
    parser.add_argument("state_json")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--out")
    args = parser.parse_args()

    state = json.loads(Path(args.state_json).read_text(encoding="utf-8"))
    reflection = analyze(state)
    output = json.dumps(reflection, ensure_ascii=False, indent=2) + "\n" if args.as_json else render_markdown(reflection)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
