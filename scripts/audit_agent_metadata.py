#!/usr/bin/env python3
"""Audit agents/openai.yaml metadata for every CTF skill."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RE_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)
RE_SIMPLE_KV = re.compile(r"^(\s*)([A-Za-z0-9_-]+):(?:\s+(.+))?$")
RESIDUE_TERMS = ("to" + "do", "place" + "holder", "option" + "al")


def parse_frontmatter(text: str) -> dict[str, str]:
    match = RE_FRONTMATTER.match(text)
    if not match:
        raise ValueError("missing YAML frontmatter")
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def strip_value(value: str | None) -> Any:
    if value is None:
        return {}
    value = value.strip()
    if not value:
        return {}
    if value[0] == value[-1] == '"':
        return value[1:-1]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return value


def parse_simple_yaml(path: Path) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = RE_SIMPLE_KV.match(line)
        if not match:
            raise ValueError(f"unsupported YAML at line {lineno}: {line}")
        indent = len(match.group(1))
        key = match.group(2)
        raw_value = match.group(3)
        value = strip_value(raw_value)
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        parent[key] = value
        if isinstance(value, dict):
            stack.append((indent, value))
    return root


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9][a-z0-9-]{2,}", text.lower()))


def audit_skill(skill_dir: Path, root: Path) -> dict[str, Any]:
    skill_md = skill_dir / "SKILL.md"
    meta_path = skill_dir / "agents" / "openai.yaml"
    problems: list[str] = []
    warnings: list[str] = []
    evidence: list[str] = []
    try:
        fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "skill": skill_dir.name,
            "ok": False,
            "problems": [f"SKILL.md frontmatter parse failed: {exc}"],
            "warnings": warnings,
            "evidence": evidence,
        }
    skill_name = fm.get("name", skill_dir.name)
    description = fm.get("description", "")
    if not meta_path.exists():
        problems.append("missing agents/openai.yaml")
        return {
            "skill": skill_name,
            "ok": False,
            "problems": problems,
            "warnings": warnings,
            "evidence": evidence,
        }
    try:
        meta = parse_simple_yaml(meta_path)
    except Exception as exc:
        problems.append(f"openai.yaml parse failed: {exc}")
        meta = {}
    interface = meta.get("interface", {})
    if not isinstance(interface, dict):
        problems.append("interface must be a mapping")
        interface = {}
    display_name = str(interface.get("display_name", "")).strip()
    short_description = str(interface.get("short_description", "")).strip()
    default_prompt = str(interface.get("default_prompt", "")).strip()
    for field, value in [
        ("display_name", display_name),
        ("short_description", short_description),
        ("default_prompt", default_prompt),
    ]:
        if not value:
            problems.append(f"interface.{field} is required")
    if short_description and not (25 <= len(short_description) <= 64):
        problems.append("interface.short_description must be 25-64 characters")
    if default_prompt and f"${skill_name}" not in default_prompt:
        problems.append(f"interface.default_prompt must mention ${skill_name}")
    if any(value in short_description.lower() for value in RESIDUE_TERMS):
        problems.append("interface.short_description contains template residue")
    if any(value in default_prompt.lower() for value in RESIDUE_TERMS):
        problems.append("interface.default_prompt contains template residue")

    desc_words = words(description)
    meta_words = words(f"{display_name} {short_description} {default_prompt}")
    overlap = sorted(desc_words & meta_words)
    if len(overlap) < 2:
        warnings.append("metadata has weak lexical overlap with SKILL.md description")
    evidence.extend([
        f"metadata={meta_path.relative_to(root)}",
        f"default_prompt_mentions=${skill_name}:{f'${skill_name}' in default_prompt}",
        f"description_overlap={','.join(overlap[:8])}",
    ])
    return {
        "skill": skill_name,
        "ok": not problems,
        "problems": problems,
        "warnings": warnings,
        "evidence": evidence,
        "display_name": display_name,
        "short_description": short_description,
    }


def audit_agent_metadata(root: Path) -> dict[str, Any]:
    results = [audit_skill(path, root) for path in sorted((root / "skills").glob("ctf-*"))]
    failing = [item for item in results if not item["ok"]]
    return {
        "schema": "ctf-agent-metadata-audit-v1",
        "root": str(root),
        "ok": not failing,
        "skill_count": len(results),
        "failing_count": len(failing),
        "failing_ids": [item["skill"] for item in failing],
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit agents/openai.yaml metadata")
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    result = audit_agent_metadata(Path(args.root))
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"agent_metadata_audit_ok={result['ok']}")
        for item in result["results"]:
            status = "ok" if item["ok"] else "fail"
            print(f"{status}: {item['skill']}")
            for problem in item["problems"]:
                print(f"  problem: {problem}")
            for warning in item["warnings"]:
                print(f"  warn: {warning}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
