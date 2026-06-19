#!/usr/bin/env python3
"""Audit the source matrix that justifies CTF skill-suite design choices."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = Path("research/seed-source-matrix.md")
REQUIRED_COLUMNS = [
    "Source",
    "Type",
    "Topic",
    "Relevance",
    "Source Anchor",
    "Observed Signals",
    "Last Reviewed",
    "Borrowed Design",
    "Do Not Blindly Copy",
    "Skill Conversion",
]
REQUIRED_SOURCES = {
    "src-hunter-skill": {
        "terms": [
            "checkpoint",
            "scope gate",
            "evidence",
            "playbook",
            "mcp",
            "ctf-master",
            "gate_state.py",
        ],
        "conversion_terms": ["ctf-master", "gate_state.py", "ctf-knowledge", "ctf-handoff-report"],
    },
    "yaklang/hack-skills": {
        "terms": [
            "master",
            "category",
            "deep topic",
            "distillation",
            "on-demand",
            "route_topic.py",
        ],
        "conversion_terms": ["route_topic.py", "deep-topic-router.md", "category skill", "ctf-specialty"],
    },
    "red_team_skill": {
        "terms": [
            "runner/tricks/bypass/verdict",
            "hard gates",
            "tool enablement",
            "structured evidence",
            "context protection",
            "ctfrunstate",
        ],
        "conversion_terms": ["ctf-tool-preflight", "ctfrunstate", "evidencerecord", "toolcards"],
    },
}
BROADER_REQUIRED_SIGNALS = [
    "cybench",
    "nyu ctf bench",
    "model context protocol",
    "owasp",
    "ctf wiki",
]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def split_row(line: str) -> list[str]:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return [re.sub(r"\s+", " ", cell) for cell in cells]


def parse_markdown_table(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    header: list[str] | None = None
    for line in lines:
        if not line.startswith("|"):
            if header and rows:
                break
            continue
        cells = split_row(line)
        if not cells:
            continue
        if cells == REQUIRED_COLUMNS:
            header = cells
            continue
        if header and set(cells) <= {"---", ":---", "---:", ":---:"}:
            continue
        if header:
            if len(cells) != len(header):
                raise ValueError(f"table row has {len(cells)} cells, expected {len(header)}: {line}")
            rows.append(dict(zip(header, cells)))
    if not header:
        raise ValueError("source matrix table header not found")
    return rows


def row_text(row: dict[str, str]) -> str:
    return " ".join(row.values()).lower()


def contains_all(text: str, terms: list[str]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term.lower() not in lowered]


def audit_rows(rows: list[dict[str, str]]) -> dict[str, Any]:
    problems: list[str] = []
    provenance_problems: list[str] = []
    source_results: list[dict[str, Any]] = []
    if len(rows) < 8:
        problems.append(f"expected at least 8 source rows, found {len(rows)}")

    for index, row in enumerate(rows, start=1):
        for column in REQUIRED_COLUMNS:
            value = row.get(column, "").strip()
            if not value:
                problems.append(f"row {index} has empty {column}")
        if len(row.get("Borrowed Design", "")) < 12:
            problems.append(f"row {index} borrowed design is too thin")
        if len(row.get("Do Not Blindly Copy", "")) < 12:
            problems.append(f"row {index} do-not-copy boundary is too thin")
        if len(row.get("Skill Conversion", "")) < 12:
            problems.append(f"row {index} skill conversion is too thin")
        anchor = row.get("Source Anchor", "")
        if not (anchor.startswith("https://") or anchor.startswith("http://") or anchor.startswith("/")):
            provenance_problems.append(f"row {index} source anchor must be an absolute URL or local absolute path")
        if len(row.get("Observed Signals", "")) < 20:
            provenance_problems.append(f"row {index} observed signals are too thin")
        reviewed = row.get("Last Reviewed", "")
        if not DATE_RE.match(reviewed):
            provenance_problems.append(f"row {index} last reviewed must use YYYY-MM-DD")

    for source_key, spec in REQUIRED_SOURCES.items():
        row = next((item for item in rows if source_key.lower() in item.get("Source", "").lower()), None)
        if not row:
            source_results.append({
                "source": source_key,
                "ok": False,
                "missing_terms": ["row"],
                "missing_conversion_terms": [],
            })
            problems.append(f"missing required source row: {source_key}")
            continue
        missing_terms = contains_all(row_text(row), spec["terms"])
        missing_conversion = contains_all(row.get("Skill Conversion", ""), spec["conversion_terms"])
        ok = not missing_terms and not missing_conversion
        source_results.append({
            "source": source_key,
            "ok": ok,
            "missing_terms": missing_terms,
            "missing_conversion_terms": missing_conversion,
            "source_anchor": row.get("Source Anchor", ""),
            "last_reviewed": row.get("Last Reviewed", ""),
            "conversion": row.get("Skill Conversion", ""),
        })
        for term in missing_terms:
            problems.append(f"{source_key} missing absorption term: {term}")
        for term in missing_conversion:
            problems.append(f"{source_key} missing conversion term: {term}")

    all_text = " ".join(row_text(row) for row in rows)
    broader_missing = contains_all(all_text, BROADER_REQUIRED_SIGNALS)
    for term in broader_missing:
        problems.append(f"matrix missing broader research signal: {term}")
    problems.extend(provenance_problems)

    return {
        "schema": "ctf-source-matrix-audit-v1",
        "ok": not problems,
        "source_count": len(rows),
        "required_source_count": len(REQUIRED_SOURCES),
        "missing_provenance_count": len(provenance_problems),
        "failing_source_ids": [item["source"] for item in source_results if not item["ok"]],
        "broader_missing": broader_missing,
        "provenance_problems": provenance_problems,
        "problems": problems,
        "required_sources": source_results,
    }


def audit_source_matrix(root: Path, matrix_path: str | None) -> dict[str, Any]:
    path = Path(matrix_path) if matrix_path else root / DEFAULT_MATRIX
    if not path.is_absolute():
        path = root / path
    rows = parse_markdown_table(path)
    result = audit_rows(rows)
    result["matrix"] = str(path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit reference-source absorption matrix")
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--matrix", help="Source matrix markdown path, relative to root unless absolute")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    try:
        result = audit_source_matrix(Path(args.root), args.matrix)
    except Exception as exc:
        result = {
            "schema": "ctf-source-matrix-audit-v1",
            "ok": False,
            "source_count": 0,
            "required_source_count": len(REQUIRED_SOURCES),
            "failing_source_ids": sorted(REQUIRED_SOURCES),
            "broader_missing": BROADER_REQUIRED_SIGNALS,
            "problems": [str(exc)],
            "required_sources": [],
        }
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"source_matrix_audit_ok={result['ok']}")
        for problem in result["problems"]:
            print(f"problem: {problem}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
