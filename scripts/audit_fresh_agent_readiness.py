#!/usr/bin/env python3
"""Audit whether a forward-test workspace is ready for a fresh agent."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FORBIDDEN_LEAK_TERMS = {
    "expected_skills",
    "must_include",
    "must_not_include",
    "rubric_minimum",
    "expected_answers",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def as_path(value: str, base: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def check_exists(problems: list[str], label: str, path: Path, *, directory: bool | None = None) -> bool:
    if not path.exists():
        problems.append(f"{label} does not exist: {path}")
        return False
    if directory is True and not path.is_dir():
        problems.append(f"{label} is not a directory: {path}")
        return False
    if directory is False and not path.is_file():
        problems.append(f"{label} is not a file: {path}")
        return False
    return True


def leak_terms(text: str) -> list[str]:
    lowered = text.lower()
    return sorted(term for term in FORBIDDEN_LEAK_TERMS if term.lower() in lowered)


def audit_prompt_hashes(workspace: dict[str, Any], manifest_dir: Path, problems: list[str]) -> list[dict[str, Any]]:
    prompt_pack_dir = as_path(str(workspace.get("prompt_pack_dir", "")), manifest_dir)
    prompt_checks: list[dict[str, Any]] = []
    prompt_hashes = workspace.get("prompt_hashes", [])
    if not isinstance(prompt_hashes, list) or not prompt_hashes:
        problems.append("workspace prompt_hashes is empty or not a list")
        return prompt_checks
    seen_ids: set[str] = set()
    for item in prompt_hashes:
        scenario_id = str(item.get("scenario_id", ""))
        path_value = str(item.get("path", ""))
        digest = str(item.get("sha256", ""))
        item_problems: list[str] = []
        if not scenario_id:
            item_problems.append("missing scenario_id")
        elif scenario_id in seen_ids:
            item_problems.append(f"duplicate scenario_id {scenario_id}")
        seen_ids.add(scenario_id)
        prompt_path = as_path(path_value, manifest_dir) if path_value else Path("")
        if not path_value:
            item_problems.append("missing prompt path")
        elif not check_exists(item_problems, "prompt file", prompt_path, directory=False):
            pass
        else:
            try:
                prompt_path.resolve().relative_to(prompt_pack_dir.resolve())
            except ValueError:
                item_problems.append(f"prompt file is outside prompt_pack_dir: {prompt_path}")
            actual_digest = sha256_file(prompt_path)
            if digest != actual_digest:
                item_problems.append(f"prompt sha256 mismatch: {prompt_path}")
            text = prompt_path.read_text(encoding="utf-8", errors="replace")
            leaked = leak_terms(text)
            if leaked:
                item_problems.append(f"prompt leaks forbidden terms: {', '.join(leaked)}")
        if not digest or len(digest) != 64:
            item_problems.append("sha256 is missing or malformed")
        prompt_checks.append({
            "scenario_id": scenario_id,
            "path": str(prompt_path) if path_value else "",
            "ok": not item_problems,
            "problems": item_problems,
        })
        problems.extend(f"{scenario_id or '<missing-id>'}: {problem}" for problem in item_problems)
    return prompt_checks


def audit_record(record_path: Path, workspace: dict[str, Any], problems: list[str]) -> dict[str, Any]:
    if not check_exists(problems, "fresh-agent run record", record_path, directory=False):
        return {"ok": False, "path": str(record_path)}
    record = load_json(record_path)
    record_problems: list[str] = []
    expected_pairs = {
        "schema": "ctf-forward-run-record-v1",
        "run_id": workspace.get("run_id"),
        "suite_version": workspace.get("suite_version"),
        "fresh_context_confirmed": False,
        "fork_context": False,
        "expected_answers_disclosed": False,
        "pass_fail": "not_run",
    }
    for key, expected in expected_pairs.items():
        if record.get(key) != expected:
            record_problems.append(f"{key} must start as {expected!r}")
    for key in ["prompt_pack_dir", "response_dir", "score_summary_path", "workspace_manifest_path", "rubric_template_path", "fresh_agent_handoff_path"]:
        if not record.get(key):
            record_problems.append(f"missing {key}")
    rubric = record.get("human_rubric", {})
    if rubric.get("completed") is not False:
        record_problems.append("human_rubric.completed must start false")
    if record.get("response_hashes"):
        record_problems.append("response_hashes must be empty before the fresh-agent run")
    problems.extend(f"run record: {problem}" for problem in record_problems)
    return {"ok": not record_problems, "path": str(record_path), "problems": record_problems}


def audit_rubric(rubric_path: Path, workspace: dict[str, Any], problems: list[str]) -> dict[str, Any]:
    if not check_exists(problems, "rubric template", rubric_path, directory=False):
        return {"ok": False, "path": str(rubric_path)}
    rubric = load_json(rubric_path)
    rubric_problems: list[str] = []
    if rubric.get("schema") != "ctf-forward-human-rubric-v1":
        rubric_problems.append("schema is not ctf-forward-human-rubric-v1")
    if rubric.get("completed") is not False:
        rubric_problems.append("completed must start false")
    if rubric.get("run_id") != workspace.get("run_id"):
        rubric_problems.append("run_id does not match workspace")
    scores = rubric.get("scenario_scores", [])
    if len(scores) != workspace.get("scenario_count"):
        rubric_problems.append("scenario_scores count does not match workspace scenario_count")
    problems.extend(f"rubric template: {problem}" for problem in rubric_problems)
    return {"ok": not rubric_problems, "path": str(rubric_path), "problems": rubric_problems}


def audit_handoff(handoff_path: Path, workspace: dict[str, Any], problems: list[str]) -> dict[str, Any]:
    if not check_exists(problems, "fresh-agent handoff", handoff_path, directory=False):
        return {"ok": False, "path": str(handoff_path)}
    text = handoff_path.read_text(encoding="utf-8", errors="replace")
    handoff_problems: list[str] = []
    required_terms = [
        "Fresh-Agent Handoff",
        "Response Rules",
        "Prompt Files",
        "Do not open scenario JSON",
        "sha256",
    ]
    for term in required_terms:
        if term not in text:
            handoff_problems.append(f"missing required term {term!r}")
    leaked = leak_terms(text)
    if leaked:
        handoff_problems.append(f"handoff leaks forbidden terms: {', '.join(leaked)}")
    for item in workspace.get("prompt_hashes", []):
        for key in ["scenario_id", "path", "sha256"]:
            value = str(item.get(key, ""))
            if value and value not in text:
                handoff_problems.append(f"handoff missing prompt {key}: {value}")
    problems.extend(f"fresh-agent handoff: {problem}" for problem in handoff_problems)
    return {"ok": not handoff_problems, "path": str(handoff_path), "problems": handoff_problems}


def audit_workspace(workspace_manifest: Path) -> dict[str, Any]:
    workspace_manifest = workspace_manifest.resolve()
    manifest_dir = workspace_manifest.parent
    problems: list[str] = []
    if not check_exists(problems, "workspace manifest", workspace_manifest, directory=False):
        return {
            "schema": "ctf-fresh-agent-readiness-audit-v1",
            "ok": False,
            "ready_for_fresh_agent": False,
            "workspace_manifest": str(workspace_manifest),
            "problems": problems,
        }

    workspace = load_json(workspace_manifest)
    if workspace.get("schema") != "ctf-forward-run-workspace-v1":
        problems.append("workspace schema is not ctf-forward-run-workspace-v1")
    if workspace.get("integrity_audit_ok") is not True:
        problems.append("workspace integrity_audit_ok is not true")
    if workspace.get("scenario_count", 0) < 5:
        problems.append("workspace scenario_count is too low")

    prompt_pack_dir = as_path(str(workspace.get("prompt_pack_dir", "")), manifest_dir)
    response_dir = as_path(str(workspace.get("response_dir", "")), manifest_dir)
    score_summary_path = as_path(str(workspace.get("score_summary_path", "")), manifest_dir)
    record_path = as_path(str(workspace.get("record_path", "")), manifest_dir)
    runbook_path = as_path(str(workspace.get("runbook_path", "")), manifest_dir)
    rubric_template_path = as_path(str(workspace.get("rubric_template_path", "")), manifest_dir)
    handoff_path = as_path(str(workspace.get("fresh_agent_handoff_path", "")), manifest_dir)

    check_exists(problems, "prompt_pack_dir", prompt_pack_dir, directory=True)
    check_exists(problems, "response_dir", response_dir, directory=True)
    check_exists(problems, "runbook", runbook_path, directory=False)
    for rel in ["index.json", "RUN_INSTRUCTIONS.md"]:
        check_exists(problems, f"prompt pack {rel}", prompt_pack_dir / rel, directory=False)
    if response_dir.exists() and any(response_dir.iterdir()):
        problems.append(f"response_dir should be empty before fresh-agent run: {response_dir}")
    if score_summary_path.exists():
        problems.append(f"score_summary_path should not exist before fresh-agent run: {score_summary_path}")

    prompt_checks = audit_prompt_hashes(workspace, manifest_dir, problems)
    record_check = audit_record(record_path, workspace, problems)
    rubric_check = audit_rubric(rubric_template_path, workspace, problems)
    handoff_check = audit_handoff(handoff_path, workspace, problems)

    if runbook_path.exists():
        runbook = runbook_path.read_text(encoding="utf-8", errors="replace")
        for term in ["fresh agent", "FRESH_AGENT_HANDOFF.md", "Do not give the fresh agent scenario JSON"]:
            if term not in runbook:
                problems.append(f"runbook missing {term!r}")

    return {
        "schema": "ctf-fresh-agent-readiness-audit-v1",
        "ok": not problems,
        "ready_for_fresh_agent": not problems,
        "workspace_manifest": str(workspace_manifest),
        "run_id": workspace.get("run_id", ""),
        "suite_version": workspace.get("suite_version", ""),
        "scenario_count": workspace.get("scenario_count", 0),
        "prompt_count": len(workspace.get("prompt_hashes", [])),
        "material_paths": {
            "prompt_pack_dir": str(prompt_pack_dir),
            "response_dir": str(response_dir),
            "record": str(record_path),
            "runbook": str(runbook_path),
            "rubric_template": str(rubric_template_path),
            "fresh_agent_handoff": str(handoff_path),
        },
        "prompt_checks": prompt_checks,
        "record_check": record_check,
        "rubric_check": rubric_check,
        "handoff_check": handoff_check,
        "forbidden_leak_terms": sorted(FORBIDDEN_LEAK_TERMS),
        "problems": problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit fresh-agent forward workspace readiness")
    parser.add_argument("workspace_manifest")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    result = audit_workspace(Path(args.workspace_manifest))
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"fresh_agent_readiness_ok={result['ok']} prompts={result.get('prompt_count', 0)}")
        for problem in result["problems"]:
            print(f"- {problem}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
