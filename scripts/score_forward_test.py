#!/usr/bin/env python3
"""Heuristically score a forward-test response against a scenario JSON file."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def present(text: str, needle: str) -> bool:
    return re.search(re.escape(needle), text, re.I) is not None


def score_text(scenario: dict, response: str) -> dict:
    expected_skills = scenario.get("expected_skills", [])
    must_include = scenario.get("must_include", [])
    must_not_include = scenario.get("must_not_include", [])

    skill_hits = [skill for skill in expected_skills if present(response, skill)]
    include_hits = [item for item in must_include if present(response, item)]
    forbidden_hits = [item for item in must_not_include if present(response, item)]

    # This is a fast regression smoke score, not a substitute for the human rubric.
    auto_points = 0
    auto_points += 2 if len(skill_hits) == len(expected_skills) else (1 if skill_hits else 0)
    auto_points += 2 if len(include_hits) == len(must_include) else (1 if include_hits else 0)
    auto_points += 2 if not forbidden_hits else 0

    return {
        "scenario_id": scenario.get("id", ""),
        "expected_skills": expected_skills,
        "expected_skills_mentioned": skill_hits,
        "must_include": must_include,
        "must_include_present": include_hits,
        "must_not_include": must_not_include,
        "must_not_include_present": forbidden_hits,
        "auto_points": auto_points,
        "auto_pass": auto_points >= 5 and not forbidden_hits,
        "human_rubric_minimum": scenario.get("rubric_minimum"),
        "note": "auto_points are heuristic; use expected-behavior.md for final scoring",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score a forward-test response")
    parser.add_argument("scenario_json")
    parser.add_argument("response_file")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    scenario = json.loads(Path(args.scenario_json).read_text(encoding="utf-8"))
    response = Path(args.response_file).read_text(encoding="utf-8", errors="replace")

    result = score_text(scenario, response)

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"scenario={result['scenario_id']} auto_points={result['auto_points']} auto_pass={result['auto_pass']}")
        if result["must_not_include_present"]:
            print("forbidden hits:", ", ".join(result["must_not_include_present"]))
        missing = [item for item in result["must_include"] if item not in result["must_include_present"]]
        if missing:
            print("missing required hints:", ", ".join(missing))
    return 0 if result["auto_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
