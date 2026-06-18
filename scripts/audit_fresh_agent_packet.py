#!/usr/bin/env python3
"""Audit an exported fresh-agent packet without reading the source workspace."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from audit_fresh_agent_readiness import FORBIDDEN_LEAK_TERMS, leak_terms, sha256_file


REQUIRED_TOP_LEVEL_FILES = {
    "FRESH_AGENT_HANDOFF.md",
    "RESPONSE_RULES.md",
    "PACKET_MANIFEST.json",
}
FORBIDDEN_FILE_NAMES = {
    "fresh-agent-run-record.json",
    "rubric-template.json",
    "score-summary.json",
    "forward-run-workspace.json",
    "expected-behavior.md",
    "RUNBOOK.md",
}
REQUIRED_EXCLUDED_MATERIALS = {
    "scenario JSON",
    "expected-behavior.md",
    "score output",
    "rubric files",
    "run records",
    "workspace manifests",
    "prior analysis",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def relative_files(packet_dir: Path) -> list[str]:
    return sorted(path.relative_to(packet_dir).as_posix() for path in packet_dir.rglob("*") if path.is_file())


def allowed_packet_file(rel_path: str) -> bool:
    if rel_path in REQUIRED_TOP_LEVEL_FILES:
        return True
    return rel_path.startswith("prompts/") and rel_path.endswith(".prompt.txt") and "/" not in rel_path.removeprefix("prompts/")


def audit_packet(packet_dir: Path) -> dict[str, Any]:
    packet_dir = packet_dir.resolve()
    problems: list[str] = []
    if not packet_dir.exists():
        return {
            "schema": "ctf-fresh-agent-packet-audit-v1",
            "ok": False,
            "packet_dir": str(packet_dir),
            "prompt_count": 0,
            "problems": [f"packet directory does not exist: {packet_dir}"],
        }
    if not packet_dir.is_dir():
        return {
            "schema": "ctf-fresh-agent-packet-audit-v1",
            "ok": False,
            "packet_dir": str(packet_dir),
            "prompt_count": 0,
            "problems": [f"packet path is not a directory: {packet_dir}"],
        }

    files = relative_files(packet_dir)
    file_set = set(files)
    missing_top = sorted(REQUIRED_TOP_LEVEL_FILES - file_set)
    for name in missing_top:
        problems.append(f"missing required packet file: {name}")
    for rel_path in files:
        name = Path(rel_path).name
        if name in FORBIDDEN_FILE_NAMES:
            problems.append(f"forbidden file in packet: {rel_path}")
        if rel_path.endswith(".json") and rel_path != "PACKET_MANIFEST.json":
            problems.append(f"unexpected JSON file in packet: {rel_path}")
        if not allowed_packet_file(rel_path):
            problems.append(f"unexpected packet file: {rel_path}")

    manifest_path = packet_dir / "PACKET_MANIFEST.json"
    manifest: dict[str, Any] = {}
    if manifest_path.exists() and manifest_path.is_file():
        manifest = load_json(manifest_path)
        if manifest.get("schema") != "ctf-fresh-agent-packet-v1":
            problems.append("PACKET_MANIFEST.json schema is not ctf-fresh-agent-packet-v1")
        for field in ["run_id", "suite_version", "allowed_skill_root", "handoff", "response_rules", "prompt_count", "prompts", "excluded_materials"]:
            if field not in manifest:
                problems.append(f"PACKET_MANIFEST.json missing {field}")
        excluded = set(manifest.get("excluded_materials", []))
        missing_excluded = sorted(REQUIRED_EXCLUDED_MATERIALS - excluded)
        for item in missing_excluded:
            problems.append(f"PACKET_MANIFEST.json excluded_materials missing {item}")
        skill_root = Path(str(manifest.get("allowed_skill_root", "")))
        if not str(skill_root):
            problems.append("PACKET_MANIFEST.json allowed_skill_root is empty")
        elif not skill_root.exists():
            problems.append(f"allowed_skill_root does not exist: {skill_root}")
        elif not (skill_root / "skills").exists():
            problems.append(f"allowed_skill_root has no skills directory: {skill_root}")
    prompt_entries = manifest.get("prompts", []) if isinstance(manifest.get("prompts", []), list) else []
    manifest_prompt_paths = {str(item.get("path", "")) for item in prompt_entries}
    actual_prompt_paths = {item for item in files if item.startswith("prompts/") and item.endswith(".prompt.txt")}
    if manifest and manifest.get("prompt_count") != len(prompt_entries):
        problems.append("PACKET_MANIFEST.json prompt_count does not match prompts list")
    if manifest_prompt_paths != actual_prompt_paths:
        problems.append(f"prompt file set mismatch manifest={sorted(manifest_prompt_paths)} actual={sorted(actual_prompt_paths)}")
    seen_ids: set[str] = set()
    for item in prompt_entries:
        scenario_id = str(item.get("scenario_id", ""))
        rel_path = str(item.get("path", ""))
        digest = str(item.get("sha256", ""))
        if not scenario_id:
            problems.append("prompt entry missing scenario_id")
        elif scenario_id in seen_ids:
            problems.append(f"duplicate scenario_id in packet manifest: {scenario_id}")
        seen_ids.add(scenario_id)
        prompt_path = packet_dir / rel_path
        if not prompt_path.exists():
            problems.append(f"manifest prompt path does not exist: {rel_path}")
            continue
        if digest != sha256_file(prompt_path):
            problems.append(f"prompt sha256 mismatch: {rel_path}")

    handoff_path = packet_dir / "FRESH_AGENT_HANDOFF.md"
    if handoff_path.exists():
        handoff_text = handoff_path.read_text(encoding="utf-8", errors="replace")
        for term in ["Fresh-Agent Handoff", "Response Rules", "Prompt Files", "Do not open scenario JSON", "sha256"]:
            if term not in handoff_text:
                problems.append(f"handoff missing required term: {term}")
        for item in prompt_entries:
            for field in ["scenario_id", "path", "sha256"]:
                value = str(item.get(field, ""))
                if value and value not in handoff_text:
                    problems.append(f"handoff missing prompt {field}: {value}")
    rules_path = packet_dir / "RESPONSE_RULES.md"
    if rules_path.exists():
        rules_text = rules_path.read_text(encoding="utf-8", errors="replace")
        for term in ["Fresh-Agent Packet Response Rules", "Do Not Open", "<scenario-id>.md", "Skill Use"]:
            if term not in rules_text:
                problems.append(f"response rules missing required term: {term}")

    for rel_path in files:
        path = packet_dir / rel_path
        if path.suffix.lower() not in {".md", ".txt", ".json"}:
            continue
        leaked = leak_terms(path.read_text(encoding="utf-8", errors="replace"))
        if leaked:
            problems.append(f"packet file leaks forbidden terms: {rel_path} -> {', '.join(leaked)}")

    return {
        "schema": "ctf-fresh-agent-packet-audit-v1",
        "ok": not problems,
        "packet_dir": str(packet_dir),
        "prompt_count": len(actual_prompt_paths),
        "file_count": len(files),
        "forbidden_leak_terms": sorted(FORBIDDEN_LEAK_TERMS),
        "files": files,
        "problems": problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit an exported fresh-agent packet")
    parser.add_argument("packet_dir")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    result = audit_packet(Path(args.packet_dir))
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"fresh_agent_packet_audit_ok={result['ok']} prompts={result['prompt_count']} files={result.get('file_count', 0)}")
        for problem in result["problems"]:
            print(f"- {problem}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
