#!/usr/bin/env python3
"""Audit requirements traceability evidence for the CTF Agent skill suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_MATRIX = Path("research/requirements-traceability.json")


def load_matrix(root: Path, matrix_path: str | None) -> dict[str, Any]:
    path = Path(matrix_path) if matrix_path else root / DEFAULT_MATRIX
    if not path.is_absolute():
        path = root / path
    return json.loads(path.read_text(encoding="utf-8"))


def check_contains(text: str, needles: list[str]) -> list[str]:
    lowered = text.lower()
    return [needle for needle in needles if needle.lower() not in lowered]


def audit_requirement(root: Path, req: dict[str, Any]) -> dict[str, Any]:
    evidence_results = []
    missing_paths = []
    missing_terms = []
    for evidence in req.get("evidence", []):
        rel = evidence.get("path", "")
        path = root / rel
        item = {"path": rel, "exists": path.exists(), "missing_terms": []}
        if not path.exists():
            missing_paths.append(rel)
        else:
            text = path.read_text(encoding="utf-8", errors="replace")
            item["missing_terms"] = check_contains(text, evidence.get("contains", []))
            for term in item["missing_terms"]:
                missing_terms.append({"path": rel, "term": term})
        evidence_results.append(item)

    status = req.get("status", "")
    priority = req.get("priority", "")
    problems = []
    if not req.get("id") or not req.get("requirement"):
        problems.append("missing id or requirement")
    if status == "covered" and (missing_paths or missing_terms):
        problems.append("covered requirement has missing evidence")
    if priority == "current_gate" and status != "covered":
        problems.append("current_gate requirement is not covered")
    if priority == "current_gate" and not req.get("evidence"):
        problems.append("current_gate requirement has no evidence")

    return {
        "id": req.get("id", ""),
        "priority": priority,
        "status": status,
        "source": req.get("source", ""),
        "problems": problems,
        "missing_paths": missing_paths,
        "missing_terms": missing_terms,
        "evidence": evidence_results,
        "notes": req.get("notes", ""),
    }


def render_markdown(results: list[dict[str, Any]]) -> str:
    lines = ["# Traceability Audit", ""]
    failing = [item for item in results if item["problems"]]
    partial = [item for item in results if item["status"] != "covered" and not item["problems"]]
    lines.append(f"- Requirements checked: {len(results)}")
    lines.append(f"- Failing current gates: {len(failing)}")
    lines.append(f"- Non-failing partial/open targets: {len(partial)}")
    lines.append("")
    lines.append("| ID | Priority | Status | Result | Notes |")
    lines.append("|---|---|---|---|---|")
    for item in results:
        result = "fail" if item["problems"] else "ok"
        notes = "; ".join(item["problems"]) or item["notes"]
        lines.append(f"| `{item['id']}` | {item['priority']} | {item['status']} | {result} | {notes} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit requirements traceability evidence")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--matrix", help="Traceability JSON path, relative to root unless absolute")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    root = Path(args.root)
    matrix = load_matrix(root, args.matrix)
    requirements = matrix.get("requirements", [])
    results = [audit_requirement(root, req) for req in requirements]
    failing = [item for item in results if item["problems"]]
    partial_or_open = [item for item in results if item["status"] != "covered"]

    output = {
        "schema": "ctf-agent-skills-traceability-audit-v1",
        "matrix_schema": matrix.get("schema"),
        "requirements_checked": len(results),
        "failing_count": len(failing),
        "partial_or_open_count": len(partial_or_open),
        "failing_ids": [item["id"] for item in failing],
        "partial_or_open_ids": [item["id"] for item in partial_or_open],
        "results": results,
    }
    if args.as_json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(results), end="")
    return 1 if failing else 0


if __name__ == "__main__":
    raise SystemExit(main())
