#!/usr/bin/env python3
"""Prepare and score CTF Agent forward-test scenarios."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from score_forward_test import score_text


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIOS = ROOT / "forward-tests" / "scenarios"
RESPONSE_SUFFIXES = (".md", ".txt", ".response.md", ".response.txt")


def load_scenarios(scenario_dir: Path) -> list[dict]:
    scenarios = []
    for path in sorted(scenario_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_path"] = str(path)
        scenarios.append(data)
    return scenarios


def response_candidates(response_dir: Path, scenario_id: str) -> list[Path]:
    candidates = []
    for suffix in RESPONSE_SUFFIXES:
        candidates.append(response_dir / f"{scenario_id}{suffix}")
    candidates.append(response_dir / scenario_id / "response.md")
    candidates.append(response_dir / scenario_id / "response.txt")
    return candidates


def find_response(response_dir: Path, scenario_id: str) -> Path | None:
    for candidate in response_candidates(response_dir, scenario_id):
        if candidate.exists():
            return candidate
    return None


def write_prompt_pack(scenarios: list[dict], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    index = []
    for scenario in scenarios:
        scenario_id = scenario["id"]
        prompt_path = out_dir / f"{scenario_id}.prompt.txt"
        prompt_path.write_text(scenario["prompt"].rstrip() + "\n", encoding="utf-8")
        index.append({
            "id": scenario_id,
            "title": scenario.get("title", ""),
            "prompt_file": str(prompt_path),
            "response_file_expected": f"{scenario_id}.md",
            "do_not_include_expected_answers": True,
        })
        written.append(prompt_path)
    (out_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "RUN_INSTRUCTIONS.md").write_text(
        "# Fresh-Agent Forward Test\n\n"
        "Start a fresh agent/thread for each prompt or one fresh agent with no prior skill-development context.\n"
        "Pass only the prompt text and the local skill path mentioned in that prompt.\n"
        "Do not include scenario JSON, expected-behavior.md, score output, intended answers, or prior analysis.\n"
        "Save each response as `<scenario-id>.md` in the response directory.\n"
        "After responses are saved, score them with `scripts/run_forward_suite.py --responses-dir <dir> --out <score.json> --json`.\n",
        encoding="utf-8",
    )
    return written


def score_responses(scenarios: list[dict], response_dir: Path) -> dict:
    results = []
    for scenario in scenarios:
        scenario_id = scenario.get("id", "")
        response_path = find_response(response_dir, scenario_id)
        if response_path is None:
            results.append({
                "scenario_id": scenario_id,
                "response_path": None,
                "auto_pass": False,
                "missing_response": True,
                "note": "No response file found for scenario.",
            })
            continue
        response = response_path.read_text(encoding="utf-8", errors="replace")
        result = score_text(scenario, response)
        result["response_path"] = str(response_path)
        result["missing_response"] = False
        results.append(result)

    passed = [item for item in results if item.get("auto_pass")]
    missing = [item for item in results if item.get("missing_response")]
    failed = [item for item in results if not item.get("auto_pass") and not item.get("missing_response")]
    return {
        "schema": "ctf-forward-suite-score-v1",
        "scenario_count": len(scenarios),
        "passed_count": len(passed),
        "failed_count": len(failed),
        "missing_count": len(missing),
        "auto_pass": len(results) == len(passed),
        "results": results,
    }


def render_text(summary: dict) -> str:
    lines = [
        f"scenario_count={summary['scenario_count']}",
        f"passed={summary['passed_count']}",
        f"failed={summary['failed_count']}",
        f"missing={summary['missing_count']}",
        f"auto_pass={summary['auto_pass']}",
    ]
    for item in summary["results"]:
        status = "missing" if item.get("missing_response") else ("pass" if item.get("auto_pass") else "fail")
        lines.append(f"{item['scenario_id']}: {status}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare and score forward-test scenario suites")
    parser.add_argument("--scenarios-dir", default=DEFAULT_SCENARIOS)
    parser.add_argument("--list", action="store_true", help="List available scenarios")
    parser.add_argument("--prompt-pack-dir", help="Write answer-free scenario prompts to this directory")
    parser.add_argument("--responses-dir", help="Directory containing one response file per scenario")
    parser.add_argument("--out", help="Write score summary JSON to this path")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    scenarios = load_scenarios(Path(args.scenarios_dir))
    if args.list:
        listing = [{"id": item.get("id"), "title": item.get("title")} for item in scenarios]
        if args.as_json:
            print(json.dumps({"scenarios": listing}, ensure_ascii=False, indent=2))
        else:
            for item in listing:
                print(f"{item['id']}: {item['title']}")

    if args.prompt_pack_dir:
        written = write_prompt_pack(scenarios, Path(args.prompt_pack_dir))
        if not args.responses_dir and not args.list:
            print(json.dumps({"prompt_files": [str(path) for path in written]}, ensure_ascii=False, indent=2) if args.as_json else f"Wrote {len(written)} prompts")

    if args.responses_dir:
        summary = score_responses(scenarios, Path(args.responses_dir))
        if args.out:
            Path(args.out).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.as_json:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print(render_text(summary), end="")
        return 0 if summary["auto_pass"] else 1

    if not args.list and not args.prompt_pack_dir:
        print("Choose --list, --prompt-pack-dir, or --responses-dir.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
