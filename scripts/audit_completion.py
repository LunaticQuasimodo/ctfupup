#!/usr/bin/env python3
"""Audit whether the suite is engineering-ready and whether v1 completion is proven."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from audit_quality import run_quality_audit
from audit_traceability import audit_requirement, load_matrix


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SKILL_COUNT = 9
FRESH_AGENT_REQ = "REQ-EVAL-FRESH-AGENT"


def criterion(
    check_id: str,
    required_for: str,
    status: str,
    summary: str,
    evidence: list[str],
    next_action: str = "",
    problems: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "required_for": required_for,
        "status": status,
        "ok": status == "pass",
        "summary": summary,
        "evidence": evidence,
        "next_action": next_action,
        "problems": problems or [],
    }


def run_json(root: Path, cmd: list[str]) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        cmd,
        cwd=root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    parsed: dict[str, Any] = {}
    try:
        parsed = json.loads(proc.stdout)
    except json.JSONDecodeError:
        parsed = {"parse_error": proc.stdout[:500]}
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "json": parsed,
    }


def audit_manifest(root: Path) -> dict[str, Any]:
    manifest_path = root / "suite-manifest.json"
    if not manifest_path.exists():
        return criterion("manifest-surface", "engineering", "fail", "suite manifest is missing", ["suite-manifest.json"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    skills = manifest.get("skills", [])
    validation = manifest.get("validation", {})
    problems = []
    if len(skills) != REQUIRED_SKILL_COUNT:
        problems.append(f"expected {REQUIRED_SKILL_COUNT} skills, found {len(skills)}")
    if not re.match(r"^\d+\.\d+\.\d+$", str(manifest.get("version", ""))):
        problems.append("version is not semver-like")
    for key in ["quality_audit", "pressure_audit", "category_coverage_audit", "evidence_contract_audit", "release_consistency_audit", "traceability", "release_gate", "completion_audit", "forward_rubric_template", "forward_handoff_render", "fresh_agent_readiness_audit", "fresh_agent_packet_export", "fresh_agent_packet_audit", "fresh_agent_launch_prompt_render", "forward_run_verify"]:
        if key not in validation:
            problems.append(f"validation missing {key}")
    return criterion(
        "manifest-surface",
        "engineering",
        "fail" if problems else "pass",
        "manifest declares skills, version, and validation commands",
        ["suite-manifest.json"],
        problems=problems,
    )


def audit_traceability_state(root: Path) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    matrix = load_matrix(root, None)
    requirements = matrix.get("requirements", [])
    results = [audit_requirement(root, req) for req in requirements]
    failing = [item for item in results if item["problems"]]
    current_uncovered = [item["id"] for item in results if item["priority"] == "current_gate" and item["status"] != "covered"]
    partial_or_open = [item["id"] for item in results if item["status"] != "covered"]
    problems = [f"failing traceability: {item['id']}" for item in failing]
    problems.extend(f"current gate not covered: {item}" for item in current_uncovered)
    trace_criterion = criterion(
        "traceability-current-gates",
        "engineering",
        "fail" if problems else "pass",
        "all current-gate requirements have direct local evidence",
        ["research/requirements-traceability.json", "scripts/audit_traceability.py"],
        problems=problems,
    )
    fresh_req = next((req for req in requirements if req.get("id") == FRESH_AGENT_REQ), {})
    return trace_criterion, fresh_req, partial_or_open


def audit_quality_state(root: Path) -> dict[str, Any]:
    result = run_quality_audit(root, 140)
    return criterion(
        "quality-gates",
        "engineering",
        "pass" if result.get("ok") else "fail",
        "quality audit covers reference absorption, pressure questions, routing, metadata, validation, and honesty gates",
        ["scripts/audit_quality.py"],
        problems=[f"failing quality check: {item}" for item in result.get("failing_ids", [])],
    )


def audit_external_command(root: Path, check_id: str, summary: str, cmd: list[str], evidence: list[str]) -> dict[str, Any]:
    result = run_json(root, cmd)
    parsed_ok = result["json"].get("ok")
    ok = result["ok"] and parsed_ok is not False
    problems = []
    if not result["ok"]:
        problems.append(f"command exited {result['returncode']}: {' '.join(cmd)}")
    if parsed_ok is False:
        problems.append("command JSON reports ok=false")
    return criterion(check_id, "engineering", "pass" if ok else "fail", summary, evidence, problems=problems)


def audit_forward_surface(root: Path) -> dict[str, Any]:
    required = [
        "forward-tests/scenarios",
        "forward-tests/fresh-agent-run-record-template.json",
        "scripts/init_forward_run.py",
        "scripts/render_forward_handoff.py",
        "scripts/render_forward_rubric.py",
        "scripts/finalize_forward_run.py",
        "scripts/verify_forward_run.py",
        "scripts/run_forward_suite.py",
        "scripts/audit_forward_integrity.py",
        "scripts/audit_fresh_agent_readiness.py",
        "scripts/export_fresh_agent_packet.py",
        "scripts/audit_fresh_agent_packet.py",
        "scripts/render_fresh_agent_launch_prompt.py",
    ]
    problems = [f"missing {rel}" for rel in required if not (root / rel).exists()]
    return criterion(
        "fresh-agent-evaluation-surface",
        "engineering",
        "fail" if problems else "pass",
        "fresh-agent prompt, scoring, finalization, and verification surface exists",
        required,
        problems=problems,
    )


def audit_honest_incomplete_state(root: Path, fresh_req: dict[str, Any], partial_or_open: list[str]) -> dict[str, Any]:
    release_gate = (root / "scripts/release_gate.py").read_text(encoding="utf-8")
    reflection = (root / "REFLECTION_AUDIT.md").read_text(encoding="utf-8")
    notes = str(fresh_req.get("notes", ""))
    problems = []
    if fresh_req.get("status") != "partial":
        problems.append(f"{FRESH_AGENT_REQ} should remain partial until an independent run is verified")
    if FRESH_AGENT_REQ not in partial_or_open:
        problems.append(f"{FRESH_AGENT_REQ} is not reported as partial/open")
    if FRESH_AGENT_REQ not in release_gate:
        problems.append("release gate does not preserve fresh-agent partial allowance")
    if "final v4 rerun is user-waived" not in reflection:
        problems.append("reflection audit no longer states the user-waived final rerun")
    if "final v4 independent rerun is explicitly user-waived" not in notes:
        problems.append("traceability notes no longer state the user-waived final rerun")
    return criterion(
        "honest-incomplete-state",
        "engineering",
        "fail" if problems else "pass",
        "suite is allowed to be engineering-ready only while the fresh-agent gap is explicit",
        ["research/requirements-traceability.json", "REFLECTION_AUDIT.md", "scripts/release_gate.py"],
        next_action="Run and verify an isolated fresh-agent forward suite before claiming v1 completion.",
        problems=problems,
    )


def audit_fresh_record(root: Path, fresh_record: str | None) -> dict[str, Any]:
    if not fresh_record:
        return criterion(
            "fresh-agent-independent-run",
            "v1",
            "missing",
            "no verified fresh-agent run record was supplied",
            ["forward-tests/RUN_LOG.md", "scripts/verify_forward_run.py"],
            next_action="Initialize a clean forward workspace, run prompts in a fresh agent context, finalize responses with a rubric, and verify the run record.",
            problems=[f"{FRESH_AGENT_REQ} has no verified run record"],
        )
    record_path = Path(fresh_record)
    if not record_path.is_absolute():
        record_path = root / record_path
    result = run_json(root, [sys.executable, "scripts/verify_forward_run.py", str(record_path), "--json"])
    ok = result["ok"] and result["json"].get("ok") is True
    problems = []
    if not ok:
        problems.extend(result["json"].get("problems", []))
        if not problems:
            problems.append(f"verify_forward_run failed with exit {result['returncode']}")
    return criterion(
        "fresh-agent-independent-run",
        "v1",
        "pass" if ok else "fail",
        "fresh-agent run record verifies clean context, scoring, rubric, and response hashes",
        [str(record_path), "scripts/verify_forward_run.py"],
        problems=problems,
    )


def audit_fresh_waiver(root: Path, fresh_waiver: str | None) -> dict[str, Any]:
    if not fresh_waiver:
        return criterion(
            "fresh-agent-user-waiver",
            "v1",
            "missing",
            "no user waiver for skipping the final fresh-agent rerun was supplied",
            ["forward-tests/fresh-agent-evaluation-waiver.json"],
            next_action="Provide a waiver only when the user explicitly accepts the current evaluation evidence without another fresh-agent rerun.",
            problems=["no waiver supplied"],
        )
    waiver_path = Path(fresh_waiver)
    if not waiver_path.is_absolute():
        waiver_path = root / waiver_path
    problems: list[str] = []
    if not waiver_path.exists():
        problems.append(f"waiver does not exist: {waiver_path}")
        waiver = {}
    else:
        waiver = json.loads(waiver_path.read_text(encoding="utf-8"))
    if waiver.get("schema") != "ctf-fresh-agent-evaluation-waiver-v1":
        problems.append("waiver schema is not ctf-fresh-agent-evaluation-waiver-v1")
    if waiver.get("accepted_by") != "user":
        problems.append("waiver accepted_by must be user")
    if waiver.get("decision") != "accept_current_evidence_skip_final_rerun":
        problems.append("waiver decision is not the expected skip-final-rerun decision")
    skipped = waiver.get("skipped_steps", [])
    if not isinstance(skipped, list) or len(skipped) < 2:
        problems.append("waiver skipped_steps must list the skipped final rerun and automatic score steps")
    for rel in waiver.get("evidence", []):
        path = root / str(rel)
        if not path.exists():
            problems.append(f"waiver evidence path missing: {rel}")
    if not waiver.get("residual_risk"):
        problems.append("waiver must record residual_risk")
    if not waiver.get("reopen_condition"):
        problems.append("waiver must record reopen_condition")
    return criterion(
        "fresh-agent-user-waiver",
        "v1",
        "pass" if not problems else "fail",
        "user explicitly accepted current fresh-agent evidence and skipped the final independent rerun",
        [str(waiver_path)],
        problems=problems,
    )


def audit_fresh_completion(root: Path, fresh_record: str | None, fresh_waiver: str | None) -> tuple[dict[str, Any], str]:
    if fresh_record:
        return audit_fresh_record(root, fresh_record), "verified_fresh_record"
    if fresh_waiver:
        return audit_fresh_waiver(root, fresh_waiver), "user_waiver"
    return audit_fresh_record(root, None), "missing"


def audit_completion(root: Path, fresh_record: str | None, fresh_waiver: str | None, require_v1: bool) -> dict[str, Any]:
    manifest_check = audit_manifest(root)
    trace_check, fresh_req, partial_or_open = audit_traceability_state(root)
    quality_check = audit_quality_state(root)
    source_check = audit_external_command(
        root,
        "source-provenance",
        "requested references have auditable source anchors and local conversions",
        [sys.executable, "scripts/audit_source_matrix.py", "--json"],
        ["research/seed-source-matrix.md", "scripts/audit_source_matrix.py"],
    )
    evidence_contract_check = audit_external_command(
        root,
        "evidence-contract",
        "handoff, writeup, and verdict-style conclusions cite reproducible evidence",
        [sys.executable, "scripts/audit_evidence_contract.py", "--json"],
        ["scripts/audit_evidence_contract.py", "skills/ctf-handoff-report/references/writeup-template.md"],
    )
    benchmark_check = audit_external_command(
        root,
        "benchmark-evidence",
        "at least one authorized benchmark run is recorded and verifier-checked",
        [sys.executable, "scripts/verify_benchmark_run.py", "benchmarks/runs/cybench-primary-knowledge", "--json"],
        ["benchmarks/runs/cybench-primary-knowledge", "scripts/verify_benchmark_run.py"],
    )
    forward_surface_check = audit_forward_surface(root)
    honest_check = audit_honest_incomplete_state(root, fresh_req, partial_or_open)
    fresh_record_check, completion_basis = audit_fresh_completion(root, fresh_record, fresh_waiver)

    criteria = [
        manifest_check,
        trace_check,
        quality_check,
        source_check,
        evidence_contract_check,
        benchmark_check,
        forward_surface_check,
        honest_check,
        fresh_record_check,
    ]
    engineering_failures = [item for item in criteria if item["required_for"] == "engineering" and not item["ok"]]
    v1_blockers = [item for item in criteria if item["required_for"] == "v1" and not item["ok"]]
    engineering_ok = not engineering_failures
    v1_ready = engineering_ok and not v1_blockers
    reported_ok = engineering_ok and (v1_ready if require_v1 else True)

    return {
        "schema": "ctf-agent-skills-completion-audit-v1",
        "root": str(root),
        "ok": reported_ok,
        "engineering_ok": engineering_ok,
        "v1_ready": v1_ready,
        "completion_basis": completion_basis,
        "require_v1": require_v1,
        "criteria_count": len(criteria),
        "engineering_failure_ids": [item["id"] for item in engineering_failures],
        "v1_blocker_ids": [item["id"] for item in v1_blockers],
        "remaining_requirement_blockers": [FRESH_AGENT_REQ] if v1_blockers else [],
        "partial_or_open_requirements": partial_or_open,
        "criteria": criteria,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit engineering readiness and v1 completion proof")
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--fresh-record", help="Optional verified fresh-agent run record to count toward v1 completion")
    parser.add_argument("--fresh-waiver", help="Optional explicit user waiver accepting current evaluation evidence without a final fresh-agent rerun")
    parser.add_argument("--require-v1", action="store_true", help="Exit nonzero unless v1 completion is fully proven")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    result = audit_completion(Path(args.root), args.fresh_record, args.fresh_waiver, args.require_v1)
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"completion_audit_ok={result['ok']} engineering_ok={result['engineering_ok']} v1_ready={result['v1_ready']}")
        for item in result["criteria"]:
            print(f"{item['status']}: {item['id']} ({item['required_for']}) - {item['summary']}")
            for problem in item["problems"]:
                print(f"  - {problem}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
