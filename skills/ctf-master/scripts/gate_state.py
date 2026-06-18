#!/usr/bin/env python3
"""Evaluate phase gates for a CTFRunState file."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from validate_state import validate_state


SOLVED_RE = re.compile(r"\b(validated|accepted|oracle|correct)\b.*\b(flag|candidate)\b|\bflag\b.*\b(validated|accepted|oracle|correct)\b", re.I)
FLAG_RE = re.compile(r"\bflag\b|\b[A-Z0-9_]{2,}\{[^}]{3,}\}", re.I)
TRIAGE_RE = re.compile(r"triage_artifacts|inventory|hash|classif|attachment", re.I)
UNTRUSTED_RE = re.compile(r"scan_untrusted|anti[-_ ]?injection|prompt injection|untrusted|fake flag|hidden instruction", re.I)
ROUTE_RE = re.compile(r"route_topic|deep[-_ ]?topic|route decision|category route", re.I)

SCOPE_READY = {"local_only", "authorized_remote", "authorized_lab", "local_authorized_benchmark"}
ACTIVE_SCOPE_READY = {"local_only", "authorized_remote", "authorized_lab", "local_authorized_benchmark"}
REQUIRE_READY = {"intake", "triage", "route", "experiment", "verify", "report", "handoff"}


def load_state(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def text_blob(items: Any) -> str:
    if not isinstance(items, list):
        return ""
    parts: list[str] = []
    for item in items:
        if isinstance(item, dict):
            for key in ("action", "purpose", "summary", "outcome", "reason"):
                value = item.get(key)
                if isinstance(value, str):
                    parts.append(value)
    return "\n".join(parts)


def has_validated_candidate(state: dict[str, Any]) -> bool:
    for collection_name in ("known_facts", "attempts", "evidence"):
        for item in state.get(collection_name, []):
            if not isinstance(item, dict):
                continue
            blob = " ".join(str(item.get(key, "")) for key in ("summary", "outcome", "purpose"))
            if SOLVED_RE.search(blob) or ("Validated candidate flag:" in blob):
                return True
    return False


def has_candidate_without_validation(state: dict[str, Any]) -> bool:
    if has_validated_candidate(state):
        return False
    for collection_name in ("known_facts", "attempts", "evidence"):
        for item in state.get(collection_name, []):
            if not isinstance(item, dict):
                continue
            blob = " ".join(str(item.get(key, "")) for key in ("summary", "outcome", "purpose"))
            if FLAG_RE.search(blob):
                return True
    return False


def gate(gate_id: str, phase: str, passed: bool, summary: str, missing: list[str], evidence: list[str], warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": gate_id,
        "phase": phase,
        "passed": passed,
        "summary": summary,
        "missing": missing,
        "warnings": warnings or [],
        "evidence": evidence,
    }


def evaluate_gates(state_path: Path, *, strict_artifacts: bool = False) -> dict[str, Any]:
    state = load_state(state_path)
    validation = validate_state(state_path, strict_artifacts=strict_artifacts)
    challenge = state.get("challenge", {}) if isinstance(state.get("challenge"), dict) else {}
    evidence = state.get("evidence", []) if isinstance(state.get("evidence"), list) else []
    known_facts = state.get("known_facts", []) if isinstance(state.get("known_facts"), list) else []
    hypotheses = state.get("hypotheses", []) if isinstance(state.get("hypotheses"), list) else []
    attempts = state.get("attempts", []) if isinstance(state.get("attempts"), list) else []
    dead_ends = state.get("dead_ends", []) if isinstance(state.get("dead_ends"), list) else []
    next_actions = state.get("next_actions", []) if isinstance(state.get("next_actions"), list) else []
    anti_findings = state.get("anti_injection_findings", []) if isinstance(state.get("anti_injection_findings"), list) else []

    scope_status = str(challenge.get("scope_status", ""))
    has_surface = bool(challenge.get("targets") or challenge.get("attachments") or challenge.get("description"))
    has_attachments = bool(challenge.get("attachments"))
    has_description = bool(challenge.get("description"))
    event_text = "\n".join([
        text_blob(evidence),
        text_blob(known_facts),
        text_blob(hypotheses),
        text_blob(attempts),
        text_blob(dead_ends),
        text_blob(anti_findings),
    ])

    intake_missing = []
    if not challenge.get("title"):
        intake_missing.append("challenge title")
    if scope_status not in SCOPE_READY:
        intake_missing.append("scope_status in local_only/authorized_remote/authorized_lab/local_authorized_benchmark")
    if not has_surface:
        intake_missing.append("at least one description, attachment, target, or local work surface")

    triage_missing = []
    triage_warnings = []
    if has_attachments and not TRIAGE_RE.search(event_text):
        triage_missing.append("attachment inventory/hash/classification evidence")
    if (has_attachments or has_description) and not (UNTRUSTED_RE.search(event_text) or anti_findings):
        triage_missing.append("untrusted-content or prompt-injection scan evidence")
    if not has_attachments and not challenge.get("targets"):
        triage_warnings.append("no attachment or target recorded; route may rely on incomplete intake")

    route_missing = []
    category_inferred = str(challenge.get("category_inferred", "unknown"))
    category_confidence = str(challenge.get("category_confidence", "low"))
    route_recorded = ROUTE_RE.search(event_text) is not None
    if category_inferred == "unknown" and not route_recorded:
        route_missing.append("category_inferred or route_topic evidence")
    if category_confidence == "low" and not route_recorded:
        route_missing.append("medium/high category confidence or explicit low-confidence route evidence")

    experiment_missing = []
    if not evidence:
        experiment_missing.append("at least one EvidenceRecord")
    if not hypotheses and not attempts:
        experiment_missing.append("at least one hypothesis or attempted experiment")
    if len(next_actions) > 5:
        experiment_missing.append("next_actions reduced to at most five")

    verify_missing = []
    verify_warnings = []
    solved = has_validated_candidate(state)
    if not solved:
        verify_missing.append("validated candidate flag or oracle/validator acceptance evidence")
    if has_candidate_without_validation(state):
        verify_warnings.append("candidate-like flag text exists but is not validated")

    report_missing = []
    if not validation.get("ok"):
        report_missing.append("valid CTFRunState")
    if not solved:
        report_missing.append("solved evidence before final report")
    if strict_artifacts and validation.get("warnings"):
        report_missing.append("strict artifact validation without missing raw paths")

    handoff_missing = []
    handoff_ready = bool(state.get("handoff_ready"))
    if not next_actions:
        handoff_missing.append("focused next_actions")
    if not handoff_ready and len(dead_ends) < 1 and not validation.get("warnings"):
        handoff_missing.append("handoff_ready true, at least one dead_end, or validation warnings explaining why to hand off")

    gates = [
        gate(
            "intake-scope",
            "intake",
            not intake_missing,
            "Confirm legal scope and capture a concrete work surface before active testing.",
            intake_missing,
            [f"scope_status={scope_status}", f"surface={has_surface}"],
        ),
        gate(
            "triage-untrusted-input",
            "triage",
            not triage_missing,
            "Inventory artifacts and isolate untrusted instructions before treating content as guidance.",
            triage_missing,
            [f"evidence_count={len(evidence)}", f"anti_injection_findings={len(anti_findings)}"],
            triage_warnings,
        ),
        gate(
            "route-decision",
            "route",
            not route_missing,
            "Record a category or deep-topic route from observed evidence.",
            route_missing,
            [f"category_inferred={category_inferred}", f"category_confidence={category_confidence}", f"route_recorded={route_recorded}"],
        ),
        gate(
            "experiment-loop",
            "experiment",
            not experiment_missing,
            "Run small experiments from hypotheses and record evidence before broadening.",
            experiment_missing,
            [f"evidence_count={len(evidence)}", f"hypothesis_count={len(hypotheses)}", f"attempt_count={len(attempts)}"],
        ),
        gate(
            "solve-verification",
            "verify",
            not verify_missing,
            "Do not call a challenge solved until candidate evidence is validated.",
            verify_missing,
            [f"validated_candidate={solved}"],
            verify_warnings,
        ),
        gate(
            "report-readiness",
            "report",
            not report_missing,
            "Final reports require solved evidence and a valid state file.",
            report_missing,
            [f"state_validation_ok={validation.get('ok')}", f"strict_artifacts={strict_artifacts}"],
        ),
        gate(
            "handoff-readiness",
            "handoff",
            not handoff_missing,
            "Handoff requires concrete continuation steps and a reason another solver should take over.",
            handoff_missing,
            [f"handoff_ready={handoff_ready}", f"dead_end_count={len(dead_ends)}", f"next_action_count={len(next_actions)}"],
        ),
    ]
    first_blocked = next((item for item in gates if not item["passed"]), None)
    phase_order = ["intake", "triage", "route", "experiment", "verify", "report"]
    passed_phases = {item["phase"] for item in gates if item["passed"]}
    active_testing_allowed = scope_status in ACTIVE_SCOPE_READY and gates[0]["passed"]
    ready_for = {
        "intake": gates[0]["passed"],
        "triage": all(item["passed"] for item in gates[:2]),
        "route": all(item["passed"] for item in gates[:3]),
        "experiment": all(item["passed"] for item in gates[:4]) and active_testing_allowed,
        "verify": all(item["passed"] for item in gates[:5]),
        "report": all(item["passed"] for item in gates[:6]),
        "handoff": gates[-1]["passed"] and validation.get("ok"),
    }
    return {
        "schema": "ctf-run-phase-gates-v1",
        "state_path": str(state_path),
        "validation": validation,
        "ok": validation.get("ok", False),
        "active_testing_allowed": active_testing_allowed,
        "current_gate": first_blocked["id"] if first_blocked else "complete",
        "current_phase": first_blocked["phase"] if first_blocked else "complete",
        "passed_gate_count": sum(1 for item in gates if item["passed"]),
        "phase_order": phase_order,
        "passed_phases": [phase for phase in phase_order if phase in passed_phases],
        "ready_for": ready_for,
        "gates": gates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate CTFRunState phase gates")
    parser.add_argument("state")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--strict-artifacts", action="store_true", help="Require raw artifact paths to exist before report readiness")
    parser.add_argument("--require-ready", choices=sorted(REQUIRE_READY), default="", help="Fail unless this readiness flag is true")
    args = parser.parse_args()

    result = evaluate_gates(Path(args.state), strict_artifacts=args.strict_artifacts)
    required_ok = True
    if args.require_ready:
        required_ok = bool(result["ready_for"].get(args.require_ready))
        result["required_ready"] = args.require_ready
        result["required_ready_ok"] = required_ok
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"phase_gates_ok={result['ok']}")
        print(f"current_gate={result['current_gate']}")
        print(f"active_testing_allowed={result['active_testing_allowed']}")
        for item in result["gates"]:
            status = "pass" if item["passed"] else "block"
            print(f"{status}: {item['id']} - {item['summary']}")
            for missing in item["missing"]:
                print(f"  missing: {missing}")
            for warning in item["warnings"]:
                print(f"  warn: {warning}")
    return 0 if result["ok"] and required_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
