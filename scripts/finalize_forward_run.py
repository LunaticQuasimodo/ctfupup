#!/usr/bin/env python3
"""Finalize a fresh-agent forward-test workspace after responses are collected."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from init_forward_run import sha256_file
from run_forward_suite import DEFAULT_SCENARIOS, load_scenarios, score_responses


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def response_hashes(summary: dict[str, Any]) -> list[dict[str, str]]:
    hashes = []
    for item in summary.get("results", []):
        response_path = item.get("response_path")
        if not response_path:
            continue
        path = Path(response_path)
        if not path.exists():
            continue
        hashes.append({
            "scenario_id": item.get("scenario_id", ""),
            "path": str(path),
            "sha256": sha256_file(path),
        })
    return hashes


def normalize_rubric(rubric: dict[str, Any] | None, summary: dict[str, Any]) -> dict[str, Any]:
    if not rubric:
        return {
            "completed": False,
            "minimum_total_met": False,
            "no_untrusted_content_zero": False,
            "scenario_scores": [],
        }
    scenario_scores = rubric.get("scenario_scores", [])
    if not isinstance(scenario_scores, list):
        scenario_scores = []
    return {
        "completed": rubric.get("completed") is True,
        "minimum_total_met": rubric.get("minimum_total_met") is True,
        "no_untrusted_content_zero": rubric.get("no_untrusted_content_zero") is True,
        "scenario_scores": scenario_scores,
        "source": rubric.get("source", "external-rubric-json"),
        "scenario_count_expected": summary.get("scenario_count", 0),
    }


def compute_pass_fail(record: dict[str, Any], summary: dict[str, Any], pass_fail: str) -> str:
    if pass_fail != "auto":
        return pass_fail
    rubric = record.get("human_rubric", {})
    eligible = (
        summary.get("auto_pass") is True
        and summary.get("missing_count") == 0
        and summary.get("failed_count") == 0
        and record.get("fresh_context_confirmed") is True
        and record.get("fork_context") is False
        and record.get("expected_answers_disclosed") is False
        and rubric.get("completed") is True
        and rubric.get("minimum_total_met") is True
        and rubric.get("no_untrusted_content_zero") is True
        and len(rubric.get("scenario_scores", [])) == summary.get("scenario_count")
    )
    return "pass" if eligible else "fail"


def finalize_forward_run(
    record_path: Path,
    scenarios_dir: Path,
    agent_or_model: str | None,
    confirm_fresh_context: bool,
    fork_context: bool,
    expected_answers_disclosed: bool,
    rubric_path: Path | None,
    pass_fail: str,
) -> dict[str, Any]:
    record_path = record_path.resolve()
    record_base = record_path.parent
    record = load_json(record_path)
    response_dir = resolve(record_base, record.get("response_dir", ""))
    score_path = resolve(record_base, record.get("score_summary_path", ""))

    scenarios = load_scenarios(scenarios_dir)
    summary = score_responses(scenarios, response_dir)
    score_path.parent.mkdir(parents=True, exist_ok=True)
    score_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rubric = normalize_rubric(load_json(rubric_path) if rubric_path else None, summary)
    record.update({
        "agent_or_model": agent_or_model or record.get("agent_or_model", ""),
        "fresh_context_confirmed": confirm_fresh_context,
        "fork_context": fork_context,
        "expected_answers_disclosed": expected_answers_disclosed,
        "score_summary_path": str(score_path),
        "response_hashes": response_hashes(summary),
        "human_rubric": rubric,
        "finalized_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    })
    record["pass_fail"] = compute_pass_fail(record, summary, pass_fail)
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "schema": "ctf-forward-run-finalize-v1",
        "ok": True,
        "record": str(record_path),
        "score_summary": str(score_path),
        "scenario_count": summary.get("scenario_count", 0),
        "passed_count": summary.get("passed_count", 0),
        "failed_count": summary.get("failed_count", 0),
        "missing_count": summary.get("missing_count", 0),
        "auto_pass": summary.get("auto_pass", False),
        "rubric_completed": rubric.get("completed", False),
        "fresh_context_confirmed": record.get("fresh_context_confirmed", False),
        "expected_answers_disclosed": record.get("expected_answers_disclosed", False),
        "pass_fail": record.get("pass_fail", ""),
        "response_hash_count": len(record.get("response_hashes", [])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize a fresh-agent forward-test run record")
    parser.add_argument("record_json")
    parser.add_argument("--scenarios-dir", default=DEFAULT_SCENARIOS)
    parser.add_argument("--agent-or-model")
    parser.add_argument("--confirm-fresh-context", action="store_true")
    parser.add_argument("--fork-context", action="store_true")
    parser.add_argument("--expected-answers-disclosed", action="store_true")
    parser.add_argument("--rubric-json", help="External human-rubric JSON with completed/minimum/no-untrusted/scenario_scores")
    parser.add_argument("--pass-fail", choices=["auto", "pass", "fail", "not_run"], default="auto")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    scenarios_dir = Path(args.scenarios_dir)
    if not scenarios_dir.is_absolute():
        scenarios_dir = ROOT / scenarios_dir
    rubric_path = Path(args.rubric_json).resolve() if args.rubric_json else None
    result = finalize_forward_run(
        Path(args.record_json),
        scenarios_dir,
        args.agent_or_model,
        args.confirm_fresh_context,
        args.fork_context,
        args.expected_answers_disclosed,
        rubric_path,
        args.pass_fail,
    )
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"finalize_ok={result['ok']} pass_fail={result['pass_fail']} auto_pass={result['auto_pass']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
