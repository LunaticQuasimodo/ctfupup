#!/usr/bin/env python3
"""Verify a fresh-agent forward-test run record."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


REQUIRED_FIELDS = [
    "schema",
    "run_id",
    "date",
    "agent_or_model",
    "suite_version",
    "fresh_context_confirmed",
    "expected_answers_disclosed",
    "prompt_pack_dir",
    "response_dir",
    "score_summary_path",
    "workspace_manifest_path",
    "rubric_template_path",
    "fresh_agent_handoff_path",
    "response_hashes",
    "human_rubric",
    "pass_fail",
]


def resolve(base: Path, value: str) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else base / path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(record_path: Path) -> dict:
    base = record_path.resolve().parents[1]
    record = load_json(record_path)
    problems: list[str] = []

    for field in REQUIRED_FIELDS:
        if field not in record or record.get(field) in ("", None):
            problems.append(f"record missing field {field}")

    if record.get("schema") != "ctf-forward-run-record-v1":
        problems.append("schema is not ctf-forward-run-record-v1")
    if record.get("fresh_context_confirmed") is not True:
        problems.append("fresh_context_confirmed is not true")
    if record.get("fork_context") is True:
        problems.append("fork_context must be false for clean forward-test evidence")
    if record.get("expected_answers_disclosed") is not False:
        problems.append("expected_answers_disclosed must be false")
    if record.get("pass_fail") != "pass":
        problems.append("pass_fail is not pass")

    prompt_pack_dir = resolve(base, record.get("prompt_pack_dir", ""))
    response_dir = resolve(base, record.get("response_dir", ""))
    score_summary_path = resolve(base, record.get("score_summary_path", ""))
    workspace_manifest_path = resolve(base, record.get("workspace_manifest_path", ""))
    rubric_template_path = resolve(base, record.get("rubric_template_path", ""))
    fresh_agent_handoff_path = resolve(base, record.get("fresh_agent_handoff_path", ""))
    for label, path in [
        ("prompt_pack_dir", prompt_pack_dir),
        ("response_dir", response_dir),
        ("score_summary_path", score_summary_path),
        ("workspace_manifest_path", workspace_manifest_path),
        ("rubric_template_path", rubric_template_path),
        ("fresh_agent_handoff_path", fresh_agent_handoff_path),
    ]:
        if path is None:
            continue
        if not path.exists():
            problems.append(f"{label} does not exist: {path}")

    workspace = load_json(workspace_manifest_path) if workspace_manifest_path is not None and workspace_manifest_path.exists() and workspace_manifest_path.is_file() else {}
    if workspace:
        if workspace.get("schema") != "ctf-forward-run-workspace-v1":
            problems.append("workspace manifest schema is not ctf-forward-run-workspace-v1")
        if workspace.get("integrity_audit_ok") is not True:
            problems.append("workspace manifest integrity_audit_ok is not true")
        if workspace.get("scenario_count", 0) < 5:
            problems.append("workspace manifest scenario_count is too low")
        for item in workspace.get("prompt_hashes", []):
            path_value = item.get("path", "")
            prompt_path = Path(path_value)
            if not prompt_path.exists():
                problems.append(f"prompt hash path does not exist: {path_value}")
                continue
            if item.get("sha256") != sha256_file(prompt_path):
                problems.append(f"prompt hash mismatch: {path_value}")
        rubric_path_value = workspace.get("rubric_template_path", "")
        if rubric_path_value and not Path(rubric_path_value).exists():
            problems.append(f"workspace rubric_template_path does not exist: {rubric_path_value}")
        handoff_path_value = workspace.get("fresh_agent_handoff_path", "")
        if not handoff_path_value:
            problems.append("workspace missing fresh_agent_handoff_path")
        elif not Path(handoff_path_value).exists():
            problems.append(f"workspace fresh_agent_handoff_path does not exist: {handoff_path_value}")
        elif fresh_agent_handoff_path is not None and Path(handoff_path_value).resolve() != fresh_agent_handoff_path.resolve():
            problems.append("workspace fresh_agent_handoff_path does not match run record")

    summary = load_json(score_summary_path) if score_summary_path is not None and score_summary_path.exists() and score_summary_path.is_file() else {}
    if summary:
        if summary.get("schema") != "ctf-forward-suite-score-v1":
            problems.append("score summary schema is not ctf-forward-suite-score-v1")
        if summary.get("auto_pass") is not True:
            problems.append("score summary auto_pass is not true")
        if summary.get("missing_count", 1) != 0:
            problems.append("score summary has missing responses")
        if summary.get("failed_count", 1) != 0:
            problems.append("score summary has failed responses")
        for item in summary.get("results", []):
            response_path = item.get("response_path")
            if response_path and not Path(response_path).exists():
                problems.append(f"response path does not exist: {response_path}")
    rubric_template = load_json(rubric_template_path) if rubric_template_path is not None and rubric_template_path.exists() and rubric_template_path.is_file() else {}
    if rubric_template:
        if rubric_template.get("schema") != "ctf-forward-human-rubric-v1":
            problems.append("rubric template schema is not ctf-forward-human-rubric-v1")
        if summary and len(rubric_template.get("scenario_scores", [])) != summary.get("scenario_count"):
            problems.append("rubric template scenario_scores count does not match scenario_count")
    if fresh_agent_handoff_path is not None and fresh_agent_handoff_path.exists() and fresh_agent_handoff_path.is_file():
        handoff_text = fresh_agent_handoff_path.read_text(encoding="utf-8", errors="replace").lower()
        for forbidden in ["expected_skills", "must_include", "must_not_include", "rubric_minimum", "expected_answers"]:
            if forbidden in handoff_text:
                problems.append(f"fresh-agent handoff leaks forbidden term: {forbidden}")
        if "fresh-agent handoff" not in handoff_text:
            problems.append("fresh-agent handoff title missing")
    response_hash_entries = record.get("response_hashes", [])
    if not isinstance(response_hash_entries, list) or not response_hash_entries:
        problems.append("response_hashes are missing")
    elif summary and len(response_hash_entries) != summary.get("scenario_count"):
        problems.append("response_hashes count does not match scenario_count")
    for item in response_hash_entries if isinstance(response_hash_entries, list) else []:
        path_value = item.get("path", "")
        response_path = Path(path_value)
        if not response_path.exists():
            problems.append(f"response hash path does not exist: {path_value}")
            continue
        if item.get("sha256") != sha256_file(response_path):
            problems.append(f"response hash mismatch: {path_value}")

    rubric = record.get("human_rubric", {})
    if rubric.get("completed") is not True:
        problems.append("human rubric is not completed")
    if rubric.get("minimum_total_met") is not True:
        problems.append("human rubric minimum_total_met is not true")
    if rubric.get("no_untrusted_content_zero") is not True:
        problems.append("human rubric no_untrusted_content_zero is not true")
    if summary and len(rubric.get("scenario_scores", [])) != summary.get("scenario_count"):
        problems.append("human rubric scenario_scores count does not match scenario_count")

    return {
        "schema": "ctf-forward-run-verification-v1",
        "record_path": str(record_path),
        "ok": not problems,
        "problems": problems,
        "run_id": record.get("run_id", ""),
        "scenario_count": summary.get("scenario_count", 0) if summary else 0,
        "passed_count": summary.get("passed_count", 0) if summary else 0,
        "pass_fail": record.get("pass_fail", ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify fresh-agent forward-test run record")
    parser.add_argument("record_json")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    result = verify(Path(args.record_json))
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']} run_id={result['run_id']} scenarios={result['scenario_count']}")
        for problem in result["problems"]:
            print(f"- {problem}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
