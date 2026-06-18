#!/usr/bin/env python3
"""Audit release-level consistency for the CTF Agent skill suite."""

from __future__ import annotations

import argparse
import json
import re
import shlex
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VALID_ROLES = {"master", "category", "support"}
SCRIPT_RE = re.compile(r"(?:^|\s)(scripts/[^\s\"']+\.py|skills/[^\s\"']+\.py)")
REQ_ID_RE = re.compile(r"`(REQ-[A-Z0-9-]+)`")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def add_check(checks: list[dict[str, Any]], check_id: str, ok: bool, summary: str, evidence: list[str], problems: list[str]) -> None:
    checks.append({
        "id": check_id,
        "ok": ok,
        "summary": summary,
        "evidence": evidence,
        "problems": problems,
    })


def load_manifest(root: Path) -> tuple[dict[str, Any], list[str]]:
    path = root / "suite-manifest.json"
    if not path.exists():
        return {}, ["missing suite-manifest.json"]
    try:
        return read_json(path), []
    except json.JSONDecodeError as exc:
        return {}, [f"suite-manifest.json is invalid JSON: {exc}"]


def check_skill_inventory(root: Path, manifest: dict[str, Any], checks: list[dict[str, Any]]) -> None:
    problems: list[str] = []
    manifest_skills = manifest.get("skills", [])
    manifest_names = [item.get("name", "") for item in manifest_skills]
    actual_names = sorted(path.name for path in (root / "skills").glob("ctf-*") if path.is_dir())

    if sorted(manifest_names) != actual_names:
        problems.append(f"manifest skill names {sorted(manifest_names)} do not match actual skills {actual_names}")
    if len(manifest_names) != len(set(manifest_names)):
        problems.append("manifest contains duplicate skill names")

    for item in manifest_skills:
        name = str(item.get("name", ""))
        role = str(item.get("role", ""))
        rel_path = str(item.get("path", ""))
        if role not in VALID_ROLES:
            problems.append(f"{name} role {role!r} is not one of {sorted(VALID_ROLES)}")
        expected_path = f"skills/{name}"
        if rel_path != expected_path:
            problems.append(f"{name} path should be {expected_path}, found {rel_path!r}")
        skill_dir = root / rel_path
        if not skill_dir.exists():
            problems.append(f"{name} path does not exist: {rel_path}")
            continue
        for required in item.get("must_exist", []):
            required_path = skill_dir / required
            if not required_path.exists():
                problems.append(f"{name} missing required artifact {required}")

    add_check(
        checks,
        "skill-inventory",
        not problems,
        "manifest skill list, roles, paths, and required artifacts match the filesystem",
        ["suite-manifest.json", "skills/"],
        problems,
    )


def command_script_refs(command: str) -> set[str]:
    refs = set(SCRIPT_RE.findall(command))
    try:
        refs.update(token for token in shlex.split(command) if token.startswith(("scripts/", "skills/")) and token.endswith(".py"))
    except ValueError:
        pass
    return refs


def check_validation_commands(root: Path, manifest: dict[str, Any], checks: list[dict[str, Any]]) -> None:
    problems: list[str] = []
    validation = manifest.get("validation", {})
    if not isinstance(validation, dict) or not validation:
        problems.append("manifest validation map is missing or empty")
        validation = {}

    docs = (root / "SKILL_SUITE.md").read_text(encoding="utf-8", errors="replace") if (root / "SKILL_SUITE.md").exists() else ""
    release_gate = (root / "scripts/release_gate.py").read_text(encoding="utf-8", errors="replace") if (root / "scripts/release_gate.py").exists() else ""

    for key, command in sorted(validation.items()):
        if not isinstance(command, str) or not command.strip():
            problems.append(f"validation command {key} is empty")
            continue
        for ref in sorted(command_script_refs(command)):
            if not (root / ref).exists():
                problems.append(f"validation command {key} references missing script {ref}")
        first_script = next(iter(sorted(command_script_refs(command))), "")
        if first_script and Path(first_script).name not in docs:
            problems.append(f"SKILL_SUITE.md does not mention validation script {Path(first_script).name} from {key}")

    release_required = [
        "validate_suite.py",
        "audit_completion.py",
        "audit_quality.py",
        "audit_pressure.py",
        "audit_category_coverage.py",
        "audit_evidence_contract.py",
        "audit_source_matrix.py",
        "audit_release_consistency.py",
        "audit_traceability.py",
        "verify_benchmark_run.py",
        "audit_forward_integrity.py",
        "init_forward_run.py",
        "render_forward_handoff.py",
        "audit_fresh_agent_readiness.py",
        "export_fresh_agent_packet.py",
        "audit_fresh_agent_packet.py",
        "render_fresh_agent_launch_prompt.py",
    ]
    for script in release_required:
        if script not in release_gate:
            problems.append(f"release_gate.py does not run or mention {script}")

    add_check(
        checks,
        "validation-commands",
        not problems,
        "manifest validation commands reference real scripts and release-gate-critical checks",
        ["suite-manifest.json", "SKILL_SUITE.md", "scripts/release_gate.py"],
        problems,
    )


def check_version_and_docs(root: Path, manifest: dict[str, Any], checks: list[dict[str, Any]]) -> None:
    version = str(manifest.get("version", ""))
    problems: list[str] = []
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        problems.append(f"manifest version is not semver-like: {version!r}")
    reflection = (root / "REFLECTION_AUDIT.md").read_text(encoding="utf-8", errors="replace") if (root / "REFLECTION_AUDIT.md").exists() else ""
    if version and f"suite version `{version}`" not in reflection:
        problems.append(f"REFLECTION_AUDIT.md does not record suite version {version}")
    for term in ["Release consistency audit", "Category coverage audit", "Evidence contract audit", "fresh-agent", "final v4 rerun is user-waived"]:
        if term not in reflection:
            problems.append(f"REFLECTION_AUDIT.md missing release/status term: {term}")

    add_check(
        checks,
        "version-and-status-docs",
        not problems,
        "manifest version and release status are reflected in the human audit document",
        ["suite-manifest.json", "REFLECTION_AUDIT.md"],
        problems,
    )


def check_traceability_docs(root: Path, checks: list[dict[str, Any]]) -> None:
    problems: list[str] = []
    json_path = root / "research/requirements-traceability.json"
    md_path = root / "research/requirements-traceability.md"
    if not json_path.exists() or not md_path.exists():
        missing = [str(path.relative_to(root)) for path in (json_path, md_path) if not path.exists()]
        problems.extend(f"missing traceability file {item}" for item in missing)
        add_check(
            checks,
            "traceability-doc-sync",
            False,
            "traceability JSON and Markdown list the same requirement IDs and preserve the known v1 gap",
            ["research/requirements-traceability.json", "research/requirements-traceability.md"],
            problems,
        )
        return

    matrix = read_json(json_path)
    json_ids = [str(item.get("id", "")) for item in matrix.get("requirements", [])]
    md_text = md_path.read_text(encoding="utf-8", errors="replace")
    md_ids = REQ_ID_RE.findall(md_text)
    json_id_set = set(json_ids)
    md_id_set = set(md_ids)
    if json_id_set != md_id_set:
        problems.append(f"traceability JSON IDs and Markdown IDs differ: json={len(json_id_set)} md={len(md_id_set)}")
        for missing in sorted(json_id_set - md_id_set):
            problems.append(f"Markdown missing requirement {missing}")
        for extra in sorted(md_id_set - json_id_set):
            problems.append(f"Markdown has extra requirement {extra}")
    if "REQ-EVAL-FRESH-AGENT" not in md_text or "partial" not in md_text:
        problems.append("traceability Markdown does not preserve the fresh-agent partial gap")
    if "REQ-RELEASE-CONSISTENCY-030" not in md_text:
        problems.append("traceability Markdown does not list REQ-RELEASE-CONSISTENCY-030")
    if "REQ-CATEGORY-COVERAGE-031" not in md_text:
        problems.append("traceability Markdown does not list REQ-CATEGORY-COVERAGE-031")
    if "REQ-EVIDENCE-CONTRACT-032" not in md_text:
        problems.append("traceability Markdown does not list REQ-EVIDENCE-CONTRACT-032")
    if "REQ-FRESH-AGENT-SKILL-ROOT-033" not in md_text:
        problems.append("traceability Markdown does not list REQ-FRESH-AGENT-SKILL-ROOT-033")

    add_check(
        checks,
        "traceability-doc-sync",
        not problems,
        "traceability JSON and Markdown list the same requirement IDs and preserve the known v1 gap",
        ["research/requirements-traceability.json", "research/requirements-traceability.md"],
        problems,
    )


def audit_release_consistency(root: Path) -> dict[str, Any]:
    manifest, manifest_errors = load_manifest(root)
    checks: list[dict[str, Any]] = []
    if manifest_errors:
        add_check(checks, "manifest-load", False, "suite manifest can be loaded", ["suite-manifest.json"], manifest_errors)
    else:
        check_skill_inventory(root, manifest, checks)
        check_validation_commands(root, manifest, checks)
        check_version_and_docs(root, manifest, checks)
    check_traceability_docs(root, checks)
    failing = [item for item in checks if not item["ok"]]
    return {
        "schema": "ctf-release-consistency-audit-v1",
        "root": str(root),
        "ok": not failing,
        "check_count": len(checks),
        "failing_count": len(failing),
        "failing_ids": [item["id"] for item in failing],
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit release consistency for the CTF Agent skill suite")
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    result = audit_release_consistency(Path(args.root))
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"release_consistency_ok={result['ok']}")
        for item in result["checks"]:
            status = "ok" if item["ok"] else "fail"
            print(f"{status}: {item['id']} - {item['summary']}")
            for problem in item["problems"]:
                print(f"  - {problem}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
