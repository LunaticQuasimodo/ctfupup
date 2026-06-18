#!/usr/bin/env python3
"""Audit forward-test prompts and records for evaluation contamination risk."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from run_forward_suite import DEFAULT_SCENARIOS, load_scenarios, write_prompt_pack


ROOT = Path(__file__).resolve().parents[1]
FORWARD_ROOT = ROOT / "forward-tests"
SENSITIVE_SCENARIO_FIELDS = {
    "expected_skills",
    "must_include",
    "must_not_include",
    "rubric_minimum",
}
REQUIRED_TEMPLATE_FIELDS = {
    "fresh_context_confirmed": False,
    "fork_context": False,
    "expected_answers_disclosed": False,
    "pass_fail": "not_run",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_prompt_pack(scenarios: list[dict[str, Any]], prompt_pack_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    problems: list[str] = []
    checks: list[dict[str, Any]] = []
    index_path = prompt_pack_dir / "index.json"
    instructions_path = prompt_pack_dir / "RUN_INSTRUCTIONS.md"
    if not index_path.exists():
        problems.append(f"prompt pack missing index.json: {prompt_pack_dir}")
        index = []
    else:
        index = read_json(index_path)
    if not instructions_path.exists():
        problems.append(f"prompt pack missing RUN_INSTRUCTIONS.md: {prompt_pack_dir}")
    else:
        instructions = instructions_path.read_text(encoding="utf-8", errors="replace").lower()
        for field in SENSITIVE_SCENARIO_FIELDS:
            if field in instructions:
                problems.append(f"RUN_INSTRUCTIONS.md leaks scenario field name: {field}")

    index_by_id = {item.get("id"): item for item in index if isinstance(item, dict)}
    for scenario in scenarios:
        scenario_id = scenario.get("id", "")
        prompt = scenario.get("prompt", "").rstrip() + "\n"
        index_item = index_by_id.get(scenario_id)
        prompt_path = prompt_pack_dir / f"{scenario_id}.prompt.txt"
        item_problems: list[str] = []
        if not index_item:
            item_problems.append("missing index entry")
        else:
            if index_item.get("do_not_include_expected_answers") is not True:
                item_problems.append("index does not mark answer-free prompt")
            for field in SENSITIVE_SCENARIO_FIELDS:
                if field in index_item:
                    item_problems.append(f"index leaks {field}")
        if not prompt_path.exists():
            item_problems.append("missing prompt file")
        else:
            prompt_text = prompt_path.read_text(encoding="utf-8", errors="replace")
            if prompt_text != prompt:
                item_problems.append("prompt file differs from scenario prompt")
            for field in SENSITIVE_SCENARIO_FIELDS:
                if field in prompt_text:
                    item_problems.append(f"prompt leaks field name {field}")
            for skill in scenario.get("expected_skills", []):
                if skill not in scenario.get("prompt", "") and skill in prompt_text:
                    item_problems.append(f"prompt leaks expected skill {skill}")
        if item_problems:
            problems.extend(f"{scenario_id}: {problem}" for problem in item_problems)
        checks.append({
            "scenario_id": scenario_id,
            "prompt_file": str(prompt_path),
            "ok": not item_problems,
            "problems": item_problems,
        })
    return checks, problems


def audit_record_template(root: Path) -> tuple[dict[str, Any], list[str]]:
    path = root / "forward-tests" / "fresh-agent-run-record-template.json"
    problems: list[str] = []
    if not path.exists():
        return {"path": str(path), "ok": False}, [f"missing run record template: {path}"]
    data = read_json(path)
    for key, expected in REQUIRED_TEMPLATE_FIELDS.items():
        if data.get(key) != expected:
            problems.append(f"fresh-agent-run-record-template.json {key} must be {expected!r}")
    rubric = data.get("human_rubric", {})
    if rubric.get("completed") is not False:
        problems.append("fresh-agent-run-record-template.json human_rubric.completed must start false")
    return {"path": str(path), "ok": not problems}, problems


def audit_forward_integrity(root: Path, scenarios_dir: Path, prompt_pack_dir: Path | None) -> dict[str, Any]:
    scenarios = load_scenarios(scenarios_dir)
    problems: list[str] = []
    if len(scenarios) < 5:
        problems.append(f"expected at least 5 forward scenarios, found {len(scenarios)}")
    for scenario in scenarios:
        for field in ["id", "title", "prompt", "expected_skills", "must_include", "must_not_include", "rubric_minimum"]:
            if field not in scenario:
                problems.append(f"{scenario.get('id', '<missing-id>')}: missing {field}")

    created_temp = None
    if prompt_pack_dir is None:
        created_temp = tempfile.TemporaryDirectory(prefix="ctf-forward-integrity-")
        prompt_pack_dir = Path(created_temp.name)
        write_prompt_pack(scenarios, prompt_pack_dir)

    prompt_checks, prompt_problems = audit_prompt_pack(scenarios, prompt_pack_dir)
    problems.extend(prompt_problems)
    template_check, template_problems = audit_record_template(root)
    problems.extend(template_problems)

    if created_temp is not None:
        created_temp.cleanup()

    return {
        "schema": "ctf-forward-integrity-audit-v1",
        "root": str(root),
        "scenarios_dir": str(scenarios_dir),
        "prompt_pack_dir": str(prompt_pack_dir),
        "ok": not problems,
        "scenario_count": len(scenarios),
        "prompt_check_count": len(prompt_checks),
        "failing_prompt_ids": [item["scenario_id"] for item in prompt_checks if not item["ok"]],
        "problems": problems,
        "prompt_checks": prompt_checks,
        "run_record_template": template_check,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit forward-test integrity")
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--scenarios-dir", default=DEFAULT_SCENARIOS)
    parser.add_argument("--prompt-pack-dir")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    root = Path(args.root)
    scenarios_dir = Path(args.scenarios_dir)
    if not scenarios_dir.is_absolute():
        scenarios_dir = root / scenarios_dir
    prompt_pack_dir = Path(args.prompt_pack_dir) if args.prompt_pack_dir else None
    result = audit_forward_integrity(root, scenarios_dir, prompt_pack_dir)
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"forward_integrity_audit_ok={result['ok']}")
        for problem in result["problems"]:
            print(f"problem: {problem}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
