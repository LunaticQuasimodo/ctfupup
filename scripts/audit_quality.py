#!/usr/bin/env python3
"""Audit CTF Agent skill-suite quality beyond basic file existence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SKILLS = {
    "ctf-master",
    "ctf-web",
    "ctf-pwn-rev",
    "ctf-forensics-crypto",
    "ctf-specialty",
    "ctf-tool-preflight",
    "ctf-knowledge",
    "ctf-anti-injection",
    "ctf-handoff-report",
}
EXPECTED_ROLES = {
    "master": {"ctf-master"},
    "category": {"ctf-web", "ctf-pwn-rev", "ctf-forensics-crypto", "ctf-specialty"},
    "support": {"ctf-tool-preflight", "ctf-knowledge", "ctf-anti-injection", "ctf-handoff-report"},
}
EXPECTED_ROUTE_TOPICS = {
    "web.ssti",
    "pwn.stack",
    "rev.checker",
    "crypto.xor-stream",
    "forensics.log-encoding",
    "meta.prompt-injection",
    "specialty.ai-tool",
}
EXPECTED_DEMO_FIXTURES = {
    "friendly-login": "meta.prompt-injection",
    "crypto-xor": "crypto.xor-stream",
    "reverse-rot13": "rev.checker",
    "pwn-offset": "pwn.stack",
    "forensics-b64log": "forensics.log-encoding",
}
AUX_DOC_NAMES = {
    "README.md",
    "INSTALLATION_GUIDE.md",
    "QUICK_REFERENCE.md",
    "CHANGELOG.md",
}


def read_text(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def has_terms(root: Path, rel: str, terms: list[str]) -> tuple[bool, list[str]]:
    text = read_text(root, rel)
    missing = [term for term in terms if term not in text]
    return not missing, missing


def regex_terms(root: Path, rel: str, patterns: list[str]) -> tuple[bool, list[str]]:
    text = read_text(root, rel)
    missing = [pattern for pattern in patterns if not re.search(pattern, text, re.I)]
    return not missing, missing


def add_check(checks: list[dict], check_id: str, ok: bool, summary: str, evidence: list[str], problems: list[str] | None = None) -> None:
    checks.append({
        "id": check_id,
        "ok": ok,
        "summary": summary,
        "evidence": evidence,
        "problems": problems or [],
    })


def check_manifest(root: Path, checks: list[dict]) -> None:
    manifest_path = root / "suite-manifest.json"
    if not manifest_path.exists():
        add_check(checks, "manifest-layering", False, "suite manifest is missing", ["suite-manifest.json"], ["missing manifest"])
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    skills = manifest.get("skills", [])
    names = {item.get("name") for item in skills}
    role_map: dict[str, set[str]] = {}
    for item in skills:
        role_map.setdefault(item.get("role", ""), set()).add(item.get("name", ""))

    problems = []
    if names != EXPECTED_SKILLS:
        problems.append(f"skill set mismatch expected={sorted(EXPECTED_SKILLS)} actual={sorted(names)}")
    for role, expected_names in EXPECTED_ROLES.items():
        actual = role_map.get(role, set())
        if actual != expected_names:
            problems.append(f"role {role} mismatch expected={sorted(expected_names)} actual={sorted(actual)}")
    if not re.match(r"^\d+\.\d+\.\d+$", manifest.get("version", "")):
        problems.append("version is not semver-like")
    purpose = manifest.get("purpose", "")
    if "legal CTFs" not in purpose or "authorized labs" not in purpose:
        problems.append("purpose must keep legal/authorized boundary")
    add_check(
        checks,
        "manifest-layering",
        not problems,
        "manifest declares the intended master/category/support skill architecture",
        ["suite-manifest.json"],
        problems,
    )


def check_progressive_disclosure(root: Path, checks: list[dict], max_skill_lines: int) -> None:
    problems = []
    evidence = []
    for skill_dir in sorted((root / "skills").glob("ctf-*")):
        skill_md = skill_dir / "SKILL.md"
        evidence.append(str(skill_md.relative_to(root)))
        lines = skill_md.read_text(encoding="utf-8").splitlines()
        if len(lines) > max_skill_lines:
            problems.append(f"{skill_md.relative_to(root)} has {len(lines)} lines > {max_skill_lines}")
        if not (skill_dir / "references").exists():
            problems.append(f"{skill_dir.relative_to(root)} lacks references/ for progressive disclosure")
        for aux_name in AUX_DOC_NAMES:
            aux = skill_dir / aux_name
            if aux.exists():
                problems.append(f"{aux.relative_to(root)} should not live inside a skill directory")
    add_check(
        checks,
        "progressive-disclosure",
        not problems,
        "SKILL.md files stay compact and detailed material lives in references/scripts",
        evidence,
        problems,
    )


def check_reference_absorption(root: Path, checks: list[dict]) -> None:
    source_ok, source_missing = has_terms(root, "research/seed-source-matrix.md", [
        "src-hunter-skill",
        "yaklang/hack-skills",
        "red_team_skill",
        "Scope gate",
        "deep topic",
        "Runner/tricks/bypass/verdict",
        "tool whitelist",
        "EvidenceRecord",
    ])
    audit_ok, audit_missing = has_terms(root, "REFLECTION_AUDIT.md", [
        "Checkpoint workflow",
        "Scope gate",
        "Master -> category -> deep topic",
        "Runner/tricks/bypass/verdict",
        "Structured evidence",
        "Context protection",
    ])
    problems = [f"seed-source-matrix missing {term}" for term in source_missing]
    problems.extend(f"REFLECTION_AUDIT missing {term}" for term in audit_missing)
    add_check(
        checks,
        "reference-absorption",
        source_ok and audit_ok,
        "requested external and local skill patterns are explicitly converted into suite design choices",
        ["research/seed-source-matrix.md", "REFLECTION_AUDIT.md"],
        problems,
    )


def check_source_matrix_audit(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "scripts/audit_source_matrix.py", [
        "ctf-source-matrix-audit-v1",
        "REQUIRED_SOURCES",
        "Source Anchor",
        "Observed Signals",
        "Last Reviewed",
        "missing_provenance_count",
        "src-hunter-skill",
        "yaklang/hack-skills",
        "red_team_skill",
        "conversion_terms",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "source_matrix_audit",
        "audit_source_matrix.py",
    ])
    release_ok, release_missing = has_terms(root, "scripts/release_gate.py", [
        "audit_source_matrix.py",
    ])
    smoke_ok, smoke_missing = has_terms(root, "scripts/validate_suite.py", [
        "audit_source_matrix.py",
        "ctf-source-matrix-audit-v1",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "test_source_matrix_audit_checks_reference_absorption",
        "missing_provenance_count",
        "source_anchor",
        "last_reviewed",
    ])
    problems = [f"audit_source_matrix.py missing {item}" for item in script_missing]
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"release_gate.py missing {item}" for item in release_missing)
    problems.extend(f"validate_suite.py missing {item}" for item in smoke_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    add_check(
        checks,
        "source-matrix-audit",
        script_ok and manifest_ok and release_ok and smoke_ok and test_ok,
        "reference-source absorption stays structured, source-specific, and tied to local conversions",
        [
            "scripts/audit_source_matrix.py",
            "research/seed-source-matrix.md",
            "suite-manifest.json",
            "scripts/release_gate.py",
            "tests/test_scripts.py",
        ],
        problems,
    )


def check_safety_and_interfaces(root: Path, checks: list[dict]) -> None:
    safety_ok, safety_missing = regex_terms(root, "skills/ctf-master/SKILL.md", [
        r"legal CTF",
        r"authorized lab",
        r"local isolated",
        r"scope gate",
        r"EvidenceRecord",
    ])
    gate_ok, gate_missing = regex_terms(root, "skills/ctf-master/references/acceptance-gates.md", [
        r"Authorization",
        r"Scope",
        r"Human Intervention",
        r"Handoff",
    ])
    schema_ok, schema_missing = has_terms(root, "skills/ctf-master/references/state-schema.md", [
        "ChallengeProfile",
        "CTFRunState",
        "EvidenceRecord",
        "HandoffPacket",
    ])
    tool_ok, tool_missing = has_terms(root, "skills/ctf-master/references/tool-card-template.md", ["ToolCard"])
    problems = [f"ctf-master/SKILL.md missing {item}" for item in safety_missing]
    problems.extend(f"acceptance-gates.md missing {item}" for item in gate_missing)
    problems.extend(f"state-schema.md missing {item}" for item in schema_missing)
    problems.extend(f"tool-card-template.md missing {item}" for item in tool_missing)
    add_check(
        checks,
        "safety-and-interfaces",
        safety_ok and gate_ok and schema_ok and tool_ok,
        "legal scope, evidence discipline, and core data contracts are explicit",
        [
            "skills/ctf-master/SKILL.md",
            "skills/ctf-master/references/acceptance-gates.md",
            "skills/ctf-master/references/state-schema.md",
            "skills/ctf-master/references/tool-card-template.md",
        ],
        problems,
    )


def check_routing_quality(root: Path, checks: list[dict]) -> None:
    route_text = read_text(root, "skills/ctf-master/scripts/route_topic.py")
    problems = []
    for topic in sorted(EXPECTED_ROUTE_TOPICS):
        if topic not in route_text:
            problems.append(f"route_topic.py missing {topic}")
    if r"tool_calls?" not in route_text:
        problems.append("AI/tool route should match tool_calls? rather than only generic tool phrases")
    if r"canary (?:token|secret|value|string)" not in route_text:
        problems.append("AI/tool route should qualify canary as token/secret/value/string")
    if re.search(r'\(r"\\bcanary\\b', route_text):
        problems.append("generic canary signal can misroute pwn stack canaries into AI/tool topic")
    add_check(
        checks,
        "routing-quality",
        not problems,
        "deep-topic router covers major CTF families and guards against known route-noise",
        ["skills/ctf-master/scripts/route_topic.py"],
        problems,
    )


def check_demo_regression(root: Path, checks: list[dict]) -> None:
    problems = []
    evidence = ["demo-fixtures", "scripts/run_demo_solve.py", "tests/test_scripts.py"]
    demo_root = root / "demo-fixtures"
    test_text = read_text(root, "tests/test_scripts.py")
    solver_text = read_text(root, "scripts/run_demo_solve.py")
    for fixture, expected_topic in EXPECTED_DEMO_FIXTURES.items():
        if not (demo_root / fixture).exists():
            problems.append(f"missing demo fixture {fixture}")
        if fixture not in solver_text:
            problems.append(f"run_demo_solve.py does not register {fixture}")
        if fixture not in test_text:
            problems.append(f"tests do not assert fixture {fixture}")
        if expected_topic not in test_text:
            problems.append(f"tests do not assert topic {expected_topic}")
    if "reflection" not in solver_text:
        problems.append("demo solver should render reflection artifacts")
    add_check(
        checks,
        "demo-regression",
        not problems,
        "safe synthetic demos cover web, crypto, reverse, pwn, and forensics paths",
        evidence,
        problems,
    )


def check_reflection_loop(root: Path, checks: list[dict]) -> None:
    audit_ok, audit_missing = has_terms(root, "REFLECTION_AUDIT.md", [
        "Hard Questions",
        "Next Iteration Triggers",
        "Remaining Risks",
        "Completion Criteria",
    ])
    script_ok, script_missing = has_terms(root, "skills/ctf-handoff-report/scripts/render_reflection.py", [
        "improvement_candidates",
        "hard_questions",
        "ToolCard",
        "prompt injection",
        "dead end",
    ])
    problems = [f"REFLECTION_AUDIT missing {item}" for item in audit_missing]
    problems.extend(f"render_reflection.py missing {item}" for item in script_missing)
    add_check(
        checks,
        "reflection-loop",
        audit_ok and script_ok,
        "post-run reflection produces concrete improvement candidates and hard questions",
        ["REFLECTION_AUDIT.md", "skills/ctf-handoff-report/scripts/render_reflection.py"],
        problems,
    )


def check_pressure_audit(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "scripts/audit_pressure.py", [
        "ctf-agent-skills-pressure-audit-v1",
        "PRESSURE_CASES",
        "accepted_gap",
        "REQ-EVAL-FRESH-AGENT",
        "pressure_cases",
        "hard_questions",
        "next_actions",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "pressure_audit",
        "audit_pressure.py",
    ])
    release_ok, release_missing = has_terms(root, "scripts/release_gate.py", [
        "audit_pressure.py",
    ])
    smoke_ok, smoke_missing = has_terms(root, "scripts/validate_suite.py", [
        "audit_pressure.py",
        "ctf-agent-skills-pressure-audit-v1",
        "accepted_gap_ids",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "test_pressure_audit_reports_hard_questions_and_honest_gap",
        "ctf-agent-skills-pressure-audit-v1",
    ])
    reflection_ok, reflection_missing = has_terms(root, "REFLECTION_AUDIT.md", [
        "Pressure audit",
        "accepted gap",
    ])
    problems = [f"audit_pressure.py missing {item}" for item in script_missing]
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"release_gate.py missing {item}" for item in release_missing)
    problems.extend(f"validate_suite.py missing {item}" for item in smoke_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    problems.extend(f"REFLECTION_AUDIT.md missing {item}" for item in reflection_missing)
    add_check(
        checks,
        "pressure-audit",
        script_ok and manifest_ok and release_ok and smoke_ok and test_ok and reflection_ok,
        "hard questions, failure modes, accepted gaps, and next actions are machine-readable",
        [
            "scripts/audit_pressure.py",
            "suite-manifest.json",
            "scripts/release_gate.py",
            "tests/test_scripts.py",
            "REFLECTION_AUDIT.md",
        ],
        problems,
    )


def check_category_coverage_audit(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "scripts/audit_category_coverage.py", [
        "ctf-category-coverage-audit-v1",
        "CATEGORY_SPECS",
        "future_benchmark_needed",
        "core_category_count",
        "specialty_category_count",
        "specialty.cloud-k8s",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "category_coverage_audit",
        "audit_category_coverage.py",
    ])
    release_ok, release_missing = has_terms(root, "scripts/release_gate.py", [
        "audit_category_coverage.py",
    ])
    smoke_ok, smoke_missing = has_terms(root, "scripts/validate_suite.py", [
        "audit_category_coverage.py",
        "ctf-category-coverage-audit-v1",
        "core_category_count",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "test_category_coverage_audit_checks_core_and_specialty_coverage",
        "ctf-category-coverage-audit-v1",
    ])
    reflection_ok, reflection_missing = has_terms(root, "REFLECTION_AUDIT.md", [
        "Category coverage audit",
        "future benchmark coverage",
    ])
    problems = [f"audit_category_coverage.py missing {item}" for item in script_missing]
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"release_gate.py missing {item}" for item in release_missing)
    problems.extend(f"validate_suite.py missing {item}" for item in smoke_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    problems.extend(f"REFLECTION_AUDIT.md missing {item}" for item in reflection_missing)
    add_check(
        checks,
        "category-coverage-audit",
        script_ok and manifest_ok and release_ok and smoke_ok and test_ok and reflection_ok,
        "major CTF categories have route, reference, demo/forward, and benchmark-gap visibility",
        [
            "scripts/audit_category_coverage.py",
            "suite-manifest.json",
            "scripts/release_gate.py",
            "tests/test_scripts.py",
            "REFLECTION_AUDIT.md",
        ],
        problems,
    )


def check_evidence_contract_audit(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "scripts/audit_evidence_contract.py", [
        "ctf-evidence-contract-audit-v1",
        "evidence-record-reproducibility",
        "writeup-verification-contract",
        "verdict consumes evidence only",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "evidence_contract_audit",
        "audit_evidence_contract.py",
    ])
    release_ok, release_missing = has_terms(root, "scripts/release_gate.py", [
        "audit_evidence_contract.py",
    ])
    smoke_ok, smoke_missing = has_terms(root, "scripts/validate_suite.py", [
        "audit_evidence_contract.py",
        "ctf-evidence-contract-audit-v1",
        "evidence-record-reproducibility",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "test_evidence_contract_audit_checks_reproducible_report_contract",
        "ctf-evidence-contract-audit-v1",
    ])
    reflection_ok, reflection_missing = has_terms(root, "REFLECTION_AUDIT.md", [
        "Evidence contract audit",
        "evidence contract",
        "reproducible evidence",
        "verdict-style separation",
    ])
    problems = [f"audit_evidence_contract.py missing {item}" for item in script_missing]
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"release_gate.py missing {item}" for item in release_missing)
    problems.extend(f"validate_suite.py missing {item}" for item in smoke_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    problems.extend(f"REFLECTION_AUDIT.md missing {item}" for item in reflection_missing)
    add_check(
        checks,
        "evidence-contract-audit",
        script_ok and manifest_ok and release_ok and smoke_ok and test_ok and reflection_ok,
        "report, handoff, and writeup conclusions stay tied to reproducible EvidenceRecord artifacts",
        [
            "scripts/audit_evidence_contract.py",
            "skills/ctf-master/references/state-schema.md",
            "skills/ctf-handoff-report/references/writeup-template.md",
            "suite-manifest.json",
            "tests/test_scripts.py",
        ],
        problems,
    )


def check_release_consistency_audit(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "scripts/audit_release_consistency.py", [
        "ctf-release-consistency-audit-v1",
        "skill-inventory",
        "validation-commands",
        "version-and-status-docs",
        "traceability-doc-sync",
        "REQ-RELEASE-CONSISTENCY-030",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "release_consistency_audit",
        "audit_release_consistency.py",
    ])
    release_ok, release_missing = has_terms(root, "scripts/release_gate.py", [
        "audit_release_consistency.py",
    ])
    smoke_ok, smoke_missing = has_terms(root, "scripts/validate_suite.py", [
        "audit_release_consistency.py",
        "ctf-release-consistency-audit-v1",
        "traceability-doc-sync",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "test_release_consistency_audit_checks_manifest_docs_and_traceability",
        "ctf-release-consistency-audit-v1",
    ])
    reflection_ok, reflection_missing = has_terms(root, "REFLECTION_AUDIT.md", [
        "Release consistency audit",
        "0.38.0",
    ])
    problems = [f"audit_release_consistency.py missing {item}" for item in script_missing]
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"release_gate.py missing {item}" for item in release_missing)
    problems.extend(f"validate_suite.py missing {item}" for item in smoke_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    problems.extend(f"REFLECTION_AUDIT.md missing {item}" for item in reflection_missing)
    add_check(
        checks,
        "release-consistency-audit",
        script_ok and manifest_ok and release_ok and smoke_ok and test_ok and reflection_ok,
        "release version, manifest, validation commands, and traceability docs are kept in sync",
        [
            "scripts/audit_release_consistency.py",
            "suite-manifest.json",
            "scripts/release_gate.py",
            "tests/test_scripts.py",
            "REFLECTION_AUDIT.md",
        ],
        problems,
    )


def check_checkpoint_discipline(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "skills/ctf-master/scripts/checkpoint_state.py", [
        "ctf-run-checkpoint-v1",
        "resume_checklist",
        "resume_risks",
        "artifact_paths",
        "validate_state",
    ])
    loop_ok, loop_missing = has_terms(root, "skills/ctf-master/references/ctf-loop.md", [
        "Checkpoint",
        "checkpoint_state.py",
        "Context Compression",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "checkpoint_state.py",
        "checkpoint",
    ])
    package_ok, package_missing = has_terms(root, "skills/ctf-handoff-report/scripts/finalize_run.py", [
        "checkpoint.md",
        "CHECKPOINT_STATE",
    ])
    demo_ok, demo_missing = has_terms(root, "scripts/run_demo_solve.py", [
        "render_checkpoint",
        "checkpoint.md",
    ])
    problems = [f"checkpoint_state.py missing {item}" for item in script_missing]
    problems.extend(f"ctf-loop.md missing {item}" for item in loop_missing)
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"finalize_run.py missing {item}" for item in package_missing)
    problems.extend(f"run_demo_solve.py missing {item}" for item in demo_missing)
    add_check(
        checks,
        "checkpoint-discipline",
        script_ok and loop_ok and manifest_ok and package_ok and demo_ok,
        "state checkpointing and context compression are executable workflow artifacts",
        [
            "skills/ctf-master/scripts/checkpoint_state.py",
            "skills/ctf-master/references/ctf-loop.md",
            "skills/ctf-handoff-report/scripts/finalize_run.py",
            "scripts/run_demo_solve.py",
        ],
        problems,
    )


def check_profile_update_surface(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "skills/ctf-master/scripts/update_profile.py", [
        "ctf-profile-update-v1",
        "ChallengeProfile",
        "scope_status",
        "category_inferred",
        "add-attachment",
        "sha256",
        "handoff_ready",
    ])
    master_ok, master_missing = has_terms(root, "skills/ctf-master/SKILL.md", [
        "update_profile.py",
        "ChallengeProfile",
        "without manual JSON editing",
    ])
    schema_ok, schema_missing = has_terms(root, "skills/ctf-master/references/state-schema.md", [
        "update_profile.py",
        "ChallengeProfile",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "update_profile.py",
        "profile_update",
    ])
    smoke_ok, smoke_missing = has_terms(root, "scripts/validate_suite.py", [
        "update_profile.py",
        "ctf-profile-update-v1",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "test_update_profile_updates_scope_targets_and_attachments",
        "test_gate_state_blocks_unsafe_progress_and_passes_report_ready_state",
    ])
    problems = [f"update_profile.py missing {item}" for item in script_missing]
    problems.extend(f"ctf-master/SKILL.md missing {item}" for item in master_missing)
    problems.extend(f"state-schema.md missing {item}" for item in schema_missing)
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"validate_suite.py missing {item}" for item in smoke_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    add_check(
        checks,
        "profile-update-surface",
        script_ok and master_ok and schema_ok and manifest_ok and smoke_ok and test_ok,
        "ChallengeProfile updates are scripted instead of requiring manual JSON edits",
        [
            "skills/ctf-master/scripts/update_profile.py",
            "skills/ctf-master/SKILL.md",
            "suite-manifest.json",
            "tests/test_scripts.py",
        ],
        problems,
    )


def check_phase_gate_discipline(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "skills/ctf-master/scripts/gate_state.py", [
        "ctf-run-phase-gates-v1",
        "intake-scope",
        "triage-untrusted-input",
        "solve-verification",
        "report-readiness",
        "handoff-readiness",
        "require-ready",
    ])
    reference_ok, reference_missing = has_terms(root, "skills/ctf-master/references/phase-gates.md", [
        "intake-scope",
        "triage-untrusted-input",
        "route-decision",
        "experiment-loop",
        "solve-verification",
        "report-readiness",
        "handoff-readiness",
    ])
    master_ok, master_missing = has_terms(root, "skills/ctf-master/SKILL.md", [
        "Run phase gates",
        "gate_state.py",
        "phase-gates.md",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "gate_state.py",
        "phase_gates",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "test_gate_state_blocks_unsafe_progress_and_passes_report_ready_state",
        "handoff-readiness",
    ])
    problems = [f"gate_state.py missing {item}" for item in script_missing]
    problems.extend(f"phase-gates.md missing {item}" for item in reference_missing)
    problems.extend(f"ctf-master/SKILL.md missing {item}" for item in master_missing)
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    add_check(
        checks,
        "phase-gate-discipline",
        script_ok and reference_ok and master_ok and manifest_ok and test_ok,
        "CTF run phase transitions are checked by executable state gates",
        [
            "skills/ctf-master/scripts/gate_state.py",
            "skills/ctf-master/references/phase-gates.md",
            "suite-manifest.json",
            "tests/test_scripts.py",
        ],
        problems,
    )


def check_trigger_audit(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "scripts/audit_triggers.py", [
        "ctf-skill-trigger-audit-v1",
        "INLINE_PROBES",
        "forbidden_top",
        "CUE_PATTERNS",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "trigger_audit",
        "audit_triggers.py",
    ])
    release_ok, release_missing = has_terms(root, "scripts/release_gate.py", [
        "audit_triggers.py",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "test_trigger_audit_checks_skill_metadata",
    ])
    problems = [f"audit_triggers.py missing {item}" for item in script_missing]
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"release_gate.py missing {item}" for item in release_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    add_check(
        checks,
        "trigger-audit",
        script_ok and manifest_ok and release_ok and test_ok,
        "skill trigger metadata and obvious routing conflicts are machine-checkable",
        [
            "scripts/audit_triggers.py",
            "suite-manifest.json",
            "scripts/release_gate.py",
            "tests/test_scripts.py",
        ],
        problems,
    )


def check_agent_metadata(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "scripts/audit_agent_metadata.py", [
        "ctf-agent-metadata-audit-v1",
        "default_prompt",
        "short_description",
        "display_name",
        "agents/openai.yaml",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "agent_metadata_audit",
        "audit_agent_metadata.py",
    ])
    release_ok, release_missing = has_terms(root, "scripts/release_gate.py", [
        "audit_agent_metadata.py",
    ])
    smoke_ok, smoke_missing = has_terms(root, "scripts/validate_suite.py", [
        "audit_agent_metadata.py",
        "ctf-agent-metadata-audit-v1",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "test_agent_metadata_audit_checks_openai_yaml",
    ])
    problems = [f"audit_agent_metadata.py missing {item}" for item in script_missing]
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"release_gate.py missing {item}" for item in release_missing)
    problems.extend(f"validate_suite.py missing {item}" for item in smoke_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    add_check(
        checks,
        "agent-metadata",
        script_ok and manifest_ok and release_ok and smoke_ok and test_ok,
        "agents/openai.yaml metadata stays aligned with SKILL.md trigger identity",
        [
            "scripts/audit_agent_metadata.py",
            "suite-manifest.json",
            "scripts/release_gate.py",
            "tests/test_scripts.py",
        ],
        problems,
    )


def check_forward_integrity(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "scripts/audit_forward_integrity.py", [
        "ctf-forward-integrity-audit-v1",
        "SENSITIVE_SCENARIO_FIELDS",
        "expected_answers_disclosed",
        "do_not_include_expected_answers",
        "fresh-agent-run-record-template.json",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "forward_integrity_audit",
        "audit_forward_integrity.py",
    ])
    release_ok, release_missing = has_terms(root, "scripts/release_gate.py", [
        "audit_forward_integrity.py",
    ])
    smoke_ok, smoke_missing = has_terms(root, "scripts/validate_suite.py", [
        "audit_forward_integrity.py",
        "ctf-forward-integrity-audit-v1",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "test_forward_integrity_audit_blocks_answer_leakage",
    ])
    problems = [f"audit_forward_integrity.py missing {item}" for item in script_missing]
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"release_gate.py missing {item}" for item in release_missing)
    problems.extend(f"validate_suite.py missing {item}" for item in smoke_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    add_check(
        checks,
        "forward-integrity",
        script_ok and manifest_ok and release_ok and smoke_ok and test_ok,
        "fresh-agent forward-test prompts and record templates avoid expected-answer leakage",
        [
            "scripts/audit_forward_integrity.py",
            "forward-tests/scenarios",
            "forward-tests/fresh-agent-run-record-template.json",
            "suite-manifest.json",
            "tests/test_scripts.py",
        ],
        problems,
    )


def check_forward_run_init(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "scripts/init_forward_run.py", [
        "ctf-forward-run-init-v1",
        "ctf-forward-run-workspace-v1",
        "write_prompt_pack",
        "audit_forward_integrity",
        "fresh-agent-run-record.json",
        "rubric-template.json",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "forward_run_init",
        "init_forward_run.py",
    ])
    release_ok, release_missing = has_terms(root, "scripts/release_gate.py", [
        "init_forward_run.py",
    ])
    smoke_ok, smoke_missing = has_terms(root, "scripts/validate_suite.py", [
        "init_forward_run.py",
        "ctf-forward-run-init-v1",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "test_init_forward_run_creates_fresh_workspace",
    ])
    problems = [f"init_forward_run.py missing {item}" for item in script_missing]
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"release_gate.py missing {item}" for item in release_missing)
    problems.extend(f"validate_suite.py missing {item}" for item in smoke_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    add_check(
        checks,
        "forward-run-init",
        script_ok and manifest_ok and release_ok and smoke_ok and test_ok,
        "fresh-agent forward-test workspaces can be initialized without hand-built evidence paths",
        [
            "scripts/init_forward_run.py",
            "scripts/run_forward_suite.py",
            "scripts/audit_forward_integrity.py",
            "suite-manifest.json",
            "tests/test_scripts.py",
        ],
        problems,
    )


def check_forward_run_rubric(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "scripts/render_forward_rubric.py", [
        "ctf-forward-human-rubric-v1",
        "ctf-forward-human-rubric-render-v1",
        "untrusted_content_boundary",
        "minimum_total",
        "scenario_scores",
    ])
    init_ok, init_missing = has_terms(root, "scripts/init_forward_run.py", [
        "build_rubric_template",
        "rubric_template_path",
        "rubric-template.json",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "forward_rubric_template",
        "render_forward_rubric.py",
    ])
    smoke_ok, smoke_missing = has_terms(root, "scripts/validate_suite.py", [
        "render_forward_rubric.py",
        "ctf-forward-human-rubric-render-v1",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "test_render_forward_rubric_creates_review_template",
        "ctf-forward-human-rubric-v1",
    ])
    problems = [f"render_forward_rubric.py missing {item}" for item in script_missing]
    problems.extend(f"init_forward_run.py missing {item}" for item in init_missing)
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"validate_suite.py missing {item}" for item in smoke_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    add_check(
        checks,
        "forward-run-rubric",
        script_ok and init_ok and manifest_ok and smoke_ok and test_ok,
        "fresh-agent human rubric templates are generated with stable dimensions and scenario rows",
        [
            "scripts/render_forward_rubric.py",
            "scripts/init_forward_run.py",
            "suite-manifest.json",
            "tests/test_scripts.py",
        ],
        problems,
    )


def check_forward_handoff(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "scripts/render_forward_handoff.py", [
        "ctf-forward-handoff-render-v1",
        "FORBIDDEN_LEAK_TERMS",
        "Fresh-Agent Handoff",
        "prompt_hashes",
        "expected_skills",
    ])
    init_ok, init_missing = has_terms(root, "scripts/init_forward_run.py", [
        "build_handoff",
        "FRESH_AGENT_HANDOFF.md",
        "fresh_agent_handoff_path",
    ])
    verifier_ok, verifier_missing = has_terms(root, "scripts/verify_forward_run.py", [
        "fresh_agent_handoff_path",
        "fresh-agent handoff leaks forbidden term",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "forward_handoff_render",
        "render_forward_handoff.py",
    ])
    release_ok, release_missing = has_terms(root, "scripts/release_gate.py", [
        "render_forward_handoff.py",
        "forward-handoff.md",
    ])
    smoke_ok, smoke_missing = has_terms(root, "scripts/validate_suite.py", [
        "render_forward_handoff.py",
        "ctf-forward-handoff-render-v1",
        "fresh_agent_handoff",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "test_render_forward_handoff_creates_answer_free_packet",
        "FRESH_AGENT_HANDOFF.md",
    ])
    problems = [f"render_forward_handoff.py missing {item}" for item in script_missing]
    problems.extend(f"init_forward_run.py missing {item}" for item in init_missing)
    problems.extend(f"verify_forward_run.py missing {item}" for item in verifier_missing)
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"release_gate.py missing {item}" for item in release_missing)
    problems.extend(f"validate_suite.py missing {item}" for item in smoke_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    add_check(
        checks,
        "forward-handoff",
        script_ok and init_ok and verifier_ok and manifest_ok and release_ok and smoke_ok and test_ok,
        "fresh-agent runs get an answer-free sealed handoff packet",
        [
            "scripts/render_forward_handoff.py",
            "scripts/init_forward_run.py",
            "scripts/verify_forward_run.py",
            "suite-manifest.json",
            "tests/test_scripts.py",
        ],
        problems,
    )


def check_fresh_agent_readiness(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "scripts/audit_fresh_agent_readiness.py", [
        "ctf-fresh-agent-readiness-audit-v1",
        "ready_for_fresh_agent",
        "FORBIDDEN_LEAK_TERMS",
        "response_dir should be empty before fresh-agent run",
        "score_summary_path should not exist before fresh-agent run",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "fresh_agent_readiness_audit",
        "audit_fresh_agent_readiness.py",
    ])
    release_ok, release_missing = has_terms(root, "scripts/release_gate.py", [
        "audit_fresh_agent_readiness.py",
        "forward-run-workspace.json",
    ])
    smoke_ok, smoke_missing = has_terms(root, "scripts/validate_suite.py", [
        "audit_fresh_agent_readiness.py",
        "ctf-fresh-agent-readiness-audit-v1",
        "ready_for_fresh_agent",
    ])
    completion_ok, completion_missing = has_terms(root, "scripts/audit_completion.py", [
        "fresh_agent_readiness_audit",
        "audit_fresh_agent_readiness.py",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "test_fresh_agent_readiness_audit_checks_clean_handoff_materials",
        "ctf-fresh-agent-readiness-audit-v1",
    ])
    problems = [f"audit_fresh_agent_readiness.py missing {item}" for item in script_missing]
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"release_gate.py missing {item}" for item in release_missing)
    problems.extend(f"validate_suite.py missing {item}" for item in smoke_missing)
    problems.extend(f"audit_completion.py missing {item}" for item in completion_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    add_check(
        checks,
        "fresh-agent-readiness",
        script_ok and manifest_ok and release_ok and smoke_ok and completion_ok and test_ok,
        "fresh-agent workspaces have a pre-run audit for material completeness and answer-leak prevention",
        [
            "scripts/audit_fresh_agent_readiness.py",
            "scripts/init_forward_run.py",
            "scripts/render_forward_handoff.py",
            "suite-manifest.json",
            "tests/test_scripts.py",
        ],
        problems,
    )


def check_fresh_agent_packet(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "scripts/export_fresh_agent_packet.py", [
        "ctf-fresh-agent-packet-export-v1",
        "ctf-fresh-agent-packet-v1",
        "PACKET_MANIFEST.json",
        "allowed_skill_root",
        "RESPONSE_RULES.md",
        "readiness audit failed",
        "excluded_materials",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "fresh_agent_packet_export",
        "export_fresh_agent_packet.py",
    ])
    release_ok, release_missing = has_terms(root, "scripts/release_gate.py", [
        "export_fresh_agent_packet.py",
        "fresh-agent-packet",
    ])
    smoke_ok, smoke_missing = has_terms(root, "scripts/validate_suite.py", [
        "export_fresh_agent_packet.py",
        "ctf-fresh-agent-packet-export-v1",
        "ctf-fresh-agent-packet-v1",
    ])
    completion_ok, completion_missing = has_terms(root, "scripts/audit_completion.py", [
        "fresh_agent_packet_export",
        "export_fresh_agent_packet.py",
    ])
    readme_ok, readme_missing = has_terms(root, "forward-tests/README.md", [
        "export_fresh_agent_packet.py",
        "PACKET_MANIFEST.json",
        "prompts/",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "test_export_fresh_agent_packet_contains_only_handoff_and_prompts",
        "ctf-fresh-agent-packet-v1",
    ])
    problems = [f"export_fresh_agent_packet.py missing {item}" for item in script_missing]
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"release_gate.py missing {item}" for item in release_missing)
    problems.extend(f"validate_suite.py missing {item}" for item in smoke_missing)
    problems.extend(f"audit_completion.py missing {item}" for item in completion_missing)
    problems.extend(f"forward-tests/README.md missing {item}" for item in readme_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    add_check(
        checks,
        "fresh-agent-packet",
        script_ok and manifest_ok and release_ok and smoke_ok and completion_ok and readme_ok and test_ok,
        "fresh-agent launch materials can be exported as a minimal answer-free packet",
        [
            "scripts/export_fresh_agent_packet.py",
            "scripts/audit_fresh_agent_readiness.py",
            "forward-tests/README.md",
            "suite-manifest.json",
            "tests/test_scripts.py",
        ],
        problems,
    )


def check_fresh_agent_packet_audit(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "scripts/audit_fresh_agent_packet.py", [
        "ctf-fresh-agent-packet-audit-v1",
        "REQUIRED_TOP_LEVEL_FILES",
        "FORBIDDEN_FILE_NAMES",
        "PACKET_MANIFEST.json schema is not ctf-fresh-agent-packet-v1",
        "allowed_skill_root",
        "prompt sha256 mismatch",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "fresh_agent_packet_audit",
        "audit_fresh_agent_packet.py",
    ])
    release_ok, release_missing = has_terms(root, "scripts/release_gate.py", [
        "audit_fresh_agent_packet.py",
        "fresh-agent-packet",
    ])
    smoke_ok, smoke_missing = has_terms(root, "scripts/validate_suite.py", [
        "audit_fresh_agent_packet.py",
        "ctf-fresh-agent-packet-audit-v1",
    ])
    completion_ok, completion_missing = has_terms(root, "scripts/audit_completion.py", [
        "fresh_agent_packet_audit",
        "audit_fresh_agent_packet.py",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "test_audit_fresh_agent_packet_detects_extra_files_and_hash_drift",
        "ctf-fresh-agent-packet-audit-v1",
    ])
    problems = [f"audit_fresh_agent_packet.py missing {item}" for item in script_missing]
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"release_gate.py missing {item}" for item in release_missing)
    problems.extend(f"validate_suite.py missing {item}" for item in smoke_missing)
    problems.extend(f"audit_completion.py missing {item}" for item in completion_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    add_check(
        checks,
        "fresh-agent-packet-audit",
        script_ok and manifest_ok and release_ok and smoke_ok and completion_ok and test_ok,
        "exported fresh-agent packets can be verified independently after copy or handoff",
        [
            "scripts/audit_fresh_agent_packet.py",
            "scripts/export_fresh_agent_packet.py",
            "suite-manifest.json",
            "scripts/release_gate.py",
            "tests/test_scripts.py",
        ],
        problems,
    )


def check_fresh_agent_launch_prompt(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "scripts/render_fresh_agent_launch_prompt.py", [
        "ctf-fresh-agent-launch-prompt-render-v1",
        "audit_packet",
        "Fresh-Agent Forward Test Launch Prompt",
        "Allowed local skill root",
        "Resolve `./skills/<skill-name>`",
        "development notes",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "fresh_agent_launch_prompt_render",
        "render_fresh_agent_launch_prompt.py",
    ])
    release_ok, release_missing = has_terms(root, "scripts/release_gate.py", [
        "render_fresh_agent_launch_prompt.py",
        "fresh-agent-launch-prompt.md",
    ])
    smoke_ok, smoke_missing = has_terms(root, "scripts/validate_suite.py", [
        "render_fresh_agent_launch_prompt.py",
        "ctf-fresh-agent-launch-prompt-render-v1",
        "Fresh-Agent Forward Test Launch Prompt",
    ])
    completion_ok, completion_missing = has_terms(root, "scripts/audit_completion.py", [
        "fresh_agent_launch_prompt_render",
        "render_fresh_agent_launch_prompt.py",
    ])
    readme_ok, readme_missing = has_terms(root, "forward-tests/README.md", [
        "render_fresh_agent_launch_prompt.py",
        "launch prompt",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "test_render_fresh_agent_launch_prompt_uses_packet_and_allowed_skill_root",
        "ctf-fresh-agent-launch-prompt-render-v1",
    ])
    problems = [f"render_fresh_agent_launch_prompt.py missing {item}" for item in script_missing]
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"release_gate.py missing {item}" for item in release_missing)
    problems.extend(f"validate_suite.py missing {item}" for item in smoke_missing)
    problems.extend(f"audit_completion.py missing {item}" for item in completion_missing)
    problems.extend(f"forward-tests/README.md missing {item}" for item in readme_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    add_check(
        checks,
        "fresh-agent-launch-prompt",
        script_ok and manifest_ok and release_ok and smoke_ok and completion_ok and readme_ok and test_ok,
        "audited packets can render a copy-paste fresh-agent launch prompt with packet-local prompts and an allowed skill root",
        [
            "scripts/render_fresh_agent_launch_prompt.py",
            "scripts/audit_fresh_agent_packet.py",
            "forward-tests/README.md",
            "suite-manifest.json",
            "tests/test_scripts.py",
        ],
        problems,
    )


def check_forward_run_finalize(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "scripts/finalize_forward_run.py", [
        "ctf-forward-run-finalize-v1",
        "score_responses",
        "response_hashes",
        "confirm_fresh_context",
        "rubric-json",
        "compute_pass_fail",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "forward_run_finalize",
        "finalize_forward_run.py",
    ])
    smoke_ok, smoke_missing = has_terms(root, "scripts/validate_suite.py", [
        "finalize_forward_run.py",
        "ctf-forward-run-finalize-v1",
        "must not pass without fresh-context/rubric confirmation",
    ])
    verifier_ok, verifier_missing = has_terms(root, "scripts/verify_forward_run.py", [
        "response_hashes",
        "response hash mismatch",
    ])
    readme_ok, readme_missing = has_terms(root, "forward-tests/README.md", [
        "finalize_forward_run.py",
        "rubric JSON",
        "confirm-fresh-context",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "test_finalize_forward_run_scores_hashes_and_preserves_honesty_gate",
    ])
    problems = [f"finalize_forward_run.py missing {item}" for item in script_missing]
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"validate_suite.py missing {item}" for item in smoke_missing)
    problems.extend(f"verify_forward_run.py missing {item}" for item in verifier_missing)
    problems.extend(f"forward-tests/README.md missing {item}" for item in readme_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    add_check(
        checks,
        "forward-run-finalize",
        script_ok and manifest_ok and smoke_ok and verifier_ok and readme_ok and test_ok,
        "fresh-agent response directories can be scored, hashed, and finalized without weakening honesty gates",
        [
            "scripts/finalize_forward_run.py",
            "scripts/verify_forward_run.py",
            "forward-tests/README.md",
            "suite-manifest.json",
            "tests/test_scripts.py",
        ],
        problems,
    )


def check_validation_isolation(root: Path, checks: list[dict]) -> None:
    release_ok, release_missing = has_terms(root, "scripts/release_gate.py", [
        "tempfile.mkdtemp",
        "run_root",
        "ctf-agent-skills-release-",
        'run_root / "demo"',
        'run_root / "forward-init"',
    ])
    smoke_ok, smoke_missing = has_terms(root, "scripts/validate_suite.py", [
        "tempfile.mkdtemp",
        "smoke_tmp",
        "demo_smoke_dir",
        "forward_init_dir",
        "benchmark_smoke_dir",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "run_root",
        "ctf-agent-skills-release-demo",
        "ctf-agent-skills-forward-init",
    ])
    forbidden_by_file = {
        "scripts/release_gate.py": [
            "/tmp/ctf-agent-skills-release-demo",
            "/tmp/ctf-agent-skills-forward-init",
        ],
        "scripts/validate_suite.py": [
            "/tmp/ctf-suite-smoke-state.json",
            "/tmp/ctf-suite-smoke-package",
            "/tmp/ctf-suite-demo-smoke",
            "/tmp/ctf-suite-forward-init-smoke",
            "/tmp/ctf-suite-benchmark-smoke",
            "ctf-suite-forward-response.md",
        ],
    }
    problems = [f"release_gate.py missing {item}" for item in release_missing]
    problems.extend(f"validate_suite.py missing {item}" for item in smoke_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    for rel, forbidden_values in forbidden_by_file.items():
        text = read_text(root, rel)
        for forbidden in forbidden_values:
            if forbidden in text:
                problems.append(f"{rel} still uses fixed validation path {forbidden}")
    add_check(
        checks,
        "validation-isolation",
        release_ok and smoke_ok and test_ok and not problems,
        "release and smoke validations use per-run workspaces instead of fixed /tmp outputs",
        ["scripts/release_gate.py", "scripts/validate_suite.py", "tests/test_scripts.py"],
        problems,
    )


def check_completion_audit(root: Path, checks: list[dict]) -> None:
    script_ok, script_missing = has_terms(root, "scripts/audit_completion.py", [
        "ctf-agent-skills-completion-audit-v1",
        "engineering_ok",
        "v1_ready",
        "require_v1",
        "REQ-EVAL-FRESH-AGENT",
        "fresh-agent-independent-run",
        "fresh-agent-user-waiver",
        "fresh_waiver",
        "honest-incomplete-state",
    ])
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "completion_audit",
        "audit_completion.py",
    ])
    release_ok, release_missing = has_terms(root, "scripts/release_gate.py", [
        "audit_completion.py",
    ])
    smoke_ok, smoke_missing = has_terms(root, "scripts/validate_suite.py", [
        "audit_completion.py",
        "ctf-agent-skills-completion-audit-v1",
        "completion audit should not mark v1 ready without fresh-agent proof",
    ])
    test_ok, test_missing = has_terms(root, "tests/test_scripts.py", [
        "test_completion_audit_reports_engineering_ready_but_not_v1",
        "--require-v1",
        "--fresh-waiver",
        "remaining_requirement_blockers",
    ])
    problems = [f"audit_completion.py missing {item}" for item in script_missing]
    problems.extend(f"suite-manifest missing {item}" for item in manifest_missing)
    problems.extend(f"release_gate.py missing {item}" for item in release_missing)
    problems.extend(f"validate_suite.py missing {item}" for item in smoke_missing)
    problems.extend(f"tests/test_scripts.py missing {item}" for item in test_missing)
    add_check(
        checks,
        "completion-audit",
        script_ok and manifest_ok and release_ok and smoke_ok and test_ok,
        "completion status is audited separately from installable engineering readiness",
        [
            "scripts/audit_completion.py",
            "suite-manifest.json",
            "scripts/release_gate.py",
            "scripts/validate_suite.py",
            "tests/test_scripts.py",
        ],
        problems,
    )


def check_validation_surface(root: Path, checks: list[dict]) -> None:
    manifest_ok, manifest_missing = has_terms(root, "suite-manifest.json", [
        "completion_audit",
        "quality_audit",
        "pressure_audit",
        "category_coverage_audit",
        "evidence_contract_audit",
        "release_consistency_audit",
        "source_matrix_audit",
        "forward_integrity_audit",
        "fresh_agent_readiness_audit",
        "fresh_agent_packet_export",
        "fresh_agent_packet_audit",
        "fresh_agent_launch_prompt_render",
        "forward_run_init",
        "forward_rubric_template",
        "forward_handoff_render",
        "forward_run_finalize",
        "agent_metadata_audit",
        "trigger_audit",
        "profile_update",
        "phase_gates",
        "checkpoint",
        "release_gate",
        "demo",
        "traceability",
        "official_skill_validator",
    ])
    release_ok, release_missing = has_terms(root, "scripts/release_gate.py", [
        "audit_completion.py",
        "audit_quality.py",
        "audit_pressure.py",
        "audit_category_coverage.py",
        "audit_evidence_contract.py",
        "audit_release_consistency.py",
        "audit_source_matrix.py",
        "audit_forward_integrity.py",
        "audit_fresh_agent_readiness.py",
        "export_fresh_agent_packet.py",
        "audit_fresh_agent_packet.py",
        "render_fresh_agent_launch_prompt.py",
        "render_forward_rubric.py",
        "render_forward_handoff.py",
        "init_forward_run.py",
        "audit_agent_metadata.py",
        "audit_triggers.py",
        "gate_state.py",
        "checkpoint_state.py",
        "audit_traceability.py",
        "run_demo_solve.py",
        "verify_benchmark_run.py",
        "REQ-EVAL-FRESH-AGENT",
    ])
    problems = [f"suite-manifest missing {item}" for item in manifest_missing]
    problems.extend(f"release_gate.py missing {item}" for item in release_missing)
    add_check(
        checks,
        "validation-surface",
        manifest_ok and release_ok,
        "release checks include completion, traceability, quality, demo, benchmark, and known fresh-agent honesty gate",
        ["suite-manifest.json", "scripts/release_gate.py"],
        problems,
    )


def check_fresh_agent_honesty(root: Path, checks: list[dict]) -> None:
    trace_ok, trace_missing = has_terms(root, "research/requirements-traceability.json", [
        "REQ-EVAL-FRESH-AGENT",
        '"status": "partial"',
        "final v4 independent rerun is explicitly user-waived",
    ])
    release_ok, release_missing = has_terms(root, "scripts/release_gate.py", [
        'ALLOWED_PARTIAL_OR_OPEN = {"REQ-EVAL-FRESH-AGENT"}',
    ])
    verifier_ok, verifier_missing = has_terms(root, "scripts/verify_forward_run.py", [
        "fresh_context_confirmed",
        "expected_answers_disclosed",
        "human_rubric",
    ])
    waiver_ok, waiver_missing = has_terms(root, "forward-tests/fresh-agent-evaluation-waiver.json", [
        "ctf-fresh-agent-evaluation-waiver-v1",
        "accept_current_evidence_skip_final_rerun",
        "residual_risk",
    ])
    problems = [f"requirements-traceability missing {item}" for item in trace_missing]
    problems.extend(f"release_gate.py missing {item}" for item in release_missing)
    problems.extend(f"verify_forward_run.py missing {item}" for item in verifier_missing)
    problems.extend(f"fresh-agent waiver missing {item}" for item in waiver_missing)
    add_check(
        checks,
        "fresh-agent-honesty",
        trace_ok and release_ok and verifier_ok and waiver_ok,
        "fresh-agent validation is prepared and user-waived completion is explicitly distinguished from strict verification",
        [
            "research/requirements-traceability.json",
            "forward-tests/fresh-agent-evaluation-waiver.json",
            "scripts/release_gate.py",
            "scripts/verify_forward_run.py",
        ],
        problems,
    )


def run_quality_audit(root: Path, max_skill_lines: int) -> dict:
    checks: list[dict] = []
    check_manifest(root, checks)
    check_progressive_disclosure(root, checks, max_skill_lines)
    check_reference_absorption(root, checks)
    check_source_matrix_audit(root, checks)
    check_safety_and_interfaces(root, checks)
    check_routing_quality(root, checks)
    check_demo_regression(root, checks)
    check_reflection_loop(root, checks)
    check_pressure_audit(root, checks)
    check_category_coverage_audit(root, checks)
    check_evidence_contract_audit(root, checks)
    check_release_consistency_audit(root, checks)
    check_checkpoint_discipline(root, checks)
    check_profile_update_surface(root, checks)
    check_phase_gate_discipline(root, checks)
    check_agent_metadata(root, checks)
    check_forward_integrity(root, checks)
    check_forward_run_init(root, checks)
    check_forward_run_rubric(root, checks)
    check_forward_handoff(root, checks)
    check_fresh_agent_readiness(root, checks)
    check_fresh_agent_packet(root, checks)
    check_fresh_agent_packet_audit(root, checks)
    check_fresh_agent_launch_prompt(root, checks)
    check_forward_run_finalize(root, checks)
    check_validation_isolation(root, checks)
    check_completion_audit(root, checks)
    check_trigger_audit(root, checks)
    check_validation_surface(root, checks)
    check_fresh_agent_honesty(root, checks)
    failing = [item for item in checks if not item["ok"]]
    return {
        "schema": "ctf-agent-skills-quality-audit-v1",
        "root": str(root),
        "ok": not failing,
        "check_count": len(checks),
        "failing_count": len(failing),
        "failing_ids": [item["id"] for item in failing],
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit CTF Agent skill-suite quality")
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--max-skill-lines", type=int, default=140)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    result = run_quality_audit(Path(args.root), args.max_skill_lines)
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"quality_audit_ok={result['ok']}")
        for item in result["checks"]:
            status = "ok" if item["ok"] else "fail"
            print(f"{status}: {item['id']} - {item['summary']}")
            for problem in item["problems"]:
                print(f"  - {problem}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
