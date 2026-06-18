#!/usr/bin/env python3
"""Audit that CTF conclusions remain tied to reproducible evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def read_text(root: Path, rel: str) -> str:
    path = root / rel
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def require_terms(root: Path, rel: str, terms: list[str]) -> tuple[bool, list[str]]:
    text = read_text(root, rel)
    if not text:
        return False, [f"missing file {rel}"]
    missing = [term for term in terms if term not in text]
    return not missing, missing


def build_check(root: Path, check_id: str, summary: str, terms_by_rel: dict[str, list[str]]) -> dict[str, Any]:
    problems: list[str] = []
    for rel, terms in terms_by_rel.items():
        ok, missing = require_terms(root, rel, terms)
        if not ok:
            problems.extend(f"{rel} missing {item}" for item in missing)
    return {
        "id": check_id,
        "ok": not problems,
        "summary": summary,
        "evidence": sorted(terms_by_rel),
        "problems": problems,
    }


def audit_evidence_contract(root: Path) -> dict[str, Any]:
    checks = [
        build_check(root, "evidence-record-reproducibility", "EvidenceRecord captures enough material to reproduce or falsify a claim", {
            "skills/ctf-master/references/state-schema.md": [
                "EvidenceRecord",
                "purpose",
                "inputs",
                "raw_artifact",
                "exit_status",
                "supports",
                "contradicts",
                "risk",
            ],
        }),
        build_check(root, "handoff-evidence-table", "Handoff keeps raw artifact paths, support/contradiction links, and safety notes visible", {
            "skills/ctf-handoff-report/references/handoff-template.md": [
                "Evidence Table",
                "Raw Artifact",
                "Supports/Contradicts",
                "Safety Notes",
            ],
            "skills/ctf-handoff-report/scripts/render_handoff.py": [
                "state.get(\"evidence\"",
                "state.get(\"artifacts\"",
                "state.get(\"dead_ends\"",
            ],
        }),
        build_check(root, "writeup-verification-contract", "Writeups require reproducible commands, evidence references, contrast checks, and verification outcome", {
            "skills/ctf-handoff-report/references/writeup-template.md": [
                "Evidence References",
                "Contrast Checks",
                "Commands and Scripts",
                "Verification",
                "Failed Paths",
            ],
            "skills/ctf-handoff-report/scripts/render_writeup.py": [
                "Evidence References",
                "Raw Artifacts",
                "Verification",
                "known_facts",
                "dead_ends",
                "FLAG_RE",
            ],
        }),
        build_check(root, "reference-source-evidence-discipline", "Requested references are converted into evidence-first CTF behavior, not copied payload catalogs", {
            "research/seed-source-matrix.md": [
                "reproducible evidence",
                "contrast checks",
                "verdict consumes evidence only",
                "do-not-copy payload catalogs",
            ],
            "REFLECTION_AUDIT.md": [
                "evidence contract",
                "reproducible evidence",
                "verdict-style separation",
            ],
        }),
        build_check(root, "release-surface-evidence-audit", "Evidence contract audit is part of the release, quality, and traceability surface", {
            "suite-manifest.json": ["evidence_contract_audit", "0.38.0"],
            "scripts/validate_suite.py": ["audit_evidence_contract.py", "ctf-evidence-contract-audit-v1"],
            "scripts/release_gate.py": ["audit_evidence_contract.py"],
            "scripts/audit_quality.py": ["evidence-contract-audit", "audit_evidence_contract.py"],
            "research/requirements-traceability.json": ["REQ-EVIDENCE-CONTRACT-032", "audit_evidence_contract.py"],
            "research/requirements-traceability.md": ["REQ-EVIDENCE-CONTRACT-032", "audit_evidence_contract.py"],
        }),
    ]
    failing = [item for item in checks if not item["ok"]]
    return {
        "schema": "ctf-evidence-contract-audit-v1",
        "root": str(root),
        "ok": not failing,
        "check_count": len(checks),
        "failing_count": len(failing),
        "failing_ids": [item["id"] for item in failing],
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit reproducible evidence contracts for the CTF Agent suite")
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    result = audit_evidence_contract(Path(args.root))
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"evidence_contract_audit_ok={result['ok']}")
        for item in result["checks"]:
            status = "ok" if item["ok"] else "fail"
            print(f"{status}: {item['id']} - {item['summary']}")
            for problem in item["problems"]:
                print(f"  - {problem}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
